#!/usr/bin/env python3
"""Add the preregistered ramoops node to a decompiled device tree."""

import re
import sys
from pathlib import Path


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    state = "code"
    escaped = False
    index = opening
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "line-comment":
            if char == "\n":
                state = "code"
        elif state == "block-comment":
            if char == "*" and next_char == "/":
                state = "code"
                index += 1
        elif state == "string":
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                state = "code"
        elif char == "/" and next_char == "/":
            state = "line-comment"
            index += 1
        elif char == "/" and next_char == "*":
            state = "block-comment"
            index += 1
        elif char == '"':
            state = "string"
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError("unmatched DTS brace")


def find_node(text: str, name: str, start: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", text[start:])
    if not match:
        raise ValueError(f"node not found: {name}")
    opening = start + match.end() - 1
    return opening, matching_brace(text, opening)


def cell_value(block: str, name: str) -> int | None:
    match = re.search(
        rf"(?m)^\s*{re.escape(name)}\s*=\s*<\s*(0x[0-9a-fA-F]+|[0-9]+)\s*>\s*;",
        block,
    )
    return int(match.group(1), 0) if match else None


def cells_for(value: int, count: int) -> list[int]:
    result = []
    for _ in range(count):
        result.append(value & 0xFFFFFFFF)
        value >>= 32
    if value:
        raise ValueError("value does not fit in the DTB cell count")
    return list(reversed(result))


def cell_text(value: int, count: int) -> str:
    return " ".join(f"0x{cell:x}" for cell in cells_for(value, count))


def add_node(text: str) -> str:
    root_open, root_close = find_node(text, "/")
    root = text[root_open + 1 : root_close]
    root_address = cell_value(root, "#address-cells") or 2
    root_size = cell_value(root, "#size-cells") or 1

    try:
        reserved_open, reserved_close = find_node(text, "reserved-memory")
    except ValueError:
        reserved_address = root_address
        reserved_size = root_size
        node = (
            "\n\treserved-memory {\n"
            f"\t\t#address-cells = <0x{reserved_address:x}>;\n"
            f"\t\t#size-cells = <0x{reserved_size:x}>;\n"
            "\t\tranges;\n"
            f"\t\tramoops@1f000000 {{\n"
            '\t\t\tcompatible = "ramoops";\n'
            "\t\t\treg = <"
            f"{cell_text(0x1F000000, reserved_address)} "
            f"{cell_text(0x100000, reserved_size)}"
            ">;\n"
            "\t\t\trecord-size = <0x20000>;\n"
            "\t\t\tconsole-size = <0x20000>;\n"
            "\t\t};\n"
            "\t};\n"
        )
        return text[:root_close] + node + text[root_close:]

    reserved = text[reserved_open + 1 : reserved_close]
    if re.search(r"(?m)^\s*ramoops@1f000000\s*\{", reserved):
        raise ValueError("DTB already contains ramoops@1f000000")
    reserved_address = cell_value(reserved, "#address-cells")
    reserved_size = cell_value(reserved, "#size-cells")
    if reserved_address is None:
        reserved_address = root_address
    if reserved_size is None:
        reserved_size = root_size
    node = (
        "\n\t\tramoops@1f000000 {\n"
        '\t\t\tcompatible = "ramoops";\n'
        "\t\t\treg = <"
        f"{cell_text(0x1F000000, reserved_address)} "
        f"{cell_text(0x100000, reserved_size)}"
        ">;\n"
        "\t\t\trecord-size = <0x20000>;\n"
        "\t\t\tconsole-size = <0x20000>;\n"
        "\t\t};\n"
    )
    properties = ""
    if cell_value(reserved, "#address-cells") is None:
        properties += f"\n\t\t#address-cells = <0x{reserved_address:x}>;"
    if cell_value(reserved, "#size-cells") is None:
        properties += f"\n\t\t#size-cells = <0x{reserved_size:x}>;"
    insertion = properties + node
    return text[:reserved_close] + insertion + text[reserved_close:]


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT.dts OUTPUT.dts", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    output = add_node(source)
    Path(sys.argv[2]).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
