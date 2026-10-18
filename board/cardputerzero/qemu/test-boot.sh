#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
TIMEOUT_SECONDS="${QEMU_BOOT_TIMEOUT:-300}"
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

status=0
timeout "${TIMEOUT_SECONDS}s" "${SCRIPT_DIR}/run-qemu.sh" "$@" >"$LOG_FILE" 2>&1 || status=$?
if [ "$status" -ne 0 ] && [ "$status" -ne 124 ]; then
	cat "$LOG_FILE"
	printf 'QEMU exited with status %s\n' "$status" >&2
	exit "$status"
fi

if ! grep -Fq 'MSD-Linux ready' "$LOG_FILE"; then
	cat "$LOG_FILE"
	printf 'Boot marker not found in QEMU output\n' >&2
	exit 1
fi

if ! grep -Eiq '(^|[[:space:]])msd login:|login:' "$LOG_FILE"; then
	cat "$LOG_FILE"
	printf 'Login prompt not found in QEMU output\n' >&2
	exit 1
fi

printf 'QEMU boot marker and login prompt found.\n'
