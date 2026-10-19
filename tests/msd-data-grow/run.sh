#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
grow="$repo_root/board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow"
test_root="$(mktemp -d)"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

make_image() {
	image="$1"
	with_partition_8="$2"
	truncate -s 2G "$image"
	p4_end=1482752
	if [ "$with_partition_8" -eq 1 ]; then
		p4_end=1517568
	fi
	{
		printf 'label: dos\nunit: sectors\n\n'
		printf 'start=2048, size=32768, type=c\n'
		printf 'start=34816, size=131072, type=c\n'
		printf 'start=165888, size=131072, type=c\n'
		printf 'start=296960, size=%s, type=5\n' "$((p4_end - 296960))"
		printf 'start=299008, size=524288, type=83\n'
		printf 'start=825344, size=524288, type=83\n'
		printf 'start=1351680, size=131072, type=83\n'
		if [ "$with_partition_8" -eq 1 ]; then
			printf 'start=1484800, size=32768, type=83\n'
		fi
	} | sfdisk "$image" >/dev/null
}

run_grow() {
	MSD_DATA_GROW_DISK="$1" \
	MSD_DATA_GROW_PARTITION_PREFIX="$1" \
	MSD_DATA_GROW_DATA_DEVICE="$2" \
	MSD_DATA_GROW_SKIP_KERNEL_NOTIFY=1 \
	"$grow"
}

partition_value() {
	sfdisk --dump "$1" |
		awk -v partition="$1$2" -v wanted="$3" '
			$1 == partition && $2 == ":" {
				gsub(/[[:space:]]*=[[:space:]]*/, "=", $0)
				for (i = 3; i <= NF; i++) {
					field = $i
					sub(/,$/, "", field)
					if (index(field, wanted "=") == 1) {
						sub("^[^=]*=", "", field)
						print field
						found = 1
					}
				}
			}
			END { if (!found) exit 1 }
		'
}

image="$test_root/cardputerzero.img"
data_fs="$test_root/data.ext4"
make_image "$image" 0
truncate -s 64M "$data_fs"
mke2fs -q -F -t ext4 "$data_fs"
truncate -s 96M "$data_fs"
run_grow "$image" "$data_fs"

disk_sectors=$((2 * 1024 * 1024 * 1024 / 512))
p4_start="$(partition_value "$image" 4 start)"
p7_start="$(partition_value "$image" 7 start)"
p4_size="$(partition_value "$image" 4 size)"
p7_size="$(partition_value "$image" 7 size)"
[ "$((p4_start + p4_size))" -eq "$disk_sectors" ] || fail "partition 4 did not reach the disk end"
[ "$((p7_start + p7_size))" -eq "$disk_sectors" ] || fail "partition 7 did not reach the disk end"
blocks="$(dumpe2fs -h "$data_fs" 2>/dev/null | awk -F: '$1 == "Block count" {gsub(/[[:space:]]/, "", $2); print $2}')"
[ "$blocks" -gt 16384 ] || fail "ext4 filesystem was not grown beyond 64 MiB"
printf 'ok - p4 and p7 grow to the disk end and ext4 grows offline\n'

before="$(sha256sum "$image" | awk '{print $1}')"
run_grow "$image" "$data_fs"
after="$(sha256sum "$image" | awk '{print $1}')"
[ "$before" = "$after" ] || fail "a second run changed the partition table"
printf 'ok - a second run leaves the partition table unchanged\n'

nonlast="$test_root/nonlast.img"
make_image "$nonlast" 1
sfdisk --dump "$nonlast" > "$test_root/nonlast.before"
if run_grow "$nonlast" "$data_fs" > "$test_root/nonlast.log" 2>&1; then
	fail "growth succeeded when partition 7 was not last"
fi
sfdisk --dump "$nonlast" > "$test_root/nonlast.after"
cmp "$test_root/nonlast.before" "$test_root/nonlast.after" ||
	fail "the partition table changed when partition 7 was not last"
printf 'ok - growth refuses when partition 7 is not last\n'

printf 'All msd-data-grow host tests passed.\n'
