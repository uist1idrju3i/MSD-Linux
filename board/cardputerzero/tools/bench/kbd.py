#!/usr/bin/env python3
"""Repack a verified CI artifact and check kbd, keymap and module invariants."""

import argparse
import csv
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[4]
BOARD = ROOT / "board/cardputerzero"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMON = load("module_index", Path(__file__).with_name("module-index.py"))
PRUNE = load("prune_kbd", BOARD / "tools/prune-kbd.py")


def keymap_hook(negative=False):
    command = '/bin/false' if negative else '/usr/bin/loadkeys "$@"'
    return ("loadkeys() {\n" + command + "\n_kbd_rc=$?\n"
            "printf 'KBD_LOADKEYS_RESULT=%s\\n' \"$_kbd_rc\" >/dev/console\n"
            "return \"$_kbd_rc\"\n}\n")


def tool_version(path, flag):
    result = subprocess.run([str(path), flag], capture_output=True, text=True)
    text = result.stdout
    if result.returncode and not (path.name == "unsquashfs" and result.returncode == 1
                                  and text.startswith("unsquashfs version ")):
        raise ValueError("version probe failed: " + str(path))
    if not text.strip():
        raise ValueError("version probe returned no version: " + str(path))
    return text.splitlines()[0]


def check_serial(text):
    if re.findall(r"^KBD_LOADKEYS_RESULT=(\d+)\r?$", text, re.M) != ["0"]:
        raise ValueError("missing, repeated or failed real S04 loadkeys result")
    if text.count("MODULE_INVENTORY_BEGIN") != 1 or text.count("MODULE_INVENTORY_END") != 1:
        raise ValueError("missing or repeated module inventory")
    body = text.split("MODULE_INVENTORY_BEGIN", 1)[1].split("MODULE_INVENTORY_END", 1)[0]
    modules = []
    for line in body.splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 6 or not fields[1].isdigit() or not fields[2].isdigit():
            raise ValueError("malformed module inventory")
        modules.append((fields[0], int(fields[1]), fields[3], fields[4]))
    if not modules or len({m[0] for m in modules}) != len(modules):
        raise ValueError("empty or duplicate module inventory")
    return sorted(modules)


def source_inputs():
    scripts = [Path(__file__).relative_to(ROOT), Path("board/cardputerzero/post-build.sh"),
               Path("board/cardputerzero/squashfs-sort.txt"),
               *(Path("board/cardputerzero/tools") / name for name in
                 ("prune-kbd.py", "prune-libgomp.py", "prune-module-indexes.sh", "bench/module-index.py", "bench/libgomp.py")),
               *(Path("board/cardputerzero/qemu") / name for name in
                 ("test-boot.sh", "test-ab.sh", "test-qemu.sh", "boot-test.py", "run-qemu.sh", "check-serial-log.sh", "serial-allowlist.txt")),
               Path("board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py")]
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *map(str, scripts)], cwd=ROOT, check=True)
    return {str(p): COMMON.sha(ROOT / p) for p in scripts}


def negative_rejected(returncode, text, output, process):
    return (returncode == 1
            and re.findall(r"^KBD_LOADKEYS_RESULT=(\d+)\r?$", text, re.M) == ["1"]
            and "MSD/Linux ready" in text and re.search(r"login:", text, re.I) is not None
            and "msd-keymap: failed to load " in text
            and "QEMU reached ready after " in output
            and "QEMU serial log contains boot error patterns." in output
            and process.get("qmp_quit") is True and process.get("reaped") is True
            and process.get("returncode") == 0 and process.get("fallback") == []
            and process.get("error") is None)


