#!/usr/bin/env python3
"""Stage the pinned QEMU for localhost-only SSH trials; retain every attempt."""

import argparse
import csv
import getpass
import gzip
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import time

from build import ROOT, VARIANTS, sha


def parse_serial(text, variants, repetitions):
    if "SSH_COMPARE_DONE" not in text or "Kernel panic" in text:
        raise ValueError("incomplete guest or panic")
    results = {}
    for line in text.replace("\r", "").splitlines():
        if line.startswith("SSH_RESULT "):
            _, variant, condition, repeat, code, changed = line.split()
            key = (variant, condition, int(repeat))
            if key in results or int(changed) != 0:
                raise ValueError("duplicate trial or known_hosts was modified")
            results[key] = int(code)
    expected = {(variant, condition, repeat) for variant in variants
                for condition in ("good", "wrong") for repeat in range(1, repetitions + 1)}
    if set(results) != expected:
        raise ValueError("missing or unexpected trials")
    for (variant, condition, repeat), code in results.items():
        begin = f"SSH_BEGIN {variant} {condition} {repeat}"
        end = f"SSH_RESULT {variant} {condition} {repeat} "
        body = text.split(begin, 1)[1].split(end, 1)[0]
        remote_ok = "SSH_REMOTE_OK" in [line.strip() for line in body.splitlines()]
        if condition == "good":
            if code != 0 or not remote_ok:
                raise ValueError(f"authentication/command failed: {begin} ({code})")
        elif code == 0 or code == 124 or remote_ok or not re.search(
                r"HOST IDENTIFICATION HAS CHANGED|host key.*(?:mismatch|does not match)|hostkey.*mismatch|Host key mismatch|host key is not cached|Host key not in manually configured list",
                body, re.I):
            raise ValueError(f"negative control did not reject host key: {begin} ({code})")
    return results


def export_qemu(out):
    out.mkdir(parents=True, exist_ok=False)
    binary = Path(shutil.which("qemu-system-aarch64")).resolve()
    (out / "bin").mkdir()
    (out / "lib").mkdir()
    shutil.copyfile(binary, out / "bin/qemu-system-aarch64")
    (out / "bin/qemu-system-aarch64").chmod(0o755)
    libraries = re.findall(r"(/[^\s()]+)", subprocess.check_output(["ldd", binary], text=True))
    for name in libraries:
        path = Path(name)
        if path.is_file():
            shutil.copyfile(path.resolve(), out / "lib" / path.name)
            if path.name.startswith("ld-linux"):
                (out / "lib" / path.name).chmod(0o755)
    (out / "qemu-version.txt").write_text(subprocess.check_output([binary, "--version"], text=True))
    hashes = {str(path.relative_to(out)): sha(path) for path in out.rglob("*") if path.is_file()}
    (out / "hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")


def initramfs(tree, destination):
    entries = [(str(path.relative_to(tree)), path) for path in sorted(tree.rglob("*"))]
    entries.extend((name, None) for name in ("dev/console", "dev/null")
                   if not (tree / name).exists())
    entries.append(("TRAILER!!!", None))
    with destination.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        for index, (name, path) in enumerate(entries, 1):
            data, major, minor = b"", 0, 0
            if path is None:
                mode = 0
                if name != "TRAILER!!!":
                    mode = stat.S_IFCHR | 0o600
                    major, minor = (5, 1) if name == "dev/console" else (1, 3)
            else:
                mode = path.lstat().st_mode
                if path.is_symlink():
                    data = os.readlink(path).encode()
                elif path.is_file():
                    data = path.read_bytes()
            encoded = name.encode() + b"\0"
            fields = (index, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(encoded), 0)
            header = b"070701" + b"".join(f"{field:08x}".encode() for field in fields)
            stream.write(header + encoded + b"\0" * (-(len(header) + len(encoded)) % 4))
            stream.write(data + b"\0" * (-len(data) % 4))


