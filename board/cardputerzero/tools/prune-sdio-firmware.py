#!/usr/bin/env python3
"""Keep both documented CM0 wireless families and their firmware link targets."""

import argparse
from pathlib import Path
import re


REQUIRED = frozenset(
    [f"brcm/brcmfmac43439-sdio.{suffix}" for suffix in ("bin", "txt", "clm_blob")]
    + [f"brcm/brcmfmac43430-sdio.{suffix}" for suffix in ("bin", "txt", "clm_blob")]
    + [f"brcm/brcmfmac{chip}-sdio.raspberrypi,0-compute-module.{suffix}"
       for chip in ("43430", "43436s") for suffix in ("bin", "txt")]
    + ["brcm/brcmfmac43436s-sdio.bin", "brcm/brcmfmac43436s-sdio.txt",
       "brcm/brcmfmac43436s-sdio.nolpo.txt"]
    + [f"brcm/{name}.hcd" for name in ("BCM4343A2", "BCM43430A1", "BCM43430B0")])
OPTIONAL = frozenset(
    [f"brcm/brcmfmac{chip}-sdio.raspberrypi,0-compute-module.{suffix}"
     for chip in ("43439", "43430", "43436s") for suffix in ("bin", "txt", "clm_blob")]
    + [f"brcm/{name}.raspberrypi,0-compute-module.hcd"
       for name in ("BCM4343A2", "BCM43430A1", "BCM43430B0", "BCM")]
    + ["brcm/BCM.hcd"]) - REQUIRED
OWNED = {"brcm": re.compile(r"(?:brcmfmac.*|BCM.*\.hcd)\Z"),
         "cypress": re.compile(r"cyfmac.*\Z"),
         "synaptics": re.compile(r"SYN.*\.hcd\Z")}


def prune(target):
    if not target.is_dir():
        raise ValueError("target directory does not exist")
    base = target / "lib/firmware"
    if not base.resolve().is_relative_to(target.resolve()):
        raise ValueError("firmware directory escapes target")
    for directory in OWNED:
        parent = base / directory
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError("unexpected firmware directory: " + str(parent))
    keep = set()

    def retain(path, active):
        if path in active:
            raise ValueError("firmware symlink cycle: " + str(path))
        if path in keep:
            return
        if not path.is_relative_to(base):
            raise ValueError("firmware symlink escapes firmware directory: " + str(path))
        if path.is_symlink():
            link = path.readlink()
            if link.is_absolute():
                raise ValueError("absolute firmware symlink: " + str(path))
            joined = path.parent / link
            parts = []
            for part in joined.relative_to(base).parts:
                if part == "..":
                    if not parts:
                        raise ValueError("firmware symlink escapes firmware directory: " + str(path))
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            retain(base.joinpath(*parts), active | {path})
        elif not path.resolve().is_relative_to(base.resolve()):
            raise ValueError("firmware target escapes firmware directory: " + str(path))
        elif not path.is_file() or path.stat().st_size == 0:
            raise ValueError("missing or empty required firmware: " + str(path))
        keep.add(path)

    for name in sorted(REQUIRED):
        retain(base / name, set())
    for name in sorted(OPTIONAL):
        path = base / name
        if path.exists() or path.is_symlink():
            retain(path, set())
    removed = []
    for directory, pattern in OWNED.items():
        for path in sorted((base / directory).glob("*")):
            if path in keep or not pattern.fullmatch(path.name):
                continue
            if not path.is_file() and not path.is_symlink():
                raise ValueError("unexpected firmware entry: " + str(path))
            removed.append(path)
    for path in removed:
        path.unlink()
    return [str(path.relative_to(target)) for path in removed]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    prune(args.target)
