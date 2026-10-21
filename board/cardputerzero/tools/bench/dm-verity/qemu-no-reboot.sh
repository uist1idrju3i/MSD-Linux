#!/bin/sh
set -eu
qemu="${QEMU_REAL_BINARY:-qemu-system-aarch64}"
exec "$qemu" "$@" -no-reboot
