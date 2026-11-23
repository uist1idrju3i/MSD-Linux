#!/usr/bin/env python3
"""Create cnf-only rootfs overlays and run independent QEMU functional probes."""

import argparse
import base64
import csv
import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tarfile
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CASES = [
    "idle-before", "providers", "ciphers", "module", "bad-config",
    "update-valid", "update-invalid", "argon2id-format", "argon2id-open",
    "pbkdf2-format", "pbkdf2-open",
    "tls-control-tls1-aead", "tls-control-tls1_1-aead",
    *[f"tls-{direction}-{protocol}-aead" for direction in ("server", "client")
      for protocol in ("tls1", "tls1_1", "tls1_2", "tls1_3")],
    "tls-server-tls1_2-cbc", "tls-client-tls1_2-cbc", "idle-after", "data-content",
]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def configuration(original, variant):
    if variant == "C0":
        return original
    if variant not in ("C1", "C2"):
        raise ValueError("unknown variant")
    if original.count("[openssl_init]") != 1 or original.count("# activate = 1") != 1:
        raise ValueError("unexpected reference cnf")
    result = original.replace("[openssl_init]", "[openssl_init]\nssl_conf = cnf_experiment")
    result = result.replace("# activate = 1", "activate = 1")
    cipher = "DEFAULT:@SECLEVEL=2" if variant == "C1" else (
        "ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!eNULL:!PSK:@SECLEVEL=2")
    result += ("\n[cnf_experiment]\nsystem_default = cnf_policy\n\n[cnf_policy]\n"
               f"MinProtocol = TLSv1.2\nCipherString = {cipher}\n")
    if variant == "C2":
        result += ("Ciphersuites = TLS_CHACHA20_POLY1305_SHA256:"
                   "TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384\nGroups = DEFAULT\n")
    return result


def parse_serial(text):
    lines = text.replace("\r", "").splitlines()
    if lines.count("CNF_DONE") != 1 or lines.count("PROBE_EXIT=0") != 1:
        raise ValueError("incomplete or failed guest")
    rows = []
    for line in lines:
        if not line.startswith("CNF_RESULT "):
            continue
        match = re.fullmatch(
            r"CNF_RESULT case=(\S+) rc=(\d+) pass=1 writes=(\d+) sectors=(\d+)", line)
        if not match:
            raise ValueError("failed or invalid case")
        name, code, writes, sectors = match.groups()
        rows.append(dict(case=name, exit_code=int(code), writes=int(writes), sectors=int(sectors)))
    if len(rows) != len(CASES) or {row["case"] for row in rows} != set(CASES):
        raise ValueError("missing or duplicate cases")
    if lines.count("CNF_LOGS_BEGIN") != 1 or lines.count("CNF_LOGS_END") != 1:
        raise ValueError("missing guest raw logs")
    start, end = lines.index("CNF_LOGS_BEGIN"), lines.index("CNF_LOGS_END")
    data = base64.b64decode("".join(lines[start + 1:end]), validate=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        logs = {}
        for member in archive.getmembers():
            if member.isfile():
                if member.name in logs or not member.name.startswith("logs/"):
                    raise ValueError("invalid guest log member")
                logs[member.name] = archive.extractfile(member).read().decode(errors="replace")
    if "CONFIG_MODULE_SIG_FORCE=y" not in logs["logs/module-config.log"]:
        raise ValueError("module signature enforcement was not exercised")
    for pbkdf in ("argon2id", "pbkdf2"):
        for action in ("format", "open"):
            if "[default][legacy]" not in logs[f"logs/{pbkdf}-{action}.log"]:
                raise ValueError("cryptsetup legacy self-load was not observed")
        if pbkdf not in logs[f"logs/{pbkdf}-dump.log"]:
            raise ValueError("unexpected LUKS KDF")
    if "legacy" in logs["logs/providers.log"]:
        raise ValueError("legacy provider unexpectedly enabled by cnf")
    for direction in ("server", "client"):
        for protocol, expected in (("tls1_2", "TLSv1.2"), ("tls1_3", "TLSv1.3")):
            if f"Protocol version: {expected}" not in logs[f"logs/tls-{direction}-{protocol}-aead.log"]:
                raise ValueError("wrong TLS version")
    return rows, data


def command(args, log):
    subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, check=True)


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            result[relative] = ["link", os.readlink(path)]
        elif path.is_file():
            result[relative] = ["file", path.stat().st_mode & 0o7777, sha(path)]
    return result


