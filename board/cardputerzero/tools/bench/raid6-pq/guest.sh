#!/bin/sh
set -eu

case "${1:-start}" in
	start) ;;
	*) exit 0 ;;
esac

exec >/dev/console 2>&1
trap 'printf "RAID6_PROBE_EXIT=%s\n" "$?"' EXIT
printf 'RAID6_BOOT_COMPLETE uptime=%s\n' "$(cut -d ' ' -f 1 /proc/uptime)"
mkdir -p /run/raid6-mount
truncate -s 256M /run/raid6.img
mkfs.btrfs -f -d single -m dup /run/raid6.img
mount -t btrfs -o loop /run/raid6.img /run/raid6-mount
dd if=/dev/urandom of=/run/raid6-mount/data bs=4096 count=64
sync
sha256sum /run/raid6-mount/data >/run/raid6.sha256
umount /run/raid6-mount
mount -t btrfs -o loop /run/raid6.img /run/raid6-mount
sha256sum -c /run/raid6.sha256
btrfs --version
btrfs filesystem df /run/raid6-mount
btrfs scrub start -B -R /run/raid6-mount
umount /run/raid6-mount
rm /run/raid6.img
echo RAID6_BTRFS_OK
echo RAID6_DONE
