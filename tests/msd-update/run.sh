#!/bin/sh
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
UPDATER="${REPO_ROOT}/board/cardputerzero/rootfs-overlay/usr/sbin/msd-update"
TEST_DIR="$(mktemp -d)"
DT_DIR="${TEST_DIR}/dt"
P1_DIR="${TEST_DIR}/p1"
STATE_DIR="${TEST_DIR}/state"
PARTITION_PREFIX="${TEST_DIR}/partition"
LOG_FILE="${TEST_DIR}/output"
FSYNC_LOG="${TEST_DIR}/fsync.log"
UPDATE_PRIVATE_KEY="${TEST_DIR}/update-private.pem"
UPDATE_PUBLIC_KEY="${TEST_DIR}/update-public.pem"
RUNNING_VERSION="${TEST_DIR}/version"

cleanup() {
	rm -rf "$TEST_DIR"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

set_property() {
	case "$2" in
		0) printf '\000\000\000\000' > "$1" ;;
		1) printf '\000\000\000\001' > "$1" ;;
		2) printf '\000\000\000\002' > "$1" ;;
		3) printf '\000\000\000\003' > "$1" ;;
		*) fail "test property out of range: $2" ;;
	esac
}

set_dt() {
	set_property "$DT_DIR/partition" "$1"
	set_property "$DT_DIR/tryboot" "$2"
}

set_autoboot() {
	printf '[all]\ntryboot_a_b=1\nboot_partition=%s\n[tryboot]\nboot_partition=%s\n' "$1" "$2" > "$P1_DIR/autoboot.txt"
}

expect_autoboot() {
	printf '[all]\ntryboot_a_b=1\nboot_partition=%s\n[tryboot]\nboot_partition=%s\n' "$1" "$2" > "$TEST_DIR/expected"
	cmp "$TEST_DIR/expected" "$P1_DIR/autoboot.txt" || fail "autoboot.txt did not match $1/$2"
}

run_update() {
	PATH="$TEST_DIR/bin:$PATH" \
	MSD_TEST_FSYNC_LOG="$FSYNC_LOG" \
	MSD_UPDATE_DT_DIR="$DT_DIR" \
	MSD_UPDATE_P1_DIR="$P1_DIR" \
	MSD_UPDATE_STATE_DIR="$STATE_DIR" \
	MSD_UPDATE_PARTITION_PREFIX="$PARTITION_PREFIX" \
	MSD_UPDATE_KEY_PATH="$UPDATE_PUBLIC_KEY" \
	MSD_UPDATE_VERSION_PATH="$RUNNING_VERSION" \
	/bin/sh "$UPDATER" "$@"
}

sign_manifest() {
	openssl pkeyutl -sign -rawin -inkey "$1" -in "$2/manifest" -out "$2/manifest.sig"
}

expect_failure() {
	if run_update "$@" > "$LOG_FILE" 2>&1; then
		fail "command unexpectedly succeeded: $*"
	fi
}

mkdir -p "$DT_DIR" "$P1_DIR" "$STATE_DIR"
printf '100\n' > "$RUNNING_VERSION"
mkdir -p "$TEST_DIR/bin"
openssl genpkey -algorithm Ed25519 -out "$UPDATE_PRIVATE_KEY"
openssl pkey -in "$UPDATE_PRIVATE_KEY" -pubout -out "$UPDATE_PUBLIC_KEY"
# shellcheck disable=SC2016 # The generated test command must retain its variable expansion.
printf '#!/bin/sh\nprintf "%%s\\n" "$1" >> "$MSD_TEST_FSYNC_LOG"\n' > "$TEST_DIR/bin/fsync"
chmod +x "$TEST_DIR/bin/fsync"
set_dt 2 1
status="$(run_update status)"
[ "$status" = 'slot=A partition=2 tryboot=1' ] || fail "big-endian status decode: $status"
printf 'ok - status decodes big-endian DT properties\n'

set_autoboot 2 3
cp "$P1_DIR/autoboot.txt" "$TEST_DIR/original-autoboot.txt"
printf '3\n' > "$STATE_DIR/installed"
set_dt 3 0
expect_failure commit
cmp "$TEST_DIR/original-autoboot.txt" "$P1_DIR/autoboot.txt" || fail "commit changed autoboot.txt without tryboot"
printf 'ok - commit refuses tryboot=0\n'

set_dt 2 1
expect_failure commit
cmp "$TEST_DIR/original-autoboot.txt" "$P1_DIR/autoboot.txt" || fail "commit changed autoboot.txt on partition mismatch"
printf 'ok - commit refuses a partition mismatch\n'

