#!/usr/bin/env python3
"""独立したerrors/erasures位置検出と実codewordの容量境界検査。"""
from stage_a import codeword, decode_erasures, mul, power, syndromes


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


def boundaries(clean, p):
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
        if guaranteed and outcome != 'recovered-to-clean':
            raise ValueError('failed guaranteed RS capacity')
        results.append(dict(errors=errors, erasures=erasures, bound=2 * errors + erasures,
                            roots=roots, guaranteed=guaranteed, outcome=outcome))
    return results
