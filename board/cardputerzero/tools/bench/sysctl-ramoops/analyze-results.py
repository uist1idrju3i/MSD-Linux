#!/usr/bin/env python3
"""Validate the S21 result matrix and print condition summaries."""

import argparse
import csv
import re
import statistics
import sys
from pathlib import Path


EXPECTED_COUNTS = {
    "Y0-boot": 5,
    "Y1-boot": 5,
    "Y1-test-ab": 1,
    "Y1-powerfail": 5,
    "Y2-powerfail": 5,
    "P0": 5,
    "P1": 5,
    "R0": 5,
    "R1": 5,
}

EXPECTED_SYSCTLS = {
    "kernel.kptr_restrict": "2",
    "kernel.dmesg_restrict": "1",
    "kernel.sysrq": "32",
    "fs.protected_fifos": "2",
    "fs.protected_regular": "2",
    "fs.protected_hardlinks": "1",
    "fs.protected_symlinks": "1",
    "net.core.bpf_jit_harden": "2",
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.default.accept_redirects": "0",
    "net.ipv4.conf.all.send_redirects": "0",
    "net.ipv4.conf.default.accept_source_route": "0",
    "net.ipv4.conf.all.rp_filter": "1",
    "net.ipv4.conf.all.log_martians": "1",
    "net.ipv4.conf.default.log_martians": "1",
}


def sysctls_match(values: str) -> bool:
    observed = {}
    for item in values.split(";"):
        match = re.fullmatch(r"([^=]+)=([^ (]+)\(status=([0-9]+)\)", item)
        if match:
            observed[match.group(1)] = (match.group(2), match.group(3))
    return all(
        observed.get(key) == (value, "0")
        for key, value in EXPECTED_SYSCTLS.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--all-columns", action="store_true")
    args = parser.parse_args()

    with args.csv.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise SystemExit("CSV has no header")
        rows = list(reader)
    if not rows:
        raise SystemExit("CSV has no result rows")
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise SystemExit(f"malformed CSV row {row_number}")
        for column, value in row.items():
            if not isinstance(column, str) or not isinstance(value, str):
                raise SystemExit(f"unreadable column in row {row_number}: {column}")
        if args.all_columns:
            print(f"row={row_number} " + " ".join(f"{key}={value}" for key, value in row.items()))

    failed = False
    for condition, expected in EXPECTED_COUNTS.items():
        selected = [row for row in rows if row["condition"] == condition]
        if condition == "R1":
            replacement = [
                row
                for row in selected
                if row["run_id"].startswith("s21-R1-amendment1-")
            ]
            if replacement:
                initial = [row for row in selected if row not in replacement]
                print(
                    f"R1 initial incomplete attempts={len(initial)} "
                    f"amendment1 replacement trials={len(replacement)}"
                )
                if len(initial) != 5 or len(replacement) != expected:
                    failed = True
                selected = replacement
        passed = sum(row["criteria_result"] == "pass" for row in selected)
        expected_negative = sum(
            row["criteria_result"] == "expected-negative" for row in selected
        )
        valid = sum(row["valid"] == "1" for row in selected)
        times = [
            float(row["ready_seconds"])
            for row in selected
            if row["ready_seconds"]
        ]
        times.extend(
            float(row["marker_to_reset_seconds"])
            for row in selected
            if row["marker_to_reset_seconds"]
        )
        timing = ""
        if times:
            timing = (
                f" median={statistics.median(times):.3f}s"
                f" range={min(times):.3f}-{max(times):.3f}s"
            )
        print(
            f"{condition}: n={len(selected)}/{expected} valid={valid} "
            f"pass={passed} expected-negative={expected_negative}{timing}"
        )
        if len(selected) != expected:
            failed = True
        if condition == "Y0-boot":
            if valid != expected:
                failed = True
        elif condition == "Y1-boot":
            if passed != expected or any(
                not sysctls_match(row["sysctl_readbacks"])
                or row["running_sysctl"] != "OK"
                or row["serial_check_exit"] != "0"
                or row["ready"] != "yes"
                for row in selected
            ):
                failed = True
        elif condition == "Y1-powerfail":
            if passed != expected or any(
                row["powerfail_event"] != "yes"
                or row["powerfail_sysrq_u_remount"] != "yes"
                for row in selected
            ):
                failed = True
        elif condition == "Y2-powerfail":
            if expected_negative != expected or valid != expected:
                failed = True
            if any(row["powerfail_sysrq_u_remount"] != "no" for row in selected):
                failed = True
        elif passed != expected:
            failed = True

    if failed:
        print("S21 matrix is incomplete or does not meet the preregistered criteria.", file=sys.stderr)
        return 1
    print("All preregistered condition counts and criteria match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
