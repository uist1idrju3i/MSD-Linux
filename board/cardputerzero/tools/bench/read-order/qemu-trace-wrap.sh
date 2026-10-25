#!/usr/bin/env bash
# Run qemu-system-aarch64 with the sdcard_read_block trace event written to
# QEMU_LOG_DIR/sd-trace.log. Used as QEMU_SYSTEM_AARCH64.
set -euo pipefail
qemu="${READ_ORDER_QEMU:-qemu-system-aarch64}"
if [[ "${1:-}" == --version ]]; then
	exec "$qemu" "$@"
fi
exec "$qemu" -trace enable=sdcard_read_block -D "${QEMU_LOG_DIR:?set QEMU_LOG_DIR}/sd-trace.log" "$@"
