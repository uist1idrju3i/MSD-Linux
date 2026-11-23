#!/usr/bin/env python3
"""Derive template-compatible results from the preserved libgomp trial table."""

import argparse
import csv
import json
import math
from pathlib import Path


LEGACY = ["kind", "variant", "slot", "rootfs_regular_bytes", "squashfs_bytes",
          "module_count", "exit_code", "detail"]
FIELDS = ["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"]
FIELDS += [name for name in LEGACY if name != "variant"]


def export(source, destination, prefix, followup=None, followup_plan=None):
    if bool(followup) != bool(followup_plan):
        raise ValueError("followup and followup plan must be supplied together")
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != LEGACY:
            raise ValueError("unexpected source CSV columns")
        rows = list(reader)
    if not rows:
        raise ValueError("source has no trials")
    output, repeats, ids = [], {}, set()
    metrics = {"pack": ("squashfs_bytes", "bytes"), "qemu": ("module_count", "count"),
               "negative": ("exit_code", "status"), "not_run": ("exit_code", "status")}
    for index, row in enumerate(rows, 1):
        if set(row) != set(LEGACY) or any(value is None for value in row.values()):
            raise ValueError("malformed source row")
        kind, variant, slot = (row[key] for key in ("kind", "variant", "slot"))
        if kind not in metrics:
            raise ValueError("unknown trial kind")
        metric, unit = metrics[kind]
        for name in ("rootfs_regular_bytes", "squashfs_bytes", "module_count", "exit_code"):
            if row[name]:
                int(row[name])
        if kind != "not_run" and (not row[metric] or not row["exit_code"]):
            raise ValueError("executed trial has no result")
        key = (kind, "before" if variant == "before-aa" else variant, slot)
        repeats[key] = repeats.get(key, 0) + 1
        run_id = "-".join((prefix, kind, variant, slot or "none"))
        if run_id in ids:
            raise ValueError("duplicate run ID")
        ids.add(run_id)
        expected = "1" if kind == "negative" else "0"
        valid = kind != "not_run" and row["exit_code"] == expected
        note = f"source row {index}; " + ("expected failure" if kind == "negative" else
                                         "not executed" if kind == "not_run" else "observed result")
        output.append(dict(row, run_id=run_id, repeat=repeats[key], metric=metric,
                           value=row[metric], unit=unit, valid=str(valid).lower(), note=note))
    if followup:
        planned = json.loads(followup_plan.read_text())
        if (not isinstance(planned, dict) or not planned or
                any(type(repeat) is not int or repeat < 1 for repeat in planned.values())):
            raise ValueError("followup plan must declare run IDs and positive repeat numbers")
        seen = set()
        with followup.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS[:8]:
                raise ValueError("unexpected followup CSV columns")
            for row in reader:
                if set(row) != set(FIELDS[:8]) or any(v is None for v in row.values()):
                    raise ValueError("malformed followup row")
                if (row["run_id"] not in planned or row["run_id"] in ids or
                        int(row["repeat"]) != planned[row["run_id"]] or
                        row["valid"] not in ("true", "false") or
                        (row["valid"] == "true" and not row["value"]) or
                        (not row["value"] and not row["note"].startswith("not run:")) or
                        (row["value"] and not math.isfinite(float(row["value"])))):
                    raise ValueError("invalid followup trial or duplicate run ID")
                ids.add(row["run_id"])
                seen.add(row["run_id"])
                output.append(dict.fromkeys(FIELDS, "") | row)
        if seen != set(planned):
            raise ValueError("incomplete followup; missing planned run IDs: " + ", ".join(sorted(set(planned) - seen)))
    with destination.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(f"CSV derivation: {len(output)} rows; all source columns retained; unique run IDs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--followup", type=Path)
    parser.add_argument("--followup-plan", type=Path)
    args = parser.parse_args()
    export(args.input, args.out, args.run_prefix, args.followup, args.followup_plan)
