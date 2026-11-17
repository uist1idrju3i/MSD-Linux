#!/usr/bin/env python3
"""Reconcile QEMU SD writes with guest counters and report idle filesystem blocks."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re


FIELDS = ["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"]


def select_blocks(text, before, after, total, start, size):
    if not 0 <= before <= after <= total or start < 0 or size <= 0:
        raise ValueError("invalid counter range or partition geometry")
    sectors = []
    for line in text.splitlines():
        match = re.fullmatch(
            r"blk_co_pwritev blk \S+ bs \S+ offset (\d+) bytes (\d+) flags \S+", line
        )
        if not match:
            raise ValueError("invalid trace event")
        offset, length = map(int, match.groups())
        if offset % 512 or length <= 0 or length % 512:
            raise ValueError("unaligned trace event")
        first, end = offset // 512, (offset + length) // 512
        if end <= start or first >= start + size:
            continue
        if first < start or end > start + size:
            raise ValueError("write crosses partition boundary")
        sectors.extend((sector - start) // 8 for sector in range(first, end))
    if len(sectors) != total:
        raise ValueError(f"trace/guest total mismatch: {len(sectors)} != {total}")
    return Counter(sectors[before:after])


def read_run(directory, start, size, excluded):
    metadata = json.loads((directory / "metadata.json").read_text())
    with (directory / "raw.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    counters = {}
    for row in rows:
        if (row["run_id"] != directory.name or row["valid"] != "yes" or
                row["variant"] != metadata["variant"] or row["unit"] != "sector512"):
            raise ValueError("invalid raw row")
        if row["metric"] == "mmcblk0p7.write_sectors":
            note = re.fullmatch(r"phase=([^;]+);uptime=([^;]+);stat=(.*)", row["note"])
            if not note:
                raise ValueError("invalid counter note")
            stat = [int(value) for value in note[3].split()]
            if len(stat) < 11 or stat[6] != int(row["value"]) or stat[8] != 0:
                raise ValueError("invalid counter or outstanding I/O at a boundary")
            key = note[1], int(row["repeat"])
            if key in counters:
                raise ValueError("duplicate counter")
            counters[key] = int(row["value"])
        if excluded:
            row["valid"] = "no"
            row["note"] += ";excluded_from_primary=pilot_window_too_long"
    blocks = select_blocks(
        (directory / "writes.trace").read_text(),
        counters["idle-before", 1], counters["idle-after", 1],
        counters["disk-after", 0], start, size,
    )
    for block, count in sorted(blocks.items()):
        rows.append(dict(
            run_id=directory.name, variant=metadata["variant"], repeat=1,
            metric=f"p7.fs_block_{block}.idle1_sectors", value=count,
            unit="sector512", valid="no" if excluded else "yes",
            note="block_size=4096;source=QEMU_trace_reconciled_with_guest_counters",
        ))
    return rows, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--start-sectors", type=int, required=True)
    parser.add_argument("--size-sectors", type=int, required=True)
    parser.add_argument("--exclude-from-primary", action="append", default=[])
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    names = [directory.name for directory in args.directories]
    if len(names) != len(set(names)) or set(args.exclude_from_primary) - set(names):
        parser.error("duplicate run name or unknown excluded run")
    rows = []
    for directory in args.directories:
        raw, blocks = read_run(
            directory, args.start_sectors, args.size_sectors,
            directory.name in args.exclude_from_primary,
        )
        rows.extend(raw)
        print(f"{directory.name}: idle1={sum(blocks.values())} sectors; blocks={dict(sorted(blocks.items()))}")
    with args.csv.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
