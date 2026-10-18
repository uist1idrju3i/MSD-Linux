#!/bin/bash
set -euo pipefail

BOARD_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
BOOT_DIR="$(mktemp -d "${BINARIES_DIR}/cardputerzero-boot.XXXXXX")"
GENIMAGE_TMP="$(mktemp -d "${BINARIES_DIR}/genimage.XXXXXX")"
trap 'rm -rf "$BOOT_DIR" "$GENIMAGE_TMP"' EXIT

cp -a "${BINARIES_DIR}/rpi-firmware/." "$BOOT_DIR/"
cp "${BINARIES_DIR}/Image" \
	"${BINARIES_DIR}/bcm2710-rpi-cm0.dtb" \
	"${BINARIES_DIR}/bcm2710-rpi-3-b.dtb" "$BOOT_DIR/"
mkdir -p "$BOOT_DIR/overlays"
if [ -d "${BINARIES_DIR}/overlays" ]; then
	cp -a "${BINARIES_DIR}/overlays/." "$BOOT_DIR/overlays/"
fi

genimage \
	--tmppath "${GENIMAGE_TMP}" \
	--inputpath "${BOOT_DIR}" \
	--outputpath "${BINARIES_DIR}" \
	--config "${BOARD_DIR}/genimage.cfg"
