#!/bin/bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd)"
parser="${repo_root}/board/cardputerzero/tools/bench/boottime/parse-boottime.py"
variant=
image=
runs=
csv=
log_dir=

usage() {
	printf 'Usage: %s --variant NAME --image SD_IMAGE --runs N --csv FILE --log-dir DIR\n' "$0" >&2
}

while (($#)); do
	case "$1" in
		--variant) variant="$2"; shift 2 ;;
		--image) image="$2"; shift 2 ;;
		--runs) runs="$2"; shift 2 ;;
		--csv) csv="$2"; shift 2 ;;
		--log-dir) log_dir="$2"; shift 2 ;;
		*) usage; exit 2 ;;
	esac
done

if [[ -z "$variant" || -z "$image" || ! "$runs" =~ ^[0-9]+$ ||
	-z "$csv" || -z "$log_dir" ]]; then
	usage
	exit 2
fi
[[ -f "$image" && -f "$parser" ]]
mkdir -p "$log_dir" "$(dirname "$csv")"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-${variant}-icount"
failed=0

for ((repeat = 0; repeat <= runs; repeat++)); do
	boot_dir="${log_dir}/boot${repeat}"
	serial_log="${boot_dir}/serial-mmcblk0p5.log"
	mkdir -p "$boot_dir"
	start_ns="$(date +%s%N)"
	exit_status=0
	if OUTPUT_DIR="${OUTPUT_DIR:?set OUTPUT_DIR}" \
		QEMU_LOG_DIR="$boot_dir" QEMU_ICOUNT=shift=0 \
		QEMU_COPY_IMAGE=0 QEMU_BOOT_TIMEOUT="${QEMU_BOOT_TIMEOUT:-1800}" \
		QEMU_EXTRA_APPEND='initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1 trace_event=sched:sched_process_exec trace_buf_size=4M' \
		"${repo_root}/board/cardputerzero/qemu/test-boot.sh" "$image" \
		>"${boot_dir}/test-boot.log" 2>&1; then
		exit_status=0
	else
		exit_status=$?
		failed=1
	fi
	end_ns="$(date +%s%N)"
	wall_ns=$((end_ns - start_ns))
	printf -v wall_seconds '%d.%06d' \
		"$((wall_ns / 1000000000))" "$(((wall_ns % 1000000000) / 1000))"
	python3 "$parser" --log "$serial_log" --csv "$csv" --run-id "$run_id" \
		--variant "$variant" --mode icount --repeat "$repeat" \
		--first-boot "$((repeat == 0 ? 1 : 0))" \
		--wall-seconds "$wall_seconds" --exit-status "$exit_status" \
		|| failed=1
done
exit "$failed"
