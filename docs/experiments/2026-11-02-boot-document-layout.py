#!/usr/bin/env python3
"""起動文書の移動前後を、案内の変更を除いた本文で照合する。"""

import argparse
import csv
import hashlib
from pathlib import Path
import posixpath
import re
import subprocess


MOVES = {
    'boot-sequence.md': 'sequence.md',
    'boot-time-methods.md': 'measurement-methods.md',
    'boot-time-measurements.md': 'measurements.md',
    'kernel-boot-comparison.md': 'kernel-comparison.md',
    'kernel-size.md': 'kernel-size.md',
    'kernel-policy.md': 'kernel-policy.md',
    'rpi-firmware-spec.md': 'firmware.md',
    'boot-and-kernel.md': 'design-notes.md',
}
LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')
INTRO = '以下は公開資料と過去の検証の記録です。数値の測定条件と未確認事項を保ち、現在の配備設定や実機での検証とは区別します。\n\n'


def relocate(text, old, new):
    def replace(match):
        url = match[2]
        if url.startswith(('#', '/')) or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', url):
            return match[0]
        path, sep, fragment = url.partition('#')
        target = posixpath.normpath(posixpath.join(posixpath.dirname(old), path))
        prefix, name = posixpath.split(target)
        if prefix == 'docs/research' and name in MOVES:
            name = 'sequence.md' if name == 'boot-and-kernel.md' else MOVES[name]
            target = f'docs/research/boot/{name}'
        path = posixpath.relpath(target, posixpath.dirname(new))
        return match[1] + path + (sep + fragment if sep else '') + match[3]
    return LINK.sub(replace, text)


def source_body(text, name):
    if name == 'boot-and-kernel.md':
        return text.split('## 22. 関連する設計事項\n', 1)[1].lstrip('\n')
    if name == 'kernel-policy.md':
        return text.removeprefix('\n## カーネル\n').lstrip()
    body = text.split('\n', 1)[1].lstrip('\n')
    if body.startswith('[') and '調査の索引' in body.split('\n', 1)[0]:
        body = body.split('\n', 1)[1].lstrip('\n')
    if body.startswith('boot-and-kernel.md から分割した節です。'):
        body = body.removeprefix('boot-and-kernel.md から分割した節です。').lstrip('\n')
    if body.startswith('以下は公開資料の調査記録です。測定条件と未確認の記述を含め、元の節を保持しています。現在の実装は '):
        body = body.split('\n', 1)[1].lstrip('\n')
    return body


def target_body(text, name):
    if name == 'boot-and-kernel.md':
        marker = '以下は起動時間や電断耐性の検討項目です。'
        return marker + text.split(marker, 1)[1]
    if name == 'kernel-policy.md':
        return text.split('## 過去の方針メモ\n\n', 1)[1].split('\n\n', 1)[1]
    return text.split(INTRO, 1)[1]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    rows = []
    samples = {}
    for repeat in range(1, 6):
        for old_name, new_name in MOVES.items():
            old = f'docs/research/{old_name}'
            new = f'docs/research/boot/{new_name}'
            original = subprocess.check_output(['git', 'show', f'{args.base}:{old}'], cwd=root).decode()
            final = (root / new).read_text()
            expected = relocate(source_body(original, old_name), old, new)
            actual = target_body(final, old_name)
            ok = expected == actual
            rows.append([f'body-{repeat}-{new_name}', repeat, old_name, new_name,
                         len(expected.encode()), len(actual.encode()), sha(expected), sha(actual),
                         'preserved', 'pass' if ok else 'fail'])
            samples[old_name] = (expected, actual)
    table = samples['boot-and-kernel.md']
    firmware = samples['rpi-firmware-spec.md']
    controls = {
        'changed-gpio': (table[0], table[1].replace('GPIO6', 'GPIO7', 1)),
        'removed-row': (table[0], '\n'.join(table[1].split('\n')[:-3])),
        'removed-firmware-intro': (firmware[0], firmware[1].split('## 1. 起動フロー', 1)[1]),
        'changed-source-url': (firmware[0], firmware[1].replace('https://', 'http://', 1)),
    }
    for name, (expected, actual) in controls.items():
        rows.append([name, 1, '', '', len(expected.encode()), len(actual.encode()),
                     sha(expected), sha(actual), 'rejected', 'pass' if expected != actual else 'fail'])
    with args.output.open('x', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['run_id', 'repeat', 'source', 'destination', 'expected_bytes',
                         'actual_bytes', 'expected_sha256', 'actual_sha256', 'expected_result', 'status'])
        writer.writerows(rows)
    failures = [row[0] for row in rows if row[-1] != 'pass']
    print(f'body comparisons=40 negative controls=4 failures={len(failures)}')
    if failures:
        raise SystemExit(', '.join(failures))


if __name__ == '__main__':
    main()
