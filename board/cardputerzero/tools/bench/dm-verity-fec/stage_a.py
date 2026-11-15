#!/usr/bin/env python3
"""B3研究用の注入位置、既知消失RS復号、終了原因判定。"""
from functools import lru_cache
import re


def parameters(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines()
                if "=" in line and not line.startswith("#"))


def locate(offset, p):
    d, h, count, roots = (int(p[k]) for k in
                          ("data_blocks", "hash_start_block", "hash_area_blocks", "fec_roots"))
    if d < 1 or h < d or count < 1 or (roots != 0 and not 2 <= roots <= 24):
        raise ValueError("invalid geometry")
    if offset < 0:
        raise ValueError("negative offset")
    block, lane = divmod(offset, 4096)
    digest_size = {"crc32c": 4, "sha256": 32}[p["hash_alg"]]
    per_block = 4096 // digest_size
    levels, n = [], d
    while True:
        n = (n + per_block - 1) // per_block
        levels.append(n)
        if n == 1:
            break
    if sum(levels) != count:
        raise ValueError("hash tree geometry mismatch")
    result = dict(offset=offset, physical_block=block, byte_in_block=lane,
                  tree_level=None, digest_index=None, fec_column=None,
                  fec_symbol=None, fec_logical_block=None)
    logical = None
    if block < d:
        result["region"], logical = "data", block
    elif block == d and h == d + 1:
        result["region"] = "superblock"
    elif h <= block < h + count:
        result["region"], logical = "hash", d + block - h
        start = h
        for level in reversed(range(len(levels))):
            if start <= block < start + levels[level]:
                result.update(tree_level=level,
                              digest_index=(block - start) * per_block + lane // digest_size)
                break
            start += levels[level]
    else:
        result["region"] = "outside"
    if roots:
        rounds = (d + count + 254 - roots) // (255 - roots)
        fec_start = int(p["fec_area_offset"])
        if logical is not None:
            result.update(fec_logical_block=logical, fec_column=[logical % rounds, lane],
                          fec_symbol=logical // rounds)
        elif fec_start <= offset < fec_start + int(p["fec_bytes"]):
            relative = offset - fec_start
            column, symbol = divmod(relative % (4096 * roots), roots)
            result.update(region="parity", fec_column=[relative // (4096 * roots), column],
                          fec_symbol=255 - roots + symbol)
    return result


@lru_cache(maxsize=None)
def mul(a, b):
    value = 0
    while b:
        if b & 1:
            value ^= a
        b >>= 1
        a <<= 1
        if a & 256:
            a ^= 0x11d
    return value


@lru_cache(maxsize=None)
def power(a, n):
    value = 1
    for _ in range(n % 255):
        value = mul(value, a)
    return value


def syndromes(word, roots):
    if len(word) != 255 or not 2 <= roots <= 24:
        raise ValueError("invalid codeword geometry")
    values = []
    for j in range(roots):
        value = 0
        for symbol in word:
            value = mul(value, power(2, j)) ^ symbol
        values.append(value)
    return values


def decode_erasures(word, positions, roots):
    positions = sorted(set(positions))
    if not positions or len(positions) > roots or any(i < 0 or i >= 255 for i in positions):
        raise ValueError("invalid erasure positions/capacity")
    s = syndromes(word, roots)
    n = len(positions)
    matrix = [[power(2, j * (254 - k)) for k in positions] + [s[j]]
              for j in range(n)]
    for col in range(n):
        pivot = next(row for row in range(col, n) if matrix[row][col])
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        inverse = power(matrix[col][col], 254)
        matrix[col] = [mul(v, inverse) for v in matrix[col]]
        for row in range(n):
            if row != col:
                scale = matrix[row][col]
                matrix[row] = [a ^ mul(scale, b) for a, b in zip(matrix[row], matrix[col])]
    fixed = list(word)
    for row, position in enumerate(positions):
        fixed[position] ^= matrix[row][-1]
    if any(syndromes(fixed, roots)):
        raise ValueError("residual syndrome")
    return fixed


def codeword(image, p, column):
    d, h, count, roots = (int(p[k]) for k in
                          ("data_blocks", "hash_start_block", "hash_area_blocks", "fec_roots"))
    rounds = (d + count + 254 - roots) // (255 - roots)
    round_number, lane = column
    word = []
    for i in range(255 - roots):
        logical = i * rounds + round_number
        physical = logical if logical < d else h + logical - d
        word.append(image[physical * 4096 + lane] if logical < d + count else 0)
    start = int(p["fec_area_offset"]) + (round_number * 4096 + lane) * roots
    word.extend(image[start:start + roots])
    return word


def independent_check(clean, damaged, p, locations):
    roots = int(p["fec_roots"])
    if not roots:
        return dict(scope="no FEC", columns=[])
    affected = {}
    for item in locations:
        if item["fec_column"] is not None:
            affected.setdefault(tuple(item["fec_column"]), []).append(item["fec_symbol"])
    rounds = (int(p["fec_blocks"]) + 254 - roots) // (255 - roots)
    columns = sorted(set(affected) | {(r, b) for r in range(rounds) for b in (0, 4095)})
    results = []
    for column in columns:
        reference = codeword(clean, p, column)
        if any(syndromes(reference, roots)):
            raise ValueError("clean parity syndrome is nonzero")
        actual = codeword(damaged, p, column)
        positions = affected.get(column, [])
        outcome = "clean"
        if positions:
            if len(set(positions)) > roots:
                if not any(syndromes(actual, roots)):
                    raise ValueError("negative control has zero syndrome")
                outcome = "over-erasure-capacity"
            else:
                if decode_erasures(actual, positions, roots) != reference:
                    raise ValueError("decoded word differs from clean reference")
                outcome = "decoded-to-clean"
        elif actual != reference:
            raise ValueError("unrecorded column change")
        results.append(dict(column=column, erasures=len(set(positions)), outcome=outcome))
    return dict(scope="all affected columns + first/last byte of every round; known erasures",
                columns=results)


def judge(serial, expected, exit_status, stop_reason, events):
    ready = "MSD/Linux ready" in serial
    corrupt = bool(re.search(r"device-mapper:\s*verity:[^\n]*(?:is corrupted|verification failed)|"
                             r"dm-verity device corrupted", serial))
    panic = "Kernel panic" in serial
    verity_panic = bool(re.search(r"Kernel panic[^\n]*dm-verity", serial))
    restart = "reboot: Restarting system" in serial
    banners = len(re.findall(r"(?:^|\n)(?:\[\s*[\d.]+\]\s*)?Linux version ", serial))
    reset = any(event.get("event") == "RESET" and event.get("after_restart_marker") for event in events)
    signal = "terminating on signal" in serial
    eio = bool(re.search(r"(?:I/O error|error -5|error=-5|Buffer I/O error)", serial))
    valid = False
    if expected == "ready":
        valid = ready and not (corrupt or panic or restart or signal) and stop_reason == "ready"
    elif expected == "verity-panic":
        valid = corrupt and verity_panic and not (ready or restart) and stop_reason == "panic"
    elif expected == "verity-eio":
        valid = corrupt and eio and not (ready or restart or panic) and stop_reason == "eio"
    elif expected == "restart-request":
        valid = (corrupt and restart and not (ready or panic or signal) and
                 stop_reason == "natural-exit" and exit_status == 0)
    elif expected == "restart-reset":
        valid = (corrupt and restart and reset and banners >= 2 and not (ready or panic) and
                 stop_reason == "reset-observed")
    else:
        raise ValueError("unknown expectation")
    return dict(functional_pass=bool(valid), expected=expected, ready=ready, corruption=corrupt,
                panic=panic, restart=restart, boot_banners=banners, qmp_reset=reset, eio=eio,
                exit_status=exit_status, stop_reason=stop_reason)
