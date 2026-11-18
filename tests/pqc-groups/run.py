#!/usr/bin/env python3
import hashlib
import importlib.util
import base64
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
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
cnspec = importlib.util.spec_from_file_location(
    "cnf_probe", ROOT / "board/cardputerzero/tools/bench/openssl-cnf/run.py")
cnf = importlib.util.module_from_spec(cnspec)
cnspec.loader.exec_module(cnf)


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


class CnfTests(unittest.TestCase):
    def fixture(self):
        logs = {"module-config": "CONFIG_MODULE_SIG_FORCE=y",
                "providers": "Providers:\n  default\n"}
        for pbkdf in ("argon2id", "pbkdf2"):
            logs[f"{pbkdf}-dump"] = pbkdf
            for action in ("format", "open"):
                logs[f"{pbkdf}-{action}"] = "[default][legacy]"
        for direction in ("server", "client"):
            for protocol, version in (("tls1_2", "TLSv1.2"), ("tls1_3", "TLSv1.3")):
                logs[f"tls-{direction}-{protocol}-aead"] = f"Protocol version: {version}"
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:") as archive:
            for name, text in logs.items():
                data = text.encode()
                member = tarfile.TarInfo(f"logs/{name}.log")
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return "\n".join([
            *[f"CNF_RESULT case={name} rc=0 pass=1 writes=0 sectors=0" for name in cnf.CASES],
            "CNF_LOGS_BEGIN", base64.b64encode(buffer.getvalue()).decode(), "CNF_LOGS_END",
            "CNF_DONE", "PROBE_EXIT=0"])

    def test_cnf_only_and_preserved_ca_csr(self):
        original = ("config_diagnostics = 1\n[openssl_init]\nproviders = provider_sect\n"
                    "[default_sect]\n# activate = 1\n[ca]\n[req]\n")
        self.assertEqual(cnf.configuration(original, "C0"), original)
        for variant in ("C1", "C2"):
            result = cnf.configuration(original, variant)
            for text in ("[ca]", "[req]", "MinProtocol = TLSv1.2", "activate = 1"):
                self.assertIn(text, result)
        self.assertIn("DEFAULT:@SECLEVEL=2", cnf.configuration(original, "C1"))
        self.assertIn("Groups = DEFAULT", cnf.configuration(original, "C2"))
        for original, variant in (("", "C1"), ("[openssl_init]", "C2"), ("x", "unknown")):
            with self.assertRaises(ValueError):
                cnf.configuration(original, variant)

    def test_complete_cnf_probe(self):
        rows, data = cnf.parse_serial(self.fixture())
        self.assertEqual(len(rows), 25)
        self.assertTrue(data)

    def test_empty_missing_failed_duplicate_or_corrupt(self):
        raw = self.fixture()
        for text in ("", raw.replace("CNF_DONE", ""),
                     raw.replace("PROBE_EXIT=0", "PROBE_EXIT=1"),
                     raw.replace("pass=1", "pass=0", 1),
                     raw.replace("sectors=0", "sectors=-1", 1),
                     raw.replace("case=providers", "case=ciphers"),
                     raw.replace("CNF_LOGS_BEGIN", "missing"),
                     raw.replace("CNF_LOGS_END", "invalid!\nCNF_LOGS_END")):
            with self.subTest(text=text[:50]), self.assertRaises((ValueError, tarfile.TarError)):
                cnf.parse_serial(text)


if __name__ == "__main__":
    unittest.main()
