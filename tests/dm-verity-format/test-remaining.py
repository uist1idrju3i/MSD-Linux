#!/usr/bin/env python3
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parents[2] / 'board/cardputerzero/tools/bench/dm-verity-fec'
sys.path.insert(0, str(HERE))
import remaining
from stage_a import locate


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


if __name__ == '__main__':
    unittest.main()
