#!/usr/bin/env python3
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
READY = ROOT / "board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready"
UPDATER = ROOT / "board/cardputerzero/rootfs-overlay/usr/sbin/msd-update"


class ReadyTests(unittest.TestCase):
    def run_ready(self, slot, partition=None, trial=None, cmdline="", sweep=False,
                  lcd=True, action="start"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dt = root / "dt"
            dt.mkdir()
            for name, value in (("partition", partition), ("tryboot", trial)):
                if value is not None:
                    (dt / name).write_bytes(
                        value if isinstance(value, bytes) else struct.pack(">I", value)
                    )
            (root / "msd-update").symlink_to(UPDATER)
            (root / "cmdline").write_text(cmdline)
            for name in ("console", "kmsg", "tty1"):
                if name != "tty1" or lcd:
                    (root / name).touch()
            env = os.environ.copy()
            env.update({
                "PATH": str(root) + os.pathsep + env["PATH"],
                "MSD_UPDATE_DT_DIR": str(dt),
                "MSD_READY_CMDLINE": str(root / "cmdline"),
                "MSD_READY_RUN_DIR": str(root),
                "MSD_READY_CONSOLE": str(root / "console"),
                "MSD_READY_KMSG": str(root / "kmsg"),
                "MSD_READY_TTY1": str(root / "tty1"),
            })
            result = subprocess.run(["sh", str(READY), action], env=env,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stderr, "")
            self.assertEqual(result.stdout, "")
            expected = f"Boot from slot {slot}\nMSD/Linux ready\n"
            console = (root / "console").read_text()
            kmsg = (root / "kmsg").read_text()
            if action != "start":
                self.assertEqual(console + kmsg, "")
                self.assertFalse((root / "msd-ready").exists())
                return
            self.assertTrue((root / "msd-ready").is_file())
            self.assertEqual(console, "" if sweep else expected)
            self.assertEqual(kmsg, expected.replace("Boot", "<6>Boot").replace(
                "MSD/Linux", "<6>MSD/Linux") if sweep else "")
            if lcd:
                self.assertEqual((root / "tty1").read_text(), expected)
            else:
                self.assertFalse((root / "tty1").exists())

    def test_dt_slots_and_trials_override_cmdline(self):
        for partition, slot in ((2, "A"), (3, "B")):
            for trial in (0, 1):
                with self.subTest(partition=partition, trial=trial):
                    self.run_ready(slot + (" (try)" if trial else ""),
                                   partition, trial, "root=/dev/mmcblk0p5")

    def test_cmdline_fallback(self):
        for partition, slot in ((5, "A"), (6, "B")):
            with self.subTest(partition=partition):
                self.run_ready(slot, cmdline=f"quiet root=/dev/mmcblk0p{partition} ro")

    def test_unknown_and_token_boundaries(self):
        for cmdline in ("", "root=/dev/mmcblk0p7", "root=PARTUUID=abc",
                        "notroot=/dev/mmcblk0p5", "root=/dev/mmcblk0p50",
                        "root=/dev/mmcblk0p5 root=unknown"):
            with self.subTest(cmdline=cmdline):
                self.run_ready("?", cmdline=cmdline)

    def test_malformed_or_incomplete_dt_falls_back(self):
        for partition, trial in ((b"", 0), (b"\x02", 1),
                                 (b"\x00\x00\x00\x02\x00", 0),
                                 (0x02000000, 0), (4, 1), (2, 2),
                                 (2, b"bad"), (2, None), (None, 1)):
            with self.subTest(partition=partition, trial=trial):
                self.run_ready("B", partition, trial, "root=/dev/mmcblk0p6")

    def test_unknown_does_not_claim_trial(self):
        self.run_ready("?", partition=4, trial=1)

    def test_missing_tty1_is_not_created(self):
        self.run_ready("A", 2, 0, lcd=False)

    def test_sweep_preserves_kmsg_ready_path(self):
        self.run_ready("B (try)", 3, 1, "msd.sweep=1", sweep=True)

    def test_stop_does_not_emit_or_mark_ready(self):
        self.run_ready("?", action="stop")


if __name__ == "__main__":
    unittest.main()
