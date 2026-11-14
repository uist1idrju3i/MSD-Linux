#!/usr/bin/env python3
"""Collect guest counters over serial without modifying the product rootfs."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[5]
FIELDS = ["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"]
DEVICES = {"mmcblk0"} | {f"mmcblk0p{i}" for i in range(1, 8)}


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parse_samples(text, windows):
    samples = {}
    for phase, repeat, uptime, device, raw in re.findall(
        r"^MSDSTAT,([^,]+),(\d+),([\d.]+),([^,]+),([^\r\n]+)", text, re.MULTILINE
    ):
        key = phase, int(repeat), device
        values = [int(value) for value in raw.split()]
        if key in samples or device not in DEVICES or len(values) < 11:
            raise ValueError(f"invalid or duplicate sample: {key}")
        samples[key] = (float(uptime), values[6], raw)
    expected = {("boot", 0, device) for device in DEVICES}
    for phase, count in [("idle", windows), ("ram", 1), ("disk", 1)]:
        for repeat in range(1, count + 1) if phase == "idle" else [0]:
            for edge in ["before", "after"]:
                expected.update((f"{phase}-{edge}", repeat, device) for device in DEVICES)
    if set(samples) != expected:
        raise ValueError("missing or unexpected samples")
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Buildroot O= directory")
    parser.add_argument("--run-dir", type=Path, required=True, help="must not exist")
    parser.add_argument("--variant", required=True)
    parser.add_argument("--seconds", type=positive, default=120)
    parser.add_argument("--windows", type=positive, default=5)
    args = parser.parse_args()
    output = args.output.resolve()
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    images = output / "images"
    inputs = [images / name for name in [
        "sdcard.img", "rootfs.squashfs", "Image", "bcm2710-rpi-cm0.dtb"
    ]] + [
        output / ".config", Path(__file__), Path(__file__).with_name("guest.sh"),
        ROOT / "board/cardputerzero/qemu/run-qemu.sh",
        ROOT / "board/cardputerzero/qemu/check-serial-log.sh",
        ROOT / "board/cardputerzero/qemu/serial-allowlist.txt",
    ]
    metadata = {
        "variant": args.variant, "seconds": args.seconds, "windows": args.windows,
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    image = run_dir / "sdcard.img"
    shutil.copyfile(images / "sdcard.img", image)
    with image.open("r+b") as stream:
        stream.truncate(1 << (image.stat().st_size - 1).bit_length())
    env = dict(os.environ, OUTPUT_DIR=str(output), QEMU_COPY_IMAGE="0",
               QEMU_MACHINE="raspi3ap", QEMU_ICOUNT="", QEMU_EXTRA_APPEND="",
               QEMU_EXTRA_ARGS="", QEMU_QMP_SOCKET="", QEMU_HASH_IMAGE="1",
               KERNEL_IMAGE=str(images / "Image"),
               DTB_IMAGE=str(images / "bcm2710-rpi-cm0.dtb"),
               ROOT_DEVICE="/dev/mmcblk0p5", ROOT_FSTYPE="squashfs",
               QEMU_DRIVE_FILE=str(image), QEMU_DRIVE_FORMAT="raw",
               QEMU_WATCHDOG="0", QEMU_DTB_BLUETOOTH="0")
    command = [str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)]
    with (run_dir / "serial.log").open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, env=env)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        pending = bytearray()
        transcript = bytearray()

        def receive(marker, timeout):
            deadline = time.monotonic() + timeout
            while marker not in pending:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"waiting for {marker!r}")
                if not selector.select(timeout=1):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError(f"QEMU exited early: {process.poll()}")
                log.write(chunk)
                log.flush()
                pending.extend(chunk)
                transcript.extend(chunk)
            position = pending.index(marker) + len(marker)
            del pending[:position]

        def send(text):
            process.stdin.write(text.encode())
            process.stdin.flush()

        try:
            receive(b"login:", 300)
            send("root\n")
            receive(b"\n# ", 30)
            send("stty -echo\n")
            receive(b"\n# ", 30)
            send("cat > /run/msd-write-probe.sh <<'MSDPROBE_EOF'\n")
            receive(b"> ", 30)
            for line in Path(__file__).with_name("guest.sh").read_text().splitlines():
                send(line + "\n")
                receive(b"> ", 30)
            send("MSDPROBE_EOF\n")
            receive(b"# ", 30)
            send(f"sh /run/msd-write-probe.sh {args.seconds} {args.windows}\n")
            receive(b"MSDPROBE finished", args.seconds * args.windows + 180)
            receive(b"\n# ", 30)
            if process.poll() is not None:
                raise RuntimeError("QEMU exited unexpectedly after the probe")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            selector.close()
            process.stdin.close()
            process.stdout.close()
    text = transcript.decode(errors="replace")
    subprocess.run([str(ROOT / "board/cardputerzero/qemu/check-serial-log.sh"),
                    str(run_dir / "serial.log")], check=True)
    samples = parse_samples(text, args.windows)
    for phase, count in [("idle", args.windows), ("ram", 1), ("disk", 1)]:
        for repeat in range(1, count + 1) if phase == "idle" else [0]:
            deltas = {}
            for device in sorted(DEVICES):
                before = samples[f"{phase}-before", repeat, device]
                after = samples[f"{phase}-after", repeat, device]
                if after[0] < before[0] or after[1] < before[1]:
                    raise ValueError("counters or clock moved backwards")
                if phase == "idle" and after[0] - before[0] < args.seconds:
                    raise ValueError("idle interval is too short")
                deltas[device] = after[1] - before[1]
            if phase == "disk" and (deltas["mmcblk0p7"] < 2048 or deltas["mmcblk0"] < 2048):
                raise ValueError("disk positive control did not register 1 MiB")
            print(f"{args.variant} {phase} repeat={repeat} sectors={deltas}")
    with (run_dir / "raw.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for (phase, repeat, device), (uptime, sectors, raw) in samples.items():
            writer.writerow(dict(
                run_id=run_dir.name, variant=args.variant, repeat=repeat,
                metric=f"{device}.write_sectors", value=sectors, unit="sector512",
                valid="yes", note=f"phase={phase};uptime={uptime};stat={raw}"
            ))
    print(f"ok - complete counters and positive control: {run_dir}")


if __name__ == "__main__":
    main()
