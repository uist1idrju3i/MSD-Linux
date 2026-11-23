#!/usr/bin/env python3
"""Separate image bytes, target staging bytes and randomized non-OpenSSL files."""

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[5]
spec = importlib.util.spec_from_file_location("inventory", Path(__file__).resolve().parents[1] / "module-index.py")
COMMON = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COMMON)
OPENSSL = ("usr/lib/libcrypto.so.3", "usr/lib/libssl.so.3", "usr/bin/openssl", "usr/lib/ossl-modules/legacy.so")


def analyze(pair, out):
    out.mkdir()
    prefix = "openssl-analysis-" + uuid.uuid4().hex
    rows = [dict(run_id=f"{prefix}-{variant}-{metric}", variant=variant, repeat=1, metric=metric,
                 value="", unit="bytes", valid="false", note="not run")
            for variant in ("baseline", "candidate")
            for metric in ("rootfs_image_regular_bytes", "squashfs_used_bytes", "openssl_elf_bytes", *OPENSSL)]
    rows += [dict(run_id=f"{prefix}-{variant}-control", variant=variant, repeat=1,
                  metric="control_squashfs_bytes", value="", unit="bytes", valid="false", note="not run")
             for variant in ("baseline", "baseline-aa", "isolated")]
    (out / "plan.json").write_text(json.dumps(rows, indent=2) + "\n")
    metadata = dict(run_prefix=prefix, runner_sha256=COMMON.sha(Path(__file__)), tool_sha256={}, inputs_sha256={})

    def record(variant, metric, value, note):
        row = next(row for row in rows if row["variant"] == variant and row["metric"] == metric)
        row.update(value=value, valid="true", note=note)

    try:
        metadata["execution_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        metadata["sort_source_sha256"] = COMMON.sha(ROOT / "board/cardputerzero/squashfs-sort.txt")
        with (out / "analysis.log").open("x") as log:
            host = pair / "baseline/host/bin"
            tools = {name: host / name for name in ("unsquashfs", "mksquashfs.orig")}
            for name, tool in tools.items():
                metadata["tool_sha256"][name] = COMMON.sha(tool)
                result = subprocess.run([str(tool), "-version"], stdout=log, stderr=subprocess.STDOUT)
                if result.returncode not in (0, 1):
                    raise ValueError("tool version query failed")
            manifests = {}
            for variant in ("baseline", "candidate"):
                image = pair / variant / "images/rootfs.squashfs"
                metadata["inputs_sha256"][variant] = COMMON.sha(image)
                root = out / variant
                result = subprocess.run([str(tools["unsquashfs"]), "-no-progress", "-no-xattrs", "-d", str(root), str(image)],
                                        capture_output=True, text=True)
                log.write(result.stdout + result.stderr)
                if result.returncode and not (result.returncode == 2 and result.stderr.splitlines() and all(
                        line.startswith("set_attributes: failed to change uid and gids on ") and
                        line.endswith(", because Operation not permitted") for line in result.stderr.splitlines())):
                    raise ValueError("rootfs extraction failed")
                manifest = COMMON.inventory(root)
                manifests[variant] = manifest
                (out / f"{variant}-files.json").write_text(json.dumps(manifest, indent=2) + "\n")
                record(variant, "rootfs_image_regular_bytes", sum(value[0] for value in manifest.values()), "actual extracted SquashFS")
                with image.open("rb") as stream:
                    header = stream.read(96)
                if header[:4] != b"hsqs":
                    raise ValueError("invalid SquashFS superblock")
                record(variant, "squashfs_used_bytes", struct.unpack_from("<Q", header, 40)[0], "SquashFS superblock, excluding padding")
                record(variant, "openssl_elf_bytes", sum(manifest[name][0] for name in OPENSSL), "four installed OpenSSL ELF files")
                for name in OPENSSL:
                    record(variant, name, manifest[name][0], "installed regular file")
            before, after = manifests["baseline"], manifests["candidate"]
            if before.keys() != after.keys():
                raise ValueError("installed regular-file set differs")
            metadata["changed_files"] = [name for name in sorted(before) if before[name] != after[name]]
            if COMMON.sha(out / "baseline/etc/ssl/openssl.cnf") != COMMON.sha(out / "candidate/etc/ssl/openssl.cnf"):
                raise ValueError("C1 configuration differs")
            versions = list((out / "baseline/lib/modules").iterdir())
            if len(versions) != 1:
                raise ValueError("expected one kernel version")
            sort = out / "sort.resolved"
            sort.write_text((ROOT / "board/cardputerzero/squashfs-sort.txt").read_text().replace("@KVER@", versions[0].name))
            metadata["sort_resolved_sha256"] = COMMON.sha(sort)
            isolated = out / "isolated"
            shutil.copytree(out / "baseline", isolated, symlinks=True)
            for name in OPENSSL:
                shutil.copy2(out / "candidate" / name, isolated / name)
            hashes = {}
            for variant, root in (("baseline", out / "baseline"), ("baseline-aa", out / "baseline"), ("isolated", isolated)):
                image = out / f"{variant}-control.squashfs"
                subprocess.run([str(tools["mksquashfs.orig"]), str(root), str(image), "-noappend", "-all-root", "-no-hardlinks",
                                "-no-xattrs", "-no-progress", "-comp", "zstd", "-b", "131072", "-Xcompression-level", "22",
                                "-processors", "2", "-mkfs-time", "0", "-all-time", "0", "-sort", str(sort)],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
                hashes[variant] = COMMON.sha(image)
                record(variant, "control_squashfs_bytes", image.stat().st_size,
                       "normalized repack; isolated changes only four OpenSSL files")
            metadata["control_sha256"] = hashes
            if hashes["baseline"] != hashes["baseline-aa"]:
                for row in rows:
                    if row["metric"] == "control_squashfs_bytes":
                        row.update(valid="false", note="A/A hashes differ")
                raise ValueError("A/A hashes differ")
    except Exception as error:
        metadata["error"] = repr(error)
        raise
    finally:
        (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        with (out / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print("Image analysis: two inventories; A/A hash match; isolated OpenSSL control complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    analyze(args.pair.resolve(), args.out.resolve())
