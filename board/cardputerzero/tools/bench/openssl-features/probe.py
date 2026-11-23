#!/usr/bin/env python3
"""Exercise both cold images using RAM-only fixtures and supervised QEMU."""

import argparse
import base64
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import uuid


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CASES = ("providers", "c1-minimum", "c1-security", "ed25519", "ed25519-reject",
         "update-valid", "update-invalid", "update-unchanged", "argon2id-format",
         "argon2id-metadata", "argon2id-open", "argon2id-close", "x509", "x509-reject",
         "cms-sign", "cms-verify", "cms-reject", "tls1_2", "tls1_2-hostname", "tls1_3", "tls1_3-hostname")
ALGORITHMS = ("cipher", "digest", "public-key", "kdf", "kem", "signature", "mac", "asymcipher", "key-exchange")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KBD = load("kbd", HERE.parent / "kbd.py")
BOOT = load("boot", ROOT / "board/cardputerzero/qemu/boot-test.py")
SUPERVISOR = BOOT.helpers()


def compare_algorithms(out):
    inventories = {}
    for variant in ("baseline", "candidate"):
        with tarfile.open(out / f"{variant}-A/guest-logs.tar.gz") as archive:
            inventories[variant] = {name: hashlib.sha256(archive.extractfile(
                f"logs/{name}-algorithms.log").read()).hexdigest() for name in ALGORITHMS}
    if inventories["baseline"] != inventories["candidate"]:
        raise ValueError("algorithm inventories differ")
    return inventories


def parse(text, slot):
    lines = text.replace("\r", "").splitlines()
    if lines.count("FEATURE_DONE") != 1 or lines.count("FEATURE_EXIT=0") != 1:
        raise ValueError("guest did not finish successfully")
    names = []
    for line in lines:
        if line.startswith("FEATURE_RESULT "):
            match = re.fullmatch(r"FEATURE_RESULT case=(\S+) rc=0", line)
            if not match:
                raise ValueError("failed guest case")
            names.append(match[1])
    expected = CASES if slot == "A" else ()
    if len(names) != len(expected) or set(names) != set(expected):
        raise ValueError("missing or duplicate guest cases")
    if lines.count("FEATURE_LOGS_BEGIN") != 1 or lines.count("FEATURE_LOGS_END") != 1:
        raise ValueError("missing guest logs")
    start, end = lines.index("FEATURE_LOGS_BEGIN"), lines.index("FEATURE_LOGS_END")
    data = base64.b64decode("".join(lines[start + 1:end]), validate=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        files = [member.name for member in archive.getmembers() if member.isfile()]
    if len(files) != len(set(files)) or any(not name.startswith("logs/") or ".." in Path(name).parts for name in files):
        raise ValueError("invalid guest log archive")
    if not {"logs/" + name + ".log" for name in expected}.issubset(files):
        raise ValueError("guest case logs missing")
    if lines.count("MODULE_INVENTORY_BEGIN") != 1 or lines.count("MODULE_INVENTORY_END") != 1:
        raise ValueError("missing or repeated module inventory")
    module_lines = lines[lines.index("MODULE_INVENTORY_BEGIN") + 1:lines.index("MODULE_INVENTORY_END")]
    modules = []
    for line in module_lines:
        fields = line.split()
        if len(fields) != 6 or not fields[1].isdigit() or not fields[2].isdigit():
            raise ValueError("malformed module inventory")
        modules.append((fields[0], int(fields[1]), fields[3], fields[4]))
    if not modules or len({item[0] for item in modules}) != len(modules):
        raise ValueError("empty or duplicate module inventory")
    return names, sorted(modules), data


def boot(reference, slot, out):
    def interrupt(number, _frame):
        raise RuntimeError(f"signal {signal.Signals(number).name}")

    signals = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    handlers = {number: signal.signal(number, interrupt) for number in signals}
    try:
        with tempfile.TemporaryDirectory(prefix="ossl-probe-", dir="/tmp") as temporary:
            return supervise_boot(reference, slot, out, Path(temporary))
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)


