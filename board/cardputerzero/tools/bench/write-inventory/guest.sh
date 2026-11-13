#!/bin/sh
set -eu

seconds="${1:?interval seconds}"
windows="${2:?window count}"
case "$seconds:$windows" in *[!0-9:]*|0:*|*:0) exit 2 ;; esac

snapshot() {
	phase="$1"
	repeat="$2"
	read -r uptime _ < /proc/uptime
	for block in /sys/class/block/mmcblk0*; do
		printf 'MSDSTAT,%s,%s,%s,%s,%s\n' \
			"$phase" "$repeat" "$uptime" "${block##*/}" "$(cat "$block/stat")"
	done
}

printf 'MSDENV timezone=%s\n' "$(date '+%Z %z')"
# shellcheck disable=SC3045 # BusyBox ash supports ulimit -c.
printf 'MSDENV core_limit=%s core_pattern=%s\n' "$(ulimit -c)" "$(cat /proc/sys/kernel/core_pattern)"
cat /proc/mounts /proc/swaps
ps
ls -ld /var/log /var/cache /var/tmp /var/run /var/lock /var/spool /var/lib/misc
ls -l /etc/localtime /etc/timezone 2>/dev/null || :
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
