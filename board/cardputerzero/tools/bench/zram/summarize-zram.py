#!/usr/bin/env python3
"""Summarize =zram= lines from QEMU serial logs into the experiment CSV."""
import csv
import hashlib
import re
import sys
from pathlib import Path

COLUMNS = ["run", "metric", "value", "unit", "valid", "note"]
MM_STAT = ["orig_data_size", "compr_data_size", "mem_used_total", "mem_limit",
           "mem_used_max", "same_pages", "pages_compacted", "huge_pages",
           "huge_pages_since"]


def rows_for(log: Path):
    run = log.stem
    raw = log.read_bytes()
    text = raw.replace(b"\r", b"").replace(b"\0", b"").decode("utf-8", "replace")
    lines = [ln[ln.index("=zram="):] for ln in text.splitlines() if "=zram=" in ln]
    ready = sum(ln.count("MSD/Linux ready") for ln in text.splitlines())
    finished = any(ln.strip() == "=zram= finished" for ln in lines)
    valid = "1" if finished and ready == 1 else "0"
    out = [(run, "log_sha256", hashlib.sha256(raw).hexdigest(), "", valid, ""),
           (run, "ready_count", str(ready), "count", valid, ""),
           (run, "finished", "1" if finished else "0", "bool", valid, "")]
    for ln in lines:
        if m := re.match(r"=zram= Z1 swapon_rc=(\d+) setup_s=([\d.]+) comp=(.*)$", ln):
            sel = re.search(r"\[(\w+)\]", m.group(3))
            out += [(run, "swapon_rc", m.group(1), "rc", valid, ""),
                    (run, "setup_time", m.group(2), "s", valid, "modprobe..swapon, /proc/uptime"),
                    (run, "comp_algorithm", sel.group(1) if sel else "", "", valid, "")]
        elif m := re.match(r"=zram= Z1 swaps=(\d+),(\d+),(-?\d+)", ln):
            out += [(run, "swap_size", m.group(1), "KiB", valid, ""),
                    (run, "swap_priority", m.group(3), "", valid, "")]
        elif m := re.match(r"=zram= Z2 zswap=(\w+)", ln):
            out.append((run, "zswap_enabled", m.group(1), "", valid, ""))
        elif m := re.match(r"=zram= Z3 load=(\w+) chunks=(\d+) ok=(\w+) mm_stat=([\d,]+)", ln):
            load = m.group(1)
            out += [(run, f"{load}_chunks_4MiB", m.group(2), "count", valid, f"ok={m.group(3)}")]
            vals = m.group(4).split(",")
            for name, v in zip(MM_STAT, vals):
                unit = "count" if name.endswith("pages") or name.endswith("since") or name == "pages_compacted" else "B"
                out.append((run, f"{load}_{name}", v, unit, valid, ""))
            orig, comp = int(vals[0]), int(vals[1])
            if comp:
                out.append((run, f"{load}_ratio", f"{orig / comp:.2f}", "x", valid, "orig/compr"))
        elif m := re.match(r"=zram= Z3 load=(\w+) swaps=(\d+) memavail_kb=(\d+) oom=(\d+)", ln):
            load = m.group(1)
            out += [(run, f"{load}_swap_used", m.group(2), "KiB", valid, ""),
                    (run, f"{load}_memavailable", m.group(3), "KiB", valid, ""),
                    (run, f"{load}_oom_kills_total", m.group(4), "count", valid,
                     "cumulative dmesg 'invoked oom-killer' since boot")]
    return out


def main() -> int:
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(COLUMNS)
    for arg in sys.argv[1:]:
        writer.writerows(rows_for(Path(arg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
