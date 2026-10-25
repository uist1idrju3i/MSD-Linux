#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT
export QEMU_LOG_DIR="${TEST_DIR}/logs"
# shellcheck source=board/cardputerzero/qemu/test-powerfail.sh
source "${REPO_ROOT}/board/cardputerzero/qemu/test-powerfail.sh"

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

expect() {
	local name="$1" expected="$2"
	local actual
	actual="$(printf '%s %s %s %s %s [%s] [%s]' "$CLASS_EVENT" "$CLASS_SYSRQ_U" \
		"$CLASS_REMOUNT" "$CLASS_MARKER" "$CLASS_RECOVERY" \
		"$CLASS_FSCK_STATUS" "$CLASS_EVENT_TO_REMOUNT")"
	[[ "$actual" == "$expected" ]] || fail "${name}: expected '${expected}', got '${actual}'"
	printf 'ok - %s\n' "$name"
}

# Lines copied from an S21 integrity trial; the event marker follows the remount there.
first="${TEST_DIR}/firstboot.log"
reboot="${TEST_DIR}/reboot.log"
printf '%s\n' \
	'[   84.789792] powerfail-suo powerfail: SysRq U: emergency remount filesystems readonly' \
	'[   84.791470] sysrq: Emergency Remount R/O' \
	'[   85.029678] msd-powerfail: power-fail event received' >"$first"
printf '%s\n' 'S3CUT_FSCK_STATUS=0' 'S3CUT_MARKER_PRESENT=1' 'S3CUT_VERIFY_PASS' >"$reboot"
classify_trial_logs "$first" "$reboot"
expect 'S21 trial logs' 'yes yes yes yes no [0] [-0.238208]'

sed -i 's/$/\r/' "$first" "$reboot"
classify_trial_logs "$first" "$reboot"
expect 'CRLF serial logs' 'yes yes yes yes no [0] [-0.238208]'

printf '%s\n' \
	'[   84.789792] powerfail-suo powerfail: SysRq U: emergency remount filesystems readonly' \
	'[   85.029678] msd-powerfail: power-fail event received' >"$first"
classify_trial_logs "$first" "$reboot"
expect 'SysRq U requested without the remount line' 'yes yes no yes no [0] []'

: >"$first"
classify_trial_logs "$first" "${TEST_DIR}/missing.log"
expect 'no event and no reboot log' 'no no no no no [] []'

printf '%s\n' \
	'S3CUT_FSCK_STATUS=1' \
	'[    3.100000] EXT4-fs (mmcblk0p7): recovery complete' \
	'S3CUT_FSCK_STATUS=0' >"$reboot"
classify_trial_logs "$first" "$reboot"
expect 'journal recovery and last fsck status' 'no no no no yes [0] []'

printf '%s\n' '/dev/mmcblk0p7: recovering journal' >"$reboot"
classify_trial_logs "$first" "$reboot"
expect 'e2fsck journal recovery' 'no no no no yes [] []'

printf '%s\n' 'S3CUT_MARKER_PRESENT=0' >"$reboot"
classify_trial_logs "$first" "$reboot"
expect 'marker absent after reboot' 'no no no no no [] []'
