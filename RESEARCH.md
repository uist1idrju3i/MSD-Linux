# CardputerZero 向け MSD/Linux 調査記録

## 目的と前提

MSD/Linux は Muromi Software Distribution / Linux の略で、福岡県の室見川にちなんでいます。M5Stack CardputerZero（標準版・Lite 版の両方）向けに、再現可能な Linux イメージを作ることを目指します。

外部の事前調査を出発点に公開資料で再確認し、確認度は各行の出典に基づいて示しています。

### 決定済みの方針

- ベースは Buildroot。M5 のドライバと Raspberry Pi カーネルを組み込む。
- UI は LCD のテキストコンソールと内蔵キーボードによる CLI のみ。公式 LVGL ランチャー、公式アプリ、Debian `.deb` 互換は目標にしない。
- 標準版と Lite 版を同じイメージで扱う。Lite 版にも microSD スロットはあるが、microSD カードは付属しない。
- 起動を速くし、突然の電源断に備えて rootfs を読み取り専用にし、更新失敗時は A/B の前のスロットへ自動復帰することを目指す。
- SSH・VPN は調査対象にとどめ、実装しない。
- リポジトリのライセンス方針は GPL-2.0-or-later。配布物ごとのライセンスとソース提供に注意する。
- 開発中で、実機は来月発売予定、起動イメージはまだない。起動時間の目標値は実機測定後に決める。

### 概略アーキテクチャ案

| 層 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08、BR2_EXTERNAL として管理 |
| カーネル | Raspberry Pi `rpi-6.18.y` を基準にし、コミットを固定 |
| 起動 | Raspberry Pi firmware と `autoboot.txt` / `tryboot` による A/B を調査・実装する。CM0 実機で要検証 |
| rootfs | SquashFS を読み取り専用で使う案を第一候補とし、EROFS と実機比較する |
| 可変データ | 小さな書込み可能領域と tmpfs overlay を検討。領域・ファイルシステムは電断試験後に決める |
| UI | ST7789V3 の LCD に fbcon を使う CLI と、TCA8418 内蔵キーボード |

## ハードウェア

以下の表は公開資料で確認したハードウェア情報です。Devin が 2026-10-18 に公開資料で確認しました。

| 項目 | 確認内容 |
|---|---|
| SoC | Raspberry Pi CM0（RP3A0 / BCM2837）、Cortex-A53 4 コア、1 GHz、aarch64、LPDDR2 512 MB |
| ストレージ | microSD のみ。標準版 C154 は 32 GB カード付き、Lite 版 C155 はカードなしだがスロットあり |
| LCD | ST7789V3、320×170、SPI0（MOSI G10、SCLK G11、DC G25、CS G8、TE G5）。RST と BL は M5IOE1（I2C 0x4F）の PYG12 / PYG10 |
| キーボード | 46 キー、TCA8418（I2C 0x34、INT G27）。リセット PYG3 は USB ハブ GL852G と共用 |
| I2C1 | G2/G3 に ES8389（0x10）、TCA8418（0x34）、BMI270（0x68）、RX8130CE（0x32）、M5IOE1（0x4F）。BMM150 は BMI270 の裏側 |
| 音声 | ES8389 + I2S（G18〜21）、AW8737A アンプ EN=G24、HP_DET=G17 |
| USB | Host/Slave スイッチあり。Host 時は GL852G 経由で SR9900A Ethernet、USB-A、左 Type-C、HAT。Slave 時は右 Type-C が CM0 に直結し、ADB / rpiboot に使う |
| 電源 | 1750 mAh、BQ27220 燃料計、スイッチ検出 SW_DET=G6、PWR_DET / PWR_EN は M5IOE1 |
| その他 | IR TX G12 / RX G13、HY2.0-4P（既定 UART G14/G15、G4 で I2C に切替）、EXT 14P、HDMI 出力、IMX219 カメラ（Lite 版にはない） |
| 製品状態 | M5 の製品ページは Work in progress、SDK / Kernel ページは coming soon |

