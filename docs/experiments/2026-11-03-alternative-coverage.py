#!/usr/bin/env python3
"""Map frozen dependency inventories to comparison and ownership boundaries."""
import argparse
import copy
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path


FAMILIES = {
    'base': 'apt base-files base-passwd cdebconf debconf debian-archive-keyring dpkg hostname init-system-helpers media-types netbase rust-sequoia-sqv shadow systemd sysvinit tzdata util-linux',
    'commands': 'bash coreutils dash debianutils diffutils findutils gawk grep mawk sed',
    'compiler': 'binutils build-essential gcc-14 gcc-defaults glibc gmp isl linux libxcrypt mpclib3 mpfr4 rpcsvc-proto',
    'build': 'bc bison cmake flex liberror-perl m4 make-dfsg patch perl popt rhash',
    'python': 'expat gdbm libffi python-pip python3-defaults python3.13 setuptools sqlite3',
    'images': 'cpio cryptsetup device-tree-compiler dosfstools e2fsprogs elfutils file libarchive lvm2 mtools squashfs-tools',
    'compression': 'brotli bzip2 gzip libzstd lz4 lzo2 tar unzip xxhash xz-utils zlib',
    'transport': 'ca-certificates curl git libidn2 libpsl libssh2 libunistring nghttp2 nghttp3 ngtcp2 rsync rtmpdump wget',
    'auth': 'cyrus-sasl2 gnutls28 keyutils krb5 libcap-ng libseccomp libtasn1-6 nettle openldap openssl p11-kit pam',
    'qemu': 'glib2.0 libslirp pixman',
    'helpers': 'acl attr audit db5.3 jansson json-c libbsd libcap2 libjsoncpp libmd libselinux libsemanage libsepol libsigsegv libuv1 libxml2 libyaml ncurses pcre2 procps readline',
}
ROUTES = {name: family for family, names in FAMILIES.items() for name in names.split()}
if len(ROUTES) != sum(len(names.split()) for names in FAMILIES.values()):
    raise ValueError('duplicate source-package classification')


def read_json(path):
    return json.loads(path.read_text())


def csv_bytes(rows, fields):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def package_key(name, arch):
    parts = name.split(':')
    if len(parts) > 2 or (len(parts) == 2 and parts[1] != arch):
        raise ValueError('unexpected multiarch suffix')
    return parts[0], arch


def check_oci(packages, baseline):
    actual = {package_key(p['package'], p['architecture']): p['version'] for p in packages}
    expected = {package_key(p['name'], p['architecture']): p['installed_version'] for p in baseline}
    if len(actual) != len(packages) or len(expected) != len(baseline) or actual != expected:
        raise ValueError('OCI inventory differs from baseline')
    if {p['source_package'] for p in packages} != ROUTES.keys():
        raise ValueError('source-package classification differs from frozen population')


def check_parents(rows, known):
    for row in rows:
        contexts = json.loads(row['contexts'])
        if not contexts or any(c['action'] not in known for c in contexts):
            raise ValueError('missing parent Action')


def collect_oci():
    fmt = '${Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\t${Depends}\t${Pre-Depends}\t${Essential}\t${Priority}\t${binary:Synopsis}\n'
    rows = []
    for line in subprocess.check_output(['dpkg-query', '-W', '-f=' + fmt], text=True).splitlines():
        fields = line.split('\t')
        if len(fields) != 10:
            raise ValueError('unexpected dpkg record width')
        item = dict(zip(['package', 'version', 'architecture', 'source_package',
                         'source_version', 'depends', 'pre_depends', 'essential',
                         'priority', 'synopsis'], fields))
        copyright = Path('/usr/share/doc') / item['package'] / 'copyright'
        item['copyright_present'] = copyright.is_file()
        if copyright.is_file():
            raw = copyright.read_bytes()
            item['copyright_sha256'] = hashlib.sha256(raw).hexdigest()
            item['copyright_bytes'] = len(raw)
            item['observed_license_fields'] = sorted(set(re.findall(
                r'^License: (.+)$', raw.decode(errors='replace'), re.M)))
        rows.append(item)
    return {'packages': rows, 'python': subprocess.check_output(
        ['python3', '--version'], text=True).strip()}


