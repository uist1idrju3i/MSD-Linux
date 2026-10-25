#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
IMAGES_DIR="${OUTPUT_DIR}/images"
LOG_ROOT="${QEMU_LOG_DIR:-${REPO_ROOT}/output/qemu-logs}"
LOG_DIR="${LOG_ROOT}/powerfail"
WORK_ROOT="${REPO_ROOT}/output/qemu-powerfail"
QEMU_MACHINE="${QEMU_MACHINE:-raspi3ap}"
POWERFAIL_IMAGE="${POWERFAIL_IMAGE:-${IMAGES_DIR}/sdcard.img}"
KERNEL="${KERNEL_IMAGE:-${IMAGES_DIR}/Image}"
QEMU_GPIO_PATH="${QEMU_GPIO_PATH:-/machine/soc/peripherals/gpio}"
CURRENT_PID=""
COMPOSED_DTB=""
TEST_TEMPLATE=""
CSV_DIR="${REPO_ROOT}/docs/experiments"
CSV_BASENAME='2026-10-20-qemu-powerfail-gpio6.csv'
CSV_FILE="${CSV_FILE:-${CSV_DIR}/${CSV_BASENAME}}"

case "$QEMU_MACHINE" in
	raspi3b)
		default_dtb=bcm2710-rpi-3-b.dtb
		;;
	raspi3ap)
		default_dtb=bcm2710-rpi-cm0.dtb
		;;
	*)
		printf 'Unsupported QEMU_MACHINE: %s\n' "$QEMU_MACHINE" >&2
		exit 2
		;;
esac
BASE_DTB="${DTB_IMAGE:-${IMAGES_DIR}/${default_dtb}}"

usage() {
	printf 'Usage: %s [--smoke|--integrity|--experiment]\n' "$0" >&2
}

terminate_qemu() {
	local signal="${1:-TERM}"

	if [[ -n "$CURRENT_PID" ]]; then
		if kill -0 "$CURRENT_PID" 2>/dev/null; then
			kill -s "$signal" "$CURRENT_PID" 2>/dev/null || true
		fi
		wait "$CURRENT_PID" 2>/dev/null || true
		CURRENT_PID=""
	fi
}

prepare_overlay() {
	local dtc="${OUTPUT_DIR}/host/bin/dtc"
	local fdtoverlay="${OUTPUT_DIR}/host/bin/fdtoverlay"
	local overlay="${SCRIPT_DIR}/powerfail-qemu-overlay.dts"
	local overlay_log="${WORK_ROOT}/overlay-build.log"

	if [[ ! -x "$dtc" || ! -x "$fdtoverlay" ]]; then
		printf 'Buildroot host dtc/fdtoverlay are required under %s/host/bin\n' \
			"$OUTPUT_DIR" >&2
		return 1
	fi

	COMPOSED_DTB="${WORK_ROOT}/powerfail-${QEMU_MACHINE}.dtb"
	"$dtc" -@ -I dts -O dtb -o "${WORK_ROOT}/powerfail-qemu-overlay.dtbo" \
		"${overlay}" >"$overlay_log" 2>&1
	"$fdtoverlay" -i "$BASE_DTB" -o "$COMPOSED_DTB" \
		"${WORK_ROOT}/powerfail-qemu-overlay.dtbo" >>"$overlay_log" 2>&1
}

wait_for_text() {
	local log="$1"
	local text="$2"
	local pid="$3"
	local timeout="$4"
	local deadline=$((SECONDS + timeout))

	while ((SECONDS <= deadline)); do
		if [[ -f "$log" ]] && grep -Fq -- "$text" "$log"; then
			return 0
		fi
		if ! kill -0 "$pid" 2>/dev/null; then
			printf 'QEMU exited while waiting for %s; log=%s\n' \
				"$text" "$log" >&2
			return 1
		fi
		sleep 0.1
	done

	printf 'Timed out waiting for %s; log=%s\n' "$text" "$log" >&2
	return 1
}

