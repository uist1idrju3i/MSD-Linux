#!/bin/bash
set -euo pipefail

# dm-verity(crc32c)+FEC の破損注入 case を生成する。
# board/cardputerzero/tools/bench/dm-verity/make-case.sh の F 系列版。
# 違い: hash は crc32c、verityfmt で superblock+hash tree+FEC を生成し、
# init で /dev/dm-0 を全読みさせて全 block の検証を強制する。
#
# case:
#   F0-A2  FEC roots=8、破損なし -> ready 期待
#   F1-A2  data 1 byte 破損 -> FEC が訂正 -> ready 期待
#   F2-A2  同一 round の 9 block（roots+1）を同じ byte 位置で破損 -> 訂正不能 -> verity error
#   F3-A2  hash area 1 byte 破損 -> FEC が訂正 -> ready 期待
#   F4-A2  root_hash を 1 桁だけ改ざん -> verity error
#   F5-A2  FEC なし + data 1 byte 破損 -> verity error（F1 の対照）
#   F6-A2  FEC roots=8 + restart_on_corruption + 訂正不能破損 -> verity error
#          （QEMU に tryboot firmware が無いので再起動路しか見えない。A/B 切戻しは実機依存）

if (($# != 4)); then
	printf 'Usage: %s F0-A2|F1-A2|F2-A2|F3-A2|F4-A2|F5-A2|F6-A2 OUTPUT_DIR BASE_DIR CASE_DIR\n' "$0" >&2
	exit 2
fi

case_name="$1"
output_dir="$2"
base_dir="$3"
case_dir="$4"
experiment_head="${EXPERIMENT_HEAD:-$(git -C "$(cd -- "$(dirname -- "$0")" && pwd)/../../../.." rev-parse HEAD 2>/dev/null || printf 'unknown')}"
if [[ ! "$case_name" =~ ^F[0-6]-A2$ ]]; then
	printf 'unsupported case: %s\n' "$case_name" >&2
	exit 2
fi
case_kind="${case_name%-A2}"
host="${output_dir}/host"
v0="${base_dir}/V0"
f0="${base_dir}/F0-A2"
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd)"
verityfmt_src="${repo_root}/board/cardputerzero/tools/dm-verity/verityfmt.c"
fec_roots=8
# 固定 salt（32 byte、反復で image を決定的にするため）
salt_hex="000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
# dm-0 の全 block を読ませる inittab 行（検証の強制）
readall_line='::sysinit:/bin/dd if=/dev/dm-0 of=/dev/null bs=1048576 && /bin/echo verity-readall-complete > /dev/kmsg'
remount_line='::sysinit:/bin/mount -o remount,rw /'

[[ ! -e "$case_dir" ]] || {
	printf 'Refusing to overwrite %s\n' "$case_dir" >&2
	exit 1
}
mkdir -p "$case_dir/images"

# verityfmt を一度だけ build（base_dir 配下で共有）
verityfmt_bin="${base_dir}/verityfmt-bin/verityfmt"
if [[ ! -x "$verityfmt_bin" ]]; then
	mkdir -p "${base_dir}/verityfmt-bin"
	cc -O2 -Wall -Wextra -o "$verityfmt_bin" "$verityfmt_src"
fi

build_squashfs_with_readall() {
	# $1 = source squashfs, $2 = dest squashfs, $3 = work dir
	local src="$1" dst="$2" work="$3"
	local tree="${work}/rootfs-tree"
	"$host/bin/unsquashfs" -no-progress -no-xattrs \
		-d "$tree" "$src" >"${work}/unsquashfs.log" 2>&1 || {
		status=$?
		if ((status != 2)) ||
			! grep -Fq 'failed to change uid and gids' "${work}/unsquashfs.log"; then
			cat "${work}/unsquashfs.log" >&2
			exit "$status"
		fi
	}
	local inittab="${tree}/etc/inittab"
	local before_count after_count
	before_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
	[[ "$before_count" == 0 || "$before_count" == 1 ]]
	sed -i "\|^::sysinit:/bin/mount -o remount,rw /\$|d" "$inittab"
	after_count="$(grep -Fxc -- "$remount_line" "$inittab" || true)"
	[[ "$after_count" == 0 ]]
	# rcS 実行の sysinit 行の直前に全読み行を挿入する（順序が重要）
	if grep -q '^::sysinit:/etc/init.d/rcS' "$inittab"; then
		awk -v line="$readall_line" '
			!done && /^::sysinit:\/etc\/init.d\/rcS/ { print line; done = 1 }
			{ print }
		' "$inittab" >"${inittab}.new" && mv "${inittab}.new" "$inittab"
	else
		printf '%s\n' "$readall_line" >>"$inittab"
	fi
	grep -Fxc -- "$readall_line" "$inittab" >"${work}/inittab-readall-count.txt" || true
	[[ "$(<"${work}/inittab-readall-count.txt")" == 1 ]]
	printf 'remount_before=%s\nremount_after=%s\n' \
		"$before_count" "$after_count" >>"${work}/inittab-readall-count.txt"
	local info compression block_size
	info="$("$host/bin/unsquashfs" -s "$src")"
	compression="$(awk '$1 == "Compression" {print $2; exit}' <<<"$info")"
	block_size="$(awk '$1 == "Block" && $2 == "size" {print $3; exit}' <<<"$info")"
	"$host/bin/mksquashfs" "$tree" "$dst" \
		-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
		-b "$block_size" >"${work}/mksquashfs.log" 2>&1
}

error_mode=panic_on_corruption
case_fec_roots="$fec_roots"
offset=none
multi_offsets=none
# params file（F0/F5 生成・F1-F4/F6 は F0 由来）から source する変数の宣言
data_blocks=0 data_bytes=0 hash_start_block=0 hash_area_blocks=0
root_hash='' salt=''

case "$case_kind" in
	F0|F5)
		# F0/F5 は自前で image を生成する（F5 は FEC なし）
		if [[ "$case_kind" == F5 ]]; then
			case_fec_roots=0
		fi
		rootfs="${case_dir}/rootfs.img"
		build_squashfs_with_readall "${v0}/rootfs.squashfs" \
			"${case_dir}/rootfs.squashfs" "$case_dir"
		cp --sparse=always "${case_dir}/rootfs.squashfs" "$rootfs"
		rootfs_bytes="$(stat -c %s "$rootfs")"
		data_bytes=$(((rootfs_bytes + 4095) / 4096 * 4096))
		truncate -s "$data_bytes" "$rootfs"
		"$verityfmt_bin" --hash crc32c --block-size 4096 \
			--salt "$salt_hex" \
			--fec-roots "$case_fec_roots" \
			--params-file "${case_dir}/verity-parameters.env" \
			"$rootfs" >"${case_dir}/format.log" 2>&1
		# shellcheck disable=SC1091
		source "${case_dir}/verity-parameters.env"
		if [[ "$case_kind" == F5 ]]; then
			offset="$((4096 * (data_blocks / 2) + 123))"
		fi
		cp --sparse=always "${v0}/images/sdcard.img" "${case_dir}/images/sdcard.img"
		cp "${base_dir}/T0/images/Image" "${case_dir}/images/Image"
		cp "${v0}/images/bcm2710-rpi-cm0.dtb" \
			"${case_dir}/images/bcm2710-rpi-cm0.dtb"
		;;
	*)
		# F1-F4, F6 は F0 の image を複製して破損を注入
		[[ -f "${f0}/verity-parameters.env" && -f "${f0}/rootfs.img" ]]
		# shellcheck disable=SC1091
		source "${f0}/verity-parameters.env"
		data_bytes=$((data_blocks * 4096))
		cp "${f0}/rootfs.img" "${case_dir}/rootfs.img"
		cp --sparse=always "${f0}/images/sdcard.img" "${case_dir}/images/sdcard.img"
		cp "${f0}/images/Image" "${case_dir}/images/Image"
		cp "${f0}/images/bcm2710-rpi-cm0.dtb" \
			"${case_dir}/images/bcm2710-rpi-cm0.dtb"
		case "$case_kind" in
			F1) offset="$((4096 * (data_blocks / 2) + 123))" ;;
			F2)
				# 同一 round（block index が rounds で合同）の
				# fec_roots+1 block の同じ byte 位置を破損させて
				# 訂正不能にする。covered = data+hash blocks。
				multi_offsets=yes
				;;
			F3) offset="$((hash_start_block * 4096 + 17))" ;;
			F4) : ;;  # root_hash のみ改ざん
			F6)
				multi_offsets=yes
				error_mode=restart_on_corruption
				;;
		esac
		;;
