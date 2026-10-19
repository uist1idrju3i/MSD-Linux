#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
CHECKER="${REPO_ROOT}/board/cardputerzero/qemu/check-serial-log.sh"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
LOG_FILE="${TEMP_DIR}/serial.log"

printf '%s\n' \
	'[    1.231933] WARNING: CPU: 0 PID: 1 at arch/arm64/mm/ioremap.c:27 __ioremap_prot+0x70/0xc0' \
	'[    1.237818] Call trace:' \
	'[    1.237984] __ioremap_prot+0x70/0xc0 (P)' \
	'[    1.238154] brcmvirt_gpio_probe+0x230/0x300' \
	'[    1.241339] ---[ end trace 0000000000000000 ]---' >"$LOG_FILE"
"$CHECKER" "$LOG_FILE"

printf '%s\n' \
	'[    2.226999] mmc-bcm2835 3f300000.mmcnr: mmc_debug:0 mmc_debug2:0' >"$LOG_FILE"
"$CHECKER" "$LOG_FILE"

printf '%s\n' 'mount: mounting /dev/mmcblk0p7 on /data failed' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted a /data mount failure.\n' >&2
	exit 1
fi

if ! printf '%s\n' "$output" | grep -Fq 'mount: mounting /dev/mmcblk0p7 on /data failed'; then
	printf 'Serial log checker did not print the matching /data mount failure.\n' >&2
	exit 1
fi

printf '%s\n' '/usr/sbin/msd-data-grow: line 25: sfdisk: not found' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted a missing sfdisk command.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fq '/usr/sbin/msd-data-grow: line 25: sfdisk: not found'; then
	printf 'Serial log checker did not print the missing sfdisk command.\n' >&2
	exit 1
fi

printf '%s\n' 'msd-data-grow failed; keeping /data mounted.' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted an msd-data-grow failure.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fq 'msd-data-grow failed; keeping /data mounted.'; then
	printf 'Serial log checker did not print the msd-data-grow failure.\n' >&2
	exit 1
fi

printf '%s\n' '[    4.589263] msd-keymap: failed to load /usr/share/keymaps/tca8418_keypad_m5stack_keymap.map' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted an msd-keymap failure.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fq 'msd-keymap: failed to load'; then
	printf 'Serial log checker did not print the msd-keymap failure.\n' >&2
	exit 1
fi

printf '%s\n' \
	"Starting network: ifup: can't open '/var/run/ifstate.new': No such file or directory FAIL" \
	'FAIL' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted an init-script failure.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fq "Starting network: ifup: can't open '/var/run/ifstate.new': No such file or directory FAIL"; then
	printf 'Serial log checker did not print the failed init-script status.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fxq 'FAIL'; then
	printf 'Serial log checker did not print a standalone failure status.\n' >&2
	exit 1
fi

printf '%s\n' \
	'[    2.816830] Internal error: Oops: 0000000096000007 [#1] SMP' \
	'[    2.832438] Call trace:' >"$LOG_FILE"
if output="$("$CHECKER" "$LOG_FILE" 2>&1)"; then
	printf 'Serial log checker accepted an unrelated Oops.\n' >&2
	exit 1
fi
if ! printf '%s\n' "$output" | grep -Fq 'Internal error: Oops'; then
	printf 'Serial log checker did not print the unrelated Oops.\n' >&2
	exit 1
fi

printf 'QEMU serial-log negative test passed.\n'
