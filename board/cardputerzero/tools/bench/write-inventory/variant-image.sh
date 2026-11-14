#!/bin/bash
# Build an experiment sdcard.img whose data.ext4 uses different mke2fs
# extraargs, without touching product files. Re-runs genimage with a copy
# of genimage.cfg and produces a directory usable as run.py --output.
#
# Usage: variant-image.sh OUTPUT_DIR MKE2FS_EXTRA_ARGS DEST_DIR
set -euo pipefail

if (($# != 3)); then
	printf 'Usage: %s OUTPUT_DIR MKE2FS_EXTRA_ARGS DEST_DIR\n' "$0" >&2
	exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd -P)"
BOARD_DIR="${REPO_ROOT}/board/cardputerzero"
OUTPUT_DIR="$(cd -- "$1" && pwd -P)"
MKE2FS_EXTRA="$2"
DEST_DIR="$(cd -- "$(dirname -- "$3")" && pwd -P)/$(basename -- "$3")"
BINARIES_DIR="${OUTPUT_DIR}/images"
GENIMAGE="${OUTPUT_DIR}/host/bin/genimage"

for required in "${GENIMAGE}" "${BINARIES_DIR}/sdcard.img" "${BINARIES_DIR}/Image"; do
	if [ ! -e "${required}" ]; then
		printf 'Required build output not found: %s\n' "${required}" >&2
		exit 1
	fi
done

[ ! -e "${DEST_DIR}" ] || {
	printf 'Destination already exists: %s\n' "${DEST_DIR}" >&2
	exit 1
}

STAGE_DIR="$(mktemp -d "${BINARIES_DIR}/variant-stage.XXXXXX")"
GENIMAGE_TMP="$(mktemp -d "${BINARIES_DIR}/variant-genimage.XXXXXX")"
ROOTPATH_TMP="$(mktemp -d "${BINARIES_DIR}/variant-root.XXXXXX")"
trap 'rm -rf "${STAGE_DIR}" "${GENIMAGE_TMP}" "${ROOTPATH_TMP}"' EXIT

BOOTSEL_DIR="${STAGE_DIR}/bootsel"
BOOT_DIR="${STAGE_DIR}/boot"
mkdir -p "${BOOTSEL_DIR}" "${BOOT_DIR}/overlays"
cp "${BOARD_DIR}/autoboot.txt" "${BINARIES_DIR}/rpi-firmware/bootcode.bin" "${BOOTSEL_DIR}/"
cp "${BINARIES_DIR}/rpi-firmware/start_cd.elf" \
	"${BINARIES_DIR}/rpi-firmware/fixup_cd.dat" \
	"${BINARIES_DIR}/rpi-firmware/config.txt" "${BOOT_DIR}/"
cp "${BINARIES_DIR}/kernel8.img" \
	"${BINARIES_DIR}/bcm2710-rpi-cm0.dtb" \
	"${BINARIES_DIR}/bcm2710-rpi-3-b.dtb" "${BOOT_DIR}/"
cp "${BOARD_DIR}/cmdline_rootfs_a.txt" "${BOARD_DIR}/cmdline_rootfs_b.txt" "${BOOT_DIR}/"
cp -a "${BINARIES_DIR}/rpi-firmware/overlays/." "${BOOT_DIR}/overlays/"
if [ -d "${BINARIES_DIR}/overlays" ]; then
	cp -a "${BINARIES_DIR}/overlays/." "${BOOT_DIR}/overlays/"
fi
cp "${BINARIES_DIR}/rootfs.squashfs" "${STAGE_DIR}/"

# Copy genimage.cfg, changing only the data.ext4 mke2fs extraargs line.
VARIANT_CFG="${GENIMAGE_TMP}/genimage-variant.cfg"
ORIG_EXTRAARGS="$(grep -n 'extraargs = "-b 4096"' "${BOARD_DIR}/genimage.cfg")"
if [ "$(printf '%s\n' "${ORIG_EXTRAARGS}" | wc -l)" != 1 ]; then
	printf 'Expected exactly one data.ext4 extraargs line, got:\n%s\n' "${ORIG_EXTRAARGS}" >&2
	exit 1
fi
sed 's|extraargs = "-b 4096"|extraargs = "-b 4096 '"${MKE2FS_EXTRA}"'"|' \
	"${BOARD_DIR}/genimage.cfg" > "${VARIANT_CFG}"
diff -u "${BOARD_DIR}/genimage.cfg" "${VARIANT_CFG}" || true
printf 'variant-image: mke2fs=%s\n' "$("${OUTPUT_DIR}/host/sbin/mke2fs" -V 2>&1 | head -n 1)"
printf 'variant-image: genimage=%s\n' "$("${GENIMAGE}" --version 2>&1 | head -n 1)"

VARIANT_OUT="${GENIMAGE_TMP}/images"
mkdir -p "${VARIANT_OUT}"
"${GENIMAGE}" \
	--rootpath "${ROOTPATH_TMP}" \
	--tmppath "${GENIMAGE_TMP}/tmp" \
	--inputpath "${STAGE_DIR}" \
	--outputpath "${VARIANT_OUT}" \
	--config "${VARIANT_CFG}"

# Assemble a run.py-compatible input dir: the variant SD image plus
# symlinks for everything that stays identical to the base build.
mkdir -p "${DEST_DIR}/images"
cp "${VARIANT_OUT}/sdcard.img" "${DEST_DIR}/images/sdcard.img"
cp "${VARIANT_OUT}/data.ext4" "${DEST_DIR}/images/data.ext4"
for f in Image bcm2710-rpi-cm0.dtb bcm2710-rpi-3-b.dtb rootfs.squashfs; do
	ln -s "${BINARIES_DIR}/${f}" "${DEST_DIR}/images/${f}"
done
ln -s "${OUTPUT_DIR}/.config" "${DEST_DIR}/.config"
ln -s "${OUTPUT_DIR}/host" "${DEST_DIR}/host"

sha256sum "${DEST_DIR}/images/sdcard.img" "${DEST_DIR}/images/data.ext4"
printf 'variant-image: wrote %s\n' "${DEST_DIR}"
