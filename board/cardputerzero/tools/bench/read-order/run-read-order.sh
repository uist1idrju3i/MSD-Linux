#!/usr/bin/env bash
# Boot the A slot with test-boot.sh RUNS times and keep the QEMU
# sdcard_read_block trace of each boot. Run inside docker/msd-dev with
# OUTPUT_DIR set; set QEMU_ICOUNT to compare deterministic runs.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:?set OUTPUT_DIR}"
VARIANT="${READ_ORDER_VARIANT:?set READ_ORDER_VARIANT}"
RUNS="${READ_ORDER_RUNS:-5}"
LOG_ROOT="${READ_ORDER_LOG_DIR:-${OUTPUT_DIR}/read-order}/${VARIANT}"
IMAGE="${OUTPUT_DIR}/images/sdcard.img"

[[ -e "$LOG_ROOT" ]] && { printf 'Refusing to overwrite %s\n' "$LOG_ROOT" >&2; exit 1; }
mkdir -p "$LOG_ROOT"
{
	printf 'variant=%s runs=%s qemu_icount=%s\n' "$VARIANT" "$RUNS" "${QEMU_ICOUNT:-none}"
	sha256sum "$IMAGE" "${OUTPUT_DIR}/images/rootfs.squashfs"
	qemu-system-aarch64 --version | head -n 1
} >"${LOG_ROOT}/conditions.log"
for ((i = 1; i <= RUNS; i++)); do
	dir="${LOG_ROOT}/boot${i}"
	mkdir -p "$dir"
	status=0
	QEMU_LOG_DIR="$dir" QEMU_SYSTEM_AARCH64="${SCRIPT_DIR}/qemu-trace-wrap.sh" \
		"${REPO_DIR}/board/cardputerzero/qemu/test-boot.sh" "$IMAGE" >"${dir}/test-boot.log" 2>&1 || status=$?
	printf 'boot%s exit=%s trace_lines=%s\n' "$i" "$status" \
		"$(grep -c sdcard_read_block "${dir}/sd-trace.log" 2>/dev/null || echo 0)" >>"${LOG_ROOT}/conditions.log"
done
cat "${LOG_ROOT}/conditions.log"