esac

case_root_hash="$root_hash"
if [[ "$case_kind" == F4 ]]; then
	if [[ "${root_hash: -1}" == 0 ]]; then
		case_root_hash="${root_hash%?}1"
	else
		case_root_hash="${root_hash%?}0"
	fi
fi

if [[ "$multi_offsets" == yes ]]; then
	# covered = data_blocks + hash_area_blocks; rounds = ceil(covered/rsn)
	python3 - "${case_dir}/rootfs.img" "$data_blocks" "$hash_area_blocks" \
		"$case_fec_roots" "${case_dir}/tamper-details.txt" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data_blocks = int(sys.argv[2])
hash_area_blocks = int(sys.argv[3])
fec_roots = int(sys.argv[4])
bs = 4096
covered = data_blocks + hash_area_blocks
rsn = 255 - fec_roots
rounds = (covered + rsn - 1) // rsn
# round 0 の block 集合 {i*rounds + 0} から fec_roots+1 block を選び、
# すべて byte offset 0 を反転する -> codeword (round=0, byte=0) の
# erasure が roots+1 になり RS(255, rsn) は訂正できない。
blocks = [i * rounds for i in range(fec_roots + 1)]
data = bytearray(path.read_bytes())
lines = ["mode=multi", f"rounds={rounds}", f"rsn={rsn}", f"covered={covered}"]
for blk in blocks:
    off = blk * bs  # byte position 0 of each block
    if off >= len(data):
        raise SystemExit(f"offset out of range: {off} / {len(data)}")
    before = data[off]
    data[off] ^= 0x01
    lines.append(f"offset={off} block={blk} before=0x{before:02x} after=0x{data[off]:02x}")
