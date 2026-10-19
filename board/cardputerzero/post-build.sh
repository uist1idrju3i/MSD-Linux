#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
mkdir -p "$target_dir/run" "$target_dir/tmp" "$target_dir/var/log" "$target_dir/data"
test -x "$target_dir/etc/init.d/S98msd-ready"
test -f "$target_dir/etc/fstab"

keymap="$target_dir/usr/share/keymaps/tca8418_keypad_m5stack_keymap.map"
test -f "$keymap"
for keymaps in "$target_dir/usr/share/keymaps" "$target_dir/usr/share/kbd/keymaps"; do
	if [ -d "$keymaps" ]; then
		find "$keymaps" -depth ! -type d ! -path "$keymap" -delete
		find "$keymaps" -depth -type d -empty -delete
	fi
done
for data_dir in consolefonts consoletrans unimaps; do
	rm -rf "${target_dir:?}/usr/share/$data_dir" "${target_dir:?}/usr/share/kbd/$data_dir"
done

mdev_conf="$target_dir/etc/mdev.conf"
test -f "$mdev_conf"
insert_mdev_rule() {
	rule="$1"
	if grep -Fqx "$rule" "$mdev_conf"; then
		return
	fi
	awk -v rule="$rule" '
		!inserted && /^\$MODALIAS=/ { print rule; inserted = 1 }
		{ print }
		END { if (!inserted) print rule }
	' "$mdev_conf" > "$mdev_conf.new"
	mv "$mdev_conf.new" "$mdev_conf"
}

insert_mdev_rule "-\$SUBSYSTEM=input;input/event[0-9]+ root:root 640 */usr/libexec/msd/cardputer-keyboard \"\$ACTION\" \"\$MDEV\""
insert_mdev_rule "-\$POWERFAIL=1 root:root 660 */usr/libexec/msd/powerfail-notify"

base_dir="${BASE_DIR:-}"
host_dir="${HOST_DIR:-}"
if [ -z "$base_dir" ] || [ -z "$host_dir" ]; then
	printf '%s\n' 'BASE_DIR and HOST_DIR must be set for update signing.' >&2
	exit 1
fi
host_openssl="$host_dir/bin/openssl"
if [ ! -x "$host_openssl" ]; then
	printf 'Required Buildroot host OpenSSL binary is missing: %s\n' "$host_openssl" >&2
	exit 1
fi

if [ -n "${MSD_UPDATE_SIGNING_KEY:-}" ]; then
	signing_key="$MSD_UPDATE_SIGNING_KEY"
	key_origin=release
else
	signing_key="$base_dir/msd-update-dev-key.pem"
	key_origin=development
	if [ ! -f "$signing_key" ]; then
		printf '%s\n' 'WARNING: generating a development update-signing key; use MSD_UPDATE_SIGNING_KEY for releases.' >&2
		(
			umask 077
			"$host_openssl" genpkey -algorithm Ed25519 -out "$signing_key"
		)
	else
		printf '%s\n' 'WARNING: using the development update-signing key; do not ship this key for releases.' >&2
	fi
	chmod 0600 "$signing_key"
fi
test -r "$signing_key"

mkdir -p "$target_dir/etc/msd-update"
"$host_openssl" pkey -in "$signing_key" -pubout \
	-out "$target_dir/etc/msd-update/update-key.pem"
printf '%s\n' "$key_origin" > "$target_dir/etc/msd-update/key-origin"
