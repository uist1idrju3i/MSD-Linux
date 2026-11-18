#!/bin/bash
set -euo pipefail

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
checker="$repo_root/.github/scripts/check-experiment-index.sh"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

check() {
	local expected=$1
	local label=$2
	local rc=0
	(cd "$test_root" && bash "$checker") >"$test_root/result.log" 2>&1 || rc=$?
	if [ "$rc" -ne "$expected" ]; then
		cat "$test_root/result.log"
		printf 'not ok - %s: expected %s, got %s\n' "$label" "$expected" "$rc" >&2
		exit 1
	fi
	printf 'ok - %s\n' "$label"
}

mkdir -p "$test_root/docs/experiments"
check 1 'missing README fails'
touch "$test_root/docs/experiments/README.md"
check 0 'empty index without records passes'

touch "$test_root/docs/experiments/record.md"
check 1 'unlisted record fails'
printf '[record](record.md)\n' >"$test_root/docs/experiments/README.md"
check 0 'direct record link passes'

printf '[October](2026-10-index.md)\n' >"$test_root/docs/experiments/README.md"
printf '[record](record.md)\n' >"$test_root/docs/experiments/2026-10-index.md"
check 0 'record in linked monthly index passes'

printf '' >"$test_root/docs/experiments/2026-10-index.md"
check 1 'record missing from linked index fails'
printf '[record](record.md)\n[self](2026-10-index.md)\n' >"$test_root/docs/experiments/2026-10-index.md"
printf '' >"$test_root/docs/experiments/README.md"
check 1 'orphan monthly index cannot index itself or records'

mv "$test_root/docs/experiments/2026-10-index.md" "$test_root/docs/experiments/notes.md"
printf '[notes](notes.md)\n' >"$test_root/docs/experiments/README.md"
check 1 'ordinary record is not an index'

printf '[record](record.md)\n[notes](notes.md)\n' >"$test_root/docs/experiments/README.md"
check 0 'all records directly indexed passes'
printf 'All check-experiment-index tests passed.\n'
