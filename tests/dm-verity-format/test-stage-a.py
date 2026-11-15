#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "board/cardputerzero/tools/bench/dm-verity-fec/stage_a.py"
SPEC = importlib.util.spec_from_file_location("stage_a", SOURCE)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


class StageA(unittest.TestCase):
    def setUp(self):
        self.p = dict(data_blocks=5832, hash_start_block=5833, hash_area_blocks=7,
                      fec_roots=8, fec_blocks=5839, fec_area_offset=23920640,
                      fec_bytes=786432, hash_alg="crc32c")
        self.bad = "Linux version first\ndevice-mapper: verity: 0: metadata block 0 is corrupted\n"
        self.restart = self.bad + "reboot: Restarting system\n"

    def test_locator(self):
        top = stage.locate(23891985, self.p)
        self.assertEqual((top["tree_level"], top["digest_index"]), (1, 4))
        self.assertEqual(top["fec_logical_block"], 5832)
        self.assertEqual(top["fec_column"], [0, 17])
        self.assertEqual(stage.locate(5832 * 4096, self.p)["region"], "superblock")
        self.assertEqual(stage.locate(5834 * 4096, self.p)["tree_level"], 0)
        first = stage.locate(23920640, self.p)
        last = stage.locate(23920640 + 786432 - 1, self.p)
        self.assertEqual((first["fec_symbol"], last["fec_symbol"]), (247, 254))
        self.assertEqual(stage.locate(23920640 + 786432, self.p)["region"], "outside")
        self.assertRaises(ValueError, stage.locate, -1, self.p)
        self.assertRaises(ValueError, stage.locate, 0, dict(self.p, hash_area_blocks=8))
        self.assertRaises(ValueError, stage.locate, 0, dict(self.p, data_blocks=0))
        self.assertRaises(KeyError, stage.locate, 0, {})

    def test_decoder(self):
        # fcr=0, roots=2: x^2 + 3*x + 2 vanishes at x=1,2.
        word = [0] * 255
        word[-3], word[-2], word[-1] = 1, 3, 2
        self.assertEqual(stage.syndromes(word, 2), [0, 0])
        damaged = list(word)
        damaged[0] ^= 93
        damaged[250] ^= 7
        self.assertEqual(stage.decode_erasures(damaged, [0, 250], 2), word)
        self.assertRaises(ValueError, stage.decode_erasures, damaged, [], 2)
        self.assertRaises(ValueError, stage.decode_erasures, damaged, [0, 1, 250], 2)
        self.assertRaises(ValueError, stage.decode_erasures, damaged, [0], 2)
        self.assertRaises(ValueError, stage.syndromes, [], 2)

    def test_judge(self):
        def passed(text, expectation, status, reason, events=()):
            return stage.judge(text, expectation, status, reason, events)["functional_pass"]
        self.assertTrue(passed("MSD/Linux ready", "ready", None, "ready"))
        self.assertFalse(passed(self.bad + "MSD/Linux ready", "ready", None, "ready"))
        self.assertTrue(passed(self.bad + "Kernel panic: dm-verity device corrupted",
                               "verity-panic", None, "panic"))
        self.assertFalse(passed(self.bad + "Kernel panic: unrelated", "verity-panic", None, "panic"))
        self.assertTrue(passed(self.restart, "restart-request", 0, "natural-exit"))
        self.assertFalse(passed(self.restart, "restart-request", -15, "timeout"))
        self.assertFalse(passed(self.restart + "terminating on signal 15", "restart-request", 0, "natural-exit"))
        reset_text = self.restart + "Linux version second\n"
        self.assertFalse(passed(reset_text, "restart-reset", None, "reset-observed"))
        self.assertFalse(passed(reset_text, "restart-reset", None, "reset-observed", [{"event": "RESET"}]))
        self.assertTrue(passed(reset_text, "restart-reset", None, "reset-observed",
                               [{"event": "RESET", "after_restart_marker": True}]))
        self.assertTrue(passed(self.bad + "Buffer I/O error", "verity-eio", None, "eio"))
        self.assertFalse(passed(self.bad + "Buffer I/O error\nKernel panic", "verity-eio", None, "eio"))
        self.assertFalse(passed("", "ready", 0, "natural-exit"))
        self.assertRaises(ValueError, stage.judge, "", "invalid", 0, "none", [])

    def test_independent_columns(self):
        p = dict(data_blocks=1, hash_start_block=2, hash_area_blocks=1, fec_roots=2,
                 fec_blocks=2, fec_area_offset=12288, fec_bytes=8192, hash_alg="crc32c")
        clean = bytes(20480)
        self.assertEqual(len(stage.independent_check(clean, clean, p, [])["columns"]), 2)
        damaged = bytearray(clean)
        damaged[0] = 9
        location = stage.locate(0, p)
        result = stage.independent_check(clean, damaged, p, [location])
        self.assertEqual(result["columns"][0]["outcome"], "decoded-to-clean")
        self.assertRaises(ValueError, stage.independent_check, clean, damaged, p, [])
        self.assertRaises(ValueError, stage.independent_check, damaged, damaged, p, [])
        for offset in (8192, 12288):
            damaged[offset] = 9
        result = stage.independent_check(clean, damaged, p, [stage.locate(o, p) for o in (0, 8192, 12288)])
        self.assertEqual(result["columns"][0]["outcome"], "over-erasure-capacity")


if __name__ == "__main__":
    unittest.main()
