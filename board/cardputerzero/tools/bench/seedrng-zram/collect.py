#!/usr/bin/env python3
"""Combine raw boot/counter records and retain the failed serial attempt."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess


FIELDS = ["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"]


def crng_time(text):
    values = set(re.findall(r"\[\s*([\d.]+)\] random: crng init done", text))
    if len(values) != 1:
        raise ValueError("missing or inconsistent crng marker")
    return next(iter(values))


def read_rows(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected columns: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty records: {path}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    root = args.run_root
    rows = []

    def add(run, variant, repeat, metric, value, unit, valid="1", note=""):
        rows.append(dict(zip(FIELDS, [run, variant, repeat, metric, value, unit, valid, note])))

    for variant in ["before", "after"]:
        rows.extend(read_rows(root / f"boot-{variant}.csv"))
        for repeat in range(6):
            log = root / f"bt-{variant}/boot{repeat}/serial-mmcblk0p5.log"
            add(f"boot-{variant}", variant, repeat, "crng_init", crng_time(log.read_text()),
                "s", note=f"first_boot={int(repeat == 0)};initcall_debug=1")
        folder = "before-images" if variant == "before" else "final-images"
        for path in sorted((root / folder).iterdir()):
            add(folder, variant, 0, path.name + ".bytes", path.stat().st_size, "B")
        log = root / ("probe-before" if variant == "before" else "probe-after-final") / "serial.log"
        text = log.read_text(errors="replace")
        add(log.parent.name, variant, 0, "crng_init", crng_time(text), "s",
            note="single functional probe;initcall_debug=0")
        if variant == "after":
            match = re.search(r"MSDLOAD available_kib=(\d+) bytes=(\d+) swap_used_kib=(\d+)", text)
            if not match or "MSDLOAD_DONE=0" not in text:
                raise ValueError("missing successful pressure result")
            for metric, value, unit in zip(["available_before_load", "allocation", "swap_used"],
                                            match.groups(), ["KiB", "B", "KiB"]):
                add(log.parent.name, variant, 0, metric, value, unit)
            add(log.parent.name, variant, 0, "oom_markers", text.count("invoked oom-killer"), "count")
    for name in ["idle-before", "idle-after-retry"]:
        for row in read_rows(root / name / "raw.csv"):
            row["valid"] = {"yes": "1", "no": "0"}.get(row["valid"], row["valid"])
            rows.append(row)
    failed = root / "idle-after/serial.log"
    for line in failed.read_text(errors="replace").splitlines():
        if line.startswith("MSDSTAT,"):
            add("idle-after", "after", 0, "failed_serial_sample", line, "raw", "0",
                "invalid run: kernel console output interleaved into a sample")
    add("idle-after", "after", 0, "exit_status", 1, "code", "0", "interleaved console; retried")
    patch = subprocess.check_output(["git", "diff", "--binary", args.base, "--",
                                     "board/cardputerzero/busybox.fragment",
                                     "board/cardputerzero/linux.fragment",
                                     "board/cardputerzero/post-build.sh",
                                     "board/cardputerzero/rootfs-overlay"])
    (root / "product.patch").write_bytes(patch)
    add("source", "after", 0, "product_patch", hashlib.sha256(patch).hexdigest(), "sha256",
        note=f"base={args.base}")
    for name in ["probe-before/inputs.json", "probe-after-final/inputs.json",
                 "idle-before/metadata.json", "idle-after-retry/metadata.json"]:
        metadata = json.loads((root / name).read_text())
        for path, digest in metadata.get("inputs", metadata).items():
            add(name, "metadata", 0, "input_sha256", digest, "sha256", note=path)
    artifacts = [p for p in root.rglob("*") if p.is_file() and
                 (p.suffix in {".log", ".config", ".json"} or p.name in
                  {"Image", "rootfs.squashfs", "sdcard.img", "bcm2710-rpi-cm0.dtb", "pressure"})]
    for path in sorted(artifacts):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        add("artifact", "metadata", 0, "sha256", digest, "sha256", note=str(path.relative_to(root)))
    with args.csv.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"ok - {len(rows)} raw rows including failed attempt and artifact hashes")


if __name__ == "__main__":
    main()