def supervise_boot(reference, slot, out, temporary):
    out.mkdir()
    log_path = out / "serial.log"
    socket = temporary / "qmp.sock"
    environment = dict(os.environ, OUTPUT_DIR=str(reference), ROOT_DEVICE="/dev/mmcblk0p" + ("5" if slot == "A" else "6"),
                       QEMU_EXTRA_APPEND="msd.module-test=usbnet,bcm2835-unicam,imx219", QEMU_QMP_SOCKET=str(socket),
                       QEMU_COPY_IMAGE="1", TMPDIR=str(temporary))
    for name in ("QEMU_DRIVE_FILE", "QEMU_DRIVE_FORMAT"):
        environment.pop(name, None)
    process = None
    selector = selectors.DefaultSelector()
    pending = bytearray()
    state = dict(qmp_quit=False, reaped=False, returncode=None, fallback=[], error=None)
    try:
        process = subprocess.Popen([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh")],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=environment)
        state["pid"] = process.pid
        selector.register(process.stdout, selectors.EVENT_READ)
        with log_path.open("xb") as log:
            def receive(marker, timeout=300):
                deadline = time.monotonic() + timeout
                while marker not in pending:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("waiting for " + repr(marker))
                    if selector.select(timeout=1):
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            raise ValueError("QEMU exited before probe completed")
                        pending.extend(chunk)
                        log.write(chunk)
                        log.flush()
                del pending[:pending.index(marker) + len(marker)]

            def send(text):
                process.stdin.write(text.encode())
                process.stdin.flush()

            receive(b"login:")
            send("root\n")
            receive(b"# ")
            send("stty -echo\n")
            receive(b"# ")
            send("base64 -d >/run/features.sh <<'FEATURE_SCRIPT'\n")
            receive(b"> ")
            payload = base64.b64encode((HERE / "guest.sh").read_bytes()).decode()
            for index in range(0, len(payload), 76):
                send(payload[index:index + 76] + "\n")
                receive(b"> ")
            send("FEATURE_SCRIPT\n")
            receive(b"# ")
            send(f"sh /run/features.sh {slot}; feature_rc=$?; "
                 "if [ \"$feature_rc\" -ne 0 ]; then cat /run/openssl-features/logs/*; fi; "
                 "echo FEATURE_EXIT=$feature_rc\n")
            receive(b"FEATURE_EXIT=", 1200)
            receive(b"# ")
            SUPERVISOR.qmp_quit(socket, 5)
            state["qmp_quit"] = True
            if SUPERVISOR.reap(process, 5) != 0:
                raise ValueError("QEMU did not exit cleanly")
    except Exception as error:
        state["error"] = repr(error)
        raise
    finally:
        for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            signal.signal(number, signal.SIG_IGN)
        if process is not None:
            for number in (signal.SIGTERM, signal.SIGKILL):
                if process.poll() is None:
                    state["fallback"].append(signal.Signals(number).name)
                    SUPERVISOR.signal_group(process, number)
                    SUPERVISOR.reap(process, 5)
            state.update(reaped=process.poll() is not None, returncode=process.returncode)
        (out / "process.json").write_text(json.dumps(state, indent=2) + "\n")
        selector.close()
        if process is not None:
            process.stdin.close()
            process.stdout.close()
    text = log_path.read_text(errors="replace")
    if state["fallback"] or not state["qmp_quit"] or state["returncode"] != 0:
        raise ValueError("unclean QEMU supervision")
    if "MSD/Linux ready" not in text or not BOOT.check_boot_log(log_path, environment["ROOT_DEVICE"], "usbnet,bcm2835-unicam,imx219"):
        raise ValueError("invalid boot log")
    names, modules, data = parse(text, slot)
    (out / "guest-logs.tar.gz").write_bytes(gzip.compress(data, mtime=0))
    return names, modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir()
    prefix = "openssl-probe-" + uuid.uuid4().hex
    rows = [dict(run_id=f"{prefix}-{variant}-{slot}-{case}", variant=f"{variant}-{slot}", repeat=1,
                 metric=case, value="", unit="status", valid="false", note="not run")
            for variant in ("baseline", "candidate") for slot in ("A", "B")
            for case in ("boot", *(CASES if slot == "A" else ()), "modules")]
    (out / "plan.json").write_text(json.dumps(rows, indent=2) + "\n")
    inventories = {}
    current = None
    try:
        sources = KBD.source_inputs()
        for path in (Path(__file__), HERE / "guest.sh"):
            sources[str(path.relative_to(ROOT))] = KBD.COMMON.sha(path)
        metadata = dict(run_prefix=prefix, source_sha256=sources,
                        execution_commit=subprocess.check_output(
                            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                        qemu_sha256=KBD.COMMON.sha(Path(shutil.which("qemu-system-aarch64")).resolve()),
                        qemu_version=subprocess.check_output(["qemu-system-aarch64", "--version"], text=True),
                        inputs_sha256={})
        for variant in ("baseline", "candidate"):
            reference = args.pair.resolve() / variant
            for name in (".config", "images/Image", "images/sdcard.img", "images/rootfs.squashfs"):
                metadata["inputs_sha256"][f"{variant}/{name}"] = KBD.COMMON.sha(reference / name)
        (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        for variant in ("baseline", "candidate"):
            for slot in ("A", "B"):
                name = f"{variant}-{slot}"
                current = name
                names, modules = boot(args.pair.resolve() / variant, slot, out / name)
                inventories[name] = modules
                for row in rows:
                    if row["variant"] == name:
                        row.update(value=0, valid="true", note="observed target result")
                (out / "modules.json").write_text(json.dumps(inventories, indent=2) + "\n")
                print(f"{name}: boot and {len(names)} crypto cases; {len(modules)} modules", flush=True)
        if any(value != inventories["baseline-A"] for value in inventories.values()):
            for row in rows:
                if row["metric"] == "modules":
                    row.update(valid="false", note="module inventories differ")
            current = None
            raise ValueError("module inventories differ")
        current = None
        try:
            algorithms = compare_algorithms(out)
        except Exception:
            for row in rows:
                if row["metric"] == "providers":
                    row.update(valid="false", note="algorithm inventory missing or different")
            raise
        (out / "algorithms.json").write_text(json.dumps(algorithms, indent=2) + "\n")
    except Exception as error:
        (out / "failure.json").write_text(json.dumps(dict(error=repr(error), variant=current), indent=2) + "\n")
        for row in rows:
            if row["variant"] == current:
                row.update(valid="false", note="aborted collection: see serial.log and process.json")
        raise
    finally:
        with (out / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
