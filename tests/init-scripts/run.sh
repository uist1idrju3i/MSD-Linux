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
# shellcheck disable=SC2016 # The stub retains its runtime arguments.
printf '%s\n' \
	'#!/bin/sh' \
	'name=${0##*/}' \
	'printf "%s" "$name" >> "$INIT_SCRIPT_STUB_LOG"' \
	'for arg do printf " <%s>" "$arg" >> "$INIT_SCRIPT_STUB_LOG"; done' \
	'printf "\n" >> "$INIT_SCRIPT_STUB_LOG"' \
	'case "$name" in' \
	'early-io) exit "${INIT_SCRIPT_GATE_STATUS:-0}" ;;' \
	'msd-data-boot) case "${1:-}" in health) exit "${INIT_SCRIPT_HEALTH_STATUS:-0}" ;; *) exit "${INIT_SCRIPT_BOOT_STATUS:-0}" ;; esac ;;' \
	'sleep) exec /bin/sleep 60 ;;' \
	'cat) exec /bin/cat "$@" ;;' \
	'awk) exit 0 ;;' \
	'msd-update) if [ "${1:-}" = status ]; then printf "tryboot=%s\n" "${INIT_SCRIPT_TRYBOOT:-0}"; else exit "${INIT_SCRIPT_COMMIT_STATUS:-0}"; fi ;;' \
	'esac' \
	'exit 0' > "$STUB_DIR/stub"
chmod +x "$STUB_DIR/stub"

for command in \
	msd-data-boot watchdog mkdir dd od tr cmp mkfs.ext4 fsck.ext4 mount awk msd-data-grow \
	loadkeys mv rm msd-hwinfo touch sed lsmod modprobe cat msd-update reboot \
	dmesg grep tail insmod umount wc sync sleep df dumpe2fs msd-syncfs early-io; do
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
	board/cardputerzero/rootfs-overlay/etc/init.d/S02a-msd-early-io \
	board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data \
	board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay \
	board/cardputerzero/rootfs-overlay/etc/init.d/S04msd-keymap \
	board/cardputerzero/rootfs-overlay/etc/init.d/S97msd-hwinfo \
	board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready \
	board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health \
	board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-zram \
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
		-e "s|/usr/sbin/msd-data-boot|${STUB_DIR}/msd-data-boot|g" \
		-e "s|/run/msd-early-io/state|${TEST_DIR}/early-state|g" \
		-e "s|/run/msd-ready|${TEST_DIR}/ready|g" \
		-e "s|/usr/sbin/msd-syncfs|${STUB_DIR}/msd-syncfs|g" \
		-e "s|/usr/libexec/msd/early-io|${STUB_DIR}/early-io|g" \
		-e "s|/data/etc|${TEST_DIR}/data/etc|g" \
		-e "s|/data/msd-update|${TEST_DIR}/data/msd-update|g" \
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

data_init="${TEST_DIR}/S02msd-data"
run_data_init() {
	: > "$STUB_LOG"
	PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" \
		/bin/sh "$data_init" start >"${TEST_DIR}/data.log" 2>&1
}

printf 'ready\n' >"$TEST_DIR/early-state"
run_data_init || fail 'product data startup failed'
grep -Fxq 'msd-data-boot <start> <product>' "$STUB_LOG" ||
	fail 'product mode not selected'
printf 'hardware-absent-qemu\n' >"$TEST_DIR/early-state"
run_data_init || fail 'qemu data startup failed'
grep -Fxq 'msd-data-boot <start> <qemu>' "$STUB_LOG" ||
	fail 'qemu mode not selected'
for fault in gate coordinator state; do
	: >"$STUB_LOG"
	printf 'ready\n' >"$TEST_DIR/early-state"
	case "$fault" in
		gate) gate_status=1; boot_status=0 ;;
		coordinator) gate_status=0; boot_status=1 ;;
		state) gate_status=0; boot_status=0; printf 'invalid\n' >"$TEST_DIR/early-state" ;;
	esac
	set +e
	timeout 0.3 env PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" \
		INIT_SCRIPT_GATE_STATUS="$gate_status" INIT_SCRIPT_BOOT_STATUS="$boot_status" \
		/bin/sh "$data_init" start >"${TEST_DIR}/data.log" 2>&1
	status=$?
	set -e
	[ "$status" -eq 124 ] || fail "$fault failure exited instead of waiting"
	grep -Fq 'Boot stopped. Safe to power off.' "$TEST_DIR/data.log" ||
		fail "$fault failure did not report stop"
	if [ "$fault" != coordinator ] && grep -Fq msd-data-boot "$STUB_LOG"; then
		fail "$fault failure reached coordinator"
	fi
