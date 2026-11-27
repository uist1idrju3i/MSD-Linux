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
        self.before[1] &= ~(termios.OPOST | termios.ONLCR)
        termios.tcsetattr(self.slave, termios.TCSANOW, self.before)
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
        assert termios.tcgetattr(self.slave)[1] & (termios.OPOST | termios.ONLCR) == (termios.OPOST | termios.ONLCR)
        self.output = b""
        self.transcript = b""
        self.secrets = {PIN}

    def send(self, data, secrets=()):
        self.secrets.update(secrets)
        os.write(self.master, data)

    def read_output(self):
        data = os.read(self.master, 8192)
        self.output += data
        self.transcript += data

    def until(self, marker):
        deadline = time.monotonic() + 10
        while marker not in self.output:
            assert time.monotonic() < deadline, "terminal prompt timeout"
            readable, _, _ = select.select([self.master], [], [], 0.1)
            if readable:
                self.read_output()
        result = self.output
        self.output = b""
        return result

    def finish(self):
        stdout, stderr = self.process.communicate(timeout=15)
        try:
            assert self.process.returncode == 0, stderr.decode(errors="replace")
            while select.select([self.master], [], [], 0)[0]:
                self.read_output()
            assert termios.tcgetattr(self.slave) == self.before, "termios was not restored"
            for secret in self.secrets:
                assert secret not in stdout + stderr + self.transcript, "secret leaked to captured output"
            assert b"must-not-be-used" not in stdout + stderr
            assert not re.search(rb"(?<!\r)\n", self.transcript), "bare LF on console"
            return stdout, stderr, self.output
        finally:
            os.close(self.master)
            os.close(self.slave)
            self.parent.close()


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
        assert output == b"****\r\n"
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGTSTP):
        session = Session("read")
        session.send(b"partial")
        session.process.send_signal(sig)
        stdout, _, _ = session.finish()
        assert f"line-result={-errno.EINTR} ".encode() in stdout


def escape_cases():
    sequences = [b"\x1b[A", b"\x1b[B", b"\x1b[C", b"\x1b[D", b"\x1b[H",
                 b"\x1b[F", b"\x1b[1~", b"\x1b[4~", b"\x1b[3~", b"\x1bOH",
                 b"\x1bOF", b"\x1bOA", b"\x1b[1;5D", b"\x1b[[A"]
    for sequence in sequences:
        session = Session("read")
        session.send(b"ab" + sequence + b"cd\n")
        stdout, stderr, output = session.finish()
        assert b"line-result=4 length=4" in stdout and not stderr
        assert output == b"****\r\n", sequence
    session = Session("read")
    session.send(b"ab\x1b")
    time.sleep(0.02)
    session.send(b"[3")
    time.sleep(0.02)
    session.send(b"~cd\n")
    stdout, _, _ = session.finish()
    assert b"line-result=4 length=4" in stdout
    session = Session("read")
    session.send(b"ab\x1b[3\x04")
    stdout, _, _ = session.finish()
    assert f"line-result={-errno.EINVAL} length=0".encode() in stdout


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
    session.secrets.update((recovery, recovery.lower()))
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
    session.send(key.lower() + b"\n", secrets=(key, key.lower()))
    session.until(b"Set a new PIN")
    session.send(PIN + b"\n")
    session.until(b"Enter the new PIN again:")
    session.send(PIN + b"\n")
    stdout, stderr, output = session.finish()
    assert b"result=0 mask=3 ready=1" in stdout
    assert key not in stdout + stderr + output


def lockout(delete_failure=False, echo=False):
    notice = b"PIN is no longer available. A recovery key is required."
    mode = "lockout-delete-failure" if delete_failure else "lockout"
    session = Session("lockout-echo" if echo else mode)
    for attempt in range(10):
        prompt = session.until(b"Enter PIN:")
        assert notice not in prompt and b"Enter recovery key:" not in prompt
        session.send(PIN + b"\n")
    if not delete_failure:
        prompt = session.until(b"Enter recovery key:")
        assert prompt.count(notice) == 1
        assert prompt.index(notice) < prompt.index(b"Enter recovery key:")
        session.send(b"\x03")
    stdout, stderr, output = session.finish()
    assert not stderr and PIN not in output
    if delete_failure:
        assert b"result=-5 mask=3 ready=1" in stdout
        assert notice not in output and b"Enter recovery key:" not in output
    else:
        assert b"result=-4 mask=2 ready=1" in stdout


def echo_negative_control():
    try:
        lockout(echo=True)
    except AssertionError as error:
        assert str(error) == "secret leaked to captured output"
    else:
        raise AssertionError("PIN echo was not detected in the full transcript")
    print("ok - PTY negative control: first PIN echo consumed by until is detected")


read_cases()
escape_cases()
setup()
setup(grow_reply=b"wrong\n")
setup(filesystem_reply=b"wrong!\n")
unlock()
lockout()
lockout(delete_failure=True)
echo_negative_control()
progress = Session("progress")
_, _, output = progress.finish()
assert b"1 seconds. Do not power off." in output
print("ok - PTY: ASCII, boundaries, masking, signals, termios, setup/recovery, control ordering, secret isolation")
