#!/usr/bin/env python3
"""Build and verify the image-defined, unformatted data region."""

import argparse
import json
from pathlib import Path
import subprocess


BOARD = Path(__file__).resolve().parent


def initial_bytes():
    key, value = (BOARD / "data-layout.conf").read_text().strip().split("=")
    if key != "MSD_DATA_INITIAL_BYTES" or not value.isdecimal():
        raise ValueError("invalid data layout definition")
    size = int(value)
    if size < 512 * 1024 * 1024 or size % 512:
        raise ValueError("data region must be sector aligned and at least 512 MiB")
    return size


def prepare(directory):
    size = initial_bytes()
    with (directory / "data.zero").open("wb") as stream:
        stream.truncate(size)
    template = (BOARD / "genimage.cfg").read_text()
    token = "@MSD_DATA_INITIAL_BYTES@"
    if template.count(token) != 1:
        raise ValueError("missing or duplicate data layout token")
    (directory / "genimage.cfg").write_text(template.replace(token, str(size)))
    allocated = (directory / "data.zero").stat().st_blocks * 512
    if allocated >= size:
        raise ValueError("data.zero was not created sparsely")
    print(f"OK: data.zero logical_bytes={size} allocated_bytes={allocated}")


def check(image):
    table = json.loads(subprocess.check_output(["sfdisk", "--json", str(image)]))["partitiontable"]
    parts = table["partitions"]
    if table["label"] != "dos" or table["sectorsize"] != 512 or len(parts) != 7:
        raise ValueError("expected seven 512-byte-sector MBR partition entries")
    if any(p["start"] % 8192 for p in parts):
        raise ValueError("partition starts must align to 8192 sectors")
    size = initial_bytes()
    data = parts[6]
    if data["type"] != "83" or data["size"] * 512 != size:
        raise ValueError("p7 does not match the fixed data layout")
    start = data["start"] * 512
    end = start + size
    extended = parts[3]
    if (extended["type"] not in ("5", "f", "85") or
            extended["start"] * 512 > start or
            (extended["start"] + extended["size"]) * 512 < end):
        raise ValueError("p7 is outside the extended partition")
    stat = image.stat()
    if stat.st_size < end:
        raise ValueError("raw image ends before p7")
    with image.open("rb") as stream:
        stream.seek(start)
        remaining = size
        zero = bytes(1024 * 1024)
        while remaining:
            block = stream.read(min(len(zero), remaining))
            if not block or block != zero[:len(block)]:
                raise ValueError("p7 contains nonzero data or a short read")
            remaining -= len(block)
    print("OK: 7 partition entries; all starts align to 8192 sectors.")
    print(f"OK: p7 zero_bytes={size} end={end} image_logical_bytes={stat.st_size}")
    print(f"INFO: image_allocated_bytes={stat.st_blocks * 512}; sparse allocation is host-filesystem dependent")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        (prepare if args.action == "prepare" else check)(args.path)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Data image check failed: {error}\n")


if __name__ == "__main__":
    main()
