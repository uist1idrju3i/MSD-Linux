#!/usr/bin/env python3
"""A QEMU CLI and QMP peer for boot-harness regression tests."""

import json
import os
from pathlib import Path
import signal
import socket
import sys
import time


if "--version" in sys.argv:
    print("QEMU emulator version fake")
    sys.exit(0)

mode = os.environ.get("FAKE_VM_MODE", "normal")
if mode == "inspect":
    print(json.dumps(sys.argv[1:]))
    sys.exit(0)

if mode in ("hang", "timeout", "interrupt"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
address = sys.argv[sys.argv.index("-qmp") + 1].split(",")[0].removeprefix("unix:")
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
if mode not in ("no-server", "exit-before", "exit-after-marker"):
    server.bind(address)
    if mode != "refused":
        server.listen(1)
state = dict(pid=os.getpid(), socket=address)
if mode == "cryptsetup":
    image = Path(sys.argv[sys.argv.index("-drive") + 1].split(",")[0].removeprefix("file="))
    state["image"] = str(image)
    image.write_bytes(b"guest write")
Path(os.environ["FAKE_VM_STATE"]).write_text(json.dumps(state))

if mode == "exit-before":
    sys.exit(int(os.environ.get("FAKE_VM_EXIT", "0")))
serial = None
if os.environ.get("QEMU_SERIAL_SOCKET"):
    serial_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    serial_server.bind(os.environ["QEMU_SERIAL_SOCKET"])
    serial_server.listen(1)
    serial, _ = serial_server.accept()
    terminal = serial.makefile("rwb", buffering=0)

    def emit(text):
        terminal.write(text.encode())

    def line():
        return terminal.readline().rstrip(b"\n")

    disk = Path(sys.argv[sys.argv.index("-drive") + 1].split(",")[0].removeprefix("file="))
    with disk.open("rb") as stream:
        fresh = stream.read(1) != b"r"
    if mode not in ("timeout", "interrupt", "unauthenticated"):
        if fresh:
            emit("Set a new PIN (4-64 printable ASCII characters):\n")
            pin = line()
            emit("Enter the new PIN again:\n")
            assert line() == pin
            assert pin.decode() not in json.dumps([sys.argv, dict(os.environ)])
            emit("Write down this recovery key on paper and keep it outside the SD card.\n")
            emit("ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567\n")
            emit("Enter the recovery key to check your copy, or an empty line to skip:\n")
            assert line() == b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
            with disk.open("r+b") as stream:
                stream.write(b"ready")
        else:
            emit("Enter PIN:\n")
            pin = line()
            assert pin.decode() not in json.dumps([sys.argv, dict(os.environ)])
        if mode == "pin-echo":
            emit(pin.decode() + "\n")
        if mode == "recovery-echo":
            emit("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567\n")
        if mode == "recovery-stdout":
            print("ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ23-4567", flush=True)
        if mode == "recovery-stderr":
            print("ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567", file=sys.stderr, flush=True)
    def output(text, **_kwargs):
        emit(text + "\n")
else:
    output = print
if mode not in ("timeout", "interrupt"):
    output("MSD/Linux ready", flush=True)
    if mode != "no-login":
        output("msd login:", flush=True)
    if mode != "no-mount":
        output("msd-data: /data btrfs noatime,nodev,nosuid,compress=zstd:3", flush=True)
    if mode == "bad-mount":
        output("msd-data: /data btrfs nodev,nosuid", flush=True)
    append = sys.argv[sys.argv.index("-append") + 1]
    for word in append.split():
        if word.startswith("msd.module-test=") and mode != "no-modules":
            for module in filter(None, word.split("=", 1)[1].split(",")):
                output(f"msd-module-check: {module} loaded via modprobe and listed by lsmod",
                      flush=True)
if mode == "exit-after-marker":
    sys.exit(int(os.environ.get("FAKE_VM_EXIT", "0")))
if mode in ("no-server", "refused", "timeout", "interrupt", "no-login"):
    while True:
        time.sleep(1)

if serial is not None and not fresh:
    assert line() == b"root"
    emit("# ")
    assert line() == b"stty -echo"
    emit("# ")
    assert b"btrfs inspect-internal" in line()
    emit("MSD_DATA_INSPECT_BEGIN\ncsum_type\t1 (xxhash64)\nData,DUP:\nMetadata,DUP:\n")
    emit("/dev/mapper/msd-data /data btrfs rw,noatime,nodev,nosuid,compress=zstd:3 0 0\n")
    emit("MSD_DATA_INSPECT_OK\r\n# ")

if mode == "cryptsetup":
    for _ in range(2):
        sys.stdin.readline()
        print("# ", end="", flush=True)
    sys.stdin.readline()
    version = os.environ.get("FAKE_CRYPTSETUP_VERSION", "2.8.9")
    print(f"\ncryptsetup {version}\nCRYPTSETUP_STATUS=0\n# ", end="", flush=True)

connection, _ = server.accept()
with connection, connection.makefile("rwb") as stream:
    stream.write(b'{"QMP": {}}\n')
    stream.flush()
    for raw in stream:
        request = json.loads(raw)
        command = request["execute"]
        if mode == "exit-before-quit" and command == "qmp_capabilities":
            sys.exit(int(os.environ.get("FAKE_VM_EXIT", "0")))
        if mode == "silent":
            time.sleep(60)
        if mode == "events":
            stream.write(b'{"event": "RESET", "data": {}}\n')
        response = {"return": {}, "id": request["id"]}
        if mode == "reject" and command == "quit":
            response = {"error": {"class": "GenericError", "desc": "no"}, "id": request["id"]}
        if mode == "secret-exception":
            response = {"error": {"class": "GenericError",
                                 "desc": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"}, "id": request["id"]}
        stream.write(json.dumps(response).encode() + b"\n")
        stream.flush()
        if command == "quit":
            if mode in ("hang", "reject"):
                while True:
                    time.sleep(1)
            if mode == "late-panic":
                output("[    9.000000] Kernel panic - not syncing: fixture", flush=True)
            if mode == "signal":
                os.kill(os.getpid(), signal.SIGKILL)
            sys.exit(7 if mode == "nonzero" else 0)
