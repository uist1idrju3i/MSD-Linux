#!/usr/bin/env python3
"""Replay the fixed build path filter and optionally capture CI job observations."""

import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def write_csv(path, header, rows):
    with path.open('x', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(header)
        writer.writerows(rows)


def classify(script, paths):
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        (temp / 'changed-files').write_bytes(b'\0'.join(p.encode() for p in paths) + b'\0')
        output = temp / 'output'
        env = dict(os.environ, RUNNER_TEMP=directory, GITHUB_OUTPUT=str(output))
        subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], env=env, check=True)
        result = output.read_text().strip()
        if result not in {'build=true', 'build=false'}:
            raise ValueError(f'unexpected filter output: {result!r}')
        return result.removeprefix('build=') == 'true'


def ensure_state(text):
    messages = re.findall(r'(?m)^\d{4}-\d\d-\d\dT\S+Z Published image ([^\r\n]+)\r?$', text)
    if len(messages) != 1:
        return 'ambiguous' if messages else 'not-observed'
    if messages[0].endswith(' was not found; building locally.'):
        return 'local-build'
    if messages[0].endswith(' found.'):
        return 'published'
    return 'not-observed'


def scope(args):
    source = git(args.root, 'show', f'{args.ref}:.github/workflows/build.yml').decode()
    start = source.index('          build=false\n')
    end = source.index('          echo "build=$build" >> "$GITHUB_OUTPUT"', start)
    end += len('          echo "build=$build" >> "$GITHUB_OUTPUT"')
    fragment = '\n'.join(line[10:] for line in source[start:end].splitlines())
    paths = git(args.root, 'diff', '--name-only', '-z', f'{args.pr_ref}^2...{args.pr_ref}')
    pr_paths = [p.decode() for p in paths.split(b'\0') if p]
    cases = [
        ('readme', ['README.md'], False),
        ('research', ['RESEARCH.md'], False),
        ('research-document', ['docs/research/alternatives/development.md'], False),
        ('site', ['public_html/index.html'], False),
        ('agent-rules', ['.agents/skills/experiment-record/SKILL.md'], False),
        ('claude-link', ['.claude/skills/experiment-record'], False),
        ('vendor-prose', ['vendor/yomiyasu'], False),
        ('license', ['LICENSE'], False),
        ('checker-fixture', ['tests/check-links/run.sh'], False),
        ('lint-workflow', ['.github/workflows/lint.yml'], False),
        ('monitor-script', ['.github/scripts/check-pins.py'], False),
        ('build-workflow', ['.github/workflows/build.yml'], True),
        ('signing-cli-test', ['tests/release-signing-key/run.py'], True),
        ('updater-test', ['tests/msd-update/run.sh'], True),
        ('kernel-config', ['board/cardputerzero/linux.fragment'], True),
        ('defconfig', ['configs/msd_cardputerzero_defconfig'], True),
        ('oci-input', ['docker/msd-dev.Dockerfile'], True),
        ('docs-plus-signing', ['README.md', 'tests/release-signing-key/run.py'], True),
        ('pr187-cumulative', pr_paths, True),
    ]
    rows = []
    for repeat in range(1, 6):
        for name, changed, expected in cases:
            actual = classify(fragment, changed)
            rows.append([repeat, name, len(changed), expected, actual,
                         'passed' if actual == expected else 'failed'])
    controls = [
        ('ignore-build-workflow', fragment.replace('.github/workflows/build.yml)', '__disabled__)')),
        ('ignore-all-tests', fragment.replace('tests/check-*/*', 'tests/*')),
    ]
    for name, changed in controls:
        if changed == fragment:
            raise ValueError(f'control did not change source: {name}')
        mismatches = sum(classify(changed, paths) != expected for _, paths, expected in cases)
        rows.append([0, name, len(cases), 'mismatches>0', mismatches,
                     'passed' if mismatches > 0 else 'failed'])
    marker_cases = [
        ('published-with-echoed-fallback', 'building locally\n2026-11-03T00:00:00Z Published image example found.\n', 'published'),
        ('fallback-with-echoed-success', 'Published image example found.\n2026-11-03T00:00:00Z Published image example was not found; building locally.\n', 'local-build'),
        ('echo-only', 'Published image example found.\nbuilding locally\n', 'not-observed'),
        ('conflicting-markers', '2026-11-03T00:00:00Z Published image example found.\n2026-11-03T00:00:01Z Published image example was not found; building locally.\n', 'ambiguous'),
    ]
    for repeat in range(1, 6):
        for name, text, expected in marker_cases:
            actual = ensure_state(text)
            rows.append([repeat, name, 1, expected, actual,
                         'passed' if expected == actual else 'failed'])
    write_csv(args.output_dir / 'scope.csv',
              ['repeat', 'case', 'path_count', 'expected', 'observed', 'status'], rows)
    metadata = {
        'source_ref': args.ref, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'pr_ref': args.pr_ref, 'pr_diff': 'second-parent...merge-head',
        'pr_path_count': len(pr_paths), 'repeats': 5,
        'bash': subprocess.check_output(['bash', '--version'], text=True).splitlines()[0],
        'scope': 'path case only; event/fetch/diff fail-safe paths are source review, not replayed',
    }
    with (args.output_dir / 'metadata.json').open('x') as stream:
        json.dump(metadata, stream, indent=2)
        stream.write('\n')
    if any(row[-1] != 'passed' for row in rows):
        raise ValueError('scope replay failed')