出典: [M5Stack CardputerZero](https://docs.m5stack.com/en/CardputerZero)、[回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)。

## 公式ソフトウェア構成

### 公式イメージとドライバ

| 対象 | 確認内容 |
|---|---|
| 公式イメージ | `CardputerZero/pi-gen` の `cardputerzero_v1.0` ブランチ、HEAD `791a985`（2026-10-08）。Debian trixie / arm64、labwc / Wayland、systemd を使う Raspberry Pi OS 派生 |
| カーネル | apt pin、ハッシュ検証、hold により `6.18.39-1+rpt1` に固定 |
| M5 ドライバ | イメージ作成時に `m5stack-linux-dtoverlays` の main を clone してビルドし、コミット値を記録するが固定していない |
| UI / アプリ | LVGL 9.5 の APPLaunch、LaunchWizard、PipeWire、ADB（既定 off）。アプリは `.deb` として配布 |
| M5 ドライバ構成 | `m5stack-linux-dtoverlays` HEAD `7551854`（2026-09-23）。全て out-of-tree モジュール。LCD（ST7789V3）、M5IOE1、キーボード（TCA8418）、音声（ES8389）、電池計、IMU、RTC overlay、電源検出など |
| 起動経路 | 公式 pi-gen は U-Boot を使わない。CardputerZero/u-boot と circle-boot-splash は実験用 |
| 公式 config / cmdline | `vc4-kms-v3d,cma-64`、UART、`dwc2`、IMX219、IR 等の設定。pi-gen の cmdline は `quiet fbcon=map:off cfg80211.ieee80211_regdom=AE` で、日本向けの regdom は見直し対象（[pi-gen](https://github.com/CardputerZero/pi-gen/tree/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)） |
| 更新 / 周辺 | apt の `.deb` 配布、launcher updater、M5 Imager がある。AppBuilder と LVGL / SDL3 template も確認。OS image / kernel の A/B OTA は公開 tracked files で未確認（[pi-gen](https://github.com/CardputerZero/pi-gen/tree/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)） |

公式イメージの追跡ファイルでは、read-only 化、overlayfs、tryboot、RAUC、Mender の設定は見つかっていないとの調査結果がありますが、公開ファイル全体を再確認できていないため未確認です。確認には [CardputerZero/pi-gen の公開ファイル](https://github.com/CardputerZero/pi-gen/tree/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc) と配布 image の内容を照合する必要があります。この否定的な記述はイメージの全バイナリ内容を保証するものではありません。

`cardputer-zero-os` の GitHub URL は HTTP 404 でした。一次（Devin が 2026-10-18 に確認）。`cardputer-zero-shell` の URL 状態（404 かどうか）と、org の公開一覧への掲載有無は未確認です。確認先: https://github.com/CardputerZero/cardputer-zero-shell、https://github.com/orgs/CardputerZero/repositories。Wayback の保存説明では OS image ではなく Raspberry Pi OS / Debian 向け system profile とされ、LCD は `panel-mipi-dbi-spi` + DRM / Wayland 系の構成でしたが、保存説明と現行版の一致も未確認です（[Wayback archive](https://web.archive.org/web/*/https://github.com/CardputerZero/cardputer-zero-os)）。`cardputer-zero-os` は GitHub org の公開一覧にありません。

公開資料で確認した主な訂正点をまとめます。

- Lite 版にないのは付属の microSD カードで、カードスロットはある。
- Raspberry Pi の文書では tryboot は全モデル対応。ただし BCM2837 / CM0 実機での動作確認はまだない。
- `PARTITION_WALK` は EEPROM ブートローダー搭載機（Pi 4 以降）の機能で、CM0 では使えない。
- ES8389 overlay の compatible は `everest,es8390`。
- 公式 `cardputer-zero-os` は GitHub の URL が 404 で、org の公開一覧にもありません。公開一覧は 34 件という記録と API の 33 件という記録があり、数え方の差は未確認です。比較対象の公式ソフトウェア基準は pi-gen と M5 ドライバとします。https://github.com/CardputerZero/cardputer-zero-os、https://github.com/orgs/CardputerZero/repositories、https://api.github.com/orgs/CardputerZero/repos?per_page=100
- M5 の `panel-mipi-dbi-m.c` は `<drm/clients/drm_client_setup.h>` を include し、このヘッダーは rpi-6.18.y にあります。rpi-6.12.y の同じパスは 404 ですが、6.12 系全体でヘッダーがないかは未確認です。6.13〜6.17 も未確認。

### よくある誤解と正しい内容

| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| Lite 版の microSD | Lite 版にはカードスロットがない | microSD スロットはあるが、カードは付属しない | [M5Stack CardputerZero](https://docs.m5stack.com/en/CardputerZero) |
| `PARTITION_WALK` | 全 Raspberry Pi で利用できる | EEPROM ブートローダー搭載機の機能で、Pi 4 以降が対象。CM0 では使えない | [Raspberry Pi bootflow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc) |
| tryboot | CM0 では非対応 | Raspberry Pi 文書では全モデル対応と記載。CM0 実機での動作は未確認 | [Raspberry Pi autoboot.txt docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc) |
| `powerfail_suo` | SysRq-U のみを行う | SysRq-U に加え、バックライト制御と GPIO 操作を行う | [M5 `powerfail_suo.c`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c) |
| ES8389 | compatible は `everest,es8389` | compatible は `everest,es8390` | [M5 CardputerZero overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts) |

### 詳細な調査記録

本文の条件、数値、確認度、根拠 URL を含む調査記録は、次の文書に分割しています。

- [調査の前提・ハードウェア・候補](docs/research/scope-and-hardware.md)
- [起動高速化・カーネル](docs/research/boot-and-kernel.md)
- [電源断耐性・A/B 更新](docs/research/power-and-updates.md)
- [ストレージ・SD カード・フラッシュ測定](docs/research/storage-and-flash.md)
- [セキュリティ・ハードニング](docs/research/security-hardening.md)
- [ハードウェア機能の対応表](docs/research/scope-and-hardware.md#ハードウェア機能の対応表)
- [ユーザー空間・SSH/VPN 調査](docs/research/userspace-and-security.md)
- [未確認事項・測定・調査限界](docs/research/measurement-and-planning.md)
- [訂正済み事項](docs/research/corrections.md)
- [出典一覧と URL 取得記録](docs/research/sources.md)

### この記録に含めないもの

特定の外部製品比較、商標の個別確認、レポートの版管理情報は収録対象外です。名称の由来は本書に残します。

出典: [pi-gen commit](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)、[kernel pin](https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3)、[M5 ドライバ](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)、[Raspberry Pi bootflow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)。

## 起動時間（実測値と分析）

CM0 上の Buildroot / MSD/Linux の起動時間は未測定です。下表は対象・条件・計測終点が異なるため、数値を合算・平均しません。

| 数値 | 対象・条件 | 確認度と解釈 | 出典 |
|---|---|---|---|
| GPU firmware 2,112 ms、画面点灯 2.26 s | CardputerZero、M5 の独自 227 KB bare-metal splash。電源投入から ARM 開始まで | M5 自身のベンチマーク記載。Linux 全体の起動時間ではない。一次（Devin が 2026-10-18 に公開資料で確認） | [BENCHMARK.md](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21) |
| 約 7〜9 s | 同じ M5 資料の「Linux 可用」値 | 実測と概算の合算で終点定義がない。値の信頼性は低い。一次（Devin が 2026-10-18 に公開資料で確認） | [BENCHMARK.md](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21) |
| ARM 開始 約 6.79 s | Raspberry Pi 3B+。既定 firmware、11.7 MB initramfs、約 10.2 MB kernel8.img | Raspberry Pi の公式 white paper のログで、CM0 にそのまま当てはめられません。一次（Devin が 2026-10-18 に公開資料で確認） | [RP-010196-WP-1](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| 5.38 → 4.75 → 4.47 s | Zero 2 W + HQ camera。検出機能を無効化し、さらに initramfs を削除した個人ブログの自己申告 | 条件固有の二次情報。kernel 読込のログ差から約 1.54 s と算出した記載には、ログのタイミングが読込完了後である可能性がある。二次 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| 3.5 s 未満 | Zero 2 W、Buildroot 2024.02.1、GPIO トグルまで。非圧縮 kernel、initramfs なし、USB / sound 等多数を無効、KASLR / Spectre 緩和も無効 | 個人ブログの自己申告。CardputerZero の機能を含まず、条件を同等に比較できない。二次 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| 約 5.5 s | 古い buildroot-quickpi の README にある値 | 対象・条件が限られ、2018 年から更新停止。参考値のみ。二次 | [README](https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16) |

M5 の約 2.1 秒は小さな bare-metal カーネルの GPU firmware 段であり、通常の Linux kernel / initramfs 読込の下限ではありません。GPU 段が kernel サイズに比例するかは未確認です。Pi 3B+ と Zero 2 W の kernel 読込値は機材・ログ区間が違うため比例関係を推定できません。最初に公式イメージの同一個体で計測し、始点・終点・カーネル・SD を記録します。

以下に未実施の計測案を示します。

- 主指標は LCD にプロンプトが出てキー入力を受け付ける時点、副指標は init の終点マーカー時点とする。
- GPIO トグル、UART 時刻、`printk.time=1`、`initcall_debug`、`scripts/bootgraph.pl`、ハイスピード撮影を組み合わせる。
- 同じ個体・SD・firmware・cmdline で一度に一要素だけ変更し、コールドブート 15 回以上の中央値と p90 を記録する。初回は別扱いにする。
- 測定用ログは起動時間に影響する。量産ビルドと測定ビルドを区別する。systemd を使う場合、`systemd-analyze blame` は並列起動待ちを反映せず、`Type=simple` のサービスも測れない。

出典: [kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)、[bootgraph.pl](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33)、[systemd-analyze](https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、[Raspberry Pi boot-time white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf)。

## 高速化のアイデア一覧

期待効果は CM0 実機で測定していません。下表の提案は検証優先度を決める材料であり、適用済み機能ではありません。設計上の判断と公開資料で確認できた事実を区別し、根拠を確認できない主張は未確認または推測として示します。

| アイデア | 期待される効果 | リスク・条件 | 確度 | 出典 |
|---|---|---|---|---|
| `kernel8.img` を gzip 再圧縮 | zopfli または libdeflate `-12` の標準 deflate で、同一 kernel を約 3〜8% 小さくできる可能性 | firmware gunzip 互換を、展開後の `cmp` でビット一致確認する。無圧縮と gzip は実機で SD 読込時間と展開時間を比較して決める | 【案・未検証】 | [Raspberry Pi boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52) |
| `start_cd.elf` / `fixup_cd.dat` の採用を比較 | 小さい firmware の可能性 | M5 ベンチで使用。GPU メモリ 16 MB（`gpu_mem=16`）で起動できるか、VC4 を起動時に使わない条件で確認 | 【案・未検証】 | [M5 benchmark](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21) |
| `boot_delay=0`、`disable_splash=1`、`avoid_warnings` | 不要な待機・表示・警告処理を減らす可能性 | BCM2837 での差分を個別に測る。`avoid_warnings` は警告を隠すため診断時は使わない | 【案・未検証】 | [config.txt boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc) |
| 未使用 dtoverlay を削除 | 不要デバイスの probe や初期化を避ける可能性 | GPIO / I2C / USB の実使用と overlay の依存を確認します。M5 公式 config と Makefile の overlay 名に不整合があります | 【一次】 | [M5 config.txt](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12)、[M5 driver repository](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20) |
| 起動必須機能を built-in、任意機能をモジュールに分ける | 不要な driver probe を終点後へ遅らせる | 起動時に必要な SD / FS / I2C1 / M5IOE1 / LCD / keyboard の依存順を保つ。Wi-Fi / BT / audio / camera / IMU / HDMI / Ethernet は後読み候補 | 【案・未検証】 | [M5 v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts) |
| `quiet`、事前設定 `lpj=`、測定時 `initcall_debug` | 本番の printk 負荷を減らし、測定時は遅い initcall を特定 | `lpj=` の値は誤ると遅延精度に影響。測定ログ自体が時間に影響するため測定用 / 量産用を分ける | 【案・未検証】 | [kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html) |
| ST7789 DRM panel 上で fbcon を CLI に使う | HDMI / GUI を起動せず内蔵 LCD を直接使う | `FRAMEBUFFER_CONSOLE` の実効値、DRM/fbcon 割当、`fbcon=map:off` の影響を実機確認する | 【推測】 | [RPi defconfig](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1110-L1135) |
| initramfs を使わない | initramfs 読込・展開と RAM 使用を削減 | 起動に必要なドライバと rootfs driver を built-in にする。外部モジュールの firmware 配布方法も設計する | 【案・未検証】 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| initramfs 非同期展開 (`initramfs_async=`) | 他の起動処理と展開を重ねられる可能性 | kernel parameter として存在する。initramfs なしとの比較が必要。古い資料の説明は最新 kernel で再検証する | 【一次（parameter の存在）】・【推測（効果）】 | [kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html) |
| SquashFS と EROFS を実機比較 | 読込・展開 CPU の差を見て最適化 | SquashFS は zstd / lz4、128〜256 KiB ブロックを候補に、EROFS は lz4・4 KiB クラスタを候補にする。同条件のサイズ・RAM・読込量も比較 | 【案・未検証】 | [SquashFS docs](https://docs.kernel.org/filesystems/squashfs.html)、[EROFS FAQ](https://erofs.docs.kernel.org/en/latest/faq.html)、[EROFS docs](https://docs.kernel.org/filesystems/erofs.html) |
| BusyBox init + mdev | 小さい init / userland でサービス数と起動処理を減らす | M5 の udev ルールは `ID_PATH` や symlink を使い、systemd unit もある。mdev でそのまま置換できるとは限らず、eudev 併用またはルール移植が必要 | 【推測】 | [M5 udev rules](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules)、[BusyBox FAQ](https://busybox.net/FAQ.html) |
| read-only SquashFS で preload / readahead を使わない | 起動時の余分な I/O と先読み処理を避ける | 効果は未測定。必要なら fanotify / blktrace で実アクセスを見てから再検討 | 【案・未検証】 | [readahead(2)](https://man7.org/linux/man-pages/man2/readahead.2.html)、[fanotify(7)](https://man7.org/linux/man-pages/man7/fanotify.7.html) |
| `mksquashfs -sort` で起動ファイルを配置 | 初期アクセスを連続読込に近づける可能性 | open 順は物理 I/O 順と同じとは限らない。ファイル配置と SD 読込量、終点時間を実測する | 【推測】 | [SquashFS docs](https://docs.kernel.org/filesystems/squashfs.html) |
| `fanotify` / `strace` / `blktrace` で起動時アクセスを観測 | 起動に必要なファイル・ブロック I/O を把握 | `strace` は ptrace overhead がある。`blktrace` には `CONFIG_BLK_DEV_IO_TRACE` が必要 | 【一次（ツール機能）】・【推測（影響）】 | [strace(1)](https://man7.org/linux/man-pages/man1/strace.1.html)、[blktrace(8)](https://man7.org/linux/man-pages/man8/blktrace.8.html) |
| 不要なカーネル機能と DTB を削る | kernel / DTB を小さくし初期化・読込を減らす | M5 必須ドライバとデバイス依存を落とすと起動不能になる。効果は実測が必要 | 【推測】 | [KittenLabs](https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/) |
| Wi-Fi / camera / display の自動検出を抑える | 不要な probe を省ける可能性 | Raspberry Pi の公開測定は別 SoC / 別条件です。CardputerZero の LCD と周辺機器に必要なものは残します。CardputerZero での効果は未確認です | 【未確認】 | [RP-010196-WP-1](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| `max_framebuffers=0`、`disable_fw_kms_setup=1` 等を比較 | HDMI EDID / firmware KMS 初期化を省く可能性 | white paper の該当記述は未確認です。LCD 表示や HDMI の要件と衝突する場合があります | 【未確認】 | [Raspberry Pi config docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc)、[RP-010196-WP-1](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| `core_freq` / `initial_turbo` を比較 | kernel 読込短縮の可能性 | mini-UART 利用時の `enable_uart=1` が core frequency と干渉する可能性があります。温度・電力・再現性も記録します | 【推測】 | [Raspberry Pi config reference](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/reference.adoc) |
| BusyBox applet を最小化、外部 fork/exec を減らす | userland 実行数とサイズを減らす | CM0 の必要 applet は未調査。実利用を `strace` 等で採取してから除去する | 【推測】 | [BusyBox FAQ](https://busybox.net/FAQ.html)、[strace(1)](https://man7.org/linux/man-pages/man1/strace.1.html) |
| 静的リンク、LTO、UPX を比較 | 共有ライブラリ読込や配布サイズを抑える可能性 | 静的リンクはファイルサイズや更新対象を増やす場合がある。UPX は起動時の展開が追加されるため、起動速度向上を前提にせず実測する | 【推測】・【未確認】 | [BusyBox FAQ](https://busybox.net/FAQ.html) |
| ネットワーク / SSH 等の常駐を終点後へ遅延 | 終点前の service / driver 初期化を減らす | 本プロジェクトでは SSH / VPN を実装しない。一般的なネットワークも必要になるまで起動しない案 | 【推測】 | [systemd.socket(5)](https://man7.org/linux/man-pages/man5/systemd.socket.5.html)、[systemd.service(5)](https://man7.org/linux/man-pages/man5/systemd.service.5.html) |
| systemd を使う場合は unit を削り critical chain を短くする | 不要サービスを省き並列化を活かす | M5 の udev ルール・`fb_load.service` に systemd 前提がある。systemd は Buildroot で glibc が必要 | 【一次（Buildroot 制約）】・【推測（効果）】 | [systemd-analyze(1)](https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、[Buildroot systemd Config.in](https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in) |
| libc / allocator を比較 | サイズ、RSS、exec の差を削減できる可能性 | 公開比較は Intel x86 等で、Cortex-A53 の現行版比較は見つからない。起動差は CM0 実測が必要 | 【二次】・【未確認】 | [musl libc comparison](https://www.etalabs.net/compare_libcs.html)、[Buildroot toolchain options](https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in) |
| カーネル圧縮を gzip / 無圧縮で比較 | SD 読込時間と CPU 展開時間のトレードオフを最適化 | 標準 RPi arm64 起動で LZ4 / ZSTD / LZO を直接使える根拠なし。カスタム ARM stub / TF-A による展開は未確認 | 【推測】・【未確認】 | [Raspberry Pi boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52)、[rpi-eeprom issue #541](https://github.com/raspberrypi/rpi-eeprom/issues/541) |
| GPU firmware 段を省略する bootloader 案 | 理論上 firmware 起動を短縮する可能性 | `rpi-open-firmware` / `lk-overlay` は実験的とされています。対応 SoC・安定性は未確認です。U-Boot Falcon も GPU firmware 段をなくす方式ではありません | 【未確認】・【推測】 | [CardputerZero u-boot](https://github.com/CardputerZero/u-boot)、[rpi-open-firmware](https://github.com/librerpi/rpi-open-firmware)、[lk-overlay](https://github.com/raspberrypi/lk-overlay) |
| PREEMPT 設定 / printk を測る | initcall / printk overhead の傾向を比較 | 起動時間差は未測定。RT の printk 変更は CM0 非 RT に適用できない可能性。量産は `quiet`、測定は `PRINTK=y` を分ける | 【一次（Kconfig）】・【推測（性能）】 | [6.18 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt)、[printk change](https://lkml.iu.edu/2512.0/00981.html) |

## 電源断耐性

### 方針と候補

- rootfs は SquashFS の読み取り専用領域を第一候補にする。設定・ログ等の書込みを分離し、必要なら overlayfs の upper を tmpfs / zram に置く。
- 永続領域は小さく保つ。ext4 の `data=ordered`、`metadata_csum`、一時ファイルへの書込み後 `fsync` + `rename` を候補とし、ファイルシステムと SD の実電断試験で選ぶ。
- `/boot` は通常読み取り専用とし、更新時だけ書き込む。FAT の `autoboot.txt` も単一障害点になり得る。
- microSD の FTL が書込み中の電源断で無関係なデータを壊す可能性は、公開一次資料で確認できていません。未確認を前提に、更新中以外の書込みを減らします。A/B の非稼働スロットが常に無傷とは保証しません。
- F2FS は Raspberry Pi の white paper が電断後の破損について警告しているため保留。btrfs は microSD 上での電断保証を確認できず保留。UBIFS は生 MTD 向け、microSD では対象外。ext3 が Linux 6.18 で独立候補ではなく ext4 に統合済みとの情報は未確認です。確認には Linux 6.18 の公開 source tree の `fs/ext3` と `fs/ext4` を照合します。
- ext4 の `data=journal` は kernel 文書の最新版と 7.3-rc7 で非推奨（2028 年 1 月に削除予定）とされていますが、6.18 / 7.2 の該当文書には記載がありません。通常案は `data=ordered` です。最新版の注意を過去 kernel に誤って当てはめないよう、[最新版](https://docs.kernel.org/filesystems/ext4/journal.html)、[7.3-rc7](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v7.3-rc7)、[6.18](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v6.18)、[7.2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/ext4/journal.rst?id=v7.2) の記述を分けて確認します。
- 電源喪失保護（PLP）付き SD の研究・ベンダー主張は microSD 製品で確認が必要。pSLC は eMMC 向けで microSD には適用できないとの調査。スーパーキャパシタは筐体上難しいとの見立て。
- `dm-verity` は rootfs 検証の候補だが、BCM2837 に SHA 命令がない可能性があり、読み込み時のソフトウェア検証負荷は未測定。A/B 切替時のみ検証する案も未確認。
- `powerfail_suo` は GPIO6 の立下り後 500 ms debounce し、実装上は SysRq `u`（read-only 再マウント）のみ実行する。`s` と poweroff はコメントアウトされ、バックライトを消し `disabled-gpios` も駆動する。overlay に gpio-keys entry はなく、ユーザー空間へ電源断イベントを届けて正常停止する経路も未実装です。したがって突然の電池抜けや枯渇を救う機能ではない。
- zram は RAM 上の block device なので read-only rootfs と併用できる見込み。zswap は swap 先を必要とし、SD swap を避けるなら zram swap と同時に有効化しない案。実機では未検証。

出典: [overlayfs docs](https://docs.kernel.org/filesystems/overlayfs.html)、[ext4 docs](https://docs.kernel.org/admin-guide/ext4.html)、[Raspberry Pi resilient filesystem white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf)、[M5 powerfail driver](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115)。

### 電源断試験

起動時間測定・電断試験・障害解析は別モードにし、記録方式で結果を汚さないようにする。起動測定時はログを最小化し、UART と ext4 ログを無効にする。電断試験では USB-UART 経由で給電が回り込まないようにし、pstore/ramoops（リセット時のみ）、専用領域への追記、または電断後の外部回収を比較する。SysRq `s` / `u` / `b` はソフトな近似で、本物の電断試験の代用ではない。試験回数、書込み中の電断、アイドル時の電断、起動不能数を記録する。

電断時の block I/O 順序を評価する候補として、`dm-flakey`、`dm-log-writes`、CrashMonkey 等の障害注入があります。これらは実カードの FTL を再現するものではなく、実物の電源遮断試験も別途必要です。

出典: [ramoops docs](https://docs.kernel.org/admin-guide/ramoops.html)、[pstore block docs](https://docs.kernel.org/admin-guide/pstore-blk.html)、[SysRq docs](https://docs.kernel.org/admin-guide/sysrq.html)。

## A/B 更新

### tryboot と制約

- Raspberry Pi の文書は全モデルが tryboot に対応すると記載する。`autoboot.txt`、`[tryboot]`、`tryboot_a_b=1` で起動パーティションを切り替え、`reboot "0 tryboot"` で一度だけ試行する仕組みが説明されている。CM0 実機での確認は未実施。
- `PARTITION_WALK` は EEPROM 機能で Pi 4 以降のみ。CM0 の復旧策として使えない。
- 人手の recovery menu は設けず、自動ロールバックを目標とする。設計案は非稼働スロットへ書き込み、tryboot で試行し、選択した終点とヘルスチェックを通ってから既定スロットを確定する。終点判定は LCD + keyboard と PID 1 marker の両方を記録する案。失敗・再起動時の復帰動作、FAT 更新の原子性、試行回数カウンタは実機で確認する。
- ウォッチドッグの `kernel_watchdog_timeout` / `kernel_watchdog_partition`、BCM2835 WDT、systemd の watchdog 連携は候補だが、BCM2837 firmware でどの機能が有効か未確認。最初の実機試験は tryboot と watchdog の確認。
- boot パーティション（FAT）と Raspberry Pi firmware 自体は A/B 化されず、単一障害点になり得る。試行中の電断・`autoboot.txt` 更新中の電断も検証が必要。

### 更新フレームワーク比較

| 方式 | 調査結果 | 判断 |
|---|---|---|
| 自作 + tryboot | CM0 の公式実装は見つからず、独自の試行カウンタ / 確定判定が必要 | Buildroot の構成に合わせる有力案。ただし設計・実装・電断試験が必要 |
| RAUC | Raspberry Pi firmware 初期対応 PR #1599 は調査時点で未マージ。tryboot 用 custom backend が必要になる可能性 | 候補。カウンタや primary 起動失敗時の挙動を調査する |
| SWUpdate | tryboot 連携を確認できず | 次点 |
| Mender | Buildroot 統合は古い系列。mender-convert の RPi3 64-bit は U-Boot 方式、CM0 構成は未確認 | 次点。U-Boot を使わない方針と整合確認が必要 |
| rpi-image-gen `image-rota` | GPT A/B 層は cm4/pi4/cm5/pi5 限定。zero2w / pi3 の device 層はあるが A/B 層は対象外 | CM0 の直接的な公式構成ではない |
| MCUboot / boot-mbr-switch | VideoCore boot の先頭になれないという見立て。`boot-mbr-switch` は rootfs A/B ではなく bootloader 領域向け | 優先しない |

GPT と MBR の CM0 での挙動は未確認。MBR は安全側との見立てがある一方、複数 boot / rootfs パーティションに主パーティション 4 個の制約があるため、レイアウトは実機ブートで決める。RAUC custom backend を使う場合も、FAT 単一障害点と失敗復帰を別途扱う。

出典: [autoboot.txt docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83)、[watchdog config docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271)、[BCM2835 WDT driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c)、[rpi-image-gen A/B layer](https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11)、[RAUC PR #1599](https://github.com/rauc/rauc/pull/1599)、[Rugix devices](https://rugix.org/docs/bakery/devices/)。

## ストレージとフラッシュの要点

現行 CI イメージの MBR パーティション開始セクターは p1–p7 = `1 / 32769 / 163841 / 294913 / 294914 / 819203 / 1343492` です。各値の 4 KiB 境界からの余りは `1 / 1 / 1 / 1 / 2 / 3 / 4` セクターで、4 MiB 境界からの余りも同じです（1 セクター = 512 bytes）。genimage v20 で測定した `align=4M` 案では全開始位置が 4 MiB 境界にそろい、イメージは 736 MiB（現行より約 16 MiB 増）になりました。速度・寿命・電断耐性への効果は実機で未確認です。【実測】【未確認】[詳細と比較表](docs/research/storage-and-flash.md)

FAT データ領域はパーティション開始位置から 292 セクター（149,504 bytes）後に始まります。現行 p2 の絶対位置は 4 MiB 境界から 150,016 bytes ずれ、パーティション整列だけでは FAT 内部の BPB／データ領域 offset は変わりません。現行 `/data` は `data=journal` で、ext4 の現行文書はこの mode を非推奨とし、2028 年 1 月の削除予定を記載しています。`data=ordered` は移行候補ですが、アプリの `fsync`／rename と電断試験なしに同等の耐久性は主張できません。discard／fstrim、A1／A2、AU・消去単位はカードとホストで実測します。【一次】【実測】【推測】[用語、ext4、discard、測定計画](docs/research/storage-and-flash.md)

CI artifact の `/data` ext4 は `dumpe2fs` で 1,024 B ブロックと実測しました。これは 4 KiB page より小さい設定です。genimage の `extraargs` と実行時 formatter の両方に `-b 4096` を指定する案がありますが、page 境界との整合が性能や耐久性を高めるかは未測定で、効果は【推測】です。[実測値と mke2fs の選択理由](docs/research/storage-and-flash.md)

## セキュリティとハードニングの要点

microSD を物理交換できる攻撃者は Linux より前の起動ファイルを差し替えられます。Raspberry Pi の secure-boot 手順は Pi 4 以降が対象で、BCM2837 向け経路は文書化されていません（物理的に不可能とは断定しません）。現行 updater は `manifest.sig` を検証し、SHA-256 manifest と書込み後の read-back を確認します。鍵や dm-verity root digest を同じカードに置いても、カード全体の交換を防げません。【一次】【未確認】[脅威モデルと A/B/C 案](docs/research/security-hardening.md)

署名検証と読み取り専用 rootfs への公開鍵配置は実装済みです。今後は署名鍵のリリース・更新・失効手順、カーネル／sysctl のハードニング、不要な無線／USB 機能の採否を検討します。dm-verity は信頼できる digest の保管が条件です。起動・RAM・保守コストとハードウェア機能への影響、QEMU で検証できる更新処理と実機でしか検証できない BootROM／OTP・周辺機器を区別します。【一次】【推測】【未確認】[詳細と検証境界](docs/research/security-hardening.md)

## アイデア総覧

この表は高速化・電源断・A/B 案に、ストレージ、セキュリティ、ハードウェア機能の案を加えた一覧です。QEMU で確認できるのは仮想化された Linux・イメージ・更新処理に限られ、ファームウェアの選択、SD 性能、実物の周辺機器、電源断は実機で確認します。優先度は目安です。状態は `origin/main` のコードと設定に照合しました。「採用済み」は実装の存在を示し、実機動作の確認を意味しません。

| 分類 | アイデア | 期待効果 | コスト | リスク | 検証（QEMU / 実機） | 優先度 | 状態 |
|---|---|---|---|---|---|---|---|
| 高速化 | [`kernel8.img` gzip 再圧縮](#高速化のアイデア一覧) | 読込量を減らす | 再現可能なカーネル生成 | 展開時間やファームウェア互換 | QEMU: 起動 / 実機: 読込・展開時間 | P2 | 一部採用（圧縮方式・サイズ比較あり、非圧縮実測なし） |
| 高速化 | [`start_cd.elf` / `fixup_cd.dat`](#高速化のアイデア一覧) | 小さいファームウェアの可能性 | 低 | GPU/ファームウェア互換 | QEMU: ファームウェア不可 / 実機: 起動 | P3 | 採用済み（実機未確認） |
| 高速化 | [`boot_delay=0` / `disable_splash=1`](#高速化のアイデア一覧) | 不要な待機・表示を減らす | 低 | 診断情報を隠す可能性 | QEMU: Linux 部分のみ / 実機: 起動時間 | P2 | 採用済み（効果未実測） |
| 高速化 | [未使用 dtoverlay の削除](#高速化のアイデア一覧) | 不要初期化探索を抑える | 中 | 必須機能喪失 | QEMU: DT / 実機: 全機能 | P2 | 未着手 |
| 高速化 | [必須ドライバー組み込み、任意機能モジュール](#高速化のアイデア一覧) | 任意初期化探索を遅らせる | 中 | モジュール依存順・起動不能 | QEMU: 起動 / 実機: LCD・入力 | P1 | 未着手 |
| 高速化 | [`quiet` / `lpj=` / `initcall_debug`](#高速化のアイデア一覧) | printk 負荷・遅い initcall の評価 | 低 | `lpj` 誤設定、測定付加負荷 | QEMU: log / 実機: 時間 | P2 | 一部採用（quiet のみ） |
| 高速化 | [ST7789 DRM panel + fbcon](#高速化のアイデア一覧) | HDMI/GUI なしの CLI | 中 | console blank / 割当違い | QEMU: 不可 / 実機: LCD | P1 | 未着手 |
| 高速化 | [initramfs を使わず `root=` を直接指定](#高速化のアイデア一覧) | 読込・展開・RAM を削減 | 中 | root ドライバー不足 | QEMU: 起動 / 実機: 起動時間 | P2 | 採用済み |
| 高速化 | [`initramfs_async=`](#高速化のアイデア一覧) | 展開と他処理を重ねる可能性 | 低 | 効果が負荷条件依存 | QEMU: 比較 / 実機: 起動時間 | P3 | 対象外（initramfs なし） |
| 軽量化 | [SquashFS と EROFS の比較](#高速化のアイデア一覧) | サイズ・読込・CPU の選択 | 中 | 圧縮・起動要件の差 | QEMU: 機能 / 実機: I/O・RAM | P2 | 未着手 |
| 軽量化 | [BusyBox init + mdev](#高速化のアイデア一覧) | ユーザー空間/サービスを小さくする | 中 | udev ルール / systemd 依存 | QEMU: デバイス / 実機: 全機能 | P3 | 採用済み |
| 高速化 | [読み取り専用 SquashFS と preload/readahead](#高速化のアイデア一覧) | 不要な先読みを避ける | 低 | 必要な読込まで遅れる | QEMU: I/O 観測 / 実機: 起動時間 | P3 | 一部採用（SquashFS rootfs、先読み未実施） |
| 高速化 | [`mksquashfs -sort`](#高速化のアイデア一覧) | 起動ファイルの配置を最適化 | 低 | open 順と I/O 順が不一致 | QEMU: イメージ / 実機: SD 読込 | P3 | 未着手 |
| 高速化 | [fanotify / strace / blktrace](#高速化のアイデア一覧) | 起動 I/O の把握 | 中 | 監視付加負荷 | QEMU: trace / 実機: 比較測定 | P2 | 未着手 |
| 軽量化 | [不要カーネル機能・DTB の削減](#高速化のアイデア一覧) | イメージと初期化を減らす | 中 | 必須周辺機器を失う | QEMU: 起動 / 実機: 全機能 | P2 | 未着手 |
| 高速化 | [Wi-Fi/camera/display 自動検出抑制](#高速化のアイデア一覧) | 未使用初期化探索を減らす可能性 | 中 | 全機能維持の柱と衝突するため遅延ロードで代替 | QEMU: 一部 / 実機: 対象機能 | P3 | 対象外（遅延ロードで代替） |
| 高速化 | [`max_framebuffers` / ファームウェア KMS](#高速化のアイデア一覧) | HDMI 初期化を抑える可能性 | 低 | LCD/HDMI と競合 | QEMU: 限定 / 実機: 表示 | P3 | 未着手 |
| 高速化 | [`core_freq` / `initial_turbo`](#高速化のアイデア一覧) | 起動ファームウェア読込時間を短縮する可能性 | 低 | 発熱・電力・UART clock | QEMU: 不可 / 実機: 時間・温度 | P3 | 未着手 |
| 軽量化 | [BusyBox applet 最小化・fork削減](#高速化のアイデア一覧) | ユーザー空間処理を削減 | 中 | 実行時に必要コマンド不足 | QEMU: 起動 / 実機: 利用操作 | P3 | 未着手 |
| 軽量化 | [static link / LTO / UPX](#高速化のアイデア一覧) | 配布サイズや load を比較 | 中 | サイズ増・展開 CPU | QEMU: 起動 / 実機: 時間・RSS | P3 | 未着手 |
| 高速化 | [ネットワーク起動を終点後へ遅延](#高速化のアイデア一覧) | 対話可能になる前のネットワークサービスを減らす | 低 | 利用可能になるまで遅れる | QEMU: サービス / 実機: 入力時点 | P2 | 未着手 |
| 軽量化 | [systemd ユニットの削減](#高速化のアイデア一覧) | 不要ユニットを減らす | 中 | BusyBox init を使うため対象外 | QEMU: ユニット / 実機: 時間 | P3 | 対象外（BusyBox init 使用） |
| 軽量化 | [libc / allocator 比較](#高速化のアイデア一覧) | 起動・RAM・サイズ最適化 | 高 | ABI/互換性・測定条件 | QEMU: 機能 / 実機: RAM・時間 | P3 | 未着手 |
| 高速化 | [カーネル gzip / 非圧縮比較](#高速化のアイデア一覧) | 読込時間と展開時間を最適化 | 低 | ファームウェア対応形式 | QEMU: Linux / 実機: 起動経路 | P2 | 一部採用（gzip 方式の生成時比較、非圧縮実測なし） |
| 高速化 | [GPU ファームウェアを省くブートローダー](#高速化のアイデア一覧) | ファームウェア段を短縮する可能性 | 高 | 非公式・SoC 互換性 | QEMU: 不可 / 実機: 起動信頼性 | P3 | 未着手 |
| 高速化 | [PREEMPT / printk 比較](#高速化のアイデア一覧) | 起動ログ・init 付加負荷の評価 | 低 | 起動時間以外の影響 | QEMU: 起動 / 実機: 時間 | P3 | 未着手 |
| 信頼性 | [読み取り専用 SquashFS rootfs](#電源断耐性) | rootfs の永続書込みをなくす | 現行構成 | 可変領域の容量・電断 | QEMU: マウント/update / 実機: 電断 | P1 | 採用済み |
| 信頼性 | [`align = 4M`](docs/research/storage-and-flash.md) | 全パーティション開始位置を 4 MiB 境界にする | イメージが約16 MiB増 | 実機効果・ファームウェア互換性未確認 | QEMU: レイアウト / 実機: 性能・電断 | P1 | 未着手（origin/main 未反映） |
| 信頼性 | [FAT data-area offset の扱い](docs/research/storage-and-flash.md) | ファイルシステム内部位置を把握 | フォーマッター/レイアウト変更 | パーティション alignment だけでは変わらない | QEMU: BPB / 実機: カード性能 | P2 | 一部調査済み（offset 測定済み、性能未測定） |
| 信頼性 | [`data=ordered` 移行検討](docs/research/storage-and-flash.md) | `data=journal` の非推奨に備える | アプリ・FS 試験 | fsync/rename と電断時整合性 | QEMU: FS / 実機: 電源断 | P1 | 未着手 |
| 信頼性 | [barrier / `commit=` と `/data` 検証](docs/research/storage-and-flash.md) | マウント durability を確認 | マウント・アプリ変更の可能性 | SD FTL の保証ではない | QEMU: マウント / 実機: 電断 | P1 | 未着手 |
| 信頼性 | [discard / `fstrim`](docs/research/storage-and-flash.md) | 対応時の空き領域通知 | カード・カーネル対応確認 | 未対応や性能差 | QEMU: コマンド / 実機: discard | P2 | 未着手 |
| 信頼性 | [カード erase/AU/sysfs と SD 性能測定](docs/research/storage-and-flash.md) | alignment 判断にデータを得る | 複数カード・計測 | 値は erase ユニット / 耐久保証でない | QEMU: 不可 / 実機: fio・sysfs | P1 | 未着手 |
| 信頼性 | [A/B + tryboot + watchdog](docs/research/power-and-updates.md) | 起動失敗を検出し旧スロットへ戻す案 | 状態・watchdog・試験 | S01msd-watchdog は実装済み、実機動作は未確認 | QEMU: スロット / 実機: tryboot・ハング | P1 | 採用済み（実機未確認） |
| 信頼性 | [電源異常正常停止](docs/research/power-and-updates.md) | 電源異常を graceful 停止に接続 | ドライバー / ユーザー空間変更 | 電源保持時間不足の可能性 | QEMU: 不可 / 実機: 電源試験 | P1 | 未着手 |
| 信頼性 | [更新記録の fsync/rename 原子性](docs/research/power-and-updates.md) | 確定記録の破損リスク低減 | 更新処理実装・試験 | FAT 上の原子性未保証 | QEMU: 更新処理 / 実機: 電断 | P1 | 一部採用（fsync・一時ファイル rename、電断未検証） |
| 信頼性 | [p7 ext4 を `msd-data-grow` で拡張](#電源断耐性) | 利用可能容量を増やす | first-起動 script | 中断時の FS 整合性 | QEMU: サイズ変更 / 実機: 電断 | P2 | 採用済み |
| 信頼性 | [RAUC / SWUpdate / Mender / Rugix 比較](docs/research/power-and-updates.md) | 更新方式を選ぶ | 導入・保守負担 | ファームウェア/bootchooser 互換性 | QEMU: package / 実機: ロールバック | P2 | 未着手 |
| セキュリティ | [署名検証・公開鍵配置と鍵運用](docs/research/security-hardening.md) | 更新物の真正性 | 署名鍵の運用 | 全 microSD 交換は防げない | QEMU: reject / 実機: 信頼連鎖 | P1 | 一部採用（署名検証・鍵配置あり、鍵運用未確認） |
| セキュリティ | [dm-verity と trusted root digest](docs/research/security-hardening.md) | root block 改ざん検知 | 起動 cmdline・digest管理 | digest が同じカードなら無効 | QEMU: corruption / 実機: 信頼起点 | P2 | 未着手 |
| セキュリティ | [`nosuid,nodev,noexec` と sysctl](docs/research/security-hardening.md) | `/data` からの権限昇格面を減らす | マウント・互換試験 | アプリ互換性 | QEMU: マウント / 実機: アプリ | P1 | 未着手 |
| セキュリティ | [SSP / FORTIFY / RELRO / PIE](docs/research/security-hardening.md) | exploit mitigation（FORTIFY_SOURCE_3 は現行設定） | binary サイズ・ビルド時間 | toolchain/package 互換 | QEMU: ビルド / 実機: アプリ | P2 | 一部採用（FORTIFY_SOURCE_3、残り未監査） |
| セキュリティ | [A/B 更新の署名・SHA-256 manifest・読込-back](docs/research/security-hardening.md) | 書込み破損検出・スロットイメージ確認 | 現行更新処理 | 署名鍵の配布・更新・失効手順は要確認 | QEMU: 正常/破損 bundle / 実機: 書込み復旧 | P1 | 採用済み |
| セキュリティ | [未使用 Wi-Fi/BT/USB surface の削減](docs/research/security-hardening.md) | attack surface を縮小 | 機能・保守判断 | 無線/USB 機能喪失 | QEMU: 設定 / 実機: peripheral | P2 | 未着手 |
| セキュリティ | [対応 secure-起動 SoC への移行](docs/research/security-hardening.md) | ファームウェア信頼連鎖を追加 | 高い BOM・移植費 | board/起動 migration | QEMU: 非対象 / 実機: BootROM | P3 | 未着手 |
| ハードウェア | [ドライバー / ファームウェア / overlay の実機対応表](docs/research/scope-and-hardware.md#ハードウェア機能の対応表) | 未対応・遅延可能機能を把握 | 各機能の個別試験 | 初期化探索成功だけで動作を誤認 | QEMU: 一部 / 実機: 全周辺 | P1 | 一部調査済み（実機動作未確認） |
| ハードウェア | [IR / camera / IP2315 charger の対応調査](docs/research/scope-and-hardware.md#目標との差分) | 未実装機能との境界を明確化 | media/charger ドライバー調査 | ハードウェア revision 依存 | QEMU: 設定 / 実機: I/O | P2 | 一部調査済み（実機対応未確認） |
| 試験・保守 | [更新中を含む 200 回電源断試験案](#電源断耐性) | 電断失敗 rate を評価 | 長時間・試験治具 | 例示合格条件で保証ではない | QEMU: 不可 / 実機: 反復試験 | P1 | 未着手 |
| 試験・保守 | [ホストテスト（msd-update／msd-data-grow／msd-hwinfo）](.devin/wiki.json) | 更新・拡張・機器情報処理を回帰検査 | 低 | ホスト試験は実機の周辺機器動作を保証しない | tests/ 配下3 テスト一式／実機：全機能 | P1 | 採用済み |
| 試験・保守 | [SSH / VPN 実装](docs/research/userspace-and-security.md) | 遠隔管理 | 鍵・更新・攻撃面 | 現方針では実装対象外 | QEMU: 不要 / 実機: 不要 | P3 | 不採用 |
| 軽量化 | GPU メモリ／CMA 量の見直し | RAM の余地を評価 |調査・測定| 削減で表示機能を損なう可能性 | 実機で必要量を測る | P2 | 未着手 |
| 軽量化 | zram／zswap の評価 | RAM 内の圧縮 swap を評価 |調査・測定| base defconfig は `ZRAM=m`／`ZSWAP=y`、実運用未確認 | QEMU・実機で評価 | P2 | 一部採用（base defconfig、実運用未確認） |
| 信頼性 | `kernel_watchdog_timeout` の OS 引継ぎ | watchdog 起動後給餌 |調査・測定| CM0 対応未確認 | QEMU・実機ハング/リセット | P1 | 一部採用（S01msd-watchdog、ファームウェア handover 未確認） |
| 信頼性 | `get_throttled` 低電圧・温度記録 | 電源・温度異常を記録 |調査・測定| bit 0／16、3／19。実機未測定 | 実機 | P1 | 未着手 |
| 信頼性 | `/data` fsck 時間 | 起動遅延を把握 |調査・測定| `fsck.ext4 -p` 実装済み、時間未測定 | QEMU・実機起動時間 | P1 | 一部採用（fsck 実装、時間未測定） |
| 信頼性 | `/data` ext4 4 KiB block／`inline_data` | 1 KiB と 4 KiB の割り当て量、inode 内保存の候補 |調査・測定| 小さい file での差はローカル測定済み。実機性能は未確認 | QEMU・実機 I/O／fsck | P2 | 候補（効果は未検証） |
| セキュリティ | カーネル Kconfig／sysctl hardening | 攻撃面を緩和 |調査・測定| RAM／CPU／保守コストあり | 設定・実機回帰 | P1 | 未着手 |
| 高速化 | [SquashFS codec／block size の実機比較](docs/research/soc-memory-compression.md) | rootfs size と展開・読込時間を比較 | 複数 build と実機測定 | SD rate、cache、CPU clock に依存 | QEMU: 起動 / 実機: SD・CPU | P1 | image size 実測済み、速度未測定 |
| 軽量化 | [kernel compressor / EROFS の削減比較](docs/research/soc-memory-compression.md) | `Image` / `vmlinux` size を比較 | kernel build と回帰試験 | rootfs 互換性・全 hardware 維持 | QEMU: mount・A/B / 実機: 起動 | P2 | 未着手 |
| 高速化 | [Buildroot `-O2` / `-Os`、LTO / PGO](docs/research/soc-memory-compression.md) | userland size と CPU-bound workload を比較 | build time、profile 回収、再現性 | package 対応と stale profile | QEMU: 機能 / 実機: CPU・起動 | P2 | 未着手 |
| 試験・保守 | [三段階 simulator 検証](docs/research/measurement-and-planning.md#シミュレーターと検証基盤の比較) | QEMU 機能、TCG option 比較、実機 timing を分離 | hardware proxy と実機が必要 | QEMU / gem5 の時間を実機値と混同しない | QEMU・gem5・Zero 2 W・CM0 | P1 | 方針案 |

## QEMU で検証できる範囲

QEMU の `raspi3b` machine は BCM2837 SoC をエミュレートしますが、Raspberry Pi の GPU ファームウェアや `tryboot`、CardputerZero の LCD・内蔵キーボード・M5 I2C デバイスは再現しません。`test-boot.sh` と `test-ab.sh` は p5／p6 の rootfs 起動後に `MSD/Linux ready` marker と login prompt を確認します。ホストテストでは更新処理の slot 判定・切替ロジックを確認します。ファームウェアによる tryboot、自動 rollback、実機周辺機器は実機検証の対象です。

## OS ベース比較

以下は公開資料で確認した OS 候補の比較です。値や互換性は出典に記載された条件とともに示し、本リポジトリでは試していません。

| 候補 | 調査結果 | 起動 / 要件への評価 |
|---|---|---|
| Buildroot 2026.08 | `raspberrypizero2w_64_defconfig` と `raspberrypi3_64_defconfig` があります。CM0 専用 defconfig の有無は未確認です。GCC 既定は 15.3.0 | 最小化・独自 A/B に適しそうとの推測です。Zero 2 W で <3.5 s の第三者値は条件が大きく異なります |
| 公式 CardputerZero pi-gen | Debian trixie / systemd / labwc、kernel 6.18.39 固定。追跡対象の公開ファイルでは A/B / RO 設定を確認できていません | M5 の現行ベースラインとして有用です。Linux 可用 7〜9 s は終点定義がありません |
| Yocto / meta-raspberrypi | `raspberrypi0-2w-64.conf` と `linux-raspberrypi_6.18.bb` があります。CM0 専用 machine の有無は未確認です。read-only-rootfs は利用可能です | Buildroot の代替です。ビルド・学習負担が大きく、起動時間の比較値はありません |
| Ubuntu Server / Minimal Ubuntu 26.04.1 | Imager 一覧に Pi 3 向け Server がある | 起動時間・A/B の根拠なし。systemd 標準 |
| Ubuntu Core 26 | Imager 一覧で pi3-64bit 向けを確認。最小 RAM / ストレージや起動高速化資料は未確認 | snap の recovery / seed が A/B 相当か未確認、秒数もなし |
| rpi-image-gen | Pi 3 / Zero 2 W の device 定義あり。`image-rota` は Pi 4 / 5 クラスのみ | CM0 の公式 A/B 構成には使えない |
| Zephyr v4.4 / Canonical Zephyr 26.04 | v4.4 に `rpi_zero_2w` / `bcm2710` 定義がないとの記述がありますが、公開 tree で未確認です。Canonical fork も未確認です | upstream main の Pi Zero 2 W 定義と SDHCI 対応状況は未確認です。CM0 対応は評価できません |
| Alpine 3.24.2 / piCore64 17.0 | CM0 対応、kernel 6.18 系との情報がありますが、公開資料の確認が未完了です | A/B と起動時間の根拠はありません。RAM 展開型は 512 MB で厳しい可能性があります |
| BusyBox 単独 | OS ではなく userland。Buildroot の最小構成で利用できる | kernel / firmware は Buildroot と共通。独立した起動時間根拠なし |
| Rugix Bakery / Ctrl | 対応表では Pi 3 は tryboot、Zero 2 W は U-Boot。CM0 自体は一覧にない | U-Boot は GPU firmware 後に起動し、CM0 の直接対応は未確認 |
| Android / BSD / RTOS / OpenWrt | 512 MB / CLI、M5 Linux ドライバ非対応、または kernel 6.12 系という理由で優先外 | FreeBSD 15.1 の Zero 2 W 対応は未確認です。LCD / keyboard / M5IOE1 も未確認です |

出典: [Buildroot 2026.08](https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1)、[Yocto meta-raspberrypi](https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf)、[Raspberry Pi Imager OS list](https://downloads.raspberrypi.com/os_list_imagingutility_v4.json)、[Zephyr Pi Zero 2 W board](https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w)、[Rugix devices](https://rugix.org/docs/bakery/devices/)。

## カーネル

- `kernel8.img` は `pigz -11 -n` で作成し、gunzip 後に `Image` と一致することを検査する。実サイズはビルドログの `Kernel compression sizes` 行に記録する。この文書では未測定値を記載しない。
- 基準は `rpi-6.18.y` とします。RPi kernel 6.18.57、Buildroot 2026.08 の 2026-09-04 版を公開情報で確認しました。カーネルと M5 driver は commit 固定します。
- M5 DRM panel API が 7.1 で削除され、7.0 で ASoC API が変更されたとの情報は未確認です。確認には M5 driver と Raspberry Pi kernel の公開 tree を版ごとに比較する必要があります。M5 driver をそのまま build できるかは未確認です。6.18 を基準、7.2 は同一構成での比較候補とします。
- 6.18 から 7.2 で BCM2835 SD host / KASLR / 圧縮展開コードの変更がないとの調査。ただし BCM2837 の実測差はない。6.18 以降の起動時間に関係しそうな公開変更は条件付き、未マージ、または x86 / 大容量向けで、CM0 に適用できる証拠は乏しい。
- 6.18 arm64 は PREEMPT_NONE が既定で VOLUNTARY 選択可能との調査。7.2 では arm64 の PREEMPT_LAZY 機能により NONE / VOLUNTARY を選べないとの調査。起動時間への影響は未測定。PREEMPT_RT は対象外。
- 7.3 系で arm64 linear alias unmap の変更が再適用されたとの情報は、公開 commit history を確認できていないため未確認です。再適用後の Raspberry Pi 3 / CM0 起動も未確認です。確認先は [Raspberry Pi Linux 7.3.y source tree](https://github.com/raspberrypi/linux/tree/rpi-7.3.y/arch/arm64/mm) です。7.x 比較時は起動可否を先に確認します。
- M5 の v5 overlay 依存では I2C1 → M5IOE1 → LCD backlight / SPI0 panel、および keyboard / input の鎖を考慮する。optional driver は終点後に modprobe する案。
- arm64 kernel は firmware 起動で gzip または非圧縮を前提に評価する。LZ4 / ZSTD / LZO kernel 形式を標準起動で使う根拠は見つかっていない。カスタム ARM stub / TF-A は未確認。

出典: [RPi kernel rpi-6.18.y](https://github.com/raspberrypi/linux/tree/rpi-6.18.y)、[6.18 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt)、[7.2 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt)、[deferred probe change](https://github.com/torvalds/linux/commit/56e3ee721b33)、[Raspberry Pi boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52)。

## init・libc

### init と周辺デバイス

M5 の udev ルールは `ID_PATH` で LCD / input device を識別して symlink と seat tag を設定し、LED に `chgrp` を実行する。LCD の `fb_load.service` は systemd unit。LCD panel は `request_firmware()` で `<compatible>.bin` を読む。M5 モジュールに `MODULE_DEVICE_TABLE` があるため modalias 自動ロードの余地はあるが、udev / mdev / modprobe の設定が必要。

BusyBox mdev は udev 形式のルールをそのまま使えない可能性があり、eudev を併用するか固定デバイスパスを使う必要がある。音声（ALSA / ASoC）、IMU（IIO）、カメラ（media / libcamera）、IR（rc-core）の上位ソフトがどこまで udev / systemd に依存するかは未調査。

### init の比較

| 観点 | systemd 最小化 | BusyBox init + mdev / eudev | 自作 init |
|---|---|---|---|
| M5 udev / unit 整合 | 高い | udev 移植または eudev が必要 | 全て自作 |
| 全機能維持の実装コスト | 低い | 中程度 | 高い |
| 並列起動 | 標準機能 | 自前で `::once` / background を設定 | 自由度は高いが自前 |
| サイズ・診断 | 大きいが journal 等の診断あり | 小さい | 最小だが診断も自作 |
| 起動時間の優位 | 未測定。unit 削減余地あり | 推測上大きい余地 | 推測上最大。ただし作り込み負担が大きい |

### libc / toolchain の調査

| 項目 | glibc | musl | uClibc-ng |
|---|---|---|---|
| Buildroot 2026.08 | 選択可能、systemd の Buildroot 設定で必須 | 選択可能 | 選択可能 |
| 主な制約 | 大きめ | NSS / nss-systemd や DynamicUser 等の差。lazy binding なし、`dlclose` no-op、locale / iconv の範囲が異なる | aarch64 PIE 条件、SSP 既定値など要確認 |
| ライセンス | LGPL-2.1+ | MIT | LGPL-2.1+ |
| CM0 起動比較 | 現行 aarch64 の比較値なし | 同左 | 同左 |

Buildroot 2026.08 の BusyBox 1.38.0、binutils 2.45.1、glibc 2.44、musl 1.2.6、uClibc-ng 1.0.59、systemd 258.7、RAUC 1.15.2、SWUpdate 2026.05.1 と、Yocto Wrynose 6.0 が glibc / musl を選べるとの情報は未確認です。確認先は [Buildroot 2026.08 package tree](https://github.com/buildroot/buildroot/tree/2026.08/package) と [Yocto release documentation](https://docs.yoctoproject.org/releases.html) です。

公開 microbenchmark は Intel Atom N280 / x86 や x86_64 の値で、Cortex-A53 の比較にはできません。Zero 2 W の 3.5 秒事例は full glibc であり、特定 libc が起動を速める証拠ではありません。mimalloc は自社 benchmark の主張と合成 benchmark への注意書きがありますが、CM0 の起動時間値はありません。jemalloc は未調査です。静的 BusyBox + musl は軽量案、systemd と全 M5 udev / unit の流用を優先するなら glibc 案という設計案は推測です。

出典: [Buildroot toolchain options](https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in)、[systemd Buildroot config](https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in)、[musl functional differences](https://wiki.musl-libc.org/functional-differences-from-glibc.html)、[musl comparison](https://www.etalabs.net/compare_libcs.html)、[uClibc-ng](https://uclibc-ng.org/)、[M5 udev / systemd files](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules)。

## ログと観測

### 開発中の観測方法

- UART: M5 の資料では HY2.0-4P と EXT 2.54-14P に G14 / G15 がある。G4 の切替で I2C1 / UART を切り替える。EXT の物理ピンは RX=12、TX=14。3.3 V logic。GPIO14/15 の最終 pinmux と UART 種別は M5 overlay / config 実機確認が必要。`enable_uart=1` が mini-UART の core frequency を固定する場合があり、速度測定に影響し得る。
- USB gadget serial: `g_serial` で `/dev/ttyGS0` を作れる。右 USB-C が OTG slave のときのみ CM0 直結し、host 側の hub / Ethernet / USB-A は同時に使えない。公式 config は `dwc2,dr_mode=host` のため gadget 運用は別設定が必要との推測。
- Ethernet SSH は実装しない。Ethernet は USB 2.0 の SR9900A、10/100 Mb/s。実際の USB ID とドライバは未確認。
- pstore / ramoops は panic / watchdog 等の reset 再起動後のログ候補。完全な電源断では RAM が消える。予約領域と firmware のメモリ配置衝突は未確認。
- 開発用 ext4 ログや専用 raw partition は候補だが、量産 rootfs に含めない。起動測定では無効にする。
- 起動時間測定は UART 設定・ログ量を固定。電断試験は給電経路を分離。障害解析では UART + printk 全開を使う。

出典: [CardputerZero docs](https://docs.m5stack.com/en/CardputerZero)、[USB gadget serial](https://docs.kernel.org/usb/gadget_serial.html)、[ramoops](https://docs.kernel.org/admin-guide/ramoops.html)、[SysRq](https://docs.kernel.org/admin-guide/sysrq.html)。

## SSH・VPN（調査のみ・実装しない）

この節は技術調査の保存のみを目的とし、MSD/Linux に SSH / VPN を実装する計画ではありません。

- Arm Cortex-A53 の Crypto Extension は optional です。BCM2837 に AES / SHA / PMULL 命令があるかはメーカー一次仕様で確認できていません。CPU feature の二次資料では AES / SHA なし、CRC32 ありとされていますが、実機の `/proc/cpuinfo` で確認する必要があります。
- WireGuard は ChaCha20-Poly1305 / Curve25519 / BLAKE2s / HKDF を使い、AES を使わない。ARM NEON 実装がある。CM0 の throughput 公開値なし。OpenVPN は既定 data cipher が AES-GCM を先頭にするため、AES 拡張がない場合は ChaCha20-Poly1305 を先頭に設定する案があるが、実装・性能は未検証。
- Buildroot 2026.08 の調査時点の版: OpenSSH 10.5p1、Dropbear 2026.94、OpenVPN 2.7.6、WireGuard tools 1.0.20260223。OpenSSH は ChaCha20-Poly1305 が既定順の先頭で、ML-KEM-768 + X25519 のハイブリッド鍵交換が既定で先頭。Dropbear は ChaCha20-Poly1305 と ML-KEM / sntrup ハイブリッドを有効、AES-GCM は既定無効との調査。OpenVPN の実効 PQ 鍵交換は OpenSSL 版依存で、接続確認なし。WireGuard 標準プロトコルに PQ hybrid はなく、PSK は任意の追加層。
- Dropbear は小型 SSH 実装で静的 build に向くとの調査。OpenSSH は標準的だが依存が多い。OpenVPN は userspace + OpenSSL、WireGuard は kernel と tools の組み合わせ。全て起動時間・CM0 throughput 未測定。
- 将来実装を再検討する場合、鍵を A/B rootfs に格納せず個体ごとの永続領域に生成する案、初回起動で固有鍵を作る案がある。SD を物理的に取り出せるため暗号化なしの秘密鍵保護は未解決。署名鍵管理・ローテーション・古いクライアントとの PQ 互換も未調査。

出典: [Arm Cortex-A53 TRM](https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=)、[sbc-bench crypto extensions](https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md)、[WireGuard protocol](https://www.wireguard.com/protocol/)、[WireGuard performance](https://www.wireguard.com/performance/)、[OpenSSH 10.0 release](https://www.openssh.org/txt/release-10.0)、[Dropbear defaults](https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h)、[OpenVPN 2.7 manual](https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html)。

## 名称

MSD/Linux は Muromi Software Distribution / Linux の略で、開発拠点のある福岡県を流れる **室見川** にちなんでいます。

## 未確認事項

| 項目 | 次に確認すること |
|---|---|
| BCM2837 / CM0 の tryboot | 実機で `autoboot.txt` / `tryboot_a_b=1`、再起動時復帰を確認 |
| watchdog | `kernel_watchdog_*` と BCM2835 WDT が firmware / CM0 で有効か実機試験 |
| 起動速度 | 公式 image baseline、Buildroot baseline、LCD + keyboard の終点と PID 1 marker を測定 |
| rootfs / SD | microSD FTL の電断に関する一次資料と、複数カードでの実電断試験 |
| Wi-Fi / Ethernet | Wi-Fi chip ID、firmware blob、SR9900A の USB ID / driver |
| HDMI / UART / framebuffer | HDMI connector type、UART pinmux / console、FRAMEBUFFER_CONSOLE の最終 `.config` と LCD fbcon |
| GPT / MBR | BCM2837 での GPT boot、パーティションレイアウト制約 |
| M5 overlay | `cardputerzero-overlay` と `cardputerzero-v3/v5-overlay` の名称不整合、RTC overlay の I2C address |
| image-rota / Zephyr | zero2w / pi3 での image-rota 挙動、Canonical Zephyr fork の内容 |
| Buildroot packages | 最終構成で `make legal-info` を生成し、各配布物のバージョン・ライセンス・source archive を確認 |
| M5 hardware revision | v3 / v5 overlay と製品回路の整合、GL852G reset と keyboard shared GPIO |
| SSH / VPN | 実装しない方針。将来方針が変わる場合に限り暗号性能・鍵管理を再調査 |
| SD の配置・性能 | 現行／1 MiB／4 MiB の image layout、FAT data-area absolute offset、target card の sysfs erase/AU 値と実性能を実機で確認 |
| `/data` の ext4 | `data=journal` から `data=ordered` へ移す場合の `fsync`/rename、barrier、`commit=` と電源断の整合性を確認 |
| discard / fstrim | target card の discard capability と処理結果を実機で確認 |
| update trust chain | 署名検証、鍵ローテーション、dm-verity root digest の保管場所を設計し、全カード交換の脅威境界を確認 |
| kernel / userspace hardening | SSP、FORTIFY、RELRO、PIE、mount options、sysctl の Buildroot 実効値と機能影響を確認 |
| watchdog / tryboot | BCM2837 での one-shot tryboot、`kernel_watchdog_timeout`、S01msd-watchdog の実 reset 動作を実機で確認 |
| hardware functions | IR、camera、IP2315 charger、SR9900A、各 M5 driver の probe と実機動作を確認 |

## 出典一覧

本書の各節に主要な根拠を記載しました。以下は本文で引用した主要な一次資料・技術資料です。版・取得日時に関する詳細は各節を参照してください。

### 製品・M5 ドライバ

- [CardputerZero 製品資料](https://docs.m5stack.com/en/CardputerZero)
- [CardputerZero 回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)
- [CardputerZero pi-gen](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)
- [M5 Linux dtoverlays](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
- [M5 powerfail_suo.c](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c)
- [CardputerZero boot benchmark](https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md)

### Raspberry Pi・Linux・Buildroot

- [Raspberry Pi config.txt boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc)
- [Raspberry Pi autoboot.txt docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc)
- [Raspberry Pi EEPROM bootflow docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)
- [Raspberry Pi boot-time white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf)
- [Raspberry Pi resilient filesystem white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf)
- [Buildroot 2026.08 commit](https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1)
- [Raspberry Pi kernel rpi-6.18.y](https://github.com/raspberrypi/linux/tree/rpi-6.18.y)
- [SquashFS kernel docs](https://docs.kernel.org/filesystems/squashfs.html)
- [EROFS FAQ](https://erofs.docs.kernel.org/en/latest/faq.html)
- [EROFS kernel docs](https://docs.kernel.org/filesystems/erofs.html)
- [overlayfs kernel docs](https://docs.kernel.org/filesystems/overlayfs.html)
- [ext4 kernel docs](https://docs.kernel.org/admin-guide/ext4.html)
- [Raspberry Pi rpi-image-gen](https://github.com/raspberrypi/rpi-image-gen)

### 計測・userland・更新

- [Kernel parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [systemd-analyze](https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)
- [strace](https://man7.org/linux/man-pages/man1/strace.1.html)
- [fanotify](https://man7.org/linux/man-pages/man7/fanotify.7.html)
- [blktrace](https://man7.org/linux/man-pages/man8/blktrace.8.html)
- [BusyBox FAQ](https://busybox.net/FAQ.html)
- [RAUC](https://rauc.io/)
- [SWUpdate](https://sbabic.github.io/swupdate/)
- [Mender docs](https://docs.mender.io/)
- [Rugix device support](https://rugix.org/docs/bakery/devices/)

### 暗号

- [Arm Cortex-A53 technical reference](https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=)
- [WireGuard protocol](https://www.wireguard.com/protocol/)
- [OpenSSH 10.0 release notes](https://www.openssh.org/txt/release-10.0)
- [OpenVPN 2.7 manual](https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html)
