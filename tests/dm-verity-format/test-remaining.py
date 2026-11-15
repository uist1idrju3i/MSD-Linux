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
                run.side_effect = [remaining.subprocess.CompletedProcess([], code) for code in (0, 1, 0, 1)]
                results = remaining.verify_sha(Path(temp), 'D-sha256-r8', p)
                self.assertEqual([r['status'] for r in results], [0, 1, 0, 1])
                self.assertIn('--hash-offset=' + str(2301 * 4096), results[0]['command'])
                run.side_effect = None
                run.return_value = remaining.subprocess.CompletedProcess([], 1)
                self.assertRaisesRegex(ValueError, 'independent check', remaining.verify_sha,
                                       Path(temp), 'D-sha256-r8', p)

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


if __name__ == '__main__':
    unittest.main()
