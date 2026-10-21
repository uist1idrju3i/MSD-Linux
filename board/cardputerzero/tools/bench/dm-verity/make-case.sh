#!/bin/bash
set -euo pipefail

if (($# != 4)); then
	printf 'Usage: %s T0-A2|T1-A2|T2-A2|T3-A2|T4-A2|T5-A2 OUTPUT_DIR BASE_DIR CASE_DIR\n' "$0" >&2
	exit 2
fi

case_name="$1"
output_dir="$2"
base_dir="$3"
case_dir="$4"
experiment_head="${EXPERIMENT_HEAD:-ce932cd0e83ebf10be853c51d9ae09116aea92bb}"
if [[ ! "$case_name" =~ ^T[0-5]-A2$ ]]; then
	printf 'unsupported case: %s\n' "$case_name" >&2
	exit 2
fi
case_kind="${case_name%-A2}"
host="${output_dir}/host"
v0="${base_dir}/V0"
t0="${base_dir}/T0-A2"

[[ ! -e "$case_dir" ]] || {
	printf 'Refusing to overwrite %s\n' "$case_dir" >&2
	exit 1
}
mkdir -p "$case_dir/images"

if [[ "$case_kind" == T0 ]]; then
	rootfs="${case_dir}/rootfs.img"
	rootfs_tree="${case_dir}/rootfs-tree"
	"$host/bin/unsquashfs" -no-progress -no-xattrs \
		-d "$rootfs_tree" "${v0}/rootfs.squashfs" \
		>"${case_dir}/unsquashfs.log" 2>&1 || {
		status=$?
		if ((status != 2)) ||
			! grep -Fq 'failed to change uid and gids' "${case_dir}/unsquashfs.log"; then
			cat "${case_dir}/unsquashfs.log" >&2
			exit "$status"
		fi
	}
	inittab="${rootfs_tree}/etc/inittab"
	remount_line='::sysinit:/bin/mount -o remount,rw /'
	before_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
	[[ "$before_count" == 1 ]]
	sed -i '\|^::sysinit:/bin/mount -o remount,rw /$|d' "$inittab"
	after_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
	[[ "$after_count" == 0 ]]
	printf 'line=%s\nbefore_count=%s\nafter_count=%s\n' \
		"$remount_line" "$before_count" "$after_count" \
		>"${case_dir}/inittab-remount-check.txt"
	info="$("$host/bin/unsquashfs" -s "${v0}/rootfs.squashfs")"
	compression="$(awk '$1 == "Compression" {print $2; exit}' <<<"$info")"
	block_size="$(awk '$1 == "Block" && $2 == "size" {print $3; exit}' <<<"$info")"
	"$host/bin/mksquashfs" "$rootfs_tree" "${case_dir}/rootfs.squashfs" \
		-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
		-b "$block_size" >"${case_dir}/mksquashfs.log" 2>&1
	cp --sparse=always "${case_dir}/rootfs.squashfs" "$rootfs"
	rootfs_bytes="$(stat -c %s "$rootfs")"
	data_bytes=$(((rootfs_bytes + 4095) / 4096 * 4096))
	truncate -s "$data_bytes" "$rootfs"
	"$host/sbin/veritysetup" format --data-block-size=4096 \
		--hash-block-size=4096 --hash-offset="$data_bytes" "$rootfs" "$rootfs" \
		>"${case_dir}/format.log" 2>&1
	root_hash="$(awk -F: 'tolower($1) == "root hash" {sub(/^[[:space:]]*/, "", $2); print $2; exit}' "${case_dir}/format.log")"
	salt="$(awk -F: 'tolower($1) == "salt" {sub(/^[[:space:]]*/, "", $2); print $2; exit}' "${case_dir}/format.log")"
	data_blocks="$((data_bytes / 4096))"
	hash_start_block="$((data_blocks + 1))"
	[[ -n "$root_hash" && -n "$salt" ]]
	"$host/sbin/veritysetup" dump --hash-offset="$data_bytes" "$rootfs" \
		>"${case_dir}/dump.log" 2>&1
	printf 'data_bytes=%s\nrootfs_bytes=%s\ndata_blocks=%s\nhash_offset=%s\nhash_start_block=%s\nroot_hash=%s\nsalt=%s\n' \
		"$data_bytes" "$rootfs_bytes" "$data_blocks" "$data_bytes" \
		"$hash_start_block" "$root_hash" "$salt" \
		>"${case_dir}/verity-parameters.env"
	cp --sparse=always "${v0}/images/sdcard.img" "${case_dir}/images/sdcard.img"
	cp "${base_dir}/T0/images/Image" "${case_dir}/images/Image"
	cp "${v0}/images/bcm2710-rpi-cm0.dtb" \
		"${case_dir}/images/bcm2710-rpi-cm0.dtb"
else
	[[ -f "${t0}/verity-parameters.env" && -f "${t0}/rootfs.img" ]]
	# shellcheck disable=SC1091
	source "${t0}/verity-parameters.env"
	cp "${t0}/rootfs.img" "${case_dir}/rootfs.img"
	cp --sparse=always "${t0}/images/sdcard.img" "${case_dir}/images/sdcard.img"
	cp "${t0}/images/Image" "${case_dir}/images/Image"
	cp "${t0}/images/bcm2710-rpi-cm0.dtb" \
		"${case_dir}/images/bcm2710-rpi-cm0.dtb"
fi

case_root_hash="$root_hash"
offset=none
case "$case_kind" in
	T1) offset=96 ;;
	T2)
		offset="$(python3 - "${case_dir}/rootfs.img" <<'PY'
