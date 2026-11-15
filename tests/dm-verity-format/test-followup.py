#!/usr/bin/env python3
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2] / 'board/cardputerzero/tools/bench/dm-verity-fec'
sys.path.insert(0, str(HERE))
import followup

SPEC = importlib.util.spec_from_file_location('trace_kernel', HERE / 'trace-kernel.py')
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)


class Followup(unittest.TestCase):
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
        self.assertNotIn('_on_corruption', line)
        self.assertIn('rdinit=/init b3.target=4096 b3.blocks=5832', line)
        self.assertIn('1 panic_on_corruption', followup.command_line(self.p, 'panic', 'normal'))
        self.assertIn('9 use_fec_from_device', followup.command_line(p, 'restart', 'normal'))

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

    def test_cpio_and_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'bin').mkdir()
            (root / 'lib').mkdir()
            (root / 'bin/busybox').write_bytes(b'busybox')
            (root / 'lib/libc.so.6').write_bytes(b'libc')
            (root / 'lib/libc.so').symlink_to('libc.so.6')
            one, two = root / 'one.gz', root / 'two.gz'
            followup.pack_initramfs(root, one)
            followup.pack_initramfs(root, two)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            data = gzip.decompress(one.read_bytes())
            self.assertTrue(data.startswith(b'070701'))
            self.assertIn((HERE / 'ram-init.sh').read_bytes(), data)
            self.assertIn(b'TRAILER!!!', data)
        header = 'unsigned int level;\t\t/* recursion level */'
        changed = trace.transform('dm-verity-fec.h', header)
        self.assertIn('u64 b3_id;', changed)
        self.assertRaises(ValueError, trace.transform, 'dm-verity-fec.c', '')


if __name__ == '__main__':
    unittest.main()
