#!/usr/bin/env python3
"""Map byte ranges of a SquashFS 4.0 image to files, fragments and tables.

Writes CSV rows: start,end,kind,path,detail (end exclusive, offsets relative
to the start of the image). Supports gzip, xz and zstd metadata.
"""
import argparse
import csv
import lzma
import struct
import sys
import zlib

try:
    from compression import zstd
except ImportError:  # Python < 3.14
    zstd = None

NO_FRAGMENT = 0xFFFFFFFF
UNCOMPRESSED_BLOCK = 1 << 24


class Image:
    def __init__(self, data):
        self.data = data
        fields = struct.unpack_from("<IIIIIHHHHHHQQQQQQQQ", data, 0)
        (magic, self.inode_count, _mtime, self.block_size, self.fragment_count,
         self.compression, _block_log, _flags, self.id_count, major, minor,
         self.root_inode, self.bytes_used, self.id_table, self.xattr_table,
         self.inode_table, self.directory_table, self.fragment_table,
         self.export_table) = fields
        if magic != 0x73717368 or (major, minor) != (4, 0):
            sys.exit("not a SquashFS 4.0 image")
        self.ranges = []

    def decompress(self, raw):
        if self.compression == 1:
            return zlib.decompress(raw)
        if self.compression == 4:
            return lzma.decompress(raw)
        if self.compression == 6:
            if zstd is None:
                sys.exit("zstd needs Python 3.14 or later")
            return zstd.decompress(raw)
        sys.exit(f"unsupported compression id {self.compression}")

    def metadata(self, start, end, kind):
        """Decompress metadata blocks in [start, end); return (bytes, map)."""
        out = bytearray()
        offsets = {}
        pos = start
        while pos < end:
            (header,) = struct.unpack_from("<H", self.data, pos)
            size = header & 0x7FFF
            raw = self.data[pos + 2:pos + 2 + size]
            offsets[pos - start] = len(out)
            out += raw if header & 0x8000 else self.decompress(raw)
            self.ranges.append((pos, pos + 2 + size, kind, "", ""))
            pos += 2 + size
        return bytes(out), offsets

    def table_pointer(self, start):
        return struct.unpack_from("<Q", self.data, start)[0]


def build(path):
    with open(path, "rb") as f:
        img = Image(f.read())
    unset = 0xFFFFFFFFFFFFFFFF
    frag_meta = img.table_pointer(img.fragment_table) if img.fragment_count else None
    ends = [p for p in (frag_meta,
                        img.table_pointer(img.export_table) if img.export_table != unset else None,
                        img.table_pointer(img.id_table)) if p is not None]
    inodes, inode_map = img.metadata(img.inode_table, img.directory_table, "inode-table")
    dirs, dir_map = img.metadata(img.directory_table, min(ends), "directory-table")
    fragments = []
    if img.fragment_count:
        index_len = (img.fragment_count + 511) // 512 * 8
        index = struct.unpack_from(f"<{index_len // 8}Q", img.data, img.fragment_table)
        raw = bytearray()
        for pointer in index:
            (header,) = struct.unpack_from("<H", img.data, pointer)
            block, _ = img.metadata(pointer, pointer + 2 + (header & 0x7FFF), "fragment-table")
            raw += block
        img.ranges.append((img.fragment_table, img.fragment_table + index_len, "fragment-table", "", "index"))
        for i in range(img.fragment_count):
            start, size, _ = struct.unpack_from("<QII", raw, i * 16)
            fragments.append((start, size & ~UNCOMPRESSED_BLOCK))
    fragment_users = {}

    def inode_at(ref):
        return inodes[inode_map[ref >> 16] + (ref & 0xFFFF):]

    def walk(ref, name):
        buf = inode_at(ref)
        kind = struct.unpack_from("<H", buf, 0)[0]
        if kind in (1, 8):
            if kind == 1:
                block, _links, size, offset, _parent = struct.unpack_from("<IIHHI", buf, 16)
            else:
                _links, size, block, _parent, _count, offset = struct.unpack_from("<IIIIHH", buf, 16)
            listing = dirs[dir_map[block] + offset:dir_map[block] + offset + size - 3]
            pos = 0
            while pos < len(listing):
                count, start, _number = struct.unpack_from("<III", listing, pos)
                pos += 12
                for _ in range(count + 1):
                    entry_offset, _delta, _type, name_size = struct.unpack_from("<HhHH", listing, pos)
                    entry = listing[pos + 8:pos + 9 + name_size].decode("utf-8", "replace")
                    pos += 9 + name_size
                    walk((start << 16) | entry_offset, f"{name.rstrip('/')}/{entry}")
        elif kind in (2, 9):
            if kind == 2:
                blocks_start, fragment, frag_offset, size = struct.unpack_from("<IIII", buf, 16)
                sizes_at = 32
            else:
                blocks_start, size, _sparse, _links, fragment, frag_offset, _x = struct.unpack_from("<QQQIIII", buf, 16)
                sizes_at = 56
            count = size // img.block_size if fragment != NO_FRAGMENT else -(-size // img.block_size)
            pos = blocks_start
            for i, value in enumerate(struct.unpack_from(f"<{count}I", buf, sizes_at)):
                length = value & ~UNCOMPRESSED_BLOCK
                if length:
                    img.ranges.append((pos, pos + length, "file", name, f"block {i}"))
                pos += length
            if fragment != NO_FRAGMENT:
                fragment_users.setdefault(fragment, []).append(name)

    walk(img.root_inode, "/")
    for i, (start, size) in enumerate(fragments):
        img.ranges.append((start, start + size, "fragment", ";".join(fragment_users.get(i, [])), f"fragment {i}"))
    img.ranges.append((0, 96, "superblock", "", ""))
    tables = [("id-table", img.id_table, (img.id_count + 2047) // 2048 * 8)]
    if img.export_table != unset:
        tables.append(("export-table", img.export_table, (img.inode_count + 1023) // 1024 * 8))
    if img.xattr_table != unset:
        tables.append(("xattr-table", img.xattr_table, 16))
    for kind, start, index_len in tables:
        meta = img.table_pointer(start)
        img.ranges.append((meta, start, kind, "", "metadata"))
        img.ranges.append((start, start + index_len, kind, "", "index"))
    img.ranges.sort()
    return img


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()
    img = build(args.image)
    with open(args.csv, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["start", "end", "kind", "path", "detail"])
        writer.writerows(img.ranges)
    gaps = overlaps = 0
    covered = 0
    for start, end, *_ in img.ranges:
        if start > covered:
            gaps += 1
        elif start < covered:
            overlaps += 1
        covered = max(covered, end)
    if covered != img.bytes_used:
        gaps += 1
    print(f"ranges={len(img.ranges)} bytes_used={img.bytes_used} covered={covered} gaps={gaps} overlaps={overlaps}", file=sys.stderr)
    if gaps or overlaps:
        sys.exit("map does not cover the image exactly once")


if __name__ == "__main__":
    main()
