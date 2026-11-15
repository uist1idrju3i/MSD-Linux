#!/usr/bin/env python3
"""QEMUなしで機能判定、上書き拒否、一括case選択を検査する。"""
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BENCH = Path("board/cardputerzero/tools/bench")
SPEC = importlib.util.spec_from_file_location("verdict", ROOT / BENCH / "dm-verity/verdict.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CAUSE = "device-mapper: verity: 254:0: data block 0 is corrupted\n"
PANIC = "Kernel panic - not syncing: dm-verity device corrupted\n"
NATURAL = "QEMU exited before the boot marker and login prompt (status 1).\n"


class Harness(unittest.TestCase):
    def test_verdicts(self):
        for serial, harness, expected, status, monitor, passed in [
            ("MSD/Linux ready", "", "ready", 0, "none", True),
            ("", "", "ready", 0, "none", False),
            (CAUSE + "MSD/Linux ready", "", "ready", 0, "none", False),
            ("Kernel panic: VFS mount failed", "", "verity-panic", 1, "panic-observed", False),
            (CAUSE + "Kernel panic: unrelated", "", "verity-panic", 1, "panic-observed", False),
            (CAUSE + PANIC, "", "verity-panic", 143, "panic-observed", True),
            (CAUSE + PANIC + "MSD/Linux ready", "", "verity-panic", 143, "panic-observed", False),
            (CAUSE, NATURAL, "verity-restart", 1, "none", False),
            (CAUSE + "reboot: Restarting system", NATURAL, "verity-restart", 1, "none", True),
            (CAUSE + "reboot: Restarting system", NATURAL, "verity-restart", 124, "none", False),
            (CAUSE + "reboot: Restarting system\nterminating on signal 15", NATURAL,
             "verity-restart", 1, "none", False),
            (CAUSE + "reboot: Restarting system", NATURAL, "verity-restart", 143, "none", False),
            (CAUSE + "Linux version A\nLinux version A", NATURAL, "verity-restart", 1, "none", True),
        ]:
            with self.subTest(serial=serial, status=status):
                self.assertEqual(MODULE.verdict(serial, harness, expected, status, monitor)["functional_pass"], passed)
        with self.assertRaises(ValueError):
            MODULE.verdict("", "", "verity-error", 0, "none")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bench = self.root / BENCH
        for relative in ("dm-verity/run-boots.sh", "dm-verity/verdict.py",
                         "boottime/parse-boottime.py", "squashfs-opts/run-all.sh"):
            destination = self.bench / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / BENCH / relative, destination)

    def executable(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def test_runner_functional_not_boottime_and_overwrite_guard(self):
        self.executable(self.root / "board/cardputerzero/qemu/test-qemu.sh", """#!/bin/sh
printf 'MSD/Linux ready\\n' >"$QEMU_LOG_DIR/serial-dm-0.log"
""")
        case = self.root / "case"
        (case / "images").mkdir(parents=True)
        image = case / "images/sdcard.img"
        image.touch()
        (case / "qemu-extra-append.txt").write_text("test\n")
        command = ["bash", str(self.bench / "dm-verity/run-boots.sh"), "--case", "test",
                   "--image", str(image), "--runs", "0", "--timeout", "2", "--expected", "ready",
                   "--csv", str(self.root / "metrics.csv"), "--log-dir", str(self.root / "logs")]
        result = subprocess.run(command, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        functional = json.loads((self.root / "logs/boot0/functional.json").read_text())
        self.assertTrue(functional["functional_pass"])
        with (self.root / "metrics.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(rows)
        self.assertTrue(all(row["valid"] == "0" for row in rows))
        before = (self.root / "metrics.csv").read_bytes()
        self.assertNotEqual(subprocess.run(command, capture_output=True, check=False).returncode, 0)
        self.assertEqual((self.root / "metrics.csv").read_bytes(), before)

    def test_b2_cases_include_l22_and_refuse_reuse(self):
        generator = self.bench / "squashfs-opts/make-case.sh"
        self.executable(generator, """#!/bin/bash
set -eu
printf '%s\\n' "$1" >>"$CALLS"
[[ "${FAIL_CASE:-}" != "$1" ]] || exit 1
mkdir -p "$4/images"
touch "$4/images/sdcard.img"
""")
        self.executable(self.bench / "dm-verity/run-boots.sh", "#!/bin/sh\nexit 0\n")
        base = self.root / "base"
        base.mkdir()
        command = ["bash", str(self.bench / "squashfs-opts/run-all.sh"), "output", str(base),
                   str(self.root / "cases"), str(self.root / "results")]
        calls = self.root / "calls.txt"
        env = dict(os.environ, CALLS=str(calls))
        self.assertEqual(subprocess.run(command, env=env, capture_output=True, check=False).returncode, 0)
        self.assertEqual(len(calls.read_text().splitlines()), 8)
        self.assertIn("S-z1m-l22", calls.read_text().splitlines())
        self.assertNotEqual(subprocess.run(command, env=env, capture_output=True, check=False).returncode, 0)
        self.assertEqual(len(calls.read_text().splitlines()), 8)
        command[-2:] = [str(self.root / "cases-fail"), str(self.root / "results-fail")]
        env["FAIL_CASE"] = "S-z1m-l22"
        self.assertNotEqual(subprocess.run(command, env=env, capture_output=True, check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
