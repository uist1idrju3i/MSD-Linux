#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
mkdir -p "$target_dir/run" "$target_dir/tmp" "$target_dir/var/log" "$target_dir/data"
test -x "$target_dir/etc/init.d/S98msd-ready"
test -f "$target_dir/etc/fstab"
