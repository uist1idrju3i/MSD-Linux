#!/usr/bin/env python3
"""Map QEMU sdcard_read_block trace lines to partitions and SquashFS files.

Inputs: the trace log written by qemu-trace-wrap.sh, the SD image (for the
MBR/EBR partition table) and the CSV from squashfs-map.py for the rootfs
partition. Writes one CSV row per contiguous read run and prints a summary.
"""
import argparse
import bisect
import csv
import re
import struct

TRACE = re.compile(r"sdcard_read_block addr 0x([0-9a-f]+) size 0x([0-9a-f]+)")


def partitions(image):
    """Return [(number, start_byte, end_byte)] from an MBR with one extended partition."""
    with open(image, "rb") as f:
        def table(offset):
            f.seek(offset + 446)
            raw = f.read(64)
            return [struct.unpack_from("<B3xB3xII", raw, i * 16) for i in range(4)]
        result = []
        extended = None
        for i, (_boot, kind, lba, count) in enumerate(table(0), 1):
            if kind in (0x05, 0x0F):
                extended = lba
            elif kind:
                result.append((i, lba * 512, (lba + count) * 512))
        number = 5
        ebr = extended
        while ebr is not None:
            entries = table(ebr * 512)
            _b, kind, lba, count = entries[0]
            if kind:
                result.append((number, (ebr + lba) * 512, (ebr + lba + count) * 512))
                number += 1
            _b, kind2, lba2, _c = entries[1]
            ebr = extended + lba2 if kind2 else None
    return sorted(result, key=lambda p: p[1])


def load_map(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append((int(row["start"]), int(row["end"]), row["kind"], row["path"], row["detail"]))
    rows.sort()
    return rows, [r[0] for r in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--rootfs-map", required=True)
    parser.add_argument("--rootfs-partition", type=int, default=5)
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()

    parts = partitions(args.image)
    starts = [p[1] for p in parts]
    root = next(p for p in parts if p[0] == args.rootfs_partition)
    rows, row_starts = load_map(args.rootfs_map)

    runs = []
    with open(args.trace, errors="replace") as f:
        for line in f:
            m = TRACE.search(line)
            if not m:
                continue
            addr, size = int(m.group(1), 16), int(m.group(2), 16)
            if runs and runs[-1][1] == addr:
                runs[-1][1] = addr + size
                runs[-1][2] += 1
            else:
                runs.append([addr, addr + size, 1])

    seen = set()
    first_order = []
    totals = {}
    with open(args.csv, "w", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["seq", "card_start", "card_end", "blocks", "partition", "part_offset", "kind", "path", "detail"])
        for seq, (start, end, blocks) in enumerate(runs):
            i = bisect.bisect_right(starts, start) - 1
            part = parts[i] if i >= 0 and start < parts[i][2] else None
            number = part[0] if part else 0
            offset = start - part[1] if part else start
            totals[number] = totals.get(number, 0) + (end - start)
            hits = []
            if part is root:
                lo, hi = offset, end - root[1]
                j = max(bisect.bisect_right(row_starts, lo) - 1, 0)
                while j < len(rows) and rows[j][0] < hi:
                    if rows[j][1] > lo:
                        hits.append(rows[j])
                    j += 1
            if not hits:
                writer.writerow([seq, start, end, blocks, number, offset, "partition" if part else "outside", "", ""])
                continue
            for r_start, _r_end, kind, path, detail in hits:
                writer.writerow([seq, start, end, blocks, number, offset, kind, path, detail])
                for name in (path.split(";") if path else [f"<{kind}>"]):
                    if name not in seen:
                        seen.add(name)
                        first_order.append((seq, name))
    print("bytes_by_partition=" + ";".join(f"p{k}:{v}" for k, v in sorted(totals.items())))
    print(f"read_runs={len(runs)} distinct_names={len(first_order)}")


if __name__ == "__main__":
    main()
