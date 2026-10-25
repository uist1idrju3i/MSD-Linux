#!/usr/bin/env bash
# S15: run the QEMU binary named by S15_QEMU, optionally with a TCG plugin
# whose output goes to QEMU_LOG_DIR/plugin.log. Used as QEMU_SYSTEM_AARCH64.
set -euo pipefail
qemu="${S15_QEMU:?set S15_QEMU}"
args=()
if [[ -n "${S15_PLUGIN:-}" && "${1:-}" != --version ]]; then
	args+=(-plugin "$S15_PLUGIN" -d plugin -D "${QEMU_LOG_DIR:?set QEMU_LOG_DIR}/plugin.log")
fi
exec "$qemu" "${args[@]}" "$@"
