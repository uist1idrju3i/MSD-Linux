#!/usr/bin/env python3

import sys
import time
from pathlib import Path


def main() -> int:
    fifo = Path(sys.argv[1])
    log = Path(sys.argv[2])
    with fifo.open("rb") as serial:
        start = time.monotonic()
        with log.open("w", encoding="utf-8", newline="") as output:
            for raw_line in serial:
                timestamp = time.monotonic() - start
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                output.write(f"{timestamp:.9f} {line}\n")
                output.flush()
            output.write(f"{time.monotonic() - start:.9f} [host] serial EOF\n")
            output.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
