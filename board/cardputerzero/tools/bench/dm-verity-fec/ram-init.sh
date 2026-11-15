#!/bin/busybox sh
set -u
B=/bin/busybox
$B mount -t devtmpfs devtmpfs /dev
$B mount -t proc proc /proc
$B mount -t sysfs sysfs /sys
target=
blocks=
for arg in $($B cat /proc/cmdline); do
	case "$arg" in
		b3.target=*) target="${arg#*=}" ;;
		b3.blocks=*) blocks="${arg#*=}" ;;
	esac
done
case "$target:$blocks" in
	*[!0-9:]* | :* | *:) echo B3_RAM_CONFIG_ERROR; exit 2 ;;
esac
n=0
while [ ! -b /dev/dm-0 ] && [ "$n" -lt 100 ]; do
	$B sleep 1
	n=$((n + 1))
done
echo "B3_RAM_BEGIN target=$target blocks=$blocks"
$B dd if=/dev/dm-0 of=/dev/null bs=4096 skip="$target" count=1
target_status=$?
echo "B3_RAM_TARGET status=$target_status"
$B dd if=/dev/dm-0 of=/dev/null bs=4096 count="$blocks"
all_status=$?
echo "B3_RAM_ALL status=$all_status"
echo B3_RAM_END
while :; do $B sleep 3600; done
