#!/usr/bin/env python3
"""Check the target cryptsetup CLI on a copied QEMU image."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[4]


def check_version(text, expected):
    versions = re.findall(r"^cryptsetup (\d+\.\d+\.\d+)(?: flags: [^\r\n]*)?\r?$", text, re.M)
    statuses = re.findall(r"^CRYPTSETUP_STATUS=(\d+)\r?$", text, re.M)
    if versions != [expected] or statuses != ["0"]:
        raise ValueError("missing, repeated, wrong or failed target cryptsetup version")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("expected")
    args = parser.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.expected):
        parser.error("expected must be a release version")
    args.evidence.mkdir()
    spec = importlib.util.spec_from_file_location(
        "supervisor", Path(__file__).with_name("fs-compare-v2") / "supervisor.py")
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    state = dict(qmp_quit=False, returncode=None, fallback=[], error=None)
    process = None
    selector = selectors.DefaultSelector()

    def interrupt(number, _frame):
        raise InterruptedError(signal.Signals(number).name)

    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, interrupt)
    try:
        with tempfile.TemporaryDirectory(prefix="crypt-version-") as temporary:
            socket = Path(temporary) / "qmp.sock"
            environment = dict(os.environ, OUTPUT_DIR=str(args.output.resolve()),
                               ROOT_DEVICE="/dev/mmcblk0p5", ROOT_FSTYPE="squashfs",
                               QEMU_COPY_IMAGE="1", QEMU_QMP_SOCKET=str(socket))
            for name in ("QEMU_DRIVE_FILE", "QEMU_DRIVE_FORMAT"):
                environment.pop(name, None)
            with (args.evidence / "serial.log").open("xb") as log:
                process = subprocess.Popen(
                    [str(ROOT / "board/cardputerzero/qemu/run-qemu.sh")],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    start_new_session=True, env=environment)
                selector.register(process.stdout, selectors.EVENT_READ)
                pending = bytearray()

                def receive(marker):
                    deadline = time.monotonic() + 300
                    while marker not in pending:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("waiting for " + repr(marker))
                        if selector.select(timeout=1):
                            chunk = os.read(process.stdout.fileno(), 65536)
                            if not chunk:
                                raise ValueError("QEMU exited before version check")
                            log.write(chunk)
                            log.flush()
                            pending.extend(chunk)
                    del pending[:pending.index(marker) + len(marker)]

                def send(text):
                    process.stdin.write(text.encode())
                    process.stdin.flush()

                receive(b"login:")
                send("root\n")
                receive(b"# ")
                send("stty -echo\n")
                receive(b"# ")
                send("printf '\\n'; cryptsetup --version; rc=$?; printf '\\nCRYPTSETUP_STATUS=%s\\n' \"$rc\"\n")
                receive(b"CRYPTSETUP_STATUS=")
                receive(b"# ")
                check_version((args.evidence / "serial.log").read_text(errors="replace"), args.expected)
                supervisor.qmp_quit(socket, 10)
                state["qmp_quit"] = True
                if supervisor.reap(process, 10) != 0:
                    raise ValueError("QEMU did not exit cleanly")
    except Exception as error:
        state["error"] = repr(error)
        raise
    finally:
        for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            signal.signal(number, signal.SIG_IGN)
        if process is not None:
            for number in (signal.SIGTERM, signal.SIGKILL):
                if process.poll() is None:
                    state["fallback"].append(signal.Signals(number).name)
                    supervisor.signal_group(process, number)
                    supervisor.reap(process, 10)
            state["returncode"] = process.poll()
            process.stdin.close()
            process.stdout.close()
        selector.close()
        (args.evidence / "process.json").write_text(json.dumps(state, indent=2) + "\n")
    print(f"ok - QEMU target cryptsetup {args.expected}; status=0; QMP quit; exit=0")


if __name__ == "__main__":
    main()
