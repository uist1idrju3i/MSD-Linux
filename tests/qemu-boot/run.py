#!/usr/bin/env python3
"""Exercise the actual boot shell entry points with a fake QEMU executable."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
QEMU = ROOT / "board/cardputerzero/qemu"


class BootTest(unittest.TestCase):
    def exercise(self, mode="normal", entry="test-boot.sh", interrupt=False,
                 keep_log=True, **overrides):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            image = directory / "sdcard.img"
            image.touch()
            state_path = directory / "vm.json"
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("QEMU_")}
            environment.update(QEMU_SYSTEM_AARCH64=str(HERE / "fake-vm.py"),
                               KERNEL_IMAGE=str(image), DTB_IMAGE=str(image),
                               QEMU_DTB_BLUETOOTH="1", QEMU_COPY_IMAGE="0",
                               QEMU_HASH_IMAGE="0", QEMU_BOOT_TIMEOUT="3",
                               QEMU_STOP_TIMEOUT="0.4", FAKE_VM_MODE=mode,
                               FAKE_VM_STATE=str(state_path))
            if keep_log:
                environment["QEMU_LOG_DIR"] = str(directory / "logs")
            environment.update(overrides)
            command = [str(QEMU / entry), str(image)]
            with subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True) as process:
                try:
                    if interrupt:
                        deadline = time.monotonic() + 4
                        while not state_path.exists() and time.monotonic() < deadline:
                            time.sleep(0.01)
                        self.assertTrue(state_path.exists(), "fake VM did not start")
                        process.send_signal(signal.SIGTERM)
                    output, _ = process.communicate(timeout=10)
                finally:
                    if process.poll() is None:
                        process.kill()
                    if state_path.exists():
                        pid = json.loads(state_path.read_text())["pid"]
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
            records = [line.removeprefix("QEMU process result: ") for line in output.splitlines()
                       if line.startswith("QEMU process result: ")]
            record = json.loads(records[0]) if records else None
            if record:
                self.assertTrue(record["reaped"], output)
                if keep_log:
                    root = "mmcblk0p6" if entry == "test-ab.sh" else "mmcblk0p5"
                    saved = directory / "logs" / f"serial-{root}.process.json"
                    self.assertEqual(json.loads(saved.read_text()), record)
                else:
                    state = json.loads(state_path.read_text())
                    self.assertFalse(Path(state["socket"]).parent.exists())
            return process.returncode, record, output

    def test_normal_quit_both_slots_and_interleaved_events(self):
        for mode, entry in (("normal", "test-boot.sh"), ("normal", "test-ab.sh"),
                            ("events", "test-boot.sh")):
            with self.subTest(mode=mode, entry=entry):
                code, result, output = self.exercise(mode, entry)
                self.assertEqual(code, 0, output)
                self.assertTrue(result["qmp_quit"])
                self.assertEqual(result["returncode"], 0)
                self.assertEqual(result["fallback"], [])

    def test_nonzero_and_signal_after_acknowledged_quit(self):
        for mode, expected in (("nonzero", 7), ("signal", -signal.SIGKILL)):
            with self.subTest(mode=mode):
                code, result, output = self.exercise(mode)
                self.assertEqual(code, 1, output)
                self.assertTrue(result["qmp_quit"])
                self.assertEqual(result["returncode"], expected)
                self.assertEqual(result["fallback"], [])

    def test_early_exit_before_and_after_marker_any_status(self):
        for mode in ("exit-before", "exit-after-marker", "exit-before-quit"):
            for status in ("0", "9"):
                with self.subTest(mode=mode, status=status):
                    code, result, output = self.exercise(mode, FAKE_VM_EXIT=status)
                    self.assertEqual(code, 1, output)
                    self.assertFalse(result["qmp_quit"])
                    self.assertIsNotNone(result["error"])

    def test_qmp_connect_error_reply_and_missing_response(self):
        for mode in ("no-server", "refused", "reject", "silent"):
            with self.subTest(mode=mode):
                code, result, output = self.exercise(mode)
                self.assertEqual(code, 1, output)
                self.assertFalse(result["qmp_quit"])
                self.assertIsNotNone(result["error"])
                self.assertEqual(result["fallback"], ["SIGTERM"])

    def test_hang_after_quit_requires_kill_and_fails(self):
        code, result, output = self.exercise("hang")
        self.assertEqual(code, 1, output)
        self.assertTrue(result["qmp_quit"])
        self.assertEqual(result["fallback"], ["SIGTERM", "SIGKILL"])
        self.assertEqual(result["returncode"], -signal.SIGKILL)

    def test_term_ignoring_timeout_and_interrupted_cleanup_are_bounded(self):
        for mode, interrupt in (("timeout", False), ("interrupt", True)):
            with self.subTest(mode=mode):
                code, result, output = self.exercise(mode, interrupt=interrupt,
                                                     QEMU_BOOT_TIMEOUT="1")
                self.assertEqual(code, 1 if interrupt else 124, output)
                self.assertFalse(result["qmp_quit"])
                self.assertEqual(result["fallback"], ["SIGTERM", "SIGKILL"])
                self.assertEqual(result["returncode"], -signal.SIGKILL)

    def test_missing_login_times_out(self):
        code, result, output = self.exercise("no-login", QEMU_BOOT_TIMEOUT="0.5")
        self.assertEqual(code, 124, output)
        self.assertFalse(result["qmp_quit"])

    def test_late_panic_mount_and_module_checks_still_fail_after_clean_exit(self):
        for mode in ("late-panic", "no-mount", "bad-mount", "no-modules"):
            with self.subTest(mode=mode):
                code, result, output = self.exercise(mode)
                self.assertEqual(code, 1, output)
                self.assertTrue(result["qmp_quit"])
                self.assertEqual(result["returncode"], 0)
                self.assertEqual(result["fallback"], [])

    def test_default_log_cleanup_and_explicit_empty_modules(self):
        code, _, output = self.exercise(keep_log=False, QEMU_MODULE_TEST="")
        self.assertEqual(code, 0, output)

    def test_invalid_timeouts_fail_before_starting_vm(self):
        for options in ({"QEMU_BOOT_TIMEOUT": "nan"}, {"QEMU_STOP_TIMEOUT": "0"},
                        {"QEMU_STOP_TIMEOUT": "11"}):
            with self.subTest(options=options):
                code, result, output = self.exercise(**options)
                self.assertEqual(code, 2, output)
                self.assertIsNone(result)

    def test_interactive_runner_does_not_add_qmp(self):
        code, result, output = self.exercise("inspect", entry="run-qemu.sh")
        self.assertEqual(code, 0, output)
        self.assertIsNone(result)
        self.assertNotIn('"-qmp"', output)


class CryptsetupVersionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "cryptsetup_version", ROOT / "board/cardputerzero/tools/bench/cryptsetup-version.py")
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def exercise(self, version="2.8.9", missing_image=False):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            images = directory / "output/images"
            images.mkdir(parents=True)
            original = b"original image"
            for name in ("sdcard.img", "Image", "bcm2710-rpi-cm0.dtb"):
                (images / name).write_bytes(original)
            if missing_image:
                (images / "sdcard.img").unlink()
            scratch = directory / "tmp"
            scratch.mkdir()
            evidence = directory / "evidence"
            state = directory / "vm.json"
            environment = {k: v for k, v in os.environ.items() if not k.startswith("QEMU_")}
            environment.update(TMPDIR=str(scratch), QEMU_DTB_BLUETOOTH="1",
                               QEMU_SYSTEM_AARCH64=str(HERE / "fake-vm.py"),
                               FAKE_VM_MODE="cryptsetup", FAKE_VM_STATE=str(state),
                               FAKE_CRYPTSETUP_VERSION=version)
            result = subprocess.run(
                [sys.executable, self.probe.__file__, str(images.parent),
                 str(evidence), "2.8.9"],
                env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(list(scratch.iterdir()), [], result.stderr)
            record = json.loads((evidence / "process.json").read_text())
            if missing_image:
                self.assertFalse(state.exists())
            else:
                vm = json.loads(state.read_text())
                self.assertFalse(Path(vm["image"]).exists())
                self.assertEqual((images / "sdcard.img").read_bytes(), original)
            return result, record

    def test_probe_cleans_copied_image_after_normal_quit(self):
        result, record = self.exercise()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(record, dict(qmp_quit=True, returncode=0, fallback=[], error=None))

    def test_probe_cleans_copied_image_after_wrong_version(self):
        result, record = self.exercise(version="2.8.7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(record["error"])
        self.assertFalse(record["qmp_quit"])

    def test_probe_cleans_scratch_after_missing_image(self):
        result, record = self.exercise(missing_image=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(record["error"])

    def test_target_version(self):
        for line in ("cryptsetup 2.8.9", "cryptsetup 2.8.9 flags: BLKID KEYRING"):
            for newline in ("\n", "\r\n"):
                with self.subTest(line=line, newline=newline):
                    self.probe.check_version(
                        newline.join((line, "CRYPTSETUP_STATUS=0", "")), "2.8.9")

    def test_empty_or_wrong_version_and_status(self):
        valid = "cryptsetup 2.8.9\nCRYPTSETUP_STATUS=0\n"
        for text in ("", "cryptsetup 2.8.9\n", "CRYPTSETUP_STATUS=0\n",
                     valid.replace("2.8.9", "2.8.7"), valid.replace("STATUS=0", "STATUS=1"),
                     valid + valid, valid.replace("2.8.9", "2.8.9-rc1"),
                     valid.replace("cryptsetup ", "echo cryptsetup "),
                     valid.replace("cryptsetup ", "# cryptsetup ")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.probe.check_version(text, "2.8.9")


if __name__ == "__main__":
    unittest.main()
