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
	'	cmp) exit "${INIT_SCRIPT_CMP_STATUS:-1}" ;;' \
	'	tr) printf "%s" "${INIT_SCRIPT_MAGIC:-}" ;;' \
	'	mkfs.ext4) exit "${INIT_SCRIPT_MKFS_STATUS:-0}" ;;' \
	'	fsck.ext4) exit "${INIT_SCRIPT_FSCK_STATUS:-0}" ;;' \
	'	mount) exit "${INIT_SCRIPT_MOUNT_STATUS:-0}" ;;' \
	'	mkdir) [ "$*" != "-p /run/msd" ] || exit 1; case "$*" in */data/etc*) exit "${INIT_SCRIPT_MKDIR_STATUS:-0}" ;; esac ;;' \
	'	msd-data-grow) exit "${INIT_SCRIPT_GROW_STATUS:-0}" ;;' \
	'	msd-syncfs) exit "${INIT_SCRIPT_SYNCFS_STATUS:-0}" ;;' \
	'	dumpe2fs) exit "${INIT_SCRIPT_DUMPE2FS_STATUS:-0}" ;;' \
	'	awk) if [ "$1" = "/^Block count:/ { print \$3; exit }" ]; then' \
	'		if [ -e "$INIT_SCRIPT_SIZE_MARKER" ]; then printf "%s\n" "${INIT_SCRIPT_BLOCKS_AFTER-100}";' \
	'		else : > "$INIT_SCRIPT_SIZE_MARKER"; printf "%s\n" "${INIT_SCRIPT_BLOCKS_BEFORE-100}"; fi; fi ;;' \
	'	msd-update) exit 1 ;;' \
	'esac' \
	'exit 0' > "$STUB_DIR/stub"
chmod +x "$STUB_DIR/stub"

for command in \
	watchdog mkdir dd od tr cmp mkfs.ext4 fsck.ext4 mount awk msd-data-grow \
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
		-e "s|/usr/sbin/msd-data-grow|${STUB_DIR}/msd-data-grow|g" \
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
mount_options=noatime,nodev,nosuid,data=ordered,errors=remount-ro,noinit_itable
run_data_init() {
	: > "$STUB_LOG"
	rm -f "$TEST_DIR/size-marker"
	PATH="$STUB_DIR" INIT_SCRIPT_STUB_LOG="$STUB_LOG" INIT_SCRIPT_SIZE_MARKER="$TEST_DIR/size-marker" \
		/bin/sh "$data_init" start >"${TEST_DIR}/data.log" 2>&1
}

INIT_SCRIPT_MAGIC=53ef run_data_init || fail 'existing ext4 startup failed'
grep -Fq "mount <-t> <ext4> <-o> <$mount_options>" "$STUB_LOG" ||
	fail 'existing ext4 mount does not suppress background inode initialization'
if grep -Fq 'mkfs.ext4' "$STUB_LOG"; then
	fail 'existing ext4 was reformatted'
fi

INIT_SCRIPT_CMP_STATUS=0 run_data_init || fail 'empty partition startup failed'
grep -Fq 'mkfs.ext4 <-F> <-b> <4096> <-L> <data> <-E> <lazy_itable_init=0,lazy_journal_init=0>' "$STUB_LOG" ||
	fail 'fallback format does not initialize inode tables and journal synchronously'
grep -Fq "mount <-t> <ext4> <-o> <$mount_options>" "$STUB_LOG" ||
	fail 'fallback mount does not suppress background inode initialization'

if run_data_init; then
	fail 'unrecognized non-empty partition was accepted'
fi
if grep -Eq '^(mkfs.ext4|mount) ' "$STUB_LOG"; then
	fail 'unrecognized non-empty partition was formatted or mounted'
fi
if INIT_SCRIPT_CMP_STATUS=0 INIT_SCRIPT_MKFS_STATUS=1 run_data_init; then
	fail 'failed format was accepted'
