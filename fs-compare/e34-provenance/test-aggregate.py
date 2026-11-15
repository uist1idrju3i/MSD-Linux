#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('aggregate', Path(__file__).with_name('aggregate.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Aggregate(unittest.TestCase):
    def row(self, **changes):
        return dict(run_id='one', config='B2', test='T5', repetition='1', status='ok',
                    wall_seconds='1', write_sectors='0', **changes)

    def test_normal_and_failed_attempt(self):
        row = self.row()
        failed = dict(row, run_id='failed', status='fail:terminated_signal_15')
        rows, failures = MODULE.aggregate([('B2', 'T5', '1')], [failed, row])
        self.assertEqual(rows[0][:3], ['B2', 'T5', '1'])
        self.assertEqual(failures, ['failed'])

    def test_empty_partial_duplicate_and_invalid(self):
        row = self.row()
        for plan, attempts in [([], []), ([('B2', 'T5', '1')], []),
                               ([('B2', 'T5', '1')], [row, row]),
                               ([('B2', 'T5', '1')], [row, dict(row, run_id='two')]),
                               ([('B2', 'T5', '1')], [dict(row, write_sectors='nan')]),
                               ([('B2', 'T5', '1')], [dict(row, write_sectors='')])]:
            with self.subTest(plan=plan, attempts=attempts), self.assertRaises(ValueError):
                MODULE.aggregate(plan, attempts)


if __name__ == '__main__':
    unittest.main()
