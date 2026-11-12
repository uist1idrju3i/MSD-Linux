#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "write_inventory",
    ROOT / "board/cardputerzero/tools/bench/write-inventory/run.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def transcript(windows=2):
    rows = []
    for device in sorted(MODULE.DEVICES):
        rows.append(f"MSDSTAT,boot,0,30.00,{device},0 0 0 0 1 0 8 0 0 0 0")
    for phase, repeats in [("idle", range(1, windows + 1)), ("ram", [0]), ("disk", [0])]:
        for repeat in repeats:
            for edge in ["before", "after"]:
                for device in sorted(MODULE.DEVICES):
                    sectors = 2056 if phase == "disk" and edge == "after" else 8
                    rows.append(
                        f"MSDSTAT,{phase}-{edge},{repeat},150.00,{device},"
                        f"0 0 0 0 1 0 {sectors} 0 0 0 0"
                    )
    return "\r\n".join(rows) + "\r\n"


class Samples(unittest.TestCase):
    def test_complete_raw_counters_preserve_sector_field(self):
        samples = MODULE.parse_samples(transcript(), 2)
        self.assertEqual(len(samples), 72)
        self.assertEqual(samples["disk-after", 0, "mmcblk0p7"][1], 2056)
        self.assertEqual(samples["idle-after", 2, "mmcblk0p7"][2], "0 0 0 0 1 0 8 0 0 0 0")

    def test_empty_is_not_zero_writes(self):
        with self.assertRaises(ValueError):
            MODULE.parse_samples("", 2)

    def test_repeatable_and_counter_sensitive(self):
        text = transcript()
        original = MODULE.parse_samples(text, 2)
        self.assertEqual(original, MODULE.parse_samples(text, 2))
        changed = text.replace("1 0 2056 0", "1 0 4096 0")
        self.assertNotEqual(original, MODULE.parse_samples(changed, 2))

    def test_missing_partition_is_an_error(self):
        text = "\n".join(line for line in transcript().splitlines() if ",mmcblk0p7," not in line)
        with self.assertRaises(ValueError):
            MODULE.parse_samples(text, 2)

    def test_duplicate_is_an_error(self):
        text = transcript()
        with self.assertRaises(ValueError):
            MODULE.parse_samples(text + text.splitlines()[0] + "\n", 2)

    def test_unexpected_device_or_phase_is_an_error(self):
        for old, new in [("mmcblk0p7", "mmcblk0p8"), ("idle-after", "other-after")]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                MODULE.parse_samples(transcript().replace(old, new), 2)

    def test_short_or_non_numeric_stat_is_an_error(self):
        for replacement in ["0 0", "0 0 0 0 1 0 invalid 0 0 0 0"]:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                MODULE.parse_samples(transcript().replace("0 0 0 0 1 0 8 0 0 0 0", replacement), 2)

    def test_missing_window_is_an_error(self):
        with self.assertRaises(ValueError):
            MODULE.parse_samples(transcript(1), 2)

    def test_interval_and_window_counts_must_be_positive(self):
        self.assertEqual(MODULE.positive("120"), 120)
        for value in ["0", "-1", "", "invalid"]:
            with self.subTest(value=value), self.assertRaises((ValueError, MODULE.argparse.ArgumentTypeError)):
                MODULE.positive(value)

    def test_timezone_and_ram_mount_configuration(self):
        config = (ROOT / "configs/msd_cardputerzero_defconfig").read_text().splitlines()
        self.assertIn("BR2_TARGET_TZ_INFO=y", config)
        self.assertIn('BR2_TARGET_TZ_ZONELIST="asia"', config)
        self.assertIn('BR2_TARGET_LOCALTIME="Asia/Tokyo"', config)
        mounts = {}
        for line in (ROOT / "board/cardputerzero/rootfs-overlay/etc/fstab").read_text().splitlines():
            if line and not line.startswith("#"):
                fields = line.split()
                mounts[fields[1]] = fields[2]
        for path in ["/tmp", "/run", "/dev/shm"]:
            self.assertEqual(mounts[path], "tmpfs")
        self.assertEqual(mounts["/"], "squashfs")


if __name__ == "__main__":
    unittest.main()
