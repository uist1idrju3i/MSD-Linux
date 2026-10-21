#!/usr/bin/env python3
import os
from collections import Counter
from pathlib import Path
import re


ROOT = Path(
    os.environ.get(
        "PPD_PATHMAP_ROOT", str(Path(__file__).resolve().parent / "inputs")
    )
)
OUT = Path(os.environ.get("PPD_PATHMAP_OUT", str(ROOT / "rodata-residual")))
ROOTS = {
    "c0": b"/work/output/host/",
    "c1": b"/work/output/per-package/libv4l/host/",
}
FILES = ("v4l2-compliance", "v4l2-ctl")


def strip_paths(data: bytes, root: bytes) -> tuple[bytes, list[int | None]]:
    out = bytearray()
    offsets: list[int | None] = []
    pos = 0
    while True:
        at = data.find(root, pos)
        if at < 0:
            break
        end_string = data.find(b"\0", at)
        if end_string < 0:
            raise ValueError("unterminated embedded path")
        end = end_string + 1
        while end < len(data) and data[end] == 0:
            end += 1
        out.extend(data[pos:at])
        offsets.extend(range(pos, at))
        out.append(0)
        offsets.append(None)
        pos = end
    out.extend(data[pos:])
    offsets.extend(range(pos, len(data)))
    while out and out[-1] == 0:
        out.pop()
        offsets.pop()
    return bytes(out), offsets


def intervals(changed: list[int]) -> list[tuple[int, int]]:
    if not changed:
        return []
    result = []
    start = previous = changed[0]
    for offset in changed[1:]:
        if offset != previous + 1:
            result.append((start, previous + 1))
            start = offset
        previous = offset
    result.append((start, previous + 1))
    return result


def section_address(readelf_file: Path) -> int:
    for line in readelf_file.read_text(errors="replace").splitlines():
        match = re.match(
            r"\s*\[\s*\d+\]\s+\.rodata\s+\S+\s+([0-9a-fA-F]+)", line
        )
        if match:
            return int(match.group(1), 16)
    raise ValueError(f".rodata address not found in {readelf_file}")


def source_offset(mapping: list[int | None], offset: int) -> int | None:
    return mapping[offset] if offset < len(mapping) else None


def scalar_distribution(
    a: bytes, b: bytes, start: int, end: int, width: int
) -> tuple[Counter[int], int]:
    count = Counter()
    complete = (end - start) // width
    for item in range(complete):
        at = start + item * width
        left = int.from_bytes(a[at : at + width], "little", signed=True)
        right = int.from_bytes(b[at : at + width], "little", signed=True)
        count[right - left] += 1
    return count, (end - start) % width


