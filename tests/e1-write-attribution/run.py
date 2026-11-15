#!/usr/bin/env python3

import copy
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py"
SPEC = importlib.util.spec_from_file_location("e1_aggregate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FIELDS = ["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"]


class Attribution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "base-r1"
        self.run.mkdir()
        (self.run / "metadata.json").write_text(json.dumps({
            "variant": "base", "windows": 2, "seconds": 120
        }))
        (self.run / "serial.log").write_text("MSDPROBE finished\n")
        self.rows = []
        phases = [("boot", 0, 0, 8), ("idle-before", 1, 1, 8),
                  ("idle-after", 1, 121, 16), ("idle-before", 2, 122, 16),
                  ("idle-after", 2, 242, 16), ("ram-before", 0, 243, 16),
                  ("ram-after", 0, 244, 16), ("disk-before", 0, 245, 16),
                  ("disk-after", 0, 246, 2064)]
        for phase, repeat, uptime, value in phases:
            for device in sorted(MODULE.DEVICES):
                self.rows.append(dict(run_id="base-r1", variant="base", repeat=repeat,
                                      metric=f"{device}.write_sectors", value=value,
                                      unit="sector512", valid="yes",
                                      note=f"phase={phase};uptime={uptime};stat=0 0 0 0 0 0 {value} 0 0 0 0"))
        self.write_rows(self.rows)

    def write_rows(self, rows):
        with (self.run / "raw.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def command(self, *args, directory=None):
        return subprocess.run(["python3", str(SCRIPT), str(directory or self.run),
                               "--windows", "2", "--repeats", "1", "--variants", "base",
                               *args], capture_output=True, text=True)

    def test_complete_validate_and_aggregate(self):
        self.assertEqual(self.command("--complete").returncode, 0)
        self.assertEqual(self.command("--validate").returncode, 0)
        result = self.command(directory=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("base\t1\t8\t8\t0\t16", result.stdout)
        self.assertNotEqual(self.command("--complete").returncode, 0)

    def test_marker_required_and_legacy_read_only(self):
        self.assertNotEqual(self.command("--validate").returncode, 0)
        self.assertEqual(self.command("--legacy", directory=self.root).returncode, 0)
        self.assertFalse((self.run / MODULE.MARKER).exists())

    def test_missing_or_duplicate_any_device(self):
        for rows in [self.rows[:-1], self.rows + [self.rows[0]]]:
            with self.subTest(rows=len(rows)):
                self.write_rows(rows)
                self.assertNotEqual(self.command("--complete").returncode, 0)
                self.assertFalse((self.run / MODULE.MARKER).exists())

    def test_empty_inputs(self):
        self.write_rows([])
        self.assertNotEqual(self.command("--complete").returncode, 0)
        (self.run / "raw.csv").write_text("")
        self.assertNotEqual(self.command("--complete").returncode, 0)
        self.assertNotEqual(self.command(directory=self.root / "absent").returncode, 0)

    def test_bad_row_and_identity(self):
        for field, value in [("valid", "no"), ("variant", "other"), ("run_id", "wrong"),
                             ("value", "-1"), ("repeat", "99"), ("metric", "bad")]:
            with self.subTest(field=field):
                rows = copy.deepcopy(self.rows)
                rows[0][field] = value
                self.write_rows(rows)
                self.assertNotEqual(self.command("--complete").returncode, 0)

    def test_bad_timing_counter_and_positive_control(self):
        for old, new in [("uptime=121", "uptime=120"),
                         ("uptime=246", "uptime=nan"), (" 2064 ", " 100 ")]:
            with self.subTest(new=new):
                rows = copy.deepcopy(self.rows)
                for row in rows:
                    row["note"] = row["note"].replace(old, new)
                    if new == " 100 " and row["value"] == 2064:
                        row["value"] = 100
                self.write_rows(rows)
                self.assertNotEqual(self.command("--complete").returncode, 0)

    def test_completion_marker_and_evidence_are_bound(self):
        self.assertEqual(self.command("--complete").returncode, 0)
        for name in ["serial.log", "raw.csv", "metadata.json"]:
            with self.subTest(name=name):
                path = self.run / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assertNotEqual(self.command("--validate").returncode, 0)
                path.write_bytes(original)

    def test_unfinished_probe_or_wrong_window_count(self):
        (self.run / "serial.log").write_text("incomplete\n")
        self.assertNotEqual(self.command("--complete").returncode, 0)
        (self.run / "serial.log").write_text("MSDPROBE finished\n")
        self.assertNotEqual(self.command("--windows", "3", "--complete").returncode, 0)

    def test_no_partial_aggregate_output(self):
        self.assertEqual(self.command("--complete").returncode, 0)
        (self.root / "other-r1").mkdir()
        result = self.command(directory=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_missing_repeat_or_variant_rejected(self):
        self.assertEqual(self.command("--complete").returncode, 0)
        for args in [("--repeats", "2"), ("--variants", "base,mature")]:
            result = self.command(*args, directory=self.root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_failed_attempt_preserved_and_excluded(self):
        self.assertEqual(self.command("--complete").returncode, 0)
        failed = self.root / "base-r1.failed-preserved"
        failed.mkdir()
        result = self.command(directory=self.root)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(failed.is_dir())

    def test_prepare_refuses_existing_input_without_removal(self):
        output = self.root / "output"
        (output / "images").mkdir(parents=True)
        (output / "images/sdcard.img").write_text("fixture")
        work = self.root / "work"
        evidence = work / "input-grown-fs64"
        evidence.mkdir(parents=True)
        (evidence / "keep").write_text("evidence")
        result = subprocess.run([
            "sh", str(SCRIPT.with_name("2026-11-15-data-first-boot-writes-prepare-variants.sh"))
        ], env=dict(os.environ, E1_OUTPUT_DIR=str(output), E1_WORK_DIR=str(work)),
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual((evidence / "keep").read_text(), "evidence")


if __name__ == "__main__":
    unittest.main()
