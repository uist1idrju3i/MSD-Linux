#!/usr/bin/env python3
"""Summarize results.csv from run-compare.sh: normal boots only (first_boot=0)."""
import csv
import statistics
import sys

rows = list(csv.DictReader(open(sys.argv[1])))
groups = {}
for r in rows:
    if r["first_boot"] != "0":
        continue
    groups.setdefault((r["condition"], r["mode"]), []).append(r)
metrics = ("t_root", "t_init", "t_ready", "wall_login_s")
print("condition,mode,n,pass," + ",".join(f"{m}_median,{m}_min,{m}_max" for m in metrics))
for (cond, mode), rs in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
    out = [cond, mode, str(len(rs)), str(sum(r["result"] == "pass" for r in rs))]
    for m in metrics:
        vals = [float(r[m]) for r in rs if r[m]]
        out += [f"{statistics.median(vals):.6f}", f"{min(vals):.6f}", f"{max(vals):.6f}"] if vals else ["", "", ""]
    print(",".join(out))
