import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = (
    REPO_ROOT
    / "board/cardputerzero/tools/bench/boottime/parse-boottime.py"
)
SPEC = importlib.util.spec_from_file_location("parse_boottime", PARSER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load parser at {PARSER_PATH}")
parse_boottime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parse_boottime)


FIXTURE_LOG = """\
console preamble
msd-boottime: dmesg begin
=dmesg= [    0.000000] Booting Linux on physical CPU 0x0
[    0.005000] Run /sbin/init as init process
=dmesg= [    0.010000] Run /sbin/init as init process
=dmesg= [    0.200000] EXT4-fs (mmcblk0p7): mounted filesystem with ordered data mode
[    0.250000] initcall noise+0x0 returned 0 after 900000 usecs
=dmesg= [    0.300000] initcall quick+0x0 returned 0 after 49999 usecs
=dmesg= [    0.350000] initcall boundary+0x0 returned -1 after 50000 usecs
=dmesg= [    0.400000] initcall load_driver+0x0 [demo_mod] returned 0 after 60000 usecs
=dmesg= [    0.500000] msd-boottime: rcS begin
=dmesg= [    0.600000] msd-boottime: begin S01demo
[    0.650000] msd-boottime: begin S03console-noise
=dmesg= [    0.900000] msd-boottime: end S01demo status=0
=dmesg= [    0.950000] msd-boottime: begin S99zz-boottime-dump
[    0.975000] MSD/Linux ready
=dmesg= [    1.000000] MSD/Linux ready
msd-boottime: dmesg end
msd-boottime: rcS end
console footer
"""


def metric_rows(rows, metric):
    return [row for row in rows if row["metric"] == metric]


class ParseBoottimeTest(unittest.TestCase):
    def parse(self, text=FIXTURE_LOG, exit_status=0):
        return parse_boottime.parse_text(
            text,
            run_id="fixture",
            variant="test",
            mode="icount",
            repeat=1,
            first_boot=0,
            wall_seconds=3.25,
            exit_status=exit_status,
            log_sha256="a" * 64,
        )

    def test_valid_boot_and_script_metrics(self):
        rows, reasons = self.parse()
        self.assertEqual(reasons, [])
        self.assertTrue(all(row["valid"] == "1" for row in rows))
        self.assertEqual(metric_rows(rows, "t_init")[0]["value"], "0.010000")
        self.assertEqual(metric_rows(rows, "t_data")[0]["value"], "0.200000")
        self.assertEqual(metric_rows(rows, "t_ready")[0]["value"], "1.000000")
        self.assertEqual(
            metric_rows(rows, "script:S01demo")[0]["value"], "0.300000"
        )
        self.assertEqual(
            metric_rows(rows, "script_status:S01demo")[0]["value"], "0"
        )
        self.assertIn("first_boot=0", rows[0]["note"])
        self.assertIn("mode=icount", rows[0]["note"])
        self.assertEqual(metric_rows(rows, "t_rcs_end"), [])
        self.assertEqual(metric_rows(rows, "script:S99zz-boottime-dump"), [])

    def test_ring_buffer_loss_invalidates_boot(self):
        text = FIXTURE_LOG.replace(
            "=dmesg= [    0.000000] Booting Linux",
            "=dmesg= [    0.000001] Booting Linux",
        )
        rows, reasons = self.parse(text)
        self.assertIn("ring_buffer_loss", reasons)
        self.assertTrue(all(row["valid"] == "0" for row in rows))
        self.assertIn("invalid:ring_buffer_loss", rows[0]["note"])

    def test_script_begin_without_end_invalidates_boot(self):
        text = FIXTURE_LOG.replace(
            "=dmesg= [    0.900000] msd-boottime: end S01demo status=0\n",
            "",
        )
        rows, reasons = self.parse(text)
        self.assertIn("script_missing_end:S01demo", reasons)
        self.assertTrue(all(row["valid"] == "0" for row in rows))
        self.assertEqual(metric_rows(rows, "script:S01demo"), [])

    def test_module_initcall_and_threshold_boundary(self):
        rows, reasons = self.parse()
        self.assertEqual(reasons, [])
        self.assertEqual(metric_rows(rows, "initcall_count")[0]["value"], "2")
        self.assertEqual(
            metric_rows(rows, "module_initcall_count")[0]["value"], "1"
        )
        self.assertEqual(
            metric_rows(rows, "module_initcall_total")[0]["value"], "0.060000"
        )
        self.assertEqual(
            metric_rows(rows, "module_initcall:demo_mod:load_driver")[0]["value"],
            "0.060000",
        )
        self.assertEqual(metric_rows(rows, "initcall:quick"), [])
        self.assertEqual(
            metric_rows(rows, "initcall:boundary")[0]["value"], "0.050000"
        )

    def test_nonzero_exit_status_invalidates_boot(self):
        rows, reasons = self.parse(exit_status=1)
        self.assertIn("exit_status_nonzero", reasons)
        self.assertTrue(all(row["valid"] == "0" for row in rows))

    def test_interleaved_console_lines_are_ignored(self):
        rows, reasons = self.parse()
        self.assertEqual(reasons, [])
        self.assertEqual(metric_rows(rows, "t_init")[0]["value"], "0.010000")
        self.assertEqual(metric_rows(rows, "t_ready")[0]["value"], "1.000000")
        self.assertEqual(metric_rows(rows, "initcall_total")[0]["value"], "0.099999")
        self.assertEqual(metric_rows(rows, "script:S03console-noise"), [])

    def test_leading_nul_before_dmesg_sentinel_is_ignored(self):
        text = FIXTURE_LOG.replace(
            "msd-boottime: dmesg begin",
            "\x00msd-boottime: dmesg begin",
        )
        rows, reasons = self.parse(text)
        self.assertEqual(reasons, [])
        self.assertTrue(all(row["valid"] == "1" for row in rows))

    def test_csv_rows_use_lf_line_endings(self):
        rows, _ = self.parse()
        with tempfile.TemporaryDirectory() as temporary_dir:
            csv_path = Path(temporary_dir) / "boot.csv"
            parse_boottime.append_csv(csv_path, rows)
            self.assertNotIn("\r", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
