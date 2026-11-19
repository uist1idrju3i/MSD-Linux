#!/usr/bin/env python3
"""Interleave RAID6 benchmark boot variants using one common rootfs."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socket
import subprocess
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parse_serial(text, variant):
    text = text.replace("\r", "")
    markers = re.findall(r"^RAID6_BOOT_COMPLETE uptime=([0-9]+\.[0-9]+)$", text, re.M)
    if (len(markers) != 1 or text.splitlines().count("RAID6_DONE") != 1
            or re.findall(r"^RAID6_PROBE_EXIT=(.*)$", text, re.M) != ["0"]
            or re.search(r"Kernel panic|\bOops:|\bBUG:|RAID6_PROBE_EXIT=[1-9]", text)
            or text.splitlines().count("RAID6_BTRFS_OK") != 1):
        raise ValueError("incomplete or failed boot")
    for profile in ("Data, single:", "Metadata, DUP:"):
        if profile not in text:
            raise ValueError("missing Btrfs profile")
    for counter in ("read_errors", "csum_errors", "verify_errors", "uncorrectable_errors"):
        if re.findall(rf"^\s*{counter}:\s+(\S+)\s*$", text, re.M) != ["0"]:
            raise ValueError("missing or nonzero scrub counter")
    throughput = re.findall(r"^.*raid6:.*(?:gen\(\)|xor\(\)).*MB/s.*$", text, re.M)
    skipped = re.findall(r"raid6: skipped pq benchmark and selected (\S+)", text)
    measured = re.findall(r"raid6: using algorithm (\S+) gen\(\)", text)
    if variant == "A" and (len(measured) != 1 or not throughput or skipped):
        raise ValueError("benchmark-on evidence missing")
    if variant == "B" and (len(skipped) != 1 or throughput or measured):
        raise ValueError("benchmark-off evidence missing")
    if variant not in ("A", "B"):
        raise ValueError("unknown variant")
    def initcall(name):
        values = re.findall(rf"initcall {name}\+.*? returned 0 after (\d+) usecs", text)
        return int(values[0]) if len(values) == 1 else None
    return dict(boot_seconds=float(markers[0]), algorithm=(measured or skipped)[0],
                raid6_init_us=initcall("raid6_select_algo"),
                xor_init_us=initcall("calibrate_xor_blocks"),
                throughput_lines=len(throughput))


def command(args, log):
    subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, check=True)


def record_path(path):
    absolute = path.resolve()
    try:
        return str(absolute.relative_to(ROOT))
    except ValueError:
        return str(absolute)


def prepare(output, runs):
    destination = runs / "prepared"
    inputs = [destination / "sdcard.img", destination / "rootfs.squashfs",
              destination / "qemu.dtb", HERE / "guest.sh", HERE / "run.py"]
    labels = {path: record_path(path) for path in inputs}
    destination.mkdir(parents=True)
    with (destination / "prepare.log").open("x") as log:
        tree = destination / "root"
        command([output / "host/bin/unsquashfs", "-no-progress", "-no-xattrs",
                 "-d", tree, output / "images/rootfs.squashfs"], log)
        hook = tree / "etc/init.d/S99zzzz-raid6-probe"
        shutil.copyfile(HERE / "guest.sh", hook)
        hook.chmod(0o755)
        squash = destination / "rootfs.squashfs"
        command([output / "host/bin/mksquashfs", tree, squash, "-noappend", "-all-root",
                 "-no-xattrs", "-no-progress", "-comp", "zstd", "-b", "131072"], log)
        image = destination / "sdcard.img"
        command(["cp", "--reflink=auto", "--sparse=always", output / "images/sdcard.img", image], log)
        table = json.loads(subprocess.check_output(
            [str(output / "host/sbin/sfdisk"), "--json", str(image)], text=True))
        partitions = table["partitiontable"]["partitions"]
        if len(partitions) != 7:
            raise ValueError("unexpected partition table")
        for partition in partitions[4:6]:
            if squash.stat().st_size > partition["size"] * 512:
                raise ValueError("probe rootfs does not fit")
            command(["dd", f"if={squash}", f"of={image}", "bs=512",
                     f"seek={partition['start']}", "conv=notrunc", "status=none"], log)
        command(["cp", output / "images/bcm2710-rpi-3-b.dtb", destination / "qemu.dtb"], log)
    (destination / "inputs.json").write_text(json.dumps(
        {labels[p]: sha(p) for p in inputs}, indent=2) + "\n")


def quit_qemu(path):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(path))
        stream = client.makefile("rwb")
        if "QMP" not in json.loads(stream.readline()):
            raise ValueError("missing QMP greeting")
        for name in ("qmp_capabilities", "quit"):
            stream.write(json.dumps({"execute": name}).encode() + b"\n")
            stream.flush()
            while True:
                response = json.loads(stream.readline())
                if "error" in response:
                    raise ValueError(response)
                if "return" in response:
                    break


def boot(output, runs, variant, run_id):
    directory = runs / run_id
    directory.mkdir()
    qmp = directory / "qmp.sock"
    if len(str(qmp)) >= 100:
        raise ValueError("QMP path too long")
    env = dict(os.environ, OUTPUT_DIR=str(output), QEMU_MACHINE="raspi3b",
               KERNEL_IMAGE=str(runs / variant / "Image"),
               DTB_IMAGE=str(runs / "prepared/qemu.dtb"),
               QEMU_QMP_SOCKET=str(qmp), QEMU_COPY_IMAGE="1",
               QEMU_EXTRA_APPEND="initcall_debug printk.time=1")
    for key in ("QEMU_DRIVE_FILE", "QEMU_ICOUNT", "QEMU_EXTRA_ARGS", "ROOT_DEVICE", "ROOT_FSTYPE"):
        env.pop(key, None)
    start = time.monotonic()
    process = subprocess.Popen(
        [str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(runs / "prepared/sdcard.img")],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    data = bytearray()
    loads = []
    wall_marker = None
    result = dict(status="failed", error="incomplete")
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while time.monotonic() - start < 900:
                loads.append([time.monotonic() - start, *os.getloadavg()])
                for key, _ in selector.select(1):
                    block = os.read(key.fd, 65536)
                    if not block:
                        raise RuntimeError("QEMU exited before guest completion")
                    data.extend(block)
                if len(data) > 16 * 1024 * 1024:
                    raise RuntimeError("serial log limit")
                if b"RAID6_BOOT_COMPLETE uptime=" in data and wall_marker is None:
                    wall_marker = time.monotonic() - start
                if re.search(rb"RAID6_PROBE_EXIT=[0-9]+\r?\n", data):
                    break
            else:
                raise TimeoutError("guest deadline")
        quit_qemu(qmp)
        code = process.wait(timeout=30)
        data.extend(process.stdout.read())
        if code != 0:
            raise RuntimeError("QEMU nonzero exit")
        result = parse_serial(data.decode(errors="replace"), variant)
        result.update(status="passed", error=None)
    except Exception as exc:
        result = dict(status="failed", error=str(exc))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        data.extend(process.stdout.read())
        (directory / "serial.log").write_bytes(data)
        (directory / "load.json").write_text(json.dumps(loads) + "\n")
    result.update(run_id=run_id, variant=variant, wall_marker_seconds=wall_marker,
                  host_load_start=loads[0][1], host_load_end=loads[-1][1],
                  host_load_min=min(row[1] for row in loads),
                  host_load_max=max(row[1] for row in loads),
                  serial_sha256=sha(directory / "serial.log"), qemu_exit=process.returncode)
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "measure"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    args = parser.parse_args()
    output, runs = args.output.resolve(), args.runs.resolve()
    if args.action == "prepare":
        prepare(output, runs)
        return
    results = []
    with (runs / "results.csv").open("x") as stream:
        fields = ["run_id", "variant", "status", "boot_seconds", "wall_marker_seconds",
                  "algorithm", "raid6_init_us", "xor_init_us", "throughput_lines",
                  "host_load_start", "host_load_end", "host_load_min", "host_load_max",
                  "serial_sha256", "qemu_exit", "error"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for run_id, variant in ([("calibration-1", "A"), ("calibration-2", "A")]
                                + [(f"{number}-{variant}", variant) for number in range(1, 6)
                                   for variant in ("A", "B")]):
            result = boot(output, runs, variant, run_id)
            results.append(result)
            writer.writerow(result)
            stream.flush()
            if result["status"] != "passed":
                raise RuntimeError(result["error"])
    (runs / "complete.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
