#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
	printf 'Usage: %s <sdcard.img>\n' "$0" >&2
	exit 2
fi

image=$1
if [ ! -r "$image" ]; then
	printf 'Image is not readable: %s\n' "$image" >&2
	exit 1
fi

if ! command -v sfdisk >/dev/null 2>&1; then
	printf 'Required command not found: sfdisk\n' >&2
	exit 1
fi

partition_table=$(sfdisk --dump "$image") || {
	printf 'Cannot read partition table from %s\n' "$image" >&2
	exit 1
}

printf '%s\n' "$partition_table" | awk '
	$2 == ":" {
		count++
		start = ""
		for (i = 3; i <= NF; i++) {
			if (index($i, "start=") == 1) {
				start = substr($i, 7)
				if (start == "") {
					start = $(i + 1)
				}
				sub(/,$/, "", start)
				break
			}
		}

		if (start !~ /^[0-9]+$/) {
			printf "Invalid start sector for %s\n", $1 > "/dev/stderr"
			failed = 1
		} else if (start % 8192 != 0) {
			printf "Unaligned start sector for %s: %s (expected a multiple of 8192)\n", $1, start > "/dev/stderr"
			failed = 1
		}
	}
	END {
		if (count != 7) {
			printf "Expected exactly 7 partition entries; found %d\n", count > "/dev/stderr"
			failed = 1
		}
		if (failed) {
			exit 1
		}
		printf "OK: %d partition entries; all starts align to 8192 sectors.\n", count
	}
'