done
if awk '$2 == "/data" { found=1 } END { exit !found }' \
	"$REPO_ROOT/board/cardputerzero/rootfs-overlay/etc/fstab"; then
	fail 'fstab still mounts data'
fi
printf 'ok - S02 selects fixed product/qemu mode and waits on gate/state/coordinator failure\n'

health_init="${TEST_DIR}/S99msd-health"
for fault in none mount ready commit; do
	: >"$STUB_LOG"
	touch "$TEST_DIR/ready"
	health_status=0
	commit_status=0
	[ "$fault" != mount ] || health_status=1
	[ "$fault" != commit ] || commit_status=1
	[ "$fault" != ready ] || rm "$TEST_DIR/ready"
	set +e
	PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" \
		INIT_SCRIPT_TRYBOOT=1 INIT_SCRIPT_HEALTH_STATUS="$health_status" \
		INIT_SCRIPT_COMMIT_STATUS="$commit_status" /bin/sh "$health_init"
	status=$?
	set -e
	if [ "$fault" = none ]; then
		[ "$status" -eq 0 ] || fail 'valid health was rejected'
		grep -Fq 'msd-update <commit>' "$STUB_LOG" || fail 'valid health did not commit'
	else
		[ "$status" -eq 1 ] || fail "health $fault failure accepted"
		grep -Fq reboot "$STUB_LOG" || fail "health $fault failure did not reboot"
		if [ "$fault" != commit ] && grep -Fq 'msd-update <commit>' "$STUB_LOG"; then
			fail "health $fault failure reached commit"
		fi
	fi
done
: >"$STUB_LOG"
PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" /bin/sh "$health_init"
if grep -Eq 'msd-data-boot|commit|reboot' "$STUB_LOG"; then
	fail 'normal boot performed tryboot commit checks'
fi
printf 'ok - health gates tryboot commit on mapper/Btrfs and ready, and rejects commit errors\n'

"${CC:-cc}" -Wall -Wextra -Werror \
	"$REPO_ROOT/package/msd-syncfs/msd-syncfs.c" \
	"$REPO_ROOT/tests/init-scripts/syncfs-faults.c" \
	-Wl,--wrap=syncfs -Wl,--wrap=close -o "$TEST_DIR/msd-syncfs"
"$TEST_DIR/msd-syncfs" "$TEST_DIR" || fail 'syncfs helper rejected a directory'
for fault in syncfs close; do
	if SYNCFS_TEST_FAULT="$fault" "$TEST_DIR/msd-syncfs" "$TEST_DIR" \
		>"$TEST_DIR/helper.log" 2>&1; then
		fail "helper hid $fault failure"
	fi
	grep -Fq "msd-syncfs: $fault:" "$TEST_DIR/helper.log" ||
		fail "helper did not diagnose $fault failure"
done
if "$TEST_DIR/msd-syncfs" "$TEST_DIR/missing" >"$TEST_DIR/helper.log" 2>&1; then
	fail 'helper accepted a missing directory'
fi
grep -Fq "$TEST_DIR/missing:" "$TEST_DIR/helper.log" || fail 'helper hid open failure'
if "$TEST_DIR/msd-syncfs" "$STUB_LOG" >"$TEST_DIR/helper.log" 2>&1; then
	fail 'helper accepted a regular file'
fi
if "$TEST_DIR/msd-syncfs" >"$TEST_DIR/helper.log" 2>&1; then
	fail 'helper accepted no argument'
fi
grep -Fq 'Usage: msd-syncfs DIRECTORY' "$TEST_DIR/helper.log" || fail 'missing helper usage'
if "$TEST_DIR/msd-syncfs" "$TEST_DIR" extra >"$TEST_DIR/helper.log" 2>&1; then
	fail 'helper accepted extra arguments'
fi
printf 'ok - syncfs helper validates input and reports writeback errors\n'

python3 "$REPO_ROOT/tests/init-scripts/data-image.py"
printf 'All init-script host tests passed.\n'
