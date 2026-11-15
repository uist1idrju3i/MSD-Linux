#!/usr/bin/env python3
"""新規directoryだけを使うstage Aの生成・反復・smoke入口。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

from stage_a import independent_check, judge, locate, parameters

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def table():
    return [line.split() for line in (HERE / "expectations-v3.tsv").read_text().splitlines()]


def prepare(args):
    args.destination.mkdir()
    seed = args.destination / "seed"
    seed.mkdir()
    for name in sorted({row[1] for row in table()}):
        subprocess.run(["bash", str(HERE / "make-case.sh"), name, str(args.output),
                        str(args.base if name in ("F0-A2", "F5-A2") else seed),
                        str(seed / name)], check=True)
        if name == "F5-A2":
            continue
    for name, source, expected, mode in table():
        dest = args.destination / name
        shutil.copytree(seed / source, dest, symlinks=True,
                        ignore=shutil.ignore_patterns("rootfs-tree"))
        p = parameters(seed / ("F5-A2" if source == "F5-A2" else "F0-A2") /
                       "verity-parameters.env")
        p.setdefault("fec_roots", "0")
        append = (dest / "qemu-extra-append.txt").read_text()
        append = append.replace("panic_on_corruption", "restart_on_corruption") if mode == "restart" else append
        if mode == "eio":
            append = append.replace("9 use_fec_from_device", "8 use_fec_from_device")
            append = append.replace(" panic_on_corruption", "")
        (dest / "qemu-extra-append.txt").write_text(append)
        if source == "F5-A2":
            image = (dest / "rootfs.img").read_bytes()
            off = int(p["data_blocks"]) // 2 * 4096 + 123
            clean = bytearray(image)
            clean[off] ^= 255
            offsets = [off]
        else:
            clean = (seed / "F0-A2/rootfs.img").read_bytes()
            image = (dest / "rootfs.img").read_bytes()
            offsets = [i for i, (a, b) in enumerate(zip(clean, image)) if a != b]
            if len(image) != len(clean):
                raise ValueError("image size mismatch")
        locations = [dict(locate(off, p), before=clean[off], after=image[off]) for off in offsets]
        expected_changes = 24 if source in ("F2-A2", "F6-A2") else int(source in ("F1-A2", "F3-A2", "F5-A2"))
        if len(locations) != expected_changes:
            raise ValueError("unexpected injection count")
        info = parameters(dest / "variant-info.txt")
        start = int(info["rootfs_a_start_sector"]) * 512
        with (dest / "images/sdcard.img").open("rb") as f:
            f.seek(start)
            if f.read(len(image)) != image:
                raise ValueError("partition readback mismatch")
        save(dest / "location.json", dict(version=3, case=name, mode=mode, expected=expected,
                                         parameters=p, locations=locations,
                                         root_hash_override=source == "F4-A2",
                                         independent=independent_check(clean, image, p, locations)))
        save(dest / "inputs.json", {str(f.relative_to(dest)): sha(f) for f in
                                   [dest / "rootfs.img", dest / "images/sdcard.img",
                                    dest / "images/Image", dest / "images/bcm2710-rpi-cm0.dtb",
                                    dest / "qemu-extra-append.txt", dest / "location.json"]})
        print("prepared", name, "changed_bytes", len(locations), flush=True)


def boot(case_dir, expected, out, timeout, restart_watchdog):
    out.mkdir()
    events = []
    env = os.environ.copy()
    env.update(ROOT_DEVICE="/dev/dm-0", QEMU_ICOUNT="shift=0", QEMU_COPY_IMAGE="0",
               QEMU_EXTRA_APPEND=(case_dir / "qemu-extra-append.txt").read_text(),
               KERNEL_IMAGE=str(case_dir / "images/Image"),
               DTB_IMAGE=str(case_dir / "images/bcm2710-rpi-cm0.dtb"))
    watchdog = expected in ("restart-request", "restart-reset") and restart_watchdog == "on"
    env["QEMU_WATCHDOG"] = "1" if watchdog else "0"
    image = out / "sdcard.img"
    shutil.copyfile(case_dir / "images/sdcard.img", image)
    with image.open("r+b") as f:
        f.truncate(1 << (image.stat().st_size - 1).bit_length())
    qmp_path = out / "qmp.sock"
    env["QEMU_QMP_SOCKET"] = str(qmp_path)
    env["QEMU_EXTRA_ARGS"] = "" if expected == "restart-reset" else "-no-reboot"
    serial_path = out / "serial.log"
    start = time.monotonic()
    reason, client, buffer = "timeout", None, b""
    with serial_path.open("wb") as serial:
        process = subprocess.Popen(["bash", str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"),
                                    str(image)], stdout=serial, stderr=serial, env=env)
        try:
            while time.monotonic() - start < timeout:
                if client is None and qmp_path.exists():
                    client = socket.socket(socket.AF_UNIX)
                    client.connect(str(qmp_path))
                    client.setblocking(False)
                    client.sendall(b'{"execute":"qmp_capabilities"}\r\n')
                if client:
                    try:
                        buffer += client.recv(65536)
                    except BlockingIOError:
                        pass
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        event = json.loads(line)
                        event["host_elapsed_seconds"] = time.monotonic() - start
                        event["after_restart_marker"] = (
                            "reboot: Restarting system" in serial_path.read_text(errors="replace"))
                        events.append(event)
                text = serial_path.read_text(errors="replace")
                status = process.poll()
                if status is not None:
                    reason = "natural-exit"
                    break
                for candidate in ("ready", "panic", "eio", "reset-observed"):
                    if judge(text, expected, None, candidate, events)["functional_pass"]:
                        reason = candidate
                        break
                if reason != "timeout":
                    break
                if "Kernel panic" in text or "MSD/Linux ready" in text:
                    reason = "unexpected-terminal-marker"
                    break
                time.sleep(0.2)
        finally:
            observed_text = serial_path.read_text(errors="replace")
            observed_status = process.poll()
            host_terminated = observed_status is None
            if host_terminated:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if client:
                client.close()
    elapsed = time.monotonic() - start
    result = judge(observed_text, expected, observed_status, reason, events)
    result.update(wall_seconds=elapsed, host_terminated_after_observation=host_terminated,
                  final_process_status=process.returncode, serial_sha256=sha(serial_path),
                  observation_bytes=len(observed_text.encode()), watchdog_enabled=watchdog)
    save(out / "qmp.json", events)
    save(out / "functional.json", result)
    image.unlink()
    qmp_path.unlink(missing_ok=True)
    return result


def run(args):
    args.destination.mkdir()
    shutil.copy2(HERE / "expectations-v3.tsv", args.destination / "expectations.tsv")
    save(args.destination / "harness.json", {f.name: sha(f) for f in
                                           [Path(__file__), HERE / "stage_a.py", HERE / "expectations-v3.tsv",
                                            ROOT / "board/cardputerzero/qemu/run-qemu.sh"]})
    save(args.destination / "settings.json", dict(runs=args.runs, timeout=args.timeout,
                                                restart_watchdog=args.restart_watchdog))
    failed = False
    for name, _, expected, _ in table():
        if args.case and name not in args.case:
            continue
        case_dir = args.base / name
        manifest = json.loads((case_dir / "inputs.json").read_text())
        if not manifest or any(sha(case_dir / f) != digest for f, digest in manifest.items()):
            raise ValueError("input hash mismatch")
        for repeat in range(args.runs):
            result = boot(case_dir, expected, args.destination / f"{name}-boot{repeat}",
                          args.timeout, args.restart_watchdog)
            print(name, repeat, json.dumps(result), flush=True)
            failed |= not result["functional_pass"]
    return int(failed)


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    prep = subs.add_parser("prepare")
    prep.add_argument("output", type=Path)
    prep.add_argument("base", type=Path)
    prep.add_argument("destination", type=Path)
    run_parser = subs.add_parser("run")
    run_parser.add_argument("base", type=Path)
    run_parser.add_argument("destination", type=Path)
    run_parser.add_argument("--runs", type=int, required=True)
    run_parser.add_argument("--timeout", type=int, default=600)
    run_parser.add_argument("--restart-watchdog", choices=["on", "off"], default="on")
    run_parser.add_argument("--case", choices=[row[0] for row in table()], action="append")
    args = parser.parse_args()
    for name in ("base", "destination", "output"):
        if hasattr(args, name):
            setattr(args, name, getattr(args, name).resolve())
    if args.command == "prepare":
        prepare(args)
        return 0
    if args.runs < 1 or args.timeout < 1:
        parser.error("positive runs/timeout required")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
