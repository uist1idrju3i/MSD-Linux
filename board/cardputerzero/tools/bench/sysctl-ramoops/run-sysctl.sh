#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../../../.." && pwd -P)"
append_row="${script_dir}/append-row.py"
output_dir="${OUTPUT_DIR:-${repo_root}/output}"
log_root="${S21_LOG_ROOT:-${QEMU_LOG_DIR:-${HOME}/work/s21-logs}}"
variant_root="${S21_VARIANT_ROOT:-${log_root}/variants}"
default_csv="${repo_root}/docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.csv"
csv="${S21_CSV:-$default_csv}"
trial_count="${S21_BOOT_TRIALS:-5}"
qemu_machine="${QEMU_MACHINE:-raspi3ap}"

[[ "$trial_count" == 5 ]] || {
	printf 'The preregistered boot count is 5; refusing %s\n' "$trial_count" >&2
	exit 2
}
[[ -d "$variant_root/Y0" && -d "$variant_root/Y1" ]]

sha256_file() {
	sha256sum "$1" | awk '{print $1}'
}

run_boot() {
	local variant="$1"
	local trial="$2"
	local root_device="${3:-/dev/mmcblk0p5}"
	local condition="Y${variant}-boot"
	local mode="test-boot"
	local device_suffix=mmcblk0p5
	local image="${variant_root}/Y${variant}/sdcard.img"
	local run_id="s21-y${variant}-boot-${trial}"
	local run_dir disk
	local serial_log test_log exit_status ready ready_seconds sysctl_values
	local running_sysctl serial_status ab_status valid criteria log_sha image_hash

	if [[ "$root_device" == /dev/mmcblk0p6 ]]; then
		condition=Y1-test-ab
		mode=test-ab
		device_suffix=mmcblk0p6
		run_id="s21-y1-test-ab-1"
	fi
	run_dir="${log_root}/${run_id}"
	disk="${run_dir}/sdcard.img"
	mkdir -p "$run_dir"
	cp --sparse=always "$image" "$disk"
	image_hash="$(sha256_file "$disk")"
	serial_log="${run_dir}/serial-${device_suffix}.log"
	test_log="${run_dir}/${mode}.log"
	exit_status=0
	if OUTPUT_DIR="$output_dir" QEMU_LOG_DIR="$run_dir" \
		QEMU_COPY_IMAGE=0 QEMU_MACHINE="$qemu_machine" \
		"${repo_root}/docker/msd-dev" \
		"board/cardputerzero/qemu/${mode}.sh" "$disk" \
		>"$test_log" 2>&1
	then
		exit_status=0
	else
		exit_status=$?
	fi

	ready=no
	ready_seconds=
	if [[ -f "$serial_log" ]] &&
		grep -Fq 'MSD/Linux ready' "$serial_log" &&
		grep -Eiq '(^|[[:space:]])msd login:|login:' "$serial_log"
	then
		ready=yes
		ready_seconds="$(sed -n \
			's/^QEMU reached ready after \([0-9][0-9]*\) seconds\..*/\1/p' \
			"$test_log" | tail -n 1)"
	fi
	sysctl_values=
	if [[ -f "$serial_log" ]]; then
		sysctl_values="$(sed -n \
			's/.*s21: sysctl key=\([^ ]*\) value=\(.*\) status=\([0-9][0-9]*\)$/\1=\2(status=\3)/p' \
			"$serial_log" | paste -sd ';' -)"
	fi
	running_sysctl=missing
	grep -Fq 'Running sysctl: OK' "$serial_log" 2>/dev/null &&
		running_sysctl=OK
	serial_status="$exit_status"
	ab_status=
	[[ "$mode" != test-ab ]] || ab_status="$exit_status"
	valid=0
	criteria=fail
	if ((exit_status == 0)) && [[ "$ready" == yes ]]; then
		valid=1
		criteria=pass
	fi
	if [[ "$variant" == Y0 ]]; then
		condition=Y0-boot
		criteria=observation
	elif [[ "$root_device" == /dev/mmcblk0p6 ]]; then
		if ((exit_status == 0)) && [[ "$ready" == yes ]]; then
			criteria=pass
		fi
	else
		if [[ "$running_sysctl" != OK ]] ||
			! python3 - "$serial_log" <<'PY'
import re
import sys

expected = {
    "kernel.kptr_restrict": "2",
    "kernel.dmesg_restrict": "1",
    "kernel.sysrq": "32",
    "fs.protected_fifos": "2",
    "fs.protected_regular": "2",
    "fs.protected_hardlinks": "1",
    "fs.protected_symlinks": "1",
    "net.core.bpf_jit_harden": "2",
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.default.accept_redirects": "0",
    "net.ipv4.conf.all.send_redirects": "0",
    "net.ipv4.conf.default.accept_source_route": "0",
    "net.ipv4.conf.all.rp_filter": "1",
    "net.ipv4.conf.all.log_martians": "1",
    "net.ipv4.conf.default.log_martians": "1",
}
observed = {}
pattern = re.compile(
    r"s21: sysctl key=([^ ]+) value=(.*?) status=([0-9]+)$"
)
with open(sys.argv[1], encoding="utf-8", errors="replace") as stream:
    for line in stream:
        match = pattern.search(line)
        if match:
            observed[match.group(1)] = (match.group(2), match.group(3))
raise SystemExit(
    0
    if all(observed.get(key) == (value, "0") for key, value in expected.items())
    else 1
)
PY
		then
			criteria=fail
		fi
	fi
	log_sha=
	if [[ -f "$serial_log" ]]; then
		log_sha="serial=$(sha256_file "$serial_log")"
	fi
	log_sha="${log_sha};runner=$(sha256_file "$test_log")"

	python3 "$append_row" "$csv" \
		"run_id=${run_id}" "condition=${condition}" "trial=${trial}" \
		"image_variant=Y${variant}" \
		"rootfs_sha256=$(sha256_file "${variant_root}/Y${variant}/rootfs.squashfs")" \
		"sdcard_sha256=${image_hash}" \
		"sdcard_after_sha256=$(sha256_file "$disk")" \
		"dtb_sha256=$(sha256_file "${output_dir}/images/bcm2710-rpi-cm0.dtb")" \
		"qemu_watchdog=0" "ready=${ready}" "ready_seconds=${ready_seconds}" \
		"sysctl_readbacks=${sysctl_values}" "running_sysctl=${running_sysctl}" \
		"serial_check_exit=${serial_status}" "ab_exit_status=${ab_status}" \
		"valid=${valid}" \
		"criteria_result=${criteria}" "log_sha256=${log_sha}" \
		"note=${run_id}/${mode}"

	printf '%s exit=%s ready=%s ready_seconds=%s sysctl=%s log=%s\n' \
		"$run_id" "$exit_status" "$ready" "${ready_seconds:-missing}" \
		"${running_sysctl}" "$run_dir"
	return 0
}

for variant in 0 1; do
	for trial in 1 2 3 4 5; do
		run_boot "$variant" "$trial"
	done
done
run_boot 1 1 /dev/mmcblk0p6
