#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
mkdir -p "$target_dir/run" "$target_dir/tmp" "$target_dir/var/log" "$target_dir/data" \
	"$target_dir/proc" "$target_dir/sys" "$target_dir/dev/pts" "$target_dir/dev/shm"

# Update this inventory when executable rootfs-overlay scripts gain commands.
required_target_commands='
awk
cat
cmp
dd
fsck.ext4
fsync
grep
ln
loadkeys
mkdir
mkfs.ext4
mount
msd-data-grow
msd-hwinfo
msd-update
mktemp
mv
od
openssl
partx
readlink
reboot
resize2fs
rm
sfdisk
sha256sum
sed
sh
sync
tar
touch
tr
umount
watchdog
wc
'
missing_target_commands=0
while IFS= read -r target_command; do
	if [ -z "$target_command" ]; then
		continue
	fi
	command_found=0
	for path_dir in bin sbin usr/bin usr/sbin; do
		if [ -x "$target_dir/$path_dir/$target_command" ]; then
			command_found=1
			break
		fi
	done
	if [ "$command_found" -eq 0 ]; then
		printf 'Required target command is missing: %s\n' "$target_command" >&2
		missing_target_commands=1
	fi
done <<EOF
$required_target_commands
EOF
if [ "$missing_target_commands" -ne 0 ]; then
	exit 1
fi

seedrng_defaults="$target_dir/etc/default/seedrng"
if ! grep -Fxq 'SEEDRNG_ARGS="--seed-dir=/data/seedrng"' "$seedrng_defaults"; then
	printf 'Seedrng state directory must be configured on /data: %s\n' \
		"$seedrng_defaults" >&2
	exit 1
fi

seedrng_init="$target_dir/etc/init.d/S01seedrng"
seedrng_late_init="$target_dir/etc/init.d/S05seedrng"
if [ -f "$seedrng_init" ]; then
	if [ -e "$seedrng_late_init" ]; then
		printf 'Both seedrng init paths exist: %s and %s\n' \
			"$seedrng_init" "$seedrng_late_init" >&2
		exit 1
	fi
	mv "$seedrng_init" "$seedrng_late_init"
elif [ ! -f "$seedrng_late_init" ]; then
	printf 'Buildroot seedrng init script is missing: %s\n' "$seedrng_init" >&2
	exit 1
fi
test -x "$seedrng_late_init"

test -x "$target_dir/etc/init.d/S98msd-ready"
test -f "$target_dir/etc/fstab"
for mountpoint in /proc /sys /run /tmp; do
	if ! grep -Eq "^[^#[:space:]]+[[:space:]]+${mountpoint}[[:space:]]" "$target_dir/etc/fstab"; then
		printf 'Required mount point is missing from target fstab: %s\n' "$mountpoint" >&2
		exit 1
	fi
done

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
	if grep -Fqx -e "$rule" "$mdev_conf"; then
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

duplicate_mdev_rules="$(awk '
	/^[[:space:]]*($|#)/ { next }
	++seen[$0] == 2 { print $0 }
' "$mdev_conf" | sort)"
if [ -n "$duplicate_mdev_rules" ]; then
	printf 'Duplicate non-comment mdev.conf lines:\n%s\n' \
		"$duplicate_mdev_rules" >&2
	exit 1
fi

base_dir="${BASE_DIR:-}"
host_dir="${HOST_DIR:-}"
if [ -z "$base_dir" ] || [ -z "$host_dir" ]; then
	printf '%s\n' 'BASE_DIR and HOST_DIR must be set for update signing.' >&2
	exit 1
fi
busybox_config=
for candidate in "$base_dir"/build/busybox-*/.config; do
	if [ -f "$candidate" ]; then
		busybox_config="$candidate"
		break
	fi
done
if [ -z "$busybox_config" ]; then
	printf 'Buildroot BusyBox configuration is missing under %s/build.\n' "$base_dir" >&2
	exit 1
fi
required_busybox_options='
CONFIG_DESKTOP=y
CONFIG_FEATURE_DD_IBS_OBS=y
CONFIG_FEATURE_MD5_SHA1_SUM_CHECK=y
'
while IFS= read -r busybox_option; do
	if [ -z "$busybox_option" ]; then
		continue
	fi
	if ! grep -Fxq "$busybox_option" "$busybox_config"; then
		printf 'Required BusyBox option is missing: %s\n' "$busybox_option" >&2
		exit 1
	fi
done <<EOF
$required_busybox_options
EOF

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

"$(dirname "$0")/tools/sign-modules.sh" "$target_dir" "$base_dir/build/linux-custom"
