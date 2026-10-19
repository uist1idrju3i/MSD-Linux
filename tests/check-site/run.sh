#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
checker="$repo_root/.github/scripts/check-site.py"
pattern_generator="$repo_root/docs/logo/tools/site_patterns.py"
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

write_webp() {
	python3 - "$fixture/public_html/images/msd-linux-social-1280x640.webp" \
		"${1:-1280}" "${2:-640}" "${3:-VP8L}" "${4:-ok}" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
width = int(sys.argv[2])
height = int(sys.argv[3])
chunk = sys.argv[4].encode("ascii")
riff_mode = sys.argv[5]
dimensions = (width - 1) | ((height - 1) << 14)
payload = bytes([0x2F]) + struct.pack("<I", dimensions) + b"\x00\x00\x00"
riff_size = 4 + 8 + len(payload)
if riff_mode == "bad-riff":
    riff_size -= 1
path.write_bytes(
    b"RIFF"
    + struct.pack("<I", riff_size)
    + b"WEBP"
    + chunk
    + struct.pack("<I", len(payload))
    + payload
)
PY
}

new_repo() {
	rm -rf "$fixture"
	mkdir -p "$fixture"
	git -C "$fixture" init -q
	mkdir -p "$fixture/public_html/images" "$fixture/docs/logo/tools"
	cp "$pattern_generator" "$fixture/docs/logo/tools/site_patterns.py"

	write_file public_html/index.html "<!doctype html>
<html><head>
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src 'self'; style-src 'self'\">
<link rel=\"canonical\" href=\"https://muromi.moe/\">
<meta property=\"og:url\" content=\"https://muromi.moe/\">
<meta property=\"og:image\" content=\"https://muromi.moe/images/msd-linux-social-1280x640.webp\">
<meta property=\"og:image:type\" content=\"image/webp\">
<meta property=\"og:image:width\" content=\"1280\">
<meta property=\"og:image:height\" content=\"640\">
<link rel=\"stylesheet\" href=\"site.css\">
</head><body><img src=\"images/msd-linux-mark.svg\"></body></html>
"
	write_file public_html/404.html "<!doctype html>
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src 'self'; style-src 'self'\">
<link rel=\"stylesheet\" href=\"/site.css\">
<img src=\"/images/msd-linux-mark.svg\">
<a href=\"/\">Home</a>
"
	write_file public_html/site.css 'body { background-image: url("images/flow-light.svg"); }
'

	write_file docs/logo/msd-linux-logo.svg '<svg>logo</svg>
'
	write_file docs/logo/msd-linux-logo-dark.svg '<svg>dark logo</svg>
'
	write_file docs/logo/msd-linux-mark.svg '<svg>mark</svg>
'
	for name in msd-linux-logo.svg msd-linux-logo-dark.svg msd-linux-mark.svg; do
		cp "$fixture/docs/logo/$name" "$fixture/public_html/images/$name"
	done
	write_webp
	python3 "$fixture/docs/logo/tools/site_patterns.py"
	git -C "$fixture" add -A
}

run_check() {
	if output="$(python3 "$checker" --root "$fixture" "$@" 2>&1)"; then
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
write_webp 1280 640 'VP8 '
git -C "$fixture" add public_html/images/msd-linux-social-1280x640.webp
run_check
expect_status 1
expect_output 'VP8L のみを使ってください（検出: VP8 ）'
printf 'ok - rejects lossy VP8 chunks\n'

new_repo
write_webp 1280 640 VP8X
git -C "$fixture" add public_html/images/msd-linux-social-1280x640.webp
run_check
expect_status 1
expect_output 'VP8L のみを使ってください（検出: VP8X）'
printf 'ok - rejects extended VP8X chunks\n'

new_repo
write_webp 1200 630
git -C "$fixture" add public_html/images/msd-linux-social-1280x640.webp
run_check
expect_status 1
expect_output 'WebP の寸法は 1280x640 が必要です（検出: 1200x630）'
printf 'ok - rejects incorrect WebP dimensions\n'

new_repo
sed '/og:image:type/d' "$fixture/public_html/index.html" > "$fixture/public_html/index.html.new"
mv "$fixture/public_html/index.html.new" "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output 'og:image:type は image/webp を指定してください'
printf 'ok - rejects missing og:image:type\n'

new_repo
sed 's#content="image/webp"#content="image/png"#' "$fixture/public_html/index.html" > "$fixture/public_html/index.html.new"
mv "$fixture/public_html/index.html.new" "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output 'og:image:type は image/webp を指定してください'
printf 'ok - rejects a PNG og:image:type\n'

new_repo
write_webp 1280 640 VP8L bad-riff
git -C "$fixture" add public_html/images/msd-linux-social-1280x640.webp
run_check
expect_status 1
expect_output 'RIFF サイズがファイル長と一致しません'
printf 'ok - rejects a mismatched RIFF size\n'

new_repo
write_file "public_html/""README.md" 'Not site content.
'
git -C "$fixture" add "public_html/""README.md"
run_check
expect_status 1
expect_output 'public_html/ はサイト専用です。文書は docs/ に置いてください。'
printf 'ok - rejects documentation files in the site root\n'

new_repo
printf '<script>bad()</script>\n' >> "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output 'script 要素は禁止です'
printf 'ok - rejects script elements\n'

new_repo
printf '<img src="https://example.com/image.png">\n' >> "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output '外部リソースを参照できません'
printf 'ok - rejects external image resources\n'

new_repo
sed 's#https://muromi.moe/#https://other.example/#' "$fixture/public_html/index.html" > "$fixture/public_html/index.html.new"
mv "$fixture/public_html/index.html.new" "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output 'SITE_ORIGIN'
printf 'ok - rejects a canonical URL using another host\n'

new_repo
sed 's#https://muromi.moe/#/#' "$fixture/public_html/index.html" > "$fixture/public_html/index.html.new"
mv "$fixture/public_html/index.html.new" "$fixture/public_html/index.html"
git -C "$fixture" add public_html/index.html
run_check
expect_status 1
expect_output 'SITE_ORIGIN'
printf 'ok - rejects relative metadata URLs\n'

new_repo
write_file public_html/images/msd-linux-mark.svg '<svg>changed</svg>
'
git -C "$fixture" add public_html/images/msd-linux-mark.svg
run_check
expect_status 1
expect_output 'マスターと内容が一致しません'
printf 'ok - rejects a logo copy that differs from its master\n'

new_repo
write_file "public_html/""CNAME" 'muromi.moe'
git -C "$fixture" add "public_html/""CNAME"
run_check
expect_status 1
expect_output 'public_html/ はサイト専用です。文書は docs/ に置いてください。'
printf 'ok - rejects the forbidden CNAME marker\n'

new_repo
run_check --expect-pages-cname muromi.moe
expect_status 0
expect_output 'errors=0'
printf 'ok - accepts the expected Pages domain\n'

new_repo
run_check --expect-pages-cname ' MuRoMi.MoE '
expect_status 0
expect_output 'errors=0'
printf 'ok - trims and case-folds the expected Pages domain\n'

new_repo
run_check --expect-pages-cname other.example
expect_status 1
expect_output 'SITE_ORIGIN'
printf 'ok - rejects a Pages domain that differs from SITE_ORIGIN\n'

new_repo
run_check --expect-pages-cname ''
expect_status 1
expect_output 'Pages の Settings にドメインがありません'
printf 'ok - rejects a missing Pages domain\n'

printf 'All check-site tests passed.\n'
