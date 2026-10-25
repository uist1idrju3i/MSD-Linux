#!/usr/bin/env python3
"""Summarize the rootfs reads of several boots mapped by map-reads.py.

For each boot: unique bytes read from the rootfs partition (repeated reads
counted once), the unique bytes per SquashFS range kind, the number of files
whose data blocks were touched, and the SHA-256 of the first-read name order.
Also reports whether the name order is the same in every boot.
"""

import argparse
import collections
import csv
import hashlib
import sys


def merged_intervals(reads_csv, partition):
    spans = set()
    with open(reads_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row["partition"] != partition:
                continue
            start = int(row["part_offset"])
            spans.add((start, start + int(row["card_end"]) - int(row["card_start"])))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def overlap(start, end, merged):
    return sum(max(0, min(end, b) - max(start, a)) for a, b in merged)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs-map", required=True)
    parser.add_argument("--rootfs-partition", default="5")
    parser.add_argument("--boot", nargs=3, action="append", required=True,
                        metavar=("NAME", "READS_CSV", "ORDER_CSV"))
    parser.add_argument("--csv", required=True, help="per-boot metrics")
    parser.add_argument("--files-csv", required=True,
                        help="unique bytes read per file, first boot")
    args = parser.parse_args()

    with open(args.rootfs_map, newline="") as f:
        ranges = [(int(r["start"]), int(r["end"]), r["kind"], r["path"])
                  for r in csv.DictReader(f)]
    file_size = collections.Counter()
    for start, end, kind, path in ranges:
        if kind == "file":
            file_size[path] += end - start
    total = max(end for _, end, _, _ in ranges)

    orders = []
    out_rows = []
    first_files = None
    for name, reads_csv, order_csv in args.boot:
        merged = merged_intervals(reads_csv, args.rootfs_partition)
        by_kind = collections.Counter()
        by_file = collections.Counter()
        for start, end, kind, path in ranges:
            n = overlap(start, end, merged)
            by_kind[kind] += n
            if kind == "file" and n:
                by_file[path] += n
        with open(order_csv, newline="") as f:
            order = [r["name"] for r in csv.DictReader(f)]
        orders.append(order)
        digest = hashlib.sha256("\n".join(order).encode()).hexdigest()
        unique = sum(b - a for a, b in merged)
        out_rows += [
            (name, "rootfs_unique_bytes", unique, "B"),
            (name, "rootfs_unique_percent", f"{unique / total * 100:.2f}", "%"),
            (name, "files_with_blocks_read", len(by_file), "count"),
            (name, "first_read_names", len(order), "count"),
            (name, "first_read_order_sha256", digest, "sha256"),
        ]
        out_rows += [(name, f"unique_bytes_{k}", v, "B") for k, v in sorted(by_kind.items())]
        if first_files is None:
            first_files = by_file
        print(f"{name} unique={unique} ({unique / total * 100:.2f} %) files={len(by_file)} "
              f"names={len(order)} order_sha256={digest[:12]}")

    same = all(o == orders[0] for o in orders)
    print(f"bytes_used={total} order_same_in_all_boots={int(same)}")
    with open(args.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["boot", "metric", "value", "unit"])
        w.writerows(out_rows)
    with open(args.files_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "unique_bytes_read", "data_bytes", "percent_read"])
        for path, n in first_files.most_common():
            w.writerow([path, n, file_size[path], f"{n / file_size[path] * 100:.1f}"])
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