import pathlib
import struct
import sys

with pathlib.Path(sys.argv[1]).open("rb") as image:
    image.seek(64)
    print(struct.unpack("<Q", image.read(8))[0] + 16)
PY
)"
		;;
	T3) offset="$((4096 * (data_blocks / 2) + 123))" ;;
	T4) offset="$((hash_start_block * 4096))" ;;
	T5)
		if [[ "${root_hash: -1}" == 0 ]]; then
			case_root_hash="${root_hash%?}1"
		else
			case_root_hash="${root_hash%?}0"
		fi
		;;
esac

if [[ "$offset" != none ]]; then
	python3 - "${case_dir}/rootfs.img" "$offset" \
		"${case_dir}/tamper-details.txt" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
offset = int(sys.argv[2])
data = bytearray(path.read_bytes())
if offset < 0 or offset >= len(data):
    raise SystemExit(f"offset out of range: {offset} / {len(data)}")
before = data[offset]
data[offset] ^= 0x01
path.write_bytes(data)
pathlib.Path(sys.argv[3]).write_text(
    f"offset={offset}\nbefore=0x{before:02x}\nafter=0x{data[offset]:02x}\n",
    encoding="ascii",
)
PY
else
	printf 'root_hash_before=%s\nroot_hash_after=%s\n' "$root_hash" \
		"$case_root_hash" >"${case_dir}/tamper-details.txt"
fi

read -r root_a_start root_a_size < <(
	"$host/sbin/sfdisk" --json "${case_dir}/images/sdcard.img" |
	python3 -c 'import json,sys; p=json.load(sys.stdin)["partitiontable"]["partitions"]; print(p[4]["start"],p[4]["size"])'
)
rootfs_size="$(stat -c %s "${case_dir}/rootfs.img")"
((rootfs_size <= root_a_size * 512))
dd if="${case_dir}/rootfs.img" of="${case_dir}/images/sdcard.img" \
	bs=512 seek="$root_a_start" conv=notrunc status=none
dd if="${case_dir}/images/sdcard.img" iflag=skip_bytes,count_bytes \
	skip="$((root_a_start * 512))" count="$rootfs_size" status=none |
	cmp - "${case_dir}/rootfs.img"

data_sectors="$((data_blocks * 8))"
dm_table="vroot,,,ro,0 ${data_sectors} verity 1 /dev/mmcblk0p5 /dev/mmcblk0p5 4096 4096 ${data_blocks} ${hash_start_block} sha256 ${case_root_hash} ${salt} 1 panic_on_corruption"
printf 'dm-mod.waitfor=/dev/mmcblk0p5 dm-mod.create="%s" initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1 trace_event=sched:sched_process_exec trace_buf_size=4M\n' \
	"$dm_table" >"${case_dir}/qemu-extra-append.txt"

{
	printf 'variant=%s\nexperiment_head=%s\n' "$case_name" "$experiment_head"
	printf 'rootfs_size=%s\nrootfs_a_start_sector=%s\nrootfs_a_size_sectors=%s\n' \
		"$rootfs_size" "$root_a_start" "$root_a_size"
	printf 'data_blocks=%s\nhash_offset=%s\nhash_start_block=%s\ndata_sectors=%s\n' \
		"$data_blocks" "$data_bytes" "$hash_start_block" "$data_sectors"
	printf 'root_hash=%s\nsalt=%s\ncmdline_root=/dev/dm-0\n' \
		"$case_root_hash" "$salt"
	sha256sum "${case_dir}/rootfs.img" "${case_dir}/images/sdcard.img" \
		"${case_dir}/images/Image" "${case_dir}/images/bcm2710-rpi-cm0.dtb"
	printf 'A_slot_rootfs_bytes_match=1\n'
} >"${case_dir}/variant-info.txt"