set_dt 3 1
printf '3\n' > "$STATE_DIR/installed"
run_update commit > "$LOG_FILE"
expect_autoboot 3 2
grep -Fxq "$P1_DIR/autoboot.txt.new" "$FSYNC_LOG" || fail "commit did not fsync the new autoboot file"
grep -Fxq "$P1_DIR" "$FSYNC_LOG" || fail "commit did not fsync the boot selector directory"
printf 'ok - commit swaps boot partitions 2 to 3\n'

set_dt 2 1
printf '2\n' > "$STATE_DIR/installed"
set_autoboot 3 2
run_update commit > "$LOG_FILE"
expect_autoboot 2 3
printf 'ok - commit swaps boot partitions 3 to 2\n'

mkdir -p "$TEST_DIR/bad"
printf 'bad-rootfs\n' > "$TEST_DIR/bad/rootfs.squashfs"
printf 'bad-boot\n' > "$TEST_DIR/bad/boot.vfat"
printf '%064d  rootfs.squashfs\n%064d  boot.vfat\n' 0 0 > "$TEST_DIR/bad/manifest"
sign_manifest "$UPDATE_PRIVATE_KEY" "$TEST_DIR/bad"
tar -cf "$TEST_DIR/bad.tar" -C "$TEST_DIR/bad" rootfs.squashfs boot.vfat manifest manifest.sig
printf 'old-rootfs\n' > "${PARTITION_PREFIX}6"
printf 'old-boot\n' > "${PARTITION_PREFIX}3"
set_dt 2 0
expect_failure install "$TEST_DIR/bad.tar"
[ "$(cat "${PARTITION_PREFIX}6")" = 'old-rootfs' ] || fail "bad hash changed the inactive rootfs"
[ "$(cat "${PARTITION_PREFIX}3")" = 'old-boot' ] || fail "bad hash changed the inactive boot slot"
printf 'ok - install rejects a bad SHA-256 without writing slots\n'

mkdir -p "$TEST_DIR/good" "$TEST_DIR/bin"
printf 'verified-rootfs\n' > "$TEST_DIR/good/rootfs.squashfs"
printf 'verified-boot\n' > "$TEST_DIR/good/boot.vfat"
(cd "$TEST_DIR/good" && { printf 'version 200\n'; sha256sum rootfs.squashfs boot.vfat; } > manifest)
sign_manifest "$UPDATE_PRIVATE_KEY" "$TEST_DIR/good"
tar -cf "$TEST_DIR/good.tar" -C "$TEST_DIR/good" rootfs.squashfs boot.vfat manifest manifest.sig
run_update install "$TEST_DIR/good.tar" > "$LOG_FILE"
root_bytes="$(wc -c < "$TEST_DIR/good/rootfs.squashfs" | tr -d '[:space:]')"
boot_bytes="$(wc -c < "$TEST_DIR/good/boot.vfat" | tr -d '[:space:]')"
dd if="${PARTITION_PREFIX}6" bs=4M iflag=count_bytes count="$root_bytes" 2>/dev/null > "$TEST_DIR/root-readback"
dd if="${PARTITION_PREFIX}3" bs=4M iflag=count_bytes count="$boot_bytes" 2>/dev/null > "$TEST_DIR/boot-readback"
cmp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/root-readback" || fail "rootfs read-back differs"
cmp "$TEST_DIR/good/boot.vfat" "$TEST_DIR/boot-readback" || fail "boot read-back differs"
[ "$(cat "$STATE_DIR/installed")" = 3 ] || fail "verified install state was not recorded"
printf 'ok - the shared boot bundle installs and verifies slot B\n'

mkdir -p "$TEST_DIR/unsigned"
cp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/good/boot.vfat" "$TEST_DIR/good/manifest" "$TEST_DIR/unsigned/"
tar -cf "$TEST_DIR/unsigned.tar" -C "$TEST_DIR/unsigned" rootfs.squashfs boot.vfat manifest
printf 'old-rootfs\n' > "${PARTITION_PREFIX}6"
printf 'old-boot\n' > "${PARTITION_PREFIX}3"
expect_failure install "$TEST_DIR/unsigned.tar"
[ "$(cat "${PARTITION_PREFIX}6")" = 'old-rootfs' ] || fail "unsigned bundle changed the inactive rootfs"
[ "$(cat "${PARTITION_PREFIX}3")" = 'old-boot' ] || fail "unsigned bundle changed the inactive boot slot"
printf 'ok - unsigned bundles are rejected before writing slots\n'

