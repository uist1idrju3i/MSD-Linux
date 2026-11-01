# フォントの調査（2026-11）

CardputerZero の ST7789V3（320×170、SPI）に CLI（fbcon またはユーザー空間ターミナル）を表示するためのフォントを調査しました。依頼された5件（萌神拼音フォント、美咲フォント、k8x12、UDEV Gothic、IPAフォント）に加え、用途の近いフォントをライセンス・収録文字・形式の面から網羅的に調べました。調査のみで、採否・実装の決定は行いません。

## 1. 表示経路とフォント形式の前提

### 1.1 本機が取り得る経路

| 経路 | しくみ | 日本語の扱い |
|---|---|---|
| fbcon（カーネルコンソール） | `FRAMEBUFFER_CONSOLE` + `DRM_FBDEV_EMULATION` で ST7789V3 のフレームバッファに等幅セルフォントを描く。`console=tty1` が現行設定 | Unicode→字形のマップ上限があり（§1.2）、JIS 全水準は扱えない |
| fbterm（ユーザー空間） | Buildroot 2026.08 に `BR2_PACKAGE_FBTERM` あり（fbterm 1.7.0、GPL-2.0+）。fontconfig + freetype で TTF/OTF を描画 | JIS 全水準を含む TTF がそのまま使える |
| jfbterm / kmscon / zhcon | Buildroot にパッケージなし（収録なしを確認） | 持ち込む場合は vendor 追加が必要 |

fbterm は fontconfig と liberation を select し、依存に `LIBSTDCPP` / `LOCALE` / `WCHAR` / `MMU` を要求します。本機の外部 Bootlin ツールチェーンは glibc で WCHAR/LOCALE 対応のため依存は充足できます【一次: vendor/buildroot/package/fbterm/Config.in】。upstream は 2010 年頃から更新が止まっており、保守性は要注意です。

### 1.2 fbcon の制約

- **字形数の上限**: カーネルの Unicode→字形 変換表は `MAX_GLYPH 512`（`drivers/tty/consolemap.c`）で、1フォントあたり表示できる文字種は事実上512までです【一次: torvalds/linux】。JIS 第1・第2水準を収録した約7,170字のフォントを PSF 化しても、そのままでは全字形を Unicode から引けません。かな・ASCII・一部漢字のサブセット化が前提になります。
- **色数**: 256 グリフを超えるフォントを読み込むと、描画面が8色に落ちる挙動が報告されています【未確認: ArchWiki「Linux console」記載、カーネル側の vt 実装依存】。
- **組み込みフォント**: `lib/fonts/Kconfig` の `CONFIG_FONT_*`（8x8、8x16、6x11、7x14、MINI_4x6、6x10、SUN8x16/SUN12x22、TER16x32、6x8）は欧文のみ。`get_default_font()` は yres < 400 で高さ8以下を優先するため、320×170 では FONT_8x8 が既定になり得ます【一次: drivers/video/console/fbcon.c 系の既定選択処理】。defconfig に FONT_* 指定はなく、既定で FONT_8x8 と FONT_8x16 が組み込まれます。
- **フォント形式**: 組み込みは ROM フォント（`lib/fonts/font_*.c`）、実行時読み込みは kbd の `setfont` が扱う PSF1/PSF2。BDF→PSF 変換には `psftools` または Debian の `bdf2psf` パッケージが使えます。

### 1.3 320×170 での桁・行（fbcon、幅は等幅セル）

| セル | 桁×行 | 感想 |
|---|---|---|
| 16×16 | 20×10 | 漢字は読めるが桁が少なく CLI としては厳しい |
| 8×16 | 40×10 | 欧文は実用的、行数が少ない |
| 8×12 | 40×14 | k8x12 の実サイズ。漢字7×11を収められる |
| 8×8 | 40×21 | 美咲の実サイズ。漢字7×7で行数確保 |
| 6×10 | 53×17 | 欧文向け（例: Terminus 6x10相当） |
| 4×6 | 80×28 | MINI_4x6。可読性は低い |

### 1.4 現状の rootfs の扱い

`board/cardputerzero/post-build.sh` が `usr/share/consolefonts`・`consoletrans`・`unimaps` を削除しており、kbd は入っていてもコンソールフォント一式は同梱されていません【一次】。setfont 経路を使う場合は削除対象の見直しと PSF 同梱が必要です。

## 2. 依頼された5件

### 2.1 萌神拼音フォント（Mengshen Pinyin Font）

