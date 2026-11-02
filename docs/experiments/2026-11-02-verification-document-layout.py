#!/usr/bin/env python3
"""測定・検証文書の移動、原記録、問いと試験IDを静的に照合する。"""

import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import posixpath
import re
import subprocess


PREFIX = 'docs/research/'
DEST = PREFIX + 'verification/'
M = 'measurement-and-planning.md'
S = 'simulation-plan.md'
Q = 'open-questions.md'
LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')
BLOCKS = [
    (M, 'design-history.md', '## 推奨案と未決事項', '## 開発中の観測手段'),
    (M, 'observability.md', '## 開発中の観測手段', '## シミュレーターと検証基盤の比較'),
    (M, 'observability.md', '## ログと観測', None),
    (M, 'hardware-measurements.md', '### 実機が届いたら最初に測る項目', '## 推奨案と未決事項'),
    (S, 'hardware-measurements.md', '#### 実機でしか検証できない項目', '#### 調査だけの項目と採用しない項目'),
    (S, 'platforms.md', '## シミュレーターと検証基盤の比較', '## シミュレーション検証計画'),
    (S, 'planning-history.md', '#### 実施順（2026-10-20 時点）', None),
    (M, 'design-history.md', '調査した公開資料は', '### 残る未確認事項'),
    (S, 'hardware-measurements.md', '- [ ] `dmesg`', '### 検証ツールと実行境界'),
]


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def section(text, start, end):
    first = text.index(start)
    last = text.index(end, first + len(start)) if end else len(text)
    return text[first:last].strip()


def canonical(text, filename):
    def replace(match):
        url = match[2]
        if url.startswith('/') or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', url):
            return match[0]
        path, sep, fragment = url.partition('#')
        target = posixpath.normpath(posixpath.join(posixpath.dirname(filename), path)) if path else filename
        if target == PREFIX + M:
            name = 'open-questions.md'
            if fragment == '実機が届いたら最初に測る項目優先順の案':
                name = 'hardware-measurements.md'
            elif fragment == '開発中の観測手段':
                name = 'observability.md'
            target = DEST + name
        elif target == PREFIX + S:
            target = DEST + 'experiment-catalog.md'
        elif target == PREFIX + Q:
            target = DEST + Q
        return match[1] + target + sep + fragment + match[3]
    return '\n'.join('' if not line.strip() else line
                     for line in LINK.sub(replace, text).splitlines())


def validate(base, originals, pages, archive):
    errors = []
    records = list(csv.DictReader(io.StringIO(archive)))
    locations = set()
    for row in records:
        source, line = row['source'], int(row['line'])
        key = source, line
        lines = originals[source].splitlines()
        heading = ''
        for value in lines[:line]:
            if value.startswith('#'):
                heading = value
        if (row['base_commit'] != base or key in locations or
                row['original'] != lines[line - 1] or row['section'] != heading):
            errors.append(f'archive:{source}:{line}')
        locations.add(key)
    ids = [row['record_id'] for row in records if row['record_id']]
    expected_ids = {f'Q{i:02}' for i in range(1, 56)} | {f'R{i:02}' for i in range(1, 25)}
    visible_ids = re.findall(r'\b[QR]\d{2}\b', pages[Q])
    if set(ids) != expected_ids or len(ids) != 79 or set(visible_ids) != expected_ids:
        errors.append('question-ids')
    if len(records) != 154:
        errors.append('archive-count')
    body = '\n'.join(canonical(text, DEST + name) for name, text in pages.items())
    for source, original in originals.items():
        for line, value in enumerate(original.splitlines(), 1):
            if value.strip() and (source, line) not in locations:
                if canonical(value, PREFIX + source) not in body:
                    errors.append(f'unaccounted:{source}:{line}')
    for source, destination, start, end in BLOCKS:
        expected = canonical(section(originals[source], start, end), PREFIX + source)
        actual = canonical(pages[destination], DEST + destination)
        if expected not in actual:
            errors.append(f'body:{source}:{start}')
    experiments = re.findall(r'^\| S(\d+) \|', pages['experiment-catalog.md'], re.M)
    if experiments != [str(i) for i in range(1, 18)]:
        errors.append('experiment-ids')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.base):
        parser.error('--base は40桁のcommit SHAを指定してください')
    root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip())
    originals = {name: git(root, 'show', f'{args.base}:{PREFIX}{name}').decode() for name in (M, S, Q)}
    pages = {p.name: p.read_text() for p in (root / DEST).glob('*.md')}
    archive = (root / DEST / 'research-records.csv').read_text()
    raw_paths = [name for name in git(root, 'ls-tree', '-r', '--name-only', args.base, 'docs/experiments').decode().splitlines() if name.endswith('.csv')]
    changed_csv = [name for name in raw_paths if git(root, 'show', f'{args.base}:{name}') != (root / name).read_bytes()]
    expected = json_text(originals)
    actual = json_text(pages) + archive
    rows = []
    for repeat in range(1, 6):
        errors = validate(args.base, originals, pages, archive)
        errors.extend('raw-csv:' + name for name in changed_csv)
        rows.append([repeat, 'preservation', sha(expected), sha(actual), 'preserved', 'fail' if errors else 'pass', ';'.join(errors)])
    variants = {}
    number = copy.copy(pages)
    number['observability.md'] = number['observability.md'].replace('115200', '9600', 1)
    variants['changed-uart-number'] = number, archive
    deleted = copy.copy(pages)
    deleted['hardware-measurements.md'] = deleted['hardware-measurements.md'].replace('- [ ] `dmesg` から IMX219 の sensor ID を採取する。', '')
    variants['removed-camera-condition'] = deleted, archive
    question = copy.copy(pages)
    question[Q] = question[Q].replace('Q01', 'Q99', 1)
    variants['missing-question'] = question, archive
    variants['changed-archive'] = pages, archive.replace('公開対応表に CM0 はありません', '公開対応表に CM0 はあります', 1)
    for name, (mutated, records) in variants.items():
        changed = mutated != pages or records != archive
        errors = validate(args.base, originals, mutated, records)
        rows.append([1, name, sha(actual), sha(json_text(mutated) + records), 'rejected', 'pass' if changed and errors else 'fail', ';'.join(errors)])
    with args.output.open('x', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['repeat', 'check', 'input_sha256', 'output_sha256', 'expected_result', 'status', 'details'])
        writer.writerows(rows)
    failures = sum(row[-2] != 'pass' for row in rows)
    print(f'body_blocks={len(BLOCKS)} questions=79 records=154 raw_csv={len(raw_paths)} repeats=5 controls=4 failures={failures}')
    if failures:
        raise SystemExit(1)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == '__main__':
    main()
