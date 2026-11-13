#!/usr/bin/env python3
"""Run a fixed release acceptance probe over the existing QEMU serial harness."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[5]


def validate(text, stage):
    if f"ACCEPTANCE_DONE {stage}" not in text:
        raise ValueError("missing acceptance completion marker")
    if "ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42" not in text:
        raise ValueError("release public key mismatch")
    if not re.search(r"^1794526865\r?$", text, re.M):
        raise ValueError("unexpected running version")
    if stage == "b":
        if "slot=B partition=3 tryboot=1" not in text:
            raise ValueError("B boot not observed")
        return
    for case, expected in [("tampered", 1), ("unsigned", 1), ("signed", 0)]:
        if not re.search(rf"^RESULT {case} {expected}\r?$", text, re.M):
            raise ValueError(f"unexpected install result: {case}")
    for part in [3, 6]:
        hashes = dict(re.findall(rf"^SNAP (\w+) p{part} ([0-9a-f]{{64}})", text, re.M))
        counters = dict(re.findall(rf"^STAT (\w+) p{part} ([^\r\n]+)", text, re.M))
        if set(hashes) != {"before", "tampered", "unsigned", "signed"} or set(counters) != set(hashes):
            raise ValueError("missing slot snapshots")
        if not hashes["before"] == hashes["tampered"] == hashes["unsigned"]:
            raise ValueError("negative test changed standby content")
        written = {label: int(raw.split()[6]) for label, raw in counters.items()}
        if not written["before"] == written["tampered"] == written["unsigned"] < written["signed"]:
            raise ValueError("unexpected standby write counter")
    for label in ["before", "tampered", "unsigned"]:
        if f"STATE {label} absent" not in text:
            raise ValueError("negative test left installed state")
    if "STATE signed 3" not in text:
        raise ValueError("missing installed B state")
    for kind, digest in [
        ("rootfs", "1eaa81c3cd3dfb1c6c458122f8d0cfa504f76725055bd60cf46f4fd51ead0d4a"),
        ("boot", "1d00199d1b9977efc739a26fab9a92ae39af4af595bf963c205ff6eb6154c234"),
    ]:
        if f"PAYLOAD {kind} {digest}" not in text:
            raise ValueError("installed payload hash mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=["a", "b"], required=True)
    args = parser.parse_args()
    prepared = args.prepared.resolve()
    run = args.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    image = prepared / "working.img"
    if args.stage == "a":
        if image.exists():
            raise FileExistsError("working image already exists")
        shutil.copyfile(prepared / "original.img", image)
        with image.open("r+b") as stream:
            stream.truncate(1 << (image.stat().st_size - 1).bit_length())
    elif not image.is_file():
        raise FileNotFoundError("B boot requires the updated working image")
    kernel = prepared / ("images/Image" if args.stage == "a" else "images/b-Image")
    env = dict(os.environ, OUTPUT_DIR=str(prepared), QEMU_COPY_IMAGE="0",
               QEMU_MACHINE="raspi3ap", QEMU_ICOUNT="", QEMU_EXTRA_APPEND="",
               KERNEL_IMAGE=str(kernel), DTB_IMAGE=str(prepared / f"images/{args.stage}.dtb"),
               ROOT_DEVICE="/dev/mmcblk0p" + ("5" if args.stage == "a" else "6"),
               QEMU_DRIVE_FILE=str(image), QEMU_DRIVE_FORMAT="raw", QEMU_HASH_IMAGE="1",
               QEMU_WATCHDOG="0", QEMU_DTB_BLUETOOTH="0", QEMU_QMP_SOCKET="",
               QEMU_EXTRA_ARGS=f"-drive file={prepared}/transfer.vfat,if=none,id=transfer,format=raw,readonly=on "
                               "-device usb-storage,drive=transfer")
    (run / "command.json").write_text(json.dumps(
        {"harness": "board/cardputerzero/qemu/run-qemu.sh", "environment":
         {key: value for key, value in env.items() if key.startswith(("QEMU_", "ROOT_", "KERNEL_", "DTB_", "OUTPUT_"))}},
        indent=2) + "\n")
    process = subprocess.Popen([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=env)
    pending = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    with (run / "serial.log").open("wb") as log:
        def receive(marker, timeout=600):
            deadline = time.monotonic() + timeout
            while marker not in pending:
                if time.monotonic() >= deadline:
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
            receive(b"login:", 300)
            send("root\n")
            receive(b"# ", 30)
            send("stty -echo\n")
            receive(b"# ", 30)
            send("base64 -d > /run/release-acceptance.sh <<'RELEASE_PROBE'\n")
            receive(b"> ", 30)
            payload = base64.b64encode(Path(__file__).with_name("guest.sh").read_bytes()).decode()
            for offset in range(0, len(payload), 76):
                send(payload[offset:offset + 76] + "\n")
                receive(b"> ", 30)
            send("RELEASE_PROBE\n")
            receive(b"# ", 30)
            send(f"sh /run/release-acceptance.sh {args.stage}; echo PROBE_EXIT=$?\n")
            receive(b"PROBE_EXIT=", 2400)
            receive(b"# ", 30)
            send("sync\n")
            receive(b"# ", 30)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            selector.close()
            process.stdin.close()
            process.stdout.close()
    text = (run / "serial.log").read_text(errors="replace")
    if not re.search(r"^PROBE_EXIT=0\r?$", text, re.M):
        raise ValueError("guest probe failed")
    validate(text, args.stage)
    print(f"ok - production release QEMU acceptance stage {args.stage}")


if __name__ == "__main__":
    main()
