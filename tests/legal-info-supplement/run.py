#!/usr/bin/env python3

from contextlib import chdir
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github/scripts/legal-info-supplement.py"
spec = importlib.util.spec_from_file_location("supplement", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Collector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.source = self.root / "source"
        self.source.mkdir()
        self.env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
                        GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.command(self.repo, "init", "-q")
        self.command(self.source, "init", "-q")
        self.toolchain = "aarch64--glibc--stable-2025.08-1"
        put(self.source / module.BOOTLIN_HASH, "sha256  " + "a" * 64 + "  " + self.toolchain + ".tar.xz\n")
        put(self.source / "COPYING", "fixed Buildroot source\n")
        self.command(self.source, "add", module.BOOTLIN_HASH, "COPYING")
        self.command(self.source, "commit", "-qm", "fixture source")
        self.commit = self.command(self.source, "rev-parse", "HEAD").strip()
        (self.repo / "vendor").mkdir()
        self.command(self.repo, "clone", "-q", "--depth=1", self.source.as_uri(), "vendor/buildroot")
        self.command(self.repo, "update-index", "--add", "--cacheinfo",
                     f"160000,{self.commit},vendor/buildroot")
        self.command(self.repo, "commit", "-qm", "fixture gitlink")
        self.legal = self.root / "output/legal-info"
        for name in ["README", "manifest.csv", "host-manifest.csv"]:
            put(self.legal / name, "original warnings remain\n")
        put(self.legal / "buildroot.config", "BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE=y\n")
        self.sdk = self.root / "sdk"
        put(self.sdk / "README.txt", self.toolchain + "\n")
        put(self.sdk / "buildroot.config", "SDK fixture\n")
        put(self.sdk / "summary.csv", '"PACKAGE","VERSION"\n"compiler","1"\n"linux-headers","5.4.296"\n')
        self.licenses = self.root / "licenses"
        put(self.licenses / "compiler-1/COPYING", "license fixture\n")
        self.readme = self.root / "README.md"
        put(self.readme, "補足資料です。完全な対応sourceではありません。\n")
        self.pins = self.root / "pins.json"
        self.data = {
            "schema": 1, "toolchain": self.toolchain, "toolchain_archive_sha256": "a" * 64,
            "builder_commit": "b" * 40,
            "metadata_sha256": {name: module.sha256(self.sdk / name)
                                for name in ["README.txt", "summary.csv", "buildroot.config"]},
            "components": [{
                "component": "compiler", "version": "1", "source_archive": "compiler.tar.xz",
                "source_url": "https://example.invalid/compiler.tar.xz",
                "source_hashes": {"sha512": "c" * 128}, "source_bytes": 10,
                "patch_location": "https://example.invalid/patches/",
                "licenses": [{"path": "compiler-1/COPYING",
                              "url": "https://toolchains.bootlin.com/downloads/releases/licenses/compiler-1/COPYING",
                              "sha256": module.sha256(self.licenses / "compiler-1/COPYING")}]},
                {"component": "linux-headers", "version": "5.4.296",
                 "source_archive": "linux.tar.xz", "source_url": "https://example.invalid/linux.tar.xz",
                 "source_hashes": {"sha256": "d" * 64}, "source_bytes": 20,
                 "patch_location": "https://example.invalid/linux/", "licenses": []}],
        }
        self.save()

    def command(self, directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), *args],
                                       stderr=subprocess.PIPE, text=True, env=self.env)

    def save(self):
        self.pins.write_text(json.dumps(self.data))

    def collect(self, directory=None):
        return module.collect(self.repo, directory or self.legal, self.sdk,
                              self.pins, self.readme, self.licenses)

    def test_manifest_archive_and_originals(self):
        before = module.inventory(self.legal)
        checkout = self.repo / "vendor/buildroot"
        self.assertEqual(self.command(checkout, "rev-parse", "--is-shallow-repository").strip(), "true")
        put(checkout / "COPYING", "not the pinned source\n")
        result = self.collect()
        output = self.legal / "supplement"
        self.assertEqual(result["original_files_sha256"], before)
        for name, digest in before.items():
            self.assertEqual(module.sha256(self.legal / name), digest)
        self.assertEqual(result["buildroot"]["gitlink_commit"], self.commit)
        with tarfile.open(output / result["buildroot"]["archive"]) as archive:
            self.assertEqual(archive.extractfile(f"buildroot-{self.commit}/COPYING").read(),
                             b"fixed Buildroot source\n")
        self.assertEqual(result["components"][1]["license_status"], "uncollected")
        self.assertEqual(len(result["uncollected"]["source_archives"]), 2)
        self.assertEqual(result["uncollected"]["source_archive_bytes"], 30)
        with (output / "manifest.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["source_sha256"], "")
        self.assertEqual(rows[0]["source_sha512"], "c" * 128)
        self.assertEqual(rows[0]["license_status"], "collected/hash-verified")
        self.assertEqual(rows[1]["license_status"], "uncollected")
        for line in (output / "SHA256SUMS").read_text().splitlines():
            digest, path = line.split("  ", 1)
            self.assertEqual(module.sha256(output / path), digest)

    def test_hash_mismatch_never_publishes_supplement(self):
        put(self.licenses / "compiler-1/COPYING", "tampered\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.collect()
        self.assertFalse((self.legal / "supplement").exists())

    def test_missing_legal_input_and_license(self):
        (self.legal / "manifest.csv").unlink()
        with self.assertRaisesRegex(ValueError, "missing legal-info"):
            self.collect()
        put(self.legal / "manifest.csv", "restored\n")
        (self.licenses / "compiler-1/COPYING").unlink()
        with self.assertRaises(FileNotFoundError):
            self.collect()
        self.assertFalse((self.legal / "supplement").exists())

    def test_wrong_or_missing_sdk(self):
        put(self.sdk / "summary.csv", "wrong SDK\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.collect()
        (self.sdk / "summary.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.collect()

    def test_empty_metadata(self):
        self.data["components"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "empty"):
            self.collect()

    def test_archive_pin_mismatch(self):
        self.data["toolchain_archive_sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "archive pin"):
            self.collect()

    def test_offline_and_repeat_are_deterministic(self):
        other = self.root / "second/legal-info"
        shutil.copytree(self.legal, other)
        with patch.object(module, "download", side_effect=AssertionError("offline called network")):
            first = self.collect()
            second = self.collect(other)
        self.assertEqual(first, second)
        self.assertEqual(module.inventory(self.legal / "supplement"),
                         module.inventory(other / "supplement"))
        with self.assertRaises(FileExistsError):
            self.collect()

    def test_online_download_and_failure(self):
        with patch.object(module, "download", return_value=b"license fixture\n") as fetch:
            module.collect(self.repo, self.legal, self.sdk, self.pins, self.readme)
            fetch.assert_called_once()
        other = self.root / "network-failure"
        shutil.copytree(self.legal, other, ignore=shutil.ignore_patterns("supplement"))
        with patch.object(module, "download", side_effect=URLError("offline")):
            with self.assertRaises(URLError):
                module.collect(self.repo, other, self.sdk, self.pins, self.readme)
        self.assertFalse((other / "supplement").exists())

    def test_relative_output_paths(self):
        with chdir(self.root):
            result = module.collect(Path("repo"), Path("output/legal-info"), Path("sdk"),
                                    Path("pins.json"), Path("README.md"), Path("licenses"))
        self.assertEqual(result["buildroot"]["gitlink_commit"], self.commit)

    def test_missing_git_object(self):
        self.command(self.repo, "update-index", "--cacheinfo", "160000," + "1" * 40 + ",vendor/buildroot")
        self.command(self.repo, "commit", "-qm", "unavailable object")
        with self.assertRaises(subprocess.CalledProcessError):
            self.collect()

    def test_path_and_download_policy(self):
        for path in ["../escape", "/absolute", "", "folder/../../escape", "folder\\escape"]:
            with self.assertRaises(ValueError):
                module.relative(path)
        with self.assertRaisesRegex(ValueError, "unsupported license URL"):
            module.download("http://example.invalid/license")

    def test_pinned_inventory_and_ci_order(self):
        pins = json.loads((module.INPUTS / "bootlin-2025.08-1.json").read_text())
        self.assertEqual(len(pins["components"]), 25)
        self.assertEqual(sum(len(c["licenses"]) for c in pins["components"]), 41)
        self.assertEqual(len({c["source_url"] for c in pins["components"]
                              if c["source_archive"] != "not saved"}), 23)
        workflow = (ROOT / ".github/workflows/build.yml").read_text()
        self.assertIn("make -C output legal-info\n            python3 .github/scripts/legal-info-supplement.py --output output", workflow)
        self.assertIn('"legal-info-supplement"', (ROOT / ".github/scripts/run-host-tests.py").read_text())


if __name__ == "__main__":
    unittest.main()
