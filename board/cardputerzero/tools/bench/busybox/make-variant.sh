#!/bin/bash
set -euo pipefail

if (($# != 4)); then
	printf 'Usage: %s NAME OUTPUT_DIR HOOK VARIANT_DIR\n' "$0" >&2
	exit 2
fi

name="$1"
output_dir="$2"
hook="$3"
variant_dir="$4"
experiment_head="${EXPERIMENT_HEAD:-ce932cd0e83ebf10be853c51d9ae09116aea92bb}"
host="${output_dir}/host"
images="${output_dir}/images"
target="${variant_dir}/target"

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

install -D -m 0755 "$hook" "$target/etc/init.d/$(basename "$hook")"
info="$("$host/bin/unsquashfs" -s "$images/rootfs.squashfs")"
compression="$(awk '$1 == "Compression" {print $2; exit}' <<<"$info")"
block_size="$(awk '$1 == "Block" && $2 == "size" {print $3; exit}' <<<"$info")"
"$host/bin/mksquashfs" "$target" "$variant_dir/rootfs.squashfs" \
	-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
	-b "$block_size" >"$variant_dir.mksquashfs.log" 2>&1

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

{
	printf 'variant=%s\n' "$name"
	printf 'experiment_head=%s\n' "$experiment_head"
	sha256sum "$images/rootfs.squashfs" "$images/sdcard.img" \
		"$images/Image" "$images/bcm2710-rpi-cm0.dtb" \
		"$hook" "$variant_dir/rootfs.squashfs" "$variant_dir/sdcard.img"
} >"$variant_dir/variant-info.txt"
rm -rf "$target"
