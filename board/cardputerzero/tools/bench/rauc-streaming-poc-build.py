#!/usr/bin/env python3
"""Build an isolated, network-enabled host RAUC without modifying vendor files."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    args.evidence.mkdir(parents=True, exist_ok=False)
    if args.output.exists():
        raise FileExistsError(args.output)
    metadata = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "buildroot": subprocess.check_output(
                    ["git", "-C", "vendor/buildroot", "rev-parse", "HEAD"], text=True).strip(),
                "platform": platform.platform(), "uname": list(platform.uname()),
                "cpu_limit": 4, "cold_output": True,
                "free_bytes": os.statvfs(root).f_bavail * os.statvfs(root).f_frsize}
    common = ["make", "-C", "vendor/buildroot", f"O={args.output.resolve()}",
              f"BR2_EXTERNAL={root}", "BR2_JLEVEL=4"]
    commands = [
        common + ["msd_cardputerzero_defconfig"],
        common + ["host-rauc", "NINJA_OPTS=-j4",
                  "HOST_RAUC_CONF_OPTS=-Djson=enabled -Dnetwork=true -Dstreaming=true "
                  "-Dservice=false -Dtests=false -Dpkcs11_engine=false -Dgpt=disabled",
                  "HOST_RAUC_DEPENDENCIES=host-json-glib host-pkgconf host-openssl "
                  "host-libglib2 host-squashfs host-libcurl host-libnl"],
    ]
    metadata["commands"] = commands
    (args.evidence / "start.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for index, command in enumerate(commands):
        start = time.monotonic()
        with (args.evidence / f"step-{index}.log").open("x") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        record = {"command": command, "exit_status": result.returncode,
                  "seconds": time.monotonic() - start}
        (args.evidence / f"step-{index}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record), flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    binary = args.output / "host/bin/rauc"
    metadata["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    metadata["version"] = subprocess.check_output([str(binary), "--version"], text=True).strip()
    (args.evidence / "complete.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
