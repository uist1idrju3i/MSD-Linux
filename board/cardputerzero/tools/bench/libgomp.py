#!/usr/bin/env python3
"""Audit and repack disposable images without changing the reference build."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[4]
BOARD = ROOT / "board/cardputerzero"
SPEC = importlib.util.spec_from_file_location("module_index", Path(__file__).with_name("module-index.py"))
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)


def needed(path):
    text = subprocess.check_output(["readelf", "-d", str(path)], text=True)
    return re.findall(r"\(NEEDED\).*?\[(.*?)\]", text)


def audit(root):
    result = dict(elf={}, literal_consumers=[], gomp_nonproviders=[], dlopen_tokens=[])
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        name = str(path.relative_to(root))
        data = path.read_bytes()
        provider = path.parent in (root / "lib", root / "usr/lib") and path.name.startswith("libgomp.so")
        if data.startswith(b"\x7fELF"):
            result["elf"][name] = needed(path)
        if not provider:
            if b"libgomp" in data:
                result["literal_consumers"].append(name)
            if b"GOMP_" in data:
                result["gomp_nonproviders"].append(name)
            if b"dlopen" in data:
                result["dlopen_tokens"].append(name)
    result["needed_consumers"] = [name for name, libs in result["elf"].items()
                                  if any(lib.startswith("libgomp") for lib in libs)]
    if result["literal_consumers"] or result["needed_consumers"] or result["gomp_nonproviders"]:
        raise ValueError("reference has possible OpenMP consumers; stop without pruning")
    return result


def build(reference, config, out):
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
            raise ValueError("unsquashfs failed")
        run(["sh", BOARD / "tools/prune-module-indexes.sh", original])
        before = COMMON.inventory(original)
        if "usr/lib/libgomp.so.1.0.0" not in before:
            raise ValueError("--reference must contain libgomp before pruning")
        report = dict(reference_squashfs=COMMON.sha(reference / "images/rootfs.squashfs"),
                      kernel=COMMON.sha(reference / "images/Image"), host=platform.platform(),
                      config_sha256=COMMON.sha(config), audit=audit(original), variants={})
        recipes = sorted({p.parent.name for p in (ROOT / "vendor/buildroot/package").glob("*/*.mk")
                          if re.search(r"openmp|libgomp", p.read_text(), re.I)})
        report["openmp_recipes"] = recipes
        report["enabled_openmp_recipes"] = [p for p in recipes if re.search(
            "^BR2_PACKAGE_" + p.upper().replace("-", "_") + "=y$", config.read_text(), re.M)]
        if report["enabled_openmp_recipes"]:
            raise ValueError("enabled OpenMP-related package requires review")
        compiler = reference / "host/bin/aarch64-linux-gcc"
        for name, source, flag in (
                ("openmp", "int main(void) {int n=0;\n#pragma omp parallel reduction(+:n)\nn+=1;\nreturn n<1;}\n", "-fopenmp"),
                ("dlopen", '#include <dlfcn.h>\nint main(void){return !dlopen("libgomp.so.1",RTLD_NOW);}\n', "-ldl")):
            src = out / f"control-{name}.c"
            src.write_text(source)
            binary = out / f"control-{name}"
            run([compiler, src, flag, "-o", binary])
            dependencies = needed(binary)
            report[f"control_{name}"] = dict(needed=dependencies, literal=b"libgomp" in binary.read_bytes())
            if not report[f"control_{name}"]["literal"] or (
                    any(lib.startswith("libgomp") for lib in dependencies) != (name == "openmp")):
                raise ValueError("consumer control failed")
        version = next((original / "lib/modules").iterdir()).name
        sort = out / "sort.resolved"
        sort.write_text((BOARD / "squashfs-sort.txt").read_text().replace("@KVER@", version))
        for variant in ("before", "before-aa", "after"):
            images = out / variant / "images"
            images.mkdir(parents=True)
            root = images.parent / "root"
            shutil.copytree(original, root, symlinks=True)
            if variant == "after":
                run(["python3", BOARD / "tools/prune-libgomp.py", root])
            measured = COMMON.inventory(root)
            removed = sorted(before.keys() - measured.keys())
            changed = sorted(k for k in before.keys() & measured.keys() if before[k] != measured[k])
            if changed or (variant == "after" and removed != ["usr/lib/libgomp.so.1.0.0"]):
                raise ValueError("unexpected target change")
            report["variants"][variant] = dict(regular_bytes=sum(v[0] for v in measured.values()),
                                               removed=removed, changed=changed)
            ready = root / "etc/init.d/S98msd-ready"
            script = ready.read_text()
            if script.count("done\n") != 1:
                raise ValueError("unexpected ready script")
            ready.write_text(script.replace("done\n", "done\n" +
                "printf 'MODULE_INVENTORY_BEGIN\\n' >/dev/console\ncat /proc/modules >/dev/console\n"
                "printf 'MODULE_INVENTORY_END\\n' >/dev/console\n"))
            sqfs = images / "rootfs.squashfs"
            run([reference / "host/bin/mksquashfs.orig", root, sqfs, "-noappend", "-all-root", "-no-xattrs",
                 "-no-progress", "-comp", "zstd", "-b", "131072", "-Xcompression-level", "22",
                 "-processors", "2", "-mkfs-time", "0", "-all-time", "0", "-sort", sort])
            report["variants"][variant].update(squashfs_bytes=sqfs.stat().st_size,
                                               squashfs_sha256=COMMON.sha(sqfs))
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
        print(json.dumps(report["variants"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.reference.resolve(), args.config.resolve(), args.out.resolve())
