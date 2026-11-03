# フレームバッファ端末とテキストブラウザの調査（2026-11）

ST7789V3（320×170）で CLI とテキストブラウザを動かすための技術を調査しました。依頼の「fbterm、w3c、Lynx」は、fbterm・w3m・Lynx と読み替えて調べ、類似するフレームバッファ端末、テキストブラウザ、画像表示の補助手段まで網羅しました。調査のみで、採否・実装の決定は行いません。

フォント経路・ライセンス詳細は [fonts.md](fonts.md) を参照してください。

## 1. 表示経路の前提

- 本機の fb は `DRM_FBDEV_EMULATION` が提供する `/dev/fb0`。fbcon（カーネルコンソール）が既定で、欧文フォントのみ。JIS 全水準は出せません（fonts.md §1.2）。
- /dev/fb0 を直接 mmap して描くアプリ（fbterm、w3m-img、fbv、links -g 等）と、KMS/GBM 経由のアプリ（kmscon、mpv --vo=drm、wayland 系）に分かれます。SPI 小型液晶では前者が軽く現実的です。

## 2. フレームバッファ端末

| 名前 | 方式 | ライセンス | Buildroot | 備考 |
|---|---|---|---|---|
| fbterm 1.7.0 | /dev/fb + freetype/fontconfig + UTF-32 内部処理 | GPL-2.0+ | `BR2_PACKAGE_FBTERM` あり | JIS 全水準の TTF が使える。IM（日本語入力）は uim-fep 等と併用。upstream は 2010 年頃から停滞、Buildroot は musl 向けパッチ4件を保持【一次: vendor/buildroot/package/fbterm】 |
| jfbterm | /dev/fb + BDF フォント | フリー | 未収録 | 日本語専用 fb 端末。2009 年以降更新なし |
| kmscon | DRM/KMS + xkbcommon + pango 等 | MIT 系 | 未収録 | 現代的な設計だが依存が多く、活動は停滞。pango+harfbuzz が要る |
| zhcon | fbdev、入力メソッド一体型 CJK console | GPL | 未収録 | 中国語主体。2006 年頃で停止 |
| bogl-bterm | bogl ライブラリの極小 fb 端末 | フリー | 未収録 | Debian インストーラ用途 |
| yat | SDL ベースの端末 | フリー | 未収録 | 古く、SDL 経由の重さがある |
| dvtm + abduco | 端末内タイル型マルチプレクサ | MIT | 未収録 | 画面分割は別次元の技術 |

### Wayland/KMS 経路（重い選択肢）

| 組み合わせ | Buildroot | 備考 |
|---|---|---|
| cage（kiosk コンポジタ、MIT）＋ foot（wayland 端末、MIT） | `BR2_PACKAGE_CAGE` / `BR2_PACKAGE_FOOT` あり | wlroots＋DRM で X/Wayland 環境なしに wayland アプリを全画面実行。レンダラは GBM/EGL または pixman ソフト描画。VC4（CM0）+ tinydrm 上の構成可否は未検証。fbterm より重い |
| weston | `BR2_PACKAGE_WESTON` あり | 本格コンポジタ。用途過剰 |
| Qt linuxfb プラグイン | `BR2_PACKAGE_QT5` / `QT6` あり | Qt アプリを X なしで fb 実行する選択肢（GUI アプリを書く場合） |
| SDL 系 | SDL1.2（`BR2_PACKAGE_SDL`）は fbcon ドライバで /dev/fb0 に直接描画、SDL2/3 は kmsdrm（GBM 依存） | netsurf-fb が SDL を使う関係（§3） |

## 3. テキストブラウザ

