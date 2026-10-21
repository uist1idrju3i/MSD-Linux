#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd -P)"
append_row="${script_dir}/append-row.py"
powerfail_repo="${S21_POWERFAIL_REPO:?set S21_POWERFAIL_REPO to the isolated test-powerfail worktree}"
output_dir="${OUTPUT_DIR:-${repo_root}/output}"
log_root="${S21_LOG_ROOT:-${QEMU_LOG_DIR:-${HOME}/work/s21-logs}}"
variant_root="${S21_VARIANT_ROOT:-${log_root}/variants}"
csv="${S21_CSV:-${repo_root}/docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.csv}"
[[ -d "$powerfail_repo/.git" || -f "$powerfail_repo/.git" ]]

sha256_file() {
	sha256sum "$1" | awk '{print $1}'
}

prepare_staging_output() {
	local variant="$1"
	local stage="${log_root}/powerfail-staging/${variant}"
	local images="${stage}/images"
	local base_images="${output_dir}/images"
	[[ ! -e "$stage" ]] || {
		printf 'Refusing to overwrite %s\n' "$stage" >&2
		exit 1
	}
	mkdir -p "$images" "$stage/host/bin" "$stage/host/sbin"
	for tool in dtc fdtoverlay mksquashfs unsquashfs; do
		cp --reflink=auto "${output_dir}/host/bin/${tool}" \
			"$stage/host/bin/${tool}"
	done
	cp --reflink=auto "${output_dir}/host/sbin/sfdisk" \
		"$stage/host/sbin/sfdisk"
	for image in Image bcm2710-rpi-cm0.dtb; do
		cp --reflink=auto "${base_images}/${image}" "$images/${image}"
	done
	cp --reflink=auto "${variant_root}/${variant}/rootfs.squashfs" \
		"$images/rootfs.squashfs"
	sha256sum "$stage"/host/bin/* "$stage/host/sbin/sfdisk" \
		"$images"/Image "$images"/bcm2710-rpi-cm0.dtb \
		"$images"/rootfs.squashfs >"$stage/support.sha256"
	printf '%s\n' "$stage"
}

run_variant() {
	local variant="$1"
	local expected_remount="$2"
	local stage trial run_id run_log test_log exit_status
	local metric_csv work_dir metric status event remount marker fsck recovery
	local target_delay actual_delay remount_delta firstboot reboot_wall total_wall
	local template_hash rootfs_hash card_hash log_hash criteria valid note
	local first_log sysctl_values running_sysctl template_path template_dir
	local parsed ready

	stage="$(prepare_staging_output "$variant")"
	for trial in 1 2 3 4 5; do
		run_log="${log_root}/s21-${variant}-powerfail-${trial}"
		mkdir -p "$run_log"
		test_log="${run_log}/test-powerfail.log"
		exit_status=0
		if OUTPUT_DIR="$stage" QEMU_LOG_DIR="$log_root" \
			QEMU_MACHINE=raspi3ap \
			"$powerfail_repo/docker/msd-dev" \
			bash -c "export POWERFAIL_IMAGE=\"\$1\"; exec board/cardputerzero/qemu/test-powerfail.sh --integrity" \
			s21 "${variant_root}/${variant}/sdcard.img" \
			>"$test_log" 2>&1
		then
			exit_status=0
		else
			exit_status=$?
		fi
		run_id="$(sed -n 's/^run=\([^ ]*\) .*/\1/p' "$test_log" | tail -n 1)"
		[[ -n "$run_id" ]] ||
			run_id="s21-${variant}-powerfail-${trial}-failed-$(date -u +%Y%m%dT%H%M%SZ)"
		metric_csv="${powerfail_repo}/docs/experiments/2026-10-20-qemu-powerfail-gpio6.csv"
		parsed=1
		if metric="$(python3 - "$metric_csv" "$run_id" <<'PY'
import csv
import sys

path, wanted = sys.argv[1:]
with open(path, encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream))
selected = [row for row in rows if row["run_id"] == wanted]
if not selected:
    raise SystemExit(f"no powerfail CSV rows for {wanted}")
for row in selected:
    for key, value in row.items():
        if value is None:
            raise SystemExit(f"missing CSV value in {wanted}: {key}")
