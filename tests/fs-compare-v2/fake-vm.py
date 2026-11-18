#!/usr/bin/env python3
"""A host-only QMP peer; never starts QEMU."""

import json
import os
import signal
import socket
import sys
import time


mode = sys.argv[1]
if mode == "hang":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
    server.bind(os.environ["QEMU_QMP_SOCKET"])
    server.listen(1)
    if mode == "cut":
        print("msd.fscmp: workload-start", flush=True)
    elif mode != "no-marker":
        print("msd.fscmp: finished", flush=True)
    print("fake-ready", flush=True)
    if mode == "early":
        sys.exit(9)
    if mode == "cut":
        while True:
            time.sleep(1)
    with server.accept()[0] as connection, connection.makefile("rwb") as stream:
        stream.write(b'{"QMP": {}}\n')
        stream.flush()
        for line in stream:
            command = json.loads(line)
            stream.write(b'{"event":"TEST_EVENT"}\n')
            reply = {"id": command["id"], "return": {}}
            if mode == "reject":
                reply = {"id": command["id"], "error": {"class": "GenericError"}}
            stream.write(json.dumps(reply).encode() + b"\n")
            stream.flush()
            if command["execute"] == "quit":
                if mode == "hang":
                    while True:
                        time.sleep(1)
                if mode == "late-error":
                    print("msd.fscmp: error=after_marker", flush=True)
                sys.exit(3 if mode == "nonzero" else 0)
