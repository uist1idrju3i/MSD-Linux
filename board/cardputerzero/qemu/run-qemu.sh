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

exec "$QEMU" -M raspi3b -m 1G \
	-kernel "$KERNEL" \
	-dtb "$DTB" \
	-drive "file=${QEMU_IMAGE},if=sd,format=raw" \
	-append "console=ttyAMA0,115200 root=${ROOT_DEVICE} rootwait ro rootfstype=${ROOT_FSTYPE}" \
	-nographic -serial mon:stdio
