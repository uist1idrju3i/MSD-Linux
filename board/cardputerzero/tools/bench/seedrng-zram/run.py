#!/usr/bin/env python3
"""Probe the unmodified product over QEMU serial; put the load only in /run."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[5]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--load", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    run = args.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    inputs = [output / "images" / name for name in
              ["Image", "sdcard.img", "rootfs.squashfs", "bcm2710-rpi-cm0.dtb"]]
    inputs += [Path(__file__), Path(__file__).with_name("pressure.c")]
    if args.load:
        inputs.append(args.load.resolve())
    hashes = {}
    for path in inputs:
        with path.open("rb") as stream:
            hashes[str(path.relative_to(ROOT))] = hashlib.file_digest(stream, "sha256").hexdigest()
    (run / "inputs.json").write_text(json.dumps(hashes, indent=2) + "\n")
    image = run / "sdcard.img"
    shutil.copyfile(output / "images/sdcard.img", image)
    with image.open("r+b") as stream:
        stream.truncate(1 << (image.stat().st_size - 1).bit_length())
    env = dict(os.environ, OUTPUT_DIR=str(output), QEMU_COPY_IMAGE="0",
               QEMU_MACHINE="raspi3ap", QEMU_ICOUNT="", QEMU_EXTRA_APPEND="",
               KERNEL_IMAGE=str(output / "images/Image"),
               DTB_IMAGE=str(output / "images/bcm2710-rpi-cm0.dtb"))
    process = subprocess.Popen([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=env)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = bytearray()
    with (run / "serial.log").open("wb") as log:
        def receive(marker, timeout=300):
            deadline = time.monotonic() + timeout
            while marker not in pending:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"waiting for {marker!r}")
                if not selector.select(timeout=1):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError(f"QEMU exited: {process.poll()}")
                log.write(chunk)
                log.flush()
                pending.extend(chunk)
            del pending[:pending.index(marker) + len(marker)]

        def send(text):
            process.stdin.write(text.encode())
            process.stdin.flush()

        try:
            receive(b"login:")
            send("root\n")
            receive(b"# ")
            send("stty -echo\n")
            receive(b"# ")
            send("sleep 5; dmesg; cat /proc/swaps; cat /proc/meminfo; "
                 "ls -ld /data/seedrng /etc/init.d/*seedrng /etc/default/seedrng; "
                 "cat /sys/block/zram0/comp_algorithm /sys/block/zram0/disksize "
                 "/sys/block/zram0/backing_dev /run/msd-zram.log; "
                 "echo MSDSTATE_DONE\n")
            receive(b"MSDSTATE_DONE")
            receive(b"# ")
            if args.load:
                send("base64 -d > /run/msd-pressure <<'MSDBINARY'\n")
                receive(b"> ")
                payload = base64.b64encode(args.load.read_bytes()).decode()
                for start in range(0, len(payload), 76):
                    send(payload[start:start + 76] + "\n")
                    receive(b"> ")
                send("MSDBINARY\n")
                receive(b"# ")
                send("chmod +x /run/msd-pressure; "
                     "/run/msd-pressure; rc=$?; "
                     "cat /sys/block/zram0/mm_stat; dmesg; "
                     "echo MSDLOAD_DONE=$rc\n")
                receive(b"MSDLOAD_DONE=0", 300)
                receive(b"# ")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            selector.close()
    text = (run / "serial.log").read_text(errors="replace")
    if "invoked oom-killer" in text or "Out of memory:" in text:
        raise RuntimeError("guest OOM")
    if args.load and "MSDLOAD available_kib=" not in text:
        raise RuntimeError("missing pressure result")
    print(f"ok - probe complete: {run}")


if __name__ == "__main__":
    main()
