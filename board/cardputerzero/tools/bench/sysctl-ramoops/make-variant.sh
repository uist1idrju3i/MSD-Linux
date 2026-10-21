#!/usr/bin/env bash
set -euo pipefail

if (($# != 3)); then
	printf 'Usage: %s VARIANT OUTPUT_DIR VARIANT_DIR\n' "$0" >&2
	exit 2
fi

variant="$1"
output_dir="$2"
variant_dir="$3"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
host="${output_dir}/host"
images="${output_dir}/images"
target="${variant_dir}/target"
rootfs="${images}/rootfs.squashfs"
sdcard="${images}/sdcard.img"
hook="${script_dir}/S99zz-s21probe"

case "$variant" in
	Y0|Y1|Y2|P0|P1|R0|R1) ;;
	*)
		printf 'Unsupported variant: %s\n' "$variant" >&2
		exit 2
		;;
esac

for required in "$rootfs" "$sdcard" "$images/Image" \
	"$images/bcm2710-rpi-cm0.dtb" "$host/bin/unsquashfs" \
	"$host/bin/mksquashfs" "$host/sbin/sfdisk" "$hook"
do
	[[ -f "$required" ]] || {
		printf 'Required file not found: %s\n' "$required" >&2
		exit 1
	}
done
[[ ! -e "$variant_dir" ]] || {
	printf 'Refusing to overwrite %s\n' "$variant_dir" >&2
	exit 1
}

mkdir -p "$target"
unsquash_status=0
"$host/bin/unsquashfs" -no-progress -no-xattrs -d "$target" "$rootfs" \
	>"${variant_dir}.unsquashfs.log" 2>&1 || unsquash_status=$?
if ((unsquash_status != 0)); then
	if ((unsquash_status != 2)) ||
		! grep -Fq 'failed to change uid and gids' \
			"${variant_dir}.unsquashfs.log"
	then
		cat "${variant_dir}.unsquashfs.log" >&2
		exit "$unsquash_status"
	fi
fi

install -D -m 0755 "$hook" "$target/etc/init.d/S99zz-s21probe"
case "$variant" in
	Y0)
		printf 'readback\n' >"$target/etc/s21-test-mode"
		;;
	Y1)
		mkdir -p "$target/etc/sysctl.d"
		printf '%s\n' \
			'kernel.kptr_restrict=2' \
			'kernel.dmesg_restrict=1' \
			'kernel.sysrq=32' \
			'fs.protected_fifos=2' \
			'fs.protected_regular=2' \
			'fs.protected_hardlinks=1' \
			'fs.protected_symlinks=1' \
			'net.core.bpf_jit_harden=2' \
			'net.ipv4.conf.all.accept_redirects=0' \
			'net.ipv4.conf.default.accept_redirects=0' \
			'net.ipv4.conf.all.send_redirects=0' \
			'net.ipv4.conf.default.accept_source_route=0' \
			'net.ipv4.conf.all.rp_filter=1' \
			'net.ipv4.conf.all.log_martians=1' \
			'net.ipv4.conf.default.log_martians=1' \
			>"$target/etc/sysctl.d/90-msd-test.conf"
		printf 'readback\n' >"$target/etc/s21-test-mode"
		;;
	Y2)
		mkdir -p "$target/etc/sysctl.d"
		printf 'kernel.sysrq=0\n' >"$target/etc/sysctl.d/90-msd-test.conf"
		printf 'readback\n' >"$target/etc/s21-test-mode"
		;;
	P0|P1)
		printf 'panic\n' >"$target/etc/s21-test-mode"
		;;
	R0|R1)
		printf 'panic-pstore\n' >"$target/etc/s21-test-mode"
		;;
esac

info="$("$host/bin/unsquashfs" -s "$rootfs")"
compression="$(awk '$1 == "Compression" {print $2; exit}' <<<"$info")"
block_size="$(awk '$1 == "Block" && $2 == "size" {print $3; exit}' <<<"$info")"
[[ -n "$compression" && -n "$block_size" ]]
"$host/bin/mksquashfs" "$target" "$variant_dir/rootfs.squashfs" \
	-noappend -all-root -no-xattrs -no-progress -comp "$compression" \
	-b "$block_size" >"${variant_dir}.mksquashfs.log" 2>&1
shared_rootfs="${S21_SHARED_ROOTFS:-}"
if [[ -n "$shared_rootfs" ]]; then
	[[ -f "$shared_rootfs" ]] || {
		printf 'Shared rootfs not found: %s\n' "$shared_rootfs" >&2
		exit 1
	}
	cp --reflink=auto "$shared_rootfs" "$variant_dir/rootfs.squashfs"
fi

cp --sparse=always "$sdcard" "$variant_dir/sdcard.img"
image_bytes="$(stat -c %s "$variant_dir/sdcard.img")"
padded_bytes=1
while ((padded_bytes < image_bytes)); do
	padded_bytes=$((padded_bytes * 2))
done
truncate -s "$padded_bytes" "$variant_dir/sdcard.img"
read -r root_a root_a_sectors root_b root_b_sectors < <(
	"$host/sbin/sfdisk" --json "$variant_dir/sdcard.img" |
		python3 -c 'import json,sys; p=json.load(sys.stdin)["partitiontable"]["partitions"]; assert len(p)==7; print(p[4]["start"],p[4]["size"],p[5]["start"],p[5]["size"])'
)
rootfs_bytes="$(stat -c %s "$variant_dir/rootfs.squashfs")"
((rootfs_bytes <= root_a_sectors * 512 && rootfs_bytes <= root_b_sectors * 512))
dd if="$variant_dir/rootfs.squashfs" of="$variant_dir/sdcard.img" \
	bs=512 seek="$root_a" conv=notrunc status=none
dd if="$variant_dir/rootfs.squashfs" of="$variant_dir/sdcard.img" \
	bs=512 seek="$root_b" conv=notrunc status=none

source_head="$(git -C "$script_dir/../../../../.." rev-parse HEAD)"
{
	printf 'variant=%s\nsource_head=%s\n' "$variant" "$source_head"
	printf 'rootfs_source=%s\nsdcard_source=%s\n' "$rootfs" "$sdcard"
	if [[ -n "$shared_rootfs" ]]; then
		printf 'shared_rootfs=%s\n' "$shared_rootfs"
	fi
	sha256sum "$rootfs" "$sdcard" "$images/Image" \
		"$images/bcm2710-rpi-cm0.dtb" "$hook" \
		"$variant_dir/rootfs.squashfs" "$variant_dir/sdcard.img"
} >"$variant_dir/variant-info.txt"
rm -rf "$target"