start_qemu() {
	local disk="$1"
	local log="$2"
	local qmp_socket="$3"
	local append="$4"
	local copy_image="$5"

	rm -f "$qmp_socket"
	QEMU_COPY_IMAGE="$copy_image" \
	QEMU_QMP_SOCKET="$qmp_socket" \
	QEMU_EXTRA_APPEND="$append" \
	QEMU_MACHINE="$QEMU_MACHINE" \
	DTB_IMAGE="$COMPOSED_DTB" \
	OUTPUT_DIR="$OUTPUT_DIR" \
	"$SCRIPT_DIR/run-qemu.sh" "$disk" >"$log" 2>&1 &
	CURRENT_PID=$!
}

now_ns() {
	python3 -c 'import time; print(time.time_ns())'
}

monotonic_ns() {
	python3 -c 'import time; print(time.monotonic_ns())'
}

seconds_between() {
	python3 - "$1" "$2" <<'PY'
import sys
print(f"{(int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000:.6f}")
PY
}

log_timestamp() {
	python3 - "$1" "$2" <<'PY'
import re
import sys

path, marker = sys.argv[1:]
with open(path, encoding="utf-8", errors="replace") as log:
    for line in log:
        if marker in line:
            match = re.search(r"\[\s*(\d+(?:\.\d+)?)\]", line)
            if match:
                print(match.group(1))
                break
PY
}

# Derives the per-trial verdicts from the saved serial logs; tests/powerfail-log covers it.
classify_trial_logs() {
	local first_log="$1"
	local reboot_log="$2"
	local event=no sysrq_u_requested=no remount=no marker=no recovery=no
	local fsck_status="" event_time="" remount_time="" event_to_remount=""

	if grep -Fq -- 'msd-powerfail: power-fail event received' "$first_log"; then
		event=yes
	fi
	if grep -Fq -- 'SysRq U: emergency remount filesystems readonly' "$first_log"; then
		sysrq_u_requested=yes
	fi
	if grep -Fq -- 'sysrq: Emergency Remount R/O' "$first_log"; then
		remount=yes
	fi
	if [[ -f "$reboot_log" ]] &&
		grep -Fq -- 'S3CUT_MARKER_PRESENT=1' "$reboot_log"; then
		marker=yes
	fi
	if [[ -f "$reboot_log" ]] &&
		grep -Eiq 'EXT4-fs.*(recover|orphan)|recovering journal|recovery complete' \
			"$reboot_log"; then
		recovery=yes
	fi
	if [[ -f "$reboot_log" ]]; then
		fsck_status="$(sed -n \
			's/.*S3CUT_FSCK_STATUS=\([0-9][0-9]*\).*/\1/p' \
			"$reboot_log" | tail -n 1)"
	fi
	if [[ -n "$first_log" && -f "$first_log" ]]; then
		event_time="$(log_timestamp "$first_log" \
			'msd-powerfail: power-fail event received')"
		remount_time="$(log_timestamp "$first_log" \
			'sysrq: Emergency Remount R/O')"
	fi
	if [[ -n "$event_time" && -n "$remount_time" ]]; then
		event_to_remount="$(python3 - "$event_time" "$remount_time" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
		)"
	fi

	CLASS_EVENT="$event"
	CLASS_SYSRQ_U="$sysrq_u_requested"
	CLASS_REMOUNT="$remount"
	CLASS_MARKER="$marker"
	CLASS_RECOVERY="$recovery"
	CLASS_FSCK_STATUS="$fsck_status"
	CLASS_EVENT_TO_REMOUNT="$event_to_remount"
}

run_smoke() {
	local run_id
	local run_dir log qmp_socket

	run_id="smoke-$(date -u +%Y%m%dT%H%M%SZ)"
	run_dir="${LOG_DIR}/${run_id}"
	log="${run_dir}/serial.log"
	qmp_socket="${run_dir}/qmp.sock"
	mkdir -p "$run_dir"
	start_qemu "$POWERFAIL_IMAGE" "$log" "$qmp_socket" "" 1
	if ! wait_for_text "$log" "MSD/Linux ready" "$CURRENT_PID" 180; then
		return 1
	fi
	python3 "${SCRIPT_DIR}/qmp-set-gpio.py" "$qmp_socket" "$QEMU_GPIO_PATH" \
		pin6 false >"${run_dir}/qmp-set.json"
	if ! wait_for_text "$log" \
		"msd-powerfail: power-fail event received" "$CURRENT_PID" 15; then
		return 1
	fi
	if ! wait_for_text "$log" \
		"SysRq U: emergency remount filesystems readonly" "$CURRENT_PID" 15; then
		return 1
	fi

	terminate_qemu TERM
	rm -f "$qmp_socket"
	"${SCRIPT_DIR}/check-serial-log.sh" "$log"
	printf 'PASS: GPIO6 event and emergency remount; log=%s\n' "$log"
}

