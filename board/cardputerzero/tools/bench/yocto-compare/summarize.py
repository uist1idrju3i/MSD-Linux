#!/usr/bin/env python3
"""Validate boot comparisons and summarize successful normal boots only."""

import argparse
import csv
import math
from pathlib import Path
import re
import statistics
import sys


COLUMNS = "condition,mode,boot,first_boot,t_root,t_init,t_ready,login,wall_login_s,result".split(",")
METRICS = ("t_root", "t_init", "t_ready", "wall_login_s")
RESULTS = {"pass", "timeout", "exited", "missing_t_ready", "missing_timestamps"}


def load_rows(path):
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != COLUMNS:
            raise ValueError("unexpected or duplicate CSV columns")
        rows = list(reader)
    if not rows:
        raise ValueError("CSV has no results")
    seen = set()
    for line, row in enumerate(rows, 2):
        def invalid(message):
            raise ValueError(f"row {line}: {message}")

        if None in row or any(value is None for value in row.values()):
            invalid("wrong number of fields")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", row["condition"]):
            invalid("invalid condition")
        if row["mode"] not in {"icount", "tcg"} or not re.fullmatch(r"0|[1-9][0-9]*", row["boot"]):
            invalid("invalid mode or boot number")
        boot = int(row["boot"])
        if row["first_boot"] != ("1" if boot == 0 else "0"):
            invalid("first_boot does not match boot number")
        key = (row["condition"], row["mode"], boot)
        if key in seen:
            invalid("duplicate condition/mode/boot")
        seen.add(key)
        if row["result"] not in RESULTS or row["login"] not in {"0", "1"}:
            invalid("invalid result or login flag")
        for metric in METRICS:
            value = row[metric]
            if not value:
                if row["result"] == "pass":
                    invalid(f"pass is missing {metric}")
                continue
            try:
                number = float(value)
            except ValueError:
                invalid(f"invalid {metric}")
            if not math.isfinite(number) or number < 0:
                invalid(f"nonfinite or negative {metric}")
        if row["result"] == "pass":
            if row["login"] != "1":
                invalid("pass has no login")
            if not float(row["t_root"]) <= float(row["t_init"]) <= float(row["t_ready"]):
                invalid("timestamps are out of order")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--min-runs", type=int, default=5, help="minimum successful normal boots per group")
    args = parser.parse_args()
    if args.min_runs < 1:
        parser.error("--min-runs must be positive")
    try:
        rows = load_rows(args.csv)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Invalid comparison: {exc}", file=sys.stderr)
        return 2
    groups = {}
    for row in rows:
        groups.setdefault((row["condition"], row["mode"]), []).append(row)
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["condition", "mode", "n", "pass", *(
        f"{metric}_{stat}" for metric in METRICS for stat in ("median", "min", "max")
    )])
    failed = False
    for (condition, mode), group in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        normal = [row for row in group if row["first_boot"] == "0"]
        passed = [row for row in normal if row["result"] == "pass"]
        boots = sorted(int(row["boot"]) for row in group)
        complete = boots == list(range(len(boots)))
        if not complete or len(passed) < args.min_runs or any(row["result"] != "pass" for row in group):
            print(f"Incomplete comparison: {condition}/{mode}: {len(passed)}/{len(normal)} normal boots passed; "
                  f"minimum={args.min_runs}, contiguous from boot 0={complete}", file=sys.stderr)
            failed = True
        output = [condition, mode, len(normal), len(passed)]
        for metric in METRICS:
            values = [float(row[metric]) for row in passed]
            output.extend([f"{value:.6f}" for value in (
                statistics.median(values), min(values), max(values)
            )] if values else ["", "", ""])
        writer.writerow(output)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
