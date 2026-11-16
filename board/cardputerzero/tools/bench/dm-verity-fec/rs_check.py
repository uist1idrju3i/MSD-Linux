#!/usr/bin/env python3
"""独立したerrors/erasures位置検出と実codewordの容量境界検査。"""
import hashlib

from stage_a import codeword, decode_erasures, locate, mul, power, syndromes


def decode(word, roots, erasures=()):
    erasures = list(erasures)
    if len(erasures) != len(set(erasures)) or len(erasures) > roots or any(not 0 <= p < 255 for p in erasures):
        raise ValueError('invalid erasures')
    values = syndromes(word, roots)
    if not any(values):
        return list(word)
    for position in erasures:
        x = power(2, 254 - position)
        values = [values[j + 1] ^ mul(x, values[j]) for j in range(len(values) - 1)]
    c, b = [1] + [0] * roots, [1] + [0] * roots
    length, shift, previous = 0, 1, 1
    for n in range(len(values)):
        discrepancy = values[n]
        for i in range(1, length + 1):
            discrepancy ^= mul(c[i], values[n - i])
        if not discrepancy:
            shift += 1
            continue
        old = c[:]
        scale = mul(discrepancy, power(previous, 254))
        for i in range(roots + 1 - shift):
            c[i + shift] ^= mul(scale, b[i])
        if 2 * length <= n:
            length, b, previous, shift = n + 1 - length, old, discrepancy, 1
        else:
            shift += 1
    if 2 * length + len(erasures) > roots:
        raise ValueError('errors/erasures capacity')
    positions = []
    for position in range(255):
        z, value = power(2, -(254 - position)), 0
        for coefficient in reversed(c[:length + 1]):
            value = mul(value, z) ^ coefficient
        if not value:
            positions.append(position)
    if len(positions) != length or set(positions) & set(erasures):
        raise ValueError('locator roots mismatch')
    all_positions = positions + erasures
    if not all_positions:
        raise ValueError('nonzero syndrome without locations')
    return decode_erasures(word, all_positions, roots)


def recovery(clean, damaged, p, record=None):
    roots = int(p['fec_roots'])
    d, h, count = (int(p[k]) for k in ('data_blocks', 'hash_start_block', 'hash_area_blocks'))
    end = int(p['fec_area_offset']) + int(p['fec_bytes'])
    if not 1 <= roots < 255 or len(clean) != len(damaged) or len(clean) < end:
        raise ValueError('invalid recovery geometry')
    columns = set()
    for offset, (before, after) in enumerate(zip(clean, damaged)):
        if before != after:
            column = locate(offset, p)['fec_column']
            if column is None:
                raise ValueError('difference outside FEC coverage')
            columns.add(tuple(column))
    rounds = (d + count + 254 - roots) // (255 - roots)
    candidate, results, changes = bytearray(damaged), [], []
    for column in sorted(columns):
        reference = codeword(clean, p, column)
        if any(syndromes(reference, roots)):
            raise ValueError('invalid clean reference codeword')
        actual = codeword(damaged, p, column)
        try:
            fixed = decode(actual, roots)
            outcome = 'recovered-to-clean' if fixed == reference else 'other-codeword'
            for i, value in enumerate(fixed):
                if i < 255 - roots:
                    logical = i * rounds + column[0]
                    if logical >= d + count:
                        continue
                    physical = logical if logical < d else h + logical - d
                    offset = physical * 4096 + column[1]
                else:
                    offset = int(p['fec_area_offset']) + (column[0] * 4096 + column[1]) * roots + i - (255 - roots)
                if candidate[offset] != value:
                    changes.append(dict(offset=offset, before=candidate[offset], after=value))
                    candidate[offset] = value
            results.append(dict(column=column, outcome=outcome))
        except ValueError as error:
            results.append(dict(column=column, outcome='rejected', error=str(error)))
        if record:
            record(list(results))
    equal = bytes(candidate) == clean
    rejected = any(item['outcome'] == 'rejected' for item in results)
    other = any(item['outcome'] == 'other-codeword' for item in results)
    outcome = 'recovered-to-clean' if equal and not (rejected or other) else ('rejected' if rejected else 'other-codeword')
    return dict(outcome=outcome, decoded_equals_clean=equal,
                clean_sha256=hashlib.sha256(clean).hexdigest(),
                decoded_sha256=hashlib.sha256(candidate).hexdigest(),
                changes=changes, columns=results,
                scope='unknown-error decoding of all changed columns; whole candidate image compared byte-for-byte; no erasure hints')


def boundaries(clean, p, record=None):
    roots = int(p['fec_roots'])
    reference = codeword(clean, p, (0, 0))
    if any(syndromes(reference, roots)):
        raise ValueError('invalid reference codeword')
    results = []
    for errors, erasures in ((roots // 2, 0), (roots // 2 + 1, 0), (0, roots),
                             (0, roots + 1), (1, roots - 2), (1, roots - 1)):
        count = errors + erasures
        damaged = reference[:]
        for i in range(count):
            damaged[i] ^= 255
        try:
            fixed = decode(damaged, roots, range(erasures))
            outcome = 'recovered-to-clean' if fixed == reference else 'other-codeword'
        except ValueError:
            outcome = 'rejected'
        guaranteed = 2 * errors + erasures <= roots
        results.append(dict(errors=errors, erasures=erasures, bound=2 * errors + erasures,
                            roots=roots, guaranteed=guaranteed, outcome=outcome))
        if record:
            record(list(results))
        if guaranteed and outcome != 'recovered-to-clean':
            raise ValueError('failed guaranteed RS capacity')
    return results
