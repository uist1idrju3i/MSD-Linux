#!/usr/bin/env python3
"""Build an isolated cold pair at the same O= path without compiler caching."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[4]
OPTIONS = ("CMP", "QUIC", "SSL_TRACE", "COMP")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def build(out):
    out.mkdir(parents=True)
    prefix = "openssl-features-" + uuid.uuid4().hex
    rows = [dict(run_id=f"{prefix}-{variant}-{metric}", variant=variant, repeat=1,
                 metric=metric, value="", unit="bytes" if metric.endswith("bytes") else "status",
                 valid="false", note="not run: previous stage incomplete")
            for variant in ("baseline", "candidate")
            for metric in ("build_exit_code", "rootfs_regular_bytes", "squashfs_bytes")]
    (out / "plan.json").write_text(json.dumps(rows, indent=2) + "\n")
    report = dict(run_prefix=prefix, host=platform.platform(), variants={})
    work = out / "work"
    env = dict(os.environ, LC_ALL="C", TZ="UTC")
    variant = None

    def run(command, log):
        subprocess.run(list(map(str, command)), cwd=ROOT, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)

    try:
        report["execution_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["runner_sha256"] = sha(Path(__file__))
        report["source_sha256"] = {}
        names = subprocess.check_output(["git", "ls-files", "-z", "board", "configs", "package",
                                         "external.mk", "Config.in"], cwd=ROOT).split(b"\0")
        for name in filter(None, names):
            path = ROOT / os.fsdecode(name)
            if path.is_file():
                report["source_sha256"][os.fsdecode(name)] = sha(path)
        report["buildroot_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT / "vendor/buildroot", text=True).strip()
        report["o_path"] = str(work.relative_to(ROOT))
        report["conditions"] = "cold O=; ccache disabled; reproducible enabled; jobs=6; shared source cache"
        for variant in ("baseline", "candidate"):
            with (out / f"{variant}-build.log").open("x") as log:
                run(["make", "-C", "vendor/buildroot", f"BR2_EXTERNAL={ROOT}", f"O={work}",
                     "msd_cardputerzero_defconfig"], log)
                config = ROOT / "vendor/buildroot/utils/config"
                run([config, "--file", work / ".config", "--disable", "BR2_CCACHE",
                     "--enable", "BR2_REPRODUCIBLE", "--set-val", "BR2_JLEVEL", "6"], log)
                if variant == "candidate":
                    for option in OPTIONS:
                        run([config, "--file", work / ".config", "--disable",
                             "BR2_PACKAGE_LIBOPENSSL_ENABLE_" + option], log)
                run(["make", "-C", work, "olddefconfig"], log)
                config_text = (work / ".config").read_text()
                for option in OPTIONS:
                    symbol = "BR2_PACKAGE_LIBOPENSSL_ENABLE_" + option
                    expected = symbol + "=y" if variant == "baseline" else "# " + symbol + " is not set"
                    if expected not in config_text.splitlines():
                        raise ValueError("configuration did not select " + expected)
                report["variants"][variant] = dict(config_sha256=sha(work / ".config"))
                run(["make", "-C", work], log)
                for row in rows:
                    if row["variant"] != variant:
                        continue
                    metric = row["metric"]
                    value = (0 if metric == "build_exit_code" else
                             (work / "images/rootfs.squashfs").stat().st_size if metric == "squashfs_bytes" else
                             sum(path.stat().st_size for path in (work / "target").rglob("*")
                                 if path.is_file() and not path.is_symlink()))
                    row.update(value=value, valid="true", note="full cold build")
                report["variants"][variant]["images_sha256"] = {
                    name: sha(work / "images" / name) for name in
                    ("Image", "rootfs.squashfs", "sdcard.img")}
                shutil.move(work, out / variant)
                (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
                print(f"{variant}: full build complete", flush=True)
    except Exception as error:
        report["error"] = repr(error)
        if isinstance(error, subprocess.CalledProcessError) and variant is not None:
            row = next(row for row in rows if row["variant"] == variant and row["metric"] == "build_exit_code")
            row.update(value=error.returncode, valid="false", note="build command failed: " + repr(error.cmd))
        raise
    finally:
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        with (out / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build(args.out.resolve())
