#!/usr/bin/env python3
"""Build isolated OpenSSL target variants and measure a fixed rootfs."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


VARIANTS = {
    "default": [],
    "no-ml-kem": ["no-ml-kem"],
    "no-ml-dsa": ["no-ml-dsa"],
    "no-slh-dsa": ["no-slh-dsa"],
    "all-three": ["no-ml-kem", "no-ml-dsa", "no-slh-dsa"],
}
FILES = ["usr/lib/libcrypto.so.3", "usr/lib/libssl.so.3", "usr/bin/openssl",
         "usr/lib/ossl-modules/legacy.so"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, cwd, log, env=None):
    log.write("$ " + " ".join(map(str, command)) + "\n")
    log.flush()
    subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                   stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    ref = args.reference.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / "source"
    source.mkdir()
    tar = root / "vendor/buildroot/dl/libopenssl/openssl-3.5.9.tar.gz"
    perl = ('print encode_json({config=>\\%configdata::config,'
            'disabled=>\\%configdata::disabled,disablables=>\\@configdata::disablables})')
    config = json.loads(subprocess.check_output(
        ["perl", f"-I{ref}/build/libopenssl-3.5.9", "-Mconfigdata", "-MJSON::PP", "-e", perl]))
    (out / "reference.json").write_text(json.dumps(config, indent=2) + "\n")
    inputs = {"archive_sha256": sha(tar), "reference_config_sha256": sha(ref / ".config"),
              "reference_rootfs_sha256": sha(ref / "images/rootfs.squashfs"),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "patches": {}}
    env = dict(os.environ, SOURCE_DATE_EPOCH="0")
    for key in ["AR", "AS", "CC", "CPP", "CXX", "RANLIB", "CFLAGS", "CPPFLAGS", "LDFLAGS"]:
        value = config["config"][key]
        env[key] = " ".join(value) if isinstance(value, list) else value
    flags = config["config"]["perlargv"]
    with (out / "prepare.log").open("w") as log:
        run(["tar", "xf", tar, "--strip-components=1", "-C", source], root, log)
        for line in (ref / "build/libopenssl-3.5.9/.applied_patches_list").read_text().splitlines():
            patch = root / line.removeprefix("/work/")
            inputs["patches"][str(patch.relative_to(root))] = sha(patch)
            run(["patch", "-p1", "-i", patch], source, log)
    (out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    with (out / "results.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"])
        for variant, extra in VARIANTS.items():
            work = out / variant
            work.mkdir()
            build = work / "build"
            build.mkdir()
            stage = work / "stage"
            with (work / "build.log").open("w") as log:
                try:
                    run(["perl", source / "Configure", *flags, *extra], build, log, env)
                    run(["make", "-j8", "build_sw"], build, log, env)
                    run(["make", f"DESTDIR={stage}", "install_sw"], build, log, env)
                    state = json.loads(subprocess.check_output(
                        ["perl", f"-I{build}", "-Mconfigdata", "-MJSON::PP", "-e", perl], cwd=build))
                    for option in extra:
                        if state["disabled"].get(option.removeprefix("no-")) != "option":
                            raise ValueError(f"option did not take effect: {option}")
                    if any(x in state["disabled"] for x in ["asm", "ec", "ecx", "cms", "apps"]):
                        raise ValueError("required feature disabled")
                    (work / "configdata.json").write_text(json.dumps(state, indent=2) + "\n")
                    tree = work / "root"
                    shutil.copytree(ref / "target", tree, symlinks=True)
                    for name in FILES:
                        target = tree / name
                        shutil.copyfile(stage / name, target)
                        run([ref / "host/bin/aarch64-linux-strip", "--strip-unneeded", target], root, log)
                        writer.writerow([variant, variant, 1, name, target.stat().st_size,
                                         "byte", 1, "sha256=" + sha(target)])
                    for repeat in ([1, 2] if variant == "default" else [1]):
                        image = work / f"rootfs-{repeat}.squashfs"
                        run([ref / "host/bin/mksquashfs", tree, image, "-noappend", "-processors", "2",
                             "-b", "128K", "-comp", "zstd", "-Xcompression-level", "22",
                             "-all-root", "-all-time", "0", "-mkfs-time", "0", "-no-xattrs"],
                            root, log, {k: v for k, v in env.items() if k != "SOURCE_DATE_EPOCH"})
                        writer.writerow([f"{variant}-{repeat}", variant, repeat, "rootfs.squashfs",
                                         image.stat().st_size, "byte", 1, "sha256=" + sha(image)])
                    if variant == "default" and sha(work / "rootfs-1.squashfs") != sha(work / "rootfs-2.squashfs"):
                        raise ValueError("A/A squashfs mismatch")
                    stream.flush()
                    print(f"ok - {variant}", flush=True)
                except Exception as error:
                    writer.writerow([variant, variant, 1, "build", 1, "exit", 0, str(error)])
                    stream.flush()
                    raise


if __name__ == "__main__":
    main()
