#!/usr/bin/env python3
"""Export complete measurement rows, preserving invalid and unrun entries."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


FIELDS = ("run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note")


def read_attempt(directory, expected):
    plan = json.loads((directory / "plan.json").read_text())
    with (directory / "results.csv").open() as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(FIELDS):
            raise ValueError("unexpected result columns")
        rows = list(reader)
    if len(plan) != expected or len(rows) != expected:
        raise ValueError("missing planned measurements")
    ids = [row["run_id"] for row in rows]
    if len(set(ids)) != expected or set(ids) != {row["run_id"] for row in plan}:
        raise ValueError("missing, duplicated or unexpected run IDs")
    for row in rows:
        if row["repeat"] != "1" or row["valid"] not in ("true", "false"):
            raise ValueError("invalid repeat or validity")
        if row["valid"] == "true" and not row["value"].lstrip("-").isdigit():
            raise ValueError("valid measurement without integer value")
        if row["valid"] == "false" and not row["note"]:
            raise ValueError("invalid measurement without reason")
    return rows


def verify_kernel(probe, variant, expected):
    for slot in ("A", "B"):
        state = json.loads((probe / f"{variant}-{slot}/process.json").read_text())
        if state.get("kernel_sha256") != expected:
            raise ValueError(f"executed kernel/build hash mismatch: {variant}-{slot}")


def verify_images(pair, probe, analysis):
    build = json.loads((pair / "results.json").read_text())
    regression = json.loads((probe / "metadata.json").read_text())["inputs_sha256"]
    measured = json.loads((analysis / "metadata.json").read_text())["inputs_sha256"]
    for variant in ("baseline", "candidate"):
        produced = build.get("variants", {}).get(variant, {})
        images = produced.get("images_sha256", {})
        expected = {".config": produced.get("config_sha256")}
        expected.update({"images/" + name: images.get(name) for name in ("Image", "rootfs.squashfs", "sdcard.img")})
        for name, digest in expected.items():
            if not isinstance(digest, str) or len(digest) != 64 or set(digest) - set("0123456789abcdef"):
                raise ValueError(f"missing or invalid build hash: {variant}/{name}")
            if regression.get(f"{variant}/{name}") != digest:
                raise ValueError(f"probe/build hash mismatch: {variant}/{name}")
        if measured.get(variant) != images["rootfs.squashfs"]:
            raise ValueError(f"analysis/build hash mismatch: {variant}/images/rootfs.squashfs")
        verify_kernel(probe, variant, images["Image"])


def export(pair, probe, host, analysis, out):
    verify_images(pair, probe, analysis)
    rows = read_attempt(pair, 6) + read_attempt(probe, 50) + read_attempt(analysis, 17)
    for row in rows:
        if row["metric"] == "rootfs_regular_bytes":
            row["note"] += "; Buildroot target staging, includes THIS_IS_NOT_YOUR_ROOT_FILESYSTEM; see rootfs_image_regular_bytes"
    source = host / "results.csv"
    with source.open() as stream:
        external = list(csv.DictReader(stream))
    if len(external) != 16 or {row["case"] for row in external} != {str(number) for number in range(1, 17)}:
        raise ValueError("incomplete host C1 probe")
    prefix = "openssl-host-" + hashlib.sha256((host / "metadata.json").read_bytes()).hexdigest()[:16]
    for row in external:
        rows.append(dict(run_id=prefix + "-" + row["case"], variant="host-" + row["variant"], repeat="1",
                         metric="tls" + row["protocol"] + ("-hostname" if row["negative"] == "1" else ""),
                         value=row["exit_code"], unit="status", valid="true" if row["pass"] == "1" else "false",
                         note="host-only endpoint " + row["host"] + ":" + row["port"]))
    if len({row["run_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate run IDs across attempts")
    with out.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} rows; invalid={sum(row['valid'] != 'true' for row in rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pair", "probe", "host", "analysis", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    export(args.pair, args.probe, args.host, args.analysis, args.out)
