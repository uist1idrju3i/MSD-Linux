#!/usr/bin/env python3
"""保存領域の主題別再配置を、基準git objectの本文全範囲と照合する。"""

import argparse
import csv
import hashlib
from pathlib import Path
import posixpath
import re
import subprocess
import unicodedata
from urllib.parse import unquote


PREFIX = 'docs/research/'
DEST = PREFIX + 'storage/'
A = 'storage-and-flash.md'
B = 'readonly-data-and-fs.md'
C = 'fs-candidates.md'
D = 'power-and-updates.md'
SPLITS = [
    (A, 'layout-and-flash.md', None, '## ext4 の `/data`'),
    (A, 'allocation-and-small-files.md', '## ext4 の `/data`', '## discard、fstrim、SD バス'),
    (A, 'media-measurements.md', '## discard、fstrim、SD バス', '## 出典と短い抜粋'),
    (A, 'layout-and-flash.md', '## 出典と短い抜粋', None),
    (B, 'write-policy-and-s3.md', None, '## S17: ストレージの障害・速度の模擬'),
    (B, 'fault-injection-s17.md', '## S17: ストレージの障害・速度の模擬', '## 出典、抜粋、信頼度'),
    (B, 'filesystem-sources.md', '## 出典、抜粋、信頼度', None),
    (C, 'filesystem-candidates.md', None, None),
    (D, 'power-loss.md', None, '## 7. OTA / A-B'),
    (D, 'ab-design-history.md', '## 7. OTA / A-B', '## 18. 失敗検知と自動復旧（A/B）'),
    (D, 'recovery-and-watchdog.md', '## 18. 失敗検知と自動復旧（A/B）', None),
]
DEFAULTS = {A: 'README.md', B: 'write-policy-and-s3.md',
            C: 'filesystem-candidates.md', D: 'README.md'}
LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def body(text):
    return text.split('\n', 1)[1].lstrip('\n')


def span(text, start, end):
    first = text.index(start) if start else 0
    last = text.index(end, first + 1) if end else len(text)
    return first, last


def slug(text):
    value = re.sub(r'[*~`]+', '', text.lower())
    value = re.sub(r'(?<!\w)_+|_+(?!\w)', '', value)
    filtered = []
    for char in value:
        if unicodedata.category(char)[0] in 'LN' or char in ' -_' or char.isspace():
            filtered.append(' ' if char.isspace() else char)
    return re.sub(r'\s+', '-', ''.join(filtered)).strip('-')


def destinations(originals):
    result = {}
    for source, target, start, end in SPLITS:
        text = body(originals[source])
        first, last = span(text, start, end)
        for heading in re.findall(r'^#{1,6} (.+)$', text[first:last], re.M):
            key = source, slug(heading)
            if key in result and result[key] != target:
                raise ValueError(f'ambiguous heading: {key}')
            result[key] = target
    return result


def relocate_url(url, filename, originals, headings):
    if url.startswith('/') or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', url):
        return url
    path, sep, fragment = url.partition('#')
    absolute = posixpath.normpath(posixpath.join(posixpath.dirname(filename), path)) if path else filename
    prefix, name = posixpath.split(absolute)
    if prefix == PREFIX.rstrip('/') and name in DEFAULTS:
        if fragment == slug(originals[name].splitlines()[0].lstrip('# ')):
            sep = fragment = ''
        target = headings.get((name, unquote(fragment)), DEFAULTS[name])
        absolute = DEST + target
    return absolute + sep + fragment


def canonical(text, filename, originals, headings):
    value = LINK.sub(lambda m: m[1] + relocate_url(m[2], filename, originals, headings) + m[3], text)
    return '\n'.join('' if not line.strip() else line for line in value.splitlines()).strip()


def validate(originals, pages, headings):
    errors = []
    intervals = {name: [] for name in originals}
    for source, target, start, end in SPLITS:
        text = body(originals[source])
        first, last = span(text, start, end)
        intervals[source].append((first, last))
        expected = canonical(text[first:last], PREFIX + source, originals, headings)
        actual = canonical(pages[target], DEST + target, originals, headings)
        if expected not in actual:
            errors.append(f'body:{source}:{start}:{target}')
    for source, ranges in intervals.items():
        cursor = 0
        for first, last in sorted(ranges):
            if first != cursor or last <= first:
                errors.append(f'coverage:{source}:{first}:{last}')
            cursor = last
        if cursor != len(body(originals[source])):
            errors.append(f'coverage-end:{source}')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(git(None, 'rev-parse', '--show-toplevel').decode().strip())
    base = git(root, 'rev-parse', args.base + '^{commit}').decode().strip()
    originals = {name: git(root, 'show', f'{base}:{PREFIX}{name}').decode()
                 for name in DEFAULTS}
    pages = {name: (root / DEST / name).read_text()
             for name in {entry[1] for entry in SPLITS}}
    headings = destinations(originals)
    csv_paths = [name for name in git(root, 'ls-tree', '-r', '--name-only', base).decode().splitlines()
                 if name.endswith('.csv')]
    raw_errors = [f'csv:{name}' for name in csv_paths
                  if not (root / name).is_file() or
                  (root / name).read_bytes() != git(root, 'show', f'{base}:{name}')]
    input_hash = sha(''.join(originals[name] for name in sorted(originals)))
    output_hash = sha(''.join(pages[name] for name in sorted(pages)))
    rows = []
    for repeat in range(1, 6):
        errors = validate(originals, pages, headings) + raw_errors
        rows.append([repeat, 'preservation', input_hash, output_hash,
                     'preserved', 'pass' if not errors else 'fail', ';'.join(errors)])
    controls = [
        ('layout-value', 'layout-and-flash.md', '| p2 | 32,769 |', '| p2 | 32,768 |'),
        ('small-file-value', 'allocation-and-small-files.md', '1,110,016', '1,110,015'),
        ('s17-condition', 'fault-injection-s17.md', 'host root 不要', 'host root 必要'),
        ('watchdog-failure', 'recovery-and-watchdog.md',
         'v1 は観測窓が不足して基準未達でした。', 'v1 は基準を満たしました。'),
    ]
    for label, target, before, after in controls:
        changed = dict(pages)
        changed[target] = changed[target].replace(before, after, 1)
        errors = validate(originals, changed, headings)
        rejected = changed[target] != pages[target] and bool(errors)
        rows.append([0, label, input_hash, sha(changed[target]), 'rejected',
                     'pass' if rejected else 'fail', ';'.join(errors)])
    with args.output.open('x', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['repeat', 'check', 'input_sha256', 'output_sha256',
                         'expected_result', 'status', 'details'])
        writer.writerows(rows)
    failures = sum(row[5] != 'pass' for row in rows)
    print(f'body_blocks={len(SPLITS)} sources={len(originals)} raw_csv={len(csv_paths)} '
          f'repeats=5 controls={len(controls)} failures={failures}')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
