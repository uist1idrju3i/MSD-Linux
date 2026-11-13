#!/bin/sh
set -eu

identity() {
	uname -a
	cat /proc/cmdline
	openssl version
	cat /usr/share/msd-update/version /usr/share/msd-update/key-origin
	openssl pkey -pubin -in /usr/share/msd-update/update-key.pem -outform DER |
		sha256sum
	sha256sum /usr/sbin/msd-update
	msd-update status
	cat /proc/mounts
}

snapshot() {
	label="$1"
	for part in 3 6; do
		printf 'SNAP %s p%s ' "$label" "$part"
		sha256sum "/dev/mmcblk0p$part"
		printf 'STAT %s p%s ' "$label" "$part"
		cat "/sys/block/mmcblk0/mmcblk0p$part/stat"
	done
	if [ -f /data/msd-update/installed ]; then
		printf 'STATE %s ' "$label"
		cat /data/msd-update/installed
	else
		printf 'STATE %s absent\n' "$label"
	fi
}

dmesg -n 1
identity
if [ "$1" = b ]; then
	printf 'AUTOHEALTH '
	if [ -f /data/msd-update/installed ]; then
		cat /data/msd-update/installed
	else
		echo cleared
	fi
	mkdir -p /run/selector
	mount -t vfat -o ro /dev/mmcblk0p1 /run/selector
	cat /run/selector/autoboot.txt
	umount /run/selector
	echo 'ACCEPTANCE_DONE b'
	exit 0
fi

modprobe usb-storage
for _ in 1 2 3 4 5; do
	[ ! -b /dev/sda ] || break
	sleep 1
done
mkdir -p /run/bundles
mount -t vfat -o ro /dev/sda /run/bundles
sha256sum /run/bundles/*.tar
snapshot before
set +e
msd-update install /run/bundles/tampered.tar
rc=$?
set -e
echo "RESULT tampered $rc"
[ "$rc" -ne 0 ]
snapshot tampered
set +e
msd-update install /run/bundles/unsigned.tar
rc=$?
set -e
echo "RESULT unsigned $rc"
[ "$rc" -ne 0 ]
snapshot unsigned
set +e
msd-update install /run/bundles/signed.tar
rc=$?
set -e
echo "RESULT signed $rc"
if [ "$rc" -ne 0 ]; then
	echo 'ACCEPTANCE_SAME_VERSION_REJECTED'
	exit 1
fi
snapshot signed
printf 'PAYLOAD rootfs '
dd if=/dev/mmcblk0p6 bs=4M iflag=count_bytes count=20676608 2>/dev/null | sha256sum
printf 'PAYLOAD boot '
sha256sum /dev/mmcblk0p3
sync
echo 'ACCEPTANCE_DONE a'
