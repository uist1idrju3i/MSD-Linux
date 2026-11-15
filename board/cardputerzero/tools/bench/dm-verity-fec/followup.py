#!/usr/bin/env python3
"""B3後続段階の新規入力・厳密な観測・停止規則。旧v3は変更しない。"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import time

from stage_a import independent_check, locate, parameters
from initramfs_check import check as check_initramfs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SALT = '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f'
OLD_READALL = '::sysinit:/bin/dd if=/dev/dm-0 of=/dev/null bs=1048576 && /bin/echo verity-readall-complete > /dev/kmsg'
READALL = '::sysinit:/bin/sh /usr/libexec/b3-readall.sh'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def validate(directory):
    manifest = json.loads((directory / 'inputs.json').read_text())
    if not manifest or any(Path(name).is_absolute() or '..' in Path(name).parts
                           or sha(directory / name) != digest for name, digest in manifest.items()):
        raise ValueError('input hash mismatch')
    return manifest


def install_readall(tree):
    inittab = tree / 'etc/inittab'
    lines = inittab.read_text().splitlines()
    if lines.count(OLD_READALL) != 1:
        raise ValueError('expected exactly one original readall action')
    inittab.write_text('\n'.join(READALL if line == OLD_READALL else line for line in lines) + '\n')
    helper = tree / 'usr/libexec/b3-readall.sh'
    helper.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / 'readall.sh', helper)
    helper.chmod(0o755)


def repack_seed(seed, tree, host, destination):
    destination.mkdir()
    copied = destination / 'rootfs-tree'
    shutil.copytree(tree, copied, symlinks=True)
    install_readall(copied)
    info = subprocess.check_output([str(host / 'bin/unsquashfs'), '-s',
                                    str(seed / 'rootfs.squashfs')], text=True)
    compression = re.search(r'^Compression (\S+)', info, re.M).group(1)
    block_size = re.search(r'^Block size (\d+)', info, re.M).group(1)
    epoch = int(time.time())
    squashfs = destination / 'rootfs.squashfs'
    with (destination / 'mksquashfs.log').open('w') as log:
        subprocess.run([str(host / 'bin/mksquashfs'), str(copied), str(squashfs),
                        '-noappend', '-all-root', '-no-xattrs', '-no-progress',
                        '-comp', compression, '-b', block_size, '-mkfs-time', str(epoch)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    rootfs = destination / 'rootfs.img'
    shutil.copy2(squashfs, rootfs)
    with rootfs.open('r+b') as stream:
        stream.truncate((rootfs.stat().st_size + 4095) // 4096 * 4096)
    with (destination / 'format.log').open('w') as log:
        subprocess.run([str(seed / 'verityfmt'), '--hash', 'crc32c', '--salt', SALT,
                        '--fec-roots', '8', '--params-file', str(destination / 'verity-parameters.env'),
                        str(rootfs)], stdout=log, stderr=subprocess.STDOUT, check=True)
    p = parameters(destination / 'verity-parameters.env')
    save(destination / 'location.json', dict(parameters=p))
    (destination / 'variant-info.txt').write_text(
        'rootfs_a_start_sector=' + parameters(seed / 'variant-info.txt')['rootfs_a_start_sector'] + '\n')
    (destination / 'images').mkdir()
    for name in ('sdcard.img', 'bcm2710-rpi-cm0.dtb'):
        subprocess.run(['cp', '--sparse=always', str(seed / 'images' / name),
                        str(destination / 'images' / name)], check=True)
    save(destination / 'repack.json', dict(original_pack=sha(seed / 'rootfs.img'),
                                         new_pack=sha(rootfs), squashfs=sha(squashfs),
                                         helper=sha(HERE / 'readall.sh'), epoch=epoch,
                                         compression=compression, block_size=int(block_size)))
    if sha(rootfs) == sha(seed / 'rootfs.img'):
        raise ValueError('expected new research pack')
    return destination


def pack_initramfs(tree, destination):
    archive = bytearray()

    def entry(name, mode, data=b'', major=0, minor=0):
        header = [1, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name.encode()) + 1, 0]
        record = b'070701' + ''.join(f'{n:08x}' for n in header).encode() + name.encode() + b'\0'
        archive.extend(record + b'\0' * (-len(record) % 4))
        archive.extend(data + b'\0' * (-len(data) % 4))

    for name in ('bin', 'lib', 'usr', 'usr/lib', 'dev', 'proc', 'sys', 'run', 'tmp'):
        entry(name, stat.S_IFDIR | 0o755)
    entry('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1)
    entry('bin/busybox', stat.S_IFREG | 0o755, (tree / 'bin/busybox').read_bytes())
    entry('bin/sh', stat.S_IFLNK | 0o777, b'busybox')
    entry('init', stat.S_IFREG | 0o755, (HERE / 'ram-init.sh').read_bytes())
    for name in ('lib64', 'usr/lib64'):
        path = tree / name
        if path.is_symlink():
            entry(name, stat.S_IFLNK | 0o777, os.readlink(path).encode())
        elif path.exists():
            raise ValueError('expected library directory alias: ' + name)
    for prefix in ('lib', 'usr/lib'):
        directory = tree / prefix
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_symlink():
                entry(f'{prefix}/{path.name}', stat.S_IFLNK | 0o777, os.readlink(path).encode())
            elif path.is_file():
                entry(f'{prefix}/{path.name}', stat.S_IFREG | 0o755, path.read_bytes())
    entry('TRAILER!!!', 0)
    compressed = gzip.compress(archive, mtime=0)
    closure = check_initramfs(compressed)
    destination.write_bytes(compressed)
    return closure


def command_line(p, mode, path):
    d, h, roots = (int(p[key]) for key in ('data_blocks', 'hash_start_block', 'fec_roots'))
    opts = []
    if roots:
        opts += ['use_fec_from_device', '/dev/mmcblk0p5', 'fec_roots', str(roots),
                 'fec_blocks', p['fec_blocks'], 'fec_start', str(int(p['fec_area_offset']) // 4096)]
    if mode != 'eio':
        opts += [f'{mode}_on_corruption']
    table = (f'vroot,,,ro,0 {d * 8} verity 1 /dev/mmcblk0p5 /dev/mmcblk0p5 '
             f'4096 4096 {d} {h} {p["hash_alg"]} {p["root_hash"]} {p["salt"]} {len(opts)} '
             + ' '.join(opts))
    result = (f'dm-mod.waitfor=/dev/mmcblk0p5 dm-mod.create="{table}" '
              'printk.time=1 log_buf_len=4M initcall_debug ignore_loglevel loglevel=8 msd.sweep=1 msd.boottime=1')
    if path == 'ram':
        digest_bytes = {'crc32c': 4, 'sha256': 32}[p['hash_alg']]
        result += f' rdinit=/init b3.target={4 * (4096 // digest_bytes)} b3.blocks={d}'
    return result + '\n'


def refresh_b(args):
    cases = sorted(path for path in args.base.iterdir() if (path / 'case.json').exists())
    if len(cases) != 10:
        raise ValueError('expected ten B cases')
    for case in cases:
        validate(case)
    args.destination.mkdir()
    initramfs = args.destination / 'ram.cpio.gz'
    closure = pack_initramfs(args.tree, initramfs)
    save(args.destination / 'closure.json', closure)

    def copy(source, target):
        subprocess.run(['cp', '--sparse=always', str(source), str(target)], check=True)
        return target

    for case in cases:
        out = args.destination / case.name
        shutil.copytree(case, out, copy_function=copy)
        if (out / 'initramfs.cpio.gz').exists():
            shutil.copy2(initramfs, out / 'initramfs.cpio.gz')
        for name in ('rootfs.img', 'images/sdcard.img', 'images/Image', 'qemu-extra-append.txt'):
            if sha(case / name) != sha(out / name):
                raise ValueError('non-initramfs input changed')
        save(out / 'inputs.json', {str(path.relative_to(out)): sha(path)
                                  for path in sorted(out.rglob('*'))
                                  if path.is_file() and path.name != 'inputs.json'})
        validate(out)
    save(args.destination / 'refresh.json', dict(source={case.name: sha(case / 'inputs.json') for case in cases},
                                                initramfs=sha(initramfs), harness=sha(Path(__file__))))


def make_case(destination, seed, kernel, p, clean, offsets, name, expected, mode, path, initramfs=None):
    out = destination / name
    out.mkdir()
    (out / 'images').mkdir()
    damaged = bytearray(clean)
    for offset in offsets:
        if offset < 0 or offset > len(damaged):
            raise ValueError('injection outside image/padding boundary')
        if offset == len(damaged):
            damaged.append(0)
        damaged[offset] ^= 255
    reference = clean + bytes(max(0, len(damaged) - len(clean)))
    actual = [i for i, (a, b) in enumerate(zip(reference, damaged)) if a != b]
    if actual != sorted(offsets) or len(set(offsets)) != len(offsets):
        raise ValueError('injection difference mismatch')
    (out / 'rootfs.img').write_bytes(damaged)
    subprocess.run(['cp', '--sparse=always', str(seed / 'images/sdcard.img'),
                    str(out / 'images/sdcard.img')], check=True)
    start = int(parameters(seed / 'variant-info.txt')['rootfs_a_start_sector']) * 512
    with (out / 'images/sdcard.img').open('r+b') as stream:
        stream.seek(start)
        stream.write(damaged)
        stream.seek(start)
        if stream.read(len(damaged)) != damaged:
            raise ValueError('p5 readback mismatch')
    shutil.copy2(kernel, out / 'images/Image')
    shutil.copy2(seed / 'images/bcm2710-rpi-cm0.dtb', out / 'images/bcm2710-rpi-cm0.dtb')
    if initramfs:
        shutil.copy2(initramfs, out / 'initramfs.cpio.gz')
    (out / 'qemu-extra-append.txt').write_text(command_line(p, mode, path))
    locations = [dict(locate(offset, p), before=reference[offset], after=damaged[offset]) for offset in offsets]
    save(out / 'case.json', dict(case=name, stage='B', expected=expected, mode=mode, path=path,
                                parameters=p, locations=locations, clean=not offsets,
                                independent=independent_check(reference, damaged, p, locations)))
    save(out / 'inputs.json', {str(f.relative_to(out)): sha(f)
                               for f in sorted(out.rglob('*')) if f.is_file()})


def prepare_b(args):
    validate(args.seed)
    args.destination.mkdir()
    formatter_hashes = {Path(name).name: digest for digest, name in
                        (line.split() for line in (args.seed / 'formatter.sha256').read_text().splitlines())}
    if (formatter_hashes['verityfmt'] != sha(args.seed / 'verityfmt') or
            formatter_hashes['verityfmt.c'] != sha(ROOT / 'board/cardputerzero/tools/dm-verity/verityfmt.c')):
        raise ValueError('formatter provenance hash mismatch')
    save(args.destination / 'preparation.json',
         dict(seed_manifest=sha(args.seed / 'inputs.json'), kernel=sha(args.kernel),
              formatter=formatter_hashes, harness=sha(Path(__file__))))
    seed = repack_seed(args.seed, args.tree, args.host, args.destination / 'repacked-seed')
    p = json.loads((seed / 'location.json').read_text())['parameters']
    clean = (seed / 'rootfs.img').read_bytes()
    initramfs = args.destination / 'ram.cpio.gz'
    pack_initramfs(seed / 'rootfs-tree', initramfs)
    for path in ('normal', 'ram'):
        make_case(args.destination, seed, args.kernel, p, clean, [], f'B-clean-{path}',
                  'normal-read' if path == 'normal' else 'ram-read', 'panic', path, initramfs)
        for mode, expected in (('panic', 'verity-panic'), ('restart', 'restart-request'), ('eio', 'verity-eio')):
            make_case(args.destination, seed, args.kernel, p, clean,
                      [int(p['hash_start_block']) * 4096 + 17], f'B-F3-{mode}-{path}',
                      expected, mode, path, initramfs)
    nofec = args.destination / 'nofec-format'
    nofec.mkdir()
    rootfs = nofec / 'rootfs.img'
    rootfs.write_bytes(clean[:int(p['data_blocks']) * 4096])
    with (nofec / 'format.log').open('w') as log:
        subprocess.run([str(args.seed / 'verityfmt'), '--hash', 'crc32c', '--salt', SALT,
                        '--fec-roots', '0', '--params-file', str(nofec / 'params.env'), str(rootfs)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    p0 = parameters(nofec / 'params.env')
    p0.setdefault('fec_roots', '0')
    if p0['root_hash'] != p['root_hash'] or rootfs.read_bytes()[:int(p['data_blocks']) * 4096] != clean[:int(p['data_blocks']) * 4096]:
        raise ValueError('same-pack control data/hash mismatch')
    for name, offsets, expected in (
            ('B-nofec-clean', [], 'normal-read'),
            ('B-nofec-data', [int(p['data_blocks']) // 2 * 4096 + 123], 'verity-panic')):
        make_case(args.destination, seed, args.kernel, p0, rootfs.read_bytes(),
                  offsets, name, expected, 'panic', 'normal')


def judge(text, case, status, reason, events):
    ready = 'MSD/Linux ready' in text
    readall_match = re.search(r'(?:^|\n)(?:\[\s*[\d.]+\]\s*)?verity-readall-complete\r?(?:\n|$)', text)
    login_match = re.search(r'(?:^|\n)[^\n]*login:[ \t\r]*(?:\n|$)', text)
    readall, login = bool(readall_match), bool(login_match)
    panic = 'Kernel panic' in text
    corrupt = bool(re.search(r'device-mapper:\s*verity:[^\n]*(?:is corrupted|verification failed)|dm-verity device corrupted', text))
    vp = bool(re.search(r'Kernel panic[^\n]*dm-verity', text))
    restart = 'reboot: Restarting system' in text
    reset = any(e.get('event') == 'RESET' and e.get('after_restart_marker') for e in events)
    banners = len(re.findall(r'(?:^|\n)(?:\[\s*[\d.]+\]\s*)?Linux version ', text))
    ram = 'B3_RAM_END' in text
    ram_ok = ram and 'B3_RAM_TARGET status=0' in text and 'B3_RAM_ALL status=0' in text
    eio = bool(re.search(r'I/O error|Input/output error|error[ =]-5', text))
    ram_failed = ram and bool(re.search(r'B3_RAM_(?:TARGET|ALL) status=[1-9]', text))
    signal = 'terminating on signal' in text
    normal_ok = (ready and readall and login and
                 readall_match.start() < text.index('MSD/Linux ready') < login_match.start())
    expectation = case['expected']
    valid = {
        'normal-read': normal_ok and not (corrupt or panic or restart or signal),
        'ram-read': ram_ok and not (corrupt or panic or restart or signal),
        'verity-panic': corrupt and vp and not (ready or ram or restart),
        'verity-eio': corrupt and eio and not (ready or panic or restart) and (
            ram_failed if case['path'] == 'ram' else True),
        'restart-request': corrupt and restart and status == 0 and reason == 'natural-exit' and not (ready or panic or ram or signal),
        'restart-reset': corrupt and restart and reset and banners >= 2 and not (ready or panic)
    }
    if expectation not in valid:
        raise ValueError('unknown expectation')
    return dict(functional_pass=bool(valid[expectation] and reason != 'timeout'),
                expected=expectation, ready=ready, readall_complete=readall, login=login,
                ram_complete=ram, ram_read_success=ram_ok, corruption=corrupt, panic=panic,
                restart=restart, eio=eio, qmp_reset=reset, boot_banners=banners, exit_status=status,
                stop_reason=reason, recovered_against_eio=expectation == 'verity-eio' and (normal_ok or ram_ok),
                guard_hits=len(re.findall(r'B3_GUARD id=', text)))


def boot(case_dir, out, timeout):
    case = json.loads((case_dir / 'case.json').read_text())
    out.mkdir()
    image = out / 'sdcard.img'
    subprocess.run(['cp', '--sparse=always', str(case_dir / 'images/sdcard.img'), str(image)], check=True)
    with image.open('r+b') as stream:
        stream.truncate(1 << (image.stat().st_size - 1).bit_length())
    env = os.environ.copy()
    qmp = out / 'qmp.sock'
    extra = '' if case['expected'] == 'restart-reset' else '-no-reboot'
    if case['path'] == 'ram':
        extra += f' -initrd {case_dir / "initramfs.cpio.gz"}'
    env.update(ROOT_DEVICE='/dev/dm-0', QEMU_ICOUNT='shift=0', QEMU_COPY_IMAGE='0',
               QEMU_EXTRA_APPEND=(case_dir / 'qemu-extra-append.txt').read_text(),
               KERNEL_IMAGE=str(case_dir / 'images/Image'), DTB_IMAGE=str(case_dir / 'images/bcm2710-rpi-cm0.dtb'),
               QEMU_WATCHDOG='1' if case['mode'] == 'restart' else '0',
               QEMU_QMP_SOCKET=str(qmp), QEMU_EXTRA_ARGS=extra)
    serial = out / 'serial.log'
    events, client, buffer, reason = [], None, b'', 'timeout'
    start = time.monotonic()
    with serial.open('wb') as output:
        process = subprocess.Popen(['bash', str(ROOT / 'board/cardputerzero/qemu/run-qemu.sh'), str(image)],
                                   env=env, stdout=output, stderr=output)
        try:
            while time.monotonic() - start < timeout:
                text = serial.read_text(errors='replace')
                if client is None and qmp.exists():
                    client = socket.socket(socket.AF_UNIX)
                    client.connect(str(qmp))
                    client.setblocking(False)
                    client.sendall(b'{"execute":"qmp_capabilities"}\r\n')
                if client:
                    try:
                        buffer += client.recv(65536)
                    except BlockingIOError:
                        pass
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        event = json.loads(line)
                        event.update(host_elapsed_seconds=time.monotonic() - start,
                                     after_restart_marker='reboot: Restarting system' in serial.read_text(errors='replace'))
                        events.append(event)
                if process.poll() is not None:
                    reason = 'natural-exit'
                    break
                result = judge(text, case, None, 'observed', events)
                complete_eio = case['path'] == 'ram' or case['expected'] != 'verity-eio'
                if (result['functional_pass'] and complete_eio) or result['recovered_against_eio']:
                    reason = 'observed'
                    break
                if result['panic'] or result['ram_complete'] or (result['ready'] and result['login']):
                    reason = 'unexpected-terminal'
                    break
                time.sleep(0.2)
        finally:
            text, status = serial.read_text(errors='replace'), process.poll()
            terminated = status is None
            if terminated:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if client:
                client.close()
    result = judge(text, case, status, reason, events)
    result.update(wall_seconds=time.monotonic() - start, host_terminated_after_observation=terminated,
                  final_process_status=process.returncode, serial_sha256=sha(serial))
    save(out / 'qmp.json', events)
    save(out / 'functional.json', result)
    image.unlink()
    qmp.unlink(missing_ok=True)
    return result


def run(args):
    args.destination.mkdir()
    cases = sorted(path for path in args.base.iterdir() if (path / 'case.json').exists())
    if args.case:
        cases = [path for path in cases if path.name in args.case]
        if len(cases) != len(set(args.case)):
            raise ValueError('unknown/duplicate selected case')
    if not cases:
        raise ValueError('empty case selection')
    cases.sort(key=lambda path: (not json.loads((path / 'case.json').read_text())['clean'], path.name))
    for case in cases:
        validate(case)
        for repeat in range(args.runs):
            result = boot(case, args.destination / f'{case.name}-boot{repeat}', args.timeout)
            print(case.name, repeat, json.dumps(result), flush=True)
            info = json.loads((case / 'case.json').read_text())
            if (info['clean'] and not result['functional_pass']) or result['stop_reason'] == 'timeout':
                raise RuntimeError('clean failure or unexpected unobserved outcome: stop before later cases')


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    prep = subs.add_parser('prepare-b')
    for name in ('seed', 'kernel', 'tree', 'destination'):
        prep.add_argument(name, type=Path)
    prep.add_argument('--host', type=Path, required=True)
    refresh = subs.add_parser('refresh-b')
    for name in ('base', 'tree', 'destination'):
        refresh.add_argument(name, type=Path)
    run_parser = subs.add_parser('run')
    for name in ('base', 'destination'):
        run_parser.add_argument(name, type=Path)
    run_parser.add_argument('--runs', type=int, required=True)
    run_parser.add_argument('--timeout', type=int, default=600)
    run_parser.add_argument('--case', action='append')
    args = parser.parse_args()
    for name in ('seed', 'kernel', 'tree', 'destination', 'base'):
        if hasattr(args, name):
            setattr(args, name, getattr(args, name).resolve())
    if args.command == 'prepare-b':
        prepare_b(args)
    elif args.command == 'refresh-b':
        refresh_b(args)
    elif args.runs < 1 or args.timeout < 1:
        parser.error('positive runs/timeout required')
    else:
        run(args)


if __name__ == '__main__':
    main()