| 項目 | 内容 |
|---|---|
| リポジトリ | https://github.com/MaruTama/Mengshen-pinyin-font |
| 最新リリース | v2.0.0（タグ `v20261020-153012`） |
| ライセンス | SIL Open Font License 1.1 |
| ファイル | `Mengshen-HanSerif.ttf`（17,163,488 B）、`Mengshen-Handwritten.ttf`（19,678,104 B）【一次: GitHub Releases】 |
| 概要 | 漢字の直上にピンインを自動合成表示するフォント。中国語学習向け。16,026 漢字に対応 |
| 基底フォント | 明朝系は Source Han Serif（源ノ明朝）＋ピンイン部に M+ M Type-1。手書き系は小頼字體（Xiaolai）＋ SetoFontSP【一次: README】 |
| 表示方式 | OpenType の `rclt`（required contextual alternates）で文脈自動合成。環境が非対応なら異体字セレクタ（IVS、U+E0100 系）で手動選択する互換経路あり【一次: README】 |
| 対応字形 | 簡体字・繁体字・日本語新字体を収録 |
| 対応環境 | README の導入手順は Windows/macOS/Android 向け。Linux は fontconfig 配置で使えるが、ピンイン合成に `rclt` 対応のレンダラ（Harfbuzz 経由）が要る点に注意 |
| 本機との適合 | TTF 約17〜20MB を fbterm で表示する前提。fbcon では字形セル固定のためルビ合成は使えず、CLI 用途としては過剰。用途は漢字学習アプリ等に限定されそうです【推測】 |

### 2.2 美咲フォント（misaki）

| 項目 | 内容 |
|---|---|
| 配布元 | https://littlelimit.net/misaki.htm |
| サイズ | 8×8 セル（字形7×7） |
| 収録 | JIS 第1・第2水準漢字、ひらがな・カタカナ・記号・ギリシャ・ロシア等、約7,171グリフ（BDF の ENCODING 数を確認） |
| バリアント | ゴシック（`misaki_gothic`）、明朝（`misaki_mincho`）、仮名のみ新版（`misaki_gothic_2nd`） |
| 形式 | BDF（ISO10646-1）、TTF（ビットマップ埋め込み）、PNG、u8g2/組み込み向け変換物など【一次: 配布 ZIP 確認】 |
| ライセンス | 「自由に使ってください」系の無制限ライセンス（作者ページ「Unlimited permission ... AS IS」）。商用・再配布・改変可 |
| 来歴 | シャープ PC-E500 系のフォントをベースに発展させたもの（配布ページ記載） |
| パッケージ | Debian に `fonts-misaki`（TTF）と `xfonts-misaki`（BDF）あり【一次: packages.debian.org】 |
| 本機との適合 | 320×170 で 8×8 → 40桁×21行。字形は漢字を含め 7×7 に圧縮した設計で、fbcon セルに収まる。上限512字形のサブセット化（かな・ASCII・頻出漢字）または fbterm で TTF 利用が道筋【推測】 |

### 2.3 k8x12

| 項目 | 内容 |
|---|---|
| 配布元 | https://littlelimit.net/k8x12.htm |
| サイズ | 8×12 セル（字形7×11） |
| 収録 | JIS 第1・第2水準、約7,170グリフ（BDF で確認） |
| バリアント | `k8x12`（標準）、`k8x12L`（太線）、`k8x12S`（仮名小さめ）ほか【一次: 配布 ZIP 確認】 |
| 形式 | BDF（ISO10646-1）、TTF、PNG 等 |
| ライセンス | 美咲と同じ無制限ライセンス |
| パッケージ | Debian に `fonts-k8x12` / `xfonts-k8x12` あり |
| 本機との適合 | 8×12 → 40桁×14行。漢字の視認性は美咲より高い【推測】。fbcon で使う場合も512上限のサブセット化が前提 |

### 2.4 UDEV Gothic

| 項目 | 内容 |
|---|---|
| リポジトリ | https://github.com/yuru7/udev-gothic |
| 最新 | v2.2.0 系 |
| 合成 | JetBrains Mono（欧文）＋ BIZ UDゴシック（日本語） |
| ライセンス | SIL Open Font License 1.1 |
| バリエーション | 標準（半角1:全角2）／`35`（半角3:全角5）／`JPDOC`（日本語文書向け、`←→□■…` などを全角優先）／`LG`（JetBrains Mono のリガチャ対応）／`NF`（Nerd Fonts 合成、拡張 Powerline 記号）／`HS`（全角スペース不可視版）【一次: README】 |
| 特徴 | 通常版は全角スペースを可視化（□形）するコーディング向け仕様。ビルドスクリプトで `--35` / `--jpdoc` 等の派生生成が可能 |
| 本機との適合 | TTF は fbterm / fontconfig 経路でのみ使える。320×170 に 12〜14px で出せば読めるが、fbterm 前提【推測】 |

