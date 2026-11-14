import csv, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("wi_run", "/work/board/cardputerzero/tools/bench/write-inventory/run.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
run_dir = Path("/work/output-dwcause/runs/mature-r1")
text = (run_dir/"serial.log").read_bytes().decode(errors="replace")
windows = 3
samples = m.parse_samples(text, windows)
for phase, count in [("idle", windows), ("ram",1), ("disk",1)]:
    for repeat in (range(1,count+1) if phase=="idle" else [0]):
        deltas={}
        for device in sorted(m.DEVICES):
            before=samples[f"{phase}-before",repeat,device]; after=samples[f"{phase}-after",repeat,device]
            assert after[0]>=before[0] and after[1]>=before[1]
            if phase=="idle": assert after[0]-before[0]>=120
            deltas[device]=after[1]-before[1]
        if phase=="disk": assert deltas["mmcblk0p7"]>=2048
        print("mature",phase,"repeat=",repeat,"sectors=",deltas,sep="")
with (run_dir/"raw.csv").open("x",newline="") as s:
    w=csv.DictWriter(s,fieldnames=m.FIELDS,lineterminator="\n"); w.writeheader()
    for (phase,repeat,device),(uptime,sectors,raw) in samples.items():
        w.writerow(dict(run_id=run_dir.name,variant="mature",repeat=repeat,metric=f"{device}.write_sectors",value=sectors,unit="sector512",valid="yes",note=f"phase={phase};uptime={uptime};stat={raw}"))
print("salvaged mature-r1")
