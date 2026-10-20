#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
TIMEOUT_SECONDS="${QEMU_BOOT_TIMEOUT:-300}"
ROOT_DEVICE="${ROOT_DEVICE:-/dev/mmcblk0p5}"
REMOVE_LOG_FILE=false
if [ -n "${QEMU_LOG_DIR:-}" ]; then
	mkdir -p -- "$QEMU_LOG_DIR"
	LOG_FILE="${QEMU_LOG_DIR%/}/serial-$(basename -- "$ROOT_DEVICE").log"
else
	LOG_FILE="$(mktemp)"
	REMOVE_LOG_FILE=true
fi
QEMU_PID=
QEMU_MODULE_TEST="${QEMU_MODULE_TEST-usbnet,bcm2835-unicam,imx219}"
if [ -n "$QEMU_MODULE_TEST" ]; then
	QEMU_EXTRA_APPEND="${QEMU_EXTRA_APPEND:+${QEMU_EXTRA_APPEND} }msd.module-test=${QEMU_MODULE_TEST}"
fi
export QEMU_EXTRA_APPEND

# shellcheck disable=SC2329 # Invoked by the EXIT trap below.
cleanup() {
	if [ -n "$QEMU_PID" ]; then
		kill "$QEMU_PID" 2>/dev/null || true
		wait "$QEMU_PID" 2>/dev/null || true
	fi
	if [ "$REMOVE_LOG_FILE" = true ]; then
		rm -f "$LOG_FILE"
	fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

START_SECONDS=$SECONDS
"${SCRIPT_DIR}/run-qemu.sh" "$@" >"$LOG_FILE" 2>&1 &
QEMU_PID=$!
deadline=$((SECONDS + TIMEOUT_SECONDS))

while (( SECONDS < deadline )); do
	if grep -Fq 'MSD/Linux ready' "$LOG_FILE" &&
		grep -Eiq '(^|[[:space:]])msd login:|login:' "$LOG_FILE"; then
		kill "$QEMU_PID" 2>/dev/null || true
		wait "$QEMU_PID" 2>/dev/null || true
		QEMU_PID=
		elapsed=$((SECONDS - START_SECONDS))
		printf 'QEMU reached ready after %s seconds.\n' "$elapsed"
		if ! "${SCRIPT_DIR}/check-serial-log.sh" "$LOG_FILE"; then
			printf 'QEMU serial log contains boot error patterns.\n' >&2
			exit 1
		fi
		mount_options_line="$(grep -aF 'msd-data: /data ' "$LOG_FILE" | tail -n 1 || true)"
		if [ -z "$mount_options_line" ]; then
			printf 'QEMU serial log is missing the /data mount options.\n' >&2
			exit 1
		fi
		for option in data=ordered nodev nosuid; do
			case "$mount_options_line" in
				*"$option"*) ;;
				*)
					printf 'QEMU /data mount options are missing %s: %s\n' \
						"$option" "$mount_options_line" >&2
					exit 1
					;;
			esac
		done
		if [ -n "$QEMU_MODULE_TEST" ]; then
			IFS=',' read -r -a modules <<< "$QEMU_MODULE_TEST"
			for module in "${modules[@]}"; do
				[ -n "$module" ] || continue
				module_check_line="msd-module-check: ${module} loaded via modprobe and listed by lsmod"
				if ! grep -Fq "$module_check_line" "$LOG_FILE"; then
					printf 'QEMU serial log is missing the %s module-load check.\n' \
						"$module" >&2
					exit 1
				fi
			done
		fi
		printf 'QEMU boot marker and login prompt found for root %s.\n' \
			"$ROOT_DEVICE"
		exit 0
	fi

	if ! jobs -pr | grep -Fxq "$QEMU_PID"; then
		status=0
		wait "$QEMU_PID" || status=$?
		QEMU_PID=
		cat "$LOG_FILE"
		if [ "$status" -eq 0 ]; then
			status=1
		fi
		printf 'QEMU exited before the boot marker and login prompt (status %s).\n' \
			"$status" >&2
		exit "$status"
	fi

	sleep 1
done

kill "$QEMU_PID" 2>/dev/null || true
wait "$QEMU_PID" 2>/dev/null || true
QEMU_PID=
cat "$LOG_FILE"
printf 'QEMU did not show the boot marker and login prompt within %s seconds.\n' \
	"$TIMEOUT_SECONDS" >&2
exit 124