### 2.5 IPAフォント群

| 項目 | 内容 |
|---|---|
| 配布元 | https://moji.or.jp/ipafont/ |
| ラインナップ | IPA 明朝 / IPA ゴシック / IPA P明朝 / IPA Pゴシック（Ver.003 系）、IPAex 明朝 / IPAex ゴシック（Ver.004.01、令和の合字対応）、IPAmj 明朝（JIS X 0213:2004 例示字体） |
| ライセンス | IPAフォントライセンス v1.0（OSI 認定）。再配布は無改変＋ライセンス添付、改変は「派生プログラム」として改名・同ライセンス・差分提供方法の明記が条件 |
| 本機との適合 | アウトライン TTF のため fbterm 前提。IPAmj は印刷・表示の標準字体として有力だが容量は MB 級【推測】 |

## 3. 類似フォントの網羅調査

### 3.1 littlelimit 姉妹フォント（同一ライセンス）

| 名前 | サイズ | 収録 | 補足 |
|---|---|---|---|
| k6x8 | 6×8（字形5×7） | JIS 第1・第2水準 | 320×170 では 53桁×21行。漢字 5×7 の可読性は未確認 |
| k12x8 | 12×8 | JIS 第1水準＋欧文 | 横長セルの欧文向け【一次: 配布ページ】 |
| 美咲 / k8x12 | 8×8 / 8×12 | §2.2 / §2.3 | |

### 3.2 日本語ビットマップ系

| 名前 | サイズ | ライセンス | 備考 |
|---|---|---|---|
| 東雲フォント（Shinonome） | 12/14/16/18px 系 | パブリックドメイン | X11 時代の定番。bdf 配布。漢字は16px以上が実用域 |
| efont Unicode | 16px 双方向 | 自由再配布（efont 系） | ISO10646 の BDF。収録面は広いが更新停止 |
| jiskan16/jiskan24（`xfonts-jis` / `font-jis-misc`） | 16/24px | X11 系古典ライセンス | X11 標準添付。Buildroot に `BR2_PACKAGE_XFONT_FONT-JIS-MISC` あり【一次: vendor/buildroot】 |
| M+ BITMAP FONTS | 10/12px 系 | M+ ライセンス（無制限） | mplus-outline と同名義のビットマップ版 |
| PixelMplus | 10/12px | M+ ライセンス | M+ 系ドットフォント |
| DotGothic16（ドットゴシック16） | 16px 系 | OFL-1.1 | Fontworks。ゲーム向けドット体。TTF（アウトライン+ビットマップ風設計） |
| 小夏フォント（Konatu） | 8〜21px 埋込み | MIT（ver.20121218 以降。旧版 CC-BY-SA 3.0） | TTF に埋め込みビットマップ。2012 年で更新停止 |
| mona フォント | 12/14/16px | フリー（mona 系） | Linux で歴史のあるドット/アウトライン。Monapo（mona+IPA 合成）は IPA 部分に IPA ライセンス |
| 梅フォント（Ume） | mplus 派生 | M+ ライセンス | 漢字は花園明朝ベースの合成 |
| さざなみ（Sazanami） | 12px 系 | 修正BSD | 和田研フォント系の流れを汲む（VLゴシックの一部にも採用） |
| 花園明朝（HanaMin） | A/B 2系統 | A=OFL-1.1 / B=独自自由ライセンス | Unicode 広範囲の漢字を収録するアウトライン |
| Unifont / Unifont JP | 16px 全 Unicode | GPL-2.0+ フォント埋込み例外 かつ OFL-1.1 の二重 | 網羅性最高だが字形品質は割愛デザイン |
| WenQuanYi Bitmap Song | 9〜12px 系 | GPLv2 + フォント埋込み例外 | 中国語簡体字主体。日本語は非対応が基本 |

### 3.3 中国語・韓国語のピクセルフォント

| 名前 | サイズ | ライセンス | 備考 |
|---|---|---|---|
| Cubic 11（俐方體11號） | 11px 全角 | OFL-1.1 | 台湾製。繁体字＋日本語仮名・常用漢字も収録 |
| Ark Pixel Font | 10/12/16px | OFL-1.1 | 日中韓対応を目指す進行中プロジェクト |
| Fusion Pixel Font | 8/10/12px | OFL-1.1 | 日中韓ピクセル。8px 系は美咲の近いサイズ感 |
| Zpix | 12px | プロプライエタリ（商用課金あり） | 品質は高いが再配布条件から本機には不可【一次: 作者のライセンス表示】 |
| Galmuri | 11/14px 系 | OFL-1.1 | 韓国語主体。日本語仮名も一部 |

