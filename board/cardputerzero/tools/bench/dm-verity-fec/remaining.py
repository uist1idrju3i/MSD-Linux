#!/usr/bin/env python3
"""B3残段階のhost入力生成。旧入力・期待は変更しない。"""
import argparse
import json
from pathlib import Path
import struct

from followup import make_case, parameters, save, sha, validate
from stage_a import locate


def column_offsets(p, count, dispersed=False):
    d, total, roots = (int(p[k]) for k in ('data_blocks', 'fec_blocks', 'fec_roots'))
    rounds = (total + 254 - roots) // (255 - roots)
    if count < 1 or (dispersed and count > rounds):
        raise ValueError('invalid column selection')
    blocks = list(range(count)) if dispersed else [i * rounds for i in range(count)]
    if max(blocks) >= d:
        raise ValueError('data injection out of range')
    return [block * 4096 for block in blocks]


def c_cases(p):
    d, h, roots = (int(p[k]) for k in ('data_blocks', 'hash_start_block', 'fec_roots'))
    per = 4096 // {'crc32c': 4, 'sha256': 32}[p['hash_alg']]
    if p['hash_alg'] != 'crc32c' or roots != 8 or d <= per:
        raise ValueError('stage C requires lower crc32c tree and roots8')
    levels, n = [], d
    while n > 1:
        n = (n + per - 1) // per
        levels.append(n)
    bottom = h + sum(levels[1:])
    head, tail = int(p['fec_area_offset']), int(p['fec_area_offset']) + int(p['fec_bytes']) - 1
    result = [
        ('lower-head', [bottom * 4096], 'normal-read'),
        ('lower-tail', [(bottom + (d - 1) // per) * 4096 + (d - 1) % per * 4], 'normal-read'),
        ('superblock', [d * 4096], 'normal-read'),
        ('parity-head', [head], 'normal-read'),
        ('parity-tail', [tail], 'normal-read')]
    for name, parity in (('head', head), ('tail', tail)):
        round_number, lane = locate(parity, p)['fec_column']
        data = round_number * 4096 + lane
        if locate(data, p)['fec_column'] != locate(parity, p)['fec_column']:
            raise ValueError('parity/data columns differ')
        result.append(('parity-data-' + name, [parity, data], 'normal-read'))
    result += [('data-first', [0], 'normal-read'), ('data-last', [(d - 1) * 4096], 'normal-read'),
               ('post-parity', [tail + 1], 'normal-read')]
    for index, digest in ((0, 0), (1, d - 1)):
        item = locate(result[index][1][0], p)
        if item['tree_level'] != 0 or item['digest_index'] != digest:
            raise ValueError('invalid lower digest')
    return result


def header_probe(image, p):
    offset = int(p['data_blocks']) * 4096
    header = image[offset:offset + 512]
    if len(header) != 512 or header[:8] != b'verity\0\0':
        raise ValueError('invalid verity signature')
    if struct.unpack_from('<II', header, 8) != (1, 1):
        raise ValueError('invalid verity version/type')
    if header[32:64].split(b'\0', 1)[0].decode() != p['hash_alg']:
        raise ValueError('header algorithm mismatch')
    if struct.unpack_from('<IIQ', header, 64) != (4096, 4096, int(p['data_blocks'])):
        raise ValueError('header geometry mismatch')
    salt = bytes.fromhex(p['salt'])
    if struct.unpack_from('<H', header, 80)[0] != len(salt) or header[88:88 + len(salt)] != salt:
        raise ValueError('header salt mismatch')
    return dict(signature='verity', version=1, hash_type=1, algorithm=p['hash_alg'])


def generate(args):
    validate(args.base / 'B-clean-normal')
    seed = args.base / 'repacked-seed'
    if sha(seed / 'rootfs.img') != sha(args.base / 'B-clean-normal/rootfs.img'):
        raise ValueError('seed differs from B clean')
    p = parameters(seed / 'verity-parameters.env')
    clean = (seed / 'rootfs.img').read_bytes()
    args.destination.mkdir()
    rows = []
    for name, offsets, expected in c_cases(p):
        label = 'C-' + name
        make_case(args.destination, seed, args.kernel, p, clean, offsets,
                  label, expected, 'panic', 'normal', stage='C')
        validate(args.destination / label)
        rows.append(dict(case=label, inputs=sha(args.destination / label / 'inputs.json')))
    positive = header_probe(clean, p)
    try:
        header_probe((args.destination / 'C-superblock/rootfs.img').read_bytes(), p)
    except ValueError as error:
        negative = str(error)
    else:
        raise ValueError('header negative control accepted')
    save(args.destination / 'host-check.json', dict(cases=rows, header_positive=positive,
                                                   header_negative=negative, generator=sha(Path(__file__))))


def main():
    parser = argparse.ArgumentParser()
    for name in ('base', 'kernel', 'destination'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    generate(args)


if __name__ == '__main__':
    main()
