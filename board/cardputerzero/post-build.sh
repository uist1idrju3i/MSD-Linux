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
