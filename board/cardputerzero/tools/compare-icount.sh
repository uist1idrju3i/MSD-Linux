#!/bin/bash
# 2 つの qemu-system-aarch64 で icount 起動の ready 実時間を比較する。
# QEMU_VERSION を上げる前の回帰ゲート（docker/msd-dev.Dockerfile の手順参照）。
# 使い方:
#   docker/msd-dev board/cardputerzero/tools/compare-icount.sh \
#     <qemu-a> <qemu-b> [sdcard.img]
# 11.0.2 を build-qemu.sh で作った binary と新バージョンを比較し、
# b が COMPARE_ICOUNT_THRESHOLD（既定 1.5）倍より遅ければ exit 1。
set -euo pipefail
unset BASH_ENV

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
QEMU_A="${1:?usage: compare-icount.sh <qemu-a> <qemu-b> [sdcard.img]}"
QEMU_B="${2:?usage: compare-icount.sh <qemu-a> <qemu-b> [sdcard.img]}"
IMAGE="${3:-}"
RUNS="${COMPARE_ICOUNT_RUNS:-1}"
THRESHOLD="${COMPARE_ICOUNT_THRESHOLD:-1.5}"

for b in "$QEMU_A" "$QEMU_B"; do
	if [ ! -x "$b" ]; then
		printf 'qemu binary not executable: %s\n' "$b" >&2
		exit 2
	fi
done

ready_seconds() {
	local cmd=("${SCRIPT_DIR}/../qemu/test-boot.sh")
	if [ -n "$IMAGE" ]; then cmd+=("$IMAGE"); fi
	QEMU_SYSTEM_AARCH64="$1" \
	QEMU_ICOUNT='shift=0,sleep=off' \
	QEMU_MODULE_TEST='' \
		"${cmd[@]}" 2>/dev/null \
		| sed -n 's/.*ready after \([0-9][0-9]*\) seconds.*/\1/p' \
		| tail -n 1
}

for side in A B; do
	case "$side" in
		A) bin="$QEMU_A" ;;
		B) bin="$QEMU_B" ;;
	esac
	best=
	for _ in $(seq 1 "$RUNS"); do
		s="$(ready_seconds "$bin")"
		if [ -z "$s" ]; then
			printf 'boot did not reach ready for %s\n' "$bin" >&2
			exit 1
		fi
		if [ -z "$best" ] || [ "$s" -lt "$best" ]; then best="$s"; fi
	done
	eval "BEST_${side}=$best"
	printf '%s ready: %ss (%s)\n' "$side" "$best" "$bin"
done

ratio="$(awk -v a="$BEST_A" -v b="$BEST_B" 'BEGIN { printf "%.2f", b / a }')"
printf 'ratio B/A: %sx (threshold %sx)\n' "$ratio" "$THRESHOLD"
if [ "$(awk -v r="$ratio" -v t="$THRESHOLD" 'BEGIN { print (r > t) ? 1 : 0 }')" = 1 ]; then
	printf 'regression: %s is slower than %s\n' "$QEMU_B" "$QEMU_A" >&2
	exit 1
fi
