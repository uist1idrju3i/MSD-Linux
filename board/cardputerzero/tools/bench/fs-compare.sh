#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output-fscmp}"
IMAGES_DIR="${OUTPUT_DIR}/images"
RUNS_ROOT="${QEMU_LOG_DIR:-}"
RUN_QEMU="${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh"
TEST_ROOTFS="${IMAGES_DIR}/rootfs.squashfs"
BASE_IMAGE="${IMAGES_DIR}/sdcard.img"
KERNEL="${IMAGES_DIR}/Image"
DTB="${IMAGES_DIR}/bcm2710-rpi-3-b.dtb"

usage()
{
	printf 'Usage: %s <config> <test> <run_id>\n' "${BASH_SOURCE[0]}" >&2
	exit 2
}

[[ $# -eq 3 ]] || usage
CONFIG=$1
TEST=$2
RUN_ID=$3
[[ "$CONFIG" =~ ^(E[1-5]|F[1-5]|B[1-5]|L[1-3]|I[1-2])$ ]] || usage
[[ "$TEST" =~ ^(smoke|T1|T1-negative|T1-final|T1-negative-final|T1-sample|T2|T3|T4-sync|T4-nosync|T4-idle-control|T4-odirect-control|T5|T6|T7)$ ]] || usage
[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] || usage
[[ "$RUNS_ROOT" = /* ]] || {
	printf 'QEMU_LOG_DIR must be an absolute persistent path\n' >&2
	exit 1
}

RUN_DIR="${RUNS_ROOT}/${RUN_ID}"
if [[ -e "$RUN_DIR" ]]; then
	printf 'Refusing to overwrite run directory %s\n' "$RUN_DIR" >&2
	exit 1
fi
mkdir -p "$RUNS_ROOT"
mkdir "$RUN_DIR"
BUILD_DIR="${RUN_DIR}/build"
ROOTFS_DIR="${BUILD_DIR}/rootfs"
mkdir -p "$BUILD_DIR"

for required in "$TEST_ROOTFS" "$BASE_IMAGE" "$KERNEL" "$DTB" \
	"${OUTPUT_DIR}/host/bin/unsquashfs" "${OUTPUT_DIR}/host/bin/mksquashfs" \
	"${OUTPUT_DIR}/host/sbin/sfdisk" "${OUTPUT_DIR}/fs-compare/replay-log" \
	"${OUTPUT_DIR}/fs-compare/fs-compare-workload"; do
	[[ -f "$required" ]] || {
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	}
done

ROW="$(awk -F '\t' -v id="$CONFIG" '$1 == id { print; count++ } END { if (count != 1) exit 1 }' \
	"${SCRIPT_DIR}/fs-compare-configs.tsv")" || {
	printf 'Configuration %s is not defined exactly once\n' "$CONFIG" >&2
	exit 1
}

unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"
"$unsquashfs" -no-progress -no-xattrs -d "$ROOTFS_DIR" "$TEST_ROOTFS" \
	>"${BUILD_DIR}/unsquashfs.log" 2>&1 ||
	grep -Fq 'failed to change uid and gids' "${BUILD_DIR}/unsquashfs.log"
mkdir -p "${ROOTFS_DIR}/usr/libexec" "${ROOTFS_DIR}/usr/share"
install -m 0755 "${SCRIPT_DIR}/S97zz-fs-compare" \
	"${ROOTFS_DIR}/etc/init.d/S97zz-fs-compare"
install -m 0755 "${SCRIPT_DIR}/fs-compare-guest" \
	"${ROOTFS_DIR}/usr/libexec/fs-compare-guest"
install -m 0755 "${OUTPUT_DIR}/fs-compare/replay-log" \
	"${ROOTFS_DIR}/usr/libexec/replay-log"
install -m 0755 "${OUTPUT_DIR}/fs-compare/fs-compare-workload" \
	"${ROOTFS_DIR}/usr/libexec/fs-compare-workload"
install -m 0644 "${SCRIPT_DIR}/fs-compare-configs.tsv" \
	"${ROOTFS_DIR}/usr/share/fs-compare-configs.tsv"
rootfs_info="$("$unsquashfs" -s "$TEST_ROOTFS")"
compression="$(awk '$1 == "Compression" { print $2; exit }' <<<"$rootfs_info")"
block_size="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' <<<"$rootfs_info")"
"$mksquashfs" "$ROOTFS_DIR" "${BUILD_DIR}/rootfs-fs-compare.squashfs" \
	-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
	-b "$block_size" >"${BUILD_DIR}/mksquashfs.log" 2>&1

IMAGE="${RUN_DIR}/sdcard.img"
cp --sparse=always "$BASE_IMAGE" "$IMAGE"
read -r rootfs_start rootfs_size <<<"$("$sfdisk" --json "$IMAGE" | python3 -c '
import json, sys
parts = json.load(sys.stdin)["partitiontable"]["partitions"]
assert len(parts) == 7, len(parts)
print(parts[4]["start"], parts[4]["size"])
')"
rootfs_bytes=$(stat -c %s "${BUILD_DIR}/rootfs-fs-compare.squashfs")
((rootfs_bytes <= rootfs_size * 512)) || {
	printf 'Experiment rootfs (%s bytes) exceeds rootfs partition (%s bytes)\n' \
		"$rootfs_bytes" "$((rootfs_size * 512))" >&2
	exit 1
}
dd if="${BUILD_DIR}/rootfs-fs-compare.squashfs" of="$IMAGE" bs=512 \
	seek="$rootfs_start" conv=notrunc status=none
# S02msd-data grows only this disposable image's /data partition to the disk end.
truncate -s 8G "$IMAGE"

{
	printf 'config=%s\ntest=%s\nrun_id=%s\n' "$CONFIG" "$TEST" "$RUN_ID"
	printf 'base_commit=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD)"
	printf 'run_qemu=%s\n' "$RUN_QEMU"
	printf 'rootfs_partition_start=%s\nrootfs_partition_sectors=%s\n' \
		"$rootfs_start" "$rootfs_size"
	printf 'disposable_image_bytes=%s\n' "$(stat -c %s "$IMAGE")"
	printf 'setup_and_options=%s\n' "$ROW"
	printf 'replay_log_source_commit=%s\n' \
		"$(sed -n 's/^commit=//p' "${OUTPUT_DIR}/fs-compare/replay-log.provenance")"
	printf 'replay_log_sha256=%s\n' \
		"$(sha256sum "${OUTPUT_DIR}/fs-compare/replay-log" | cut -d' ' -f1)"
	printf 'workload_sha256=%s\n' \
		"$(sha256sum "${OUTPUT_DIR}/fs-compare/fs-compare-workload" | cut -d' ' -f1)"
} >"${RUN_DIR}/run-meta.txt"
sha256sum "$TEST_ROOTFS" "$BASE_IMAGE" "$KERNEL" "$DTB" "$RUN_QEMU" \
	"${BUILD_DIR}/rootfs-fs-compare.squashfs" \
	"${SCRIPT_DIR}/S97zz-fs-compare" "${SCRIPT_DIR}/fs-compare-guest" \
	"${SCRIPT_DIR}/fs-compare-workload.c" "${SCRIPT_DIR}/fs-compare-configs.tsv" \
	"${SCRIPT_DIR}/fs-compare.sh" "${SCRIPT_DIR}/fs-compare-build.sh" \
	"${SCRIPT_DIR}/fs-compare.fragment" \
	"${SCRIPT_DIR}/fs-compare.buildroot.fragment" \
	>"${RUN_DIR}/inputs.sha256"

QEMU_LOG="${RUN_DIR}/qemu.log"
prep_seconds=$SECONDS
printf 'prepare_seconds=%s\n' "$prep_seconds" >>"${RUN_DIR}/run-meta.txt"
SECONDS=0
VM_PID=

start_vm()
{
	local phase=$1
	local append="msd.fscmp=${CONFIG}:${TEST}:${RUN_ID}"
	if [[ "$phase" == verify ]]; then
		append+=" msd.fscmp.phase=verify"
	fi
	QEMU_COPY_IMAGE=0 QEMU_MACHINE=raspi3b OUTPUT_DIR="$OUTPUT_DIR" \
		QEMU_EXTRA_APPEND="$append" "$RUN_QEMU" "$IMAGE" \
		>>"$QEMU_LOG" 2>&1 &
	VM_PID=$!
}

stop_vm()
{
	if [[ -n "${VM_PID:-}" ]]; then
		kill -KILL "$VM_PID" 2>/dev/null || true
		wait "$VM_PID" 2>/dev/null || true
		VM_PID=
	fi
}
trap stop_vm EXIT

wait_for_marker()
{
	local marker=$1 timeout=$2
	local deadline=$((SECONDS + timeout))
	while ((SECONDS <= deadline)); do
		if tail -n 1000 "$QEMU_LOG" | grep -aFq "$marker"; then
			return 0
		fi
		if tail -n 1000 "$QEMU_LOG" | grep -aFq 'msd.fscmp: error='; then
			return 1
		fi
		if [[ -n "${VM_PID:-}" ]] && ! kill -0 "$VM_PID" 2>/dev/null; then
			return 1
		fi
		sleep 1
	done
	return 1
}

start_vm run
case "$TEST" in
	T2|T3)
		if [[ "$TEST" == T2 ]]; then
			start_marker='msd.fscmp: workload-start'
			delay="$(shuf -i 10-60 -n 1)"
		else
			start_marker='msd.fscmp: writer-start'
			delay="$(shuf -i 30-90 -n 1)"
		fi
		if ! wait_for_marker "$start_marker" 180; then
			printf 'Timed out waiting for %s; see %s\n' "$start_marker" "$QEMU_LOG" >&2
			stop_vm
			exit 1
		fi
		printf 'power_cut_after_seconds=%s\n' "$delay" | tee -a "${RUN_DIR}/run-meta.txt"
		sleep "$delay"
		stop_vm
		cp "$QEMU_LOG" "${RUN_DIR}/qemu-before-reboot.log"
		start_vm verify
		if ! wait_for_marker 'msd.fscmp: recovery_finished' 300; then
			printf 'Recovery did not finish; see %s\n' "$QEMU_LOG" >&2
			stop_vm
			exit 1
		fi
		stop_vm
		if [[ "$TEST" == T3 ]]; then
			last_console="$(sed -n 's/.*msd\.fscmp: T3_SEQ seq=\([0-9][0-9]*\).*/\1/p' \
				"${RUN_DIR}/qemu-before-reboot.log" | tail -n 1)"
			last_disk="$(sed -n 's/.*msd\.fscmp: T3_DISK last_seq=\([0-9][0-9]*\).*/\1/p' \
				"$QEMU_LOG" | tail -n 1)"
			fsync_lost="$(sed -n 's/.*msd\.fscmp: T3_FSYNC_LOST count=\([0-9][0-9]*\).*/\1/p' \
				"$QEMU_LOG" | tail -n 1)"
			[[ -n "$last_console" ]] || last_console=0
			[[ -n "$last_disk" ]] || last_disk=0
			[[ -n "$fsync_lost" ]] || fsync_lost=unknown
			printf 'T3 last_console_seq=%s last_disk_seq=%s lost_seconds=%s fsynced_record_loss=%s\n' \
				"$last_console" "$last_disk" "$((last_console - last_disk))" \
				"$fsync_lost" | tee -a "${RUN_DIR}/run-meta.txt"
		fi
		;;
	*)
		case "$TEST" in
			T1|T1-negative|T1-final|T1-negative-final|T1-sample) timeout=14400 ;;
			T4-sync|T4-nosync) timeout=1500 ;;
			T4-idle-control) timeout=180 ;;
			T6|T7) timeout=1800 ;;
			*) timeout=600 ;;
		esac
		if ! wait_for_marker 'msd.fscmp: finished' "$timeout"; then
			printf 'Test did not finish; see %s\n' "$QEMU_LOG" >&2
			stop_vm
			exit 1
		fi
		stop_vm
		;;
esac

qemu_seconds=$SECONDS
wall_seconds=$((prep_seconds + qemu_seconds))
printf 'qemu_seconds=%s\nwall_seconds=%s\nqemu_log=%s\n' \
	"$qemu_seconds" "$wall_seconds" "$QEMU_LOG" |
	tee -a "${RUN_DIR}/run-meta.txt"
sha256sum "$QEMU_LOG" >"${RUN_DIR}/qemu.log.sha256"
printf 'Run directory: %s\n' "$RUN_DIR"