def generate(root, oci_path, license_path):
    dep = root / 'docs/research/dependencies'
    alt = root / 'docs/research/alternatives'
    oci = read_json(oci_path)['packages']
    check_oci(oci, read_json(dep / 'development-apt.json')['packages'])
    actions = read_json(dep / 'actions-recursive.json')
    licenses = {(a['repository'], a['commit']): a for a in read_json(license_path) if a['status'] == 200}
    ids = {(a['repository'], a['commit'], a['suffix']): f'A{i:02}' for i, a in enumerate(actions, 1)}
    if len(ids) != len(actions):
        raise ValueError('duplicate Action reference')
    children = {(repo, commit, '') for a in actions for repo, commit in a['children']}
    if not children <= ids.keys():
        raise ValueError('missing child Action')
    direct_refs = set(re.findall(r'uses:\s*([\w.-]+/[\w./-]+)@([0-9a-f]{40})', '\n'.join(
        p.read_text() for p in sorted((root / '.github/workflows').glob('*.yml')))))
    known_direct = {(a['repository'] + ('/' + a['suffix'] if a['suffix'] else ''), a['commit'])
                    for a in actions if (a['repository'], a['commit'], a['suffix']) not in children}
    if direct_refs != known_direct:
        raise ValueError('workflow Action references differ from frozen inventory')
    ar, contexts = [], {}
    for a in actions:
        key = (a['repository'], a['commit'], a['suffix'])
        proof = licenses[(a['repository'], a['commit'])]
        ar.append(dict(id=ids[key], repository=a['repository'], commit=a['commit'], suffix=a['suffix'],
                       using=a['using'], relation='child' if key in children else 'direct',
                       children=';'.join(ids[(repo, commit, '')] for repo, commit in a['children']),
                       comparison_document='ci-actions.md', root_license='MIT', license_url=proof['url'],
                       license_sha256=proof['sha256']))
        for lock in a['source_lockfiles']:
            if lock['filename'] != 'package-lock.json':
                continue
            if lock.get('status') == 'not-present':
                if a['using'] != 'composite':
                    raise ValueError('missing Node Action lockfile')
                continue
            for p in lock['packages']:
                name = p['path'].split('node_modules/')[-1]
                if not p['path'].startswith('node_modules/') or not name or not p['version']:
                    raise ValueError('unexpected npm identity')
                context = dict(action=ids[key], dev=p.get('dev'), optional=p.get('optional'), license=p.get('license'))
                contexts.setdefault((name, p['version']), set()).add(encoded(context))
    npm = [dict(name=name, version=version,
                contexts='[' + ','.join(sorted(value)) + ']', comparison_document='ci-actions.md')
           for (name, version), value in sorted(contexts.items())]
    registry = {(p['name'], v) for p in read_json(dep / 'actions-npm-latest.json') for v in p['source_versions']}
    if registry != contexts.keys():
        raise ValueError('npm population differs from registry comparison')
    check_parents(npm, set(ids.values()))
    dockerfile = (root / 'docker/msd-dev.Dockerfile').read_text().split(' AS msd-dev\n', 1)[1]
    direct = set()
    for block in re.findall(r'apt-get[^\n]*?\sinstall\s+(.*?)(?=\s*&&)', dockerfile, re.S):
        direct.update(token for token in block.replace('\\', ' ').split()
                      if re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', token))
    if not direct or not direct <= {p['package'] for p in oci}:
        raise ValueError('unresolved direct APT selection')
    # Dependency alternatives remain in the metadata; this reverse graph records installed candidates only.
    reverse = {p['package']: set() for p in oci}
    for p in oci:
        for group in (p['depends'] + ',' + p['pre_depends']).split(','):
            for alternative in group.split('|'):
                match = re.match(r'\s*([a-z0-9][a-z0-9+.-]*)', alternative)
                if match and match[1] in reverse:
                    reverse[match[1]].add(p['package'])
    rows = []
    for p in sorted(oci, key=lambda p: p['package']):
        family = ROUTES[p['source_package']]
        rows.append(dict(package=p['package'], architecture=p['architecture'], version=p['version'],
                         source_package=p['source_package'], source_version=p['source_version'], family=family,
                         selected_in_final_stage=str(p['package'] in direct).lower(), essential=p['essential'],
                         installed_reverse_dependencies=';'.join(sorted(reverse[p['package']])),
                         observed_license_fields=encoded(p.get('observed_license_fields', [])),
                         copyright_sha256=p.get('copyright_sha256', ''), comparison_document='oci-components.md'))
    go = [dict(module=p['module'], version=p['installed'], parent='actionlint',
               comparison_document='oci-components.md') for p in read_json(dep / 'actionlint-go-modules.json')]
    with (alt / 'coverage.csv').open() as f:
        covered = list(csv.DictReader(f))
    with (root / 'docs/research/component-options/packages.csv').open() as f:
        original = list(csv.DictReader(f))
    identity = lambda p, scope: (p['component'], p[scope], p['show_info_version'], p['sbom_version'])
    if len(covered) != len(original) or {identity(p, 'scope') for p in covered} != {identity(p, 'role') for p in original}:
        raise ValueError('Buildroot comparison differs from original population')
    for item in covered + ar + rows + npm + go:
        if not (alt / item['comparison_document']).is_file():
            raise ValueError('missing comparison document')
    outputs = {}
    for filename, records in [('oci-coverage.csv', rows), ('action-coverage.csv', ar),
                               ('npm-coverage.csv', npm), ('go-coverage.csv', go)]:
        outputs[filename] = csv_bytes(records, list(records[0]))
    summary = dict(buildroot=len(covered), oci=len(rows), source_packages=len(ROUTES), actions=len(ar),
                   direct_actions=len(known_direct), child_actions=len(children), npm_names=len({p['name'] for p in npm}),
                   npm_name_versions=len(npm), go_modules=len(go), direct_final_apt=len(direct),
                   copyright_files=sum(p['copyright_present'] for p in oci),
                   families={f: sum(p['family'] == f for p in rows) for f in FAMILIES})
    return outputs, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect-oci', action='store_true')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--oci-metadata', type=Path)
    parser.add_argument('--licenses', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if args.collect_oci:
        print(json.dumps(collect_oci(), indent=2))
        return
    if not all([args.oci_metadata, args.licenses, args.output_dir]):
        parser.error('metadata, licenses and a new output directory are required')
    args.output_dir.mkdir(exist_ok=False)
    checks, baseline = [], None
    for iteration in range(1, 6):
        outputs, summary = generate(args.root, args.oci_metadata, args.licenses)
        checks.append(dict(check='repeat', iteration=iteration, passed=baseline is None or outputs == baseline))
        if not checks[-1]['passed']:
            raise ValueError('non-deterministic output')
        baseline = outputs
    oci = read_json(args.oci_metadata)['packages']
    expected = read_json(args.root / 'docs/research/dependencies/development-apt.json')['packages']
    for name in ['missing-package', 'wrong-version', 'unknown-source']:
        modified = copy.deepcopy(oci)
        if name == 'missing-package':
            modified.pop()
        elif name == 'wrong-version':
            modified[0]['version'] += '-mutant'
        else:
            modified[0]['source_package'] = 'unknown-source'
        try:
            check_oci(modified, expected)
        except ValueError:
            checks.append(dict(check=name, iteration=1, passed=True))
        else:
            raise ValueError('negative control was not rejected')
    try:
        check_parents([dict(contexts=encoded([dict(action='missing')]))], {'A01'})
    except ValueError:
        checks.append(dict(check='missing-parent', iteration=1, passed=True))
    else:
        raise ValueError('missing parent accepted')
    inputs = [args.oci_metadata, args.licenses, Path(__file__),
              args.root / 'docker/msd-dev.Dockerfile', *sorted((args.root / 'docs/research/dependencies').glob('*.json')),
              args.root / 'docs/research/component-options/packages.csv', args.root / 'docs/research/alternatives/coverage.csv',
              *sorted((args.root / '.github/workflows').glob('*.yml'))]
    summary['inputs'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    summary['outputs'] = {name: hashlib.sha256(data).hexdigest() for name, data in outputs.items()}
    for name, data in outputs.items():
        (args.output_dir / name).write_bytes(data)
    (args.output_dir / 'checks.csv').write_bytes(csv_bytes(checks, ['check', 'iteration', 'passed']))
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
