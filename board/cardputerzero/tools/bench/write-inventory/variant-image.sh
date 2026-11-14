#!/bin/bash
# Build an experiment sdcard.img whose data.ext4 uses different mke2fs
# extraargs, without touching product files. Re-runs genimage with a copy
# of genimage.cfg, then splices only the data partition into a copy of the
# base sdcard.img so partitions 1-6 stay byte-identical to the base build.
#
# Usage: variant-image.sh OUTPUT_DIR MKE2FS_EXTRA_ARGS DEST_DIR [TOTAL_BYTES]
#
#   MKE2FS_EXTRA_ARGS  extra mke2fs args appended to "-b 4096" in the
#                      data.ext4 extraargs; "" keeps the stock args.
#   TOTAL_BYTES        when given, pad the sdcard.img copy to exactly this
#                      size (should be a power of two) and extend partitions
#                      4 and 7 to the end of the disk with sfdisk, mirroring
#                      what msd-data-grow does on the guest. data.ext4 is
#                      then sized to fill partition 7 so resize2fs is a
#                      no-op on the guest.
#
# DEST_DIR gets an images/ directory usable as run.py --output.
set -euo pipefail

if (($# < 3 || $# > 4)); then
	printf 'Usage: %s OUTPUT_DIR MKE2FS_EXTRA_ARGS DEST_DIR [TOTAL_BYTES]\n' "$0" >&2
	exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd -P)"
BOARD_DIR="${REPO_ROOT}/board/cardputerzero"
OUTPUT_DIR="$(cd -- "$1" && pwd -P)"
MKE2FS_EXTRA="$2"
DEST_DIR="$(cd -- "$(dirname -- "$3")" && pwd -P)/$(basename -- "$3")"
TOTAL_BYTES="${4:-}"
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

command -v sfdisk >/dev/null || { printf 'sfdisk not found\n' >&2; exit 1; }

# genimage resolves mke2fs via PATH. Put the build's own host tools first so
# the variant is produced by the same binaries as the base image.
export PATH="${OUTPUT_DIR}/host/sbin:${OUTPUT_DIR}/host/bin:${PATH}"
printf 'variant-image: mke2fs=%s\n' "$(command -v mke2fs) ($("$(command -v mke2fs)" -V 2>&1 | head -n 1))"
printf 'variant-image: genimage=%s\n' "$("${GENIMAGE}" --version 2>&1 | head -n 1)"

# Partition 7 start (sectors) and size decide how large data.ext4 must be.
p7_start="$(sfdisk -d "${BINARIES_DIR}/sdcard.img" |
	awk -v part="sdcard.img7" '
		$1 ~ (part "$") || $1 ~ (part "[[:space:]]*:$") {
			gsub(/[[:space:]]*=[[:space:]]*/, "=", $0)
			for (i = 3; i <= NF; i++) {
				field = $i; sub(/,$/, "", field)
				if (field ~ /^start=/) { sub(/^start=/, "", field); print field; exit }
			}
		}')"
[ -n "${p7_start}" ] || { printf 'cannot read partition 7 start from sdcard.img\n' >&2; exit 1; }
printf 'variant-image: p7_start_sectors=%s\n' "${p7_start}"

data_size="64M"
if [ -n "${TOTAL_BYTES}" ]; then
	data_size="$((TOTAL_BYTES - p7_start * 512))"
	((data_size > 0)) || { printf 'TOTAL_BYTES too small for partition 7\n' >&2; exit 1; }
fi

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

# Copy genimage.cfg, changing only the data.ext4 mke2fs extraargs line and,
# when TOTAL_BYTES was given, the data image/partition sizes.
VARIANT_CFG="${GENIMAGE_TMP}/genimage-variant.cfg"
ORIG_EXTRAARGS="$(grep -n 'extraargs = "-b 4096"' "${BOARD_DIR}/genimage.cfg")"
if [ "$(printf '%s\n' "${ORIG_EXTRAARGS}" | wc -l)" != 1 ]; then
	printf 'Expected exactly one data.ext4 extraargs line, got:\n%s\n' "${ORIG_EXTRAARGS}" >&2
	exit 1
fi
if [ -n "${MKE2FS_EXTRA}" ]; then
	sed 's|extraargs = "-b 4096"|extraargs = "-b 4096 '"${MKE2FS_EXTRA}"'"|' \
		"${BOARD_DIR}/genimage.cfg" > "${VARIANT_CFG}.1"
else
	cp "${BOARD_DIR}/genimage.cfg" "${VARIANT_CFG}.1"
fi
awk -v sz="${data_size}" '
	/^image / { blk = ($0 ~ /^image data\.ext4/) ? "data" : "" }
	/blk == ""/ && /^[[:space:]]*partition data[[:space:]]*\{/ { blk = "part" }
	blk == "data" && /^[[:space:]]*size = / { sub(/size = [0-9]+[A-Za-z]*/, "size = " sz) }
	blk == "part" && /^[[:space:]]*size = / { sub(/size = [0-9]+[A-Za-z]*/, "size = " sz) }
	blk == "part" && /^[[:space:]]*}/ { blk = "" }
	{ print }
' "${VARIANT_CFG}.1" > "${VARIANT_CFG}"
diff -u "${BOARD_DIR}/genimage.cfg" "${VARIANT_CFG}" || true

VARIANT_OUT="${GENIMAGE_TMP}/images"
mkdir -p "${VARIANT_OUT}"
"${GENIMAGE}" \
	--rootpath "${ROOTPATH_TMP}" \
	--tmppath "${GENIMAGE_TMP}/tmp" \
	--inputpath "${STAGE_DIR}" \
	--outputpath "${VARIANT_OUT}" \
	--config "${VARIANT_CFG}"

# Splice: start from the base sdcard.img, optionally grow the disk and the
# partition table like msd-data-grow does, then overwrite only partition 7
# with the variant data.ext4.
mkdir -p "${DEST_DIR}/images"
cp "${BINARIES_DIR}/sdcard.img" "${DEST_DIR}/images/sdcard.img"
IMG="${DEST_DIR}/images/sdcard.img"

if [ -n "${TOTAL_BYTES}" ]; then
	truncate -s "${TOTAL_BYTES}" "${IMG}"
	dump="$(sfdisk -d "${IMG}")"
	p4_line="$(printf '%s\n' "${dump}" | grep -E 'sdcard\.img4[[:space:]]*:')"
	p7_line="$(printf '%s\n' "${dump}" | grep -E 'sdcard\.img7[[:space:]]*:')"
	p4_start="$(printf '%s\n' "${p4_line}" | sed -n 's/.*start=[[:space:]]*\([0-9]*\).*/\1/p')"
	p4_type="$(printf '%s\n' "${p4_line}" | sed -n 's/.*type=[[:space:]]*\([0-9a-fA-F]*\).*/\1/p')"
	p7_type="$(printf '%s\n' "${p7_line}" | sed -n 's/.*type=[[:space:]]*\([0-9a-fA-F]*\).*/\1/p')"
	disk_sectors="$((TOTAL_BYTES / 512))"
	printf 'variant-image: extending p4 and p7 to %s sectors (same sfdisk ops as msd-data-grow)\n' "${disk_sectors}"
	printf 'start=%s, size=%s, type=%s\n' "${p4_start}" "$((disk_sectors - p4_start))" "${p4_type}" |
		sfdisk --no-reread -N 4 "${IMG}" >/dev/null
	printf 'start=%s, size=%s, type=%s\n' "${p7_start}" "$((disk_sectors - p7_start))" "${p7_type}" |
		sfdisk --no-reread -N 7 "${IMG}" >/dev/null
fi

dd if="${VARIANT_OUT}/data.ext4" of="${IMG}" bs=512 seek="${p7_start}" conv=notrunc status=none
cp "${VARIANT_OUT}/data.ext4" "${DEST_DIR}/images/data.ext4"

# Evidence that partitions 1-6 are byte-identical to the base image: hash
# the region before partition 7 and each partition's byte range.
{
	printf '%s\n' "== region [0, p7_start) sha256 =="
	head -c "$((p7_start * 512))" "${BINARIES_DIR}/sdcard.img" | sha256sum
	head -c "$((p7_start * 512))" "${IMG}" | sha256sum
	printf '%s\n' "== partition region sha256 (base / variant) =="
	sfdisk -d "${BINARIES_DIR}/sdcard.img" |
		awk 'match($0, /(sdcard\.img[0-9]+)[[:space:]]*:[[:space:]]*start=[[:space:]]*([0-9]+),[[:space:]]*size=[[:space:]]*([0-9]+)/, m) { print m[1], m[2], m[3] }' |
		while read -r part start size; do
			[ "${part}" = "sdcard.img4" ] && continue
			[ "${part}" = "sdcard.img7" ] && continue
			b="$(dd if="${BINARIES_DIR}/sdcard.img" bs=512 skip="${start}" count="${size}" status=none | sha256sum | cut -d' ' -f1)"
			v="$(dd if="${IMG}" bs=512 skip="${start}" count="${size}" status=none | sha256sum | cut -d' ' -f1)"
			printf '%s base=%s variant=%s %s\n' "${part}" "${b}" "${v}" "$([ "${b}" = "${v}" ] && echo SAME || echo DIFF)"
		done
} | tee "${DEST_DIR}/partition-hashes.txt"

for f in Image bcm2710-rpi-cm0.dtb bcm2710-rpi-3-b.dtb rootfs.squashfs; do
	ln -s "${BINARIES_DIR}/${f}" "${DEST_DIR}/images/${f}"
done
ln -s "${OUTPUT_DIR}/.config" "${DEST_DIR}/.config"
ln -s "${OUTPUT_DIR}/host" "${DEST_DIR}/host"

sha256sum "${IMG}" "${DEST_DIR}/images/data.ext4"
printf 'variant-image: wrote %s\n' "${DEST_DIR}"
