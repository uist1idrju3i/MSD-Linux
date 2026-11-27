#!/usr/bin/env python3
"""Reproduce signed metadata selection for the November 26 snapshot update."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--keyring-image", default="msd-dev:base309")
    args = parser.parse_args()
    source = Path(__file__).with_name("2026-11-12-dev-image-snapshot.py")
    spec = importlib.util.spec_from_file_location("snapshot_metadata", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OLD = "20261121T225354Z"
    module.PREVIOUS = "20261124T184346Z"
    module.NEW = "20261124T215723Z"
    module.FIXES = {
        "libgssapi-krb5-2": "1.21.3-5+deb13u2",
        "libk5crypto3": "1.21.3-5+deb13u2",
        "libkrb5-3": "1.21.3-5+deb13u2",
        "libkrb5support0": "1.21.3-5+deb13u2",
        "libzstd-dev": "1.5.7+dfsg-1+deb13u1",
        "libzstd1": "1.5.7+dfsg-1+deb13u1",
        "linux-libc-dev": "6.12.118-1",
    }
    module.metadata(args.output, args.keyring_image)
    binaries = json.loads((args.output / "linux-libc-dev-binfiles.json").read_text())
    shared = [row for row in binaries["result"] if row["architecture"] == "all"]
    assert len(shared) == 1
    filename = args.output / "linux-libc-dev-all.json"
    info = json.loads(module.fetch(
        f"https://snapshot.debian.org/mr/file/{shared[0]['hash']}/info", filename))
    assert min(row["first_seen"] for row in info["result"]) <= module.NEW
    with (args.output / "sources.csv").open("a") as stream:
        csv.writer(stream).writerow((filename.name, filename.stat().st_size,
                                    hashlib.sha256(filename.read_bytes()).hexdigest()))
    print("ok - architecture-independent linux-libc-dev first_seen also precedes selection")


if __name__ == "__main__":
    main()
