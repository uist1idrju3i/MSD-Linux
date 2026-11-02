import csv
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "board/cardputerzero/tools/bench/yocto-compare"
COLUMNS = "condition,mode,boot,first_boot,t_root,t_init,t_ready,login,wall_login_s,result".split(",")


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.csv = self.path / "results.csv"
        self.rows = [["A", "tcg", str(n), "1" if n == 0 else "0", "1", "2", "3", "1", "4", "pass"]
                     for n in range(6)]

    def summarize(self, rows=None, expected=0, header=COLUMNS, path=None):
        if path is None:
            with self.csv.open("w", newline="") as target:
                writer = csv.writer(target)
                writer.writerow(header)
                writer.writerows(self.rows if rows is None else rows)
            path = self.csv
        result = subprocess.run(["python3", str(TOOLS / "summarize.py"), str(path)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(expected, result.returncode, result.stderr)
        return list(csv.DictReader(io.StringIO(result.stdout)))

    def test_normal_boots_and_first_boot_exclusion(self):
        self.rows[0][6] = "999"
        result = self.summarize()[0]
        self.assertEqual("5", result["n"])
        self.assertEqual("3.000000", result["t_ready_median"])

    def test_failure_values_are_not_aggregated(self):
        self.rows[1][-1] = "timeout"
        self.rows[1][4:7] = ["999", "999", "999"]
        result = self.summarize(expected=1)[0]
        self.assertEqual("4", result["pass"])
        self.assertEqual("3.000000", result["t_ready_max"])

    def test_all_failed_and_failed_first_boot(self):
        self.rows[0][-1] = "exited"
        self.summarize(expected=1)
        for row in self.rows:
            row[-1] = "timeout"
            row[4:7], row[8] = ["", "", ""], ""
        result = self.summarize(expected=1)[0]
        self.assertEqual("", result["t_ready_median"])

    def test_missing_repeats_first_boot_and_gaps(self):
        self.summarize(self.rows[:-1], expected=1)
        self.summarize(self.rows[1:], expected=1)
        self.rows[-1][2] = "9"
        self.summarize(expected=1)

    def test_duplicate_and_flag_disagreement(self):
        self.summarize(self.rows + [self.rows[1]], expected=2)
        self.rows[0][3] = "0"
        self.summarize(expected=2)

    def test_bad_numbers_and_missing_pass_fields(self):
        for value in ("nan", "inf", "-1", "abc", ""):
            with self.subTest(value=value):
                self.rows[1][4] = value
                self.summarize(expected=2)

    def test_bad_columns_status_login_and_order(self):
        self.summarize(expected=2, header=COLUMNS + ["extra"])
        self.summarize([self.rows[0][:-1]], expected=2)
        self.summarize([], expected=2)
        for column, value in ((0, "../escape"), (1, "bad"), (2, "-1"), (7, "0"), (9, "unknown"), (5, "0")):
            with self.subTest(column=column):
                rows = [row.copy() for row in self.rows]
                rows[1][column] = value
                self.summarize(rows, expected=2)

    def test_recorded_54_rows_are_still_valid(self):
        results = self.summarize(path=ROOT / "docs/experiments/2026-11-02-buildroot-yocto-boottime.csv")
        self.assertEqual(9, len(results))
        self.assertTrue(all(row["n"] == row["pass"] == "5" for row in results))


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.image = self.path / "input.img"
        self.image.write_bytes(b"input image")
        self.fake = self.path / "fake-qemu"
        self.fake.write_text('''#!/usr/bin/env python3
import os, sys, time
if "--version" in sys.argv:
    print("fake QEMU for negative controls")
    sys.exit(0)
case = os.environ.get("FAKE_CASE", "pass")
if "FAKE_PID" in os.environ:
    open(os.environ["FAKE_PID"], "w").write(str(os.getpid()))
if case != "timeout":
    if case != "missing":
        print("[ 1.0] VFS: Mounted root squashfs", flush=True)
        print("[ 2.0] Run /sbin/init as init process", flush=True)
    marker = "msd-compare: ready" if "rootfstype=ext4" in " ".join(sys.argv) else "MSD/Linux ready"
    print("[ 3.0] " + marker, flush=True)
    print("host login:", flush=True)
if case == "exited":
    sys.exit(7)
time.sleep(60)
''')
        self.fake.chmod(0o755)
        self.env = dict(os.environ, QEMU_SYSTEM_AARCH64=str(self.fake), QEMU_DTB_BLUETOOTH="1")
        self.out = self.path / "new-output"

    def args(self, **overrides):
        values = dict(condition="A", kernel=self.image, dtb=self.image, image=self.image,
                      root_dev="/dev/mmcblk0p5", root_fstype="squashfs", ready_marker="MSD/Linux ready",
                      mode="tcg", runs="1", out=self.out, timeout="1")
        values.update(overrides)
        return [str(TOOLS / "run-compare.sh"), *(
            part for key, value in values.items() for part in ("--" + key.replace("_", "-"), str(value))
        )]

    def run_script(self, args=None, expected=0):
        result = subprocess.run(args or self.args(), env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(expected, result.returncode, result.stderr)
        return result

    def test_success_preserves_input_and_refuses_any_existing_output(self):
        self.run_script()
        self.assertEqual(b"input image", self.image.read_bytes())
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        self.run_script(expected=2)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})
        self.assertFalse((self.out / "A-tcg.img").exists())

    def test_rejects_bad_arguments_before_creating_output(self):
        for values in (dict(runs="0"), dict(runs="08"), dict(runs="bad"), dict(timeout="0"),
                       dict(condition="../../escape"), dict(kernel=self.path / "missing"), dict(mode="bad")):
            with self.subTest(values=values):
                self.run_script(self.args(**values), expected=2)
                self.assertFalse(self.out.exists())

    def test_failed_cases_leave_raw_evidence(self):
        for case, result in (("missing", "missing_timestamps"), ("exited", "exited"), ("timeout", "timeout")):
            with self.subTest(case=case):
                self.env["FAKE_CASE"] = case
                out = self.path / case
                self.run_script(self.args(out=out), expected=1)
                with (out / "results.csv").open() as source:
                    rows = list(csv.DictReader(source))
                self.assertEqual(2, len(rows))
                self.assertTrue(all(row["result"] == result for row in rows))
                self.assertTrue((out / "A-tcg.img").exists())
                self.assertTrue((out / "A-tcg-boot0.log").exists())

    def test_signal_stops_qemu_and_keeps_log(self):
        pidfile = self.path / "qemu.pid"
        self.env.update(FAKE_CASE="timeout", FAKE_PID=str(pidfile))
        process = subprocess.Popen(self.args(timeout="60"), env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists())
            process.terminate()
            self.assertEqual(143, process.wait(timeout=5))
            with self.assertRaises(ProcessLookupError):
                os.kill(int(pidfile.read_text()), 0)
            self.assertTrue((self.out / "A-tcg-boot0.log").exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_full_matrix_uses_separate_output_directories(self):
        for name in ("br-Image", "br-cm0.dtb", "br-sdcard.img", "yocto-e-Image", "yocto-b2-Image", "yocto-cmp.wic"):
            (self.path / name).write_bytes(b"fixture")
        args = [str(TOOLS / "run-all.sh"), str(self.path), str(self.out), "1"]
        self.run_script(args)
        with (self.out / "results.csv").open() as source:
            self.assertEqual(18, len(list(csv.DictReader(source))))
        self.run_script(args, expected=2)
        self.assertEqual(9, len(list(self.out.glob("*/results.csv"))))


if __name__ == "__main__":
    unittest.main()
