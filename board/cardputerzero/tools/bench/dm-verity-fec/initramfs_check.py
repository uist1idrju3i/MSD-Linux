#!/usr/bin/env python3
"""研究用newc内だけでELF64のinterpreterと依存libraryを解決する。"""
import gzip
import stat
import struct


def entries(archive):
    data = gzip.decompress(archive)
    result, offset = {}, 0
    while offset < len(data):
        if data[offset:offset + 6] != b'070701' or offset + 110 > len(data):
            raise ValueError('invalid newc header')
        fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        start = offset + 110
        end = start + fields[11]
        if fields[11] < 1 or end > len(data) or data[end - 1] != 0:
            raise ValueError('invalid newc name')
        name = data[start:end - 1].decode()
        start = (end + 3) // 4 * 4
        end = start + fields[6]
        if end > len(data):
            raise ValueError('truncated newc payload')
        if name == 'TRAILER!!!':
            return result
        if not name or name.startswith('/') or '..' in name.split('/') or name in result:
            raise ValueError('unsafe/duplicate newc path')
        result[name] = (fields[1], data[start:end])
        offset = (end + 3) // 4 * 4
    raise ValueError('missing newc trailer')


def resolve(files, path):
    pending, resolved, links = path.split('/'), [], 0
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            if not resolved:
                raise ValueError('path escapes archive')
            resolved.pop()
            continue
        name = '/'.join(resolved + [part])
        if name not in files:
            raise FileNotFoundError(name)
        mode, payload = files[name]
        if stat.S_ISLNK(mode):
            links += 1
            if links > 40:
                raise ValueError('symlink loop')
            target = payload.decode()
            if not target:
                raise ValueError('empty symlink')
            if target.startswith('/'):
                resolved = []
            pending = target.split('/') + pending
        else:
            if pending and not stat.S_ISDIR(mode):
                raise ValueError('non-directory path component')
            resolved.append(part)
    return '/'.join(resolved)


def elf(data):
    if len(data) < 64 or data[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('expected ELF64 little-endian')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    if header[9] != 56 or header[5] + header[10] * 56 > len(data):
        raise ValueError('invalid ELF program headers')
    loads, dynamic, interpreter = [], [], None
    for index in range(header[10]):
        kind, _, offset, address, _, size, _, _ = struct.unpack_from('<IIQQQQQQ', data, header[5] + index * 56)
        if offset + size > len(data):
            raise ValueError('truncated ELF segment')
        if kind == 1:
            loads.append((address, offset, size))
        elif kind == 3:
            if not size or data[offset + size - 1] != 0:
                raise ValueError('invalid ELF interpreter')
            interpreter = data[offset:offset + size - 1].decode()
        elif kind == 2:
            if size % 16:
                raise ValueError('invalid dynamic segment')
            dynamic = []
            for pos in range(offset, offset + size, 16):
                tag, value = struct.unpack_from('<qQ', data, pos)
                if tag == 0:
                    break
                dynamic.append((tag, value))
            else:
                raise ValueError('unterminated dynamic segment')
    strings = [value for tag, value in dynamic if tag in (1, 15, 29)]
    needed, paths = [], []
    if strings:
        tags = dict(dynamic)
        address, size = tags.get(5, -1), tags.get(10, 0)
        source = next((offset + address - start for start, offset, length in loads
                       if start <= address and address + size <= start + length), None)
        if source is None or size < 1:
            raise ValueError('invalid dynamic string table')
        table = data[source:source + size]
        for tag, value in dynamic:
            if tag not in (1, 15, 29):
                continue
            end = table.find(b'\0', value)
            if value >= size or end < 0:
                raise ValueError('invalid dynamic string')
            text = table[value:end].decode()
            if tag == 1:
                needed.append(text)
            else:
                paths.extend(text.split(':'))
    return interpreter, needed, paths


def check(archive, search=('/lib64', '/usr/lib64')):
    files = entries(archive)
    pending, checked, edges = ['/bin/busybox'], set(), []
    while pending:
        requested = pending.pop()
        name = resolve(files, requested)
        if name in checked:
            continue
        mode, data = files[name]
        if not stat.S_ISREG(mode):
            raise ValueError('ELF is not a regular file')
        interpreter, needed, paths = elf(data)
        if paths:
            raise ValueError('RPATH/RUNPATH needs an explicit loader policy')
        checked.add(name)
        if interpreter:
            pending.append(interpreter)
        for library in needed:
            if not library or '/' in library:
                raise ValueError('unsupported DT_NEEDED path')
            for directory in search:
                candidate = directory + '/' + library
                try:
                    found = resolve(files, candidate)
                except FileNotFoundError:
                    continue
                edges.append(dict(source=name, needed=library, resolved=found))
                pending.append(candidate)
                break
            else:
                raise ValueError('unresolved DT_NEEDED: ' + name + ': ' + library)
    return dict(search=list(search), objects=sorted(checked), dependencies=edges,
                scope='ELF64 static dependency closure inside newc; no host fallback')