prepare_integrity_template() {
	local rootfs="${IMAGES_DIR}/rootfs.squashfs"
	local unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
	local mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
	local sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"
	local build_dir target_dir rootfs_test image_template
	local squashfs_info compression block_size partition_info
	local root_a_start root_a_size root_b_start root_b_size rootfs_bytes
	local image_size padded_size
	local unsquash_status=0

	build_dir="${WORK_ROOT}/integrity-$(date -u +%Y%m%dT%H%M%SZ)"
	target_dir="${build_dir}/target"
	rootfs_test="${build_dir}/rootfs-powerfail.squashfs"
	image_template="${build_dir}/sdcard-powerfail.img"
	for required in "$rootfs" "$unsquashfs" "$mksquashfs" "$sfdisk"; do
		if [[ ! -x "$required" && ! -f "$required" ]]; then
			printf 'Required test-image tool or input not found: %s\n' \
				"$required" >&2
			return 1
		fi
	done

	mkdir -p "$build_dir"
	"$unsquashfs" -no-progress -no-xattrs -d "$target_dir" "$rootfs" \
		>"${build_dir}/unsquashfs.log" 2>&1 || unsquash_status=$?
	if ((unsquash_status != 0)); then
		if ((unsquash_status != 2)) ||
			! grep -Fq 'failed to change uid and gids' \
				"${build_dir}/unsquashfs.log"; then
			cat "${build_dir}/unsquashfs.log" >&2
			return 1
		fi
	fi
	install -D -m 0755 "${REPO_ROOT}/board/cardputerzero/tools/bench/s3/S02zz-s3verify" \
		"${target_dir}/etc/init.d/S02zz-s3verify"
	install -D -m 0755 "${REPO_ROOT}/board/cardputerzero/tools/bench/s3/S06msd-s3bench" \
		"${target_dir}/etc/init.d/S06msd-s3bench"

	squashfs_info="$("$unsquashfs" -s "$rootfs")"
	compression="$(awk '$1 == "Compression" { print $2; exit }' \
		<<<"$squashfs_info")"
	block_size="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' \
		<<<"$squashfs_info")"
	if [[ -z "$compression" || -z "$block_size" ]]; then
		printf 'Could not read SquashFS options from %s\n' "$rootfs" >&2
		return 1
	fi
	"$mksquashfs" "$target_dir" "$rootfs_test" -noappend -all-root \
		-no-xattrs -no-progress -comp "$compression" -b "$block_size" \
		>"${build_dir}/mksquashfs.log" 2>&1

	cp --reflink=auto --sparse=always "$POWERFAIL_IMAGE" "$image_template"
	image_size="$(stat -c '%s' "$image_template")"
	padded_size=1
	while ((padded_size < image_size)); do
		padded_size=$((padded_size * 2))
	done
	truncate -s "$padded_size" "$image_template"

	partition_info="$("$sfdisk" --json "$image_template" | python3 -c '
import json
import sys

partitions = json.load(sys.stdin)["partitiontable"]["partitions"]
if len(partitions) != 7:
    raise SystemExit(f"expected 7 partitions, found {len(partitions)}")
for number in (5, 6):
    partition = partitions[number - 1]
    print(partition["start"], partition["size"], end=" ")
')"
	read -r root_a_start root_a_size root_b_start root_b_size \
		<<<"$partition_info"
	rootfs_bytes="$(stat -c '%s' "$rootfs_test")"
	if ((rootfs_bytes > root_a_size * 512 || rootfs_bytes > root_b_size * 512)); then
		printf 'Test SquashFS does not fit in rootfs A/B partitions.\n' >&2
		return 1
	fi
	dd if="$rootfs_test" of="$image_template" bs=512 \
		seek="$root_a_start" conv=notrunc status=none
	dd if="$rootfs_test" of="$image_template" bs=512 \
		seek="$root_b_start" conv=notrunc status=none

	TEST_TEMPLATE="$image_template"
	printf 'Test-only S3 hooks installed in %s\n' "$TEST_TEMPLATE"
}

