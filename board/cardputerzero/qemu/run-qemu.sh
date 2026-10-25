#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
IMAGES_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}/images"
IMAGE="${1:-${IMAGES_DIR}/sdcard.img}"
KERNEL="${KERNEL_IMAGE:-${IMAGES_DIR}/Image}"
QEMU="${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}"
QEMU_MACHINE="${QEMU_MACHINE:-raspi3ap}"
ROOT_DEVICE="${ROOT_DEVICE:-/dev/mmcblk0p5}"
ROOT_FSTYPE="${ROOT_FSTYPE:-squashfs}"
QEMU_EXTRA_APPEND="${QEMU_EXTRA_APPEND:-}"
QEMU_ICOUNT="${QEMU_ICOUNT:-}"
case "$QEMU_MACHINE" in
	raspi3b)
		QEMU_MEMORY=1G
		default_dtb=bcm2710-rpi-3-b.dtb
		;;
	raspi3ap)
		QEMU_MEMORY=512M
		default_dtb=bcm2710-rpi-cm0.dtb
		;;
	*)
		printf 'Unsupported QEMU_MACHINE: %s\n' "$QEMU_MACHINE" >&2
		exit 2
		;;
esac
DTB="${DTB_IMAGE:-${IMAGES_DIR}/${default_dtb}}"
QEMU_COPY_IMAGE="${QEMU_COPY_IMAGE:-1}"

for required in "$IMAGE" "$KERNEL" "$DTB"; do
	if [ ! -f "$required" ]; then
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	fi
done

case "$QEMU_COPY_IMAGE" in
	1)
		WORK_DIR="$(mktemp -d)"
		trap 'rm -rf "$WORK_DIR"' EXIT
		QEMU_IMAGE="${WORK_DIR}/sdcard.img"
		cp "$IMAGE" "$QEMU_IMAGE"
		image_size="$(stat -c '%s' "$QEMU_IMAGE")"
		padded_size=1
		while [ "$padded_size" -lt "$image_size" ]; do
			padded_size=$((padded_size * 2))
		done
		truncate -s "$padded_size" "$QEMU_IMAGE"
		;;
	0)
		QEMU_IMAGE="$IMAGE"
		;;
	*)
		printf 'QEMU_COPY_IMAGE must be 0 or 1: %s\n' "$QEMU_COPY_IMAGE" >&2
		exit 2
		;;
esac

append_args=(
	"earlycon=pl011,mmio32,0x3f201000"
	"console=ttyAMA1,115200"
	"root=$ROOT_DEVICE"
	"rootwait"
	"ro"
	"rootfstype=$ROOT_FSTYPE"
)
if [ "${QEMU_WATCHDOG:-0}" != 1 ]; then
	append_args+=("initcall_blacklist=bcm2835_wdt_driver_init")
fi
if [ -n "$QEMU_EXTRA_APPEND" ]; then
	read -r -a extra_append <<< "$QEMU_EXTRA_APPEND"
	append_args+=("${extra_append[@]}")
fi
qemu_args=()
if [ -n "$QEMU_ICOUNT" ]; then
	qemu_args+=(-icount "$QEMU_ICOUNT")
fi
if [ -n "${QEMU_QMP_SOCKET:-}" ]; then
	qemu_args+=(-qmp "unix:${QEMU_QMP_SOCKET},server=on,wait=off")
fi

case "${QEMU_HASH_IMAGE:-1}" in
	0 | 1) ;;
	*)
		printf 'QEMU_HASH_IMAGE must be 0 or 1: %s\n' "$QEMU_HASH_IMAGE" >&2
		exit 2
		;;
esac
qemu_path="$(command -v "$QEMU")"
provenance_files=("$qemu_path" "$KERNEL" "$DTB")
if [ "${QEMU_HASH_IMAGE:-1}" = 1 ]; then
	provenance_files+=("$IMAGE")
fi
# Record what this run used so experiment logs carry their own provenance.
{
	printf 'run-qemu: version=%s\n' "$("$QEMU" --version | head -n 1)"
	printf 'run-qemu: machine=%s memory=%s icount=%s\n' \
		"$QEMU_MACHINE" "$QEMU_MEMORY" "${QEMU_ICOUNT:-off}"
	sha256sum -- "${provenance_files[@]}" | sed 's/^/run-qemu: sha256 /'
} >&2

# Both Pi 3 DTBs map the PL011 to ttyAMA1; enable the QEMU watchdog model only on request.
exec "$QEMU" "${qemu_args[@]}" -M "$QEMU_MACHINE" -m "$QEMU_MEMORY" \
	-kernel "$KERNEL" \
	-dtb "$DTB" \
	-drive "file=${QEMU_IMAGE},if=sd,format=raw" \
	-append "${append_args[*]}" \
	-nographic -serial mon:stdio
