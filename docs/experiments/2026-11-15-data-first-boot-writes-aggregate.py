#!/usr/bin/env python3
"""E1 集計: output-dwcause/runs/*/raw.csv を variant 別に集約する。
出力: variant,rep,boot,idle1..idle3(各 p7 write_sectors の累積値ではなく差分)"""
import csv, glob, sys, collections

rows = collections.defaultdict(dict)  # (variant, rep) -> {phase/repeat: sectors delta on p7}
for path in sorted(glob.glob("/work/output-dwcause/runs/*/raw.csv")):
    run = path.split("/")[-2]
    with open(path) as f:
        data = list(csv.DictReader(f))
    # phase 順に累積値を持つ p7 行を取り差分化
    seq = []
    for r in data:
        if r["metric"] != "mmcblk0p7.write_sectors":
            continue
        note = r["note"]
        phase = note.split(";")[0].split("=")[1]
        seq.append((phase, int(r["repeat"]), int(r["value"])))
    variant = data[0]["variant"]
    rep = run.rsplit("-r", 1)[-1]
    prev = 0
    for phase, repeat, val in seq:
        if phase.endswith("-after") or phase == "boot":
            delta = val - prev
            rows[(variant, rep)][f"{phase}{repeat}"] = delta
        if not phase.endswith("-before"):
            prev = val

hdr = ["variant", "rep", "boot", "idle1", "idle2", "idle3", "total"]
print("\t".join(hdr))
for (variant, rep), d in sorted(rows.items()):
    boot = d.get("boot0", 0)
    i1, i2, i3 = d.get("idle-after1", 0), d.get("idle-after2", 0), d.get("idle-after3", 0)
    print(f"{variant}\t{rep}\t{boot}\t{i1}\t{i2}\t{i3}\t{boot+i1+i2+i3}")
