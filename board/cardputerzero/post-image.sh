#!/bin/bash
set -euo pipefail

BOARD_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
STAGE_DIR="$(mktemp -d "${BINARIES_DIR}/cardputerzero-stage.XXXXXX")"
GENIMAGE_TMP="$(mktemp -d "${BINARIES_DIR}/genimage.XXXXXX")"
ROOTPATH_TMP="$(mktemp -d "${BINARIES_DIR}/genimage-root.XXXXXX")"
trap 'rm -rf "$STAGE_DIR" "$GENIMAGE_TMP" "$ROOTPATH_TMP"' EXIT

BOOTSEL_DIR="${STAGE_DIR}/bootsel"
BOOT_DIR="${STAGE_DIR}/boot"
UPDATE_DIR="${STAGE_DIR}/update"
mkdir -p "$BOOTSEL_DIR" "$BOOT_DIR/overlays" "$UPDATE_DIR"

gzip -9n -c "${BINARIES_DIR}/Image" > "${STAGE_DIR}/kernel-gzip-9.img"
pigz -11 -n -c "${BINARIES_DIR}/Image" > "${BINARIES_DIR}/kernel8.img"
gunzip -c "${BINARIES_DIR}/kernel8.img" | cmp - "${BINARIES_DIR}/Image"
image_bytes="$(wc -c < "${BINARIES_DIR}/Image" | tr -d '[:space:]')"
gzip_bytes="$(wc -c < "${STAGE_DIR}/kernel-gzip-9.img" | tr -d '[:space:]')"
pigz_bytes="$(wc -c < "${BINARIES_DIR}/kernel8.img" | tr -d '[:space:]')"
printf 'Kernel compression sizes (bytes): Image=%s gzip -9n=%s pigz -11=%s\n' \
	"$image_bytes" "$gzip_bytes" "$pigz_bytes"

cp "${BOARD_DIR}/autoboot.txt" "$BOOTSEL_DIR/"
cp "${BINARIES_DIR}/rpi-firmware/bootcode.bin" "$BOOTSEL_DIR/"

cp "${BINARIES_DIR}/rpi-firmware/start_cd.elf" \
	"${BINARIES_DIR}/rpi-firmware/fixup_cd.dat" \
	"${BINARIES_DIR}/rpi-firmware/config.txt" "$BOOT_DIR/"
cp "${BINARIES_DIR}/kernel8.img" \
	"${BINARIES_DIR}/bcm2710-rpi-cm0.dtb" \
	"${BINARIES_DIR}/bcm2710-rpi-3-b.dtb" "$BOOT_DIR/"
cp "${BOARD_DIR}/cmdline_rootfs_a.txt" "${BOARD_DIR}/cmdline_rootfs_b.txt" "$BOOT_DIR/"
cp -a "${BINARIES_DIR}/rpi-firmware/overlays/." "$BOOT_DIR/overlays/"
if [ -d "${BINARIES_DIR}/overlays" ]; then
	cp -a "${BINARIES_DIR}/overlays/." "$BOOT_DIR/overlays/"
fi
"${BOARD_DIR}/tools/check-dt-overlays.sh" \
	"${HOST_DIR:?}" "$BINARIES_DIR" "${BINARIES_DIR}/rpi-firmware/config.txt"
cp "${BINARIES_DIR}/rootfs.squashfs" "$STAGE_DIR/"

genimage \
	--rootpath "${ROOTPATH_TMP}" \
	--tmppath "${GENIMAGE_TMP}" \
	--inputpath "${STAGE_DIR}" \
	--outputpath "${BINARIES_DIR}" \
	--config "${BOARD_DIR}/genimage.cfg"

cp "${BINARIES_DIR}/rootfs.squashfs" "${BINARIES_DIR}/boot.vfat" "$UPDATE_DIR/"
(
	cd "$UPDATE_DIR"
	update_version="$(cat "${TARGET_DIR:?Buildroot must pass TARGET_DIR}/etc/msd-update/version")"
	{
		printf 'version %s\n' "$update_version"
		sha256sum rootfs.squashfs boot.vfat
	} > manifest
	host_openssl="${HOST_DIR:-}/bin/openssl"
	if [ ! -x "$host_openssl" ]; then
		printf 'Required Buildroot host OpenSSL binary is missing: %s\n' "$host_openssl" >&2
		exit 1
	fi
	signing_key="${MSD_UPDATE_SIGNING_KEY:-${BASE_DIR:?Buildroot must pass BASE_DIR}/msd-update-dev-key.pem}"
	if [ ! -r "$signing_key" ]; then
		printf 'Update signing key is missing or unreadable: %s\n' "$signing_key" >&2
		exit 1
	fi
	"$host_openssl" pkeyutl -sign -rawin -inkey "$signing_key" \
		-in manifest -out manifest.sig
	tar -cf "${BINARIES_DIR}/msd-update-bundle.tar" \
		rootfs.squashfs boot.vfat manifest manifest.sig
)
