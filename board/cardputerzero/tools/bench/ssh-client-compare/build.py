#!/usr/bin/env python3
"""Build isolated client payloads with the vendor Buildroot recipes."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[5]
VARIANTS = ("openssh", "dropbear", "putty")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, log, **kwargs):
    log.write("$ " + " ".join(map(str, command)) + "\n")
    log.flush()
    return subprocess.run(list(map(str, command)), stdout=log,
                          stderr=subprocess.STDOUT, check=True, **kwargs)


def overrides(variant):
    binary = {"openssh": "ssh", "dropbear": "dropbearmulti",
              "putty": "plink"}[variant]
    destination = {"openssh": "ssh", "dropbear": "dbclient", "putty": "plink"}[variant]
    prefix = variant.upper()
    result = [f"{prefix}_INSTALL_TARGET_CMDS=$(INSTALL) -D -m 0755 $(@D)/{binary} $(TARGET_DIR)/usr/bin/{destination}",
              f"{prefix}_POST_INSTALL_TARGET_HOOKS=", f"{prefix}_INSTALL_INIT_SYSV=",
              f"{prefix}_INSTALL_INIT_SYSTEMD="]
    if variant == "openssh":
        result.append("OPENSSH_MAKE_OPTS=ssh")
    elif variant == "dropbear":
        result.append("DROPBEAR_PROGRAMS=dbclient")
    return result


def needed(path):
    result = subprocess.check_output(["readelf", "-d", path], text=True)
    return re.findall(r"Shared library: \[([^]]+)\]", result)


def payload(variant, output, reference, log, source=None):
    source = source if source is not None else output / "buildroot/target"
    tree = output / "root"
    shutil.copytree(reference / "target", tree, symlinks=True)
    name = {"openssh": "ssh", "dropbear": "dbclient", "putty": "plink"}[variant]
    binary = tree / "usr/bin" / name
    shutil.copyfile(source / "usr/bin" / name, binary)
    binary.chmod(0o755)
    strip = reference / "host/bin/aarch64-linux-strip"
    run([strip, "--strip-unneeded", binary], log)
    queue = [binary]
    dependencies = {}
    while queue:
        path = queue.pop()
        for library in needed(path):
            if library in dependencies:
                continue
            relative = next((Path(directory) / library for directory in ("usr/lib", "lib")
                             if (tree / directory / library).exists()), None)
            if relative is None:
                dependency = next((source / directory / library
                               for directory in ("usr/lib", "lib")
                               if (source / directory / library).exists()), None)
                if dependency is None:
                    raise ValueError(f"missing dependency {library}")
                relative = Path("usr/lib") / library
                shutil.copyfile(dependency.resolve(), tree / relative)
                run([strip, "--strip-unneeded", tree / relative], log)
            dependencies[library] = str(relative)
            queue.append(tree / relative)
    (output / "dependencies.json").write_text(json.dumps(dependencies, indent=2) + "\n")
    additions = []
    for path in sorted(tree.rglob("*")):
        relative = path.relative_to(tree)
        if path.is_file() and not path.is_symlink() and not (reference / "target" / relative).exists():
            additions.append(dict(path=str(relative), bytes=path.stat().st_size, sha256=sha(path)))
    (output / "files.json").write_text(json.dumps(additions, indent=2) + "\n")
    return sum(row["bytes"] for row in additions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", choices=VARIANTS, nargs="+", default=list(VARIANTS))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--measure-from", type=Path,
                        help="reuse immutable prepared payloads; do not rebuild packages")
    args = parser.parse_args()
    if args.repetitions < 1 or len(set(args.variants)) != len(args.variants):
        parser.error("positive repetitions and distinct variants required")
    os.nice(19)
    reference, out = args.reference.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(path.relative_to(ROOT)): sha(path) for path in
              [reference / ".config", reference / "images/Image",
               reference / "images/bcm2710-rpi-cm0.dtb", reference / "images/rootfs.squashfs"]}
    inputs["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    squashfs = reference / "host/bin/mksquashfs.orig"
    if not squashfs.exists():
        squashfs = reference / "host/bin/mksquashfs"
    inputs["mksquashfs_sha256"] = sha(squashfs)
    inputs["script_sha256"] = sha(Path(__file__))
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    with (out / "results.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"])
        for variant in ["baseline", *args.variants]:
            work = out / variant
            work.mkdir()
            with (work / "build.log").open("x") as log:
                start = time.monotonic()
                try:
                    if variant != "baseline":
                        if args.measure_from:
                            source = args.measure_from.resolve() / variant
                            added = payload(variant, work, reference, log, source / "root")
                        else:
                            output = work / "buildroot"
                            command = ["make", "-C", ROOT / "vendor/buildroot", f"O={output}",
                                       f"BR2_EXTERNAL={ROOT}", "BR2_JLEVEL=4", "-j4"]
                            run([*command, "msd_cardputerzero_defconfig"], log)
                            config = output / ".config"
                            text = config.read_text()
                            for symbol in [f"BR2_PACKAGE_{variant.upper()}"]:
                                text = re.sub(rf"(?m)^(?:# )?{symbol}(?:=.*| is not set)$", "", text)
                                text += f"\n{symbol}=y\n"
                            if variant == "openssh":
                                text += "\n# BR2_PACKAGE_OPENSSH_SERVER is not set\n# BR2_PACKAGE_OPENSSH_KEY_UTILS is not set\n"
                            config.write_text(text)
                            run([*command, "olddefconfig"], log)
                            run([*command, *overrides(variant), variant], log)
                            added = payload(variant, work, reference, log)
                        writer.writerow([variant, variant, 1, "installed_added", added,
                                         "byte", 1, "minimal runtime dependency closure; common libraries reused"])
                        tree = work / "root"
                    else:
                        tree = reference / "target"
                    hashes = []
                    for repeat in range(1, args.repetitions + 1):
                        image = work / f"rootfs-{repeat}.squashfs"
                        run([squashfs, tree, image, "-noappend", "-processors", "2",
                             "-b", "128K", "-comp", "zstd", "-Xcompression-level", "22", "-all-root",
                             "-all-time", "0", "-mkfs-time", "0", "-no-xattrs"], log,
                            env={key: value for key, value in os.environ.items() if key != "SOURCE_DATE_EPOCH"})
                        hashes.append(sha(image))
                        writer.writerow([f"{variant}-{repeat}", variant, repeat, "squashfs", image.stat().st_size,
                                         "byte", 1, "sha256=" + hashes[-1]])
                    if len(set(hashes)) != 1:
                        raise ValueError("deterministic A/A squashfs mismatch")
                    writer.writerow([variant, variant, 1, "measure" if args.measure_from else "build", 0, "exit", 1,
                                     f"seconds={time.monotonic() - start:.6f}; not a timing comparison"])
                    print(f"ok - {variant}", flush=True)
                except Exception as error:
                    writer.writerow([variant, variant, 1, "build", 1, "exit", 0, str(error)])
                    raise
                finally:
                    stream.flush()


if __name__ == "__main__":
    main()
