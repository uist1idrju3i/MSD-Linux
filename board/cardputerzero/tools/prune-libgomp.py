#!/usr/bin/env python3
"""Remove the target OpenMP runtime only when no literal consumer remains."""

from pathlib import Path
import sys


def prune(target):
    if not target.is_dir():
        raise ValueError("target directory does not exist")
    libraries = {p for directory in (target / "lib", target / "usr/lib")
                 for p in directory.glob("libgomp.so*") if p.is_file() or p.is_symlink()}
    consumers = []
    for path in sorted(target.rglob("*")):
        if path in libraries:
            continue
        if path.is_symlink():
            used = "libgomp" in str(path.readlink())
        else:
            used = path.is_file() and b"libgomp" in path.read_bytes()
        if used:
            consumers.append(str(path.relative_to(target)))
    if consumers:
        raise ValueError("Refusing libgomp removal: consumers: " + ", ".join(consumers))
    for library in sorted(libraries):
        library.unlink()


if __name__ == "__main__":
    prune(Path(sys.argv[1]))
