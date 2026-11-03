"""Check the real build workflow's filter and its always-on signing regression."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / '.github/workflows/build.yml').read_text()
SIGNING_PATH = 'tests/release-signing-key/run.py'
FAKE_GIT = '''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
args = sys.argv[1:]
with open(os.environ['GIT_CALLS'], 'a') as stream:
    stream.write(' '.join(args) + '\\n')
if args[0] == 'cat-file':
    if args[-1] == 'b' * 40 + '^{commit}':
        sys.exit(int(os.environ['MISSING_BASE'] or '0'))
    sys.exit(int(bool(os.environ['MISSING_HEAD']) and not Path(os.environ['FETCHED']).exists()))
if args[0] == 'fetch':
    if os.environ['FETCH_FAIL']:
        sys.exit(1)
    Path(os.environ['FETCHED']).touch()
    sys.exit(0)
if args[0] == 'diff':
    assert args == ['diff', '--name-only', '-z', 'b' * 40 + '...' + 'a' * 40], args
    if os.environ['DIFF_FAIL']:
        sys.exit(1)
    sys.stdout.buffer.write(bytes.fromhex(os.environ['CHANGED_HEX']))
    sys.exit(0)
raise AssertionError(args)
'''


def filter_script(workflow):
    block = workflow.split('name: Check whether the build is needed\n', 1)[1]
    block = block.split('        run: |\n', 1)[1].split('\n  msd-update-tests:', 1)[0]
    return textwrap.dedent(block)


def signing_enabled(workflow):
    job = workflow.split('\n  msd-update-tests:\n', 1)[1].split('\n  build:\n', 1)[0]
    return (
        not re.search(r'^    (?:if|needs):', job, re.M)
        and f'docker/msd-dev python3 {SIGNING_PATH} --output-dir ' in job
        and 'docker/msd-dev python3 tests/check-build-scope/run.py' in job
    )


def classify(workflow, paths, event='pull_request', **flags):
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        stub = temp / 'git'
        stub.write_text(FAKE_GIT)
        stub.chmod(0o700)
        output, calls = temp / 'output', temp / 'calls'
        env = dict(
            os.environ, PATH=f'{temp}:{os.environ["PATH"]}',
            RUNNER_TEMP=directory, GITHUB_OUTPUT=str(output),
            EVENT_NAME=event, BASE_SHA='b' * 40, HEAD_SHA='a' * 40, PR_NUMBER='123',
            CHANGED_HEX=b''.join(path.encode() + b'\0' for path in paths).hex(),
            GIT_CALLS=str(calls), FETCHED=str(temp / 'fetched'),
            MISSING_BASE='', MISSING_HEAD='', FETCH_FAIL='', DIFF_FAIL='',
        )
        env.update(flags)
        subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', filter_script(workflow)],
                       env=env, check=True, capture_output=True, timeout=15)
        result = output.read_text().strip()
        if result not in {'build=true', 'build=false'}:
            raise AssertionError(result)
        return result == 'build=true', calls.read_text() if calls.exists() else ''


class BuildScope(unittest.TestCase):
    def test_lightweight_paths(self):
        for paths in (['README.md'], [SIGNING_PATH], ['docs/UPDATE.md', SIGNING_PATH],
                      ['tests/check-build-scope/run.py']):
            with self.subTest(paths=paths):
                self.assertFalse(classify(WORKFLOW, paths)[0])

    def test_product_and_unknown_paths(self):
        for path in ('.github/workflows/build.yml', 'package/msd-update/msd-update',
                     'tests/msd-update/run.sh', 'configs/msd_cardputerzero_defconfig',
                     'docker/msd-dev.Dockerfile', 'unknown path\nwith newline',
                     'tests/release-signing-key/new-file.py'):
            with self.subTest(path=path):
                self.assertTrue(classify(WORKFLOW, ['README.md', SIGNING_PATH, path])[0])

    def test_cumulative_diff_and_event_contract(self):
        for event in ('push', 'pull_request'):
            result, calls = classify(WORKFLOW, ['README.md'], event)
            self.assertFalse(result)
            self.assertIn('diff --name-only -z ' + 'b' * 40 + '...' + 'a' * 40, calls)
        for event in ('schedule', 'workflow_dispatch', 'unrecognized-event'):
            result, calls = classify(WORKFLOW, ['README.md'], event)
            self.assertTrue(result)
            self.assertEqual(calls, '')

    def test_uncertain_diff_fails_closed(self):
        for flags in ({'MISSING_BASE': '1'}, {'BASE_SHA': '0' * 40},
                      {'MISSING_HEAD': '1', 'FETCH_FAIL': '1'}, {'DIFF_FAIL': '1'}):
            with self.subTest(flags=flags):
                self.assertTrue(classify(WORKFLOW, ['README.md'], **flags)[0])
        result, calls = classify(WORKFLOW, [SIGNING_PATH], MISSING_HEAD='1')
        self.assertFalse(result)
        self.assertIn('refs/pull/123/head:refs/remotes/pull/123/head', calls)

    def test_signing_regression_is_always_on(self):
        self.assertTrue(signing_enabled(WORKFLOW))

    def test_mutations_are_detected(self):
        no_call = WORKFLOW.replace(f'docker/msd-dev python3 {SIGNING_PATH}', 'disabled')
        self.assertNotEqual(no_call, WORKFLOW)
        self.assertFalse(signing_enabled(no_call))
        gated = WORKFLOW.replace('  msd-update-tests:\n', '  msd-update-tests:\n    needs: changes\n')
        self.assertFalse(signing_enabled(gated))
        no_exemption = WORKFLOW.replace(f'|{SIGNING_PATH}|', '|')
        self.assertNotEqual(no_exemption, WORKFLOW)
        self.assertTrue(classify(no_exemption, [SIGNING_PATH])[0])
        ignore_products = WORKFLOW.replace('tests/check-*/*', 'tests/*')
        self.assertFalse(classify(ignore_products, ['tests/msd-update/run.sh'])[0])
        ignore_workflow = WORKFLOW.replace('.github/workflows/build.yml)', 'disabled)')
        self.assertFalse(classify(ignore_workflow, ['.github/workflows/build.yml'])[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
