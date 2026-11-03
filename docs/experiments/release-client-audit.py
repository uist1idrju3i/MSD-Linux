#!/usr/bin/env python3
"""Audit saved research captures, not a TUF client or protocol test."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def check(entry: dict, data: bytes | None) -> list[str]:
    if data is None:
        return ["missing"]
    errors = []
    if len(data) != entry["bytes"]:
        errors.append("length")
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        errors.append("sha256")
    if "git_blob_sha" in entry:
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob, usedforsecurity=False).hexdigest() != entry["git_blob_sha"]:
            errors.append("git-blob")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--captures", required=True, type=Path)
    parser.add_argument("--negative-tests", action="store_true")
    args = parser.parse_args()
    entries = json.loads(args.ledger.read_text(encoding="utf-8"))["sources"]
    seen = set()
    retrieved = failed = blobs = errors = 0
    sample = None
    for entry in entries:
        name = entry["file"]
        if name in seen or Path(name).name != name:
            raise ValueError(f"duplicate or invalid capture name: {name!r}")
        seen.add(name)
        if entry["status"] == "failed":
            if not entry.get("error"):
                raise ValueError(f"missing failure reason: {name}")
            failed += 1
            continue
        if entry["status"] != "retrieved":
            raise ValueError(f"unknown capture status: {name}")
        source = args.captures / name
        data = source.read_bytes() if source.is_file() else None
        problems = check(entry, data)
        if problems:
            errors += 1
            print(f"capture={name} errors={','.join(problems)}")
        retrieved += 1
        blobs += int("git_blob_sha" in entry)
        if not problems and sample is None:
            sample = (entry, data)
    print(f"retrieved={retrieved} recorded_failures={failed} git_blobs={blobs} errors={errors}")
    if args.negative_tests:
        if sample is None or not sample[1]:
            raise ValueError("no valid nonempty sample for negative tests")
        entry, data = sample
        altered = bytes([data[0] ^ 1]) + data[1:]
        bad_hash = copy.deepcopy(entry)
        bad_hash["sha256"] = "0" * 64
        cases = [("modified-bytes", entry, altered), ("modified-hash", bad_hash, data),
                 ("missing-source", entry, None)]
        for label, metadata, content in cases:
            rejected = bool(check(metadata, content))
            print(f"negative={label} rejected={int(rejected)}")
            errors += int(not rejected)
    return int(errors != 0)


if __name__ == "__main__":
    raise SystemExit(main())
