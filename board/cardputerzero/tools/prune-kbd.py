#!/usr/bin/env python3
"""Keep loadkeys and reject references before pruning the known kbd tool set."""

import argparse
from pathlib import Path
import re


TOOLS = frozenset("""
mapscrn loadunimap dumpkeys loadkeys showkey setfont showconsolefont setleds
setmetamode kbd_mode psfxtable fgconsole kbdrate chvt deallocvt openvt kbdinfo
setvtrgb getkeycodes setkeycodes resizecons setlogcons setvesablank getunimap
clrunimap outpsfheader setpalette screendump spawn_console spawn_login
unicode_start unicode_stop psfaddtable psfgettable psfstriptable vlock
""".split())
KEEP = frozenset({"loadkeys"})
DIRECTORIES = ("bin", "sbin", "usr/bin", "usr/sbin")


def prune(target):
    if not target.is_dir():
        raise ValueError("target directory does not exist")
    cohort = {target / directory / name for directory in DIRECTORIES for name in TOOLS}
    removed = [p for p in sorted(cohort) if p.name not in KEEP and (p.is_file() or p.is_symlink())
               and not (p.is_symlink() and p.readlink().name == "busybox")]
    if removed and not any((target / directory / "loadkeys").is_file() for directory in DIRECTORIES):
        raise ValueError("refusing kbd pruning without retained loadkeys")
    names = {p.name for p in removed}
    if not names:
        return []
    pattern = re.compile(rb"(?<![A-Za-z0-9_])(?:" + b"|".join(re.escape(n.encode()) for n in sorted(names))
                         + rb")(?![A-Za-z0-9_])")
    consumers = []
    for path in sorted(target.rglob("*")):
        if path in cohort or path.name == "busybox":
            continue
        data = str(path.readlink()).encode() if path.is_symlink() else path.read_bytes() if path.is_file() else b""
        if pattern.search(data):
            consumers.append(str(path.relative_to(target)))
    if consumers:
        raise ValueError("refusing kbd pruning; references: " + ", ".join(consumers))
    for path in removed:
        path.unlink()
    return [str(path.relative_to(target)) for path in removed]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    prune(args.target)