csv_row() {
	local run_id="$1"
	local variant="$2"
	local repeat="$3"
	local metric="$4"
	local value="$5"
	local unit="$6"
	local valid="$7"
	local note="${8//,/;}"

	if [[ ! -e "$CSV_FILE" ]]; then
		printf 'run_id,variant,repeat,metric,value,unit,valid,note\n' >"$CSV_FILE"
	fi
	printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
		"$run_id" "$variant" "$repeat" "$metric" "$value" "$unit" \
		"$valid" "$note" >>"$CSV_FILE"
}

run_integrity_trial() {
	local run_id="$1"
	local variant="$2"
	local repeat="$3"
	local target_delay="$4"
	local control="$5"
	local run_dir="${LOG_DIR}/${run_id}"
	local disk="${run_dir}/sdcard.img"
	local first_log="${run_dir}/firstboot.log"
	local reboot_log="${run_dir}/reboot.log"
	local qmp_socket="${run_dir}/qmp.sock"
	local start_wall_ns firstboot_done_ns reboot_start_ns reboot_done_ns
	local gpio_response_ns="" cut_start_ns="" kill_ns="" qmp_result=""
	local failure="" event_to_remount=""
	local firstboot_wall="" reboot_wall="" total_wall=""
	local recovery=no fsck_status="" marker=no event=no remount=no
	local sysrq_u_requested=no
	local status=ok

	TRIAL_ACTUAL_DELAY=""
	TRIAL_STATUS=""
	TRIAL_EVENT=no
	TRIAL_REMOUNT=no
	TRIAL_MARKER=no
	TRIAL_FSCK_STATUS=""
	TRIAL_RECOVERY=no
	TRIAL_FAILURE=""

	if [[ -e "$run_dir" ]]; then
		printf 'Refusing to overwrite powerfail log directory %s\n' \
			"$run_dir" >&2
		return 1
	fi
	if [[ -f "$CSV_FILE" ]] &&
		awk -F, -v id="$run_id" '$1 == id { found=1 } END { exit !found }' \
			"$CSV_FILE"
	then
		printf 'Refusing to append existing run ID %s to %s\n' \
			"$run_id" "$CSV_FILE" >&2
		return 1
	fi

	mkdir -p "$run_dir"
	start_wall_ns="$(now_ns)"
	cp --reflink=auto --sparse=always "$TEST_TEMPLATE" "$disk"
	start_qemu "$disk" "$first_log" "$qmp_socket" \
		"msd.s3bench=1 msd.s3cut=1 msd.powerfail=1" 0
	if ! wait_for_text "$first_log" "MSD/Linux ready" "$CURRENT_PID" 180; then
		failure=firstboot-ready-timeout
	elif ! wait_for_text "$first_log" "S3CUT_MARKER_WRITTEN=1" \
		"$CURRENT_PID" 30; then
		failure="marker-write-missing"
	elif ! wait_for_text "$first_log" "S3CUT_C_START" "$CURRENT_PID" 30; then
		failure=s3-start-missing
	fi

	if [[ -z "$failure" ]]; then
		if [[ "$control" == yes ]]; then
			cut_start_ns="$(monotonic_ns)"
			sleep "$target_delay"
		else
			if qmp_result="$(python3 "${SCRIPT_DIR}/qmp-set-gpio.py" \
				"$qmp_socket" "$QEMU_GPIO_PATH" pin6 false)"; then
				gpio_response_ns="$(python3 -c \
					'import json,sys; print(json.load(sys.stdin)["response_ns"])' \
					<<<"$qmp_result")"
				sleep "$target_delay"
			else
				failure=qmp-set-failed
			fi
		fi
	fi

	if [[ -n "$CURRENT_PID" ]]; then
		if kill -0 "$CURRENT_PID" 2>/dev/null; then
			kill -KILL "$CURRENT_PID" 2>/dev/null || true
			kill_ns="$(monotonic_ns)"
		fi
		wait "$CURRENT_PID" 2>/dev/null || true
		CURRENT_PID=""
	fi
	rm -f "$qmp_socket"

	if [[ -n "$gpio_response_ns" && -n "$kill_ns" ]]; then
		TRIAL_ACTUAL_DELAY="$(seconds_between "$gpio_response_ns" "$kill_ns")"
	elif [[ -n "$cut_start_ns" && -n "$kill_ns" ]]; then
		TRIAL_ACTUAL_DELAY="$(seconds_between "$cut_start_ns" "$kill_ns")"
	else
		TRIAL_ACTUAL_DELAY=""
	fi

	firstboot_done_ns="$(now_ns)"
	firstboot_wall="$(seconds_between "$start_wall_ns" "$firstboot_done_ns")"
	reboot_start_ns="$(now_ns)"
	reboot_done_ns="$reboot_start_ns"
	if [[ -z "$failure" ]]; then
		start_qemu "$disk" "$reboot_log" "$qmp_socket" \
			"msd.s3verify=1 msd.powerfail=1" 0
		if wait_for_text "$reboot_log" "S3CUT_VERIFY_" "$CURRENT_PID" 180; then
			reboot_done_ns="$(now_ns)"
			reboot_wall="$(seconds_between "$reboot_start_ns" "$reboot_done_ns")"
		else
			failure=reboot-verifier-timeout
		fi
		terminate_qemu TERM
	else
		reboot_done_ns="$reboot_start_ns"
		reboot_wall=0
	fi
	total_wall="$(seconds_between "$start_wall_ns" "$reboot_done_ns")"
	if [[ -n "$failure" ]]; then
		status="failed-run"
	fi

	classify_trial_logs "$first_log" "$reboot_log"
	event="$CLASS_EVENT"
	sysrq_u_requested="$CLASS_SYSRQ_U"
	remount="$CLASS_REMOUNT"
	marker="$CLASS_MARKER"
	recovery="$CLASS_RECOVERY"
	fsck_status="$CLASS_FSCK_STATUS"
	event_to_remount="$CLASS_EVENT_TO_REMOUNT"

	TRIAL_STATUS="$status"
	TRIAL_EVENT="$event"
	TRIAL_REMOUNT="$remount"
	TRIAL_MARKER="$marker"
	TRIAL_FSCK_STATUS="$fsck_status"
	TRIAL_RECOVERY="$recovery"
	TRIAL_ACTUAL_DELAY="${TRIAL_ACTUAL_DELAY:-}"
	TRIAL_FAILURE="$failure"

	local valid=true
	local note="logs=output/qemu-logs/powerfail/${run_id}"
	if [[ "$status" == failed-run ]]; then
		valid=false
		note="${note};reason=${failure}"
	fi
	csv_row "$run_id" "$variant" "$repeat" status "$status" status "$valid" "$note"
	csv_row "$run_id" "$variant" "$repeat" target_delay_seconds \
		"$target_delay" s "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" gpio_low_to_kill_seconds \
		"$TRIAL_ACTUAL_DELAY" s "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" event_logged "$event" bool "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" remount_seen "$remount" bool "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" sysrq_u_requested \
		"$sysrq_u_requested" bool "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" remount_from_event_seconds \
		"$event_to_remount" s "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" marker_present_after_reboot \
		"$marker" bool "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" fsck_exit_status \
		"$fsck_status" code "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" fs_recovery_messages \
		"$recovery" bool "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" firstboot_wall_seconds \
		"$firstboot_wall" s "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" reboot_verify_wall_seconds \
		"$reboot_wall" s "$valid" ""
	csv_row "$run_id" "$variant" "$repeat" total_wall_seconds \
		"$total_wall" s "$valid" ""

	printf 'run=%s status=%s event=%s remount=%s sysrq_u_requested=%s marker=%s fsck=%s recovery=%s delay=%s logs=%s\n' \
		"$run_id" "$status" "$event" "$remount" "$sysrq_u_requested" \
		"$marker" "$fsck_status" "$recovery" "$TRIAL_ACTUAL_DELAY" "$run_dir"
	if [[ "$status" == ok ]]; then
		rm -f "$disk"
	fi
}

