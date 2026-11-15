#!/bin/bash
set -euo pipefail

# B2: SquashFS compression option 別の read 性能 case を生成する。
# rootfs を rebuild（codec/block/level 変更）して sdcard.img の p5 に書き、
# init で全 file の読み出し（decompress 経路）を強制する readall script を入れる。
# verity は掛けない（純粋な read 性能のみ。整合性込みの影響は B7 で見る）。
#
# Usage: make-case.sh VARIANT OUTPUT_DIR BASE_DIR CASE_DIR -- <mksquashfs args...>
#   VARIANT: S- 始まりの名前（例: S-zstd-1M-l19）
#   <mksquashfs args>: -comp/-b/-Xcompression-level/-Xbcj など
#
# BASE_DIR には V0/（rootfs.squashfs, images/{sdcard.img,bcm2710-rpi-cm0.dtb}）と
# T0/images/Image が必要。

if (($# < 6)); then
	printf 'Usage: %s VARIANT OUTPUT_DIR BASE_DIR CASE_DIR -- <mksquashfs args...>\n' "$0" >&2
	exit 2
fi

case_name="$1"
output_dir="$2"
base_dir="$3"
case_dir="$4"
shift 4
if [[ "$1" != -- ]]; then
	printf 'expected -- before mksquashfs args\n' >&2
	exit 2
fi
shift
mkfs_args=("$@")
experiment_head="${EXPERIMENT_HEAD:-$(git -C "$(cd -- "$(dirname -- "$0")" && pwd)/../../../.." rev-parse HEAD 2>/dev/null || printf 'unknown')}"
if [[ ! "$case_name" =~ ^S-[a-z0-9-]+$ ]]; then
	printf 'unsupported case name: %s\n' "$case_name" >&2
	exit 2
fi
host="${output_dir}/host"
v0="${base_dir}/V0"
remount_line='::sysinit:/bin/mount -o remount,rw /'
readall_line='::sysinit:/usr/sbin/msd-readall'

[[ ! -e "$case_dir" ]] || {
	printf 'Refusing to overwrite %s\n' "$case_dir" >&2
	exit 1
}
mkdir -p "$case_dir/images"
tree="${case_dir}/rootfs-tree"

"$host/bin/unsquashfs" -no-progress -no-xattrs \
	-d "$tree" "${v0}/rootfs.squashfs" >"${case_dir}/unsquashfs.log" 2>&1 || {
	status=$?
	if ((status != 2)) ||
		! grep -Fq 'failed to change uid and gids' "${case_dir}/unsquashfs.log"; then
		cat "${case_dir}/unsquashfs.log" >&2
		exit "$status"
	fi
}

inittab="${tree}/etc/inittab"
before_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
[[ "$before_count" == 0 || "$before_count" == 1 ]]
sed -i "\|^::sysinit:/bin/mount -o remount,rw /\$|d" "$inittab"
after_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
[[ "$after_count" == 0 ]]

# 全 file を読んで decompress させる readall script（rcS の前に実行）。
# 計測: readall 中の MemAvailable 最小値と、drop_caches 後の MemAvailable を
# /dev/kmsg に出す（zstd level 等の decompress 側メモリ比較用）。
cat >"${tree}/usr/sbin/msd-readall" <<'EOF'
#!/bin/sh
# 全 file の内容を読ませて SquashFS の decompress 経路を確実に通す。
min_file=/dev/.readall-min-avail
printf 'squashfs-readall-begin\n' >/dev/kmsg
(
	min_avail=
	while :; do
		v="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
		if [ -n "$v" ] && { [ -z "$min_avail" ] || [ "$v" -lt "$min_avail" ]; }; then
			min_avail="$v"
			printf '%s\n' "$min_avail" >"$min_file"
		fi
		sleep 0.5
	done
) &
sampler=$!
find / -xdev -type f -exec cat {} + >/dev/null 2>&1
kill "$sampler" 2>/dev/null
wait "$sampler" 2>/dev/null
min_avail="$(cat "$min_file" 2>/dev/null)"
rm -f "$min_file"
sync
echo 3 >/proc/sys/vm/drop_caches 2>/dev/null
post_avail="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
printf 'squashfs-readall-mem min_avail_kb=%s post_drop_avail_kb=%s\n' \
	"$min_avail" "$post_avail" >/dev/kmsg
printf 'squashfs-readall-complete\n' >/dev/kmsg
EOF
chmod 755 "${tree}/usr/sbin/msd-readall"
if grep -q '^::sysinit:/etc/init.d/rcS' "$inittab"; then
	awk -v line="$readall_line" '
		!done && /^::sysinit:\/etc\/init.d\/rcS/ { print line; done = 1 }
		{ print }
	' "$inittab" >"${inittab}.new" && mv "${inittab}.new" "$inittab"
else
	printf '%s\n' "$readall_line" >>"$inittab"
fi
grep -Fxc -- "$readall_line" "$inittab" >"${case_dir}/inittab-readall-count.txt" || true
[[ "$(<"${case_dir}/inittab-readall-count.txt")" == 1 ]]
printf 'remount_before=%s\nremount_after=%s\n' \
	"$before_count" "$after_count" >>"${case_dir}/inittab-readall-count.txt"

"$host/bin/mksquashfs" "$tree" "${case_dir}/rootfs.squashfs" \
	-noappend -all-root -no-xattrs -no-progress \
	"${mkfs_args[@]}" >"${case_dir}/mksquashfs.log" 2>&1

cp --sparse=always "${v0}/images/sdcard.img" "${case_dir}/images/sdcard.img"
cp "${base_dir}/T0/images/Image" "${case_dir}/images/Image"
cp "${v0}/images/bcm2710-rpi-cm0.dtb" \
	"${case_dir}/images/bcm2710-rpi-cm0.dtb"

read -r root_a_start root_a_size < <(
	"$host/sbin/sfdisk" --json "${case_dir}/images/sdcard.img" |
	python3 -c 'import json,sys; p=json.load(sys.stdin)["partitiontable"]["partitions"]; print(p[4]["start"],p[4]["size"])'
)
rootfs_size="$(stat -c %s "${case_dir}/rootfs.squashfs")"
((rootfs_size <= root_a_size * 512))
dd if="${case_dir}/rootfs.squashfs" of="${case_dir}/images/sdcard.img" \
	bs=512 seek="$root_a_start" conv=notrunc status=none
dd if="${case_dir}/images/sdcard.img" iflag=skip_bytes,count_bytes \
	skip="$((root_a_start * 512))" count="$rootfs_size" status=none |
	cmp - "${case_dir}/rootfs.squashfs"

printf 'initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1\n' \
	>"${case_dir}/qemu-extra-append.txt"

{
	printf 'variant=%s\nexperiment_head=%s\n' "$case_name" "$experiment_head"
	printf 'mksquashfs_args=%s\n' "${mkfs_args[*]}"
	printf 'rootfs_size=%s\nrootfs_a_start_sector=%s\nrootfs_a_size_sectors=%s\n' \
		"$rootfs_size" "$root_a_start" "$root_a_size"
	printf 'cmdline_root=/dev/mmcblk0p5\n'
	sha256sum "${case_dir}/rootfs.squashfs" "${case_dir}/images/sdcard.img" \
		"${case_dir}/images/Image" "${case_dir}/images/bcm2710-rpi-cm0.dtb"
	printf 'A_slot_rootfs_bytes_match=1\n'
} >"${case_dir}/variant-info.txt"
