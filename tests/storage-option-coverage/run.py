#!/usr/bin/env python3
"""固定版の入力からoptionを抽出し、分類表の欠落・重複を検査する。"""
import csv
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/experiments/2026-11-15-storage-option-coverage.csv"
STATES = {"実測済み", "既測定", "対象外", "実行不能", "未実施"}


def extract(text, kind):
    if kind == "cli":
        return set(re.findall(r"(?<![\w/-])--?[A-Za-z0-9#][A-Za-z0-9_-]*", text))
    if kind == "zswap":
        return {"zswap." + token for token in re.findall(
            r"module_param_(?:cb|named)\(\s*(\w+)", text)}
    if kind == "zram":
        return set(re.findall(r"(?:DEVICE|CLASS)_ATTR_\w+\((\w+)\)", text)) | set(
            re.findall(r"__ATTR\((\w+),", text)) | {
            "num_devices"}
    if kind == "mount":
        pairs = re.findall(r'fsparam_(\w+)\("([^"\n]+)"', text)
        return {name for _, name in pairs} | {
            "no" + name for kind, name in pairs if kind == "flag_no"}
    if kind == "mkfs":
        options = text.split("static const struct option long_options[] = {", 1)[1]
        options, tail = options.split("};", 1)
        short = re.search(r'getopt_long\(argc, argv, "([^"]+)"', tail)[1]
        return {"--" + name for name in re.findall(r'{\s*"([^"]+)"', options)} | {
            "-" + letter for letter in short if letter != ":"}
    if kind == "verity":
        return set(re.findall(r'^#define DM_VERITY\w*OPT\w*\s+"([^"]+)"', text, re.M))
    if kind == "zstd-lib":
        return set(re.findall(r'\bZSTD_[cd]_\w+', text))
    if kind in {"config", "brconfig"}:
        prefix = "CONFIG_" if kind == "config" else ""
        return {prefix + token for token in re.findall(
            r"^\s*(?:menuconfig|config)\s+(\w+)", text, re.M)}
    raise ValueError("unknown extractor: " + kind)


def validate(expected, rows):
    actual = [(row["surface"], row["token"]) for row in rows]
    if not actual or len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError("missing, duplicate, unexpected, or empty tokens")
    for row in rows:
        if row["status"] not in STATES or not row["reason"] or not row["reference"]:
            raise ValueError("classification, reason, and reference required")


class Coverage(unittest.TestCase):
    def test_extractors(self):
        self.assertEqual(extract("-b --fast --long=27 /foo/bar not-an-option", "cli"),
                         {"-b", "--fast", "--long"})
        self.assertEqual(extract('fsparam_flag_no("ssd", Opt_ssd)', "mount"),
                         {"ssd", "nossd"})
        self.assertEqual(extract("module_param_cb(enabled, x)", "zswap"),
                         {"zswap.enabled"})
        self.assertEqual(extract("", "cli"), set())
        with self.assertRaises(ValueError):
            extract("", "unknown")

    def test_validation_failures(self):
        row = dict(surface="x", token="-b", status="未実施", reason="未測定", reference="B1")
        expected = {("x", "-b")}
        validate(expected, [row])
        for rows in [[], [row, row], [dict(row, token="-x")],
                     [dict(row, status="完了")], [dict(row, reason="")],
                     [dict(row, reference="")]]:
            with self.assertRaises(ValueError):
                validate(expected, rows)

    def test_committed_coverage(self):
        sources = json.loads(BASE.with_suffix(".json").read_text())
        expected = set()
        with tarfile.open(BASE.with_suffix(".tar.gz")) as archive:
            for source in sources:
                data = archive.extractfile(source["member"]).read()
                self.assertEqual(hashlib.sha256(data).hexdigest(), source["sha256"])
                tokens = extract(data.decode(), source["extractor"])
                self.assertTrue(tokens, source["id"])
                expected.update((source["id"], token) for token in tokens)
        with BASE.with_suffix(".csv").open() as stream:
            rows = list(csv.DictReader(stream))
        validate(expected, rows)
        print(f"ok - option coverage: tokens={len(expected)} missing=0 duplicate=0")


if __name__ == "__main__":
    unittest.main()
