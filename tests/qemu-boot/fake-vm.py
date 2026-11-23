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
Path(os.environ["FAKE_VM_STATE"]).write_text(json.dumps(dict(pid=os.getpid(), socket=address)))

if mode == "exit-before":
    sys.exit(int(os.environ.get("FAKE_VM_EXIT", "0")))
if mode not in ("timeout", "interrupt"):
    print("MSD/Linux ready", flush=True)
    if mode != "no-login":
        print("msd login:", flush=True)
    if mode != "no-mount":
        print("msd-data: /data rw,data=ordered,nodev,nosuid", flush=True)
    if mode == "bad-mount":
        print("msd-data: /data rw,data=writeback,nodev,nosuid", flush=True)
    append = sys.argv[sys.argv.index("-append") + 1]
    for word in append.split():
        if word.startswith("msd.module-test=") and mode != "no-modules":
            for module in filter(None, word.split("=", 1)[1].split(",")):
                print(f"msd-module-check: {module} loaded via modprobe and listed by lsmod",
                      flush=True)
if mode == "exit-after-marker":
    sys.exit(int(os.environ.get("FAKE_VM_EXIT", "0")))
if mode in ("no-server", "refused", "timeout", "interrupt", "no-login"):
    while True:
        time.sleep(1)

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
        stream.write(json.dumps(response).encode() + b"\n")
        stream.flush()
        if command == "quit":
            if mode in ("hang", "reject"):
                while True:
                    time.sleep(1)
            if mode == "late-panic":
                print("[    9.000000] Kernel panic - not syncing: fixture", flush=True)
            if mode == "signal":
                os.kill(os.getpid(), signal.SIGKILL)
            sys.exit(7 if mode == "nonzero" else 0)
