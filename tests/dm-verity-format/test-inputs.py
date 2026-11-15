#!/usr/bin/env python3
"""formatterの入力、乱数、自己検査と失敗伝搬をhostで検査する。"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(sys.argv.pop(1)).resolve()
ROOT = Path(__file__).resolve().parents[2]


class Inputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.image = self.directory / "test.img"
        self.params = self.directory / "test.env"
        self.data = bytes(range(256)) * 32

    def run_tool(self, *args, data=None, env=None, stdout=subprocess.PIPE):
        self.image.write_bytes(self.data if data is None else data)
        return subprocess.run([str(TOOL), *args, "--params-file", str(self.params),
                               str(self.image)], stdout=stdout, stderr=subprocess.PIPE,
                              env=env, check=False)

    def test_fixed_salt_and_independent_sha256_readback(self):
        images = []
        for _ in range(2):
            result = self.run_tool("--hash", "sha256", "--salt", "aB01", "--no-superblock")
            self.assertEqual(result.returncode, 0, result.stderr)
            params = dict(line.split("=", 1) for line in self.params.read_text().splitlines())
            image = self.image.read_bytes()
            salt = bytes.fromhex("ab01")
            level = b"".join(hashlib.sha256(salt + self.data[i:i+4096]).digest()
                             for i in range(0, len(self.data), 4096)).ljust(4096, b"\0")
            self.assertEqual(image[len(self.data):], level)
            self.assertEqual(params["root_hash"], hashlib.sha256(salt + level).hexdigest())
            images.append(image)
        self.assertEqual(*images)

    def test_random_salt_length_and_nondeterminism(self):
        for size in (1, 32, 256):
            salts = []
            # 1 byteでは衝突し得るので8回全て同じ場合だけ失敗する。
            for _ in range(8 if size == 1 else 2):
                result = self.run_tool("--salt-random", str(size))
                self.assertEqual(result.returncode, 0, result.stderr)
                params = dict(line.split("=", 1) for line in self.params.read_text().splitlines())
                salt = bytes.fromhex(params["salt"])
                self.assertEqual(len(salt), size)
                self.assertEqual(self.image.read_bytes()[len(self.data)+88:len(self.data)+88+size], salt)
                salts.append(salt)
            self.assertGreater(len(set(salts)), 1)

    def test_invalid_numbers_and_hex(self):
        for option in ("--salt-random", "--fec-roots", "--block-size"):
            for value in ("", "x", "1x", "-1", "+2", " 2", "18446744073709551616", "4294967298"):
                with self.subTest(option=option, value=value):
                    self.assertNotEqual(self.run_tool(option, value).returncode, 0)
                    self.assertEqual(self.image.read_bytes(), self.data)
        for value in ("", "0g", "g0", " 0", "+0", "0x", "abc", "aa" * 257):
            with self.subTest(hex=value):
                self.assertNotEqual(self.run_tool("--salt", value).returncode, 0)
                self.assertEqual(self.image.read_bytes(), self.data)

    def test_short_input(self):
        for data in (b"", b"x", bytes(4096)):
            self.assertNotEqual(self.run_tool("--salt", "-", data=data).returncode, 0)
            self.assertEqual(self.image.read_bytes(), data)

    def test_io_failures(self):
        shim = self.directory / "fault.so"
        subprocess.run(["cc", "-shared", "-fPIC", "-Wall", "-Wextra", "-o", str(shim),
                        str(ROOT / "tests/dm-verity-format/fault.c"), "-ldl"], check=True)
        for fault in ("image-read", "image-write", "image-sync", "image-close",
                      "params-sync", "params-close"):
            env = dict(os.environ, LD_PRELOAD=str(shim), VERITYFMT_FAIL=fault)
            with self.subTest(fault=fault):
                self.assertNotEqual(self.run_tool("--salt", "-", env=env).returncode, 0)
        self.image.write_bytes(self.data)
        result = subprocess.run([str(TOOL), "--params-file", "/dev/full", str(self.image)],
                                capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        with open("/dev/full", "wb") as full:
            self.assertNotEqual(self.run_tool("--salt", "-", stdout=full).returncode, 0)

    def test_selftest_detects_sha_failure(self):
        source = (ROOT / "board/cardputerzero/tools/dm-verity/verityfmt.c").read_text()
        mutated = self.directory / "mutated.c"
        mutated.write_text(source.replace("0x428a2f98", "0x428a2f99"))
        binary = self.directory / "mutated"
        subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-o", str(binary), str(mutated)], check=True)
        result = subprocess.run([str(binary), "--selftest"], capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
