#!/bin/sh
# SVG マスターから splash 用・SNS 用の派生ファイルを作り直す。
# 必要なもの: rsvg-convert（librsvg）、ImageMagick 6 の convert、python3、cwebp、dwebp
set -eu
cd "$(dirname "$0")"

command -v rsvg-convert >/dev/null || { echo "rsvg-convert が必要です" >&2; exit 1; }
command -v convert >/dev/null || { echo "ImageMagick の convert が必要です" >&2; exit 1; }
command -v cwebp >/dev/null || { echo "cwebp（libwebp）が必要です" >&2; exit 1; }
command -v dwebp >/dev/null || { echo "dwebp（libwebp）が必要です" >&2; exit 1; }

splash=splash/msd-linux-splash-320x170

# 320x170 の PNG（LCD と同じ解像度、横置き）
rsvg-convert -w 320 -h 170 "$splash.svg" -o "$splash.png"

# RGB565 リトルエンディアンの生データ（108,800 バイト、ヘッダーなし）
convert "$splash.png" -depth 8 rgb:- | python3 -c '
import struct, sys
d = sys.stdin.buffer.read()
out = bytearray()
for i in range(0, len(d), 3):
    r, g, b = d[i], d[i + 1], d[i + 2]
    out += struct.pack("<H", ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3))
sys.stdout.buffer.write(out)
' > "$splash.rgb565"
test "$(wc -c < "$splash.rgb565")" -eq 108800

# Linux カーネルの起動ロゴ形式（ASCII PPM、224 色以下、80x80）
rsvg-convert -w 80 -h 80 msd-linux-mark.svg | \
  convert png:- -background black -flatten -colors 224 -compress none \
    splash/logo_msd_clut224.ppm

# GitHub の Social preview（1280x640、1 MB 未満）
rsvg-convert -w 1280 -h 640 msd-linux-social-1280x640.svg -o msd-linux-social-1280x640.png
test "$(wc -c < msd-linux-social-1280x640.png)" -lt 1000000

# GitHub Pages のサイトでも同じロゴを使う。
site_images=../../public_html/images
mkdir -p "$site_images"
cp msd-linux-logo.svg msd-linux-logo-dark.svg msd-linux-mark.svg \
  "$site_images/"
python3 tools/site_patterns.py
for image in msd-linux-logo.svg msd-linux-logo-dark.svg msd-linux-mark.svg; do
  cmp "$image" "$site_images/$image"
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' 0
trap 'exit 1' HUP INT TERM
rsvg-convert -w 1280 -h 640 msd-linux-social-1280x640.svg -o "$tmp/social.png"
webp="$site_images/msd-linux-social-1280x640.webp"
cwebp -quiet -z 9 -metadata none "$tmp/social.png" -o "$webp"
dwebp -quiet "$webp" -ppm -o "$tmp/decoded.ppm"
convert "$tmp/social.png" -depth 8 "rgb:$tmp/source.rgb"
convert "$tmp/decoded.ppm" -depth 8 "rgb:$tmp/decoded.rgb"
cmp "$tmp/source.rgb" "$tmp/decoded.rgb"