def history(args):
    rows = []
    job_rows = []
    for run_id in args.collect_run:
        data = subprocess.check_output(['gh', 'api', f'repos/{args.repository}/actions/runs/{run_id}'])
        (args.output_dir / f'run-{run_id}.json').write_bytes(data)
        run = json.loads(data)
        data = subprocess.check_output(['gh', 'api', f'repos/{args.repository}/actions/runs/{run_id}/jobs?per_page=100'])
        (args.output_dir / f'jobs-{run_id}.json').write_bytes(data)
        result = json.loads(data)
        if result['total_count'] > len(result['jobs']):
            raise ValueError('job pagination is required')
        for job in result['jobs']:
            if job['name'] not in {'build', 'changes', 'MSD tests in development image'}:
                continue
            log_state, raw, ensure = 'not-requested-skipped', b'', 'not-observed'
            if job['conclusion'] != 'skipped':
                response = subprocess.run(['gh', 'api', f'repos/{args.repository}/actions/jobs/{job["id"]}/logs'], capture_output=True)
                raw = response.stdout if response.returncode == 0 else response.stderr
                (args.output_dir / f'job-{job["id"]}.log').write_bytes(raw)
                log_state = 'downloaded' if response.returncode == 0 else 'download-failed'
                if response.returncode == 0:
                    ensure = ensure_state(raw.decode(errors='replace'))
            job_rows.append([run_id, run['head_sha'], job['id'], job['name'],
                             job['conclusion'], ensure, log_state,
                             hashlib.sha256(raw).hexdigest() if raw else '',
                             job['html_url']])
            for step in job.get('steps', []):
                a, b = step.get('started_at'), step.get('completed_at')
                elapsed = (datetime.datetime.fromisoformat(b) - datetime.datetime.fromisoformat(a)).total_seconds() if a and b else ''
                rows.append([run_id, run['head_sha'], run['event'], run['conclusion'], job['id'], job['name'], job['conclusion'], step['name'], step.get('conclusion', ''), a or '', b or '', elapsed, ensure, log_state, hashlib.sha256(raw).hexdigest() if raw else '', job['html_url']])
    write_csv(args.output_dir / 'history-steps.csv', ['run_id', 'head_sha', 'event', 'run_conclusion', 'job_id', 'job_name', 'job_conclusion', 'step_name', 'step_conclusion', 'started_at', 'completed_at', 'elapsed_seconds', 'ensure_state', 'log_state', 'log_sha256', 'job_url'], rows)
    write_csv(args.output_dir / 'history-jobs.csv', ['run_id', 'head_sha', 'job_id',
              'job_name', 'job_conclusion', 'ensure_state', 'log_state',
              'log_sha256', 'job_url'], job_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--ref', required=True)
    parser.add_argument('--pr-ref', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--repository', default='uist1idrju3i/MSD-Linux')
    parser.add_argument('--collect-run', type=int, action='append', default=[])
    args = parser.parse_args()
    args.output_dir.mkdir(exist_ok=False)
    scope(args)
    if args.collect_run:
        history(args)


if __name__ == '__main__':
    main()