openssl genpkey -algorithm Ed25519 -out "$TEST_DIR/wrong-private.pem"
mkdir -p "$TEST_DIR/wrong-key"
cp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/good/boot.vfat" "$TEST_DIR/good/manifest" "$TEST_DIR/wrong-key/"
sign_manifest "$TEST_DIR/wrong-private.pem" "$TEST_DIR/wrong-key"
tar -cf "$TEST_DIR/wrong-key.tar" -C "$TEST_DIR/wrong-key" rootfs.squashfs boot.vfat manifest manifest.sig
expect_failure install "$TEST_DIR/wrong-key.tar"
[ "$(cat "${PARTITION_PREFIX}6")" = 'old-rootfs' ] || fail "wrong-key bundle changed the inactive rootfs"
[ "$(cat "${PARTITION_PREFIX}3")" = 'old-boot' ] || fail "wrong-key bundle changed the inactive boot slot"
printf 'ok - bundles signed by another key are rejected before writing slots\n'

mkdir -p "$TEST_DIR/tampered"
cp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/good/boot.vfat" "$TEST_DIR/good/manifest.sig" "$TEST_DIR/tampered/"
printf 'tampered manifest\n' > "$TEST_DIR/tampered/manifest"
tar -cf "$TEST_DIR/tampered.tar" -C "$TEST_DIR/tampered" rootfs.squashfs boot.vfat manifest manifest.sig
expect_failure install "$TEST_DIR/tampered.tar"
[ "$(cat "${PARTITION_PREFIX}6")" = 'old-rootfs' ] || fail "tampered manifest changed the inactive rootfs"
[ "$(cat "${PARTITION_PREFIX}3")" = 'old-boot' ] || fail "tampered manifest changed the inactive boot slot"
printf 'ok - tampered manifests are rejected before writing slots\n'

# make_versioned NAME VERSION_LINES: sign a bundle with the good images and the given version lines.
make_versioned() {
	mkdir -p "$TEST_DIR/$1"
	cp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/good/boot.vfat" "$TEST_DIR/$1/"
	(cd "$TEST_DIR/$1" && { printf '%b' "$2"; sha256sum rootfs.squashfs boot.vfat; } > manifest)
	sign_manifest "$UPDATE_PRIVATE_KEY" "$TEST_DIR/$1"
	tar -cf "$TEST_DIR/$1.tar" -C "$TEST_DIR/$1" rootfs.squashfs boot.vfat manifest manifest.sig
}

reset_slot_b() {
	set_dt 2 0
	printf 'old-rootfs\n' > "${PARTITION_PREFIX}6"
	printf 'old-boot\n' > "${PARTITION_PREFIX}3"
	rm -f "$STATE_DIR/installed"
}

expect_slot_b_unchanged() {
	[ "$(cat "${PARTITION_PREFIX}6")" = 'old-rootfs' ] || fail "$1 changed the inactive rootfs"
	[ "$(cat "${PARTITION_PREFIX}3")" = 'old-boot' ] || fail "$1 changed the inactive boot slot"
	[ ! -e "$STATE_DIR/installed" ] || fail "$1 recorded an install"
}

expect_slot_b_installed() {
	dd if="${PARTITION_PREFIX}6" bs=4M iflag=count_bytes count="$root_bytes" 2>/dev/null > "$TEST_DIR/root-readback"
	cmp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/root-readback" || fail "$1 did not install the rootfs"
	[ "$(cat "$STATE_DIR/installed")" = 3 ] || fail "$1 did not record the install"
}

make_versioned same 'version 100\n'
reset_slot_b
run_update install "$TEST_DIR/same.tar" > "$LOG_FILE"
expect_slot_b_installed "same-version bundle"
printf 'ok - a bundle with the running version installs\n'

make_versioned older 'version 99\n'
reset_slot_b
expect_failure install "$TEST_DIR/older.tar"
grep -Fq 'older than running version 100' "$LOG_FILE" || fail "older bundle was not rejected as a downgrade"
expect_slot_b_unchanged "older bundle"
printf 'ok - an older bundle is rejected before writing slots\n'

run_update install --allow-downgrade "$TEST_DIR/older.tar" > "$LOG_FILE" 2>&1
grep -Fq 'downgrading from version 100 to 99' "$LOG_FILE" || fail "downgrade was not reported"
expect_slot_b_installed "allowed downgrade"
printf 'ok - --allow-downgrade installs an older bundle\n'

