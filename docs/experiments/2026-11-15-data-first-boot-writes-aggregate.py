#!/usr/bin/env python3
"""E1の全phaseと完了記録を検査し、boot・idleの差分を集計する。"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys


DEVICES = {"mmcblk0"} | {f"mmcblk0p{i}" for i in range(1, 8)}
MARKER = "e1-complete.json"
RUN_NAME = re.compile(r"([a-z][a-z0-9-]*)-r([1-9][0-9]*)")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_run(directory, windows, seconds, require_marker=True):
    match = RUN_NAME.fullmatch(directory.name)
    if not match:
        raise ValueError("invalid run directory name")
    variant, repeat = match.groups()
    metadata = json.loads((directory / "metadata.json").read_text())
    if (metadata["variant"], metadata["windows"], metadata["seconds"]) != (
        variant, windows, seconds
    ):
        raise ValueError("metadata does not match requested conditions")
    if "MSDPROBE finished" not in (directory / "serial.log").read_text(errors="replace"):
        raise ValueError("missing probe completion marker")
    phases = [("boot", 0)]
    for number in range(1, windows + 1):
        phases.extend([("idle-before", number), ("idle-after", number)])
    phases.extend((phase, 0) for phase in [
        "ram-before", "ram-after", "disk-before", "disk-after"
    ])
    expected = {(phase, number, device) for phase, number in phases for device in DEVICES}
    samples = {}
    with (directory / "raw.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if (row["variant"] != variant or row["run_id"] != directory.name or
                    row["valid"] != "yes" or row["unit"] != "sector512"):
                raise ValueError("invalid row identity or validity")
            note = re.fullmatch(r"phase=([^;]+);uptime=([^;]+);stat=(.*)", row["note"])
            if not note or not row["metric"].endswith(".write_sectors"):
                raise ValueError("invalid metric or phase note")
            key = note[1], int(row["repeat"]), row["metric"].removesuffix(".write_sectors")
            value, uptime = int(row["value"]), float(note[2])
            stat = [int(field) for field in note[3].split()]
            if (key not in expected or key in samples or value < 0 or
                    not math.isfinite(uptime) or uptime < 0 or
                    len(stat) < 11 or stat[6] != value):
                raise ValueError("duplicate, unexpected, or malformed sample")
            samples[key] = uptime, value
    if set(samples) != expected:
        raise ValueError("missing phases or devices")
    for device in DEVICES:
        previous = (0, 0)
        for phase, number in phases:
            current = samples[phase, number, device]
            if current[0] < previous[0] or current[1] < previous[1]:
                raise ValueError("clock or counter moved backwards")
            previous = current
        for number in range(1, windows + 1):
            if (samples["idle-after", number, device][0] -
                    samples["idle-before", number, device][0] < seconds):
                raise ValueError("idle interval too short")
    for device in ["mmcblk0", "mmcblk0p7"]:
        if samples["disk-after", 0, device][1] - samples["disk-before", 0, device][1] < 2048:
            raise ValueError("disk positive control failed")
    marker = {"windows": windows, "seconds": seconds, "sha256": {
        name: digest(directory / name) for name in ["raw.csv", "serial.log", "metadata.json"]
    }}
    if require_marker and json.loads((directory / MARKER).read_text()) != marker:
        raise ValueError("completion record does not match evidence")
    values = [samples["boot", 0, "mmcblk0p7"][1]] + [
        samples["idle-after", n, "mmcblk0p7"][1] - samples["idle-before", n, "mmcblk0p7"][1]
        for n in range(1, windows + 1)
    ]
    return variant, repeat, values, marker


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--windows", type=positive, default=3)
    parser.add_argument("--seconds", type=positive, default=120)
    parser.add_argument("--repeats", type=positive, default=3)
    parser.add_argument("--variants", default="base,grown-fs64,pregrown,pregrown-nolazy,mature")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true", help="検査のみ（完了記録必須）")
    mode.add_argument("--complete", action="store_true", help="成功したrunnerの完了記録を新規作成")
    mode.add_argument("--legacy", action="store_true", help="旧rawを変更せず検査（完了記録なし）")
    args = parser.parse_args()
    try:
        if args.validate or args.complete:
            result = read_run(args.directory, args.windows, args.seconds, not args.complete)
            if args.complete:
                with (args.directory / MARKER).open("x") as stream:
                    json.dump(result[3], stream, sort_keys=True)
                    stream.write("\n")
            return 0
        rows = []
        for directory in sorted(p for p in args.directory.iterdir() if p.is_dir()):
            if ".failed-" in directory.name:
                print(f"skip preserved failed attempt: {directory.name}", file=sys.stderr)
                continue
            rows.append(read_run(directory, args.windows, args.seconds, not args.legacy))
        if not rows:
            raise ValueError("no completed runs")
        expected_runs = {(variant, str(repeat)) for variant in args.variants.split(",")
                         for repeat in range(1, args.repeats + 1)}
        identities = [(variant, repeat) for variant, repeat, _, _ in rows]
        if len(set(identities)) != len(identities) or set(identities) != expected_runs:
            raise ValueError("missing, duplicate, or unexpected runs")
        print("\t".join(["variant", "rep", "boot"] + [
            f"idle{n}" for n in range(1, args.windows + 1)
        ] + ["total"]))
        for variant, repeat, values, _ in rows:
            print("\t".join([variant, repeat] + [str(v) for v in values + [sum(values)]]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"E1 validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
