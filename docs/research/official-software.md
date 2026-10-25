# 公式ソフトウェア構成

[RESEARCH.md](../../RESEARCH.md) から分けた節です。

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

出典: [pi-gen commit](https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)、[kernel pin](https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3)、[M5 ドライバ](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)、[Raspberry Pi bootflow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)。
