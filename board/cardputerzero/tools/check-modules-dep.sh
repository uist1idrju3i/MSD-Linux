#!/bin/sh
set -eu

target_dir="${1:?Buildroot must pass TARGET_DIR}"
modules_dir="$target_dir/lib/modules"
found_modules_dep=0

for modules_dep in "$modules_dir"/*/modules.dep; do
	if [ ! -f "$modules_dep" ]; then
		continue
	fi

	found_modules_dep=1
	if [ ! -s "$modules_dep" ]; then
		printf 'Kernel module dependency list is empty: %s\n' "$modules_dep" >&2
		exit 1
	fi
	if ! grep -Eq '(^|/)usbnet\.ko(\.[[:alnum:]]+)?[[:space:]]*:' "$modules_dep"; then
		printf 'Kernel module dependency list is missing usbnet: %s\n' "$modules_dep" >&2
		exit 1
	fi
done

if [ "$found_modules_dep" -eq 0 ]; then
	printf 'Kernel module dependency list is missing under %s\n' "$modules_dir" >&2
	exit 1
fi
