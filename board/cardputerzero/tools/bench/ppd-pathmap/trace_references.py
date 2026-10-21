#!/usr/bin/env python3
import csv
import os
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(
    os.environ.get(
        "PPD_PATHMAP_ROOT", str(Path(__file__).resolve().parent / "inputs")
    )
)
OUT = Path(os.environ.get("PPD_PATHMAP_OUT", str(ROOT / "rodata-residual")))
FILES = {
    "v4l2-compliance": 0x95130,
    "v4l2-ctl": 0x55300,
}
TABLES = {
    "v4l2-compliance": [
        ("switch-227e8-u8", 0x227E8, 0x227EC, 0x227F0, 0x227F4, 0x227F8, 0x227FC,
         0xAC970, 0xAC980, 1, 13),
        ("switch-23f70-s16", 0x23F70, 0x23F74, 0x23F78, 0x23F7C, 0x23F80, 0x23F84,
         0xAC980, 0xAC990, 2, 13),
    ],
    "v4l2-ctl": [
        ("switch-30f94-s16", 0x30F94, 0x30F98, 0x30FA0, 0x30FA4, 0x30FA8, 0x30FAC,
         0x6BCA0, 0x6BCC0, 2, 35),
        ("switch-96c8-s16", 0x96C8, 0x96CC, 0x96D0, 0x96D4, 0x96D8, 0x96DC,
         0x6BD8C, 0x6BDAC, 2, 98),
        ("switch-416cc-u8", 0x416CC, 0x416D0, 0x41710, 0x41714, 0x41718, 0x4171C,
         0x6BD80, 0x6BDA0, 1, 12),
        ("switch-4d148-u8", 0x4D148, 0x4D14C, 0x4D150, 0x4D154, 0x4D158, 0x4D15C,
         0x6BE7C, 0x6BE9C, 1, 13),
        ("switch-4e8d0-s16", 0x4E8D0, 0x4E8D4, 0x4E8D8, 0x4E8DC, 0x4E8E0, 0x4E8E4,
         0x6BE8C, 0x6BEAC, 2, 13),
        ("switch-4efb4-u8", 0x4EFB4, 0x4EFB8, 0x4EFBC, 0x4EFC0, 0x4EFC4, 0x4EFC8,
         0x71560, 0x71580, 1, 21),
    ],
}


def read_disassembly(name, side):
    raw_path = ROOT / f"{name}.{side}.disasm.txt"
    lines = raw_path.read_text().splitlines()
    normalized_lines = (ROOT / f"{name}.{side}.disasm.normalized.txt").read_text().splitlines()
    if len(lines) != len(normalized_lines):
        raise ValueError(f"{raw_path}: raw/normalized line counts differ")
    instructions = {}
    functions = []
    pc_lines = {}
    for line_index, line in enumerate(lines):
        label = re.match(r"^([0-9a-fA-F]{16}) <(.+)>:$", line)
        if label:
            functions.append((int(label.group(1), 16), label.group(2)))
        match = re.match(r"\s*([0-9a-fA-F]+):\s+([a-z][a-z0-9.]*)\s+(.*)", line)
        if match:
            pc = int(match.group(1), 16)
            instructions[pc] = (match.group(2), match.group(3), line)
            pc_lines[pc] = line_index
    return instructions, functions, pc_lines, normalized_lines


def instruction_text(instructions, pc):
    if pc not in instructions:
        raise ValueError(f"missing disassembly instruction at 0x{pc:x}")
    return instructions[pc][2].strip().replace("\t", " ")


def normalize_instruction(instructions, pc_lines, normalized_lines, pc):
    instruction_text(instructions, pc)
    return normalized_lines[pc_lines[pc]]


def function_position(functions, pc):
    prior = [item for item in functions if item[0] <= pc]
    if not prior:
        return ("", -1)
    start, name = prior[-1]
    return name, pc - start


