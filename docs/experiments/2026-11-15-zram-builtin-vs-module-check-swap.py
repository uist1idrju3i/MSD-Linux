#!/usr/bin/env python3
"""E2補助: =m imageでzram swapが有効になるかをserial経由で確認する。"""
import os, selectors, subprocess, sys, time
from pathlib import Path

ROOT = Path("/work")
OUT = Path(sys.argv[1]).resolve()          # e.g. /work/output-zram-m
LOG = Path(sys.argv[2]).resolve()          # serial log path
images = OUT / "images"
image = Path("/work/output-e2/zram-check-sdcard.img")
import shutil
shutil.copyfile(images / "sdcard.img", image)
with image.open("r+b") as s:
    s.truncate(1 << (image.stat().st_size - 1).bit_length())
env = dict(os.environ, OUTPUT_DIR=str(OUT), QEMU_COPY_IMAGE="0",
           QEMU_MACHINE="raspi3ap", QEMU_ICOUNT="", QEMU_EXTRA_APPEND="",
           QEMU_EXTRA_ARGS="", QEMU_QMP_SOCKET="", QEMU_HASH_IMAGE="0",
           KERNEL_IMAGE=str(images / "Image"),
           DTB_IMAGE=str(images / "bcm2710-rpi-cm0.dtb"),
           ROOT_DEVICE="/dev/mmcblk0p5", ROOT_FSTYPE="squashfs",
           QEMU_DRIVE_FILE=str(image), QEMU_DRIVE_FORMAT="raw",
           QEMU_WATCHDOG="0", QEMU_DTB_BLUETOOTH="0")
cmd = [str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, env=env)
sel = selectors.DefaultSelector(); sel.register(proc.stdout, selectors.EVENT_READ)
pending = bytearray(); log = LOG.open("wb")
def receive(marker, timeout):
    deadline = time.monotonic() + timeout
    while marker not in pending:
        if time.monotonic() >= deadline:
            raise TimeoutError(marker)
        if not sel.select(timeout=1):
            continue
        c = os.read(proc.stdout.fileno(), 65536)
        if not c:
            raise RuntimeError("qemu exited")
        log.write(c); log.flush(); pending.extend(c)
    pos = pending.index(marker) + len(marker); del pending[:pos]
def send(t):
    proc.stdin.write(t.encode()); proc.stdin.flush()
try:
    receive(b"login:", 300); send("root\n"); receive(b"\n# ", 60)
    send("sleep 25; cat /proc/swaps; cat /run/msd-zram.log; ls -l /dev/zram0; cat /sys/block/zram0/disksize\n")
    receive(b"# ", 90)
    for _ in range(3):
        sel.select(timeout=1)
        c = os.read(proc.stdout.fileno(), 65536)
        if c: log.write(c); log.flush(); pending.extend(c)
finally:
    log.close(); proc.terminate()
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
print(open(LOG, errors="replace").read()[-3000:])