### 3.4 欧文コンソール・ピクセル

| 名前 | サイズ | ライセンス | 備考 |
|---|---|---|---|
| Terminus | 4〜32px 多サイズ | OFL-1.1 | Linux コンソール定番。PSF 配布。日本語なし |
| classic UNIX console fonts（kbd 付属） | 8x8〜16x32 | kbd 同梱（GPL） | setfont でそのまま使える |
| Spleen | 5x8〜32x64 | BSD 系 | OpenBSD 由来。PSF/BDF あり |

### 3.5 日本語プログラミング合成フォント

yuru7 氏の合成系はすべて OFL-1.1 です。

| 名前 | 合成 | 特徴 |
|---|---|---|
| HackGen（白源） | Hack ＋ 源柔ゴシック | 等幅 1:2。合成系の原点 |
| PlemolJP | IBM Plex Mono ＋ IBM Plex Sans JP | 落ち着いた字幅 |
| Firge | Fira Mono ＋ 源真ゴシック | |
| Bizin Gothic | Inconsolata ＋ BIZ UDゴシック | UDEV の兄弟、欧文は Inconsolata |
| Juisee | JuliaMono ＋ LINE Seed JP（Ricty 系替） | |
| Moralerspace | Monaspace ＋ IBM Plex Sans JP / Kiwi Maru 等 | |

その他の合成・派生の代表例を示します。

| 名前 | 合成 | ライセンス |
|---|---|---|
| Ricty / Ricty Diminished | Inconsolata ＋ Migu / CircleM+ | OFL 系（派生ごとに確認） |
| Myrica | Inconsolata ＋ M+ ＋ IPA 系 | M+/IPA 混合 |
| Cica | Hack ＋ DejaVu ＋ Rounded Mgen+ ＋ NF ＋ emoji | OFL-1.1 |
| Sarasa Gothic / Mono J | Iosevka ＋ Source Han 系 | OFL-1.1 |
| Sarack | Sarasa ＋ Hack | OFL 系 |
| Cojica | Cica 系派生 | OFL 系 |
| Noto Sans Mono CJK JP | — | OFL-1.1 |

### 3.6 IPA 系・日本語アウトライン

| 名前 | 関係 | ライセンス |
|---|---|---|
| Takao フォント | IPA 派生（Ubuntu 系） | IPA ライセンス |
| 東風フォント（Kochi） | 和田研系の古典 | 自由（明文化は弱い。Debian main） |
| VLゴシック | M+ ＋ さざなみ ＋ 独自 | 修正BSD ＋ M+【一次: daisukesuzuki/VLGothic LICENSE】 |
| Migu / MigMix | M+ ＋ IPA 系 | IPA ライセンス相当 |
| Monapo | mona ＋ IPA | mona ＋ IPA 混合 |
| Koruri | M+ OUTLINE ＋ Open Sans | M+ / Apache-2.0 |
| 源暎 / 源柔 / 源真 / 源ノ角 系 | Source Han の派生 | OFL-1.1 |
| Noto Sans JP / Source Han Sans | — | OFL-1.1（Source Han Serif 同様） |
| BIZ UD ゴシック/明朝 | Morisawa | OFL-1.1 |
| LXGW WenKai | Klee 派生の中国語楷書 | OFL-1.1（日本語収録は限定的） |

### 3.7 ルビ・注音・ピンイン系（萌神の類似）

| 名前 | 方式 | ライセンス | 備考 |
|---|---|---|---|
| 萌神拼音 | rclt 自動合成 ＋ IVS | OFL-1.1 | §2.1。自動ピンインの OSS として独自 |
| bpmfvs プロジェクト（ズィハイ 注音シリーズ: 源樣注音明體 など） | 注音（ボポモフォ）を字の右に合成。IVS で選択制 | Apache-2.0（生成ツール）＋各フォント側ライセンス | 台湾向け注音。中国語ピンインとは別系統【一次: github.com/ButTaiwan/bpmfvs】 |
| 注音IVSフォント（ズィハイ系） | IVS 選択で注音切替 | 各フォント準拠 | 源流・源雲・源石・源泉・源樣 の各派生 |

萌神拼音フォントは「拼音を文字上に合成する」点でピンイン系では珍しい実装です。中国語学習用で、日本語 CLI 用途とは目的が異なります。

## 4. ライセンスの整理

