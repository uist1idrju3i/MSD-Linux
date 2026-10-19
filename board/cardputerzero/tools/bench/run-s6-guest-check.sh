#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../" && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/output}"
LOG_DIR="${2:-${OUTPUT_DIR}/bench/s6-guest-check}"
OVERLAY_DIR="${REPO_ROOT}/board/cardputerzero/rootfs-overlay"
HOOK_PATH="${OVERLAY_DIR}/etc/init.d/S97msd-s6-hardening-check"
UNSIGNED_MODULE_PATH="${OVERLAY_DIR}/usr/lib/msd-hardening/usbnet-unsigned.ko"
MODULE_PATH=

if [ ! -d "${OUTPUT_DIR}/target/lib/modules" ]; then
	printf 'Buildroot module tree is missing: %s\n' "${OUTPUT_DIR}/target/lib/modules" >&2
	exit 1
fi
if [ -e "$HOOK_PATH" ] || [ -e "$UNSIGNED_MODULE_PATH" ]; then
	printf 'Refusing to overwrite an existing local overlay file.\n' >&2
	exit 1
fi

MODULE_PATH="$(find "${OUTPUT_DIR}/target/lib/modules" -type f \
	-path '*/kernel/drivers/net/usb/usbnet.ko.xz' -print -quit)"
if [ -z "$MODULE_PATH" ]; then
	printf 'usbnet.ko.xz is missing from %s\n' "${OUTPUT_DIR}/target/lib/modules" >&2
	exit 1
fi

cleanup() {
	rm -f "$HOOK_PATH" "$UNSIGNED_MODULE_PATH"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

mkdir -p "$LOG_DIR"
install -D "$SCRIPT_DIR/S97msd-s6-hardening-check" "$HOOK_PATH"
python3 "$SCRIPT_DIR/strip-module-signature.py" "$MODULE_PATH" "$UNSIGNED_MODULE_PATH"

env -u BASH_ENV make -C "$OUTPUT_DIR" -j2
"$REPO_ROOT/board/cardputerzero/tools/check-modules-dep.sh" "$OUTPUT_DIR/target"

for slot in boot ab; do
	if [ "$slot" = boot ]; then
		root_device=mmcblk0p5
	else
		root_device=mmcblk0p6
	fi
	slot_log_dir="${LOG_DIR}/${root_device}"
	mkdir -p "$slot_log_dir"
	export OUTPUT_DIR
	export KERNEL_IMAGE="${OUTPUT_DIR}/images/Image"
	export DTB_IMAGE="${OUTPUT_DIR}/images/bcm2710-rpi-3-b.dtb"
	export QEMU_EXTRA_APPEND='msd.s6check=1'
	export QEMU_LOG_DIR="$slot_log_dir"
	"$REPO_ROOT/board/cardputerzero/qemu/test-${slot}.sh"

	serial_log="${slot_log_dir}/serial-${root_device}.log"
	for marker in \
		'ptrace_scope=1' \
		'unsigned usbnet rejected (key/signature)' \
		'signed usbnet loaded via modprobe and shown by lsmod'; do
		if ! grep -Fq "$marker" "$serial_log"; then
			printf 'Missing guest-check marker "%s" in %s\n' "$marker" "$serial_log" >&2
			exit 1
		fi
	done
	if ! grep -F 'LSM: initializing lsm=' "$serial_log" | grep -Eq '(^|,)yama([,[:space:]]|$)'; then
		printf 'Yama is absent from LSM initialization in %s\n' "$serial_log" >&2
		exit 1
	fi
done
