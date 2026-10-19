#!/usr/bin/env python3
import argparse
import lzma
from pathlib import Path


SIGNATURE_MARKER = b"~Module signature appended~\n"
SIGNATURE_HEADER_SIZE = 12


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("output")
    args = parser.parse_args()

    module_path = Path(args.module)
    output_path = Path(args.output)
    data = module_path.read_bytes()
    if module_path.suffix == ".xz":
        data = lzma.decompress(data)

    if data.endswith(SIGNATURE_MARKER):
        header_end = len(data) - len(SIGNATURE_MARKER)
        header_start = header_end - SIGNATURE_HEADER_SIZE
        if header_start < 0:
            raise SystemExit("Module signature header is truncated")
        header = data[header_start:header_end]
        signer_len = header[3]
        key_id_len = header[4]
        signature_len = int.from_bytes(header[8:12], "big")
        unsigned_end = header_start - signer_len - key_id_len - signature_len
        if unsigned_end <= 0:
            raise SystemExit("Module signature lengths are invalid")
        data = data[:unsigned_end]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


if __name__ == "__main__":
    main()