run_integrity() {
	local delay="${POWERFAIL_DELAY:-1.5}"
	local run_id

	run_id="integrity-$(date -u +%Y%m%dT%H%M%SZ)"

	prepare_integrity_template
	run_integrity_trial "$run_id" single 1 "$delay" no
	if [[ "$TRIAL_STATUS" != ok ]]; then
		printf 'Integrity trial failed to complete: %s\n' "$TRIAL_FAILURE" >&2
		return 1
	fi
	if [[ "$delay" == 1.5 || "$delay" == 5 ]] &&
		[[ "$TRIAL_EVENT" != yes || "$TRIAL_REMOUNT" != yes ||
			"$TRIAL_MARKER" != yes || "$TRIAL_FSCK_STATUS" != 0 ||
			"$TRIAL_RECOVERY" != no ]]; then
		printf 'Integrity acceptance failed; inspect the recorded logs.\n' >&2
		return 1
	fi
}

run_experiment() {
	local timestamp run_id repeat delay aa_delta
	local -a aa_times=()
	local failed=false

	prepare_integrity_template
	timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
	for repeat in 1 2; do
		run_id="${timestamp}-aa-${repeat}"
		run_integrity_trial "$run_id" aa  "$repeat" 1.5 no
		aa_times+=("$TRIAL_ACTUAL_DELAY")
		if [[ "$TRIAL_STATUS" != ok ]]; then
			failed=true
		fi
	done
	if [[ "$failed" == true || -z "${aa_times[0]}" || -z "${aa_times[1]}" ]]; then
		printf 'A/A instrument check did not complete; stopping experiment.\n' >&2
		return 1
	fi
	aa_delta="$(python3 - "${aa_times[0]}" "${aa_times[1]}" <<'PY'
import sys
print(f"{abs(float(sys.argv[1]) - float(sys.argv[2])):.6f}")
PY
	)"
	printf 'A/A actual delays: %s s, %s s; absolute difference=%s s\n' \
		"${aa_times[0]}" "${aa_times[1]}" "$aa_delta"
	if python3 - "$aa_delta" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) <= 0.05 else 1)
