#!/bin/sh
set -eu

target_dir="${1:?target directory is required}"
case "$(readlink "$target_dir/sbin/modprobe")" in
	../bin/busybox|/bin/busybox) ;;
	*) printf 'Refusing binary index removal: modprobe is not BusyBox\n' >&2; exit 1 ;;
esac
find "$target_dir/lib/modules" -type f -name 'modules.*.bin' -delete
