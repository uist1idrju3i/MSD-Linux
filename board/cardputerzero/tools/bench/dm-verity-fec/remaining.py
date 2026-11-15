#!/usr/bin/env python3
"""B3残段階のhost入力生成。旧入力・期待は変更しない。"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from followup import ROOT, SALT, make_case, parameters, save, sha, validate
from stage_a import locate
from rs_check import boundaries, recovery


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


def e_cases(p):
    if p['hash_alg'] != 'crc32c' or int(p['fec_roots']) != 8:
        raise ValueError('stage E requires crc32c roots8')
    return [(f'{count}-' + ('dispersed' if dispersed else 'concentrated'),
             column_offsets(p, count, dispersed),
             'normal-read' if dispersed else 'verity-panic')
            for count in (9, 24) for dispersed in (False, True)]


def f_case(p):
    if p['hash_alg'] != 'crc32c' or int(p['fec_roots']) != 8:
        raise ValueError('stage F requires crc32c roots8')
    return 'F-reset', column_offsets(p, 24), 'restart-reset'


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


def verify_sha(destination, prefix, p, record=None):
    results = []
    for kind, fec in (('clean', False), ('data', False), ('data', True), ('over', True)):
        image = destination / (prefix + '-' + kind) / 'rootfs.img'
        command = ['veritysetup', 'verify', '--no-superblock', '--hash=sha256',
                   '--data-blocks=' + p['data_blocks'],
                   '--hash-offset=' + str(int(p['hash_start_block']) * 4096),
                   '--salt=' + p['salt']]
        if fec:
            command += ['--fec-device=' + str(image), '--fec-roots=' + p['fec_roots'],
                        '--fec-offset=' + p['fec_area_offset']]
        command += [str(image), str(image), p['root_hash']]
        name = prefix + '-' + kind + ('-fec' if fec else '-nofec')
        item = dict(name=name, command=command, status='pending', scope='CLI observation only; not a recovery verdict')
        save(destination / (name + '.json'), item)
        try:
            with (destination / (name + '.log')).open('x') as log:
                item['status'] = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        except OSError as error:
            item.update(status='error', error=str(error))
            save(destination / (name + '.json'), item)
            raise
        item['log_sha256'] = sha(destination / (name + '.log'))
        save(destination / (name + '.json'), item)
        results.append(item)
        if record:
            record(list(results))
    return results


def generate(args):
    validate(args.base / 'B-clean-normal')
    seed = args.base / 'repacked-seed'
    if sha(seed / 'rootfs.img') != sha(args.base / 'B-clean-normal/rootfs.img'):
        raise ValueError('seed differs from B clean')
    p = parameters(seed / 'verity-parameters.env')
    clean = (seed / 'rootfs.img').read_bytes()
    args.destination.mkdir()
    rows = []
    checks = {}

    def checkpoint(name=None, value=None):
        if name is not None:
            checks[name] = value
        save(args.destination / 'host-check.json', dict(status='generating', cases=rows,
             checks=checks, generator=sha(Path(__file__))))

    def emit(label, params, image, offsets, expected, mode='panic'):
        make_case(args.destination, seed, args.kernel, params, image, offsets,
                  label, expected, mode, 'normal', stage=args.stage)
        validate(args.destination / label)
        rows.append(dict(case=label, inputs=sha(args.destination / label / 'inputs.json')))
        checkpoint()

    if args.stage == 'C':
        for name, offsets, expected in c_cases(p):
            emit('C-' + name, p, clean, offsets, expected)
        checks['header_positive'] = header_probe(clean, p)
        try:
            header_probe((args.destination / 'C-superblock/rootfs.img').read_bytes(), p)
        except ValueError as error:
            checks['header_negative'] = str(error)
        else:
            raise ValueError('header negative control accepted')
    elif args.stage == 'D':
        if args.formatter is None:
            raise ValueError('D needs pinned formatter')
        original = json.loads((args.base / 'preparation.json').read_text())['formatter']
        if (sha(args.formatter) != original['verityfmt'] or
                sha(ROOT / 'board/cardputerzero/tools/dm-verity/verityfmt.c') != original['verityfmt.c']):
            raise ValueError('formatter provenance hash mismatch')
        for algorithm in ('crc32c', 'sha256'):
            for roots in (2, 8, 16):
                template = args.destination / f'format-{algorithm}-r{roots}'
                template.mkdir()
                image = template / 'rootfs.img'
                image.write_bytes(clean[:int(p['data_blocks']) * 4096])
                command = [str(args.formatter), '--hash', algorithm, '--salt', SALT,
                           '--fec-roots', str(roots), '--params-file', str(template / 'params.env'), str(image)]
                save(template / 'format.json', dict(command=command, status='pending'))
                with (template / 'format.log').open('x') as log:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
                save(template / 'format.json', dict(command=command, status=result.returncode))
                result.check_returncode()
                params, packed = parameters(template / 'params.env'), image.read_bytes()
                checkpoint(template.name + '-pack', dict(parameters=params, sha256=sha(image)))
                checkpoint(template.name, boundaries(packed, params,
                           lambda values: checkpoint(template.name, values)))
                for kind, offsets, expected in (
                        ('clean', [], 'normal-read'),
                        ('data', [int(params['data_blocks']) // 2 * 4096 + 123], 'normal-read'),
                        ('over', column_offsets(params, roots + 1), 'verity-panic')):
                    emit(f'D-{algorithm}-r{roots}-{kind}', params, packed, offsets, expected)
                    label = f'D-{algorithm}-r{roots}-{kind}'
                    verdict = recovery(packed, (args.destination / label / 'rootfs.img').read_bytes(),
                                       params, lambda values: checkpoint(label, dict(status='decoding', columns=values)))
                    checkpoint(label, verdict)
                    if kind in ('clean', 'data') and verdict['outcome'] != 'recovered-to-clean':
                        raise ValueError('independent recovery failed within capacity: ' + label)
                if algorithm == 'sha256':
                    checkpoint(template.name + '-veritysetup', verify_sha(args.destination,
                        f'D-{algorithm}-r{roots}', params,
                        lambda values: checkpoint(template.name + '-veritysetup', values)))
    elif args.stage == 'E':
        for name, offsets, expected in e_cases(p):
            emit('E-' + name, p, clean, offsets, expected)
    elif args.stage == 'F':
        name, offsets, expected = f_case(p)
        emit(name, p, clean, offsets, expected, 'restart')
    if len(rows) != dict(C=10, D=18, E=4, F=1)[args.stage]:
        raise ValueError('stage case count mismatch')
    save(args.destination / 'host-check.json', dict(status='complete', cases=rows, checks=checks, generator=sha(Path(__file__))))


def main():
    parser = argparse.ArgumentParser()
    for name in ('base', 'kernel', 'destination'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--stage', choices=('C', 'D', 'E', 'F'), default='C')
    parser.add_argument('--formatter', type=Path)
    args = parser.parse_args()
    generate(args)


if __name__ == '__main__':
    main()
