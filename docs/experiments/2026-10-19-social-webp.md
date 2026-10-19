# Social preview の可逆 WebP 符号化

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin
- 関連: PR #44

## 目的と仮説

`docs/logo/msd-linux-social-1280x640.svg` からサイト用 Social preview を生成する可逆 WebP の設定を比較します。`cwebp -z 9 -metadata none` は、画素を保ちながら候補中で最小のファイルを作ると予想します。

## 採否の基準（結果を見る前に書く）

1. デコードした RGB 画素が `rsvg-convert` の 1280×640 ラスターと完全一致する。
2. 同じ条件の再実行で出力バイト列が一致する。
3. 1 と 2 を満たす候補のうち、最小サイズを採用する。符号化時間は手動実行のため採否に使わない。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `188a6a8` |
| ホスト | Ubuntu 22.04.5 LTS、x86_64、Linux 6.8.0-1061-aws |
| 使ったツールの版 | `cwebp` 1.2.2、`dwebp` 1.2.2、`rsvg-convert` 2.52.5、ImageMagick 6.9.11-60 Q16 x86_64 |
| Python 画像ライブラリ | Pillow 13.0.0。`python3 -m pip install Pillow==13.0.0` |
| 出力先と状態 | 一時作業領域。リポジトリには記録と CSV のみ保存 |
| 変える条件 | cwebp の `-z`、`-lossless`、`-q`、`-m`、`-exact`、`-metadata`、`-mt`。Pillow の `method`。PNG の `optimize` |
| 変えない条件 | 入力 SVG、`rsvg-convert -w 1280 -h 640`、ホスト、画素比較手順 |
| 繰り返し | 各符号化候補を 5 回。時間は中央値・最小・最大を記録 |

## 手順

```sh
set -eu
WORK=$(mktemp -d)
VENV=$(mktemp -d)
python3 -m venv "$VENV"
"$VENV/bin/pip" install Pillow==13.0.0
rsvg-convert -w 1280 -h 640 docs/logo/msd-linux-social-1280x640.svg -o "$WORK/social.png"

# 各候補を 5 回符号化し、計測器で毎回の経過時間とサイズを記録する。
cwebp -quiet -z 0 "$WORK/social.png" -o "$WORK/cwebp-z0.webp"
cwebp -quiet -z 3 "$WORK/social.png" -o "$WORK/cwebp-z3.webp"
cwebp -quiet -z 6 "$WORK/social.png" -o "$WORK/cwebp-z6.webp"
cwebp -quiet -z 9 "$WORK/social.png" -o "$WORK/cwebp-z9.webp"
cwebp -quiet -lossless -q 100 -m 6 "$WORK/social.png" -o "$WORK/cwebp-lossless-q100-m6.webp"
cwebp -quiet -z 9 -exact "$WORK/social.png" -o "$WORK/cwebp-z9-exact.webp"
cwebp -quiet -z 9 -metadata none "$WORK/social.png" -o "$WORK/cwebp-z9-metadata-none.webp"
cwebp -quiet -z 9 -mt "$WORK/social.png" -o "$WORK/cwebp-z9-mt.webp"

"$VENV/bin/python" - "$WORK/social.png" "$WORK/pillow-lossless-method4.webp" <<'PY'
from PIL import Image
import sys
with Image.open(sys.argv[1]) as image:
    image.save(sys.argv[2], format="WEBP", lossless=True, quality=100, method=4)
PY
"$VENV/bin/python" - "$WORK/social.png" "$WORK/pillow-lossless-method6.webp" <<'PY'
from PIL import Image
import sys
with Image.open(sys.argv[1]) as image:
    image.save(sys.argv[2], format="WEBP", lossless=True, quality=100, method=6)
PY
"$VENV/bin/python" - "$WORK/social.png" "$WORK/pillow-png-optimize.png" <<'PY'
from PIL import Image
import sys
with Image.open(sys.argv[1]) as image:
    image.save(sys.argv[2], format="PNG", optimize=True)
PY

# 上記の 11 候補をそれぞれ 5 回符号化し、perf_counter で時間を測る。
dwebp -quiet "$WORK/cwebp-z9-metadata-none.webp" -ppm -o "$WORK/decoded.ppm"
convert "$WORK/social.png" -depth 8 "rgb:$WORK/source.rgb"
convert "$WORK/decoded.ppm" -depth 8 "rgb:$WORK/decoded.rgb"
cmp "$WORK/source.rgb" "$WORK/decoded.rgb"
# 5 回の各出力は計測器でバイト列を比較し、決定性も記録する。
```

