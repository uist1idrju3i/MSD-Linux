#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path
from typing import TypedDict

CSV_COLUMNS = (
    "run_id",
    "variant",
    "repeat",
    "metric",
    "value",
    "unit",
    "valid",
    "note",
)
TIMESTAMP_RE = re.compile(r"^\[\s*(\d+\.\d+)\]\s?(.*)$")
SCRIPT_BEGIN_RE = re.compile(r"^msd-boottime: begin (\S+)$")
SCRIPT_END_RE = re.compile(r"^msd-boottime: end (\S+) status=(-?\d+)$")
T_DATA_RE = re.compile(r"EXT4-fs \(mmcblk0p7\): mounted filesystem")
BUILTIN_INITCALL_RE = re.compile(
    r"^initcall (\S+) returned (-?\d+) after (\d+) usecs$"
)
MODULE_INITCALL_RE = re.compile(
    r"^initcall (\S+) \[(\S+)\] returned (-?\d+) after (\d+) usecs$"
)


class CsvRow(TypedDict):
    run_id: str
    variant: str
    repeat: str
    metric: str
    value: str
    unit: str
    valid: str
    note: str


def format_seconds(value: float) -> str:
    return f"{value:.6f}"


def parse_text(
    text: str,
    *,
    run_id: str,
    variant: str,
    mode: str,
    repeat: int,
    first_boot: int,
    wall_seconds: float,
    exit_status: int,
    log_sha256: str,
) -> tuple[list[CsvRow], list[str]]:
    lines = [line.lstrip("\x00") for line in text.splitlines()]
    begin_index: int | None = None
    end_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == "msd-boottime: dmesg begin":
            begin_index = index
            break
    if begin_index is not None:
        for index in range(begin_index + 1, len(lines)):
            if lines[index].strip() == "msd-boottime: dmesg end":
                end_index = index
                break

    reasons: list[str] = []

    def invalidate(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    timestamped: list[tuple[float, str]] = []
    if begin_index is None or end_index is None:
        invalidate("missing_dmesg_begin_or_end")
    else:
        for line in lines[begin_index + 1 : end_index]:
            if not line.startswith("=dmesg= "):
                continue
            line = line[len("=dmesg= ") :]
            match = TIMESTAMP_RE.match(line)
            if match is not None:
                timestamped.append((float(match.group(1)), match.group(2)))

    if exit_status != 0:
        invalidate("exit_status_nonzero")
    if begin_index is not None and end_index is not None:
        if (
            not timestamped
            or timestamped[0][0] != 0.0
            or not timestamped[0][1].startswith("Booting Linux")
        ):
            invalidate("ring_buffer_loss")

    base_metrics: dict[str, float] = {}
    script_begins: dict[str, list[float]] = {}
    script_ends: dict[str, list[tuple[float, int]]] = {}
    builtin_initcalls: list[tuple[str, int]] = []
    module_initcalls: list[tuple[str, str, int]] = []

    for timestamp, message in timestamped:
        if "Run /sbin/init as init process" in message:
            base_metrics.setdefault("t_init", timestamp)
        if "t_rcs_begin" not in base_metrics and message == "msd-boottime: rcS begin":
            base_metrics["t_rcs_begin"] = timestamp
        if "t_data" not in base_metrics and T_DATA_RE.search(message):
            base_metrics["t_data"] = timestamp
        if "t_ready" not in base_metrics and message == "MSD/Linux ready":
            base_metrics["t_ready"] = timestamp

        begin_match = SCRIPT_BEGIN_RE.fullmatch(message)
        if begin_match is not None:
            name = begin_match.group(1)
            if name != "S99zz-boottime-dump":
                script_begins.setdefault(name, []).append(timestamp)
            continue

        end_match = SCRIPT_END_RE.fullmatch(message)
        if end_match is not None:
            name = end_match.group(1)
            if name != "S99zz-boottime-dump":
                script_ends.setdefault(name, []).append(
                    (timestamp, int(end_match.group(2)))
                )
            continue

        module_match = MODULE_INITCALL_RE.fullmatch(message)
        if module_match is not None:
            function, module, _status, usecs_text = module_match.groups()
            module_initcalls.append((module, function, int(usecs_text)))
            continue

        builtin_match = BUILTIN_INITCALL_RE.fullmatch(message)
        if builtin_match is not None:
            function, _status, usecs_text = builtin_match.groups()
            builtin_initcalls.append((function, int(usecs_text)))

    required_metrics = (
        ("t_init", "missing_t_init"),
        ("t_ready", "missing_t_ready"),
        ("t_rcs_begin", "missing_t_rcs_begin"),
        ("t_data", "missing_t_data"),
    )
    for metric, reason in required_metrics:
        if metric not in base_metrics:
            invalidate(reason)

    script_rows: list[tuple[str, str, str]] = []
    for name in sorted(set(script_begins) | set(script_ends)):
        starts = script_begins.get(name, [])
        ends = script_ends.get(name, [])
        if len(starts) > len(ends):
            invalidate(f"script_missing_end:{name}")
        if len(ends) > len(starts):
            invalidate(f"script_missing_begin:{name}")
        for _timestamp, status in ends:
            script_rows.append((f"script_status:{name}", str(status), "code"))
        for start_time, (end_time, _status) in zip(starts, ends):
            script_rows.append(
                (
                    f"script:{name}",
                    format_seconds(end_time - start_time),
                    "s",
                )
            )

    builtin_rows: list[tuple[str, str, str]] = []
    if builtin_initcalls:
        total_usecs = sum(usecs for _function, usecs in builtin_initcalls)
        builtin_rows.extend(
            [
                ("initcall_count", str(len(builtin_initcalls)), "count"),
                ("initcall_total", format_seconds(total_usecs / 1_000_000), "s"),
            ]
        )
        for function, usecs in builtin_initcalls:
            if usecs >= 50_000:
                function_name = function.split("+0x", 1)[0]
                builtin_rows.append(
                    (
                        f"initcall:{function_name}",
                        format_seconds(usecs / 1_000_000),
                        "s",
                    )
                )

    module_rows: list[tuple[str, str, str]] = []
    if module_initcalls:
        total_usecs = sum(usecs for _module, _function, usecs in module_initcalls)
        module_rows.extend(
            [
                ("module_initcall_count", str(len(module_initcalls)), "count"),
                (
                    "module_initcall_total",
                    format_seconds(total_usecs / 1_000_000),
                    "s",
                ),
            ]
        )
        for module, function, usecs in module_initcalls:
            if usecs >= 50_000:
                function_name = function.split("+0x", 1)[0]
                module_rows.append(
                    (
                        f"module_initcall:{module}:{function_name}",
                        format_seconds(usecs / 1_000_000),
                        "s",
                    )
                )

    valid = "0" if reasons else "1"
    note = f"first_boot={first_boot};mode={mode}"
    if reasons:
        note += ";" + ";".join(f"invalid:{reason}" for reason in reasons)

    rows: list[CsvRow] = []

    def add_row(metric: str, value: str, unit: str) -> None:
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "repeat": str(repeat),
                "metric": metric,
                "value": value,
                "unit": unit,
                "valid": valid,
                "note": note,
            }
        )

    for metric in ("t_init", "t_data", "t_ready", "t_rcs_begin"):
        if metric in base_metrics:
            add_row(metric, format_seconds(base_metrics[metric]), "s")
    for metric, value, unit in script_rows + builtin_rows + module_rows:
        add_row(metric, value, unit)
    add_row("wall", format_seconds(wall_seconds), "s")
    add_row("exit_status", str(exit_status), "code")
    add_row("log_sha256", log_sha256, "sha256")
    return rows, reasons


