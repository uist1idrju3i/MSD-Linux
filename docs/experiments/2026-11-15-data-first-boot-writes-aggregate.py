#!/usr/bin/env python3
"""E1 集計: runs dir 以下の */raw.csv を variant 別に集約する。
使い方: python3 aggregate.py [RUNS_DIR]（既定 /work/output-dwcause/runs）
出力: variant,rep,boot,idle1..idleN(各区間は after-before の差分、
区間数はデータから検出)。
raw.csv を持たない run dir は警告して除外する。欠けた phase は 0 にせず
空欄にして区別する。"""
import csv, glob, sys, collections

runs_dir = sys.argv[1] if len(sys.argv) > 1 else "/work/output-dwcause/runs"
rows = collections.defaultdict(dict)  # (variant, rep) -> {column: sectors}
missing = []
for path in sorted(glob.glob(runs_dir + "/*")):
    run = path.split("/")[-1]
    csv_path = path + "/raw.csv"
    try:
        data = list(csv.DictReader(open(csv_path)))
    except OSError:
        missing.append(run)
        continue
    # phase 順の累積値から、各区間は直前 before と after の差を取る
    seq = []
    for r in data:
        if r["metric"] != "mmcblk0p7.write_sectors":
            continue
        phase = r["note"].split(";")[0].split("=")[1]
        seq.append((phase, int(r["repeat"]), int(r["value"])))
    variant = data[0]["variant"]
    rep = run.rsplit("-r", 1)[-1]
    cumulative = {}
    for phase, repeat, val in seq:
        cumulative[(phase, repeat)] = val
        if phase == "boot":
            rows[(variant, rep)]["boot"] = val
        elif phase == "idle-after":
            # ram/disk probeのwindowは記録の定義上totalに含めない
            before = cumulative.get(("idle-before", repeat))
            if before is None:
                rows[(variant, rep)][f"idle{repeat}"] = None
            else:
                rows[(variant, rep)][f"idle{repeat}"] = val - before
    # idle-beforeだけある欠損区間も列として残す（after欠損は空欄）
    for (phase, repeat) in cumulative:
        if phase == "idle-before":
            rows[(variant, rep)].setdefault(f"idle{repeat}", None)

if missing:
    print("warn: raw.csvがないrun dirを除外:", ", ".join(missing), file=sys.stderr)

def cell(v):
    return "" if v is None else str(v)

idle_ns = sorted({k for d in rows.values() for k in d if k.startswith("idle")},
                 key=lambda k: int(k[4:]))
hdr = ["variant", "rep", "boot"] + idle_ns + ["total"]
print("\t".join(hdr))
for (variant, rep), d in sorted(rows.items()):
    parts = [d.get("boot")] + [d.get(k) for k in idle_ns]
    total = "" if any(p is None for p in parts) else str(sum(parts))
    print("\t".join([variant, rep] + [cell(p) for p in parts] + [total]))
