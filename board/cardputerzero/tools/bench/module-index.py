#!/usr/bin/env python3
"""Build disposable paired images; never modify the reference build."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[4]
BOARD = ROOT / "board/cardputerzero"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): (p.stat().st_size, sha(p))
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


def fixture_probe_check(probe="/usr/libexec/module-index-kmod-probe", console="/dev/console"):
    return ("module_probe_rc=0\n"
            f"{shlex.quote(str(probe))} >{shlex.quote(console)} 2>&1 || module_probe_rc=$?\n"
            f"printf 'MODULE_INDEX_PROBE_RESULT=%s\\n' \"$module_probe_rc\" >{shlex.quote(console)}\n"
            "[ \"$module_probe_rc\" -eq 0 ] || exit \"$module_probe_rc\"\n")


def build(reference, out):
    out.mkdir()
    with (out / "build.log").open("x") as log:
        def run(args):
            subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, check=True)

        original = out / "original"
        result = subprocess.run([str(reference / "host/bin/unsquashfs"), "-no-progress", "-no-xattrs",
                                 "-d", str(original), str(reference / "images/rootfs.squashfs")],
                                capture_output=True, text=True)
        log.write(result.stdout + result.stderr)
        if result.returncode and not (result.returncode == 2 and result.stderr.splitlines() and all(
                line.startswith("set_attributes: failed to change uid and gids on ") and
                line.endswith(", because Operation not permitted") for line in result.stderr.splitlines())):
            raise RuntimeError("unsquashfs failed")
        before = inventory(original)
        private = out / "private-fixture"
        shutil.copytree(original, private, symlinks=True)
        run(["sh", BOARD / "tools/prune-module-indexes.sh", private])
        spec = importlib.util.spec_from_file_location("cnf", BOARD / "tools/bench/openssl-cnf/run.py")
        cnf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cnf)
        cnf.prepare_module_indexes(reference, private, log)
        fixture_indexes = sorted(str(p.relative_to(private)) for p in private.glob("lib/modules/*/modules.*.bin"))
        if not fixture_indexes:
            raise ValueError("fixture depmod produced no indexes")
        probe = out / "kmod-probe"
        run([reference / "host/bin/aarch64-linux-gcc", "-Os", "-Wall", "-Wextra", "-Werror",
             BOARD / "tools/bench/openssl-cnf/module.c", "-lkmod", "-o", probe])
        versions = list((original / "lib/modules").iterdir())
        if len(versions) != 1:
            raise ValueError("expected one kernel version")
        sort = out / "sort.resolved"
        sort.write_text((BOARD / "squashfs-sort.txt").read_text().replace("@KVER@", versions[0].name))
        report = {"reference_squashfs": sha(reference / "images/rootfs.squashfs"),
                  "kernel": sha(reference / "images/Image"), "variants": {},
                  "fixture_indexes": fixture_indexes}
        for variant in ("before", "before-aa", "after", "fixture"):
            directory = out / variant
            images = directory / "images"
            images.mkdir(parents=True)
            root = directory / "root"
            shutil.copytree(private if variant == "fixture" else original, root, symlinks=True)
            if variant == "after":
                run(["sh", BOARD / "tools/prune-module-indexes.sh", root])
            measured = inventory(root)
            removed = sorted(before.keys() - measured.keys())
            changed = sorted(k for k in before.keys() & measured.keys() if before[k] != measured[k])
            if variant == "after" and (changed or not removed or any(
                    not Path(p).match("lib/modules/*/modules.*.bin") for p in removed)):
                raise ValueError("pruning changed something other than binary indexes")
            report["variants"][variant] = dict(regular_bytes=sum(v[0] for v in measured.values()),
                                                removed=removed, changed=changed)
            ready = root / "etc/init.d/S98msd-ready"
            script = ready.read_text()
            markers = ("printf 'MODULE_INVENTORY_BEGIN\\n' >/dev/console\n"
                       "cat /proc/modules >/dev/console\n"
                       "printf 'MODULE_INVENTORY_END\\n' >/dev/console\n")
            if variant == "fixture":
                target = root / "usr/libexec/module-index-kmod-probe"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(probe, target)
                markers = fixture_probe_check() + markers
            if script.count("done\n") != 1:
                raise ValueError("unexpected ready script")
            ready.write_text(script.replace("done\n", "done\n" + markers))
            run([reference / "host/bin/mksquashfs.orig", root, images / "rootfs.squashfs",
                 "-noappend", "-all-root", "-no-xattrs", "-no-progress", "-comp", "zstd", "-b", "131072",
                 "-Xcompression-level", "22", "-processors", "2", "-mkfs-time", "0", "-all-time", "0",
                 "-sort", sort])
            sqfs = images / "rootfs.squashfs"
            report["variants"][variant].update(squashfs_bytes=sqfs.stat().st_size, squashfs_sha256=sha(sqfs))
            disk = images / "sdcard.img"
            run(["cp", "--sparse=always", reference / "images/sdcard.img", disk])
            partitions = json.loads(subprocess.check_output([
                str(reference / "host/sbin/sfdisk"), "--json", str(disk)]))["partitiontable"]["partitions"]
            if len(partitions) != 7:
                raise ValueError("expected seven partitions")
            with disk.open("r+b") as stream:
                for partition in partitions[4:6]:
                    if sqfs.stat().st_size > partition["size"] * 512:
                        raise ValueError("rootfs exceeds slot")
                    stream.seek(partition["start"] * 512)
                    with sqfs.open("rb") as data:
                        shutil.copyfileobj(data, stream)
            for name in ("Image", "bcm2710-rpi-cm0.dtb", "bcm2710-rpi-3-b.dtb"):
                (images / name).symlink_to(os.path.relpath(reference / "images" / name, images))
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        if report["variants"]["before"]["squashfs_sha256"] != report["variants"]["before-aa"]["squashfs_sha256"]:
            raise ValueError("A/A image mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.reference.resolve(), args.out.resolve())
