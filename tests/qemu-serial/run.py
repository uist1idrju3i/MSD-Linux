#!/usr/bin/env python3
"""Privacy controls independent of the serial detector's format list."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "serial_session", ROOT / "board/cardputerzero/qemu/serial-session.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
KEY = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
DISPLAY = b"ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567"
NEGATIVES = (b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
             b"ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567",
             b"ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ23-4567")


class CaptureTest(unittest.TestCase):
    def capture(self, fresh=True):
        credentials = M.Credentials()
        credentials.pin = b"private-test-pin-9284"
        return M.Capture(credentials, fresh)

    def initial(self, capture):
        for byte in M.NOTICE + DISPLAY + b"\r\n":
            capture.feed("serial", bytes([byte]))
        self.assertEqual(capture.credentials.recovery, KEY)

    def test_empty_and_one_display_split_at_every_byte(self):
        capture = self.capture()
        self.assertIn(b"secret leakage check passed", capture.render())
        self.initial(capture)
        self.assertIn(b"[recovery display removed]", capture.render())
        for form in NEGATIVES:
            self.assertNotIn(form, capture.render())

    def test_pin_echo_split_everywhere_on_all_channels(self):
        for channel in ("serial", "stdout", "stderr"):
            for split in range(1, 21):
                capture = self.capture()
                value = capture.credentials.pin
                capture.feed(channel, value[:split])
                with self.assertRaises(M.PrivacyError):
                    capture.feed(channel, value[split:])
                self.assertNotIn(value, capture.render())
                self.assertIn(b"transcript withheld", capture.render())

    def test_repeated_display_and_each_fixed_format_on_each_channel(self):
        for form in NEGATIVES:
            for channel in ("serial", "stdout", "stderr"):
                for split in range(1, len(form)):
                    capture = self.capture()
                    self.initial(capture)
                    capture.feed(channel, form[:split])
                    with self.assertRaises(M.PrivacyError):
                        capture.feed(channel, form[split:])
                    self.assertNotIn(form, capture.render())

    def test_ready_has_no_authorized_display(self):
        capture = self.capture(False)
        capture.credentials.recovery = KEY
        with self.assertRaises(M.PrivacyError):
            capture.feed("serial", M.NOTICE + DISPLAY + b"\n")
        self.assertNotIn(DISPLAY, capture.render())

    def test_second_notice_even_with_another_key_and_wrong_channel(self):
        for channel in ("serial", "stdout", "stderr"):
            capture = self.capture()
            self.initial(capture)
            with self.assertRaises(M.PrivacyError):
                capture.feed(channel, M.NOTICE + b"ZZZZ YYYY XXXX WWWW VVVV UUUU TTTT SSSS\n")
            self.assertIn(b"transcript withheld", capture.render())
        for channel in ("stdout", "stderr"):
            capture = self.capture()
            with self.assertRaises(M.PrivacyError):
                capture.feed(channel, M.NOTICE + DISPLAY + b"\n")
            self.assertNotIn(DISPLAY, capture.render())

    def test_preceding_stdout_disclosure_and_incomplete_display(self):
        capture = self.capture()
        capture.feed("stderr", NEGATIVES[2])
        with self.assertRaises(M.PrivacyError):
            self.initial(capture)
        self.assertNotIn(NEGATIVES[2], capture.render())
        capture = self.capture()
        capture.feed("serial", M.NOTICE + DISPLAY[:13])
        self.assertIn(b"transcript withheld", capture.render())

    def test_exception_message_is_not_a_saved_transcript(self):
        capture = self.capture()
        with self.assertRaises(M.PrivacyError) as result:
            capture.feed("stderr", capture.credentials.pin)
        self.assertNotIn(capture.credentials.pin.decode(), str(result.exception))
        self.assertNotIn(capture.credentials.pin, capture.render())


if __name__ == "__main__":
    unittest.main()