fi
if grep -Eq '^(fsck.ext4|mount) ' "$STUB_LOG"; then
	fail 'failed format continued to fsck or mount'
fi
if INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_FSCK_STATUS=2 run_data_init; then
	fail 'failed fsck was accepted'
fi
if grep -Eq '^mount ' "$STUB_LOG"; then
	fail 'failed fsck continued to mount'
fi
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_MOUNT_STATUS=1 run_data_init
if grep -Fq 'msd-data-grow' "$STUB_LOG"; then
	fail 'failed mount continued to grow'
fi
grep -Fq "ext4 $mount_options" "$REPO_ROOT/board/cardputerzero/rootfs-overlay/etc/fstab" ||
	grep -Fq "ext4 noauto,$mount_options" "$REPO_ROOT/board/cardputerzero/rootfs-overlay/etc/fstab" ||
	fail 'fstab does not preserve the data mount options'
printf 'ok - data startup initializes synchronously and rejects unsafe paths\n'

grep_syncfs() {
	grep -Fq 'msd-syncfs </data>' "$STUB_LOG"
}
INIT_SCRIPT_MAGIC=53ef run_data_init || fail 'initial directory setup failed'
grep_syncfs || fail 'initial directories were not synchronized'
grep -Fxq 'msd-data: setup synchronized' "$CONSOLE" || fail 'syncfs success was not English-only'
[ "$(tail -n 1 "$STUB_LOG")" = 'msd-syncfs </data>' ] || fail 'syncfs ran before setup finished'
mkdir -p "$TEST_DIR/data/etc" "$TEST_DIR/data/msd-update"
INIT_SCRIPT_MAGIC=53ef run_data_init || fail 'unchanged startup failed'
if grep_syncfs; then fail 'unchanged startup unnecessarily synchronized'; fi
[ "$(grep -c '^dumpe2fs <-h>' "$STUB_LOG")" -eq 2 ] || fail 'raw filesystem size was not checked'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_BLOCKS_AFTER=200 run_data_init || fail 'grow startup failed'
grep_syncfs || fail 'grow with existing directories was not synchronized'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_BLOCKS_BEFORE='' run_data_init || fail 'unknown size startup failed'
grep_syncfs || fail 'unknown size was treated as unchanged'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_BLOCKS_AFTER=invalid run_data_init || fail 'invalid size startup failed'
grep_syncfs || fail 'invalid size was treated as unchanged'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_DUMPE2FS_STATUS=1 run_data_init || fail 'size probe failure changed startup behavior'
grep_syncfs || fail 'failed size probe was treated as unchanged'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_FSCK_STATUS=1 run_data_init || fail 'repaired startup failed'
grep_syncfs || fail 'fsck repairs were not synchronized'
INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_GROW_STATUS=1 run_data_init || fail 'grow error changed recovery behavior'
grep_syncfs || fail 'partial grow was not synchronized'
grep -Fq 'msd-data-grow failed' "$TEST_DIR/data.log" || fail 'grow error was hidden'
if INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_MKDIR_STATUS=8 run_data_init; then
	fail 'mkdir failure was hidden'
fi
grep_syncfs || fail 'partial mkdir was not synchronized'
if INIT_SCRIPT_MAGIC=53ef INIT_SCRIPT_BLOCKS_AFTER=200 INIT_SCRIPT_SYNCFS_STATUS=1 run_data_init; then
	fail 'syncfs failure was hidden'
fi
grep -Fq 'setup syncfs failed' "$TEST_DIR/data.log" || fail 'syncfs failure was not logged'
grep -Fxq 'msd-data: setup syncfs failed; keeping /data mounted.' "$TEST_DIR/data.log" || fail 'syncfs failure was not English-only'
INIT_SCRIPT_CMP_STATUS=0 run_data_init || fail 'format synchronization failed'
grep_syncfs || fail 'format was not synchronized'
printf 'ok - setup syncfs follows writes, skips unchanged boots, and reports errors\n'

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

printf 'All init-script host tests passed.\n'
