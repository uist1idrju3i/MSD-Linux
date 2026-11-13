#!/usr/bin/env python3
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "pqc", ROOT / "board/cardputerzero/tools/bench/pqc-groups/run.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
qspec = importlib.util.spec_from_file_location(
    "pqc_qemu", ROOT / "board/cardputerzero/tools/bench/pqc-groups/qemu.py")
qemu = importlib.util.module_from_spec(qspec)
qspec.loader.exec_module(qemu)


class ProbeTests(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(len(probe.VARIANTS), 5)
        self.assertEqual(probe.VARIANTS["default"], [])
        self.assertEqual(probe.VARIANTS["all-three"],
                         ["no-ml-kem", "no-ml-dsa", "no-slh-dsa"])

    def test_hash_empty_and_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data"
            for data in [b"", b"pqc"]:
                path.write_bytes(data)
                self.assertEqual(probe.sha(path), hashlib.sha256(data).hexdigest())

    def test_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                probe.sha(Path(directory) / "missing")

    def test_command_status(self):
        with tempfile.TemporaryFile(mode="w+") as log:
            probe.run([sys.executable, "-c", "pass"], ROOT, log)
            with self.assertRaises(subprocess.CalledProcessError):
                probe.run([sys.executable, "-c", "raise SystemExit(7)"], ROOT, log)


class SerialTests(unittest.TestCase):
    def fixture(self):
        lines = [f"FUNCTIONAL_OK {variant}" for variant in probe.VARIANTS]
        lines += [f"CLIENTHELLO {group} 300" for group in [
            "DEFAULT", "X25519", "X25519MLKEM768", "?X25519MLKEM768:DEFAULT"]]
        for repeat in range(1, 6):
            lines += [f"SPEED_REPEAT {repeat}", "+DTP:X25519:keygen:1",
                      "+DTP:X25519MLKEM768:keygen:1",
                      "+F9:10:100:200:300", "+F9:15:50:60:70"]
        return "\r\n".join(lines + ["PQC_DONE", "PROBE_EXIT=0"])

    def test_normal(self):
        result = qemu.parse_serial(self.fixture())
        self.assertEqual(len(result["speed"]), 10)
        self.assertEqual(result["speed"][1]["algorithm"], "X25519MLKEM768")
        self.assertEqual(result["speed"][0]["keygen"], 100)
        self.assertEqual(result["clienthello"]["DEFAULT"], 300)

    def test_empty_incomplete_and_failed(self):
        for raw in ["", self.fixture().replace("PROBE_EXIT=0", "PROBE_EXIT=1"),
                    self.fixture().replace("+F9:10:100:200:300", ""),
                    self.fixture().replace("FUNCTIONAL_OK default", ""),
                    self.fixture().replace("CLIENTHELLO DEFAULT 300", ""),
                    self.fixture().replace("SPEED_REPEAT 3", "SPEED_REPEAT 4")]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                qemu.parse_serial(raw)

    def test_invalid_rate(self):
        for value in ["0", "-1", "nan", "inf", "oops"]:
            raw = self.fixture().replace(":100:200:300", f":{value}:200:300")
            with self.subTest(value=value), self.assertRaises(ValueError):
                qemu.parse_serial(raw)


if __name__ == "__main__":
    unittest.main()
