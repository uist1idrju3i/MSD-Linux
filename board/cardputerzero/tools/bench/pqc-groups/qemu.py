#!/usr/bin/env python3
"""Run the PQC probe against measured target libraries through read-only USB."""

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time


def parse_serial(data):
    lines = data.replace("\r", "").splitlines()
    variants = ["default", "no-ml-kem", "no-ml-dsa", "no-slh-dsa", "all-three"]
    if [s.removeprefix("FUNCTIONAL_OK ") for s in lines
            if s.startswith("FUNCTIONAL_OK ")] != variants:
        raise ValueError("missing or duplicate functional result")
    if "PQC_DONE" not in lines or "PROBE_EXIT=0" not in lines:
        raise ValueError("incomplete guest probe")
    hello, speed, algorithms = {}, [], []
    repeat, rows = 0, 0
    for line in lines:
        if line.startswith("CLIENTHELLO "):
            _, group, count = line.split()
            if group in hello or int(count) <= 0:
                raise ValueError("invalid ClientHello result")
            hello[group] = int(count)
        elif line.startswith("SPEED_REPEAT "):
            if repeat and rows != 2:
                raise ValueError("incomplete speed repeat")
            repeat += 1
            if int(line.split()[1]) != repeat:
                raise ValueError("invalid repeat sequence")
            rows, algorithms = 0, []
        elif line.startswith("+DTP:"):
            name = line.split(":")[1]
            if name not in algorithms:
                algorithms.append(name)
        elif line.startswith("+F9:"):
            fields = line.split(":")
            if len(fields) != 5 or rows >= len(algorithms):
                raise ValueError("invalid KEM result")
            values = [float(value) for value in fields[2:]]
            if any(not math.isfinite(value) or value <= 0 for value in values):
                raise ValueError("invalid KEM rate")
            speed.append({"repeat": repeat, "algorithm": algorithms[rows],
                          **dict(zip(["keygen", "encaps", "decaps"], values))})
            rows += 1
    if repeat != 5 or rows != 2 or len(speed) != 10 or set(hello) != {
            "DEFAULT", "X25519", "X25519MLKEM768", "?X25519MLKEM768:DEFAULT"}:
        raise ValueError("missing benchmark results")
    if any([s["algorithm"] for s in speed if s["repeat"] == n]
           != ["X25519", "X25519MLKEM768"] for n in range(1, 6)):
        raise ValueError("unexpected benchmark algorithms")
    return {"clienthello": hello, "speed": speed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--hello", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    ref, variants, out = (x.resolve() for x in [args.reference, args.variants, args.out])
    out.mkdir(parents=True, exist_ok=False)
    transfer = out / "transfer"
    transfer.mkdir()
    shutil.copyfile(args.hello, transfer / "hello")
    for variant in ["default", "no-ml-kem", "no-ml-dsa", "no-slh-dsa", "all-three"]:
        for name in ["usr/lib/libcrypto.so.3", "usr/lib/libssl.so.3", "usr/bin/openssl"]:
            path = transfer / variant / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(variants / variant / "root" / name, path)
    fat = out / "transfer.vfat"
    with fat.open("xb") as stream:
        stream.truncate(128 * 1024 * 1024)
    subprocess.run(["mformat", "-i", str(fat), "-F", "::"], check=True)
    subprocess.run(["mcopy", "-s", "-i", str(fat), *map(str, transfer.iterdir()), "::/"], check=True)
    image = out / "sdcard.img"
    shutil.copyfile(ref / "images/sdcard.img", image)
    with image.open("r+b") as stream:
        stream.truncate(1 << (image.stat().st_size - 1).bit_length())
    paths = [ref / "images" / name for name in ["Image", "bcm2710-rpi-cm0.dtb", "sdcard.img"]]
    paths += list(transfer.rglob("*.so.3")) + list(transfer.rglob("openssl"))
    paths += [transfer / "hello", Path(__file__), Path(__file__).with_name("guest.sh")]
    hashes = {}
    for path in paths:
        with path.open("rb") as stream:
            hashes[str(path.relative_to(root))] = hashlib.file_digest(stream, "sha256").hexdigest()
    (out / "inputs.json").write_text(json.dumps(hashes, indent=2) + "\n")
    env = dict(os.environ, OUTPUT_DIR=str(ref), QEMU_COPY_IMAGE="0", QEMU_MACHINE="raspi3ap",
               QEMU_ICOUNT="", QEMU_EXTRA_APPEND="", QEMU_HASH_IMAGE="1",
               QEMU_EXTRA_ARGS=f"-drive file={fat},if=none,id=transfer,format=raw,readonly=on "
                               "-device usb-storage,drive=transfer")
    process = subprocess.Popen([str(root / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=env)
    pending = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    with (out / "serial.log").open("wb") as log:
        def receive(marker, timeout=300):
            deadline = time.monotonic() + timeout
            while marker not in pending:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"waiting for {marker!r}")
                if not selector.select(timeout=1):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("QEMU exited before probe completed")
                pending.extend(chunk)
                log.write(chunk)
                log.flush()
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
            send("base64 -d > /run/pqc.sh <<'PQC_SCRIPT'\n")
            receive(b"> ")
            payload = base64.b64encode(Path(__file__).with_name("guest.sh").read_bytes()).decode()
            for i in range(0, len(payload), 76):
                send(payload[i:i + 76] + "\n")
                receive(b"> ")
            send("PQC_SCRIPT\n")
            receive(b"# ")
            send("sh /run/pqc.sh; echo PROBE_EXIT=$?\n")
            receive(b"PROBE_EXIT=", 1200)
            receive(b"# ")
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
    text = (out / "serial.log").read_text(errors="replace")
    parse_serial(text)
    print("ok - five variant Ed25519/CMS probes and five KEM repeats")


if __name__ == "__main__":
    main()
