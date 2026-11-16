#!/usr/bin/env python3
"""研究用の6.18.59 treeの写しへFEC観測点だけを加える。"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path


def transform(name, text):
    if name.endswith('.h'):
        edits = [('unsigned int level;\t\t/* recursion level */',
                  'unsigned int level;\t\t/* recursion level */\n\tu64 b3_id;')]
    else:
        edits = [
            ('#include <linux/math64.h>', '#include <linux/math64.h>\n#include <linux/atomic.h>'),
            ('#define DM_MSG_PREFIX\t"verity-fec"',
             '#define DM_MSG_PREFIX\t"verity-fec"\n\nstatic atomic64_t b3_ids = ATOMIC64_INIT(0);'),
            ('\t\tif (res < 0) {\n\t\t\tr = res;',
             '\t\tif (res || !block_offset)\n'
             '\t\t\tDMINFO("B3_RS id=%llu column=%llu neras=%d result=%d",\n'
             '\t\t\t       fio->b3_id, rsb + block_offset, neras, res);\n'
             '\t\tif (res < 0) {\n\t\t\tr = res;'),
            ('\t\t/* locate erasures if the block is on the data device */',
             '\t\tif (bufio == v->fec->data_bufio)\n'
             '\t\t\tDMINFO("B3_HASH id=%llu data_block=%llu level=%u",\n'
             '\t\t\t       fio->b3_id, block, fio->level);\n\n'
             '\t\t/* locate erasures if the block is on the data device */'),
            ('\tr = fec_alloc_bufs(v, fio);',
             '\tDMINFO("B3_PHASE id=%llu rsb=%llu erasures=%u",\n'
             '\t       fio->b3_id, rsb, use_erasures);\n'
             '\tr = fec_alloc_bufs(v, fio);'),
            ('\tif (fio->level)\n\t\treturn -EIO;',
             '\tDMINFO("B3_ENTER id=%llu type=%u block=%llu level=%u mode=%u",\n'
             '\t       fio->b3_id, type, (u64)block, fio->level, v->mode);\n'
             '\tif (fio->level) {\n'
             '\t\tDMINFO("B3_GUARD id=%llu level=%u result=%d",\n'
             '\t\t       fio->b3_id, fio->level, -EIO);\n'
             '\t\treturn -EIO;\n\t}'),
            ('\tfio->level--;\n\treturn r;',
             '\tDMINFO("B3_EXIT id=%llu level=%u result=%d", fio->b3_id, fio->level, r);\n'
             '\tfio->level--;\n\treturn r;'),
            ('\tfio->level = 0;', '\tfio->level = 0;\n\tfio->b3_id = atomic64_inc_return(&b3_ids);')]
    for before, after in edits:
        if text.count(before) != 1:
            raise ValueError(f'unsupported/already instrumented source: {name}: {before!r}')
        text = text.replace(before, after)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tree', type=Path)
    args = parser.parse_args()
    if '6.18.59' not in (args.tree / 'include/config/kernel.release').read_text():
        raise ValueError('6.18.59 tree required')
    changes = []
    for name in ('dm-verity-fec.h', 'dm-verity-fec.c'):
        path = args.tree / 'drivers/md' / name
        before = path.read_text()
        after = transform(name, before)
        changes.append((path, before, after))
    patch = ''.join(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                     fromfile=f'a/drivers/md/{path.name}', tofile=f'b/drivers/md/{path.name}'))
                    for path, before, after in changes)
    (args.tree / 'b3-trace.patch').write_text(patch)
    (args.tree / 'b3-source-hashes.json').write_text(json.dumps({
        path.name: {'before': hashlib.sha256(before.encode()).hexdigest(),
                    'after': hashlib.sha256(after.encode()).hexdigest()}
        for path, before, after in changes}, indent=2) + '\n')
    for path, _, after in changes:
        path.write_text(after)


if __name__ == '__main__':
    main()
