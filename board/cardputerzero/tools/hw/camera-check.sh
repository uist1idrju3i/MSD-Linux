#!/bin/sh
# CardputerZero のカメラ（IMX219）を実機で確認するスクリプト。
# シリアルコンソール上の target で実行する。
# 確認結果と生ログを /tmp/camera-check（第 1 引数で変更可）に残す。
# Lite（センサー未実装）でも実行し、probe failure の実際の kernel message を採取する。

set -u

out_dir="${1:-/tmp/camera-check}"
mkdir -p "$out_dir"

pass=0
fail=0
info() { printf 'INFO %s\n' "$*"; }
ok() { printf 'PASS %s\n' "$*"; pass=$((pass + 1)); }
ng() { printf 'FAIL %s\n' "$*"; fail=$((fail + 1)); }

# 1. kernel の probe 結果（sensor ID / 失敗 message を採取）
dmesg > "$out_dir/dmesg.txt"
if grep -qi 'imx219' "$out_dir/dmesg.txt"; then
	grep -i 'imx219' "$out_dir/dmesg.txt" | while IFS= read -r line; do
		info "dmesg: $line"
	done
	ok 'imx219 の kernel message あり'
else
	ng 'imx219 の kernel message なし（probe failure か module 未ロード）'
fi

# 2. module のロード状態
for mod in imx219 bcm2835_unicam; do
	if grep -qw "$mod" /proc/modules; then
		ok "module ロード済み: $mod"
	else
		ng "module 未ロード: $mod"
	fi
done

# 3. media topology（CSI1 2-lane の配線を確認）
if command -v media-ctl >/dev/null 2>&1 && \
	media-ctl -p > "$out_dir/media-topology.txt" 2>&1; then
	if grep -qi 'imx219' "$out_dir/media-topology.txt"; then
		ok 'media topology に imx219 entity あり'
	else
		ng 'media topology に imx219 entity なし'
	fi
	grep -i 'csi\|unicam\|lane' "$out_dir/media-topology.txt" | \
		while IFS= read -r line; do info "topology: $line"; done
else
	ng 'media-ctl -p の実行に失敗'
fi

# 4. capture node と形式一覧
video=/dev/video0
if [ -c "$video" ]; then
	ok "capture node あり: $video"
else
	ng "capture node なし: $video"
fi

if command -v v4l2-ctl >/dev/null 2>&1; then
	if v4l2-ctl -d "$video" --list-formats-ext > "$out_dir/formats.txt" 2>&1; then
		ok '形式一覧の取得に成功'
		grep 'Size:\|Pixel' "$out_dir/formats.txt" | while IFS= read -r line; do
			info "format: $line"
		done
	else
		ng 'v4l2-ctl --list-formats-ext に失敗'
	fi

	# IMX219 の full resolution RAW10（SRGGB10P = RG10）
	if v4l2-ctl -d "$video" \
		--set-fmt-video=width=3280,height=2464,pixelformat=RG10 \
		> "$out_dir/set-fmt.txt" 2>&1; then
		ok 'format 設定 3280x2464 RG10'
	else
		ng 'format 設定に失敗（formats.txt で対応形式を確認）'
	fi

	if v4l2-ctl -d "$video" --stream-mmap=3 --stream-count=30 \
		> "$out_dir/stream.txt" 2>&1; then
		ok 'stream-mmap で 30 frame 受信'
		grep -i 'frame\|fps' "$out_dir/stream.txt" | tail -3 | \
			while IFS= read -r line; do info "stream: $line"; done
	else
		ng 'stream-mmap に失敗'
	fi

	if v4l2-ctl -d "$video" --stream-mmap=3 --stream-count=1 \
		--stream-to="$out_dir/frame.raw" > "$out_dir/capture.txt" 2>&1; then
		bytes="$(wc -c < "$out_dir/frame.raw")"
		if [ "$bytes" -gt 0 ]; then
			ok "1 frame 採取: $bytes bytes"
		else
			ng '採取した frame が空'
		fi
	else
		ng '1 frame の採取に失敗'
	fi
else
	ng 'v4l2-ctl が見つからない'
fi

printf 'RESULT pass=%d fail=%d logs=%s\n' "$pass" "$fail" "$out_dir"
[ "$fail" -eq 0 ]
