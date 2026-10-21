#!/bin/bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd)"
parser="${repo_root}/board/cardputerzero/tools/bench/boottime/parse-boottime.py"
output_dir="${OUTPUT_DIR:-${repo_root}/output}"
qemu_system="${QEMU_SYSTEM_AARCH64:-${script_dir}/qemu-no-reboot.sh}"
case_name=
image=
runs=
timeout_seconds=
csv=
log_dir=
expected=verity-error
container_id="${CONTAINER_ID:-}"

usage() {
	printf 'Usage: %s --case NAME --image FILE --runs N --timeout SEC --csv FILE --log-dir DIR [--expected ready|verity-error]\n' "$0" >&2
}

while (($#)); do
	case "$1" in
		--case) case_name="$2"; shift 2 ;;
		--image) image="$2"; shift 2 ;;
		--runs) runs="$2"; shift 2 ;;
		--timeout) timeout_seconds="$2"; shift 2 ;;
		--csv) csv="$2"; shift 2 ;;
		--log-dir) log_dir="$2"; shift 2 ;;
		--expected) expected="$2"; shift 2 ;;
		*) usage; exit 2 ;;
	esac
done

if [[ -z "$case_name" || -z "$image" || ! "$runs" =~ ^[0-9]+$ ||
	! "$timeout_seconds" =~ ^[0-9]+$ || -z "$csv" || -z "$log_dir" ||
	! -f "$parser" ]]; then
	usage
	exit 2
fi
if [[ "$expected" != ready && "$expected" != verity-error ]]; then
	usage
	exit 2
fi
[[ -f "$image" ]]
image_dir="$(cd -- "$(dirname -- "$image")" && pwd)"
case_dir="$(dirname -- "$image_dir")"
case_append="${case_dir}/qemu-extra-append.txt"
[[ -f "$case_append" ]]
extra_append="${QEMU_EXTRA_APPEND:-$(<"$case_append")}"
mkdir -p "$log_dir" "$(dirname "$csv")"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-${case_name}-icount"
failed=0

for ((repeat = 0; repeat <= runs; repeat++)); do
	boot_dir="${log_dir}/boot${repeat}"
	serial_log="${boot_dir}/serial-mmcblk0p5.log"
	mkdir -p "$boot_dir"
	: >"${boot_dir}/test-qemu.log"
	start_ns="$(date +%s%N)"
	exit_status=0
	test_env=(
		env
		"OUTPUT_DIR=${output_dir}"
		"QEMU_LOG_DIR=${boot_dir}"
		"ROOT_DEVICE=/dev/dm-0"
		"QEMU_SYSTEM_AARCH64=${qemu_system}"
		"KERNEL_IMAGE=${image_dir}/Image"
		"DTB_IMAGE=${image_dir}/bcm2710-rpi-cm0.dtb"
		"QEMU_MODULE_TEST="
		"QEMU_BOOT_TIMEOUT=$timeout_seconds"
		"QEMU_ICOUNT=shift=0"
		"QEMU_COPY_IMAGE=1"
		"QEMU_EXTRA_APPEND=${extra_append}"
	)
	if [[ "$expected" == verity-error ]]; then
		"${test_env[@]}" "${repo_root}/board/cardputerzero/qemu/test-qemu.sh" "$image" \
			>"${boot_dir}/test-qemu.log" 2>&1 &
		test_pid=$!
		while jobs -pr | grep -Fxq "$test_pid"; do
			if [[ -f "$serial_log" ]] &&
				! grep -aFq 'MSD/Linux ready' "$serial_log" &&
				grep -aFq 'device-mapper: verity' "$serial_log"; then
				printf 'terminated-after-verity-error\n' >"${boot_dir}/monitor.log"
				kill -TERM "$test_pid" 2>/dev/null || true
				break
			fi
			sleep 1
		done
		if wait "$test_pid"; then
			exit_status=0
		else
			exit_status=$?
		fi
	else
		if "${test_env[@]}" "${repo_root}/board/cardputerzero/qemu/test-qemu.sh" "$image" \
			>"${boot_dir}/test-qemu.log" 2>&1; then
			exit_status=0
		else
			exit_status=$?
			failed=1
		fi
	fi
	end_ns="$(date +%s%N)"
	wall_ns=$((end_ns - start_ns))
	printf -v wall_seconds '%d.%06d' \
		"$((wall_ns / 1000000000))" "$(((wall_ns % 1000000000) / 1000))"
	python3 "$parser" --log "$serial_log" --csv "$csv" --run-id "$run_id" \
		--variant "$case_name" --mode icount --repeat "$repeat" \
		--first-boot "$((repeat == 0 ? 1 : 0))" \
		--wall-seconds "$wall_seconds" --exit-status "$exit_status" \
		>"${boot_dir}/parse.log" 2>&1 || failed=1
	{
		printf 'run_id=%s\nrepeat=%s\nexpected=%s\nexit_status=%s\n' \
			"$run_id" "$repeat" "$expected" "$exit_status"
		if [[ -f "$serial_log" ]]; then
			grep -aniE 'MSD/Linux ready|login:|device-mapper: verity|Kernel panic' \
				"$serial_log" || true
		fi
		cat "${boot_dir}/parse.log"
	} >"${boot_dir}/result.txt"
done

if [[ -n "$container_id" ]]; then
	docker stop "$container_id" >/dev/null
	[[ "$(docker inspect -f '{{.State.Running}}' "$container_id")" == false ]]
fi
exit "$failed"
