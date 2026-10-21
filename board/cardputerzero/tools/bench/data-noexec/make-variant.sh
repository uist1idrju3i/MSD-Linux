#!/bin/bash
# Usage (inside docker/msd-dev): make-variant.sh VARIANT OUTDIR HOOK [noexec]
# Builds a test-only SD image from an existing Buildroot output. Not shipped.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
variant="$1"; outdir="$2"; hook="$3"; mod="${4:-}"
images="${OUTPUT_DIR}/images"
host="${OUTPUT_DIR}/host"
rm -rf "$outdir"; mkdir -p "$outdir"
"$host/bin/unsquashfs" -no-progress -no-xattrs -d "$outdir/target" "$images/rootfs.squashfs" >"$outdir/unsquashfs.log" 2>&1 || {
	st=$?
	if ((st != 2)) || ! grep -Fq 'failed to change uid and gids' "$outdir/unsquashfs.log"; then
		cat "$outdir/unsquashfs.log"; exit 1
	fi
}
install -m 0755 "$hook" "$outdir/target/etc/init.d/$(basename "$hook")"
if [[ "$mod" == noexec ]]; then
	f="$outdir/target/etc/fstab"; s="$outdir/target/etc/init.d/S02msd-data"
	[[ "$(grep -c '^/dev/mmcblk0p7 /data ext4 noauto,noatime,nodev,nosuid,data=ordered' "$f")" == 1 ]]
	sed -i 's|^\(/dev/mmcblk0p7 /data ext4 noauto,noatime,nodev,nosuid\),|\1,noexec,|' "$f"
	[[ "$(grep -c 'mount -t ext4 -o noatime,nodev,nosuid,data=ordered' "$s")" == 1 ]]
	sed -i 's|mount -t ext4 -o noatime,nodev,nosuid,data=ordered|mount -t ext4 -o noatime,nodev,nosuid,noexec,data=ordered|' "$s"
	[[ "$(grep -c 'nosuid,noexec,data=ordered' "$f" "$s" | awk -F: '{n+=$2} END {print n}')" == 2 ]]
fi
info="$("$host/bin/unsquashfs" -s "$images/rootfs.squashfs")"
comp="$(awk '$1 == "Compression" { print $2; exit }' <<<"$info")"
bs="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$info")"
"$host/bin/mksquashfs" "$outdir/target" "$outdir/rootfs.squashfs" -noappend -all-root -no-xattrs -no-progress -comp "$comp" -b "$bs" >"$outdir/mksquashfs.log" 2>&1
cp --sparse=always "$images/sdcard.img" "$outdir/sdcard.img"
size="$(stat -c %s "$outdir/sdcard.img")"; p=1; while ((p < size)); do p=$((p * 2)); done; truncate -s "$p" "$outdir/sdcard.img"
read -r a_start a_size b_start b_size < <("$host/sbin/sfdisk" --json "$outdir/sdcard.img" | python3 -c '
import json,sys
p=json.load(sys.stdin)["partitiontable"]["partitions"]
assert len(p)==7, len(p)
print(p[4]["start"],p[4]["size"],p[5]["start"],p[5]["size"])')
rb="$(stat -c %s "$outdir/rootfs.squashfs")"
((rb <= a_size * 512 && rb <= b_size * 512))
dd if="$outdir/rootfs.squashfs" of="$outdir/sdcard.img" bs=512 seek="$a_start" conv=notrunc status=none
dd if="$outdir/rootfs.squashfs" of="$outdir/sdcard.img" bs=512 seek="$b_start" conv=notrunc status=none
{
	echo "variant=$variant mod=$mod"
	echo "git_head=$(git -C "$REPO_ROOT" rev-parse HEAD)"
	sha256sum "$images/rootfs.squashfs" "$images/sdcard.img" "$images/Image" "$images/bcm2710-rpi-cm0.dtb" "$hook" "$outdir/rootfs.squashfs"
	grep -n '/data' "$outdir/target/etc/fstab"; grep -n 'mount -t ext4' "$outdir/target/etc/init.d/S02msd-data"
} >"$outdir/variant-info.txt"
rm -rf "$outdir/target"
echo "built $outdir"
