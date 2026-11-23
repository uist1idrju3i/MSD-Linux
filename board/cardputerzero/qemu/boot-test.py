#!/usr/bin/env python3
"""Require readiness, acknowledged QMP quit, clean exit and a valid boot log."""

import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent


def helpers():
    path = HERE.parent / "tools/bench/fs-compare-v2/supervisor.py"
    spec = importlib.util.spec_from_file_location("qemu_supervision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def supervise(log_path, socket_path, command, timeout, grace, environment):
    shared = helpers()
    result = dict(qmp_quit=False, returncode=None, reaped=False, fallback=[], error=None)
    process = None
    status = 1
    started = time.monotonic()

    def interrupt(number, _frame):
        raise InterruptedError(f"signal {signal.Signals(number).name}")

    signals = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    handlers = {number: signal.signal(number, interrupt) for number in signals}
    try:
        with log_path.open("wb") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=dict(environment, QEMU_QMP_SOCKET=str(socket_path)),
                                       start_new_session=True)
            result["pid"] = process.pid
            deadline = time.monotonic() + timeout
            while True:
                if process.poll() is not None:
                    raise ValueError("QEMU exited before the harness requested quit")
                if time.monotonic() >= deadline:
                    status = 124
                    raise TimeoutError("QEMU did not show the boot marker and login prompt "
                                       f"within {timeout:g} seconds")
                text = log_path.read_text(errors="replace")
                if "MSD/Linux ready" in text and re.search("login:", text, re.I):
                    if process.poll() is not None:
                        raise ValueError("QEMU exited after the marker but before quit")
                    shared.qmp_quit(socket_path, grace)
                    result["qmp_quit"] = True
                    if shared.reap(process, grace) is None:
                        raise TimeoutError("QEMU did not exit after QMP quit")
                    if process.returncode != 0:
                        raise ValueError(f"QEMU exited with status {process.returncode}")
                    status = 0
                    break
                time.sleep(0.05)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
    finally:
        for number in signals:
            signal.signal(number, signal.SIG_IGN)
        try:
            if process is not None:
                for number in (signal.SIGTERM, signal.SIGKILL):
                    if process.poll() is None:
                        result["fallback"].append(signal.Signals(number).name)
                        shared.signal_group(process, number)
                        shared.reap(process, grace)
                result["returncode"] = process.poll()
                result["reaped"] = result["returncode"] is not None
        finally:
            for number, handler in handlers.items():
                signal.signal(number, handler)
    log_path.with_suffix(".process.json").write_text(json.dumps(result, indent=2) + "\n")
    print("QEMU process result: " + json.dumps(result), flush=True)
    if (result["fallback"] or not result["reaped"] or not result["qmp_quit"]
            or result["returncode"] != 0 or result["error"] is not None):
        status = 124 if status == 124 else 1
    return status, int(time.monotonic() - started)


def check_boot_log(log_path, root_device, modules):
    if subprocess.run([str(HERE / "check-serial-log.sh"), str(log_path)]).returncode:
        print("QEMU serial log contains boot error patterns.", file=sys.stderr)
        return False
    text = log_path.read_text(errors="replace")
    mount_lines = [line for line in text.splitlines() if "msd-data: /data " in line]
    if not mount_lines:
        print("QEMU serial log is missing the /data mount options.", file=sys.stderr)
        return False
    for option in ("data=ordered", "nodev", "nosuid"):
        if option not in mount_lines[-1]:
            print(f"QEMU /data mount options are missing {option}: {mount_lines[-1]}",
                  file=sys.stderr)
            return False
    for module in filter(None, modules.split(",")):
        marker = f"msd-module-check: {module} loaded via modprobe and listed by lsmod"
        if marker not in text:
            print(f"QEMU serial log is missing the {module} module-load check.", file=sys.stderr)
            return False
    print(f"QEMU boot marker and login prompt found for root {root_device}.")
    return True


def main():
    environment = dict(os.environ)
    root_device = environment.get("ROOT_DEVICE") or "/dev/mmcblk0p5"
    modules = environment.get("QEMU_MODULE_TEST", "usbnet,bcm2835-unicam,imx219")
    if modules:
        environment["QEMU_EXTRA_APPEND"] = (
            environment.get("QEMU_EXTRA_APPEND", "") + f" msd.module-test={modules}").strip()
    try:
        timeout = float(environment.get("QEMU_BOOT_TIMEOUT") or "300")
        grace = float(environment.get("QEMU_STOP_TIMEOUT") or "5")
        if not 0 < timeout < float("inf") or not 0 < grace <= 10:
            raise ValueError("timeouts must be positive; QEMU_STOP_TIMEOUT must be at most 10")
    except ValueError as error:
        print(f"QEMU boot test: {error}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="qemu-boot-") as temporary:
        directory = Path(environment.get("QEMU_LOG_DIR") or temporary)
        directory.mkdir(parents=True, exist_ok=True)
        log_path = directory / f"serial-{Path(root_device).name}.log"
        status, elapsed = supervise(log_path, Path(temporary) / "qmp.sock",
                                    [str(HERE / "run-qemu.sh"), *sys.argv[1:]],
                                    timeout, grace, environment)
        if status:
            print(log_path.read_text(errors="replace"), end="")
            return status
        print(f"QEMU reached ready after {elapsed} seconds.")
        return 0 if check_boot_log(log_path, root_device, modules) else 1


if __name__ == "__main__":
    sys.exit(main())
