#!/bin/bash
set -euo pipefail

if (($# != 4)); then
	printf 'Usage: %s OUTPUT_DIR BUSYBOX_LINKS HOOK VARIANT_DIR\n' "$0" >&2
	exit 2
fi

output_dir="$1"
links_file="$2"
hook="$3"
variant_dir="$4"
experiment_head="${EXPERIMENT_HEAD:-ce932cd0e83ebf10be853c51d9ae09116aea92bb}"
host="${output_dir}/host"
images="${output_dir}/images"
target="${variant_dir}/target"
stale_file="${variant_dir}/stale-symlinks.tsv"
resolution_file="${variant_dir}/link-resolution.tsv"

[[ ! -e "$variant_dir" ]] || {
	printf 'Refusing to overwrite %s\n' "$variant_dir" >&2
	exit 1
}
mkdir -p "$target"
"$host/bin/unsquashfs" -no-progress -no-xattrs -d "$target" \
	"$images/rootfs.squashfs" >"${variant_dir}.unsquashfs.log" 2>&1 || {
	status=$?
	if ((status != 2)) ||
		! grep -Fq 'failed to change uid and gids' "${variant_dir}.unsquashfs.log"; then
		cat "${variant_dir}.unsquashfs.log" >&2
		exit "$status"
	fi
}

python3 - "$target" "$links_file" "$stale_file" "$resolution_file" <<'PY'
import os
import sys
from pathlib import Path

root, links_file, stale_file, resolution_file = map(Path, sys.argv[1:])
expected = {
    line.strip().lstrip("/")
    for line in links_file.read_text().splitlines()
    if line.strip()
}

def busybox_link(path):
    target = os.readlink(path)
    if target.startswith("/"):
        resolved = os.path.normpath(target.lstrip("/"))
    else:
        resolved = os.path.normpath(
            os.path.join(path.parent.relative_to(root).as_posix(), target)
        )
    return resolved == "bin/busybox", target

actual = {}
for directory, dirnames, filenames in os.walk(root, followlinks=False):
    for name in dirnames + filenames:
        path = Path(directory) / name
        if path.is_symlink():
            is_busybox, target = busybox_link(path)
            if is_busybox:
                actual[path.relative_to(root).as_posix()] = target

stale = sorted(set(actual) - expected)
missing = sorted(
    rel for rel in expected - set(actual)
    if not (root / rel).is_file()
)
if missing:
    raise SystemExit(f"expected applet paths missing before cleanup: {missing}")

stale_file.write_text(
    "path\tsymlink_target\n" +
    "".join(f"/{rel}\t{actual[rel]}\n" for rel in stale)
)
for rel in stale:
    (root / rel).unlink()

rows = []
effective = set()
for rel in sorted(expected):
    path = root / rel
    if path.is_symlink():
        is_busybox, target = busybox_link(path)
        if not is_busybox:
            raise SystemExit(f"expected applet path is another symlink: /{rel} -> {target}")
        kind, detail = "busybox-symlink", target
    elif path.is_file():
        kind, detail = "regular-file", ""
    else:
        raise SystemExit(f"expected applet path missing after cleanup: /{rel}")
    rows.append(f"/{rel}\t{kind}\t{detail}\n")
    effective.add(rel)

remaining = {
    rel for rel in actual
    if rel not in expected and (root / rel).is_symlink()
}
if remaining or effective != expected:
    raise SystemExit(f"link set mismatch: stale={sorted(remaining)}")
resolution_file.write_text("path\tkind\tdetail\n" + "".join(rows))
print(f"removed stale BusyBox symlinks={len(stale)}; links match={effective == expected}")
PY

install -D -m 0755 "$hook" "$target/etc/init.d/$(basename "$hook")"
info="$("$host/bin/unsquashfs" -s "$images/rootfs.squashfs")"
compression="$(awk '$1 == "Compression" {print $2; exit}' <<<"$info")"
block_size="$(awk '$1 == "Block" && $2 == "size" {print $3; exit}' <<<"$info")"
"$host/bin/mksquashfs" "$target" "$variant_dir/rootfs.squashfs" \
	-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
	-b "$block_size" >"${variant_dir}.mksquashfs.log" 2>&1

cp --sparse=always "$images/sdcard.img" "$variant_dir/sdcard.img"
image_bytes="$(stat -c %s "$variant_dir/sdcard.img")"
padded_bytes=1
while ((padded_bytes < image_bytes)); do padded_bytes=$((padded_bytes * 2)); done
truncate -s "$padded_bytes" "$variant_dir/sdcard.img"
read -r root_a root_a_sectors root_b root_b_sectors < <(
	"$host/sbin/sfdisk" --json "$variant_dir/sdcard.img" |
	python3 -c 'import json,sys; p=json.load(sys.stdin)["partitiontable"]["partitions"]; assert len(p)==7; print(p[4]["start"],p[4]["size"],p[5]["start"],p[5]["size"])'
)
rootfs_bytes="$(stat -c %s "$variant_dir/rootfs.squashfs")"
((rootfs_bytes <= root_a_sectors * 512 && rootfs_bytes <= root_b_sectors * 512))
dd if="$variant_dir/rootfs.squashfs" of="$variant_dir/sdcard.img" \
	bs=512 seek="$root_a" conv=notrunc status=none
dd if="$variant_dir/rootfs.squashfs" of="$variant_dir/sdcard.img" \
	bs=512 seek="$root_b" conv=notrunc status=none

printf 'variant=B2\nexperiment_head=%s\n' "$experiment_head" >"$variant_dir/variant-info.txt"
sha256sum "$images/rootfs.squashfs" "$images/sdcard.img" \
	"$images/Image" "$images/bcm2710-rpi-cm0.dtb" \
	"$hook" "$variant_dir/rootfs.squashfs" "$variant_dir/sdcard.img" \
	>>"$variant_dir/variant-info.txt"
rm -rf "$target"