path.write_bytes(data)
pathlib.Path(sys.argv[5]).write_text("\n".join(lines) + "\n", encoding="ascii")
PY
elif [[ "$offset" != none ]]; then
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
if ((case_fec_roots)); then
	fec_start_block="$((hash_start_block + hash_area_blocks))"
	opt_args="9 use_fec_from_device /dev/mmcblk0p5 fec_roots ${case_fec_roots} fec_blocks $((data_blocks + hash_area_blocks)) fec_start ${fec_start_block} ${error_mode}"
else
	opt_args="1 ${error_mode}"
fi
dm_table="vroot,,,ro,0 ${data_sectors} verity 1 /dev/mmcblk0p5 /dev/mmcblk0p5 4096 4096 ${data_blocks} ${hash_start_block} crc32c ${case_root_hash} ${salt} ${opt_args}"
printf 'dm-mod.waitfor=/dev/mmcblk0p5 dm-mod.create="%s" initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1\n' \
	"$dm_table" >"${case_dir}/qemu-extra-append.txt"

{
	printf 'variant=%s\nexperiment_head=%s\n' "$case_name" "$experiment_head"
	printf 'rootfs_size=%s\nrootfs_a_start_sector=%s\nrootfs_a_size_sectors=%s\n' \
		"$rootfs_size" "$root_a_start" "$root_a_size"
	printf 'data_blocks=%s\nhash_offset=%s\nhash_start_block=%s\nhash_area_blocks=%s\ndata_sectors=%s\n' \
		"$data_blocks" "$data_bytes" "$hash_start_block" "$hash_area_blocks" "$data_sectors"
	printf 'fec_roots=%s\nerror_mode=%s\nhash_alg=crc32c\n' \
		"$case_fec_roots" "$error_mode"
	printf 'root_hash=%s\nsalt=%s\ncmdline_root=/dev/dm-0\n' \
		"$case_root_hash" "$salt"
	sha256sum "${case_dir}/rootfs.img" "${case_dir}/images/sdcard.img" \
		"${case_dir}/images/Image" "${case_dir}/images/bcm2710-rpi-cm0.dtb"
	printf 'A_slot_rootfs_bytes_match=1\n'
} >"${case_dir}/variant-info.txt"