PY
	then
		:
	else
		printf 'A/A timing check exceeded the pre-registered 0.050000 s threshold.\n' \
			>&2
		return 1
	fi

	for delay in 0.1 0.4 0.7 1.5 5; do
		for repeat in 1 2 3 4 5; do
			run_id="${timestamp}-delay-${delay}-${repeat}"
			run_integrity_trial "$run_id" "delay-${delay}" "$repeat" "$delay" no
		done
	done
	for repeat in 1 2 3 4 5; do
		run_id="${timestamp}-control-${repeat}"
		run_integrity_trial "$run_id" control-no-gpio "$repeat" 5 yes
	done
	printf 'Experiment CSV: %s\n' "$CSV_FILE"
	printf 'A/A timing-difference threshold: 0.050000 s\n'
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
	return 0
fi

trap 'terminate_qemu TERM' EXIT
trap 'terminate_qemu INT; exit 130' INT
trap 'terminate_qemu TERM; exit 143' TERM

for required in "$POWERFAIL_IMAGE" "$KERNEL" "$BASE_DTB"; do
	if [[ ! -f "$required" ]]; then
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	fi
done

mkdir -p "$LOG_DIR" "$WORK_ROOT"
mode="${1:---integrity}"
if [[ "$#" -gt 1 ]]; then
	usage
	exit 2
fi
if ! prepare_overlay; then
	exit 1
fi

case "$mode" in
	--smoke)
		run_smoke
		;;
	--integrity)
		run_integrity
		;;
	--experiment)
		run_experiment
		;;
	*)
		usage
		exit 2
		;;
esac