def parse_imm(text):
    token = text.strip().lstrip("#")
    return int(token, 0)


def table_metadata(name, side, spec, instructions):
    label, setup_pc, add_pc, load_pc, adr_pc, branch_add_pc, branch_pc, base0, base1, width, count = spec
    adrp_mn, adrp_ops, _ = instructions[setup_pc]
    add_mn, add_ops, _ = instructions[add_pc]
    load_mn, load_ops, _ = instructions[load_pc]
    adr_mn, adr_ops, _ = instructions[adr_pc]
    branch_add_mn, branch_add_ops, _ = instructions[branch_add_pc]
    branch_mn, branch_ops, _ = instructions[branch_pc]
    if adrp_mn != "adrp" or add_mn != "add":
        raise ValueError(f"{name} {side} {label}: missing adrp/add")
    page_match = re.search(r",\s*([0-9a-fA-F]+)(?:\s|$)", adrp_ops)
    add_match = re.search(r",\s*#(0x[0-9a-fA-F]+|[0-9]+)\s*$", add_ops)
    if not page_match or not add_match:
        raise ValueError(f"{name} {side} {label}: cannot decode address")
    table_base = int(page_match.group(1), 16) + parse_imm(add_match.group(1))
    expected = base0 if side == "c0" else base1
    if table_base != expected:
        raise ValueError(f"{name} {side} {label}: 0x{table_base:x} != 0x{expected:x}")
    if not load_mn.startswith("ldrb" if width == 1 else "ldrh"):
        raise ValueError(f"{name} {side} {label}: unexpected table load {load_mn}")
    if adr_mn != "adr" or branch_add_mn != "add" or branch_mn != "br":
        raise ValueError(f"{name} {side} {label}: missing adr/add/br")
    adr_match = re.search(r",\s*([0-9a-fA-F]+)(?:\s|$)", adr_ops)
    branch_reg = re.match(r"\s*(x\d+)", branch_ops)
    branch_add_reg = re.match(r"\s*(x\d+),\s*x\d+,\s*w\d+", branch_add_ops)
    if not adr_match or not branch_reg or not branch_add_reg or branch_reg.group(1) != branch_add_reg.group(1):
        raise ValueError(f"{name} {side} {label}: cannot decode branch base")
    return {
        "label": label,
        "table_base": table_base,
        "branch_base": int(adr_match.group(1), 16),
        "width": width,
        "count": count,
        "setup_pc": setup_pc,
        "add_pc": add_pc,
        "load_pc": load_pc,
        "adr_pc": adr_pc,
        "branch_add_pc": branch_add_pc,
        "branch_pc": branch_pc,
    }


def signed_value(raw, width):
    bits = width * 8
    return raw - (1 << bits) if raw & (1 << (bits - 1)) else raw


def direct_xrefs(name, side, instructions, section_base, section_size):
    records = []
    pcs = sorted(instructions)
    for index, pc in enumerate(pcs):
        mnemonic, operands, _ = instructions[pc]
        if mnemonic != "adrp":
            continue
        reg_match = re.match(r"\s*(x\d+),\s*([0-9a-fA-F]+)", operands)
        if not reg_match:
            continue
        reg, page = reg_match.group(1), int(reg_match.group(2), 16)
        for next_pc in pcs[index + 1:index + 7]:
            next_mn, next_ops, _ = instructions[next_pc]
            if next_mn == "add":
                add_match = re.match(
                    rf"\s*{reg},\s*{reg},\s*#(0x[0-9a-fA-F]+|[0-9]+)(?:\s|$)",
                    next_ops,
                )
                if add_match:
                    target = page + parse_imm(add_match.group(1))
                    if section_base <= target < section_base + section_size:
                        records.append((target, 0, "address", pc, next_pc))
                    break
            load = re.match(
                rf"\s*[^,]+,\s*\[{reg}(?:,\s*#(0x[0-9a-fA-F]+|[0-9]+))?\]",
                next_ops,
            )
            if load and next_mn.startswith(("ldr", "ldrb", "ldrh", "ldrsw")):
                target = page + (parse_imm(load.group(1)) if load.group(1) else 0)
                size = 16 if next_mn == "ldr" and "q" in next_ops.split(",", 1)[0] else 8
                if next_mn == "ldrb":
                    size = 1
                elif next_mn == "ldrh":
                    size = 2
                elif next_mn.startswith("ldrsw") or re.search(r"\bw\d+\b", next_ops.split(",", 1)[0]):
                    size = 4
                if section_base <= target < section_base + section_size:
                    records.append((target, size, "load", pc, next_pc))
                break
    return records


