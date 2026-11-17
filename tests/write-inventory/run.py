#!/usr/bin/env python3

import importlib.util
import io
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "write_inventory",
    ROOT / "board/cardputerzero/tools/bench/write-inventory/run.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPORT_SPEC = importlib.util.spec_from_file_location(
    "residual_report",
    ROOT / "board/cardputerzero/tools/bench/write-inventory/residual-report.py",
)
REPORT = importlib.util.module_from_spec(REPORT_SPEC)
REPORT_SPEC.loader.exec_module(REPORT)


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
    def test_trace_blocks_reconcile_with_guest_counters(self):
        text = (
            "blk_co_pwritev blk 0x1 bs 0x2 offset 0 bytes 512 flags 0x0\n"
            "blk_co_pwritev blk 0x1 bs 0x2 offset 4096 bytes 4096 flags 0x0\n"
            "blk_co_pwritev blk 0x1 bs 0x2 offset 8192 bytes 4096 flags 0x0\n"
        )
        self.assertEqual(REPORT.select_blocks(text, 8, 16, 16, 8, 16), {1: 8})
        self.assertEqual(REPORT.select_blocks(text, 8, 8, 16, 8, 16), {})

    def test_empty_or_truncated_trace_is_not_zero_writes(self):
        for text in ["", "blk_co_pwritev blk 0x1"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                REPORT.select_blocks(text, 0, 8, 8, 8, 16)

    def test_trace_mismatch_and_unaligned_or_cross_partition_writes_fail(self):
        for offset, length, total in [(4096, 4096, 7), (4097, 4096, 8),
                                      (4096, 0, 0), (4096, 12288, 24)]:
            text = f"blk_co_pwritev blk 0x1 bs 0x2 offset {offset} bytes {length} flags 0x0"
            with self.subTest(offset=offset, length=length, total=total):
                with self.assertRaises(ValueError):
                    REPORT.select_blocks(text, 0, total, total, 8, 16)

    def test_residual_cli_accepts_guest_script_and_trace(self):
        arguments = [
            "run.py", "--output", "unused", "--run-dir", "unused-run",
            "--variant", "trace", "--guest-script", "probe.sh", "--trace-writes",
        ]
        with mock.patch("sys.argv", arguments), mock.patch.object(
            Path, "mkdir", side_effect=RuntimeError("arguments accepted")
        ), self.assertRaisesRegex(RuntimeError, "arguments accepted"):
            MODULE.main()

    def test_empty_cli_is_not_a_successful_probe(self):
        with mock.patch("sys.argv", ["run.py"]), mock.patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                MODULE.main()
        self.assertEqual(error.exception.code, 2)

    def test_guest_script_requires_a_value(self):
        with mock.patch("sys.argv", ["run.py", "--guest-script"]), mock.patch(
            "sys.stderr", io.StringIO()
        ):
            with self.assertRaises(SystemExit) as error:
                MODULE.main()
        self.assertEqual(error.exception.code, 2)

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
