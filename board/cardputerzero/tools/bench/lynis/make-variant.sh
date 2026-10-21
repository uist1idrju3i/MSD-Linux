#!/bin/bash
# Usage (inside docker/msd-dev): make-variant.sh OUTDIR LYNIS_SRC_DIR
# Builds a test-only SD image with Lynis installed like Buildroot's
# LYNIS_INSTALL_TARGET_CMDS. BusyBox and the rest of the rootfs are unchanged.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
outdir="$1"; src="$2"
images="${OUTPUT_DIR}/images"
host="${OUTPUT_DIR}/host"
rm -rf "$outdir"; mkdir -p "$outdir"
"$host/bin/unsquashfs" -no-progress -no-xattrs -d "$outdir/target" "$images/rootfs.squashfs" >"$outdir/unsquashfs.log" 2>&1 || {
	st=$?
	if ((st != 2)) || ! grep -Fq 'failed to change uid and gids' "$outdir/unsquashfs.log"; then
		cat "$outdir/unsquashfs.log"; exit 1
	fi
}
t="$outdir/target"
install -m 0755 "$SCRIPT_DIR/S99zz-lynis-audit" "$t/etc/init.d/S99zz-lynis-audit"
install -m 0755 "$src/lynis" "$t/usr/sbin/lynis"
install -D -m 0644 "$src/default.prf" "$t/etc/lynis/default.prf"
install -D -m 0644 "$src/developer.prf" "$t/etc/lynis/developer.prf"
install -D -m 0644 "$src"/plugins/* -t "$t/etc/lynis/plugins"
install -D -m 0644 "$src"/include/* -t "$t/usr/share/lynis/include"
install -D -m 0644 "$src"/db/*.db -t "$t/usr/share/lynis/db"
install -D -m 0644 "$src/db/languages/en" -t "$t/usr/share/lynis/db/languages"
info="$("$host/bin/unsquashfs" -s "$images/rootfs.squashfs")"
comp="$(awk '$1 == "Compression" { print $2; exit }' <<<"$info")"
bs="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$info")"
"$host/bin/mksquashfs" "$t" "$outdir/rootfs.squashfs" -noappend -all-root -no-xattrs -no-progress -comp "$comp" -b "$bs" >"$outdir/mksquashfs.log" 2>&1
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
	echo "git_head=$(git -C "$REPO_ROOT" rev-parse HEAD)"
	sha256sum "$images/rootfs.squashfs" "$images/sdcard.img" "$images/Image" "$SCRIPT_DIR/S99zz-lynis-audit" "$outdir/rootfs.squashfs"
} >"$outdir/variant-info.txt"
rm -rf "$t"
echo "built $outdir"
