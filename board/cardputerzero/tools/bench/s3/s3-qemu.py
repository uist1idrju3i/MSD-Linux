#!/usr/bin/env python3
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

QEMU = os.environ.get("QEMU_SYSTEM_AARCH64", "qemu-system-aarch64")


def prepare_disk(source, destination):
    shutil.copy2(source, destination)
    size = destination.stat().st_size
    padded_size = 1
    while padded_size < size:
        padded_size *= 2
    with destination.open("r+b") as disk:
        disk.truncate(padded_size)


def qemu_command(disk, log, append, qmp_socket=None):
    command_line = [
        "earlycon=pl011,mmio32,0x3f201000",
        "console=ttyAMA1,115200",
        "initcall_blacklist=bcm2835_wdt_driver_init",
        "root=/dev/mmcblk0p5",
        "rootwait",
        "ro",
        "rootfstype=squashfs",
    ]
    extra_append = append or os.environ.get("QEMU_EXTRA_APPEND", "")
    if extra_append:
        command_line.extend(extra_append.split())
    command = [
        QEMU,
        "-M", "raspi3b",
        "-m", "1G",
        "-kernel", str(Path(args.kernel).resolve()),
        "-dtb", str(Path(args.dtb).resolve()),
        "-drive", f"file={disk},if=sd,format=raw",
        "-append", " ".join(command_line),
        "-display", "none",
        "-monitor", "none",
        "-serial", f"file:{log}",
    ]
    if qmp_socket:
        command.extend(["-qmp", f"unix:{qmp_socket},server=on,wait=off"])
    return command


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def wait_for_text(log, token, process, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        text = log.read_text(errors="replace") if log.exists() else ""
        if token in text:
            return text
        if process.poll() is not None:
            raise RuntimeError(f"QEMU exited with {process.returncode}; log={log}")
        time.sleep(0.05)
    raise TimeoutError(f"timed out waiting for {token}; log={log}")


def marker_value(text, name):
    prefix = f"{name}="
    for line in text.splitlines():
        position = line.find(prefix)
        if position >= 0:
            value = line[position + len(prefix):].split()
            if not value:
                continue
            try:
                return int(value[0])
            except ValueError:
                continue
    return None


def measure_attempt(work):
    work.mkdir(parents=True, exist_ok=True)
    disk = work / "trial.img"
    log = work / "serial.log"
    for path in (disk, log):
        path.unlink(missing_ok=True)
    prepare_disk(Path(args.image), disk)
    process = subprocess.Popen(qemu_command(disk, log, args.append))
    try:
        started = False
        before = after = None
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            text = log.read_text(errors="replace") if log.exists() else ""
            if "S3BENCH_FAILED" in text:
                raise RuntimeError(f"guest benchmark failed; log={log}")
            if "S3BENCH_INVALID=1" in text:
                idle_before = marker_value(text, "S3BENCH_IDLE_SECTORS_BEFORE")
                idle_after = marker_value(text, "S3BENCH_IDLE_SECTORS_AFTER")
                idle_delta = marker_value(text, "S3BENCH_IDLE_DELTA")
                if idle_before is None or idle_after is None or idle_delta is None:
                    time.sleep(0.025)
                    continue
                return {
                    "valid": False,
                    "idle_sectors_before": idle_before,
                    "idle_sectors_after": idle_after,
                    "idle_delta_sectors": idle_delta,
                    "log": str(log),
                }
            started = started or "S3BENCH_START" in text
            before = marker_value(text, "S3BENCH_SECTORS_BEFORE")
            after = marker_value(text, "S3BENCH_SECTORS_AFTER")
            if started and "S3BENCH_DONE" in text:
                break
            if process.poll() is not None:
                raise RuntimeError(f"QEMU exited with {process.returncode}; log={log}")
            time.sleep(0.025)
        if not started or "S3BENCH_DONE" not in text or before is None or after is None:
            raise TimeoutError(f"benchmark markers missing; log={log}")
        delta_sectors = after - before
        if delta_sectors < 0:
            raise RuntimeError(f"guest sector counter decreased; log={log}")
        used = marker_value(text, "S3BENCH_DF_USED_KB")
        return {
            "valid": True,
            "idle_sectors_before": marker_value(text, "S3BENCH_IDLE_SECTORS_BEFORE"),
            "idle_sectors_after": marker_value(text, "S3BENCH_IDLE_SECTORS_AFTER"),
            "idle_delta_sectors": marker_value(text, "S3BENCH_IDLE_DELTA"),
            "sectors_written_before": before,
            "sectors_written_after": after,
            "delta_sectors": delta_sectors,
            "delta_bytes": delta_sectors * 512,
            "df_used_kib": used,
            "log": str(log),
        }
    finally:
        stop_process(process)
        disk.unlink(missing_ok=True)


def measure():
    base = Path(args.output).resolve()
    gate_attempts = []
    for attempt in range(args.retries + 1):
        work = base / f"attempt{attempt + 1}" if args.retries else base
        result = measure_attempt(work)
        gate_attempts.append({
            "attempt": attempt + 1,
            "idle_delta_sectors": result.get("idle_delta_sectors"),
            "valid": result["valid"],
            "log": result["log"],
        })
        if result["valid"]:
            result["gate_attempts"] = gate_attempts
            print(json.dumps(result, sort_keys=True))
            return
    print(json.dumps({
        "valid": False,
        "gate_attempts": gate_attempts,
    }, sort_keys=True))
    raise SystemExit(2)


def cut_test():
    work = Path(args.output).resolve()
    work.mkdir(parents=True, exist_ok=True)
    disk = work / "trial.img"
    first_log = work / "firstboot.log"
    verify_log = work / "reboot.log"
    qmp = work / "qmp.sock"
    for path in (disk, first_log, verify_log, qmp):
        path.unlink(missing_ok=True)
    prepare_disk(Path(args.image), disk)
    process = subprocess.Popen(qemu_command(disk, first_log, args.append, qmp))
    try:
        wait_for_text(first_log, "S3CUT_C_START", process, args.timeout)
        delay = random.randint(1, 10)
        time.sleep(delay)
        process.kill()
        process.wait()
        qmp.unlink(missing_ok=True)
        os.environ["QEMU_EXTRA_APPEND"] = args.verify_append
        process = subprocess.Popen(qemu_command(disk, verify_log, args.verify_append, qmp))
        text = wait_for_text(verify_log, "S3CUT_VERIFY_", process, args.timeout)
        if "S3CUT_VERIFY_PASS" not in text:
            raise RuntimeError(f"power-cut verification failed; log={verify_log}")
        print(json.dumps({
            "delay_seconds": delay,
            "status": "PASS",
            "firstboot_log": str(first_log),
            "reboot_log": str(verify_log),
        }, sort_keys=True))
    finally:
        stop_process(process)
        disk.unlink(missing_ok=True)
        qmp.unlink(missing_ok=True)


parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("measure", "cut"))
parser.add_argument("--image", required=True)
parser.add_argument("--kernel", required=True)
parser.add_argument("--dtb", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--append", default="")
parser.add_argument("--verify-append", default="")
parser.add_argument("--timeout", type=int, default=180)
parser.add_argument("--retries", type=int, default=0)
args = parser.parse_args()

try:
    measure() if args.mode == "measure" else cut_test()
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
