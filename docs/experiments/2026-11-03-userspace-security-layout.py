#!/usr/bin/env python3
"""ユーザー空間と強化項目の移動・要約統合を基準git objectと照合する。"""

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
U = 'userspace-and-security.md'
S = 'security-hardening.md'
H = 'security-2026-11-hardening-list.md'
RECORDS = 'docs/research/userspace/original-summaries.csv'
DEFAULTS = {U: 'userspace/README.md', S: 'security/threat-model.md',
            H: 'security/history/README.md'}
INIT = '## 16. ユーザー空間の除去・遅延起動・init 選択'
READ_ORDER = '### 16.4 SquashFS + overlayfs と読込み順最適化'
LIBC = '## 17. libc・アロケータ'
SSH = 'SSH・VPN、暗号拡張、鍵保管と A/B OTA の調査（21 節）は、'
SUMMARY = '## init・libc'
TOOLCHAIN = '### libc / toolchain の調査'
BLOCKS = [
    (U, '@intro', None, INIT),
    (U, 'userspace/init-history.md', INIT, READ_ORDER),
    (U, 'storage/rootfs-read-order.md', READ_ORDER, LIBC),
    (U, 'userspace/libc-history.md', LIBC, SSH),
    (U, '@ssh', SSH, SUMMARY),
    (U, '@init', SUMMARY, TOOLCHAIN),
    (U, '@libc', TOOLCHAIN, None),
    (S, 'security/threat-model.md', None, None),
]
HISTORY = {
    1: 'network.md', 2: 'kernel-and-mounts.md', 3: 'kernel-and-mounts.md',
    4: 'kernel-and-mounts.md', 5: 'kernel-and-mounts.md',
    6: 'kernel-and-mounts.md', 7: 'network.md', 8: 'network.md',
    9: 'network.md', 10: 'kernel-and-mounts.md', 11: 'monitoring.md',
    12: 'software-and-sandbox.md', 13: 'kernel-and-mounts.md',
    14: 'software-and-sandbox.md', 15: 'software-and-sandbox.md',
}
BLOCKS.append((H, 'security/history/README.md', None, '## 1. '))
for number, target in HISTORY.items():
    end = f'## {number + 1}. ' if number < 15 else '## 実装の優先順位案'
    BLOCKS.append((H, 'security/history/' + target, f'## {number}. ', end))
BLOCKS.extend([
    (H, 'security/history/README.md', '## 実装の優先順位案', '## 検証方法'),
    (H, 'security/history/README.md', '## 検証方法', None),
])
NOTES = {
    '@intro': ('navigation', 'userspace/README.md',
               '現在の比較への案内を新しい入口へ統合。Wi-Fiの未実装範囲は維持'),
    '@ssh': ('navigation', 'ssh-vpn-and-keys.md',
             '既に分割済みのSSH本文への案内。新しい入口から直接参照'),
    '@init': ('overlapping-summary', 'userspace/init-history.md',
              '16.2のM5依存表・init比較と対応。推測・未測定・未調査は詳細表へ保持'),
    '@libc': ('superseded-status', 'userspace/libc-history.md',
              '17.1から17.5の版・制約・条件付き測定と重複する要約。版の未確認表現は後の一次資料照合と混同しない'),
}
FIELDS = ['id', 'source', 'start', 'end', 'kind', 'canonical', 'reason',
          'original_sha256', 'original_payload']
LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def body(value):
    return value.split('\n', 1)[1].lstrip('\n')


def span(value, start, end):
    first = value.index(start) if start else 0
    last = value.index(end, first + 1) if end else len(value)
    return first, last


def slug(value):
    value = re.sub(r'[*~`]+', '', value.lower())
    value = re.sub(r'(?<!\w)_+|_+(?!\w)', '', value)
    chars = [' ' if char.isspace() else char for char in value
             if unicodedata.category(char)[0] in 'LN' or char in ' -_' or char.isspace()]
    return re.sub(r'\s+', '-', ''.join(chars)).strip('-')


def source_records(originals):
    rows = []
    for source, target, start, end in BLOCKS:
        if not target.startswith('@'):
            continue
        text = body(originals[source])
        first, last = span(text, start, end)
        kind, canonical, reason = NOTES[target]
        values = [target[1:], source, start or '', end or '', kind, canonical,
                  reason, sha(text[first:last]), text[first:last]]
        rows.append(dict(zip(FIELDS, values)))
    return rows


def destinations(originals):
    result = {}
    for source, target, start, end in BLOCKS:
        if target.startswith('@'):
            continue
        text = body(originals[source])
        first, last = span(text, start, end)
        for heading in re.findall(r'^#{1,6} (.+)$', text[first:last], re.M):
            key = source, slug(heading)
            if key in result and result[key] != (target, slug(heading)):
                raise ValueError(f'ambiguous heading: {key}')
            result[key] = target, slug(heading)
    init_heading = re.search(r'^### (16\.2 .+)$', originals[U], re.M)[1]
    libc_heading = re.search(r'^### (17\.1 .+)$', originals[U], re.M)[1]
    result.update({
        (U, slug('init・libc')): (DEFAULTS[U], ''),
        (U, slug('init と周辺デバイス')): ('userspace/init-history.md', slug(init_heading)),
        (U, slug('init の比較')): ('userspace/init-history.md', slug(init_heading)),
        (U, slug('libc / toolchain の調査')): ('userspace/libc-history.md', slug(libc_heading)),
    })
    return result


