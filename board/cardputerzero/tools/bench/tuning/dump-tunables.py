#!/usr/bin/env python3
"""Dump every tunable (sysctl, block queue, cpufreq/cpuidle, sysfs mm/power,
module parameters, Kconfig) of a built image as it is after a normal QEMU boot.

The serial console of `qemu -M raspi3b` does not accept input here, so the
script copies the image, repacks the chosen rootfs slot with one extra init
script (S99zz-msd-tunables-dump) that runs guest-dump.sh on /dev/console, and
boots that copy. The original image is not modified. The dump is read-only in
the guest: it never writes to /proc/sys or /sys.
"""
import argparse, csv, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
BEGIN, END = "MSD_TUNABLES_BEGIN", "MSD_TUNABLES_END"
KINDS = {"SYSCTL", "BLOCK", "CPU", "SYSFS", "MODPARAM", "PROC", "ULIMIT", "MODULES", "KCONFIG"}
HOOK = f"""#!/bin/sh
[ "$1" = start ] || exit 0
{{
	echo {BEGIN}
	sh /usr/libexec/msd-bench/guest-dump.sh
	echo {END}
}} > /dev/console 2>&1
"""


def partition(image: Path, index: int) -> tuple[int, int]:
    out = subprocess.run(["sfdisk", "-J", str(image)], check=True, capture_output=True, text=True).stdout
    import json
    parts = json.loads(out)["partitiontable"]["partitions"]
    p = next(p for p in parts if p["node"].endswith(str(index)))
    return p["start"] * 512, p["size"] * 512


def inject(src: Path, dst: Path, index: int, work: Path) -> None:
    shutil.copyfile(src, dst)
    offset, size = partition(dst, index)
    raw = work / "rootfs.squashfs"
    with open(dst, "rb") as fh, open(raw, "wb") as out:
        fh.seek(offset)
        out.write(fh.read(size))
    tree = work / "tree"
    subprocess.run(["unsquashfs", "-no-xattrs", "-d", str(tree), str(raw)], check=False,
                   stdout=subprocess.DEVNULL)
    (tree / "usr/libexec/msd-bench").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "guest-dump.sh", tree / "usr/libexec/msd-bench/guest-dump.sh")
    hook = tree / "etc/init.d/S99zz-msd-tunables-dump"
    hook.write_text(HOOK)
    hook.chmod(0o755)
    new = work / "new.squashfs"
    subprocess.run(["mksquashfs", str(tree), str(new), "-comp", "zstd", "-all-root",
                    "-noappend", "-no-xattrs", "-quiet"], check=True)
    if new.stat().st_size > size:
        raise SystemExit("repacked rootfs does not fit the partition")
    with open(dst, "r+b") as fh, open(new, "rb") as inp:
        fh.seek(offset)
        fh.write(inp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=os.environ.get("OUTPUT_DIR", str(REPO / "output")))
    ap.add_argument("--slot", type=int, choices=(5, 6), default=5)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    images = Path(a.output_dir) / "images"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        image = work / "sdcard.img"
        inject(images / "sdcard.img", image, a.slot, work)
        env = dict(os.environ, OUTPUT_DIR=a.output_dir, ROOT_DEVICE=f"/dev/mmcblk0p{a.slot}")
        with open(a.log, "wb") as log:
            proc = subprocess.Popen([str(REPO / "board/cardputerzero/qemu/run-qemu.sh"), str(image)],
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env)
            deadline = time.monotonic() + a.timeout
            try:
                while time.monotonic() < deadline and proc.poll() is None:
                    time.sleep(2)
                    if END.encode() in Path(a.log).read_bytes():
                        break
            finally:
                proc.kill()
                proc.wait()
    text = Path(a.log).read_bytes().decode("utf-8", "replace")
    if BEGIN not in text or END not in text:
        print("dump markers missing", file=sys.stderr)
        return 1
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    rows = []
    for raw in body.splitlines():
        parts = raw.rstrip("\r").split("|", 3)
        if len(parts) == 4 and parts[0] in KINDS:
            rows.append(parts)
    with open(a.csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "path", "mode", "value"])
        w.writerows(rows)
    print(f"{len(rows)} rows -> {a.csv}", file=sys.stderr)
    return 0 if any(r[0] == "SYSCTL" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
