#!/usr/bin/env python3
"""Exercise the actual terminal and control-channel implementation using PTYs."""

import errno
import os
from pathlib import Path
import pty
import re
import select
import signal
import socket
import subprocess
import sys
import termios
import time


DRIVER = Path(sys.argv[1])
PIN = b"Private PIN 92!"


class Session:
    def __init__(self, mode):
        self.master, self.slave = pty.openpty()
        self.before = termios.tcgetattr(self.slave)
        self.parent, child = socket.socketpair()
        self.parent.settimeout(10)
        self.args = [str(DRIVER), mode, str(self.slave), str(child.fileno())]
        assert not any(PIN.decode() in arg for arg in self.args)
        self.process = subprocess.Popen(
            self.args, pass_fds=(self.slave, child.fileno()),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "MSD_TEST_SECRET": "must-not-be-used"},
        )
        child.close()
        assert self.process.stdout.readline() == b"READY\n"
        assert PIN not in Path(f"/proc/{self.process.pid}/cmdline").read_bytes()
        assert not termios.tcgetattr(self.slave)[3] & termios.ECHO
        self.output = b""

    def send(self, data):
        os.write(self.master, data)

    def until(self, marker):
        deadline = time.monotonic() + 10
        while marker not in self.output:
            assert time.monotonic() < deadline, "terminal prompt timeout"
            readable, _, _ = select.select([self.master], [], [], 0.1)
            if readable:
                self.output += os.read(self.master, 8192)
        result = self.output
        self.output = b""
        return result

    def finish(self):
        stdout, stderr = self.process.communicate(timeout=15)
        assert self.process.returncode == 0, stderr.decode(errors="replace")
        while select.select([self.master], [], [], 0)[0]:
            self.output += os.read(self.master, 8192)
        assert termios.tcgetattr(self.slave) == self.before, "termios was not restored"
        assert PIN not in stdout + stderr + self.output
        assert b"must-not-be-used" not in stdout + stderr
        os.close(self.master)
        os.close(self.slave)
        self.parent.close()
        return stdout, stderr, self.output


def read_cases():
    cases = [
        (b"\n", 0), (b"123\n", 3), (b"1234\n", 4),
        (b"x" * 64 + b"\n", 64), (b"x" * 65 + b"\n", -errno.EINVAL),
        (b"ab\x00cd\n", -errno.EINVAL), (b"ab\xffcd\n", -errno.EINVAL),
        (b"    \n", 4), (b" a b \n", 5), (b"abc\x7fd\n", 3),
        (b"abc\x08d\n", 3), (b"\x04", -errno.ENODATA),
        (b"\x03", -errno.EINTR), (b"\x1b", -errno.EINTR),
    ]
    for data, expected in cases:
        session = Session("read")
        session.send(data)
        stdout, stderr, _ = session.finish()
        assert f"line-result={expected} ".encode() in stdout
        assert not stderr
    for value in range(0x20, 0x7f):
        session = Session("read")
        session.send(bytes([value]) * 4 + b"\n")
        stdout, _, output = session.finish()
        assert b"line-result=4 length=4" in stdout
        assert output == b"****\n"
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGTSTP):
        session = Session("read")
        session.send(b"partial")
        session.process.send_signal(sig)
        stdout, _, _ = session.finish()
        assert f"line-result={-errno.EINTR} ".encode() in stdout


def setup(grow_reply=b"grown\n", filesystem_reply=b"synced\n"):
    session = Session("prepare")
    session.until(b"Set a new PIN")
    session.send(PIN + b"\n")
    session.until(b"Enter the new PIN again:")
    session.send(PIN + b"\n")
    display = session.until(b"Enter the recovery key to check your copy")
    match = re.search(rb"[A-Z2-7]{4}(?: [A-Z2-7]{4}){7}", display)
    assert match, "recovery key grouping missing"
    recovery = match.group().replace(b" ", b"")
    assert PIN not in display
    session.send(b"\n")
    session.until(b"Skip verification? Type yes to confirm:")
    session.send(b"yes\n")
    assert session.parent.recv(64) == b"grow\n"
    session.parent.sendall(grow_reply)
    if grow_reply == b"grown\n":
        assert session.parent.recv(64) == b"filesystem\n"
        session.parent.sendall(filesystem_reply)
    stdout, stderr, output = session.finish()
    assert recovery not in stdout + stderr + output
    if grow_reply == b"grown\n" and filesystem_reply == b"synced\n":
        assert b"result=0 mask=3 ready=1" in stdout
    else:
        assert b"ready=0" in stdout and b"result=0 " not in stdout


def unlock():
    session = Session("unlock")
    prompt = session.until(b"Enter PIN:")
    assert b"Forgot PIN? Press Enter on an empty line to use the recovery key." in prompt
    session.send(PIN + b"\n")
    stdout, stderr, output = session.finish()
    assert PIN not in output and not stderr
    assert b"result=0 mask=3 ready=1" in stdout
    session = Session("unlock")
    session.until(b"Enter PIN:")
    session.send(b"\n")
    session.until(b"Use the recovery key?")
    session.send(b"yes\n")
    session.until(b"Enter recovery key:")
    key = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    session.send(key.lower() + b"\n")
    session.until(b"Set a new PIN")
    session.send(PIN + b"\n")
    session.until(b"Enter the new PIN again:")
    session.send(PIN + b"\n")
    stdout, stderr, output = session.finish()
    assert b"result=0 mask=3 ready=1" in stdout
    assert key not in stdout + stderr + output


read_cases()
setup()
setup(grow_reply=b"wrong\n")
setup(filesystem_reply=b"wrong!\n")
unlock()
progress = Session("progress")
_, _, output = progress.finish()
assert b"1 seconds. Do not power off." in output
print("ok - PTY: ASCII, boundaries, masking, signals, termios, setup/recovery, control ordering, secret isolation")