| 区分 | フォント | 再配布・埋込みの要点 |
|---|---|---|
| 無制限・PD 相当 | 美咲、k8x12、k6x8、k12x8、東雲、M+ 系、PixelMplus | 表示義務なし。製品同梱が最も容易 |
| MIT / BSD | 小夏、VLゴシック（修正BSD+M+）、さざなみ（修正BSD） | 著作権表示とライセンス文の同梱 |
| SIL OFL-1.1 | 萌神拼音、UDEV Gothic、yuru7 全系、DotGothic16、Cubic 11、Ark Pixel、Fusion Pixel、Galmuri、Sarasa、Cica、Noto/Source Han、BIZ UD、LXGW、Hanazono-A、Terminus | フォント単体販売禁止。派生は予約名を使わず OFL を維持。文書・画面への埋込みは可 |
| IPA フォントライセンス v1.0 | IPA 全系列、Takao、Migu/MigMix、Monapo の IPA 部分 | 再配布は原則無改変。改変は「派生プログラム」として改名・差分提供の明記・同ライセンスが条件 |
| GPL + フォント埋込み例外 | Unifont、WenQuanYi Bitmap Song | フォントを埋め込んだ成果物（ドキュメント/画像）に GPL は及ばないが、フォント自体の改変・再配布は GPL のまま。本機リポジトリの GPL-2.0-or-later と整合しやすい一方、OS 同梱時は legal-info への記録が要る |
| プロプライエタリ | Zpix | 再配布不可 → 対象外 |

リポジトリ方針（GPL-2.0-or-later）との関係では、フォントファイル同梱はどの区分でも概ね可能ですが、OFL/IPA 系はそれぞれの添付条件と「単体販売禁止」「改名義務」を満たす必要があります。

## 5. MSD/Linux への適用メモ

- **fbcon で日本語を出す場合の最短ルート**: littlelimit 系（無制限）の BDF から、かな・ASCII・頻出漢字のサブセットを作って PSF2 化し setfont。512 字形上限と 8 色化の制約は残ります【推測】。
- **fbterm に切り替える場合**: TTF（美咲 TTF、k8x12 TTF、UDEV Gothic、IPA 等）がそのまま使え JIS 全水準が出ます。fontconfig+freetype+libstdc++ とロケールが前提で、イメージサイズと保守性（上流停止）のトレードオフがあります【推測】。
- **欧文だけでよい最小構成**: 既定の CONFIG_FONT_8x8/8x16 のまま。追加フォント不要。
- **萌神拼音・IPA・UDEV Gothic など MB 級 TTF**: CLI だけなら容量が過剰になりがち。漢字学習・文書表示など別アプリ用途向け。

## 6. 未確認事項

- k8x12 の fbcon 実表示（8×12 セルで 40×14 行の見え方）。実機/エミュレータで要確認。
- 512 字形上限を超えた PSF2 を読み込んだときの実挙動（切り詰めか拒否か）。カーネルコードからは上限の存在のみ確認。
- littlelimit ライセンス文の正式名称（「無制限」扱いはページ記述より【一次: littlelimit.net/font.htm】）。
- 美咲の名称由来・作者の英語表記。Wikipedia に記述があるが出典確認は今後。
- fbterm の musl パッチ（0001-0004）が glibc 環境で問題なく当たるか。
- Mengshen の v2.0.0 で追加された字形の内訳（日本語漢字の拡充有無）。
- 各 Debian パッケージの最新版追随（fonts-misaki 等）。

## 7. 主な出典（2026-11-02 確認）

- https://github.com/MaruTama/Mengshen-pinyin-font（リリース v20261020-153012 / v2.0.0、README、LICENSE）
- https://littlelimit.net/misaki.htm / https://littlelimit.net/k8x12.htm / https://littlelimit.net/font.htm（ライセンス文）
- https://github.com/yuru7/udev-gothic（README、バリエーション表）
- https://moji.or.jp/ipafont/（IPA フォント配布・ライセンス）
- https://github.com/daisukesuzuki/VLGothic（LICENSE.ja）
- https://github.com/ButTaiwan/bpmfvs（注音 IVS 規格）
- https://packages.debian.org（fonts-misaki, xfonts-misaki, fonts-k8x12, xfonts-k8x12 の存在確認）
- `vendor/buildroot/package/fbterm/{Config.in,fbterm.mk}`、`vendor/buildroot/package/kbd/kbd.mk`、`vendor/buildroot/package/xfont_xfont-font-jis-misc`
- `drivers/tty/consolemap.c`（MAX_GLYPH）、`drivers/video/console/fbcon.c`（get_default_font）、`lib/fonts/Kconfig`（torvalds/linux）
- `board/cardputerzero/post-build.sh`（consolefonts 等の削除）
