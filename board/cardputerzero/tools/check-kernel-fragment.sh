#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
	printf 'Usage: %s <fragment> <.config>\n' "$0" >&2
	exit 2
fi

fragment=$1
config=$2
if [ ! -r "$fragment" ] || [ ! -r "$config" ]; then
	printf 'Both fragment and .config must be readable.\n' >&2
	exit 2
fi

declare -A actual=()
while IFS= read -r line || [ -n "$line" ]; do
	if [[ "$line" =~ ^(CONFIG_[A-Za-z0-9_]+)=(.*)$ ]]; then
		actual["${BASH_REMATCH[1]}"]=${BASH_REMATCH[2]}
	elif [[ "$line" =~ ^#\ (CONFIG_[A-Za-z0-9_]+)\ is\ not\ set$ ]]; then
		actual["${BASH_REMATCH[1]}"]=n
	fi
done < "$config"

failures=0
line_number=0
while IFS= read -r line || [ -n "$line" ]; do
	line_number=$((line_number + 1))
	symbol=
	expected=
	if [[ "$line" =~ ^(CONFIG_[A-Za-z0-9_]+)=(.*)$ ]]; then
		symbol=${BASH_REMATCH[1]}
		expected=${BASH_REMATCH[2]}
	elif [[ "$line" =~ ^#\ (CONFIG_[A-Za-z0-9_]+)\ is\ not\ set$ ]]; then
		symbol=${BASH_REMATCH[1]}
		expected=n
	else
		continue
	fi

	got=${actual[$symbol]-n}
	if [ "$got" != "$expected" ]; then
		printf '%s:%d: expected %s=%s, got %s\n' \
			"$fragment" "$line_number" "$symbol" "$expected" "$got" >&2
		failures=$((failures + 1))
	fi
done < "$fragment"

if [ "$failures" -ne 0 ]; then
	printf 'Kernel fragment check failed: %d mismatch(es).\n' "$failures" >&2
	exit 1
fi

printf 'Kernel fragment matches %s.\n' "$config"