## 計測器の検証

A/A 試行では、同じ候補を複数回符号化し出力バイト列を比較します。画素比較は全ピクセル同一の入力で一致することを確認し、別試行では画素を 1 点変更して比較器が `DIFF` を返すことを確認します。

## 結果

| 候補 | バイト | 時間中央値 (秒) | 最小 (秒) | 最大 (秒) | 画素同一 | 決定的 |
|---|---:|---:|---:|---:|---|---|
| `cwebp -z 0` | 164382 | 0.019724 | 0.019237 | 0.022245 | はい | はい |
| `cwebp -z 3` | 19542 | 0.031183 | 0.030451 | 0.033230 | はい | はい |
| `cwebp -z 6` | 19570 | 0.034691 | 0.033419 | 0.038770 | はい | はい |
| `cwebp -z 9` | 19262 | 0.670468 | 0.654277 | 0.713942 | はい | はい |
| `cwebp -lossless -q 100 -m 6` | 19262 | 0.656394 | 0.649181 | 0.751334 | はい | はい |
| `cwebp -z 9 -exact` | 19262 | 0.620228 | 0.614626 | 0.637055 | はい | はい |
| `cwebp -z 9 -metadata none` | 19262 | 0.664218 | 0.648983 | 0.698071 | はい | はい |
| `cwebp -z 9 -mt` | 19262 | 0.354303 | 0.343728 | 0.366010 | はい | はい |
| Pillow lossless `method=4`, `quality=100` | 19268 | 0.056820 | 0.055066 | 0.088869 | はい | はい |
| Pillow lossless `method=6`, `quality=100` | 19268 | 0.950543 | 0.930125 | 1.050544 | はい | はい |
| Pillow PNG `optimize=True` | 44830 | 0.050580 | 0.050300 | 0.064289 | はい | はい |
| 元の PNG | 46456 | — | — | — | はい | — |

各回のサイズ、時間、画素同一性、決定性は同名 CSV に記録しました。WebP と Pillow PNG の各候補は 5 回の出力バイト列がすべて一致しました。手元の単回値とのサイズ差はありません。`-z 9` 系と `-lossless -q 100 -m 6` は 19262 バイトで同率最小となりました。採用設定は、指定済みの `-z 9 -metadata none` です。

時間は cwebp のプロセス起動を含む壁時計時間、Pillow は保存処理の壁時計時間です。符号化時間は採否に使いません。

元の PNG を含む各候補の RGB 生データは基準画像と一致しました。画素比較の陽性対照では、1 画素を変更すると比較器が `DIFF` を返すことを確認しました。A/A 試行は候補ごとに 5 回行い、出力はすべて同じバイト列でした。

## 捨てた試行と経緯

lossy、`-near_lossless`、`-sharp_yuv` は、本リポジトリでは試していない。いずれも可逆形式ではないためです。

## 結論

`cwebp -z 9 -metadata none` を採用します。RGB 画素が一致し、5 回の再実行で出力が決定的で、19262 バイトと最小サイズで同率です。`render.sh` は SVG から再生成し、デコード後の RGB 生データを変換前のラスターと比較します。

## 未確認の点

異なる libwebp 版ではファイルのバイト列が変わる可能性があります。画素同一性は `render.sh` の検査で確認します。

## ロゴの余白と横長 crop

1280×640 の基準画像の背景色は `(243, 243, 242)`、背景と異なる領域の bounding box は `(389, 115, 899, 531)` でした。1.91:1 の 1222×640 中央 crop は左右を 29 ピクセルずつ切りますが、その範囲は背景だけで、図柄を切りません。

## ログ

符号化の一時出力はコミットしません。全測定値と再実行可能な条件は同名 CSV とこの記録に保存します。
