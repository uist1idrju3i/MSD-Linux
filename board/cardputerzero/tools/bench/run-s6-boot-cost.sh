#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../" && pwd)"
if [ "$#" -ne 6 ]; then
	printf 'Usage: %s <variant> <sdcard.img> <Image> <dtb> <log-dir> <csv>\n' "$0" >&2
	exit 2
fi

variant="$1"
image="$2"
kernel="$3"
dtb="$4"
log_dir="$5"
csv="$6"

mkdir -p "$log_dir" "$(dirname -- "$csv")"
if [ ! -e "$csv" ]; then
	printf 'variant,run,ready_kernel_seconds\n' > "$csv"
fi
export QEMU_MODULE_TEST=

for run in 1 2 3; do
	run_log_dir="${log_dir}/run${run}"
	mkdir -p "$run_log_dir"
	OUTPUT_DIR="$(dirname -- "$(dirname -- "$image")")" \
	KERNEL_IMAGE="$kernel" \
	DTB_IMAGE="$dtb" \
	QEMU_ICOUNT=shift=0 \
	QEMU_EXTRA_APPEND='initcall_debug printk.time=1 msd.sweep=1' \
	QEMU_LOG_DIR="$run_log_dir" \
		"$REPO_ROOT/board/cardputerzero/qemu/test-boot.sh" "$image"

	serial_log="${run_log_dir}/serial-mmcblk0p5.log"
	ready_time="$(
		sed -nE 's/^\[[[:space:]]*([0-9]+([.][0-9]+)?)\][[:space:]]+MSD\/Linux ready.*/\1/p' \
			"$serial_log" | head -n 1
	)"
	if [ -z "$ready_time" ]; then
		printf 'Could not extract the ready-marker kernel time from %s\n' "$serial_log" >&2
		exit 1
	fi
	printf '%s,%s,%s\n' "$variant" "$run" "$ready_time" >> "$csv"
done
