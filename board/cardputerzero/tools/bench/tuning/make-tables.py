#!/usr/bin/env python3
"""Merge dump-tunables.py CSVs into the experiment-record CSV and a Markdown
appendix that lists every sysctl, the mmcblk0 queue, CPU/sysfs and module
parameter value. Usage: make-tables.py OUT_CSV OUT_MD RUN_ID=dump.csv ..."""
import csv, sys
from pathlib import Path

VARIANTS = {"a1": "slot-a-1g", "a2": "slot-a-1g", "b1": "slot-b-1g", "m1": "slot-a-mem512m"}


def load(path):
    return {(r["kind"], r["path"]): r for r in csv.DictReader(open(path))}


def cell(text):
    text = text.replace("|", "\\|").strip()
    return f"`{text}`" if text else "（空）"


def main():
    out_csv, out_md, *runs = sys.argv[1:]
    data = {}
    for item in runs:
        run_id, path = item.split("=", 1)
        data[run_id] = load(path)
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"])
        for run_id, rows in data.items():
            repeat = 2 if run_id == "a2" else 1
            for (kind, path), r in rows.items():
                if kind in {"PROC", "ULIMIT", "MODULES"}:
                    continue
                w.writerow([run_id, VARIANTS[run_id], repeat, path, r["value"], kind.lower(), "yes",
                            f"mode={r['mode']}" if r["mode"] else ""])
    base, small = data["a1"], data.get("m1", {})
    lines = []
    sections = [
        ("sysctl（`/proc/sys`）", lambda k: k[0] == "SYSCTL"),
        ("ブロックデバイス `mmcblk0`（queue、iosched、bdi）", lambda k: k[0] == "BLOCK" and "/mmcblk0/" in k[1]),
        ("CPU（cpuidle、脆弱性対策の状態）", lambda k: k[0] == "CPU"),
        ("sysfs（mm、power、thermal）", lambda k: k[0] == "SYSFS"),
        ("モジュールパラメーター（`/sys/module/*/parameters`）", lambda k: k[0] == "MODPARAM"),
    ]
    for title, pred in sections:
        keys = sorted(k for k in base if pred(k))
        lines += [f"## {title}", "", f"{len(keys)} 項目です。", "",
                  "| パス | 値（1 GiB） | 値（`mem=512M`） |", "|---|---|---|"]
        for k in keys:
            r = base[k]
            other = small.get(k)
            if other is None:
                second = "（なし）" if small else "-"
            elif other["value"] == r["value"]:
                second = "同じ"
            else:
                second = cell(other["value"])
            lines.append(f"| `{k[1]}` | {cell(r['value'])} | {second} |")
        lines.append("")
    Path(out_md).write_text("\n".join(lines))


if __name__ == "__main__":
    main()