def append_csv(path: Path, rows: list[CsvRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--mode", required=True, choices=("icount", "tcg"))
    parser.add_argument("--repeat", required=True, type=int)
    parser.add_argument("--first-boot", required=True, type=int, choices=(0, 1))
    parser.add_argument("--wall-seconds", required=True, type=float)
    parser.add_argument("--exit-status", required=True, type=int)
    args = parser.parse_args()

    try:
        log_bytes = args.log.read_bytes()
    except OSError as error:
        print(f"Could not read serial log {args.log}: {error}", file=sys.stderr)
        return 2

    rows, reasons = parse_text(
        log_bytes.decode("utf-8", errors="replace"),
        run_id=args.run_id,
        variant=args.variant,
        mode=args.mode,
        repeat=args.repeat,
        first_boot=args.first_boot,
        wall_seconds=args.wall_seconds,
        exit_status=args.exit_status,
        log_sha256=hashlib.sha256(log_bytes).hexdigest(),
    )
    try:
        append_csv(args.csv, rows)
    except OSError as error:
        print(f"Could not write CSV {args.csv}: {error}", file=sys.stderr)
        return 2

    if reasons:
        print(
            f"INVALID: run_id={args.run_id} repeat={args.repeat} "
            f"reasons={','.join(reasons)}"
        )
    else:
        print(f"VALID: run_id={args.run_id} repeat={args.repeat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
