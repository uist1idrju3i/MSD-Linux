#!/usr/bin/env python3
"""Summarize =lynis= lines from QEMU serial logs into the experiment CSV."""
import csv
import hashlib
import re
import sys
from pathlib import Path

COLUMNS = ["run", "kind", "id", "value", "valid", "note"]


def rows_for(log: Path):
    run = log.stem
    raw = log.read_bytes()
    text = raw.replace(b"\r", b"").replace(b"\0", b"").decode("utf-8", "replace")
    # Kernel printk lines can land in the middle of a long =lynis= line; rejoin it.
    text = re.sub(r"(?m)(?<=\S)\[ *\d+\.\d+\] [^\n]*\n", "", text)
    lines = [ln[ln.index("=lynis= ") + 8:] for ln in text.splitlines() if "=lynis= " in ln]
    finished = "finished" in lines
    valid = "1" if finished and "rc=0" in lines else "0"
    out = [(run, "meta", "log_sha256", hashlib.sha256(raw).hexdigest(), valid, ""),
           (run, "meta", "finished", "1" if finished else "0", valid, "")]
    for ln in lines:
        if m := re.match(r"(rc|lynis_version|lynis_tests_done|hardening_index|skipped_tests)=(.*)$", ln):
            out.append((run, "meta", m.group(1), m.group(2), valid, ""))
        elif m := re.match(r"tests_executed=(.*)$", ln):
            ids = [t for t in m.group(1).split("|") if t]
            out += [(run, "meta", "tests_executed_count", str(len(ids)), valid, ""),
                    (run, "meta", "tests_executed_sha256",
                     hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest(), valid,
                     "SHA-256 of sorted IDs joined by |")]
        elif m := re.match(r"(warning|suggestion)\[\]=([A-Z]+-\d+)\|([^|]*)\|", ln):
            out.append((run, m.group(1), m.group(2), m.group(3), valid, ""))
        elif m := re.match(r"sysctl Result: sysctl key (\S+) .*Expected=(\S+), Real=(\S+)", ln):
            out.append((run, "sysctl", m.group(1), m.group(3), valid, f"profile expects {m.group(2)}"))
    return out


def main() -> int:
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(COLUMNS)
    for arg in sys.argv[1:]:
        writer.writerows(rows_for(Path(arg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
