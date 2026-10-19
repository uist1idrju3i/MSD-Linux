#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
IMAGES_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}/images"
IMAGE="${1:-${IMAGES_DIR}/sdcard.img}"
KERNEL="${KERNEL_IMAGE:-${IMAGES_DIR}/Image}"
DTB="${DTB_IMAGE:-${IMAGES_DIR}/bcm2710-rpi-3-b.dtb}"
QEMU="${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}"
ROOT_DEVICE="${ROOT_DEVICE:-/dev/mmcblk0p5}"
ROOT_FSTYPE="${ROOT_FSTYPE:-squashfs}"
QEMU_EXTRA_APPEND="${QEMU_EXTRA_APPEND:-}"
QEMU_ICOUNT="${QEMU_ICOUNT:-}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

for required in "$IMAGE" "$KERNEL" "$DTB"; do
	if [ ! -f "$required" ]; then
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	fi
done

QEMU_IMAGE="${WORK_DIR}/sdcard.img"
cp "$IMAGE" "$QEMU_IMAGE"
image_size="$(stat -c '%s' "$QEMU_IMAGE")"
padded_size=1
while [ "$padded_size" -lt "$image_size" ]; do
	padded_size=$((padded_size * 2))
done
truncate -s "$padded_size" "$QEMU_IMAGE"

append_args=(
	"earlycon=pl011,mmio32,0x3f201000"
	"console=ttyAMA1,115200"
	"initcall_blacklist=bcm2835_wdt_driver_init"
	"root=$ROOT_DEVICE"
	"rootwait"
	"ro"
	"rootfstype=$ROOT_FSTYPE"
)
if [ -n "$QEMU_EXTRA_APPEND" ]; then
	read -r -a extra_append <<< "$QEMU_EXTRA_APPEND"
	append_args+=("${extra_append[@]}")
fi
qemu_args=()
if [ -n "$QEMU_ICOUNT" ]; then
	qemu_args+=(-icount "$QEMU_ICOUNT")
fi

# The Pi 3 DTB maps the PL011 to ttyAMA1; QEMU resets when bcm2835_wdt is armed.
# Blacklist the watchdog only in QEMU; hardware watchdog behavior is unchanged.
exec "$QEMU" "${qemu_args[@]}" -M raspi3b -m 1G \
	-kernel "$KERNEL" \
	-dtb "$DTB" \
	-drive "file=${QEMU_IMAGE},if=sd,format=raw" \
	-append "${append_args[*]}" \
	-nographic -serial mon:stdio
