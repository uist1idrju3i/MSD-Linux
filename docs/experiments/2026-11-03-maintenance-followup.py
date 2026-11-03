"""Run the maintenance and workflow checks in the pinned development container."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--collect-sources', action='store_true')
args = parser.parse_args()
out = args.output_dir.resolve()
out.mkdir(parents=True, exist_ok=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


metadata = {
    'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'scope': 'working-tree host/static checks; not target OpenSSL, QEMU or hardware',
    'python': sys.version,
    'platform': platform.platform(),
    'openssl': subprocess.check_output(['openssl', 'version'], text=True).strip(),
    'inputs': {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in [
        ROOT / '.github/scripts/check-pins.py', ROOT / '.github/workflows/build.yml',
        ROOT / '.github/workflows/pins-check.yml', ROOT / 'tests/check-pins/run.sh',
        ROOT / 'tests/check-build-scope/run.py', ROOT / 'tests/release-signing-key/run.py',
    ]},
}
(out / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
rows = []
for repeat in range(1, 6):
    suites = [
        ('pins', ['tests/check-pins/run.sh']),
        ('build-scope', ['python3', 'tests/check-build-scope/run.py']),
        ('signing-cli', ['python3', 'tests/release-signing-key/run.py',
                         '--output-dir', str(out / f'keys-{repeat}')]),
    ]
    for name, command in suites:
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f'{repeat}-{name}.log').write_bytes(result.stdout)
        rows.append([repeat, name, 0, result.returncode, len(result.stdout),
                     digest(result.stdout), 'passed' if result.returncode == 0 else 'failed'])
with (out / 'results.csv').open('x', newline='') as stream:
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['repeat', 'suite', 'expected_exit', 'actual_exit',
                     'output_bytes', 'output_sha256', 'status'])
    writer.writerows(rows)

if args.collect_sources:
    spec = importlib.util.spec_from_file_location('pins', ROOT / '.github/scripts/check-pins.py')
    pins = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pins)
    sources = []
    sha = pins.buildroot_gitlink_sha(ROOT)
    urls = [
        f'https://raw.githubusercontent.com/buildroot/buildroot/{sha}/package/libopenssl/libopenssl.mk',
        'https://openssl-library.org/source/',
        'https://openssl-library.org/policies/releasestrat/',
    ]
    for index, url in enumerate(urls):
        record = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat()}
        try:
            body = pins.fetch(url).encode()
            (out / f'source-{index}.txt').write_bytes(body)
            record.update(status='fetched', bytes=len(body), sha256=digest(body))
        except (OSError, ValueError) as exc:
            record.update(status='unavailable', error=str(exc))
        sources.append(record)
    (out / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n')
    if any(source['status'] != 'fetched' for source in sources):
        raise SystemExit('Source collection incomplete; inspect sources.json')
    downloads = pins.parse_openssl_downloads((out / 'source-1.txt').read_text())
    (out / 'releases.json').write_text(json.dumps({
        series: {'version': value[0], 'expires': value[1].isoformat()}
        for series, value in downloads.items()
    }, indent=2) + '\n')

if any(row[-1] != 'passed' for row in rows):
    raise SystemExit('Regression failures; inspect results.csv and logs')
print(f'{len(rows)} suite runs passed; inspect results.csv and all logs')