print("\t".join(f"{row['metric']}={row['value']}" for row in selected))
PY
		)"; then
			:
		else
			metric=
			parsed=0
		fi
		status="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^status=/) {sub(/^status=/,"",$i); print $i}}' <<<"$metric")"
		event="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^event_logged=/) {sub(/^event_logged=/,"",$i); print $i}}' <<<"$metric")"
		remount="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^remount_seen=/) {sub(/^remount_seen=/,"",$i); print $i}}' <<<"$metric")"
		marker="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^marker_present_after_reboot=/) {sub(/^marker_present_after_reboot=/,"",$i); print $i}}' <<<"$metric")"
		target_delay="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^target_delay_seconds=/) {sub(/^target_delay_seconds=/,"",$i); print $i}}' <<<"$metric")"
		actual_delay="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^gpio_low_to_kill_seconds=/) {sub(/^gpio_low_to_kill_seconds=/,"",$i); print $i}}' <<<"$metric")"
		remount_delta="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^remount_from_event_seconds=/) {sub(/^remount_from_event_seconds=/,"",$i); print $i}}' <<<"$metric")"
		fsck="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^fsck_exit_status=/) {sub(/^fsck_exit_status=/,"",$i); print $i}}' <<<"$metric")"
		recovery="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^fs_recovery_messages=/) {sub(/^fs_recovery_messages=/,"",$i); print $i}}' <<<"$metric")"
		firstboot="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^firstboot_wall_seconds=/) {sub(/^firstboot_wall_seconds=/,"",$i); print $i}}' <<<"$metric")"
		reboot_wall="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^reboot_verify_wall_seconds=/) {sub(/^reboot_verify_wall_seconds=/,"",$i); print $i}}' <<<"$metric")"
		total_wall="$(awk -F '\t' '{for (i=1;i<=NF;i++) if ($i ~ /^total_wall_seconds=/) {sub(/^total_wall_seconds=/,"",$i); print $i}}' <<<"$metric")"
		template_path="$(sed -n \
			's/^Test-only S3 hooks installed in \(.*\)$/\1/p' \
			"$test_log" | tail -n 1)"
		template_hash=missing
		rootfs_hash="$(sha256_file "${variant_root}/${variant}/rootfs.squashfs")"
		work_dir=
		if [[ -n "$template_path" ]]; then
			template_dir="$(basename "$(dirname "$template_path")")"
			work_dir="${powerfail_repo}/output/qemu-powerfail/${template_dir}"
		fi
		if [[ -f "${work_dir}/sdcard-powerfail.img" ]]; then
			template_hash="$(sha256_file "${work_dir}/sdcard-powerfail.img")"
			rootfs_hash="$(sha256_file "${work_dir}/rootfs-powerfail.squashfs")"
			mkdir -p "${run_log}/build-logs"
			find "$work_dir" -maxdepth 1 -type f -name '*.log' \
				-exec cp -t "${run_log}/build-logs" {} +
		fi
		card_hash="$(sha256_file "${variant_root}/${variant}/sdcard.img")"
		first_log="${log_root}/powerfail/${run_id}/firstboot.log"
		sysctl_values=
		running_sysctl=missing
		ready=no
		if [[ -f "$first_log" ]]; then
			sysctl_values="$(sed -n \
				's/.*s21: sysctl key=\([^ ]*\) value=\(.*\) status=\([0-9][0-9]*\)$/\1=\2(status=\3)/p' \
				"$first_log" | paste -sd ';' -)"
			if grep -Fq 'Running sysctl: OK' "$first_log"; then
				running_sysctl=OK
			fi
			if grep -Fq 'MSD/Linux ready' "$first_log"; then
				ready=yes
			fi
		fi
		log_hash="serial=$(find "$log_root/powerfail/$run_id" -maxdepth 1 -type f -name '*.log' -exec sha256sum {} \; | awk '{printf "%s%s",$1,(NR==1?"":";")}')"
		log_hash="${log_hash};runner=$(sha256_file "$test_log")"
		valid=0
		criteria=fail
		if [[ "$parsed" == 1 && "$status" == ok ]]; then
			valid=1
		fi
		if [[ "$valid" == 1 && "$variant" == Y1 && "$expected_remount" == yes &&
			"$event" == yes && "$remount" == yes && "$marker" == yes &&
			"$fsck" == 0 && "$recovery" == no && "$exit_status" == 0 &&
			"$running_sysctl" == OK ]]
		then
			criteria=pass
		elif [[ "$valid" == 1 && "$variant" == Y2 && "$expected_remount" == no &&
			"$event" == yes && "$remount" == no &&
			"$exit_status" -ne 0 ]]
		then
			criteria=expected-negative
		fi
		note="powerfail_run=${run_id};template_sdcard_sha256=${template_hash};log=s21-${variant}-powerfail-${trial}"
		python3 "$append_row" "$csv" \
			"run_id=s21-${variant}-powerfail-${trial}" \
			"condition=${variant}-powerfail" "trial=${trial}" \
			"image_variant=${variant}" "rootfs_sha256=${rootfs_hash}" \
			"sdcard_sha256=${card_hash}" \
			"dtb_sha256=$(sha256_file "${output_dir}/images/bcm2710-rpi-cm0.dtb")" \
			"sysctl_readbacks=${sysctl_values}" \
			"running_sysctl=${running_sysctl}" \
			"qemu_watchdog=0" "ready=${ready}" \
			"cmdline=msd.s3bench=1 msd.s3cut=1 msd.powerfail=1" \
			"powerfail_exit_status=${exit_status}" \
			"powerfail_status=${status}" \
			"powerfail_target_delay_seconds=${target_delay}" \
			"powerfail_gpio_low_to_kill_seconds=${actual_delay}" \
			"powerfail_event=${event}" "powerfail_sysrq_u_remount=${remount}" \
			"powerfail_remount_from_event_seconds=${remount_delta}" \
			"powerfail_marker_after_reboot=${marker}" \
			"powerfail_fsck_exit_status=${fsck}" \
			"powerfail_fs_recovery=${recovery}" \
			"powerfail_firstboot_wall_seconds=${firstboot}" \
			"powerfail_reboot_verify_wall_seconds=${reboot_wall}" \
			"powerfail_total_wall_seconds=${total_wall}" \
			"valid=${valid}" "criteria_result=${criteria}" \
			"log_sha256=${log_hash}" "note=${note}"
		printf '%s trial=%s exit=%s status=%s event=%s remount=%s marker=%s criteria=%s\n' \
			"$variant" "$trial" "$exit_status" "$status" "$event" \
			"$remount" "$marker" "$criteria"
		if ((trial < 5)); then
			sleep 1
		fi
	done
}

run_variant Y1 yes
run_variant Y2 no
