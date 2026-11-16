#!/usr/bin/env python3
"""容量超過入力のCLI応答と独立RS出力を記録する読取り専用probe。"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from followup import save, sha, validate
from rs_check import decode
from stage_a import codeword, syndromes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cases', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    clean = args.cases / 'D-sha256-r2-clean'
    over = args.cases / 'D-sha256-r2-over'
    for case in (clean, over):
        validate(case)
    args.destination.mkdir()
    info = json.loads((over / 'case.json').read_text())
    p = info['parameters']
    reference, damaged = (clean / 'rootfs.img').read_bytes(), (over / 'rootfs.img').read_bytes()
    differences = [i for i, pair in enumerate(zip(reference, damaged)) if pair[0] != pair[1]]
    if differences != [item['offset'] for item in info['locations']]:
        raise ValueError('input difference mismatch')
    before = sha(over / 'rootfs.img')
    image = over / 'rootfs.img'
    command = ['veritysetup', 'verify', '--no-superblock', '--hash=sha256',
               '--data-blocks=' + p['data_blocks'],
               '--hash-offset=' + str(int(p['hash_start_block']) * 4096),
               '--salt=' + p['salt'], '--fec-device=' + str(image),
               '--fec-roots=' + p['fec_roots'], '--fec-offset=' + p['fec_area_offset'],
               str(image), str(image), p['root_hash']]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.destination / 'veritysetup.log').write_bytes(result.stdout)
    expected_word, word = codeword(reference, p, (0, 0)), codeword(damaged, p, (0, 0))
    fixed = decode(word, int(p['fec_roots']))
    output = dict(command=command, returncode=result.returncode, input_sha256=before,
                  input_unchanged=sha(image) == before,
                  version=subprocess.check_output(['veritysetup', '--version'], text=True).strip(),
                  binary_sha256=sha(Path(shutil.which('veritysetup'))),
                  differences=differences, metadata=info['locations'],
                  independent=dict(reference_syndromes=syndromes(expected_word, 2),
                     damaged_syndromes=syndromes(word, 2), decoded_syndromes=syndromes(fixed, 2),
                     decoded_equals_clean=fixed == expected_word,
                     decoder_changes=[i for i in range(255) if fixed[i] != word[i]],
                     remaining_differences=[i for i in range(255) if fixed[i] != expected_word[i]],
                     scope='independent decoder, not a trace of libcryptsetup internal buffers'))
    save(args.destination / 'probe.json', output)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
