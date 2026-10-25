#!/bin/bash
# Run via docker/msd-dev board/cardputerzero/tools/bench/boottime/run-boottime.sh ...
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../../../" && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/output}"
IMAGES_DIR="${OUTPUT_DIR}/images"
QEMU_MACHINE="${QEMU_MACHINE:-raspi3ap}"
QEMU_SYSTEM_AARCH64="${QEMU_SYSTEM_AARCH64:-qemu-system-aarch64}"
QEMU_BOOT_TIMEOUT="${QEMU_BOOT_TIMEOUT:-1800}"

usage() {
	printf 'Usage: %s --variant NAME --runs N --csv PATH --log-dir DIR [--mode icount|tcg] [--kernel Image] [--dtb file] [--squashfs-comp NAME] [--squashfs-block BYTES]\n' "$0" >&2
}

variant=
runs=
csv_path=
log_dir=
mode=icount
kernel_option=
dtb_option=
squashfs_comp_option=
squashfs_block_option=
while (($#)); do
	case "$1" in
		--variant)
			(($# >= 2)) || { usage; exit 2; }
			variant="$2"
			shift 2
			;;
		--runs)
			(($# >= 2)) || { usage; exit 2; }
			runs="$2"
			shift 2
			;;
		--csv)
			(($# >= 2)) || { usage; exit 2; }
			csv_path="$2"
			shift 2
			;;
		--log-dir)
			(($# >= 2)) || { usage; exit 2; }
			log_dir="$2"
			shift 2
			;;
		--mode)
			(($# >= 2)) || { usage; exit 2; }
			mode="$2"
			shift 2
			;;
		--kernel)
			(($# >= 2)) || { usage; exit 2; }
			kernel_option="$2"
			shift 2
			;;
		--dtb)
			(($# >= 2)) || { usage; exit 2; }
			dtb_option="$2"
			shift 2
			;;
		--squashfs-comp)
			(($# >= 2)) || { usage; exit 2; }
			squashfs_comp_option="$2"
			shift 2
			;;
		--squashfs-block)
			(($# >= 2)) || { usage; exit 2; }
			squashfs_block_option="$2"
			shift 2
			;;
		*)
			usage
			exit 2
			;;
	esac
done

if [[ -z "$variant" || -z "$runs" || -z "$csv_path" || -z "$log_dir" ]] ||
	[[ ! "$runs" =~ ^[0-9]+$ ]]; then
	usage
	exit 2
fi

case "$mode" in
	icount|tcg) ;;
	*)
		printf 'Unsupported mode: %s\n' "$mode" >&2
		exit 2
		;;
esac

case "$QEMU_MACHINE" in
	raspi3ap)
		default_dtb=bcm2710-rpi-cm0.dtb
		;;
	raspi3b)
		default_dtb=bcm2710-rpi-3-b.dtb
		;;
	*)
		printf 'Unsupported QEMU_MACHINE: %s\n' "$QEMU_MACHINE" >&2
		exit 2
		;;
esac

kernel_used="${kernel_option:-${IMAGES_DIR}/Image}"
dtb_used="${dtb_option:-${IMAGES_DIR}/${default_dtb}}"
base_rootfs="${IMAGES_DIR}/rootfs.squashfs"
base_image="${IMAGES_DIR}/sdcard.img"
unsquashfs="${OUTPUT_DIR}/host/bin/unsquashfs"
mksquashfs="${OUTPUT_DIR}/host/bin/mksquashfs"
sfdisk="${OUTPUT_DIR}/host/sbin/sfdisk"

mkdir -p -- "$log_dir" "$(dirname -- "$csv_path")"
log_dir="$(cd -- "$log_dir" && pwd -P)"
csv_path="$(realpath -m -- "$csv_path")"
for required in \
	"$base_rootfs" "$base_image" "$kernel_used" "$dtb_used" \
	"$unsquashfs" "$mksquashfs" "$sfdisk"; do
	if [[ ! -f "$required" ]]; then
		printf 'Required boot-time input or tool not found: %s\n' \
			"$required" >&2
		exit 1
	fi
done

image_build_dir="${log_dir}/image-build-$(date -u +%Y%m%dT%H%M%SZ)"
target_dir="${image_build_dir}/target"
test_rootfs="${image_build_dir}/rootfs-boottime.squashfs"
test_image="${image_build_dir}/sdcard-boottime.img"
mkdir -p -- "$image_build_dir"

unsquash_status=0
"$unsquashfs" -no-progress -no-xattrs -d "$target_dir" "$base_rootfs" \
	>"${image_build_dir}/unsquashfs.log" 2>&1 || unsquash_status=$?
if ((unsquash_status != 0)); then
	if ((unsquash_status != 2)) ||
		! grep -Fq 'failed to change uid and gids' \
			"${image_build_dir}/unsquashfs.log"; then
		cat "${image_build_dir}/unsquashfs.log" >&2
		exit 1
	fi
fi
install -D -m 0755 "${SCRIPT_DIR}/rcS" "${target_dir}/etc/init.d/rcS"
install -D -m 0755 "${SCRIPT_DIR}/S99zz-boottime-dump" \
	"${target_dir}/etc/init.d/S99zz-boottime-dump"

squashfs_info="$("$unsquashfs" -s "$base_rootfs")"
compression="$(awk '$1 == "Compression" { print $2; exit }' \
	<<<"$squashfs_info")"
block_size="$(awk '$1 == "Block" && $2 == "size" { print $3; exit }' \
	<<<"$squashfs_info")"
if [[ -z "$compression" || -z "$block_size" ]]; then
	printf 'Could not read SquashFS options from %s\n' "$base_rootfs" >&2
	exit 1
fi
compression="${squashfs_comp_option:-$compression}"
block_size="${squashfs_block_option:-$block_size}"
"$mksquashfs" "$target_dir" "$test_rootfs" -noappend -all-root \
	-no-xattrs -no-progress -comp "$compression" -b "$block_size" \
	>"${image_build_dir}/mksquashfs.log" 2>&1

cp --reflink=auto --sparse=always "$base_image" "$test_image"
image_size="$(stat -c '%s' "$test_image")"
padded_size=1
while ((padded_size < image_size)); do
	padded_size=$((padded_size * 2))
done
truncate -s "$padded_size" "$test_image"

partition_info="$("$sfdisk" --json "$test_image" | python3 -c '
import json
import sys

partitions = json.load(sys.stdin)["partitiontable"]["partitions"]
if len(partitions) != 7:
    raise SystemExit(f"expected 7 partitions, found {len(partitions)}")
for number in (5, 6):
    partition = partitions[number - 1]
    print(partition["start"], partition["size"], end=" ")
')"
read -r root_a_start root_a_size root_b_start root_b_size \
	<<<"$partition_info"
rootfs_bytes="$(stat -c '%s' "$test_rootfs")"
if ((rootfs_bytes > root_a_size * 512 || rootfs_bytes > root_b_size * 512)); then
	printf 'Test SquashFS does not fit in rootfs A/B partitions.\n' >&2
	exit 1
fi
dd if="$test_rootfs" of="$test_image" bs=512 \
	seek="$root_a_start" conv=notrunc status=none
dd if="$test_rootfs" of="$test_image" bs=512 \
	seek="$root_b_start" conv=notrunc status=none

qemu_version_output="$("$QEMU_SYSTEM_AARCH64" --version)"
qemu_version="${qemu_version_output%%$'\n'*}"
{
	printf 'git_head=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD)"
	printf 'git_status_porcelain:\n'
	git -C "$REPO_ROOT" status --porcelain
	printf 'sha256_base_rootfs=%s\n' \
		"$(sha256sum "$base_rootfs" | awk '{print $1}')"
	printf 'sha256_kernel_image=%s\n' \
		"$(sha256sum "$kernel_used" | awk '{print $1}')"
	printf 'sha256_dtb=%s\n' \
		"$(sha256sum "$dtb_used" | awk '{print $1}')"
	printf 'sha256_test_rootfs=%s\n' \
		"$(sha256sum "$test_rootfs" | awk '{print $1}')"
	printf 'qemu_version=%s\n' "$qemu_version"
	printf 'squashfs_compression=%s\n' "$compression"
	printf 'squashfs_block_size=%s\n' "$block_size"
	printf 'test_rootfs_bytes=%s\n' "$rootfs_bytes"
} >"${log_dir}/image-build.txt"

run_id="$(date -u +%Y%m%dT%H%M%SZ)-${variant}-${mode}"
qemu_environment=(env)
if [[ "$mode" == icount ]]; then
	qemu_environment+=(QEMU_ICOUNT=shift=0)
else
	qemu_environment+=(-u QEMU_ICOUNT)
fi
qemu_environment+=(
	"OUTPUT_DIR=$OUTPUT_DIR"
	QEMU_COPY_IMAGE=0
	QEMU_MODULE_TEST=
	"QEMU_BOOT_TIMEOUT=$QEMU_BOOT_TIMEOUT"
	'QEMU_EXTRA_APPEND=initcall_debug printk.time=1 log_buf_len=4M msd.sweep=1 msd.boottime=1'
	"KERNEL_IMAGE=$kernel_used"
	"DTB_IMAGE=$dtb_used"
	"QEMU_MACHINE=$QEMU_MACHINE"
)
failed=0
for ((repeat = 0; repeat <= runs; repeat++)); do
	boot_log_dir="${log_dir}/boot${repeat}"
	serial_log="${boot_log_dir}/serial-mmcblk0p5.log"
	mkdir -p -- "$boot_log_dir"
	if ((${#serial_log} >= 100)); then
		printf 'QEMU serial log path must be shorter than 100 characters: %s\n' \
			"$serial_log" >&2
		exit 2
	fi
	: >"$serial_log"

	start_ns="$(date +%s%N)"
	exit_status=0
	qemu_environment_for_boot=(
		"${qemu_environment[@]}"
		"QEMU_LOG_DIR=$boot_log_dir"
	)
	if "${qemu_environment_for_boot[@]}" \
		"${REPO_ROOT}/board/cardputerzero/qemu/test-boot.sh" "$test_image" \
		>"${boot_log_dir}/test-boot.log" 2>&1; then
		exit_status=0
	else
		exit_status=$?
		failed=1
	fi
	end_ns="$(date +%s%N)"
	wall_ns=$((end_ns - start_ns))
	printf -v wall_seconds '%d.%06d' \
		"$((wall_ns / 1000000000))" "$(((wall_ns % 1000000000) / 1000))"

	if ! python3 "${SCRIPT_DIR}/parse-boottime.py" \
		--log "$serial_log" --csv "$csv_path" --run-id "$run_id" \
		--variant "$variant" --mode "$mode" --repeat "$repeat" \
		--first-boot "$((repeat == 0 ? 1 : 0))" \
		--wall-seconds "$wall_seconds" --exit-status "$exit_status"; then
		failed=1
	fi
done

if ((failed != 0)); then
	exit 1
fi
