#!/usr/bin/env python3
"""Require readiness, acknowledged QMP quit, clean exit and a valid boot log."""

import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
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


def serial_helpers():
    spec = importlib.util.spec_from_file_location("serial_session", HERE / "serial-session.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_data(session, timeout):
    session.send(b"root")
    session.receive(b"# ", timeout)
    session.send(b"stty -echo")
    session.receive(b"# ", timeout)
    session.send(b"printf '\\nMSD_DATA_INSPECT_BEGIN\\n'; "
                 b"/usr/sbin/msd-data-boot health && "
                 b"btrfs inspect-internal dump-super /dev/mapper/msd-data && "
                 b"btrfs filesystem usage -b /data && cat /proc/mounts && "
                 b"printf '\\nMSD_DATA_INSPECT_OK\\n'")
    session.receive(b"MSD_DATA_INSPECT_OK\r\n", timeout)
    text = session.text.decode(errors="replace")
    text = text[text.rindex("MSD_DATA_INSPECT_BEGIN"):]
    for pattern in (r"csum_type\s+1 \(xxhash64\)", r"Data,DUP:", r"Metadata,DUP:",
                    r"/dev/\S+ /data btrfs [^\r\n]*"):
        if not re.search(pattern, text):
            raise ValueError("Btrfs inspection failed")
    mount = re.search(r"/dev/\S+ /data btrfs (\S+)", text)[1].split(",")
    if not {"noatime", "nodev", "nosuid", "compress=zstd:3"} <= set(mount):
        raise ValueError("Btrfs mount options failed")


def supervise(log_path, socket_path, command, timeout, grace, environment,
              credentials=None, fresh=True, gpio=False):
    shared = helpers()
    serial = serial_helpers()
    credentials = credentials or serial.Credentials()
    result = dict(qmp_quit=False, returncode=None, reaped=False, fallback=[], error=None)
    process = None
    session = None
    status = 1
    started = time.monotonic()

    def interrupt(number, _frame):
        raise ValueError("harness interrupted")

    signals = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    handlers = {number: signal.signal(number, interrupt) for number in signals}
    try:
        serial_path = socket_path.with_name("serial.sock")
        for path in (serial_path, socket_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       env=dict(environment, QEMU_QMP_SOCKET=str(socket_path),
                                                QEMU_SERIAL_SOCKET=str(serial_path)),
                                       start_new_session=True)
        session = serial.Session(process, serial_path, credentials, fresh)
        result["pid"] = process.pid
        try:
            session.receive(b"login:", timeout)
        except TimeoutError:
            status = 124
            raise
        if b"MSD/Linux ready" not in session.text:
            raise ValueError("login before readiness")
        if session.auth != (3 if fresh else 1):
            raise ValueError("readiness without authentication")
        if not fresh:
            inspect_data(session, timeout)
        if gpio:
            cursor = session.cursor
            subprocess.run([sys.executable, str(HERE / "qmp-set-gpio.py"),
                            str(socket_path),
                            environment.get("QEMU_GPIO_PATH", "/machine/soc/peripherals/gpio"),
                            "pin6", "false"], check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=grace + 2)
            session.receive(b"msd-powerfail: power-fail event received", 15)
            session.cursor = cursor
            session.receive(b"SysRq U: emergency remount filesystems readonly", 15)
        if process.poll() is not None:
            raise ValueError("QEMU exited before quit")
        shared.qmp_quit(socket_path, grace)
        result["qmp_quit"] = True
        if shared.reap(process, grace) is None:
            raise TimeoutError("QEMU did not exit after QMP quit")
        if process.returncode != 0:
            raise ValueError("QEMU exited with nonzero status")
        status = 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["error"] = type(error).__name__
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
            if session is not None:
                if result["error"] == "PrivacyError":
                    session.capture.failed = True
                try:
                    session.drain()
                    session.save(log_path)
                except (OSError, ValueError) as error:
                    result["error"] = type(error).__name__
                    log_path.write_bytes(session.capture.render())
                finally:
                    session.close()
            elif not log_path.exists():
                log_path.write_text("harness: QEMU did not start\n")
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
    for option in ("btrfs", "noatime", "nodev", "nosuid", "compress=zstd:3"):
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
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    environment = dict(os.environ)
    for key in ("QEMU_DRIVE_FILE", "QEMU_DRIVE_FORMAT"):
        environment.pop(key, None)
    arguments = sys.argv[1:]
    gpio = "--gpio-smoke" in arguments
    if gpio:
        arguments.remove("--gpio-smoke")
    root_device = environment.get("ROOT_DEVICE") or "/dev/mmcblk0p5"
    modules = environment.get("QEMU_MODULE_TEST", "usbnet,bcm2835-unicam,imx219")
    if modules:
        environment["QEMU_EXTRA_APPEND"] = (
            environment.get("QEMU_EXTRA_APPEND", "") + f" msd.module-test={modules}").strip()
    try:
        timeout = float(environment.get("QEMU_BOOT_TIMEOUT") or "600")
        grace = float(environment.get("QEMU_STOP_TIMEOUT") or "5")
        if not 0 < timeout < float("inf") or not 0 < grace <= 10:
            raise ValueError("timeouts must be positive; QEMU_STOP_TIMEOUT must be at most 10")
    except ValueError as error:
        print(f"QEMU boot test: {error}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="qemu-boot-") as temporary:
        directory = Path(environment.get("QEMU_LOG_DIR") or temporary)
        directory.mkdir(parents=True, exist_ok=True)
        images = Path(environment.get("OUTPUT_DIR") or HERE.parents[2] / "output") / "images"
        source = Path(arguments[0]) if arguments else images / "sdcard.img"
        disk = Path(temporary) / "disk.img"
        shutil.copyfile(source, disk)
        size = disk.stat().st_size
        with disk.open("r+b") as stream:
            stream.truncate(1 << max(0, size - 1).bit_length())
        environment["QEMU_COPY_IMAGE"] = "0"
        credentials = serial_helpers().Credentials()
        for fresh in (True, False):
            suffix = "-fresh" if fresh else ""
            log_path = directory / f"serial-{Path(root_device).name}{suffix}.log"
            status, elapsed = supervise(log_path, Path(temporary) / "qmp.sock",
                                        [str(HERE / "run-qemu.sh"), str(disk)],
                                        timeout, grace, environment, credentials, fresh,
                                        gpio and not fresh)
            if status:
                print(log_path.read_text(errors="replace"), end="")
                return status
            print(f"QEMU {'fresh' if fresh else 'ready restart'} reached ready after {elapsed} seconds.")
            if not check_boot_log(log_path, root_device, modules):
                return 1
        if gpio:
            print("PASS: authenticated GPIO6 event and emergency remount")
        return 0


if __name__ == "__main__":
    sys.exit(main())
