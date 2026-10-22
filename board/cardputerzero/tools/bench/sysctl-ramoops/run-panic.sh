#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd -P)"
qemu_runner="${repo_root}/board/cardputerzero/qemu/run-qemu.sh"
append_row="${script_dir}/append-row.py"
output_dir="${OUTPUT_DIR:-${repo_root}/output}"
log_root="${QEMU_LOG_DIR:?set QEMU_LOG_DIR to the persistent S21 log directory}"
variant_root="${log_root}/variants"
csv="${repo_root}/docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.csv"
base_dtb="${output_dir}/images/bcm2710-rpi-cm0.dtb"
run_tag=
modes=(P0 P1 R0 R1)

usage() {
	printf 'Usage: %s [--modes MODE[,MODE...]] [--run-tag TAG] [--variant-root DIR] [--csv FILE]\n' "$0"
}

while (($#)); do
	case "$1" in
		--modes)
			(($# >= 2)) || { usage >&2; exit 2; }
			IFS=, read -r -a modes <<<"$2"
			shift 2
			;;
		--run-tag)
			(($# >= 2)) || { usage >&2; exit 2; }
			run_tag="$2"
			shift 2
			;;
		--variant-root)
			(($# >= 2)) || { usage >&2; exit 2; }
			variant_root="$2"
			shift 2
			;;
		--csv)
			(($# >= 2)) || { usage >&2; exit 2; }
			csv="$2"
			shift 2
			;;
		--help)
			usage
			exit 0
			;;
		*)
			printf 'Unknown argument: %s\n' "$1" >&2
			usage >&2
			exit 2
			;;
	esac
done

if ((${#modes[@]} == 0)); then
	printf 'At least one mode is required.\n' >&2
	exit 2
fi
declare -A selected_modes=()
run_ids=()
for mode in "${modes[@]}"; do
	case "$mode" in
		P0|P1|R0|R1) ;;
		*)
			printf 'Unsupported mode: %s\n' "$mode" >&2
			exit 2
			;;
	esac
	if [[ -v "selected_modes[$mode]" ]]; then
		printf 'Duplicate mode: %s\n' "$mode" >&2
		exit 2
	fi
	selected_modes["$mode"]=1
	for trial in 1 2 3 4 5; do
		run_id="s21-${mode}-${trial}"
		if [[ -n "$run_tag" ]]; then
			run_id="s21-${mode}-${run_tag}-${trial}"
		fi
		run_ids+=("$run_id")
	done
done

python3 - "$csv" "$log_root" "${run_ids[@]}" <<'PY'
import csv
import pathlib
import sys

csv_path = pathlib.Path(sys.argv[1])
log_root = pathlib.Path(sys.argv[2])
run_ids = sys.argv[3:]
existing = set()
if csv_path.exists():
    with csv_path.open(newline="", encoding="utf-8") as source:
        existing = {row["run_id"] for row in csv.DictReader(source)}
collisions = [
    run_id
    for run_id in run_ids
    if (log_root / run_id).exists() or run_id in existing
]
if collisions:
    print("Refusing to overwrite existing run IDs: " + ", ".join(collisions), file=sys.stderr)
    raise SystemExit(2)
PY

sha256_file() {
	sha256sum "$1" | awk '{print $1}'
}

now_ns() {
	python3 -c 'import time; print(time.monotonic_ns())'
}

wait_for_text() {
	local log="$1"
	local text="$2"
	local pid="$3"
	local timeout="$4"
	local deadline=$((SECONDS + timeout))
	while ((SECONDS <= deadline)); do
		if grep -aFq -- "$text" "$log" 2>/dev/null; then
			return 0
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			return 1
		fi
		sleep 0.1
	done
	return 1
}

wait_for_second_kernel() {
	local log="$1"
	local pid="$2"
	local timeout="$3"
	local deadline=$((SECONDS + timeout))
	while ((SECONDS <= deadline)); do
		if (( $(grep -aFc 'Booting Linux on physical CPU' "$log" 2>/dev/null || true) >= 2 )); then
			return 0
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			return 1
		fi
		sleep 0.1
	done
	return 1
}

wait_for_second_boot_ready() {
	local log="$1"
	local pid="$2"
	local timeout="$3"
	local deadline=$((SECONDS + timeout))
	while ((SECONDS <= deadline)); do
		if grep -aFq 's21: second boot' "$log" 2>/dev/null &&
			(( $(grep -aFc 'MSD/Linux ready' "$log" 2>/dev/null || true) >= 2 ))
		then
			return 0
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			return 1
		fi
		sleep 0.1
	done
	return 1
}

wait_for_pstore_collection() {
	local log="$1"
	local pid="$2"
	local timeout="$3"
	local deadline=$((SECONDS + timeout))
	while ((SECONDS <= deadline)); do
		if grep -aFq 's21: pstore collection complete' "$log" 2>/dev/null; then
			return 0
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			return 1
		fi
		sleep 0.1
	done
	return 1
}

run_trial() {
	local mode="$1"
	local trial="$2"
	local variant="$mode"
	local condition="$mode"
	local panic_arg=panic=0
	local dtb="$base_dtb"
	local run_id="s21-${mode}-${trial}"
	local run_dir="${log_root}/${run_id}"
	local image="${variant_root}/${variant}/sdcard.img"
	local rootfs="${variant_root}/${variant}/rootfs.squashfs"
	local disk="${run_dir}/sdcard.img"
	local log="${run_dir}/serial.log"
	local image_hash
	local qemu_pid marker_ns reset_ns marker_to_reset
	local ready=no reset_seen=no exit_status=0
	local panic_seen=no reboot_seen=no registration=no
	local pstore_status=missing pstore_files=
	local record_sysrq=no record_panic=no valid=0 criteria=fail note=
	local pstore_complete=no
	local cmdline=panic=0

	if [[ -n "$run_tag" ]]; then
		run_id="s21-${mode}-${run_tag}-${trial}"
		run_dir="${log_root}/${run_id}"
		disk="${run_dir}/sdcard.img"
		log="${run_dir}/serial.log"
	fi

	if [[ "$mode" == P1 || "$mode" == R0 || "$mode" == R1 ]]; then
		panic_arg=panic=5
		cmdline=panic=5
	fi
	if [[ "$mode" == R0 || "$mode" == R1 ]]; then
		condition="$mode"
		if [[ "$mode" == R1 ]]; then
			dtb="${variant_root}/R1/ramoops.dtb"
		fi
	fi
	mkdir -p "$run_dir"
	cp --sparse=always "$image" "$disk"
	image_hash="$(sha256_file "$disk")"
	: >"$log"
	env -u QEMU_ICOUNT QEMU_WATCHDOG=1 \
		QEMU_EXTRA_APPEND="$panic_arg" QEMU_COPY_IMAGE=0 \
		QEMU_MACHINE=raspi3ap DTB_IMAGE="$dtb" OUTPUT_DIR="$output_dir" \
		"$qemu_runner" "$disk" >"$log" 2>&1 &
	qemu_pid=$!

	if wait_for_text "$log" 's21: panic marker' "$qemu_pid" 180; then
		marker_ns="$(now_ns)"
		if wait_for_second_kernel "$log" "$qemu_pid" 120; then
			reset_ns="$(now_ns)"
			reset_seen=yes
			marker_to_reset="$(python3 - "$marker_ns" "$reset_ns" <<'PY'
import sys
print(f"{(int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000:.6f}")
PY
)"
			if wait_for_second_boot_ready "$log" "$qemu_pid" 120
			then
				ready=yes
				if [[ "$mode" == R1 ]]; then
					if wait_for_pstore_collection "$log" "$qemu_pid" 120; then
						pstore_complete=yes
					else
						note=pstore-collection-timeout
					fi
				fi
			fi
		else
			marker_to_reset=
			note=second-kernel-timeout
		fi
	else
		marker_ns=
		reset_ns=
		marker_to_reset=
		note=panic-marker-timeout
	fi

	if grep -aFq 'Kernel panic' "$log"; then panic_seen=yes; fi
	if grep -aFq 'Rebooting in 5 seconds' "$log"; then reboot_seen=yes; fi
	if grep -aFq 'ramoops: using 0x100000@0x1f000000' "$log"; then
		registration=yes
	fi
	pstore_status="$(tr -d '\000' <"$log" | sed -n \
		's/.*s21: pstore mount status=\([^ ]*\).*/\1/p' | tail -n 1)"
	pstore_files="$(tr -d '\000' <"$log" | sed -n \
		's/.*s21: pstore file=\([^ ]*\).*/\1/p' | paste -sd ';' -)"
	if tr -d '\000' <"$log" | grep -F 's21: record=' |
		grep -F 'sysrq: Trigger a crash' >/dev/null
	then
		record_sysrq=yes
	fi
	if tr -d '\000' <"$log" | grep -F 's21: record=' |
		grep -F 'Kernel panic' >/dev/null
	then
		record_panic=yes
	fi

	if [[ "$ready" == yes && "$reset_seen" == yes ]]; then
		valid=1
		case "$mode" in
			P0)
				if awk -v value="$marker_to_reset" 'BEGIN {exit !(value >= 8 && value <= 30)}' &&
					[[ "$reboot_seen" == no ]]
				then
					criteria=pass
				fi
				;;
			P1)
				if awk -v value="$marker_to_reset" 'BEGIN {exit !(value >= 3 && value <= 10)}' &&
					[[ "$reboot_seen" == yes ]]
				then
					criteria=pass
				fi
				;;
			R0)
				if awk -v value="$marker_to_reset" 'BEGIN {exit !(value >= 3 && value <= 10)}' &&
					[[ "$reboot_seen" == yes && "$record_sysrq" == no &&
						"$record_panic" == no ]]
				then
					criteria=pass
				fi
				;;
			R1)
				if awk -v value="$marker_to_reset" 'BEGIN {exit !(value >= 3 && value <= 10)}' &&
					[[ "$pstore_complete" == yes && "$reboot_seen" == yes && "$registration" == yes &&
						"$record_sysrq" == yes && "$record_panic" == yes ]]
				then
					criteria=pass
				fi
				;;
		esac
	fi
	if [[ -n "$qemu_pid" ]] && kill -0 "$qemu_pid" 2>/dev/null; then
		kill -TERM "$qemu_pid" 2>/dev/null || true
	fi
	if wait "$qemu_pid"; then exit_status=0; else exit_status=$?; fi
	if [[ "$criteria" != pass ]]; then
		note="${note:+${note};}qemu_exit=${exit_status}"
	fi

	python3 "$append_row" "$csv" \
		"run_id=${run_id}" "condition=${condition}" "trial=${trial}" \
		"image_variant=${variant}" "rootfs_sha256=$(sha256_file "$rootfs")" \
		"sdcard_sha256=${image_hash}" \
		"sdcard_after_sha256=$(sha256_file "$disk")" \
		"dtb_sha256=$(sha256_file "$dtb")" "cmdline=${cmdline}" \
		"qemu_watchdog=1" "ready=${ready}" "panic_triggered=${panic_seen}" \
		"panic_message=${panic_seen}" "reboot_message=${reboot_seen}" \
		"marker_to_reset_seconds=${marker_to_reset}" \
		"reset_source=$([[ "$mode" == P0 ]] && printf watchdog || printf panic)" \
		"second_boot_ready=${ready}" "ramoops_registration=${registration}" \
		"pstore_mount_status=${pstore_status:-missing}" \
		"pstore_files=${pstore_files}" \
		"ramoops_record_sysrq=${record_sysrq}" \
		"ramoops_record_panic=${record_panic}" \
		"valid=${valid}" "criteria_result=${criteria}" \
		"log_sha256=$(sha256_file "$log")" \
		"note=${note:-reset_seen=${reset_seen};run=${run_id}}"
	printf '%s reset=%s delta=%s reboot=%s ready=%s ramoops=%s sysrq_record=%s panic_record=%s criteria=%s\n' \
		"$mode" "$reset_seen" "${marker_to_reset:-missing}" "$reboot_seen" \
		"$ready" "$registration" "$record_sysrq" "$record_panic" "$criteria"
}

for mode in "${modes[@]}"; do
	for trial in 1 2 3 4 5; do
		run_trial "$mode" "$trial"
	done
done
