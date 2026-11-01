#!/usr/bin/env bash
# S17: dm-log-writes write-pattern replay. Boots an experiment image (kernel
# with CONFIG_BLK_DEV_DM=y + CONFIG_DM_LOG_WRITES=y, rootfs with dmsetup),
# records a deterministic write workload through a dm-log-writes device in the
# guest, extracts the log device contents from the /data partition, replays it
# on the host with replay-log and compares the reconstructed disk to the
# original. One CSV row per run.
#
# Usage:
#   OUTPUT_DIR=output2 REPLAY_LOG=/path/to/replay-log \
#     board/cardputerzero/tools/bench/s17-dm-log-writes.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output2}"
IMAGES_DIR="${OUTPUT_DIR}/images"
LOG_ROOT="${S17_LOG_DIR:-${OUTPUT_DIR}/qemu-logs/s17-dmlw}"
RUNS="${S17_RUNS:-5}"
CSV="${S17_CSV:-${LOG_ROOT}/s17-dmlw.csv}"
TIMEOUT="${S17_TIMEOUT:-600}"
REPLAY_LOG="${REPLAY_LOG:-replay-log}"

[[ -e "$CSV" ]] && { printf 'Refusing to overwrite %s\n' "$CSV" >&2; exit 1; }
command -v "$REPLAY_LOG" >/dev/null || { printf 'replay-log not found: %s\n' "$REPLAY_LOG" >&2; exit 1; }
mkdir -p "$LOG_ROOT"
build="${LOG_ROOT}/build-$(date -u +%Y%m%dT%H%M%S)"
mkdir "$build"
unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"

# --- guest observer image ----------------------------------------------------
"$unsquashfs" -no-progress -no-xattrs -d "${build}/target" "${IMAGES_DIR}/rootfs.squashfs" \
	>"${build}/unsquashfs.log" 2>&1 || grep -Fq 'failed to change uid and gids' "${build}/unsquashfs.log"
install -m 0755 "${SCRIPT_DIR}/S97zz-dmlwtest" "${build}/target/etc/init.d/S97zz-dmlwtest"
info="$("$unsquashfs" -s "${IMAGES_DIR}/rootfs.squashfs")"
comp="$(awk '$1 == "Compression" { print $2; exit }' <<<"$info")"
bsize="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$info")"
"$mksquashfs" "${build}/target" "${build}/rootfs-dmlw.squashfs" -noappend -all-root \
	-no-xattrs -no-progress -comp "$comp" -b "$bsize" >"${build}/mksquashfs.log" 2>&1

template="${build}/sdcard-dmlw.img"
cp --sparse=always "${IMAGES_DIR}/sdcard.img" "$template"
padded=1; while ((padded < $(stat -c %s "$template"))); do padded=$((padded * 2)); done
truncate -s "$padded" "$template"
read -r a_start a_size p7_start <<<"$("$sfdisk" --json "$template" | python3 -c '
import json, sys
p = json.load(sys.stdin)["partitiontable"]["partitions"]
assert len(p) == 7, len(p)
print(p[4]["start"], p[4]["size"], p[6]["start"])')"
(($(stat -c %s "${build}/rootfs-dmlw.squashfs") <= a_size * 512)) || { echo 'test rootfs too large' >&2; exit 1; }
dd if="${build}/rootfs-dmlw.squashfs" of="$template" bs=512 seek="$a_start" conv=notrunc status=none
sha256sum "${IMAGES_DIR}/sdcard.img" "${IMAGES_DIR}/rootfs.squashfs" "${IMAGES_DIR}/Image" \
	"${build}/rootfs-dmlw.squashfs" "$SCRIPT_DIR/S97zz-dmlwtest" "${BASH_SOURCE[0]}" >"${build}/inputs.sha256"

printf 'run,dm_create,mark,disk_sha,log_bytes,replay_sha,match,finished,note\n' >"$CSV"
for run in $(seq 1 "$RUNS"); do
	disk="${build}/run${run}.img"; log="${build}/run${run}.log"
	cp --sparse=always "$template" "$disk"
	QEMU_COPY_IMAGE=0 QEMU_EXTRA_APPEND="msd.dmlwtest=1" OUTPUT_DIR="$OUTPUT_DIR" \
		"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$disk" >"$log" 2>&1 &
	pid=$!
	deadline=$((SECONDS + TIMEOUT)); note=""
	until grep -aq 'msd-dmlw: finished' "$log"; do
		if ((SECONDS > deadline)) || ! kill -0 "$pid" 2>/dev/null; then note=timeout; break; fi
		sleep 2
	done
	kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true

	val() { tr -d '\r' <"$log" | sed -n "s/.*msd-dmlw: \(.* \)\?$1=\([^ ]*\).*/\2/p" | tail -n 1; }
	dsha="$(val disk_sha)"; lsize="$(val log_size)"
	fin=no; grep -aq 'msd-dmlw: finished' "$log" && fin=yes

	replay_sha=""; match=""
	if [[ "$fin" == yes ]]; then
		# /data (p7) の中身を debugfs で取り出す
		p7img="${build}/run${run}-p7.img"
		dd if="$disk" of="$p7img" bs=512 skip="$p7_start" status=none
		rdir="${build}/run${run}-files"; mkdir "$rdir"
		for f in dmlw-disk.img dmlw-log.img; do
			debugfs -R "dump /$f ${rdir}/$f" "$p7img" >"${rdir}/$f.debugfs.log" 2>&1 || true
		done
		rm -f "$p7img"
		if [[ -s "${rdir}/dmlw-disk.img" && -s "${rdir}/dmlw-log.img" ]]; then
			truncate -s "$(stat -c %s "${rdir}/dmlw-disk.img")" "${rdir}/dmlw-replay.img" 2>/dev/null || \
				dd if=/dev/zero of="${rdir}/dmlw-replay.img" bs=1M count=16 status=none
			"$REPLAY_LOG" --log "${rdir}/dmlw-log.img" \
				--replay "${rdir}/dmlw-replay.img" >"${rdir}/replay.log" 2>&1 || note="replay_fail"
			replay_sha="$(sha256sum "${rdir}/dmlw-replay.img" | cut -d' ' -f1)"
			[[ "$replay_sha" == "$dsha" ]] && match=yes || match=no
		else
			note="extract_fail"
		fi
	fi
	printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$run" "$(val dm_create)" "$(val mark)" \
		"$dsha" "$lsize" "$replay_sha" "$match" "$fin" "$note" >>"$CSV"
	sha256sum "$log" >>"${build}/logs.sha256"
done
printf 'CSV: %s\n' "$CSV"
