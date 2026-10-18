#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
export ROOT_DEVICE=/dev/mmcblk0p6
export ROOT_FSTYPE=squashfs
exec "${SCRIPT_DIR}/test-qemu.sh" "$@"