def main() -> None:
    interval_rows = [
        "file\tinterval\tkind\tstripped_start\tstripped_end\tlength"
        "\tunequal_bytes\tc0_rodata_offset\tc1_rodata_offset"
        "\tc0_vaddr\tc1_vaddr\tc0_source_contiguous\tc1_source_contiguous"
    ]
    scalar_rows = [
        "file\tinterval\twidth_bytes\tcomplete_values\ttrailing_bytes"
        "\tc1_minus_c0_distribution"
    ]
    details = []
    for name in FILES:
        raw: dict[str, bytes] = {}
        stripped: dict[str, bytes] = {}
        mappings: dict[str, list[int | None]] = {}
        addresses: dict[str, int] = {}
        for side in ("c0", "c1"):
            raw[side] = (ROOT / f"{name}.{side}.rodata.bin").read_bytes()
            stripped[side], mappings[side] = strip_paths(raw[side], ROOTS[side])
            saved = ROOT / f"{name}.rodata.path-stripped.{side}.bin"
            if stripped[side] != saved.read_bytes():
                raise ValueError(f"rebuilt path-stripped bytes mismatch: {saved}")
            addresses[side] = section_address(
                ROOT / f"{name}.{side}.readelf-sections.txt"
            )
        a, b = stripped["c0"], stripped["c1"]
        common = min(len(a), len(b))
        changed = [i for i in range(common) if a[i] != b[i]]
        groups = [(start, end, "common") for start, end in intervals(changed)]
        if len(a) > common:
            groups.append((common, len(a), "c0-only-tail"))
        elif len(b) > common:
            groups.append((common, len(b), "c1-only-tail"))
        details.append(
            f"{name}: stripped lengths C0/C1={len(a)}/{len(b)}; "
            f"common differing byte positions={len(changed)}; "
            f"contiguous common intervals={len(intervals(changed))}; "
            f"one-sided tail bytes={abs(len(a) - len(b))}"
        )
        for index, (start, end, kind) in enumerate(groups, 1):
            interval_id = f"I{index:03d}"
            length = end - start
            if kind == "common":
                c0_at = source_offset(mappings["c0"], start)
                c1_at = source_offset(mappings["c1"], start)
                unequal = sum(a[i] != b[i] for i in range(start, end))
                c0_contiguous = all(
                    mappings["c0"][i] == c0_at + i - start
                    for i in range(start, end)
                )
                c1_contiguous = all(
                    mappings["c1"][i] == c1_at + i - start
                    for i in range(start, end)
                )
                c0_vaddr = addresses["c0"] + c0_at if c0_at is not None else None
                c1_vaddr = addresses["c1"] + c1_at if c1_at is not None else None
            else:
                c0_at = source_offset(mappings["c0"], start) if kind == "c0-only-tail" else None
                c1_at = source_offset(mappings["c1"], start) if kind == "c1-only-tail" else None
                unequal = length
                c0_contiguous = c1_contiguous = False
                c0_vaddr = addresses["c0"] + c0_at if c0_at is not None else None
                c1_vaddr = addresses["c1"] + c1_at if c1_at is not None else None
            interval_rows.append(
                f"{name}\t{interval_id}\t{kind}\t0x{start:x}\t0x{end:x}"
                f"\t{length}\t{unequal}"
                f"\t{('0x%x' % c0_at) if c0_at is not None else 'EOF/missing'}"
                f"\t{('0x%x' % c1_at) if c1_at is not None else 'EOF/missing'}"
                f"\t{('0x%x' % c0_vaddr) if c0_vaddr is not None else 'EOF/missing'}"
                f"\t{('0x%x' % c1_vaddr) if c1_vaddr is not None else 'EOF/missing'}"
                f"\t{c0_contiguous}\t{c1_contiguous}"
            )
            details.append(
                f"  {interval_id} {kind}: stripped [0x{start:x},0x{end:x}) "
                f"len={length}, unequal={unequal}, "
                f"C0 .rodata offset={('0x%x' % c0_at) if c0_at is not None else 'EOF/missing'}, "
                f"C1 .rodata offset={('0x%x' % c1_at) if c1_at is not None else 'EOF/missing'}, "
                f"C0/C1 vaddr={('0x%x' % c0_vaddr) if c0_vaddr is not None else 'EOF/missing'}"
                f"/{('0x%x' % c1_vaddr) if c1_vaddr is not None else 'EOF/missing'}"
            )
            if kind != "common":
                details.append("    scalar C1-C0 distributions: not defined for missing bytes")
                continue
            for width in (1, 2, 4):
                distribution, trailing = scalar_distribution(a, b, start, end, width)
                dist_text = ",".join(
                    f"{value}:{count}" for value, count in sorted(distribution.items())
                )
                scalar_rows.append(
                    f"{name}\t{interval_id}\t{width}\t{sum(distribution.values())}"
                    f"\t{trailing}\t{dist_text or 'none'}"
                )
                details.append(
                    f"    int{width * 8} C1-C0: {dist_text or 'none'} "
                    f"(complete={sum(distribution.values())}, trailing={trailing})"
                )
    (OUT / "residual-intervals.tsv").write_text("\n".join(interval_rows) + "\n")
    (OUT / "scalar-deltas.tsv").write_text("\n".join(scalar_rows) + "\n")
    (OUT / "interval-details.txt").write_text("\n".join(details) + "\n")


if __name__ == "__main__":
    main()
