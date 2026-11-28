#!/usr/bin/env python3
"""RAM-only credentials and fail-closed serial capture for QEMU tests."""

import os
import re
import secrets
import selectors
import socket
import time


NOTICE = b"Write down this recovery key on paper and keep it outside the SD card.\n"
DISPLAY = re.compile(rb"([A-Z2-7]{4}(?: [A-Z2-7]{4}){7})\r?\n")


class PrivacyError(ValueError):
    pass


class Credentials:
    def __init__(self):
        self.pin = secrets.token_hex(12).encode()
        self.recovery = None


class Capture:
    def __init__(self, credentials, fresh):
        self.credentials = credentials
        self.fresh = fresh
        self.channels = {name: bytearray() for name in ("serial", "stdout", "stderr")}
        self.display = None
        self.failed = False

    def feed(self, channel, data):
        if len(self.channels[channel]) + len(data) > 8 * 1024 * 1024:
            self.failed = True
            raise PrivacyError("capture limit exceeded")
        self.channels[channel].extend(data)
        self.check()

    def check(self, final=False):
        for channel, data in self.channels.items():
            count = bytes(data).replace(b"\r\n", b"\n").count(NOTICE)
            if count and (channel != "serial" or not self.fresh or count != 1):
                self.failed = True
                raise PrivacyError("unexpected recovery display notice")
        serial = bytes(self.channels["serial"])
        normalized = serial.replace(b"\r\n", b"\n")
        if self.fresh and self.display is None and NOTICE in normalized:
            start = serial.index(b"Write down this recovery key")
            start = serial.index(b"\n", start) + 1
            match = DISPLAY.match(serial, start)
            if match:
                if self.credentials.recovery is not None:
                    self.failed = True
                    raise PrivacyError("unexpected recovery display")
                self.credentials.recovery = match[1].replace(b" ", b"")
                self.display = match.span(1)
            elif final:
                self.failed = True
                raise PrivacyError("incomplete recovery display")
        for channel, data in self.channels.items():
            text = bytes(data)
            if channel == "serial" and self.display is not None:
                a, b = self.display
                text = text[:a] + b"[recovery display removed]" + text[b:]
            if self.credentials.pin in text:
                self.failed = True
                raise PrivacyError("PIN echo detected")
            key = self.credentials.recovery
            if key:
                groups = [key[i:i + 4] for i in range(0, 32, 4)]
                for form in (key, b" ".join(groups), b"-".join(groups)):
                    if form.lower() in text.lower():
                        self.failed = True
                        raise PrivacyError("recovery disclosure detected")
                if re.search(rb"\s+".join(groups), text, re.I):
                    self.failed = True
                    raise PrivacyError("recovery disclosure detected")

    def render(self):
        try:
            self.check(final=True)
        except PrivacyError:
            pass
        if self.failed:
            return b"harness: secret disclosure or incomplete capture; transcript withheld\n"
        output = bytearray()
        for channel, data in self.channels.items():
            text = bytes(data)
            if channel == "serial" and self.display is not None:
                a, b = self.display
                text = text[:a] + b"[recovery display removed]" + text[b:]
            output.extend(b"--- " + channel.encode() + b" ---\n" + text + b"\n")
        output.extend(b"harness: secret leakage check passed\n")
        return bytes(output)


class Session:
    def __init__(self, process, address, credentials, fresh):
        self.process = process
        self.address = address
        self.capture = Capture(credentials, fresh)
        self.selector = selectors.DefaultSelector()
        self.connection = None
        self.cursor = 0
        self.auth = 0
        self.fresh = fresh
        self.selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(process.stderr, selectors.EVENT_READ, "stderr")

    @property
    def text(self):
        return bytes(self.capture.channels["serial"])

    def send(self, value):
        if self.connection is None:
            raise ValueError("serial not connected")
        self.connection.sendall(value + b"\n")

    def authenticate(self):
        prompts = ((b"Set a new PIN (4-64 printable ASCII characters):",
                    b"Enter the new PIN again:",
                    b"Enter the recovery key to check your copy, or an empty line to skip:")
                   if self.fresh else (b"Enter PIN:",))
        while self.auth < len(prompts) and prompts[self.auth] in self.text:
            value = (self.capture.credentials.recovery if self.fresh and self.auth == 2
                     else self.capture.credentials.pin)
            if value is None:
                raise PrivacyError("missing recovery display")
            self.send(value)
            self.auth += 1

    def pump(self, timeout=0.05):
        if self.connection is None and self.address.exists():
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.connect(str(self.address))
            except (ConnectionRefusedError, FileNotFoundError):
                connection.close()
            else:
                self.connection = connection
                self.selector.register(connection, selectors.EVENT_READ, "serial")
        for key, _ in self.selector.select(timeout):
            chunk = os.read(key.fileobj.fileno(), 65536)
            if not chunk:
                self.selector.unregister(key.fileobj)
                continue
            self.capture.feed(key.data, chunk)
        self.authenticate()

    def receive(self, marker, timeout):
        deadline = time.monotonic() + timeout
        while marker not in self.text[self.cursor:]:
            if time.monotonic() >= deadline:
                raise TimeoutError("guest response deadline exceeded")
            self.pump()
            if self.process.poll() is not None:
                raise ValueError("QEMU exited before guest response")
        self.cursor = self.text.index(marker, self.cursor) + len(marker)

    def drain(self):
        while self.selector.select(0):
            self.pump(0)

    def save(self, path):
        path.write_bytes(self.capture.render())
        if self.capture.failed:
            raise PrivacyError("transcript withheld")

    def close(self):
        self.selector.close()
        if self.connection is not None:
            self.connection.close()
        self.process.stdout.close()
        self.process.stderr.close()