def build(artifact, host, config, out):
    out.mkdir()
    run_prefix = "kbd-" + uuid.uuid4().hex
    source = source_inputs()
    report = dict(execution_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  source_sha256=source, host=platform.platform(), config_sha256=COMMON.sha(config),
                  input_sha256={p: COMMON.sha(artifact / "images" / p) for p in
                                ("sdcard.img.xz", "Image", "bcm2710-rpi-cm0.dtb", "bcm2710-rpi-3-b.dtb")},
                  host_tools_sha256={p: COMMON.sha(host / p) for p in
                                     ("bin/unsquashfs", "bin/mksquashfs.orig", "sbin/sfdisk")},
                  host_tools_versions={p: tool_version(host / p, flag)
                                       for p, flag in (("bin/unsquashfs", "-version"),
                                                       ("bin/mksquashfs.orig", "-version"), ("sbin/sfdisk", "--version"))},
                  run_prefix=run_prefix, variants={}, modules={})
    rows = {}

    def plan(variant, metric, repeat=1):
        rows[variant, metric] = dict(run_id=f"{run_prefix}-{variant}-{metric}", variant=variant, repeat=repeat,
                                    metric=metric, value="", unit="bytes" if "bytes" in metric else
                                    "status" if metric.endswith("exit_code") else "boolean" if metric.endswith("equal") else "count",
                                    valid="false", note="not run: earlier stage incomplete")

    def record(variant, metric, value, valid=True, note="observed result"):
        rows[variant, metric].update(value=value, valid=str(valid).lower(), note=note)

    for variant in ("before", "before-aa", "after"):
        for metric in ("rootfs_regular_bytes", "squashfs_bytes"):
            plan(variant, metric, 2 if variant == "before-aa" else 1)
    for variant in ("before-A", "before-B", "after-A", "after-B"):
        for metric in ("boot_exit_code", "loadkeys_exit_code", "module_count"):
            plan(variant, metric)
    for variant, metric in (("aa", "image_equal"), ("negative", "boot_exit_code"), ("modules", "inventory_equal")):
        plan(variant, metric)
    (out / "plan.json").write_text(json.dumps(list(rows.values()), indent=2) + "\n")
    with (out / "build.log").open("x") as log:
        def run(args):
            subprocess.run(list(map(str, args)), stdout=log, stderr=subprocess.STDOUT, check=True)

        try:
            disk = out / "source.img"
            with lzma.open(artifact / "images/sdcard.img.xz") as src, disk.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            partitions = json.loads(subprocess.check_output([str(host / "sbin/sfdisk"), "--json", str(disk)]))["partitiontable"]["partitions"]
            if len(partitions) != 7:
                raise ValueError("expected seven source partitions")
            original = out / "original"
            extracted = subprocess.run(list(map(str, [host / "bin/unsquashfs", "-no-xattrs", "-no-progress", "-offset",
                                       partitions[4]["start"] * 512, "-d", original, disk])), capture_output=True, text=True)
            log.write(extracted.stdout + extracted.stderr)
            warning = f"set_attributes: failed to change uid and gids on {original}/var/www, because Operation not permitted"
            output = extracted.stdout + extracted.stderr
            if extracted.returncode == 2 and output.count(warning) == 1 and not re.search(
                    r"error|failed|cannot|fatal", output.replace(warning, ""), re.I):
                report["extraction_warning"] = warning
            else:
                extracted.check_returncode()
            configured = load("libgomp", Path(__file__).with_name("libgomp.py"))
            report["reference_audit"] = configured.audit_configured(original, config)
            before = COMMON.inventory(original)
            if list((original / "usr/lib").glob("libgomp.so*")) or list((original / "lib/modules").glob("*/modules.*.bin")):
                raise ValueError("reference must already include candidates 1 and 2")
            for name in ("loadkeys", "dumpkeys", "setfont", "kbd_mode"):
                if f"usr/bin/{name}" not in before:
                    raise ValueError("reference must include unpruned kbd tools: " + name)
            (out / "inventory.json").write_text(json.dumps(before, indent=2) + "\n")
            version = next((original / "lib/modules").iterdir()).name
            sort = out / "sort.resolved"
            sort.write_text((BOARD / "squashfs-sort.txt").read_text().replace("@KVER@", version))
            for variant in ("before", "before-aa", "after", "negative"):
                root = out / variant / "root"
                images = root.parent / "images"
                images.mkdir(parents=True)
                shutil.copytree(original, root, symlinks=True)
                removed = PRUNE.prune(root) if variant in ("after", "negative") else []
                measured = COMMON.inventory(root)
                if any(before[p] != measured[p] for p in before.keys() & measured.keys()):
                    raise ValueError("retained file changed")
                if set(before) - set(measured) != {p for p in removed if p in before}:
                    raise ValueError("unexpected removed file")
                report["variants"][variant] = dict(removed=removed, regular_bytes=sum(v[0] for v in measured.values()))
                script = root / "etc/init.d/S04msd-keymap"
                script.write_text(script.read_text().replace("#!/bin/sh\n", "#!/bin/sh\n" + keymap_hook(variant == "negative"), 1))
                ready = root / "etc/init.d/S98msd-ready"
                text = ready.read_text()
                if text.count("done\n") != 1:
                    raise ValueError("unexpected ready script")
                ready.write_text(text.replace("done\n", "done\n"
                    "printf 'MODULE_INVENTORY_BEGIN\\n' >/dev/console\ncat /proc/modules >/dev/console\n"
                    "printf 'MODULE_INVENTORY_END\\n' >/dev/console\n"
                    "/bin/busybox --list-full >/dev/console\n/usr/bin/loadkeys -V >/dev/console 2>&1\n"))
                sqfs = images / "rootfs.squashfs"
                run([host / "bin/mksquashfs.orig", root, sqfs, "-noappend", "-all-root", "-no-xattrs", "-no-progress",
                     "-comp", "zstd", "-b", "131072", "-Xcompression-level", "22", "-processors", "2",
                     "-mkfs-time", "0", "-all-time", "0", "-sort", sort])
                report["variants"][variant].update(squashfs_bytes=sqfs.stat().st_size, squashfs_sha256=COMMON.sha(sqfs))
                if variant != "negative":
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
            for variant, slot in (("before", "A"), ("before", "B"), ("after", "A"), ("after", "B"), ("negative", "A")):
                logs = out / f"{variant}-{slot}"
                env = dict(os.environ, OUTPUT_DIR=str(out / variant), QEMU_LOG_DIR=str(logs), QEMU_HASH_IMAGE="0")
                with (out / f"{variant}-{slot}.log").open("x") as f:
                    result = subprocess.run([str(BOARD / "qemu" / ("test-boot.sh" if slot == "A" else "test-ab.sh"))],
                                            env=env, stdout=f, stderr=subprocess.STDOUT)
                text = (logs / f"serial-mmcblk0p{5 if slot == 'A' else 6}.log").read_text()
                if variant == "negative":
                    process = json.loads((logs / "serial-mmcblk0p5.process.json").read_text())
                    rejected = negative_rejected(result.returncode, text, (out / f"{variant}-{slot}.log").read_text(), process)
                    record("negative", "boot_exit_code", result.returncode, rejected, "expected keymap failure")
                    if not rejected:
                        raise ValueError("negative keymap control was not rejected")
                    continue
                key = f"{variant}-{slot}"
                record(key, "boot_exit_code", result.returncode, result.returncode == 0)
                if result.returncode:
                    raise ValueError("QEMU boot failed: " + key)
                modules = check_serial(text)
                report["modules"][key] = modules
                record(key, "loadkeys_exit_code", 0)
                record(key, "module_count", len(modules))
            equal = all(m == report["modules"]["before-A"] for m in report["modules"].values())
            record("modules", "inventory_equal", int(equal), equal)
            if not equal:
                raise ValueError("module inventories differ")
        except Exception as error:
            report["error"] = str(error)
            raise
        finally:
            (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
            with (out / "results.csv").open("x", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"], lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows.values())
    print(json.dumps(report["variants"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--host-tools", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.artifact.resolve(), args.host_tools.resolve(), args.config.resolve(), args.out.resolve())
