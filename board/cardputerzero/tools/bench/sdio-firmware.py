#!/usr/bin/env python3
"""Compare disposable CI images with both approved CM0 firmware families retained."""

import argparse
import csv
import json
import lzma
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import uuid

from importlib.util import module_from_spec, spec_from_file_location


ROOT = Path(__file__).resolve().parents[4]
BOARD = ROOT / "board/cardputerzero"


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KBD = load("kbd_bench", Path(__file__).with_name("kbd.py"))
COMMON = KBD.COMMON
PRUNE = load("sdio_firmware", BOARD / "tools/prune-sdio-firmware.py")


def links(root):
    return {str(p.relative_to(root)): str(p.readlink()) for p in root.rglob("*") if p.is_symlink()}


def build(artifact, host, config, out):
    out.mkdir()
    prefix = "sdio-" + uuid.uuid4().hex
    report = dict(run_prefix=prefix, host=platform.platform(), phase="preflight", variants={}, modules={})
    rows = {}

    def plan(variant, metric, repeat=1):
        rows[variant, metric] = dict(run_id=f"{prefix}-{variant}-{metric}", variant=variant, repeat=repeat,
                                    metric=metric, value="", unit="bytes" if metric.endswith("bytes") else "count"
                                    if metric.endswith("count") else "status" if metric.endswith("code") else "boolean",
                                    valid="false", note="not run: earlier stage incomplete")

    def record(variant, metric, value, valid=True, note="observed result"):
        rows[variant, metric].update(value=value, valid=str(valid).lower(), note=note)

    for variant in ("before", "before-aa", "after"):
        for metric in ("rootfs_regular_bytes", "squashfs_bytes"):
            plan(variant, metric, 2 if variant == "before-aa" else 1)
    for variant in ("before-A", "before-B", "after-A", "after-B"):
        for metric in ("boot_exit_code", "loadkeys_exit_code", "module_count"):
            plan(variant, metric)
    for variant, metric in (("aa", "image_equal"), ("negative", "missing_required_rejected"), ("modules", "inventory_equal")):
        plan(variant, metric)
    plan("preflight", "preflight_exit_code")
    (out / "plan.json").write_text(json.dumps(list(rows.values()), indent=2) + "\n")
    with (out / "build.log").open("x") as log:
        def run(args):
            subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, check=True)

        try:
            report["execution_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            source = report["source_sha256"] = KBD.source_inputs()
            paths = [Path(__file__).relative_to(ROOT), Path("board/cardputerzero/tools/prune-sdio-firmware.py")]
            subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *map(str, paths)], cwd=ROOT, check=True)
            source.update({str(p): COMMON.sha(ROOT / p) for p in paths})
            report["config_sha256"] = COMMON.sha(config)
            for field, parent, names in (
                    ("input_sha256", artifact / "images", ("sdcard.img.xz", "Image", "bcm2710-rpi-cm0.dtb", "bcm2710-rpi-3-b.dtb")),
                    ("host_tools_sha256", host, ("bin/unsquashfs", "bin/mksquashfs.orig", "sbin/sfdisk"))):
                hashes = report[field] = {}
                for name in names:
                    hashes[name] = COMMON.sha(parent / name)
            versions = report["host_tools_versions"] = {}
            for name, flag in (("bin/unsquashfs", "-version"), ("bin/mksquashfs.orig", "-version"), ("sbin/sfdisk", "--version")):
                versions[name] = KBD.tool_version(host / name, flag)
            record("preflight", "preflight_exit_code", 0)
            report["phase"] = "measurement"
            disk = out / "source.img"
            with lzma.open(artifact / "images/sdcard.img.xz") as src, disk.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            partitions = json.loads(subprocess.check_output([str(host / "sbin/sfdisk"), "--json", str(disk)]))["partitiontable"]["partitions"]
            if len(partitions) != 7:
                raise ValueError("expected seven source partitions")
            original = out / "original"
            extracted = subprocess.run(list(map(str, [host / "bin/unsquashfs", "-no-xattrs", "-no-progress", "-offset",
                                       partitions[4]["start"] * 512, "-d", original, disk])), capture_output=True, text=True)
            output = extracted.stdout + extracted.stderr
            log.write(output)
            warning = f"set_attributes: failed to change uid and gids on {original}/var/www, because Operation not permitted"
            if extracted.returncode == 2 and output.count(warning) == 1 and not re.search(
                    r"error|failed|cannot|fatal", output.replace(warning, ""), re.I):
                report["extraction_warning"] = warning
            else:
                extracted.check_returncode()
            configured = KBD.load("libgomp", Path(__file__).with_name("libgomp.py"))
            report["reference_audit"] = configured.audit_configured(original, config)
            before = COMMON.inventory(original)
            before_links = links(original)
            if list((original / "usr/lib").glob("libgomp.so*")) or list((original / "lib/modules").glob("*/modules.*.bin")):
                raise ValueError("reference must include candidates 1 and 2")
            if any((original / "usr/bin" / name).exists() for name in ("dumpkeys", "setfont", "kbd_mode")):
                raise ValueError("reference must include candidate 3")
            (out / "inventory.json").write_text(json.dumps(before, indent=2) + "\n")
            (out / "symlinks.json").write_text(json.dumps(before_links, indent=2) + "\n")
            negative = out / "negative-root"
            shutil.copytree(original, negative, symlinks=True)
            missing = negative / "lib/firmware/brcm/BCM4343A2.hcd"
            missing.unlink()
            negative_before, negative_links = COMMON.inventory(negative), links(negative)
            rejected = False
            try:
                PRUNE.prune(negative)
            except ValueError as error:
                report["negative_error"] = str(error)
                rejected = "missing or empty required firmware" in str(error) and str(missing) in str(error)
            rejected = rejected and negative_before == COMMON.inventory(negative) and negative_links == links(negative)
            record("negative", "missing_required_rejected", int(rejected), rejected)
            if not rejected:
                raise ValueError("missing-required negative control failed")
            version = next((original / "lib/modules").iterdir()).name
            sort = out / "sort.resolved"
            sort.write_text((BOARD / "squashfs-sort.txt").read_text().replace("@KVER@", version))
            for variant in ("before", "before-aa", "after"):
                root = out / variant / "root"
                images = root.parent / "images"
                images.mkdir(parents=True)
                shutil.copytree(original, root, symlinks=True)
                removed = PRUNE.prune(root) if variant == "after" else []
                measured, measured_links = COMMON.inventory(root), links(root)
                if any(before[p] != measured[p] for p in before.keys() & measured.keys()):
                    raise ValueError("retained file changed")
                if any(before_links[p] != measured_links[p] for p in before_links.keys() & measured_links.keys()):
                    raise ValueError("retained symlink changed")
                if (set(before) | set(before_links)) - (set(measured) | set(measured_links)) != set(removed):
                    raise ValueError("unexpected removed file")
                report["variants"][variant] = dict(removed=removed, regular_bytes=sum(v[0] for v in measured.values()),
                    firmware={p: {"bytes": v[0], "sha256": v[1]} for p, v in measured.items() if p.startswith("lib/firmware/")},
                    firmware_links={p: v for p, v in measured_links.items() if p.startswith("lib/firmware/")})
                script = root / "etc/init.d/S04msd-keymap"
                script.write_text(script.read_text().replace("#!/bin/sh\n", "#!/bin/sh\n" + KBD.keymap_hook(), 1))
                ready = root / "etc/init.d/S98msd-ready"
                text = ready.read_text()
                if text.count("done\n") != 1:
                    raise ValueError("unexpected ready script")
                ready.write_text(text.replace("done\n", "done\n"
                    "printf 'MODULE_INVENTORY_BEGIN\\n' >/dev/console\ncat /proc/modules >/dev/console\n"
                    "printf 'MODULE_INVENTORY_END\\n' >/dev/console\n"))
                sqfs = images / "rootfs.squashfs"
                run([host / "bin/mksquashfs.orig", root, sqfs, "-noappend", "-all-root", "-no-xattrs", "-no-progress",
                     "-comp", "zstd", "-b", "131072", "-Xcompression-level", "22", "-processors", "2",
                     "-mkfs-time", "0", "-all-time", "0", "-sort", sort])
                report["variants"][variant].update(squashfs_bytes=sqfs.stat().st_size, squashfs_sha256=COMMON.sha(sqfs))
                record(variant, "rootfs_regular_bytes", report["variants"][variant]["regular_bytes"])
                record(variant, "squashfs_bytes", sqfs.stat().st_size)
                image = images / "sdcard.img"
                run(["cp", "--sparse=always", disk, image])
                with image.open("r+b") as dst:
                    for partition in partitions[4:6]:
                        if sqfs.stat().st_size > partition["size"] * 512:
                            raise ValueError("rootfs exceeds slot")
                        dst.seek(partition["start"] * 512)
                        with sqfs.open("rb") as src:
                            shutil.copyfileobj(src, dst)
                for name in ("Image", "bcm2710-rpi-cm0.dtb", "bcm2710-rpi-3-b.dtb"):
                    (images / name).symlink_to(os.path.relpath(artifact / "images" / name, images))
            aa = report["variants"]["before"]["squashfs_sha256"] == report["variants"]["before-aa"]["squashfs_sha256"]
            record("aa", "image_equal", int(aa), aa)
            if not aa:
                raise ValueError("A/A image mismatch")
            for variant, slot in (("before", "A"), ("before", "B"), ("after", "A"), ("after", "B")):
                key = f"{variant}-{slot}"
                logs = out / key
                env = dict(os.environ, OUTPUT_DIR=str(out / variant), QEMU_LOG_DIR=str(logs), QEMU_HASH_IMAGE="0")
                with (out / f"{key}.log").open("x") as f:
                    result = subprocess.run([str(BOARD / "qemu" / ("test-boot.sh" if slot == "A" else "test-ab.sh"))],
                                            env=env, stdout=f, stderr=subprocess.STDOUT)
                record(key, "boot_exit_code", result.returncode, result.returncode == 0)
                if result.returncode:
                    raise ValueError("QEMU boot failed: " + key)
                text = (logs / f"serial-mmcblk0p{5 if slot == 'A' else 6}.log").read_text()
                modules = KBD.check_serial(text)
                report["modules"][key] = modules
                record(key, "loadkeys_exit_code", 0)
                record(key, "module_count", len(modules))
            equal = all(m == report["modules"]["before-A"] for m in report["modules"].values())
            record("modules", "inventory_equal", int(equal), equal)
            if not equal:
                raise ValueError("module inventories differ")
            report["phase"] = "complete"
        except Exception as error:
            report["error"] = str(error)
            report["error_type"] = type(error).__name__
            if report["phase"] == "preflight":
                record("preflight", "preflight_exit_code", 1, False, str(error))
            raise
        finally:
            (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
            with (out / "results.csv").open("x", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"], lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows.values())
    print(json.dumps({name: {k: v for k, v in data.items() if k not in ("firmware", "firmware_links", "removed")}
                      for name, data in report["variants"].items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--host-tools", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.artifact.resolve(), args.host_tools.resolve(), args.config.resolve(), args.out.resolve())
