#!/usr/bin/env python3
"""Serial stage-4 construction, diagnostic controls and smoke-only launch."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import preflight
import storage
from supervisor import write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CASES = [("E1", "smoke"), ("E1", "smoke"),
         *[("E1", path) for path in ("T1", "T1-final", "T1-sample", "T1-sample-selected",
                                     "T1-negative", "T1-negative-final", "T2", "T3", "T4-sync",
                                     "T4-nosync", "T4-idle-control", "T4-odirect-control", "T5", "T7")],
         ("F1", "smoke"), ("B1", "smoke"), ("L1", "smoke"), ("I1", "smoke"), ("I2", "T6")]


def capture(command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "representative", "smoke"))
    parser.add_argument("--runs-dir", required=True, type=Path)
    args = parser.parse_args()
    root = storage.persistent(args.runs_dir)
    root.mkdir(parents=True, exist_ok=True)
    output = Path(os.environ.get("OUTPUT_DIR", ROOT / "output-fscmp-v2")).resolve()
    os.environ["OUTPUT_DIR"] = str(output)
    os.environ["FSCMP_MAX_ATTEMPTS"] = "2"
    directory = root / args.action
    directory.mkdir(exist_ok=False)
    meta = dict(action=args.action, commit=capture(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
                buildroot=capture(["git", "-C", str(ROOT / "vendor/buildroot"), "rev-parse", "HEAD"]),
                output=str(output), pid=os.getpid(), started_epoch=time.time(),
                host=capture(["uname", "-a"]), os_release=Path("/etc/os-release").read_text(),
                df=capture(["df", "-B1", str(root)]),
                ccache_environment={key: value for key, value in os.environ.items() if "CCACHE" in key},
                qemu=dict(version=capture(["qemu-system-aarch64", "--version"]),
                          sha256=preflight.digest(shutil.which("qemu-system-aarch64"))),
                profile=preflight.smoke_profile.load(), profile_sha256=preflight.smoke_profile.fingerprint())
    write_json(directory / "start.json", meta)
    started = time.monotonic()
    try:
        if args.action == "build":
            if (output / ".config").exists():
                raise ValueError("stage-4 build requires a fresh output directory")
            command = [str(HERE / "fs-compare-build.sh")]
            write_json(directory / "command.json", command)
            with (directory / "build.log").open("x") as log:
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            environment = preflight.environment(output)
            write_json(directory / "environment.json", environment)
            compiler = next((output / "host/bin").glob("aarch64*-gcc"))
            write_json(directory / "compiler.json", dict(version=capture([str(compiler), "--version"]),
                                                         sha256=preflight.digest(compiler)))
            ccache = output / "host/bin/ccache"
            if ccache.exists():
                write_json(directory / "ccache-after.json", capture([str(ccache), "-s"]))
        elif args.action == "representative":
            with (directory / "results.csv").open("x", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=("number", "config", "path", "status", "seconds", "directory"))
                writer.writeheader()
                for number, (config, path) in enumerate(CASES, 1):
                    destination = directory / f"{number:02d}-{config}-{path}"
                    command = ["python3", str(HERE / "preflight.py"), "diagnose", config, path, str(destination)]
                    start = time.monotonic()
                    with (directory / f"{number:02d}.log").open("x") as log:
                        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
                    row = dict(number=number, config=config, path=path, status=result.returncode,
                               seconds=time.monotonic() - start, directory=str(destination))
                    writer.writerow(row)
                    stream.flush()
                    os.fsync(stream.fileno())
                    print(json.dumps(row), flush=True)
                    if result.returncode:
                        raise ValueError(f"representative diagnostic failed: {destination}")
        else:
            if not (root / "representative/result.json").exists() or not storage.load_json(root / "representative/result.json")["ok"]:
                raise ValueError("representative controls must pass before full smoke")
            rows = preflight.generated("all", 1)
            if len(preflight.requirements(rows)) != 851:
                raise ValueError("unexpected smoke coverage size")
            plan = directory / "plan.tsv"
            plan.write_bytes(preflight.plan_bytes(rows))
            preflight.gate(rows, directory, output,
                           parameters=dict(plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(), smoke_only=True))
    except BaseException as error:
        write_json(directory / "result.json", dict(ok=False, seconds=time.monotonic() - started, error=str(error)))
        raise
    write_json(directory / "result.json", dict(ok=True, seconds=time.monotonic() - started,
                                               df=capture(["df", "-B1", str(root)])))


if __name__ == "__main__":
    main()