def relocate_url(url, filename, originals, headings):
    if url.startswith('/') or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', url):
        return url
    path, sep, fragment = url.partition('#')
    absolute = posixpath.normpath(posixpath.join(posixpath.dirname(filename), path)) if path else filename
    prefix, name = posixpath.split(absolute)
    if prefix == PREFIX.rstrip('/') and name in DEFAULTS:
        if fragment == slug(originals[name].splitlines()[0].lstrip('# ')):
            fragment = ''
        if fragment:
            target, fragment = headings[name, unquote(fragment)]
        else:
            target = DEFAULTS[name]
        absolute = PREFIX + target
        sep = '#' if fragment else ''
    return absolute + sep + fragment


def canonical(value, filename, originals, headings):
    value = LINK.sub(lambda m: m[1] + relocate_url(m[2], filename, originals, headings) + m[3], value)
    return '\n'.join('' if not line.strip() else line for line in value.splitlines()).strip()


def validate(originals, pages, records, headings, blocks=None):
    errors = []
    intervals = {source: [] for source in originals}
    if records != source_records(originals):
        errors.append('source-records')
    for source, target, start, end in BLOCKS if blocks is None else blocks:
        text = body(originals[source])
        first, last = span(text, start, end)
        intervals[source].append((first, last))
        if target.startswith('@'):
            continue
        expected = canonical(text[first:last], PREFIX + source, originals, headings)
        actual = canonical(pages[target], PREFIX + target, originals, headings)
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
    originals = {name: git(root, 'show', f'{base}:{PREFIX}{name}').decode() for name in DEFAULTS}
    targets = {b[1] for b in BLOCKS if not b[1].startswith('@')}
    pages = {name: (root / PREFIX / name).read_text() for name in targets}
    with (root / RECORDS).open(newline='') as handle:
        records = list(csv.DictReader(handle))
    headings = destinations(originals)
    csv_paths = [p for p in git(root, 'ls-tree', '-r', '--name-only', base).decode().splitlines()
                 if p.endswith('.csv')]
    raw_errors = [f'csv:{p}' for p in csv_paths if not (root / p).is_file()
                  or (root / p).read_bytes() != git(root, 'show', f'{base}:{p}')]
    input_hash = sha(''.join(originals[name] for name in sorted(originals)))
    output_hash = sha(''.join(pages[name] for name in sorted(pages)) + repr(records))
    rows = []
    for repeat in range(1, 6):
        errors = validate(originals, pages, records, headings) + raw_errors
        rows.append([repeat, 'preservation', input_hash, output_hash, 'preserved',
                     'fail' if errors else 'pass', ';'.join(errors)])
    controls = [
        ('applet-count', 'userspace/init-history.md', '試験用の 63 applet の集合', '試験用の 64 applet の集合'),
        ('sort-condition', 'storage/rootfs-read-order.md', '-32768〜32767', '-32767〜32767'),
        ('libc-value', 'userspace/libc-history.md', '234μs', '235μs'),
        ('s6-value', 'security/threat-model.md', '82.673 ms', '82.674 ms'),
        ('module-condition', 'security/history/kernel-and-mounts.md',
         '`modules_disabled=1`', '`modules_disabled=0`'),
        ('signature-clock', 'security/history/network.md',
         '数学的検証自体は壁時計に依存しません', '数学的検証自体は壁時計に依存します'),
        ('monitoring-limit', 'security/history/monitoring.md', '本機は 512 MiB / BusyBox', '本機は 256 MiB / BusyBox'),
    ]
    for label, target, before, after in controls:
        changed = dict(pages)
        changed[target] = changed[target].replace(before, after, 1)
        errors = validate(originals, changed, records, headings)
        rejected = changed[target] != pages[target] and bool(errors)
        rows.append([0, label, input_hash, sha(changed[target]), 'rejected',
                     'pass' if rejected else 'fail', ';'.join(errors)])
    changed_records = [dict(row) for row in records]
    changed_records[-1]['original_payload'] = changed_records[-1]['original_payload'].replace('未確認', '確認済み', 1)
    for label, candidate, blocks in [
        ('summary-negation', changed_records, None),
        ('summary-row-drop', records[:-1], None),
        ('coverage-gap', records, BLOCKS[:-1]),
    ]:
        errors = validate(originals, pages, candidate, headings, blocks)
        changed = candidate != records or blocks is not None
        rows.append([0, label, input_hash, sha(repr(candidate)), 'rejected',
                     'pass' if changed and errors else 'fail', ';'.join(errors)])
    with args.output.open('x', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['repeat', 'check', 'input_sha256', 'output_sha256',
                         'expected_result', 'status', 'details'])
        writer.writerows(rows)
    failures = sum(row[5] != 'pass' for row in rows)
    print(f'body_blocks={len(BLOCKS)} sources={len(originals)} raw_csv={len(csv_paths)} '
          f'source_records={len(records)} repeats=5 controls={len(rows) - 5} failures={failures}')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