def prepare(args):
    tree = args.out / "root"
    shutil.copytree(args.reference / "target", tree, symlinks=True)
    for variant in args.variants:
        files = json.loads((args.build / variant / "files.json").read_text())
        for row in files:
            if sha(args.build / variant / "root" / row["path"]) != row["sha256"]:
                raise ValueError("payload hash changed")
            destination = tree / row["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.build / variant / "root" / row["path"], destination)
            destination.chmod(0o755)
    fixtures = tree / "fixtures"
    fixtures.mkdir()
    if args.strace:
        shutil.copyfile(args.strace, fixtures / "strace")
        (fixtures / "strace").chmod(0o755)
    for name in ("client", "settings", "known-good", "known-wrong"):
        shutil.copyfile(args.out / name, fixtures / name)
    if "dropbear" in args.variants:
        source = next((args.build / "dropbear/buildroot/build").glob("dropbear-*"))
        with (args.out / "fixture-tools.log").open("a") as log:
            subprocess.run(["nice", "-n", "19", "make", "-j4", "-C", source,
                            "PROGRAMS=dropbearconvert", "MULTI=0", "dropbearconvert"],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        shutil.copyfile(source / "dropbearconvert", fixtures / "dropbearconvert")
        (fixtures / "dropbearconvert").chmod(0o755)
    if "putty" in args.variants:
        source = next((args.build / "putty/buildroot/build").glob("putty-*"))
        shutil.copyfile(source / "puttygen", fixtures / "puttygen")
        (fixtures / "puttygen").chmod(0o755)
    shutil.copyfile(Path(__file__).with_name("guest.sh"), tree / "init")
    (tree / "init").chmod(0o755)
    dtb = args.out / "qemu.dtb"
    shutil.copyfile(args.reference / "images/bcm2710-rpi-cm0.dtb", dtb)
    subprocess.run([args.reference / "host/bin/fdtput", "-t", "s", dtb,
                    "/soc/serial@7e201000/bluetooth", "status", "disabled"], check=True)
    initramfs(tree, args.out / "initrd.gz")


def execute(args):
    for name in ("client", "host", "wrong"):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", args.out / name], check=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    login = getpass.getuser()
    config = (f"ListenAddress 127.0.0.1\nPort {port}\nHostKey {args.out}/host\n"
              f"AuthorizedKeysFile {args.out}/client.pub\nPidFile {args.out}/sshd.pid\n"
              "PasswordAuthentication no\nKbdInteractiveAuthentication no\nUsePAM no\n"
              f"AllowUsers {login}\nPubkeyAcceptedAlgorithms ssh-ed25519\nLogLevel DEBUG2\n")
    (args.out / "sshd.conf").write_text(config)
    fingerprints = {}
    for condition, key in (("good", "host"), ("wrong", "wrong")):
        public = (args.out / f"{key}.pub").read_text().split()
        (args.out / f"known-{condition}").write_text(
            f"[10.0.2.2]:{port} {' '.join(public[:2])}\n10.0.2.2 {' '.join(public[:2])}\n")
        fingerprints[condition] = subprocess.check_output(
            ["ssh-keygen", "-lf", args.out / f"{key}.pub"], text=True).split()[1]
    settings = dict(port=str(port), login=login, variants=" ".join(args.variants),
                    repetitions=str(args.repetitions), good_fingerprint=fingerprints["good"],
                    wrong_fingerprint=fingerprints["wrong"])
    (args.out / "settings").write_text("".join(f"{key}={shlex.quote(value)}\n" for key, value in settings.items()))
    relative = lambda path: str(path.relative_to(ROOT))
    command = [str(ROOT / "docker/msd-dev"), "python3", relative(Path(__file__).resolve()), "prepare",
               "--out", relative(args.out), "--reference", relative(args.reference),
               "--build", relative(args.build), "--variants", *args.variants]
    if args.strace:
        command.extend(["--strace", relative(args.strace)])
    with (args.out / "prepare.log").open("x") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    inputs = {str(path.relative_to(ROOT)): sha(path) for path in
              [args.reference / "images/Image", args.out / "qemu.dtb", args.out / "initrd.gz",
               args.tools / "bin/qemu-system-aarch64", Path(__file__), Path(__file__).with_name("guest.sh")]}
    inputs["sshd_version"] = subprocess.run(["/usr/sbin/sshd", "-V"], capture_output=True,
                                           text=True, check=True).stderr.strip()
    inputs["host_os"] = Path("/etc/os-release").read_text()
    if args.strace:
        inputs["strace_sha256"] = sha(args.strace)
    (args.out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    launcher = args.out / "qemu-launch"
    loader = args.tools / "lib/ld-linux-x86-64.so.2"
    binary = args.tools / "bin/qemu-system-aarch64"
    launcher.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(str(value)) for value in
                        [loader, "--library-path", args.tools / "lib", binary]) + ' "$@"\n')
    launcher.chmod(0o755)
    image = args.out / "unused-sd.img"
    with image.open("xb") as stream:
        stream.truncate(64 * 1024 * 1024)
    environment = dict(os.environ, OUTPUT_DIR=str(args.reference), QEMU_SYSTEM_AARCH64=str(launcher),
                       DTB_IMAGE=str(args.out / "qemu.dtb"), QEMU_DTB_BLUETOOTH="1", QEMU_COPY_IMAGE="0",
                       QEMU_QMP_SOCKET=str(args.out / "qmp.sock"), QEMU_EXTRA_APPEND="rdinit=/init",
                       QEMU_EXTRA_ARGS=f"-initrd {args.out}/initrd.gz -netdev user,id=n0 -device usb-net,netdev=n0 -snapshot")
    spec = importlib.util.spec_from_file_location("supervisor", ROOT / "board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py")
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    result = dict(qmp_quit=False, returncode=None, fallback=[], error=None)
    with (args.out / "sshd.log").open("wb") as server_log, (args.out / "serial.log").open("wb") as log:
        server = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e", "-f", args.out / "sshd.conf"],
                                  stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        process = None
        try:
            deadline = time.monotonic() + 5
            while True:
                if server.poll() is not None:
                    raise ValueError("test sshd exited; see sshd.log")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("test sshd did not listen")
                    time.sleep(0.05)
            process = subprocess.Popen([str(ROOT / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            data = bytearray()
            deadline = time.monotonic() + 900
            while b"SSH_COMPARE_DONE" not in data:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise TimeoutError("QEMU exited early or trial deadline exceeded")
                if selector.select(timeout=1):
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise ValueError("serial EOF")
                    data.extend(chunk)
                    log.write(chunk)
                    log.flush()
                    if b"Kernel panic" in data or b"SSH_FATAL_" in data:
                        raise ValueError("guest panic or network setup failure")
            if process.poll() is not None:
                raise ValueError("QEMU exited before requested quit")
            supervisor.qmp_quit(args.out / "qmp.sock", 5)
            result["qmp_quit"] = True
            process.wait(timeout=5)
            remaining = process.stdout.read()
            data.extend(remaining)
            log.write(remaining)
            if process.returncode != 0:
                raise ValueError("QEMU nonzero exit")
            trials = parse_serial(data.decode(errors="replace"), args.variants, args.repetitions)
            accepted = re.findall(r"Accepted publickey for .* ED25519 ",
                                  (args.out / "sshd.log").read_text(errors="replace"))
            if len(accepted) != len(args.variants) * args.repetitions:
                raise ValueError(f"server accepted count mismatch: {len(accepted)}")
            with (args.out / "results.csv").open("x", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"])
                for (variant, condition, repeat), code in trials.items():
                    writer.writerow([f"{variant}-{condition}-{repeat}", variant, repeat, condition,
                                     code, "exit", 1, "known_hosts unchanged; initramfs only"])
        except BaseException as error:
            result["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            for child, label in ((process, "qemu"), (server, "sshd")):
                if child is None:
                    continue
                for number in (signal.SIGTERM, signal.SIGKILL):
                    if child.poll() is None:
                        if label == "qemu":
                            result["fallback"].append(signal.Signals(number).name)
                        supervisor.signal_group(child, number)
                        supervisor.reap(child, 5)
            result["returncode"] = process.returncode if process else None
            if not (args.out / "results.csv").exists():
                log.flush()
                markers = re.findall(r"SSH_RESULT (\S+) (\S+) (\d+) (-?\d+) (\d+)",
                                     (args.out / "serial.log").read_text(errors="replace"))
                with (args.out / "results.csv").open("x", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"])
                    for variant, condition, repeat, code, changed in markers:
                        writer.writerow([f"{variant}-{condition}-{repeat}", variant, repeat,
                                         condition, code, "exit", 0,
                                         f"failed attempt; known_hosts_changed={changed}; {result['error']}"])
            (args.out / "process.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("export", "prepare", "run"))
    parser.add_argument("--reference", type=Path, default=Path("output-integrity"))
    parser.add_argument("--build", type=Path, default=Path("output-ssh-compare-01"))
    parser.add_argument("--tools", type=Path, default=Path("output-ssh-tools-01"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", choices=VARIANTS, nargs="+", default=list(VARIANTS))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--strace", type=Path, help="optional AArch64 file-syscall tracer, fixture only")
    args = parser.parse_args()
    if args.repetitions < 1 or len(set(args.variants)) != len(args.variants):
        parser.error("positive repetitions and distinct variants required")
    for name in ("reference", "build", "tools", "out"):
        setattr(args, name, getattr(args, name).resolve())
    if args.strace:
        args.strace = args.strace.resolve()
    os.nice(19)
    if args.phase == "run":
        args.out.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(__file__, args.out / "runner.py")
        shutil.copyfile(Path(__file__).with_name("guest.sh"), args.out / "guest-input.sh")
        try:
            execute(args)
        except BaseException as error:
            (args.out / "failure.json").write_text(json.dumps({"error": f"{type(error).__name__}: {error}"}, indent=2) + "\n")
            raise
    else:
        {"export": lambda value: export_qemu(value.out), "prepare": prepare}[args.phase](args)


if __name__ == "__main__":
    main()