def prepare_module_indexes(reference, rootfs, log):
    versions = sorted(path for path in (rootfs / "lib/modules").iterdir() if path.is_dir())
    if not versions:
        raise ValueError("fixture has no kernel module directory")
    for version in versions:
        command([reference / "host/sbin/depmod", "-a", "-b", rootfs, version.name], log)
        if not (version / "modules.dep.bin").is_file():
            raise ValueError("fixture depmod did not produce modules.dep.bin")


def build(reference, out):
    manifest = dict(reference=str(reference.relative_to(ROOT)), files={}, variants={})
    inputs = [reference / "images" / name for name in (
        "Image", "bcm2710-rpi-cm0.dtb", "sdcard.img", "rootfs.squashfs")]
    inputs += [reference / ".config", HERE / "run.py", HERE / "guest.sh", HERE / "module.c"]
    inputs += list((reference / "build").glob("libopenssl-*/configdata.pm"))
    inputs += list((reference / "build").glob("linux*/.config"))
    inputs += list((reference / "build").glob("busybox-*/.config"))
    inputs += [reference / "host/sbin/depmod"]
    for path in inputs:
        manifest["files"][str(path.relative_to(ROOT))] = sha(path)
    with (out / "build.log").open("x") as log:
        command([reference / "host/bin/aarch64-linux-gcc", "-Os", "-Wall", "-Wextra",
                 "-Werror", HERE / "module.c", "-lkmod", "-o", out / "kmod-probe"], log)
        manifest["files"][str((out / "kmod-probe").relative_to(ROOT))] = sha(out / "kmod-probe")
        for args in (["git", "rev-parse", "HEAD"], ["git", "submodule", "status", "vendor/buildroot"],
                     ["uname", "-a"], ["qemu-system-aarch64", "--version"],
                     [reference / "host/bin/aarch64-linux-gcc", "--version"]):
            command(args, log)
        trees = {}
        for variant in ("C0", "C1", "C2"):
            directory = out / variant
            directory.mkdir()
            rootfs = directory / "root"
            extracted = subprocess.run([
                str(reference / "host/bin/unsquashfs"), "-no-progress", "-no-xattrs",
                "-d", str(rootfs), str(reference / "images/rootfs.squashfs")],
                capture_output=True, text=True)
            log.write(extracted.stdout + extracted.stderr)
            diagnostics = extracted.stderr.splitlines()
            if extracted.returncode and not (
                    extracted.returncode == 2 and diagnostics and all(re.fullmatch(
                        r"set_attributes: failed to change uid and gids on .+, because Operation not permitted",
                        line) for line in diagnostics)):
                raise RuntimeError("unsquashfs failed; see build.log")
            prepare_module_indexes(reference, rootfs, log)
            cnf = rootfs / "etc/ssl/openssl.cnf"
            original = cnf.read_text()
            cnf.write_text(configuration(original, variant))
            shutil.copyfile(cnf, directory / "openssl.cnf")
            trees[variant] = inventory(rootfs)
            if variant != "C0":
                different = {key for key in trees["C0"].keys() | trees[variant].keys()
                             if trees["C0"].get(key) != trees[variant].get(key)}
                if different != {"etc/ssl/openssl.cnf"}:
                    raise ValueError(f"non-cnf rootfs changes: {different}")
            sqfs = directory / "rootfs.squashfs"
            env = dict(os.environ)
            env.pop("SOURCE_DATE_EPOCH", None)
            subprocess.run([str(reference / "host/bin/mksquashfs"), str(rootfs), str(sqfs),
                            "-noappend", "-all-root", "-no-xattrs", "-no-progress",
                            "-comp", "zstd", "-b", "131072", "-processors", "2",
                            "-mkfs-time", "0", "-all-time", "0"],
                           stdout=log, stderr=subprocess.STDOUT, check=True, env=env)
            disk = directory / "sdcard.img"
            command(["cp", "--sparse=always", reference / "images/sdcard.img", disk], log)
            partitions = json.loads(subprocess.check_output([
                str(reference / "host/sbin/sfdisk"), "--json", str(disk)]))["partitiontable"]["partitions"]
            if len(partitions) != 7 or sqfs.stat().st_size > partitions[4]["size"] * 512:
                raise ValueError("invalid disposable partition layout")
            command(["dd", f"if={sqfs}", f"of={disk}", "bs=512",
                     f"seek={partitions[4]['start']}", "conv=notrunc", "status=none"], log)
            with disk.open("r+b") as stream:
                stream.truncate(1 << (disk.stat().st_size - 1).bit_length())
            manifest["variants"][variant] = dict(
                cnf=sha(cnf), rootfs=sha(sqfs), image=sha(disk),
                files=trees[variant], rootfs_bytes=sqfs.stat().st_size)
    (out / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def boot(reference, image, variant, directory):
    directory.mkdir()
    disk = directory / "sdcard.img"
    subprocess.run(["cp", "--sparse=always", str(image), str(disk)], check=True)
    env = dict(os.environ, OUTPUT_DIR=str(reference), QEMU_COPY_IMAGE="0",
               QEMU_MACHINE="raspi3ap", QEMU_ICOUNT="", QEMU_EXTRA_APPEND="",
               QEMU_HASH_IMAGE="1", ROOT_DEVICE="/dev/mmcblk0p5", ROOT_FSTYPE="squashfs")
    process = subprocess.Popen([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(disk)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=env)
    pending = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    with (directory / "serial.log").open("xb") as log:
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
            for source, destination in ((HERE / "guest.sh", "/run/cnf-probe.sh"),
                                        (image.parent.parent / "kmod-probe", "/run/kmod-probe")):
                send(f"base64 -d > {destination} <<'CNF_SCRIPT'\n")
                receive(b"> ")
                payload = base64.b64encode(source.read_bytes()).decode()
                for i in range(0, len(payload), 76):
                    send(payload[i:i + 76] + "\n")
                    receive(b"> ")
                send("CNF_SCRIPT\n")
                receive(b"# ")
            send("chmod +x /run/kmod-probe\n")
            receive(b"# ")
            send(f"sh /run/cnf-probe.sh {variant}; cnf_rc=$?; "
                 "if [ \"$cnf_rc\" -ne 0 ]; then "
                 "for f in /run/cnf/logs/*; do echo \"FAILED_LOG=$f\"; cat \"$f\"; done; "
                 "fi; echo PROBE_EXIT=$cnf_rc\n")
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
    rows, data = parse_serial((directory / "serial.log").read_text(errors="replace"))
    (directory / "guest-logs.tar.gz").write_bytes(gzip.compress(data, mtime=0))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("at least three independent boots required")
    reference, out = args.reference.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    build(reference, out)
    rows = []
    with (out / "results.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "variant", "run", "case", "exit_code", "writes", "sectors", "valid", "serial_sha256"])
        writer.writeheader()
        for number in range(1, args.runs + 1):
            for label in ("C0", "C1", "C2", "C0-AA"):
                variant = label.split("-")[0]
                directory = out / f"{label}-r{number}"
                try:
                    result = boot(reference, out / variant / "sdcard.img", variant, directory)
                    for row in result:
                        item = dict(variant=label, run=number, valid=1, **row,
                                    serial_sha256=sha(directory / "serial.log"))
                        writer.writerow(item)
                        rows.append(item)
                    print(f"ok - {label} r{number}: {len(result)} functional cases", flush=True)
                except Exception:
                    writer.writerow(dict(variant=label, run=number, case="incomplete", valid=0,
                                         serial_sha256=sha(directory / "serial.log")
                                         if (directory / "serial.log").exists() else ""))
                    raise
                finally:
                    stream.flush()
    print(f"ok - {len(rows)} case results; all independent boots complete")


if __name__ == "__main__":
    main()
