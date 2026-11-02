from pathlib import Path
import argparse
import json
import os
import platform
import shutil
import csv
import hashlib
import subprocess
import tempfile

parser = argparse.ArgumentParser(description='Check Ed25519 CLI operations using disposable test keys')
parser.add_argument('--output-dir', required=True, type=Path)
args = parser.parse_args()
out = args.output_dir.resolve()
os.umask(0o077)
out.mkdir(mode=0o700, exist_ok=False)
metadata = {'openssl': subprocess.check_output(['openssl', 'version'], text=True).strip(), 'openssl_binary_sha256': hashlib.sha256(Path(shutil.which('openssl')).read_bytes()).hexdigest(), 'host': platform.platform(), 'trials': 5, 'key_scope': 'disposable test keys only; never product keys'}
(out / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
rows = []
for trial in range(1, 6):
    with tempfile.TemporaryDirectory(prefix='test-key-', dir=out) as name:
        cwd = Path(name)
        commands = [
            ('generate', ['openssl','genpkey','-algorithm','Ed25519','-out','private.pem'], 0),
            ('derive-public', ['openssl','pkey','-in','private.pem','-pubout','-out','public.pem'], 0),
            ('check-private', ['openssl','pkey','-in','private.pem','-check','-noout'], 0),
            ('inspect-public', ['openssl','pkey','-pubin','-in','public.pem','-text','-noout'], 0),
            ('public-der', ['openssl','pkey','-pubin','-in','public.pem','-outform','DER','-out','public.der'], 0),
            ('fingerprint', ['openssl','dgst','-sha256','public.der'], 0),
            ('sign', ['openssl','pkeyutl','-sign','-rawin','-inkey','private.pem','-in','probe.txt','-out','probe.sig'], 0),
            ('verify', ['openssl','pkeyutl','-verify','-pubin','-rawin','-inkey','public.pem','-in','probe.txt','-sigfile','probe.sig'], 0),
            ('reject-tamper', ['openssl','pkeyutl','-verify','-pubin','-rawin','-inkey','public.pem','-in','tampered.txt','-sigfile','probe.sig'], 1),
            ('generate-other', ['openssl','genpkey','-algorithm','Ed25519','-out','other-private.pem'], 0),
            ('derive-other', ['openssl','pkey','-in','other-private.pem','-pubout','-out','other-public.pem'], 0),
            ('reject-wrong-key', ['openssl','pkeyutl','-verify','-pubin','-rawin','-inkey','other-public.pem','-in','probe.txt','-sigfile','probe.sig'], 1),
        ]
        (cwd/'probe.txt').write_bytes(b'MSD/Linux release signing key check\n')
        (cwd/'tampered.txt').write_bytes(b'MSD/Linux release signing key check!\n')
        for ident, command, expected in commands:
            result = subprocess.run(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            log = out/f'key-check-{trial}-{ident}.log'
            log.write_bytes(result.stdout)
            rows.append([trial,ident,' '.join(command),expected,result.returncode,len(result.stdout),hashlib.sha256(result.stdout).hexdigest()])
            assert result.returncode == expected, (trial,ident,result.returncode)
            if ident == 'inspect-public':
                assert b'ED25519' in result.stdout
            if ident == 'fingerprint':
                assert hashlib.sha256((cwd/'public.der').read_bytes()).hexdigest().encode() in result.stdout
        assert len((cwd/'probe.sig').read_bytes()) == 64
        # Do not retain private test keys in logs or result artifacts.
with (out/'key-checks.csv').open('w',newline='') as handle:
    writer=csv.writer(handle,lineterminator='\n')
    writer.writerow(['trial','case','command','expected_exit','actual_exit','output_bytes','output_sha256'])
    writer.writerows(rows)
print(f'{len(rows)} command results across 5 independent test-key trials matched expectations')