| 名前 | 機能 | 画像 | Buildroot | ライセンス | 備考 |
|---|---|---|---|---|---|
| lynx 2.9.2 | テキスト描画・SSL・Cookie | 不可 | `BR2_PACKAGE_LYNX` あり（ncurses/slang、openssl か gnutls） | GPL-2.0 | 最軽量の定番。活発に保守（Thomas Dickey 系） |
| w3m | 表・フレーム・インライン画像 | w3m-img が /dev/fb または X に直接描画 | 未収録 | BSD 系 | Debian の `tats/w3m` が事実上の上流。tats 氏が 2024 年以降応答なしで、現在は rkta 氏の sr.ht フォークが継続保守（gemini 対応ブランチも）【一次: github.com/tats/w3m issue #304、sr.ht/~rkta/w3m】 |
| links2 2.30 | 表・フレーム・色・`-g` グラフィックモード | fbdev/DirectFB/X 経由で描画＋マウス | `BR2_PACKAGE_LINKS` あり（`LINKS_GRAPHICS` オプション、directfb は off） | GPL-2.0+ | `-g` でページ内画像を表示。マウスは gpm |
| elinks | links 系の拡張（タブ・スクリプト・限定的 CSS） | 不可 | 未収録 | GPL-2.0 | JS は実験的で事実上使われない |
| netsurf-fb 3.10 | HTML4+CSS2 の実ブラウザ、JS 限定的 | 可 | `BR2_PACKAGE_NETSURF`（`NETSURF_SDL` = framebuffer フロントエンドを選択） | GPL-2.0 | 小型画面前提でないため 320×170 では厳しい可能性【推測】。静的リンク制約あり |
| dillo 3.3.0 | 軽量 GUI ブラウザ | 可 | 収録はあるが `XORG7` 必須 | GPL-3.0+ | X 前提のため本機の fb 構成では不可 |
| edbrowse | ed 型 CLI + duktape JS | 不可 | 未収録（duktape/mujs/quickjs は収録済み） | GPL | 実 JS エンジンを持つ数少ない CLI ブラウザ |
| chawan | Nim 製。タブ・CSS 強め・sixel 画像 | sixel 端末のみ | 未収録 | フリー | sixel 非対応の fbterm では画像が出ない |
| brow.sh | Firefox を ssh/mosh 経由で端末表示 | 可（外部ブラウザ） | 未収録 | フリー | Docker+Firefox が要り本機には非現実的 |
| offpunk 等 gemini 系 | gemini/gopher/http を端末で | — | 未収録 | GPL | Python 製。gemini 用途限定 |
| html2text / pandoc / urlscan | 変換・URL 抽出の補助 | — | 未収録 | — | CLI 整形の補助手段 |

## 4. fb 上での画像・動画表示の補助

| 手段 | Buildroot | 備考 |
|---|---|---|
| fbv | `BR2_PACKAGE_FBV` あり | GIF/PNG/JPEG/BMP を /dev/fb へ直接表示 |
| fbi / fbim（fbida 系） | 未収録 | 定番 fb 画像ビューワ |
| w3mimgdisplay | w3m 付属 | w3m-img の fb 描画バックエンド |
| chafa / viu / catimg / img2txt（libcaca） | いずれも未収録 | 端末内に画像を文字（半角ブロック・sixel・ASCII）で描画。fbterm は sixel 非対応だが半角ブロック系なら可【推測】 |
| mpv `--vo=drm` / `--vo=tct` | `BR2_PACKAGE_MPV` あり | drm は KMS 経路。tct は端末文字で動画を描き fbterm/fbcon 上でも動く（色数制約あり） |
| ffmpeg / ffplay | `BR2_PACKAGE_FFMPEG` あり | ffplay は SDL 経由 |
| mplayer | 未収録 | fbdev2 出力は歴史的存在 |
| busybox fbsplash | busybox のアプレット | 起動スプラッシュ用。有効化は defconfig 側 |

## 5. 入出力の補助

