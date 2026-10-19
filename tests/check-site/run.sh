#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
checker="$repo_root/.github/scripts/check-site.py"
pattern_generator="$repo_root/documentation/logo/tools/site_patterns.py"
test_root="$(mktemp -d)"
fixture="$test_root/repo"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

write_file() {
	file="$fixture/$1"
	mkdir -p "$(dirname "$file")"
	printf '%s' "$2" > "$file"
}

new_repo() {
	rm -rf "$fixture"
	mkdir -p "$fixture"
	git -C "$fixture" init -q
	mkdir -p "$fixture/docs/images" "$fixture/documentation/logo/tools"
	cp "$pattern_generator" "$fixture/documentation/logo/tools/site_patterns.py"

	write_file docs/CNAME 'muromi.moe
'
	: > "$fixture/docs/.nojekyll"
	write_file docs/index.html "<!doctype html>
<html><head>
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src 'self'; style-src 'self'\">
<link rel=\"canonical\" href=\"https://muromi.moe/\">
<meta property=\"og:url\" content=\"https://muromi.moe/\">
<meta property=\"og:image\" content=\"https://muromi.moe/images/msd-linux-social-1280x640.png\">
<link rel=\"stylesheet\" href=\"site.css\">
</head><body><img src=\"images/msd-linux-mark.svg\"></body></html>
"
	write_file docs/404.html "<!doctype html>
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src 'self'; style-src 'self'\">
<link rel=\"stylesheet\" href=\"/site.css\">
<img src=\"/images/msd-linux-mark.svg\">
<a href=\"/\">Home</a>
"
	write_file docs/site.css 'body { background-image: url("images/flow-light.svg"); }
'

	write_file documentation/logo/msd-linux-logo.svg '<svg>logo</svg>
'
	write_file documentation/logo/msd-linux-logo-dark.svg '<svg>dark logo</svg>
'
	write_file documentation/logo/msd-linux-mark.svg '<svg>mark</svg>
'
	write_file documentation/logo/msd-linux-social-1280x640.png 'png data
'
	for name in msd-linux-logo.svg msd-linux-logo-dark.svg msd-linux-mark.svg msd-linux-social-1280x640.png; do
		cp "$fixture/documentation/logo/$name" "$fixture/docs/images/$name"
	done
	python3 "$fixture/documentation/logo/tools/site_patterns.py"
	git -C "$fixture" add -A
}

run_check() {
	if output="$(python3 "$checker" --root "$fixture" 2>&1)"; then
		status=0
	else
		status=$?
	fi
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

new_repo
run_check
expect_status 0
expect_output 'errors=0'
printf 'ok - accepts a valid local GitHub Pages site\n'

new_repo
write_file "docs/""README.md" 'Not site content.
'
git -C "$fixture" add "docs/""README.md"
run_check
expect_status 1
expect_output 'docs/ はサイト専用'
printf 'ok - rejects documentation files in the site root\n'

new_repo
printf '<script>bad()</script>\n' >> "$fixture/docs/index.html"
git -C "$fixture" add docs/index.html
run_check
expect_status 1
expect_output 'script 要素は禁止です'
printf 'ok - rejects script elements\n'

new_repo
printf '<img src="https://example.com/image.png">\n' >> "$fixture/docs/index.html"
git -C "$fixture" add docs/index.html
run_check
expect_status 1
expect_output '外部リソースを参照できません'
printf 'ok - rejects external image resources\n'

new_repo
write_file docs/CNAME 'other.example
'
git -C "$fixture" add docs/CNAME
run_check
expect_status 1
expect_output 'CNAME の HTTPS URL に一致'
printf 'ok - rejects canonical and OGP hosts that differ from CNAME\n'

new_repo
write_file docs/images/msd-linux-mark.svg '<svg>changed</svg>
'
git -C "$fixture" add docs/images/msd-linux-mark.svg
run_check
expect_status 1
expect_output 'マスターと内容が一致しません'
printf 'ok - rejects a logo copy that differs from its master\n'

printf 'All check-site tests passed.\n'
