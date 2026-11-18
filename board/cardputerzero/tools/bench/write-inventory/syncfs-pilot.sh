#!/bin/sh
set -eu

read -r uptime _ < /proc/uptime
printf 'SYNCFS_PILOT before %s %s\n' "$uptime" "$(cat /sys/class/block/mmcblk0p7/stat)"
/usr/sbin/msd-syncfs /data
read -r uptime _ < /proc/uptime
printf 'SYNCFS_PILOT after %s %s\n' "$uptime" "$(cat /sys/class/block/mmcblk0p7/stat)"
seconds="${1:?interval seconds}"
windows="${2:?window count}"
dmesg -n 1

snapshot() {
	phase="$1"
	repeat="$2"
	read -r uptime _ < /proc/uptime
	for block in /sys/class/block/mmcblk0*; do
		printf 'MSDSTAT,%s,%s,%s,%s,%s\n' "$phase" "$repeat" "$uptime" "${block##*/}" "$(cat "$block/stat")"
	done
	printf 'RESIDUAL %s %s %s\n' "$phase" "$repeat" "$uptime"
	cat /sys/fs/ext4/mmcblk0p7/lifetime_write_kbytes /sys/fs/ext4/mmcblk0p7/session_write_kbytes
	cat /proc/fs/jbd2/mmcblk0p7-8/info
}

snapshot boot 0
i=1
while [ "$i" -le "$windows" ]; do
	snapshot idle-before "$i"
	sleep "$seconds"
	snapshot idle-after "$i"
	i=$((i + 1))
done
snapshot ram-before 0
dd if=/dev/zero of=/var/cache/msd-write-probe bs=4096 count=256 conv=fsync
logger 'msd-write-inventory RAM log control'
snapshot ram-after 0
snapshot disk-before 0
dd if=/dev/zero of=/data/.msd-write-probe bs=4096 count=256 conv=fsync
snapshot disk-after 0
printf 'MSDPROBE finished\n'
