#!/usr/bin/env python3
"""保存済みE34を再集計する。過去の集計器ではなく監査時の可搬版。"""
import argparse
import csv
import math
from pathlib import Path
import statistics
import sys

FIELDS = ('wall_seconds', 'write_sectors', 'write_ios', 'quiesce_write_sectors',
          'quiesce_write_ios', 'quiesce_seconds', 'last_write_s', 'mem_available_kb',
          'mkfs_seconds', 'mount_seconds', 'fsck_seconds', 'lost_records', 'fsync_lost')


def aggregate(plan, attempts):
    keys = []
    expected = set()
    for config, test, repeat in plan:
        key = (config, test, repeat)
        if key in expected:
            raise ValueError('duplicate plan row')
        expected.add(key)
        if key[:2] not in keys:
            keys.append(key[:2])
    if not expected:
        raise ValueError('empty plan')
    groups = {}
    seen = set()
    ids = set()
    failures = []
    for row in attempts:
        if row['run_id'] in ids:
            raise ValueError('duplicate run ID')
        ids.add(row['run_id'])
        if row['status'] != 'ok':
            if row['status'] != 'fail:terminated_signal_15':
                raise ValueError('unexpected failed status')
            failures.append(row['run_id'])
            continue
        key = (row['config'], row['test'], row['repetition'])
        if key not in expected or key in seen:
            raise ValueError('unexpected or duplicate successful repetition')
        seen.add(key)
        if not row.get('write_sectors') or not row.get('wall_seconds'):
            raise ValueError('missing required metric')
        groups.setdefault(key[:2], []).append(row)
    if seen != expected:
        raise ValueError('partial results')
    result = []
    for key in keys:
        rows = groups[key]
        output = [*key, str(len(rows))]
        for field in FIELDS:
            values = [float(row[field]) for row in rows if row.get(field) not in ('', 'none', None)]
            if any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError('invalid metric')
            output.extend([str(statistics.median(values)), str(min(values)), str(max(values))]
                          if values else ['', '', ''])
        result.append(output)
    return result, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--check-csv', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.plan.open() as stream:
            plan = list(csv.reader(stream, delimiter='\t'))
        with args.summary.open() as stream:
            attempts = list(csv.DictReader(stream))
        result, failures = aggregate(plan, attempts)
        header = ['config', 'test', 'n'] + [f'{f}_{s}' for f in FIELDS for s in ('median', 'min', 'max')]
        with args.check_csv.open() as stream:
            if list(csv.reader(stream)) != [header, *result]:
                raise ValueError('committed aggregate mismatch')
    except (OSError, ValueError, KeyError) as error:
        print('error:', error, file=sys.stderr)
        return 1
    print(f'ok - E34: successful={sum(int(r[2]) for r in result)} groups={len(result)} interrupted={len(failures)} committed aggregate matches')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
