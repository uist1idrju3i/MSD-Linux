# MSD/Linux のロゴ

マスターは SVG です。PNG、RGB565、PPM は `render.sh` で SVG から作る派生ファイルで、直接編集しません。

| ファイル | 用途 |
|---|---|
| `msd-linux-logo.svg` | 横組みロゴ（明るい背景用）。README に掲載 |
| `msd-linux-logo-dark.svg` | 横組みロゴ（暗い背景用）。README のダークモード表示 |
| `msd-linux-mark.svg` | 円形のシンボルマーク（アイコン、favicon 用） |
| `msd-linux-social-1280x640.svg` / `.png` | GitHub の Social preview（1280×640、1 MB 未満） |
| `splash/msd-linux-splash-320x170.svg` | 起動画面のマスター（LCD と同じ 320×170、横置き） |
| `splash/msd-linux-splash-320x170.png` | 起動画面の PNG |
| `splash/msd-linux-splash-320x170.rgb565` | 起動画面の生データ（RGB565 リトルエンディアン、ヘッダーなし、108,800 バイト） |
| `splash/logo_msd_clut224.ppm` | Linux カーネルの起動ロゴ形式（ASCII PPM、80×80、224 色以下） |

## サイトで使う画像

公式サイト（`public_html/`）は、次の画像を `public_html/images/` に置きます。どれも派生ファイルで、直接編集しません。

| ファイル | 作り方 |
|---|---|
| `msd-linux-logo.svg`、`msd-linux-logo-dark.svg`、`msd-linux-mark.svg`、`msd-linux-social-1280x640.png` | `render.sh` が、このディレクトリのマスターを写します。CI の `check-site.py` が、マスターと一致するかを検査します。 |
| `flow-light.svg`、`flow-dark.svg`、`seigaiha-light.svg`、`seigaiha-dark.svg` | `render.sh` が呼ぶ `tools/site_patterns.py` が作る、流水と青海波の背景です。CI の `check-site.py` が、生成結果と一致するかを検査します。 |

## 意匠

- 名前と同じく、開発場所の近くを流れる室見川を主題にしました（[名前の由来](../../RESEARCH.md#名称)）。
- 室見川の源流から北へ流れ、博多湾へ注ぐ姿を、円の中で右上から左下へ向かう三本の流れで表します。
- 流れは流水紋の筆致にならい、上流を細く、河口を太くしました。三本の線は「川」の字も兼ねます。
- 下部の文様は青海波で、川が注ぐ博多湾を表します。青海波は穏やかな波が限りなく続く様子を表す吉祥文様です。
- 文字ロゴの「/」も同じ三本の流れで描き、マークと文字をつなげています。
- 線の数と文様の段数は、170 ピクセルの LCD や 32 ピクセルのアイコンでも潰れない量に抑えました。
- 矢絣、市松、麻の葉、七宝、亀甲、鱗、立涌も検討しました。川の流れと海への到達を一つの図で示せる流水紋と青海波の組み合わせを採りました。

## 色

伝統色から、派手さを抑えた藍系の色を選びました。

| 名前 | 値 | 使う場所 |
|---|---|---|
| 濃藍（こいあい） | `#0f2350` | マークの地、明るい背景での文字 |
| 藍色 | `#165e83` | 明るい背景での「/」 |
| 水浅葱（みずあさぎ） | `#80aba9` | マークの流れ、暗い背景での「/」 |
| 白練（しろねり） | `#f3f3f2` | 暗い背景での文字、Social preview の地 |
| 青海波の線 | `#24447f` | 地との差を小さくした波の線 |
| splash の地 | `#070b17` | LCD のバックライト漏れが目立たない暗色 |

## 書体

文字は Lato Bold 2.007 の字形をアウトライン化したものです。Lato は Łukasz Dziedzic による書体で、SIL Open Font License 1.1 で配布されています。https://www.latofonts.com/

## splash として使う場合

現在のイメージは splash を表示しません。表示する場合は、起動時間への影響を実測してから採否を決めます。

- `.rgb565` は、フレームバッファが 320×170・16 bpp・RGB565 の場合に `cat` で `/dev/fb0` へ書き込めます。デコーダーを必要としません。実機のフレームバッファ形式と向き（`fbset` や `/sys/class/graphics/fb0/`）は未確認です。
- `logo_msd_clut224.ppm` は、カーネルの `CONFIG_LOGO_LINUX_CLUT224` 用ロゴ（`drivers/video/logo/logo_linux_clut224.ppm`）と差し替えられる形式です。fbcon が起動したときに表示されます。CardputerZero の LCD ドライバーは外部モジュールのため、ロゴが表示される時点は未確認です。
- 転送量は 108,800 バイトです。SPI のクロックと DRM ドライバーの転送方式によって表示にかかる時間が変わるため、値は実機で測ります。

## 作り直し方

```sh
docs/logo/render.sh  # SVG から派生ファイルを作り直す（rsvg-convert、ImageMagick 6、python3）
python3 -m venv "$HOME/.cache/msd-linux-logo"
"$HOME/.cache/msd-linux-logo/bin/pip" install --require-hashes -r docs/logo/tools/requirements.txt
"$HOME/.cache/msd-linux-logo/bin/python" docs/logo/tools/generate.py  # 形状を変えるときだけ SVG を作り直す
```

`generate.py` の実行には、Lato Bold 2.007 と Python 3.11 以上が必要です。