def overlaps(start, end, other_start, other_end):
    return max(0, min(end, other_end) - max(start, other_start))


def write_tsv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    intervals = list(csv.DictReader((OUT / "residual-intervals.tsv").open(), delimiter="\t"))
    common = [row for row in intervals if row["kind"] == "common"]
    instruction_sets = {}
    function_sets = {}
    pc_line_sets = {}
    normalized_sets = {}
    sections = {}
    table_sets = {}
    all_samples = []
    table_summaries = []
    direct_records = {}

    for name, section_base in FILES.items():
        sections[name] = {}
        size = len((ROOT / f"{name}.c0.rodata.bin").read_bytes())
        for side in ("c0", "c1"):
            instructions, functions, pc_lines, normalized_lines = read_disassembly(name, side)
            instruction_sets[(name, side)] = instructions
            function_sets[(name, side)] = functions
            pc_line_sets[(name, side)] = pc_lines
            normalized_sets[(name, side)] = normalized_lines
            sections[name][side] = (ROOT / f"{name}.{side}.rodata.bin").read_bytes()
            direct_records[(name, side)] = direct_xrefs(name, side, instructions, section_base, size)

        table_sets[name] = []
        for spec in TABLES[name]:
            meta = {}
            for side in ("c0", "c1"):
                meta[side] = table_metadata(name, side, spec, instruction_sets[(name, side)])
            table_sets[name].append(meta)
            c0_data = sections[name]["c0"]
            c1_data = sections[name]["c1"]
            off0 = meta["c0"]["table_base"] - section_base
            off1 = meta["c1"]["table_base"] - section_base
            bytes0 = c0_data[off0:off0 + meta["c0"]["width"] * meta["c0"]["count"]]
            bytes1 = c1_data[off1:off1 + meta["c1"]["width"] * meta["c1"]["count"]]
            byte_equal = bytes0 == bytes1
            checked = exact = same_position = same_normalized = 0
            for index in range(meta["c0"]["count"]):
                width = meta["c0"]["width"]
                raw0 = int.from_bytes(c0_data[off0 + index * width:off0 + (index + 1) * width], "little")
                raw1 = int.from_bytes(c1_data[off1 + index * width:off1 + (index + 1) * width], "little")
                val0 = signed_value(raw0, width)
                val1 = signed_value(raw1, width)
                target0 = meta["c0"]["branch_base"] + val0 * 4
                target1 = meta["c1"]["branch_base"] + val1 * 4
                ins0 = instruction_sets[(name, "c0")]
                ins1 = instruction_sets[(name, "c1")]
                exists = target0 in ins0 and target1 in ins1
                fn0, pos0 = function_position(function_sets[(name, "c0")], target0)
                fn1, pos1 = function_position(function_sets[(name, "c1")], target1)
                norm0 = normalize_instruction(ins0, pc_line_sets[(name, "c0")], normalized_sets[(name, "c0")], target0) if target0 in ins0 else ""
                norm1 = normalize_instruction(ins1, pc_line_sets[(name, "c1")], normalized_sets[(name, "c1")], target1) if target1 in ins1 else ""
                if exists:
                    checked += 1
                    exact += target0 == target1
                    same_position += (fn0, pos0) == (fn1, pos1)
                    same_normalized += norm0 == norm1
                all_samples.append([
                    name, meta["c0"]["label"], index, width, hex(meta["c0"]["table_base"]),
                    hex(meta["c1"]["table_base"]), raw0, raw1, val0, val1,
                    hex(meta["c0"]["branch_base"]), hex(meta["c1"]["branch_base"]),
                    hex(target0), hex(target1), fn0, hex(pos0) if pos0 >= 0 else "",
                    fn1, hex(pos1) if pos1 >= 0 else "", norm0, norm1,
                    "yes" if exists else "no",
                    "yes" if exists and target0 == target1 else "no",
                    "yes" if exists and (fn0, pos0) == (fn1, pos1) else "no",
                    "yes" if exists and norm0 == norm1 else "no",
                ])
            table_summaries.append([
                name, meta["c0"]["label"], hex(meta["c0"]["table_base"]),
                hex(meta["c1"]["table_base"]), hex(off0), hex(off1),
                meta["c0"]["width"], meta["c0"]["count"],
                "yes" if byte_equal else "no", checked, exact,
                same_position, same_normalized,
            ])

    ref_rows = []
    unexplained = []
    for row in common:
        name = row["file"]
        length = int(row["length"])
        start0 = int(row["c0_rodata_offset"], 0)
        start1 = int(row["c1_rodata_offset"], 0)
        va0 = int(row["c0_vaddr"], 0)
        va1 = int(row["c1_vaddr"], 0)
        references = []
        for table in table_sets[name]:
            t0, t1 = table["c0"], table["c1"]
            end0 = t0["table_base"] - FILES[name] + t0["width"] * t0["count"]
            end1 = t1["table_base"] - FILES[name] + t1["width"] * t1["count"]
            ov0 = overlaps(start0, start0 + length, t0["table_base"] - FILES[name], end0)
            ov1 = overlaps(start1, start1 + length, t1["table_base"] - FILES[name], end1)
            if ov0 or ov1:
                references.append(("jump-table", table["c0"]["label"], ov0, ov1,
                                   table["c0"]["setup_pc"], table["c1"]["setup_pc"],
                                   table["c0"]["load_pc"], table["c1"]["load_pc"]))
        for side, start, va in (("c0", start0, va0), ("c1", start1, va1)):
            for target, size, kind, adrp_pc, access_pc in direct_records[(name, side)]:
                hit = (va <= target < va + length) if size == 0 else overlaps(va, va + length, target, target + size) > 0
                if hit:
                    references.append((kind, f"0x{target:x}", 1 if side == "c0" else 0,
                                       1 if side == "c1" else 0, adrp_pc, adrp_pc, access_pc, access_pc))
        if references:
            ref = references[0]
            ins0 = instruction_sets[(name, "c0")]
            ins1 = instruction_sets[(name, "c1")]
            if ref[0] == "jump-table":
                spec = next(item for item in table_sets[name] if item["c0"]["label"] == ref[1])
                meta0, meta1 = spec["c0"], spec["c1"]
                seq0 = " | ".join(instruction_text(ins0, pc) for pc in
                                  (meta0["setup_pc"], meta0["add_pc"], meta0["load_pc"],
                                   meta0["adr_pc"], meta0["branch_add_pc"], meta0["branch_pc"]))
                seq1 = " | ".join(instruction_text(ins1, pc) for pc in
                                  (meta1["setup_pc"], meta1["add_pc"], meta1["load_pc"],
                                   meta1["adr_pc"], meta1["branch_add_pc"], meta1["branch_pc"]))
                ref0, ref1 = seq0, seq1
            else:
                ref0 = instruction_text(ins0, ref[4]) + " | " + instruction_text(ins0, ref[6]) if ref[4] in ins0 and ref[6] in ins0 else ""
                ref1 = instruction_text(ins1, ref[5]) + " | " + instruction_text(ins1, ref[7]) if ref[5] in ins1 and ref[7] in ins1 else ""
            ref_rows.append([
                name, row["interval"], row["c0_rodata_offset"], row["c1_rodata_offset"], length,
                ref[0], ref[1], ref[2], ref[3], ref0, ref1,
            ])
        else:
            ref_rows.append([
                name, row["interval"], row["c0_rodata_offset"], row["c1_rodata_offset"], length,
                "not-mapped", "", 0, 0, "", "",
            ])
            unexplained.append([
                name, row["interval"], row["stripped_start"], row["stripped_end"], length,
                row["c0_rodata_offset"], row["c1_rodata_offset"], row["c0_vaddr"], row["c1_vaddr"],
            ])

    write_tsv(OUT / "jump-table-samples.tsv", [
        "file", "table", "index", "element_width", "c0_table_va", "c1_table_va",
        "c0_raw_unsigned", "c1_raw_unsigned", "c0_signed_value", "c1_signed_value",
        "c0_branch_base", "c1_branch_base", "c0_target", "c1_target",
        "c0_function", "c0_function_offset", "c1_function", "c1_function_offset",
        "c0_normalized_instruction", "c1_normalized_instruction", "target_instruction_present",
        "exact_target_match", "same_function_position", "normalized_instruction_match",
    ], all_samples)
    write_tsv(OUT / "jump-table-summary.tsv", [
        "file", "table", "c0_table_va", "c1_table_va", "c0_section_offset", "c1_section_offset",
        "element_width", "entry_count", "table_bytes_equal", "targets_checked",
        "exact_target_matches", "same_function_position_matches", "normalized_instruction_matches",
    ], table_summaries)
    write_tsv(OUT / "reference-examples.tsv", [
        "file", "interval", "c0_rodata_offset", "c1_rodata_offset", "length",
        "reference_kind", "reference_id", "c0_overlap_bytes", "c1_overlap_bytes",
        "c0_instruction_example", "c1_instruction_example",
    ], ref_rows)
    write_tsv(OUT / "unexplained-intervals.tsv", [
        "file", "interval", "stripped_start", "stripped_end", "length",
        "c0_rodata_offset", "c1_rodata_offset", "c0_vaddr", "c1_vaddr",
    ], unexplained)

    text = []
    text.append("Reference search inputs: saved C0/C1 objdump disassemblies and extracted .rodata sections.")
    text.append("Address formation search: adrp followed by same-register add or immediate load; jump-table search: explicit adrp/add, indexed ldrb/ldrh, adr, scaled add, br sequences.")
    text.append("Common residual intervals with no overlap in these searched references are listed in unexplained-intervals.tsv; this means no matching reference was mapped by this search.")
    text.append("")
    for name in FILES:
        rows = [r for r in common if r["file"] == name]
        mapped = [r for r in ref_rows if r[0] == name and r[5] != "not-mapped"]
        left = [r for r in ref_rows if r[0] == name and r[5] == "not-mapped"]
        table_refs = [r for r in mapped if r[5] == "jump-table"]
        both_sides = sum(int(r[7]) > 0 and int(r[8]) > 0 for r in table_refs)
        c0_only = sum(int(r[7]) > 0 and int(r[8]) == 0 for r in table_refs)
        c1_only = sum(int(r[7]) == 0 and int(r[8]) > 0 for r in table_refs)
        text.append(f"{name}: common intervals={len(rows)}; mapped={len(mapped)}; not mapped={len(left)}.")
        text.append(
            f"  Candidate table address-range overlaps: both builds={both_sides}; "
            f"C0 only={c0_only}; C1 only={c1_only}. The per-build overlap byte counts are in reference-examples.tsv."
        )
        for summary in [r for r in table_summaries if r[0] == name]:
            text.append(
                f"  {summary[1]}: table VA C0/C1={summary[2]}/{summary[3]}, "
                f"entries={summary[7]}, bytes equal={summary[8]}, "
                f"branch targets with instructions={summary[9]}, exact target matches={summary[10]}, "
                f"same function+offset={summary[11]}, normalized instruction matches={summary[12]}."
            )
    text.append("")
    text.append("See jump-table-samples.tsv for every checked entry and its decoded branch target.")
    text.append("See reference-examples.tsv for one mapped instruction example per common residual interval.")
    text.append("See unexplained-intervals.tsv for the complete set not mapped to the searched reference ranges.")
    (OUT / "reference-summary.txt").write_text("\n".join(text) + "\n", encoding="utf-8")

    scalar_counts = defaultdict(Counter)
    scalar_rows = defaultdict(int)
    scalar_totals = defaultdict(int)
    for row in csv.DictReader((OUT / "scalar-deltas.tsv").open(), delimiter="\t"):
        key = (row["file"], int(row["width_bytes"]))
        scalar_rows[key] += 1
        scalar_totals[key] += int(row["complete_values"])
        distribution = row["c1_minus_c0_distribution"]
        for item in distribution.split(",") if distribution != "none" else ():
            if item:
                value, count = item.split(":")
                scalar_counts[key][int(value)] += int(count)
    write_tsv(OUT / "scalar-delta-overview.tsv", [
        "file", "width_bytes", "interval_rows", "complete_values_total",
        "distinct_delta_values", "minimum_delta", "maximum_delta",
    ], [
        [name, width, scalar_rows[(name, width)], scalar_totals[(name, width)],
         len(scalar_counts[(name, width)]),
         min(scalar_counts[(name, width)]) if scalar_counts[(name, width)] else "",
         max(scalar_counts[(name, width)]) if scalar_counts[(name, width)] else ""]
        for name in FILES for width in (1, 2, 4)
    ])
    text.append("")
    text.append("Per-interval C1-C0 int8/int16/int32 value counts are in scalar-deltas.tsv.")
    text.append("The following counts aggregate decoded scalar values across common residual intervals:")
    for name in FILES:
        for width in (1, 2, 4):
            values = scalar_counts[(name, width)]
            delta_range = f"min={min(values)}; max={max(values)}." if values else "min=n/a; max=n/a."
            text.append(
                f"  {name} int{width * 8}: intervals={scalar_rows[(name, width)]}; "
                f"decoded values={scalar_totals[(name, width)]}; "
                f"distinct differences={len(values)}; {delta_range}"
            )
    (OUT / "reference-summary.txt").write_text("\n".join(text) + "\n", encoding="utf-8")

    direct_rows = []
    for name in FILES:
        for side in ("c0", "c1"):
            instructions = instruction_sets[(name, side)]
            for target, size, kind, adrp_pc, access_pc in direct_records[(name, side)]:
                touches_residual = any(
                    row["file"] == name
                    and (
                        int(row[f"{side}_vaddr"], 0) <= target < int(row[f"{side}_vaddr"], 0) + int(row["length"])
                        if size == 0
                        else overlaps(
                            int(row[f"{side}_vaddr"], 0),
                            int(row[f"{side}_vaddr"], 0) + int(row["length"]),
                            target,
                            target + size,
                        ) > 0
                    )
                    for row in common
                )
                if not touches_residual:
                    continue
                direct_rows.append([
                    name, side, kind, hex(target), size, hex(adrp_pc), instruction_text(instructions, adrp_pc),
                    hex(access_pc), instruction_text(instructions, access_pc),
                ])
    write_tsv(OUT / "direct-xrefs.tsv", [
        "file", "side", "reference_kind", "target_va", "access_size",
        "adrp_pc", "adrp_instruction", "access_pc", "access_instruction",
    ], direct_rows)
    print("\n".join(text))


if __name__ == "__main__":
    main()
