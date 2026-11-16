#!/usr/bin/env python3
"""全残条件を一括生成・照合する。QEMUは起動しない。"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import time

import followup
import initramfs_check
import remaining


def run(args):
    source = sorted(path for path in args.base.iterdir() if (path / 'case.json').exists())
    if len(source) != 10:
        raise ValueError('expected ten source cases')
    for path in source:
        followup.validate(path)
    if shutil.disk_usage(args.destination.parent).free < 100 * 1024 ** 3:
        raise ValueError('less than 100 GiB free')
    args.destination.mkdir()
    start = time.monotonic()
    record = dict(start_utc=datetime.now(timezone.utc).isoformat(),
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  kernel=followup.sha(args.kernel), stages={})
    sources = args.destination / 'sources'
    sources.mkdir()
    for path in sorted(Path(__file__).parent.iterdir()):
        if path.suffix in ('.py', '.sh', '.tsv'):
            shutil.copy2(path, sources / path.name)
    for stage in ('B', 'C', 'D', 'E', 'F'):
        stage_start = time.monotonic()
        out = args.destination / ('cases-' + stage.lower())
        try:
            if stage == 'B':
                followup.refresh_b(argparse.Namespace(base=args.base,
                    tree=args.base / 'repacked-seed/rootfs-tree', destination=out))
                old = (args.base / 'B-clean-ram/initramfs.cpio.gz').read_bytes()
                new = (out / 'ram.cpio.gz').read_bytes()
                before, after = initramfs_check.entries(old), initramfs_check.entries(new)
                if set(after) - set(before) != {'lib64', 'usr/lib64'} or any(after.get(k) != v for k, v in before.items()):
                    raise ValueError('initramfs changed beyond aliases')
                try:
                    initramfs_check.check(old)
                except ValueError as error:
                    followup.save(out / 'old-negative.json', dict(rejected=True, reason=str(error)))
                else:
                    raise ValueError('old missing-alias archive accepted')
            else:
                remaining.generate(argparse.Namespace(base=args.base, kernel=args.kernel,
                                   destination=out, stage=stage, formatter=args.formatter))
            cases = sorted(p for p in out.iterdir() if (p / 'case.json').exists())
            if len(cases) != dict(B=10, C=10, D=18, E=4, F=1)[stage]:
                raise ValueError('wrong case count')
            for case in cases:
                followup.validate(case)
            record['stages'][stage] = dict(passed=True, cases=len(cases),
                manifests={case.name: followup.sha(case / 'inputs.json') for case in cases})
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            record['stages'][stage] = dict(passed=False, error=type(error).__name__ + ': ' + str(error))
        record['stages'][stage]['wall_seconds'] = time.monotonic() - stage_start
        record['wall_seconds'] = time.monotonic() - start
        followup.save(args.destination / 'host-dry.json', record)
        print(stage, json.dumps(record['stages'][stage]), flush=True)
    if not all(item['passed'] for item in record['stages'].values()):
        raise RuntimeError('host dry check failed; no boot or formal runs allowed')
    print('ok - all 43 remaining smoke inputs generated and host-verified; zero QEMU boots', flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name in ('base', 'kernel', 'formatter', 'destination'):
        parser.add_argument(name, type=Path)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
