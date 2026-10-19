#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
ALLOWLIST_FILE="${SCRIPT_DIR}/serial-allowlist.txt"
ERROR_PATTERN='(^|\] )(BUG:|Kernel panic|Internal error: Oops|Unable to handle kernel|segfault)|Call trace:|mount: mounting .* failed|can.t create directory|overlayfs: failed|Failed to mount|Read-only file system|: not found$|(^|\] )msd-[[:alpha:]-]+: .*(fail|cannot|unable)|(^|\] )msd-[[:alpha:]-]+ failed; |(^|[[:space:]])Starting [^:]+:.*FAIL$|(^|[[:space:]])Stopping [^:]+:.*FAIL$|^FAIL$'
TRACE_FRAME_PATTERN='^[^[]*\[[[:space:]]*[0-9.]+\][[:space:]]+[[:alnum:]_.]+\+0x[[:xdigit:]]+/0x[[:xdigit:]]+'

if [ "$#" -ne 1 ] || [ ! -r "$1" ]; then
	printf 'Usage: %s <readable serial log>\n' "$0" >&2
	exit 2
fi
if [ ! -r "$ALLOWLIST_FILE" ]; then
	printf 'Serial allowlist is not readable: %s\n' "$ALLOWLIST_FILE" >&2
	exit 2
fi

ALLOW_PATTERNS=()
while IFS= read -r allow_pattern || [ -n "$allow_pattern" ]; do
	case "$allow_pattern" in
		''|\#*) continue ;;
	esac
	ALLOW_PATTERNS+=("$allow_pattern")
done <"$ALLOWLIST_FILE"

is_allowlisted() {
	local line="$1"
	local pattern

	for pattern in "${ALLOW_PATTERNS[@]}"; do
		if [[ "$line" =~ $pattern ]]; then
			return 0
		fi
	done
	return 1
}

shopt -s nocasematch
found_error=false
pending_allowed_trace=false
in_allowed_trace=false
while IFS= read -r line || [ -n "$line" ]; do
	if [ "$in_allowed_trace" = true ]; then
		if [[ "$line" == *"---[ end trace "* ]]; then
			in_allowed_trace=false
			continue
		fi
		if [[ "$line" =~ $TRACE_FRAME_PATTERN ]]; then
			continue
		fi
		in_allowed_trace=false
	fi

	if is_allowlisted "$line"; then
		if [[ "$line" == *"WARNING:"* ]]; then
			pending_allowed_trace=true
		fi
		continue
	fi

	if [[ "$line" == *"WARNING:"* || "$line" == *"Oops:"* ]]; then
		pending_allowed_trace=false
	fi
	if [ "$pending_allowed_trace" = true ] &&
		[[ "$line" == *"Call trace:"* ]]; then
		pending_allowed_trace=false
		in_allowed_trace=true
		continue
	fi

	if [[ "$line" =~ $ERROR_PATTERN ]]; then
		printf '%s\n' "$line"
		found_error=true
	fi
done <"$1"

if [ "$found_error" = true ]; then
	exit 1
fi
