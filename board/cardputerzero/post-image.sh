#!/bin/bash
set -euo pipefail

BOARD_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
STAGE_DIR="$(mktemp -d "${BINARIES_DIR}/cardputerzero-stage.XXXXXX")"
GENIMAGE_TMP="$(mktemp -d "${BINARIES_DIR}/genimage.XXXXXX")"
trap 'rm -rf "$STAGE_DIR" "$GENIMAGE_TMP"' EXIT

BOOTSEL_DIR="${STAGE_DIR}/bootsel"
BOOT_A_DIR="${STAGE_DIR}/boot-a"
BOOT_B_DIR="${STAGE_DIR}/boot-b"
mkdir -p "$BOOTSEL_DIR" "$BOOT_A_DIR/overlays" "$BOOT_B_DIR/overlays"

gzip -9n -c "${BINARIES_DIR}/Image" > "${BINARIES_DIR}/kernel8.img"
gunzip -c "${BINARIES_DIR}/kernel8.img" | cmp - "${BINARIES_DIR}/Image"

cp "${BOARD_DIR}/autoboot.txt" "$BOOTSEL_DIR/"
cp "${BINARIES_DIR}/rpi-firmware/bootcode.bin" "$BOOTSEL_DIR/"

for slot in "$BOOT_A_DIR" "$BOOT_B_DIR"; do
	cp "${BINARIES_DIR}/rpi-firmware/start_cd.elf" \
		"${BINARIES_DIR}/rpi-firmware/fixup_cd.dat" "$slot/"
	cp "${BINARIES_DIR}/rpi-firmware/config.txt" "$slot/"
	cp "${BINARIES_DIR}/kernel8.img" \
		"${BINARIES_DIR}/bcm2710-rpi-cm0.dtb" \
		"${BINARIES_DIR}/bcm2710-rpi-3-b.dtb" "$slot/"
	cp -a "${BINARIES_DIR}/rpi-firmware/overlays/." "$slot/overlays/"
	if [ -d "${BINARIES_DIR}/overlays" ]; then
		cp -a "${BINARIES_DIR}/overlays/." "$slot/overlays/"
	fi
done

cp "${BOARD_DIR}/cmdline-a.txt" "$BOOT_A_DIR/cmdline.txt"
cp "${BOARD_DIR}/cmdline-b.txt" "$BOOT_B_DIR/cmdline.txt"

genimage \
	--tmppath "${GENIMAGE_TMP}" \
	--inputpath "${STAGE_DIR}" \
	--outputpath "${BINARIES_DIR}" \
	--config "${BOARD_DIR}/genimage.cfg"