| 手段 | Buildroot | 備考 |
|---|---|---|
| uim-fep / fcitx-fbterm | 未収録 | コンソール上での日本語入力（fbterm/jfbterm と併用）。MSD は英字入力前提なら不要 |
| gpm | `BR2_PACKAGE_GPM` あり | コンソールマウス。links -g 等に必須級 |
| tmux 3.6b / screen 5.0.2 | `BR2_PACKAGE_TMUX` / `BR2_PACKAGE_SCREEN` あり | セッション維持・分割。320×170 では分割より切替用途 |
| abduco + dvtm | 未収録 | tmux より軽い代替 |

## 6. Buildroot 収録状況まとめ

- **収録あり**: lynx、links（+GRAPHICS）、netsurf（SDL=fb フロントエンド）、dillo（X 必須）、fbterm、fbv、gpm、tmux、screen、mpv、ffmpeg、cage、foot、weston、wlroots、qt5/qt6、sdl/sdl2/sdl3 系、duktape、mujs、quickjs
- **未収録**: w3m、elinks、jfbterm、kmscon、zhcon、yat、bogl-bterm、fbi/fbida、chafa、viu、catimg、caca、uim-fep、fcitx-fbterm、abduco、dvtm、edbrowse、chawan、offpunk、brow.sh、html2text

## 7. MSD/Linux への適用メモ

- **軽い順の階段**: lynx（テキストのみ・最小）→ links -g（画像・表・マウス）→ netsurf-fb（実ブラウザだが重い）。画面サイズを考えると実用は lynx/links 系までが現実線【推測】。
- **日本語表示するブラウザ**: fbterm＋日本語 TTF（fonts.md の経路）＋ links -g または w3m-img が本命。w3m は Buildroot 未収録なので vendor 追加が必要（依存は boehm-gc・openssl・ncurses 系）【推測】。
- **fbterm だけの構成**: TTF 化で JIS 全水準が出せ、lynx/links テキストモードを日本語で表示できる最小構成。
- **netsurf-fb**: SDL framebuffer フロントエンドは /dev/fb0 系で動くが、静的リンクのみ対応・PC 画面向けのレイアウト想定のため小画面適合は未検証。
- **cage + foot + wayland アプリ**: 実現可能性はあるが、wlroots/EGL または pixman 描画の保守コストが高い。将来 GUI 化するなら検討対象。
- **mpv --vo=tct**: fbterm 上で動画を文字描画できる軽い経路（実用速度・色数は要実機確認）。

## 8. 未確認事項

- 各ツールの DRM_FBDEV_EMULATION 上 `/dev/fb0` での実動作（描画・ページング速度・メモリ）。実機または QEMU で要確認。
- w3m-img の fb 描画が DRM エミュレーションの fb0 で動くか（ioctl/mmap 互換）。
- netsurf-fb の SDL が SDL1.2 fbcon ドライバ相当か SDL2 kmsdrm 相当か（Buildroot の SDL 依存の実構成）。
- links -g の fbdev ドライバの実装（/dev/fb0 直書きか svgalib 系か）。
- fbterm の色数（16/256）と、chafa・mpv tct 等が実用画質になるか。
- lynx/links の SSL/TLS が本機 openssl（wolfSSL 未使用の構成）で十分に動くか。
- cage+foot の pixman ソフトレンダラが tinydrm（SPI 液晶）デバイスを受け入れるか（GBM 不要構成）。

## 9. 主な出典（2026-11-02 確認）

- `vendor/buildroot/package/{fbterm,lynx,links,netsurf,dillo,fbv,gpm,tmux,screen,cage,foot,mpv,ffmpeg}`（バージョン・ライセンス・依存の一次確認）
- https://github.com/tats/w3m および issue #304（保守状況）、https://sr.ht/~rkta/w3m/（継続フォーク）
- http://links.twibright.com/（links2 グラフィックモード）
- https://lynx.invisible-island.net/（Lynx 保守元）
- https://www.netsurf-browser.org/（framebuffer フロントエンド）
- fonts.md §1.1・§1.2（fbcon の制約と 512 字形上限）
