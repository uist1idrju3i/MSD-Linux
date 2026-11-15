#!/usr/bin/env python3
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import stat
import struct
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2] / 'board/cardputerzero/tools/bench/dm-verity-fec'
sys.path.insert(0, str(HERE))
import followup
import initramfs_check

SPEC = importlib.util.spec_from_file_location('trace_kernel', HERE / 'trace-kernel.py')
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)


class Followup(unittest.TestCase):
    @staticmethod
    def elf(needed=(), interpreter=None, paths=None):
        strings = b'\0'
        dynamic = []
        for tag, text in [(1, n) for n in needed] + ([(29, paths)] if paths else []):
            dynamic.append((tag, len(strings)))
            strings += text.encode() + b'\0'
        phnum = 3 if interpreter else 2
        dynamic += [(5, 512), (10, len(strings)), (0, 0)]
        data = bytearray(512 + len(strings))
        struct.pack_into('<16sHHIQQQIHHHHHH', data, 0, b'\x7fELF\x02\x01\x01' + bytes(9),
                         3, 183, 1, 0, 64, 0, 0, 64, 56, phnum, 0, 0, 0)
        struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 0, 0, 0, len(data), len(data), 4096)
        struct.pack_into('<IIQQQQQQ', data, 120, 2, 4, 256, 256, 0, len(dynamic) * 16, len(dynamic) * 16, 8)
        if interpreter:
            payload = interpreter.encode() + b'\0'
            struct.pack_into('<IIQQQQQQ', data, 176, 3, 4, 400, 400, 0, len(payload), len(payload), 1)
            data[400:400 + len(payload)] = payload
        for index, pair in enumerate(dynamic):
            struct.pack_into('<qQ', data, 256 + index * 16, *pair)
        data[512:] = strings
        return bytes(data)

    def test_dependency_closure(self):
        files = {'bin': (stat.S_IFDIR, b''), 'lib': (stat.S_IFDIR, b''),
                 'usr': (stat.S_IFDIR, b''), 'usr/lib': (stat.S_IFDIR, b''),
                 'bin/busybox': (stat.S_IFREG, self.elf(['libresolv.so.2'], '/lib/ld.so')),
                 'lib/ld.so': (stat.S_IFREG, self.elf()),
                 'lib/libresolv.so.2': (stat.S_IFREG, self.elf(['libc.so.6'])),
                 'usr/lib/libc.so.6': (stat.S_IFREG, self.elf())}
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp)
            for name, (mode, payload) in files.items():
                path = tree / name
                if stat.S_ISDIR(mode):
                    path.mkdir(exist_ok=True)
                else:
                    path.write_bytes(payload)
            out = tree / 'ram.gz'
            self.assertRaisesRegex(ValueError, 'unresolved DT_NEEDED', followup.pack_initramfs, tree, out)
            self.assertFalse(out.exists())
            (tree / 'lib64').symlink_to('lib')
            (tree / 'usr/lib64').symlink_to('lib')
            result = followup.pack_initramfs(tree, out)
            self.assertEqual(len(result['objects']), 4)
            archived = initramfs_check.entries(out.read_bytes())
            self.assertEqual(archived['lib64'][1], b'lib')
            self.assertEqual(archived['usr/lib64'][1], b'lib')
            del archived['usr/lib/libc.so.6']
            self.assertRaises(FileNotFoundError, initramfs_check.resolve, archived, '/usr/lib64/libc.so.6')
            archived['lib64'] = (stat.S_IFLNK, b'lib64')
            self.assertRaisesRegex(ValueError, 'loop', initramfs_check.resolve, archived, '/lib64/libc.so.6')
            (tree / 'usr/lib/libc.so.6').unlink()
            self.assertRaisesRegex(ValueError, 'unresolved DT_NEEDED', followup.pack_initramfs, tree, out)
            (tree / 'usr/lib/libc.so.6').write_bytes(b'not ELF')
            self.assertRaisesRegex(ValueError, 'ELF64', followup.pack_initramfs, tree, out)
        for payload in (b'', b'not ELF', self.elf()[:100]):
            self.assertRaises(ValueError, initramfs_check.elf, payload)
        self.assertRaises(ValueError, initramfs_check.entries, gzip.compress(b''))
        interp, needed, paths = initramfs_check.elf(self.elf(['libc.so.6'], paths='$ORIGIN/../lib64'))
        self.assertEqual((interp, needed, paths), (None, ['libc.so.6'], ['$ORIGIN/../lib64']))

    def setUp(self):
        self.p = dict(data_blocks='1', hash_start_block='2', hash_area_blocks='1',
                      fec_roots='0', fec_blocks='2', fec_area_offset='12288',
                      fec_bytes='0', hash_alg='crc32c', root_hash='12345678', salt='00')
        self.bad = 'Linux version first\ndevice-mapper: verity: 0: metadata block 2 is corrupted\n'
        self.ok = 'verity-readall-complete\nMSD/Linux ready\nMSD/Linux login: '

    def judge(self, text, expected='normal-read', path='normal', status=None, reason='observed', events=()):
        return followup.judge(text, dict(expected=expected, path=path), status, reason, events)

    def test_normal_markers(self):
        self.assertTrue(self.judge(self.ok)['functional_pass'])
        self.assertTrue(self.judge(self.ok + '\nlate kernel info\n')['functional_pass'])
        self.assertFalse(self.judge('MSD/Linux ready\nverity-readall-complete\nx login: ')['functional_pass'])
        for text in ('', 'MSD/Linux ready', 'verity-readall-complete\nMSD/Linux ready',
                     self.ok + '\nKernel panic', self.bad + self.ok,
                     self.ok + '\nterminating on signal 15'):
            self.assertFalse(self.judge(text)['functional_pass'])
        self.assertFalse(self.judge('args verity-readall-complete\nMSD/Linux ready\nx login:')['functional_pass'])
        self.assertFalse(self.judge(self.ok, reason='timeout')['functional_pass'])
        self.assertRaises(ValueError, self.judge, self.ok, 'invalid')

    def test_ram_and_eio(self):
        ok = 'B3_RAM_TARGET status=0\nB3_RAM_ALL status=0\nB3_RAM_END\n'
        self.assertTrue(self.judge(ok, 'ram-read', 'ram')['functional_pass'])
        self.assertFalse(self.judge(ok.replace('B3_RAM_END', ''), 'ram-read', 'ram')['functional_pass'])
        failed = self.bad + 'Input/output error\nB3_RAM_TARGET status=1\nB3_RAM_ALL status=1\nB3_RAM_END\n'
        self.assertTrue(self.judge(failed, 'verity-eio', 'ram')['functional_pass'])
        self.assertFalse(self.judge(failed + 'Kernel panic', 'verity-eio', 'ram')['functional_pass'])
        self.assertFalse(self.judge(self.bad + ok, 'verity-eio', 'ram')['functional_pass'])
        self.assertTrue(self.judge(self.bad + ok, 'verity-eio', 'ram')['recovered_against_eio'])
        self.assertTrue(self.judge(self.bad + self.ok, 'verity-eio')['recovered_against_eio'])
        self.assertFalse(self.judge(self.bad + 'I/O error\nKernel panic: VFS mount failed',
                                    'verity-eio')['functional_pass'])

    def test_panic_restart_reset(self):
        panic = self.bad + 'Kernel panic: dm-verity device corrupted'
        self.assertTrue(self.judge(panic, 'verity-panic')['functional_pass'])
        self.assertFalse(self.judge(panic.replace('dm-verity', 'VFS'), 'verity-panic')['functional_pass'])
        restart = self.bad + 'reboot: Restarting system\n'
        self.assertFalse(self.judge(restart, 'restart-request')['functional_pass'])
        self.assertTrue(self.judge(restart, 'restart-request', status=0, reason='natural-exit')['functional_pass'])
        self.assertFalse(self.judge(restart, 'restart-request', status=-15, reason='natural-exit')['functional_pass'])
        reset = restart + 'Linux version second\n'
        self.assertFalse(self.judge(reset, 'restart-reset')['functional_pass'])
        self.assertTrue(self.judge(reset, 'restart-reset',
                                  events=[dict(event='RESET', after_restart_marker=True)])['functional_pass'])
        self.assertFalse(self.judge(reset, 'restart-reset',
                                   events=[dict(event='RESET', after_restart_marker=False)])['functional_pass'])

    def test_command_options(self):
        p = dict(self.p, data_blocks='5832', fec_roots='8')
        line = followup.command_line(p, 'eio', 'ram')
        self.assertIn('8 use_fec_from_device', line)
        self.assertIn('initcall_debug', line)
        self.assertNotIn('_on_corruption', line)
        self.assertIn('rdinit=/init b3.target=4096 b3.blocks=5832', line)
        self.assertIn('1 panic_on_corruption', followup.command_line(self.p, 'panic', 'normal'))
        self.assertIn('9 use_fec_from_device', followup.command_line(p, 'restart', 'normal'))

    def test_init_exec_readall(self):
        def converted(command):
            if any(char in command for char in '~`!$^&*()=|\\{}[];"\'<>?'):
                return ['/bin/sh', '-c', 'exec ' + command]
            return shlex.split(command)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'etc').mkdir()
            inittab = root / 'etc/inittab'
            inittab.write_text('')
            self.assertRaises(ValueError, followup.install_readall, root)
            inittab.write_text((followup.OLD_READALL + '\n') * 2)
            self.assertRaises(ValueError, followup.install_readall, root)
            inittab.write_text(followup.OLD_READALL + '\n')
            followup.install_readall(root)
            self.assertEqual(inittab.read_text(), followup.READALL + '\n')
            device, marker = root / 'data', root / 'marker'
            device.write_bytes(b'data')
            old = followup.OLD_READALL.split(':', 3)[3].replace('/dev/dm-0', str(device)).replace('/dev/kmsg', str(marker))
            result = subprocess.run(converted(old), capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(marker.exists(), 'negative control must reproduce missing marker')
            command = inittab.read_text().strip().split(':', 3)[3].replace('/usr/libexec/', str(root / 'usr/libexec') + '/')
            env = dict(os.environ, B3_READALL_DEVICE=str(device), B3_READALL_MARKER=str(marker))
            result = subprocess.run(converted(command), env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(marker.read_text(), 'verity-readall-complete\n')
            marker.unlink()
            env['B3_READALL_DEVICE'] = str(root / 'missing')
            result = subprocess.run(converted(command), env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_fresh_input_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / 'seed'
            (seed / 'images').mkdir(parents=True)
            (seed / 'images/sdcard.img').write_bytes(bytes(65536))
            (seed / 'images/bcm2710-rpi-cm0.dtb').write_bytes(b'dtb')
            (seed / 'variant-info.txt').write_text('rootfs_a_start_sector=1\n')
            kernel = root / 'kernel'
            kernel.write_bytes(b'kernel')
            followup.make_case(root, seed, kernel, self.p, bytes(12288), [123],
                               'test', 'verity-panic', 'panic', 'normal')
            case = root / 'test'
            followup.validate(case)
            info = json.loads((case / 'case.json').read_text())
            self.assertEqual(info['locations'][0]['offset'], 123)
            self.assertEqual(info['locations'][0]['after'], 255)
            self.assertRaises(FileExistsError, followup.make_case, root, seed, kernel,
                              self.p, bytes(12288), [], 'test', 'normal-read', 'panic', 'normal')
            (case / 'rootfs.img').write_bytes(b'changed')
            self.assertRaises(ValueError, followup.validate, case)
            (case / 'inputs.json').write_text('{}')
            self.assertRaises(ValueError, followup.validate, case)
            (case / 'inputs.json').write_text('{"../outside":"digest"}')
            self.assertRaises(ValueError, followup.validate, case)

    def test_refresh_b(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, tree = root / 'source', root / 'tree'
            source.mkdir()
            for name in ('bin', 'lib'):
                (tree / name).mkdir(parents=True)
            (tree / 'bin/busybox').write_bytes(self.elf(['libc.so.6'], '/lib/ld.so'))
            (tree / 'lib/libc.so.6').write_bytes(self.elf())
            (tree / 'lib/ld.so').write_bytes(self.elf())
            (tree / 'lib64').symlink_to('lib')
            seed = root / 'seed'
            (seed / 'images').mkdir(parents=True)
            (seed / 'images/sdcard.img').write_bytes(bytes(65536))
            (seed / 'images/bcm2710-rpi-cm0.dtb').write_bytes(b'dtb')
            (seed / 'variant-info.txt').write_text('rootfs_a_start_sector=1\n')
            kernel, old = root / 'kernel', root / 'old.gz'
            kernel.write_bytes(b'kernel')
            old.write_bytes(b'old initramfs')
            args = argparse.Namespace(base=source, tree=tree, destination=root / 'refreshed')
            self.assertRaisesRegex(ValueError, 'ten B cases', followup.refresh_b, args)
            for index in range(10):
                followup.make_case(source, seed, kernel, self.p, bytes(12288), [],
                                   f'B-test-{index}', 'ram-read', 'panic', 'ram', old)
            followup.refresh_b(args)
            for case in source.iterdir():
                target = args.destination / case.name
                followup.validate(target)
                self.assertEqual(followup.sha(case / 'rootfs.img'), followup.sha(target / 'rootfs.img'))
                self.assertNotEqual((case / 'initramfs.cpio.gz').read_bytes(),
                                    (target / 'initramfs.cpio.gz').read_bytes())
            self.assertRaises(FileExistsError, followup.refresh_b, args)
            (source / 'B-test-9/rootfs.img').write_bytes(b'changed')
            args.destination = root / 'rejected'
            self.assertRaisesRegex(ValueError, 'hash mismatch', followup.refresh_b, args)
            self.assertFalse(args.destination.exists())
    def test_cpio_and_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'bin').mkdir()
            (root / 'lib').mkdir()
            (root / 'bin/busybox').write_bytes(self.elf(['libc.so.6']))
            (root / 'lib/libc.so.6').write_bytes(self.elf())
            (root / 'lib64').symlink_to('lib')
            (root / 'lib/libc.so').symlink_to('libc.so.6')
            (root / 'usr/lib').mkdir(parents=True)
            (root / 'usr/lib/libresolv.so.2').write_bytes(b'resolver')
            one, two = root / 'one.gz', root / 'two.gz'
            followup.pack_initramfs(root, one)
            followup.pack_initramfs(root, two)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            data = gzip.decompress(one.read_bytes())
            self.assertTrue(data.startswith(b'070701'))
            self.assertIn((HERE / 'ram-init.sh').read_bytes(), data)
            self.assertIn(b'TRAILER!!!', data)
            self.assertIn(b'usr/lib/libresolv.so.2', data)
            self.assertIn(b'resolver', data)
        header = 'unsigned int level;\t\t/* recursion level */'
        changed = trace.transform('dm-verity-fec.h', header)
        self.assertIn('u64 b3_id;', changed)
        self.assertRaises(ValueError, trace.transform, 'dm-verity-fec.c', '')


if __name__ == '__main__':
    unittest.main()
