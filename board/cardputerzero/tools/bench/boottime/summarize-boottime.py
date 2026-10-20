#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

SUMMARY_METRICS = (
    "t_init",
    "t_data",
    "t_ready",
    "initcall_total",
    "module_initcall_total",
    "wall",
)
FIRST_BOOT_RE = re.compile(r"(?:^|;)first_boot=([01])(?:;|$)")
MODE_RE = re.compile(r"(?:^|;)mode=(icount|tcg)(?:;|$)")


def summarize(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    all_groups: set[tuple[str, str, int]] = set()
    valid_boots: dict[tuple[str, str, int], set[tuple[str, str]]] = defaultdict(set)
    valid_rows: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        first_boot_match = FIRST_BOOT_RE.search(row.get("note", ""))
        mode_match = MODE_RE.search(row.get("note", ""))
        if first_boot_match is None or mode_match is None:
            continue
        first_boot = int(first_boot_match.group(1))
        mode = mode_match.group(1)
        variant = row["variant"]
        group = (variant, mode, first_boot)
        all_groups.add(group)
        if row["valid"] == "1":
            valid_boots[group].add((row["run_id"], row["repeat"]))
            valid_rows[group].append(row)

    for group in sorted(all_groups):
        variant, mode, first_boot = group
        group_rows = valid_rows[group]
        print(
            f"variant={variant} mode={mode} first_boot={first_boot} "
            f"n={len(valid_boots[group])}"
        )
        print("metric\t n\tmedian\tmin\tmax")
        for metric in SUMMARY_METRICS:
            values = [
                float(row["value"])
                for row in group_rows
                if row["metric"] == metric
            ]
            if values:
                print(
                    f"{metric}\t{len(values)}\t{statistics.median(values):.6f}"
                    f"\t{min(values):.6f}\t{max(values):.6f}"
                )
            else:
                print(f"{metric}\t0\t-\t-\t-")

        detail_values: dict[str, list[float]] = defaultdict(list)
        for row in group_rows:
            metric = row["metric"]
            if (
                metric.startswith("script:")
                or metric.startswith("initcall:")
                or metric.startswith("module_initcall:")
            ):
                detail_values[metric].append(float(row["value"]))
        details = sorted(
            detail_values.items(),
            key=lambda item: statistics.median(item[1]),
            reverse=True,
        )[:15]
        print("per-script/initcall medians (top 15)")
        if not details:
            print("(none)")
        for metric, values in details:
            print(
                f"{metric}\t{len(values)}\t{statistics.median(values):.6f}"
                f"\t{min(values):.6f}\t{max(values):.6f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    summarize(args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
