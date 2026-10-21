#!/bin/bash
# Usage (inside docker/msd-dev): run-probe.sh VARIANT_DIR LOG_PREFIX [TIMEOUT]
# Boot 1 creates probe files; boot 2 (same image) checks them. QEMU raspi
# cannot reboot in place because bcm2835_wdt is blacklisted.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
export OUTPUT_DIR
vdir="$1"; prefix="$2"; timeout_s="${3:-900}"
img="$(mktemp -p "$vdir" run-XXXX.img)"
cp --sparse=always "$vdir/sdcard.img" "$img"
boot() {
	local log="$1" marker="$2" start pid result=timeout
	QEMU_COPY_IMAGE=0 DTB_IMAGE="${OUTPUT_DIR}/images/bcm2710-rpi-cm0.dtb" \
		"${REPO_ROOT}/board/cardputerzero/qemu/run-qemu.sh" "$img" </dev/null >"$log" 2>&1 &
	pid=$!
	start=$(date +%s)
	while kill -0 "$pid" 2>/dev/null; do
		if grep -aFq "$marker" "$log"; then result=finished; break; fi
		(( $(date +%s) - start > timeout_s )) && break
		sleep 2
	done
	sleep 1
	kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
	echo "$(basename "$log") result=$result elapsed=$(( $(date +%s) - start ))"
}
boot "${prefix}.boot1.log" '=noexec= stage1-done'
boot "${prefix}.boot2.log" '=noexec= finished'
rm -f "$img"
