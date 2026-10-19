#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
checker="$repo_root/.github/scripts/check-jisx0213.py"
test_root="$(mktemp -d)"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

run_check() {
	if output="$(python3 "$checker" "$@" 2>&1)"; then
		status=0
	else
		status=$?
	fi
}

write_text() {
	printf '%b' "$2" > "$test_root/$1"
}

expect_status() {
	expected="$1"
	[ "$status" -eq "$expected" ] || fail "expected exit $expected, got $status: $output"
}

expect_output() {
	needle="$1"
	case "$output" in
		*"$needle"*) ;;
		*) fail "output did not contain $needle: $output" ;;
	esac
}

write_text allowed.txt 'ASCII ①。日本語。—―～≧か゚
'
run_check "$test_root/allowed.txt"
expect_status 0
printf 'ok - accepts ASCII, kana, kanji, mapped symbols, alternates, and a JIS sequence\n'

write_text hanzi.txt '这说'
run_check "$test_root/hanzi.txt"
expect_status 1
expect_output 'U+8FD9'
printf 'ok - rejects out-of-range hanzi with its code point\n'

write_text emoji.txt '🥈'
run_check "$test_root/emoji.txt"
expect_status 1
printf 'ok - rejects emoji\n'

write_text micro.txt 'µ'
run_check "$test_root/micro.txt"
expect_status 1
printf 'ok - rejects MICRO SIGN\n'

write_text mark.txt '゚'
run_check "$test_root/mark.txt"
expect_status 1
printf 'ok - rejects a combining mark outside its JIS sequence\n'

write_text added.txt '关'
run_check "$test_root/added.txt"
expect_status 0
expect_output 'warning:'
run_check --strict "$test_root/added.txt"
expect_status 1
printf 'ok - warns for a JIS-added ideograph and fails in strict mode\n'

allowlist="$test_root/allowlist.tsv"
printf 'quote\t%s\t🥈\ttest quote\n' "$test_root/quoted.txt" > "$allowlist"
write_text quoted.txt "\`🥈\` and 🥈"
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 1
expect_output 'U+1F948'
write_text quoted.txt "\`🥈\`"
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 0
write_text quoted.txt '~~~\n🥈\n~~~~\n'
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 0
write_text quoted.txt '> 🥈\n'
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 0
printf 'ok - quote allowlist accepts inline code, fenced code, and blockquotes only\n'

printf 'file\t*.txt\t*\ttest source\n' > "$allowlist"
write_text source.txt 'µ🥈'
run_check --allowlist "$allowlist" "$test_root/source.txt"
expect_status 0
printf 'ok - file allowlist accepts all out-of-range characters in matching files\n'

printf 'quote\tquoted.txt\t🥈\tstale\n' > "$allowlist"
write_text quoted.txt 'prose'
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 0
printf 'ok - explicit path scans do not run default-set stale checks\n'

printf 'unknown\tquoted.txt\t🥈\tbad kind\n' > "$allowlist"
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 1
expect_output 'unknown allowlist kind'
printf 'ok - rejects unknown allowlist kinds\n'

printf 'quote\tquoted.txt\t🥈\t\n' > "$allowlist"
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 1
expect_output 'reason must not be empty'
printf 'ok - rejects empty allowlist reasons\n'

printf 'quote\tquoted.txt\t🥈\tvalid\nextra\n' > "$allowlist"
run_check --allowlist "$allowlist" "$test_root/quoted.txt"
expect_status 1
expect_output 'expected four TSV columns'
printf 'ok - rejects malformed allowlist lines\n'

default_repo="$test_root/default-repo"
mkdir -p "$default_repo"
git -C "$default_repo" init -q
printf 'plain text\n' > "$default_repo/readme.md"
git -C "$default_repo" add readme.md
printf 'file\t*.md\t*\tstale file\n' > "$allowlist"
if output="$(cd "$default_repo" && python3 "$checker" --allowlist "$allowlist" 2>&1)"; then
	status=0
else
	status=$?
fi
expect_status 1
expect_output 'stale file allowlist entry'
printf 'ok - reports stale file entries for the default tracked Markdown set\n'

printf 'quote\treadme.md\t🥈\tstale quote\n' > "$allowlist"
if output="$(cd "$default_repo" && python3 "$checker" --allowlist "$allowlist" 2>&1)"; then
	status=0
else
	status=$?
fi
expect_status 1
expect_output 'stale quote allowlist entry'
printf 'ok - reports stale quote characters for the default tracked Markdown set\n'

table_copy="$test_root/tampered-table.txt"
printf 'tampered\n' > "$table_copy"
write_text plain.txt 'plain'
if output="$(MSD_JISX0213_TABLE="$table_copy" python3 "$checker" "$test_root/plain.txt" 2>&1)"; then
	status=0
else
	status=$?
fi
expect_status 2
expect_output 'SHA-256 mismatch'
printf 'ok - rejects a table with an unexpected SHA-256\n'

printf '\377' > "$test_root/invalid-utf8.txt"
run_check "$test_root/invalid-utf8.txt"
expect_status 1
expect_output '無効な UTF-8'
printf 'ok - rejects invalid UTF-8\n'

python3 - "$checker" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("check_jisx0213", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
table = module.load_table()
counts = (len(table.singles), len(table.sequences), len(table.alternates))
assert counts == (11208, 25, 100), counts
print(f"JIS mapping counts: singles={counts[0]} sequences={counts[1]} alternates={counts[2]}")
PY
printf 'ok - mapping table has the expected counts\n'

printf 'All check-jisx0213 tests passed.\n'
