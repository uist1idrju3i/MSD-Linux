#!/bin/sh
set -eu

REPO_ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
TEST_DIR="$(mktemp -d)"
STUB_DIR="${TEST_DIR}/bin"
INIT_DIR="${TEST_DIR}/etc/init.d"
STUB_LOG="${TEST_DIR}/commands.log"
CONSOLE="${TEST_DIR}/console"

cleanup() {
	rm -rf "$TEST_DIR"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

mkdir -p "$STUB_DIR" "$INIT_DIR"
# shellcheck disable=SC2016 # The stub script must retain its variable expansions.
printf '%s\n' \
	'#!/bin/sh' \
	'name=${0##*/}' \
	'printf "%s" "$name" >> "$INIT_SCRIPT_STUB_LOG"' \
	'for arg do printf " <%s>" "$arg" >> "$INIT_SCRIPT_STUB_LOG"; done' \
	'printf "\n" >> "$INIT_SCRIPT_STUB_LOG"' \
	'case "$name" in' \
	'	cmp) exit 1 ;;' \
	'	mkdir) [ "$*" != "-p /run/msd" ] || exit 1 ;;' \
	'	msd-update) exit 1 ;;' \
	'esac' \
	'exit 0' > "$STUB_DIR/stub"
chmod +x "$STUB_DIR/stub"

for command in \
	watchdog mkdir dd od tr cmp mkfs.ext4 fsck.ext4 mount awk msd-data-grow \
	loadkeys mv rm msd-hwinfo touch sed lsmod modprobe cat msd-update reboot \
	dmesg grep tail insmod umount wc sync sleep df; do
	ln -s stub "$STUB_DIR/$command"
done

# shellcheck disable=SC2016 # The fixture script must retain its variable expansion.
printf '%s\n' \
	'#!/bin/sh' \
	'printf "probe <%s>\n" "$*" >> "$INIT_SCRIPT_STUB_LOG"' \
	> "$INIT_DIR/S01probe"
chmod +x "$INIT_DIR/S01probe"

for script in \
	board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog \
	board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data \
	board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay \
	board/cardputerzero/rootfs-overlay/etc/init.d/S04msd-keymap \
	board/cardputerzero/rootfs-overlay/etc/init.d/S97msd-hwinfo \
	board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready \
	board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health \
	board/cardputerzero/tools/bench/boottime/rcS \
	board/cardputerzero/tools/bench/boottime/S99zz-boottime-dump \
	board/cardputerzero/tools/bench/s3/S02zz-s3verify \
	board/cardputerzero/tools/bench/s3/S06msd-s3bench \
	board/cardputerzero/tools/bench/S97msd-s6-hardening-check
do
	source="${REPO_ROOT}/${script}"
	copy="${TEST_DIR}/$(basename "$script")"
	sh -n "$source" || fail "syntax error in $script"
	sed \
		-e "s|/dev/console|${CONSOLE}|g" \
		-e "s|/dev/kmsg|${CONSOLE}|g" \
		-e "s|/etc/init.d|${INIT_DIR}|g" \
		-e "s|/usr/sbin/msd-data-grow|${STUB_DIR}/msd-data-grow|g" \
		-e "s|/usr/sbin/msd-hwinfo|${STUB_DIR}/msd-hwinfo|g" \
		"$source" > "$copy"
	for action in stop restart; do
		: > "$STUB_LOG"
		if ! PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" \
			/bin/sh "$copy" "$action" >/dev/null 2>&1; then
			fail "$script $action returned nonzero"
		fi
		[ ! -s "$STUB_LOG" ] || fail "$script $action ran commands: $(cat "$STUB_LOG")"
	done
	printf 'ok - %s ignores stop and restart\n' "$script"
done

printf 'All init-script host tests passed.\n'
