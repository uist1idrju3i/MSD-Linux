#!/usr/bin/env python3
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[2] / 'board/cardputerzero/tools/bench/dm-verity-fec'
sys.path.insert(0, str(HERE))
import remaining
import rs_check
from stage_a import locate
from rs_check import decode


class Remaining(unittest.TestCase):
    def setUp(self):
        self.p = dict(data_blocks='2300', hash_start_block='2301', hash_area_blocks='4',
                      fec_blocks='2304', fec_roots='8', hash_alg='crc32c',
                      fec_area_offset=str(2305 * 4096), fec_bytes=str(10 * 4096 * 8), salt='aabb')

    def test_c_locations(self):
        cases = remaining.c_cases(self.p)
        self.assertEqual(len(cases), 10)
        self.assertEqual(len(set(name for name, _, _ in cases)), 10)
        self.assertEqual(locate(cases[1][1][0], self.p)['digest_index'], 2299)
        for _, offsets, _ in cases[5:7]:
            self.assertEqual(locate(offsets[0], self.p)['fec_column'],
                             locate(offsets[1], self.p)['fec_column'])
        self.assertEqual(locate(cases[-1][1][0], self.p)['region'], 'outside')
        self.assertRaises(ValueError, remaining.c_cases, dict(self.p, data_blocks='2'))

    def test_header_probe(self):
        p = dict(self.p, data_blocks='1')
        image = bytearray(8192)
        image[4096:4104] = b'verity\0\0'
        struct.pack_into('<II', image, 4104, 1, 1)
        image[4128:4134] = b'crc32c'
        struct.pack_into('<IIQ', image, 4160, 4096, 4096, 1)
        struct.pack_into('<H', image, 4176, 2)
        image[4184:4186] = bytes.fromhex('aabb')
        self.assertEqual(remaining.header_probe(image, p)['algorithm'], 'crc32c')
        image[4096] ^= 255
        self.assertRaisesRegex(ValueError, 'signature', remaining.header_probe, image, p)
        self.assertRaises(ValueError, remaining.header_probe, b'', p)

    def test_columns_and_rs_boundaries(self):
        for roots in (2, 8, 16):
            p = dict(self.p, fec_roots=str(roots))
            offsets = remaining.column_offsets(p, roots + 1)
            columns = [locate(offset, p)['fec_column'] for offset in offsets]
            self.assertTrue(all(column == columns[0] for column in columns))
            for errors, erasures in ((roots // 2, 0), (0, roots), (1, roots - 2)):
                damaged = [0] * 255
                for i in range(errors + erasures):
                    damaged[i] = i + 1
                self.assertEqual(decode(damaged, roots, range(erasures)), [0] * 255)
            self.assertRaises(ValueError, decode, [1] * 254, roots)
            self.assertRaises(ValueError, decode, [0] * 255, roots, range(roots + 1))
        self.assertRaises(ValueError, remaining.column_offsets, self.p, 0)

    def test_sha_verifier(self):
        p = dict(self.p, root_hash='abc', salt='00', hash_alg='sha256')
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(remaining.subprocess, 'run') as run:
                run.side_effect = [remaining.subprocess.CompletedProcess([], code) for code in (0, 1, 0, 0)]
                results = remaining.verify_sha(Path(temp), 'D-sha256-r8', p)
                self.assertEqual([r['status'] for r in results], [0, 1, 0, 0])
                self.assertIn('--hash-offset=' + str(2301 * 4096), results[0]['command'])
                self.assertTrue(all('observation only' in r['scope'] for r in results))
                self.assertEqual(len(list(Path(temp).glob('*.json'))), 4)
                run.side_effect = OSError('unavailable')
                self.assertRaises(OSError, remaining.verify_sha, Path(temp), 'D-sha256-r2', p)
                self.assertIn('unavailable', (Path(temp) / 'D-sha256-r2-clean-nofec.json').read_text())

    def test_full_reference_recovery(self):
        p = dict(self.p, data_blocks='80', hash_start_block='81', hash_area_blocks='1',
                 fec_blocks='81', fec_roots='2', fec_area_offset=str(82 * 4096),
                 fec_bytes=str(2 * 4096))
        clean = bytes(84 * 4096)
        self.assertEqual(rs_check.recovery(clean, clean, p)['outcome'], 'recovered-to-clean')
        for count, expected in ((1, 'recovered-to-clean'), (2, 'rejected'), (3, 'other-codeword')):
            damaged = bytearray(clean)
            for i in range(count):
                damaged[i * 4096] ^= 255
            result = rs_check.recovery(clean, damaged, p)
            self.assertEqual(result['outcome'], expected)
            self.assertEqual(result['decoded_equals_clean'], count == 1)
            if count == 3:
                self.assertEqual(result['changes'][0]['offset'], 59 * 4096)
        self.assertRaises(ValueError, rs_check.recovery, b'', b'', p)
        damaged = bytearray(clean)
        damaged[80 * 4096] ^= 1
        self.assertRaisesRegex(ValueError, 'outside', rs_check.recovery, clean, damaged, p)

    def test_boundary_checkpoint_before_failure(self):
        p = dict(self.p, data_blocks='80', hash_start_block='81', hash_area_blocks='1',
                 fec_blocks='81', fec_roots='2', fec_area_offset=str(82 * 4096),
                 fec_bytes=str(2 * 4096))
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = Path(temp) / 'boundary.json'
            with patch.object(rs_check, 'decode') as decode:
                decode.side_effect = [[0] * 255, ValueError('over capacity'), ValueError('unexpected failure')]
                self.assertRaisesRegex(ValueError, 'guaranteed', rs_check.boundaries,
                    bytes(84 * 4096), p, lambda values: remaining.save(checkpoint, values))
            values = remaining.json.loads(checkpoint.read_text())
            self.assertEqual(len(values), 3)
            self.assertTrue(values[-1]['guaranteed'])
            self.assertEqual(values[-1]['outcome'], 'rejected')

    def test_e_concentrated_and_dispersed(self):
        p = dict(self.p, data_blocks='5832', hash_start_block='5833', hash_area_blocks='7',
                 fec_blocks='5839', fec_area_offset=str(5840 * 4096), fec_bytes=str(24 * 8 * 4096))
        cases = remaining.e_cases(p)
        self.assertEqual(len(cases), 4)
        for name, offsets, expected in cases:
            count = int(name.split('-')[0])
            columns = {tuple(locate(offset, p)['fec_column']) for offset in offsets}
            self.assertEqual(len(offsets), count)
            dispersed = 'dispersed' in name
            self.assertEqual(len(columns), count if dispersed else 1)
            self.assertEqual(expected, 'normal-read' if dispersed else 'verity-panic')
        self.assertRaises(ValueError, remaining.e_cases, dict(p, fec_roots='2'))
        self.assertRaises(ValueError, remaining.column_offsets, self.p, 24, True)

    def test_f_reset(self):
        name, offsets, expected = remaining.f_case(self.p)
        self.assertEqual((name, expected), ('F-reset', 'restart-reset'))
        self.assertEqual(offsets, [i * 10 * 4096 for i in range(24)])
        self.assertRaises(ValueError, remaining.f_case, dict(self.p, fec_roots='2'))


if __name__ == '__main__':
    unittest.main()
