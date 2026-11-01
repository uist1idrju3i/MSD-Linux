#!/usr/bin/env bash
# S17: QEMU blkdebug error injection against the SD image. Wraps the product
# sdcard.img in a blkdebug driver, injects EIO on reads/writes (whole device
# or selected partition regions) and records what the guest observer
# (S97zz-blkdbgtest) reports. One CSV row per case and run.
#
# Cases:
#   control  no blkdebug (plain raw drive) — measurement-instrument check
#   wio      EIO on every guest write (whole device)
#   rio      EIO on every guest read (whole device)
#   p6w      EIO on writes covering the B-slot rootfs head region
#   p7w      EIO on writes covering the /data head region
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
IMAGES_DIR="${OUTPUT_DIR}/images"
LOG_ROOT="${S17_LOG_DIR:-${OUTPUT_DIR}/qemu-logs/s17-blkdebug}"
RUNS="${S17_RUNS:-5}"
CSV="${S17_CSV:-${LOG_ROOT}/s17-blkdebug.csv}"
TIMEOUT="${S17_TIMEOUT:-600}"
CASES="control wio rio p6w p7w"

[[ -e "$CSV" ]] && { printf 'Refusing to overwrite %s\n' "$CSV" >&2; exit 1; }
mkdir -p "$LOG_ROOT"
build="${LOG_ROOT}/build-$(date -u +%Y%m%dT%H%M%S)"
mkdir "$build"
unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"

# --- guest observer image ----------------------------------------------------
"$unsquashfs" -no-progress -no-xattrs -d "${build}/target" "${IMAGES_DIR}/rootfs.squashfs" \
	>"${build}/unsquashfs.log" 2>&1 || grep -Fq 'failed to change uid and gids' "${build}/unsquashfs.log"
install -m 0755 "${SCRIPT_DIR}/S97zz-blkdbgtest" "${build}/target/etc/init.d/S97zz-blkdbgtest"
info="$("$unsquashfs" -s "${IMAGES_DIR}/rootfs.squashfs")"
comp="$(awk '$1 == "Compression" { print $2; exit }' <<<"$info")"
bsize="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$info")"
"$mksquashfs" "${build}/target" "${build}/rootfs-blkdbg.squashfs" -noappend -all-root \
	-no-xattrs -no-progress -comp "$comp" -b "$bsize" >"${build}/mksquashfs.log" 2>&1

template="${build}/sdcard-blkdbg.img"
cp --sparse=always "${IMAGES_DIR}/sdcard.img" "$template"
padded=1; while ((padded < $(stat -c %s "$template"))); do padded=$((padded * 2)); done
truncate -s "$padded" "$template"
# p6_start/p7_start are referenced via ${!start} indirection in gen_conf.
# shellcheck disable=SC2034
read -r a_start a_size p6_start p7_start <<<"$("$sfdisk" --json "$template" | python3 -c '
import json, sys
p = json.load(sys.stdin)["partitiontable"]["partitions"]
assert len(p) == 7, len(p)
print(p[4]["start"], p[4]["size"], p[5]["start"], p[6]["start"])')"
(($(stat -c %s "${build}/rootfs-blkdbg.squashfs") <= a_size * 512)) || { echo 'test rootfs too large' >&2; exit 1; }
dd if="${build}/rootfs-blkdbg.squashfs" of="$template" bs=512 seek="$a_start" conv=notrunc status=none
sha256sum "${IMAGES_DIR}/sdcard.img" "${IMAGES_DIR}/rootfs.squashfs" "${IMAGES_DIR}/Image" \
	"${build}/rootfs-blkdbg.squashfs" "$SCRIPT_DIR/S97zz-blkdbgtest" "${BASH_SOURCE[0]}" >"${build}/inputs.sha256"

# --- blkdebug configs --------------------------------------------------------
# blkdebug on a raw child fires only event "none" (at node creation), so all
# rules use event "none"; scoping is by `iotype` and `sector` (512-byte unit,
# matched when the sector offset lies inside the request).
gen_conf() {
	local case="$1" out="$2"
	: >"$out"
	case "$case" in
		wio | rio)
			local io="write"; [[ "$case" == rio ]] && io="read"
			cat >>"$out" <<-EOF
			[inject-error]
			event = "none"
			iotype = "$io"
			errno = "5"
			immediately = "off"
			once = "off"
			EOF
			;;
		p6w | p7w)
			local start="${case%w}_start"; start="${!start}"
			local s
			for ((s = start; s < start + 4096; s += 16)); do
				cat >>"$out" <<-EOF
				[inject-error]
				event = "none"
				iotype = "write"
				errno = "5"
				sector = "$s"
				once = "off"
				EOF
			done
			;;
		control) ;;
		*) printf 'unknown case: %s\n' "$case" >&2; exit 2 ;;
	esac
}

printf 'run,case,write_data,write_p6,read_data,read_p5,data_mount,io_errors,host_werr,host_rerr,finished,note\n' >"$CSV"
for run in $(seq 1 "$RUNS"); do
	for case in $CASES; do
		disk="${build}/run${run}-${case}.img"; log="${build}/run${run}-${case}.log"
		conf="${build}/blkdebug-${case}.conf"
		gen_conf "$case" "$conf"
		cp --sparse=always "$template" "$disk"
		if [[ "$case" == control ]]; then
			env -u QEMU_DRIVE_FILE -u QEMU_DRIVE_FORMAT QEMU_COPY_IMAGE=0 \
				QEMU_EXTRA_APPEND="msd.blkdbgtest=1" OUTPUT_DIR="$OUTPUT_DIR" \
				"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$disk" >"$log" 2>&1 &
		else
			QEMU_DRIVE_FILE="blkdebug:${conf}:${disk}" QEMU_DRIVE_FORMAT=blkdebug \
				QEMU_COPY_IMAGE=0 QEMU_EXTRA_APPEND="msd.blkdbgtest=1" \
				OUTPUT_DIR="$OUTPUT_DIR" \
				"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$disk" >"$log" 2>&1 &
		fi
		pid=$!
		deadline=$((SECONDS + TIMEOUT)); note=""
		until grep -aq 'msd-blkdbg: finished' "$log"; do
			if ((SECONDS > deadline)) || ! kill -0 "$pid" 2>/dev/null; then note=timeout; break; fi
			sleep 2
		done
		kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true
		rm -f "$disk"
		val() { tr -d '\r' <"$log" | sed -n "s/.*msd-blkdbg: \(.* \)\?$1=\([^ ]*\).*/\2/p" | tail -n 1; }
		mnt="$(tr -d '\r' <"$log" | sed -n 's/.*msd-blkdbg: data_mount=\([^ ]*\).*/\1/p' | tail -n 1)"
		fin=no; grep -aq 'msd-blkdbg: finished' "$log" && fin=yes
		# QEMU の SD エミュレーションは blkdebug の注入エラーを guest に返さず
		# "sd_blk_write/read: ... error on host side" を stderr に出すだけなので、
		# 注入の発火はホスト側ログで数える
		hwerr="$(grep -ac 'write error on host side' "$log" || true)"
		hrerr="$(grep -ac 'read error on host side' "$log" || true)"
		printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$run" "$case" "$(val write_data)" "$(val write_p6)" \
			"$(val read_data)" "$(val read_p5)" "${mnt:-none}" "$(val io_errors_after)" \
			"$hwerr" "$hrerr" "$fin" "$note" >>"$CSV"
		sha256sum "$log" >>"${build}/logs.sha256"
	done
done
printf 'CSV: %s\n' "$CSV"
