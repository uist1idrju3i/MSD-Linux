#!/usr/bin/env python3
"""Exercise swap setup with isolated proc/sys/dev fixtures."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-zram"


class Zram(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ["run", "bin", "proc/1/task/1", "proc/7", "sys/block/zram0", "dev"]:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.put("proc/1/task/1/children", "7")
        self.put("proc/7/comm", "getty\n")
        self.put("proc/meminfo", "MemTotal: 262144 kB\n")
        self.put("proc/swaps", "Filename Type Size Used Priority\n")
        self.put("sys/block/zram0/comp_algorithm", "lzo-rle [zstd]\n")
        self.put("sys/block/zram0/disksize", "0\n")
        self.put("dev/zram0", "")
        for command in ["mkswap", "swapon", "sleep"]:
            path = self.root / "bin" / command
            path.write_text(
                "#!/bin/sh\n"
                'printf "%s %s\\n" "${0##*/}" "$*" >> "$TRACE"\n'
                '[ "${FAIL_COMMAND:-}" != "${0##*/}" ]\n'
            )
            path.chmod(0o755)
        text = SCRIPT.read_text()
        for prefix in ["/proc", "/sys", "/dev/zram0", "/run"]:
            text = text.replace(prefix, str(self.root) + prefix)
        text = text.replace("test -b ", "test -f ").replace("2>&1 &", "2>&1")
        self.copy = self.root / "script"
        self.copy.write_text(text)

    def put(self, path, text):
        (self.root / path).write_text(text)

    def run_script(self, action="start", fail=""):
        return subprocess.run(
            ["sh", str(self.copy), action],
            env=dict(os.environ, PATH=str(self.root / "bin") + ":" + os.environ["PATH"],
                     TRACE=str(self.root / "trace"), FAIL_COMMAND=fail),
            capture_output=True, text=True, timeout=5,
        )

    def trace(self):
        path = self.root / "trace"
        return path.read_text() if path.exists() else ""

    def test_half_ram_zstd_and_priority(self):
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual((self.root / "sys/block/zram0/disksize").read_text(), "134217728\n")
        self.assertEqual((self.root / "sys/block/zram0/comp_algorithm").read_text(), "zstd\n")
        self.assertIn("swapon -p 100 ", self.trace())
        self.assertFalse((self.root / "run/msd-zram.lock").exists())

    def test_fallback(self):
        self.put("sys/block/zram0/comp_algorithm", "[lzo-rle] lz4\n")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual((self.root / "sys/block/zram0/comp_algorithm").read_text(), "lzo-rle\n")

    def test_empty_or_unsupported_algorithms_fail_closed(self):
        for value in ["", "[lz4]\n"]:
            with self.subTest(value=value):
                self.put("sys/block/zram0/comp_algorithm", value)
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertNotIn("mkswap", self.trace())

    def test_empty_or_zero_memory_fails_closed(self):
        for value in ["", "MemTotal: 0 kB\n"]:
            with self.subTest(value=value):
                self.put("proc/meminfo", value)
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertNotIn("swapon", self.trace())

    def test_mkswap_failure_cannot_activate(self):
        self.assertNotEqual(self.run_script(fail="mkswap").returncode, 0)
        self.assertNotIn("swapon", self.trace())

    def test_swapon_failure_and_cleanup(self):
        self.assertNotEqual(self.run_script(fail="swapon").returncode, 0)
        self.assertFalse((self.root / "run/msd-zram.lock").exists())

    def test_already_active_is_not_reformatted(self):
        self.put("proc/swaps", f"{self.root}/dev/zram0 partition 131068 0 100\n")
        self.assertEqual(self.run_script().returncode, 0)
        self.assertNotIn("mkswap", self.trace())

    def test_no_console_times_out_without_swap(self):
        self.put("proc/7/comm", "rcS\n")
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertNotIn("swapon", self.trace())

    def test_login_or_shell_also_passes_console_gate(self):
        for name in ["login", "sh"]:
            with self.subTest(name=name):
                self.put("proc/7/comm", name + "\n")
                self.assertEqual(self.run_script().returncode, 0)

    def test_other_actions_do_nothing(self):
        for action in ["stop", "restart", "reload"]:
            self.assertEqual(self.run_script(action).returncode, 0)
        self.assertEqual(self.trace(), "")

    def test_seed_cleanup_is_idempotent_for_warm_rebuilds(self):
        source = (ROOT / "board/cardputerzero/post-build.sh").read_text()
        block = source[source.index('rm -f "$target_dir/etc/init.d/S01seedrng"'):
                       source.index('test -x "$target_dir/etc/init.d/S99msd-zram"')]
        for path in ["etc/init.d/S01seedrng", "etc/init.d/S05seedrng", "etc/default/seedrng"]:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        for _ in range(2):
            subprocess.run(["sh", "-ec", 'target_dir="$1"; ' + block, "test", str(self.root)], check=True)
        self.assertFalse(list((self.root / "etc/init.d").glob("*seedrng")))
        self.assertFalse((self.root / "etc/default/seedrng").exists())
        data_init = (ROOT / "board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data").read_text()
        self.assertNotIn("/data/seedrng", data_init)

    def test_builtin_and_no_writeback_policy(self):
        config = (ROOT / "board/cardputerzero/linux.fragment").read_text().splitlines()
        for line in ["CONFIG_ZRAM=y", "CONFIG_ZSMALLOC=y", "CONFIG_ZRAM_BACKEND_ZSTD=y",
                     "CONFIG_HW_RANDOM_BCM2835=y", "# CONFIG_ZRAM_WRITEBACK is not set"]:
            self.assertIn(line, config)
        self.assertTrue(SCRIPT.read_text().rstrip().endswith("&"))
        self.assertNotIn("/data", SCRIPT.read_text())
        self.assertNotIn("backing_dev", SCRIPT.read_text())


class Records(unittest.TestCase):
    def setUp(self):
        path = ROOT / "board/cardputerzero/tools/bench/seedrng-zram/collect.py"
        spec = importlib.util.spec_from_file_location("collect", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_duplicate_dmesg_copy_is_not_a_second_observation(self):
        text = "[ 2.123456] random: crng init done\n"
        self.assertEqual(self.module.crng_time(text * 2), "2.123456")

    def test_missing_or_conflicting_crng_is_not_zero(self):
        for text in ["", "[ 1.0] random: crng init done\n[ 2.0] random: crng init done\n"]:
            with self.assertRaises(ValueError):
                self.module.crng_time(text)

    def test_empty_or_wrong_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            for text in ["", "wrong,column\n1,2\n", ",".join(self.module.FIELDS) + "\n"]:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    self.module.read_rows(path)

    def test_complete_csv_preserves_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.csv"
            path.write_text(",".join(self.module.FIELDS) + "\nrun,before,1,t_ready,1.25,s,1,raw\n")
            self.assertEqual(self.module.read_rows(path)[0]["value"], "1.25")


if __name__ == "__main__":
    unittest.main()