make_versioned unversioned ''
reset_slot_b
expect_failure install "$TEST_DIR/unversioned.tar"
grep -Fq 'bundle has no version' "$LOG_FILE" || fail "unversioned bundle was not rejected for its version"
expect_slot_b_unchanged "unversioned bundle"
run_update install --allow-downgrade "$TEST_DIR/unversioned.tar" > "$LOG_FILE" 2>&1
expect_slot_b_installed "allowed unversioned bundle"
printf 'ok - a bundle without a version needs --allow-downgrade\n'

for case_name in duplicate:'version 200\nversion 201\n' word:'version abc\n' zero:'version 0200\n' long:'version 1234567890123456789\n'; do
	make_versioned "bad-version-${case_name%%:*}" "${case_name#*:}"
	reset_slot_b
	expect_failure install --allow-downgrade "$TEST_DIR/bad-version-${case_name%%:*}.tar"
	expect_slot_b_unchanged "bad version (${case_name%%:*})"
done
printf 'ok - malformed manifest versions are rejected even with --allow-downgrade\n'

mkdir -p "$TEST_DIR/version-tampered"
cp "$TEST_DIR/older/rootfs.squashfs" "$TEST_DIR/older/boot.vfat" "$TEST_DIR/older/manifest.sig" "$TEST_DIR/version-tampered/"
sed 's/^version 99$/version 300/' "$TEST_DIR/older/manifest" > "$TEST_DIR/version-tampered/manifest"
tar -cf "$TEST_DIR/version-tampered.tar" -C "$TEST_DIR/version-tampered" rootfs.squashfs boot.vfat manifest manifest.sig
reset_slot_b
expect_failure install "$TEST_DIR/version-tampered.tar"
grep -Fq 'signature verification failed' "$LOG_FILE" || fail "raised version was not caught by the signature"
expect_slot_b_unchanged "version-tampered bundle"
printf 'ok - raising the version breaks the signature\n'

mv "$RUNNING_VERSION" "$RUNNING_VERSION.saved"
reset_slot_b
expect_failure install "$TEST_DIR/good.tar"
grep -Fq 'cannot read the running version' "$LOG_FILE" || fail "missing running version was not reported"
expect_slot_b_unchanged "missing running version"
mv "$RUNNING_VERSION.saved" "$RUNNING_VERSION"
printf 'ok - install refuses when the running version is unknown\n'

expect_failure install --allow-downgrade
expect_failure install --force "$TEST_DIR/good.tar"
printf 'ok - install rejects a missing bundle and unknown options\n'

printf 'old-rootfs-a\n' > "${PARTITION_PREFIX}5"
printf 'old-boot-a\n' > "${PARTITION_PREFIX}2"
set_dt 3 0
run_update install "$TEST_DIR/good.tar" > "$LOG_FILE"
dd if="${PARTITION_PREFIX}5" bs=4M iflag=count_bytes count="$root_bytes" 2>/dev/null > "$TEST_DIR/root-a-readback"
dd if="${PARTITION_PREFIX}2" bs=4M iflag=count_bytes count="$boot_bytes" 2>/dev/null > "$TEST_DIR/boot-a-readback"
cmp "$TEST_DIR/good/rootfs.squashfs" "$TEST_DIR/root-a-readback" || fail "slot A rootfs read-back differs"
cmp "$TEST_DIR/good/boot.vfat" "$TEST_DIR/boot-a-readback" || fail "slot A boot read-back differs"
[ "$(cat "$STATE_DIR/installed")" = 2 ] || fail "slot A install state was not recorded"
printf 'ok - the same boot bundle installs and verifies slot A\n'

# shellcheck disable=SC2016 # The generated test command must retain its variable expansion.
printf '#!/bin/sh\nprintf "%%s\\n" "$*" >> "$MSD_TEST_REBOOT_LOG"\n' > "$TEST_DIR/bin/reboot"
chmod +x "$TEST_DIR/bin/reboot"
set_autoboot 3 2
MSD_TEST_REBOOT_LOG="$TEST_DIR/reboot.log" \
PATH="$TEST_DIR/bin:$PATH" \
MSD_UPDATE_DT_DIR="$DT_DIR" \
MSD_UPDATE_P1_DIR="$P1_DIR" \
MSD_UPDATE_STATE_DIR="$STATE_DIR" \
MSD_UPDATE_PARTITION_PREFIX="$PARTITION_PREFIX" \
/bin/sh "$UPDATER" try
[ "$(cat "$TEST_DIR/reboot.log")" = '0 tryboot' ] || fail "try did not request reboot '0 tryboot'"
printf 'ok - try requires and selects the verified slot\n'

printf 'All msd-update host tests passed.\n'
