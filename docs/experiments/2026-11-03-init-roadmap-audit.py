#!/usr/bin/env python3
"""Audit research provenance, roadmap references and coverage; not OS behavior."""

import argparse
import concurrent.futures
import copy
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = 'docs/research/'
STATES = {
    'implemented-hw-unverified', 'historical-host-qemu', 'static-only',
    'design-only', 'not-implemented', 'approval-pending', 'dependency-pending',
    'deferred', 'not-selected', 'conditional',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_csv(root, path):
    with (root / path).open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    require(rows and all(None not in row for row in rows), 'empty or extra CSV cells')
    return rows


def question_rows(root):
    rows = []
    for line in (root / (RESEARCH + 'verification/open-questions.md')).read_text().splitlines():
        if line.startswith('| ') and not line.startswith('| 主題'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            require(len(cells) == 4, 'question table width changed')
            rows.append((cells[0], cells[-1].split()))
    return rows


def validate_work(root, rows):
    known = {row['id'] for row in rows}
    require(len(known) == len(rows), 'duplicate work ID')
    for row in rows:
        require(re.fullmatch(r'R[0-9]{2,}', row['id']), 'invalid work ID')
        require(row['state'] in STATES, 'invalid work state')
        require(row['priority'] in {'P0', 'P1', 'P2', 'P3'}, 'invalid priority')
        require(row['decision'] in {'user', 'technical', 'none'}, 'invalid decision')
        for key, value in row.items():
            if key not in {'depends_on', 'pr_urls'}:
                require(isinstance(value, str) and value.strip(), 'missing field: ' + key)
        for path in row['evidence_paths'].split('|'):
            require(not Path(path).is_absolute() and '..' not in Path(path).parts,
                    'evidence path escapes repository')
            require((root / path).is_file(), 'missing evidence: ' + path)
        for url in filter(None, row['pr_urls'].split('|')):
            require(re.fullmatch(r'https://github.com/uist1idrju3i/MSD-Linux/pull/[0-9]+', url),
                    'invalid PR URL')
        dependencies = list(filter(None, row['depends_on'].split('|')))
        require(len(dependencies) == len(set(dependencies)), 'duplicate dependency')
        require(set(dependencies) <= known, 'unknown dependency')
    visiting, visited = set(), set()
    graph = {r['id']: list(filter(None, r['depends_on'].split('|'))) for r in rows}

    def visit(node):
        require(node not in visiting, 'dependency cycle')
        if node not in visited:
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

    for node in known:
        visit(node)


def validate_coverage(root, work, coverage):
    known = {row['id'] for row in work}
    origins = {row['origin']: row for row in coverage}
    require(len(origins) == len(coverage), 'duplicate origin')
    referenced = set()
    for row in coverage:
        require((root / row['source_path']).is_file(), 'missing coverage source')
        ids = row['work_ids'].split('|')
        require(set(ids) <= known and len(ids) == len(set(ids)), 'invalid coverage target')
        referenced.update(ids)
    require(referenced == known, 'unreferenced work item')
    questions = question_rows(root)
    expected = {'question:' + title for title, _ in questions}
    require({key for key in origins if key.startswith('question:')} == expected,
            'missing or obsolete question coverage')
    original_keys = []
    for title, keys in questions:
        mapped = origins['question:' + title]['source_keys'].split()
        require(mapped == keys, 'original Q/R keys changed')
        original_keys.extend(keys)
    require(len(original_keys) == len(set(original_keys)), 'duplicate original Q/R key')
    catalog = (root / (RESEARCH + 'verification/experiment-catalog.md')).read_text()
    experiments = set(re.findall(r'^\| (S[0-9]+) \|', catalog, re.M))
    require({key for key in origins if key.startswith('experiment:')} ==
            {'experiment:' + name for name in experiments}, 'experiment coverage mismatch')
    return len(questions), len(original_keys), len(experiments)


def validate_sources(sources):
    require(bool(sources), 'empty source list')
    ids = set()
    for source in sources:
        require(source['id'] not in ids and re.fullmatch(r'[a-zA-Z0-9_-]+', source['id']),
                'duplicate or unsafe source ID')
        ids.add(source['id'])
        require(source['url'].startswith('https://'), 'source URL must be HTTPS')
        require(bool(source.get('checked_at')), 'source date missing')
        if source.get('status') == 200:
            require(re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')),
                    'source digest missing')
            require(isinstance(source.get('bytes'), int) and source['bytes'] > 0,
                    'source bytes missing')
        else:
            require(source.get('status') or source.get('error'), 'unexplained fetch failure')


def rejected(operation):
    try:
        operation()
    except (ValueError, KeyError):
        return
    raise ValueError('negative control was accepted')


def self_test(root, work, coverage, sources):
    bad = copy.deepcopy(work)
    bad[0]['depends_on'] = bad[0]['id']
    rejected(lambda: validate_work(root, bad))
    bad = copy.deepcopy(work)
    bad[0]['depends_on'] = 'R9999'
    rejected(lambda: validate_work(root, bad))
    bad = copy.deepcopy(work)
    bad[0]['evidence_paths'] = 'missing-evidence-file'
    rejected(lambda: validate_work(root, bad))
    bad = copy.deepcopy(work)
    bad[0]['state'] = 'passed'
    rejected(lambda: validate_work(root, bad))
    bad = copy.deepcopy(coverage)
    bad.pop(0)
    rejected(lambda: validate_coverage(root, work, bad))
    bad = copy.deepcopy(coverage)
    bad[0]['source_keys'] = 'Q9999'
    rejected(lambda: validate_coverage(root, work, bad))
    bad = copy.deepcopy(sources)
    bad[0].pop('sha256')
    rejected(lambda: validate_sources(bad))
    rejected(lambda: validate_sources(sources + [sources[0]]))
    return 8


def fetch_one(source, output):
    record = {'id': source['id'], 'url': source['url'],
              'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'MSD-Linux-research/1'})
    try:
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(16 * 1024 * 1024 + 1)
            require(len(raw) <= 16 * 1024 * 1024, 'source exceeds fetch size limit')
            record.update(status=response.status, final_url=response.geturl(),
                          bytes=len(raw), sha256=digest(raw))
            (output / (source['id'] + '.raw')).write_bytes(raw)
    except (OSError, ValueError) as error:
        record.update(status=None, error=str(error))
    record['same_body_as_snapshot'] = bool(
        source.get('sha256') and record.get('sha256') == source['sha256'])
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--output', type=Path, help='New CSV; refuse overwrite')
    parser.add_argument('--fetch-sources', type=Path, help='Fetch into a new directory; no credentials')
    parser.add_argument('--verify-sources', type=Path, help='Verify saved raw bodies against snapshot')
    args = parser.parse_args()
    work = load_csv(ROOT, RESEARCH + 'pending-work.csv')
    coverage = load_csv(ROOT, RESEARCH + 'roadmap-coverage.csv')
    sources = json.loads((ROOT / (RESEARCH + 'alternatives/init-sources.json')).read_text())['sources']
    validate_work(ROOT, work)
    counts = validate_coverage(ROOT, work, coverage)
    validate_sources(sources)
    controls = self_test(ROOT, work, coverage, sources) if args.self_test else 0
    if args.verify_sources:
        for source in sources:
            if source.get('sha256'):
                raw = (args.verify_sources / (source['id'] + '.raw')).read_bytes()
                require(len(raw) == source['bytes'] and digest(raw) == source['sha256'],
                        'raw source mismatch: ' + source['id'])
    if args.fetch_sources:
        args.fetch_sources.mkdir(exist_ok=False)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            fetched = list(executor.map(lambda s: fetch_one(s, args.fetch_sources), sources))
        (args.fetch_sources / 'sources.json').write_text(json.dumps(fetched, indent=2) + '\n')
        print(json.dumps({'fetches': len(fetched), 'status_200': sum(
            s.get('status') == 200 for s in fetched), 'scope': 'Retrieval is not content review'}))
    row = dict(work_items=len(work), origins=len(coverage), questions=counts[0],
               original_keys=counts[1], experiments=counts[2], sources=len(sources),
               negative_controls=controls, status='passed', scope='static-only')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, list(row), lineterminator='\n')
    writer.writeheader()
    writer.writerow(row)
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='') as stream:
            stream.write(output.getvalue())
    print(output.getvalue(), end='')


if __name__ == '__main__':
    main()
