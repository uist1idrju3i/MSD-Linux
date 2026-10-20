# ハードウェア仕様

scope-and-hardware.md から分割した節です。

## ハードウェア機能の対応表

「ビルド済み」は設定・パッケージにドライバーや overlay が含まれることを指し、実機で機能したことを意味しません。遅延ロード欄は機能依存からの設計判断であり、起動時間や動作は未測定です。【推測】[Buildroot の M5 モジュール一覧](../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)／[ボード設定](../../board/cardputerzero/config.txt)

| 機能 | driver / Kconfig | overlay / firmware | 現在のビルド | 遅延ロード | 未確認点 |
|---|---|---|---|---|---|
| LCD | M5 `st7789v-1.0` 外部モジュール。【一次】 | CardputerZero v5 overlay とパネル firmware。【一次】 | パッケージ対象・overlay 選択あり。【一次】 | コンソール出力に使う場合は早期ロードが必要。【推測】 | 初期化、fbcon 接続、回転・色、実機表示。【未確認】 |
| キーボード | M5 TCA8418 外部モジュール。【一次】 | v5 overlay と keymap。【一次】 | パッケージ対象・overlay 選択あり。【一次】 | 起動後の CLI 入力に使うなら遅延不可。【推測】 | 入力、割込み、リセット共用端子、ロード順。【未確認】 |
| 音声 | M5 ES8389 外部モジュール。【一次】 | 音声 codec overlay。【一次】 | パッケージ対象。【一次】 | 起動必須ではなければ可能。【推測】 | 再生・録音、イヤホン検出、アンプ制御。【未確認】 |
| IMU | M5 BMI270 外部モジュール。【一次】 | BMI270/BMM150 overlay と初期化 firmware。【一次】 | モジュール・firmware 対象。【一次】 | センサーを使うまで遅延可能。【推測】 | probe、IIO 値、割込み、firmware 読込。【未確認】 |
| 磁力計 | M5 BMM150 外部モジュール。【一次】 | BMI270/BMM150 overlay。【一次】 | モジュール対象。【一次】 | センサーを使うまで遅延可能。【推測】 | IIO 登録、BMI270 経由の接続、測定値。【未確認】 |
| RTC | upstream `rtc-ds1307`／`CONFIG_RTC_DRV_DS1307`。【一次】 | v5 overlay が RX8130 を I²C 0x32 に宣言。【一次】 | kernel module と overlay 対象。【一次】 | 起動後の時刻取得まで遅延可能。【推測】 | RTC 登録、バックアップ保持、時刻同期。【未確認】 |
| 燃料計 | M5 BQ27220 外部モジュール。【一次】 | `bq27220_v5` overlay。【一次】 | モジュール・overlay 対象。【一次】 | バッテリー表示が必要になるまで可能。【推測】 | 識別、校正、残量・電圧の精度。【未確認】 |
| IP2315 充電器 | 対応 driver / Kconfig を選択した証拠なし。【未確認】 | 回路図に充電経路の記載。専用 overlay なし。【一次】 | charger module はパッケージ一覧にない。【一次】 | 現状ロード対象なし。 | 充電状態・制御・保護動作。【未確認】 |
| M5IOE1 | M5 `m5ioe1` 外部モジュール。【一次】 | v5 overlay が I²C 0x4f と GPIO/PWM を宣言。【一次】 | パッケージ対象・overlay 選択あり。【一次】 | LCD、電源・拡張制御の依存があるため早期ロード対象を確認する。【推測】 | probe、GPIO 番号対応、PWM、I²C 安定性。【未確認】 |
| 電源スイッチ／GPIO6 電源異常 | M5 `powerfail_suo` 外部モジュール。【一次】 | v5 overlay が GPIO6 と 500 ms debounce を宣言。【一次】 | パッケージ対象・overlay 選択あり。【一次】 | 電源異常への応答が目的なら早期ロードが望ましい。【推測】 | 割込み条件、SysRq 設定、電源保持時間、実際の電断耐性。【未確認】 |
| IR | upstream `IR_GPIO_CIR` / `IR_GPIO_TX`。【一次】 | 現行 config に IR overlay なし。【一次】 | `MEDIA_CEC_RC` / `RC_CORE` と既存の `media/rc` module は維持する。S2 では変更しない。【一次】 | IR 使用時まで遅延可能。【推測】 | ピン配置、受信・送信、必要な media/RC 設定。【未確認】 |
| カメラ | upstream `VIDEO_BCM2835_UNICAM` と `VIDEO_IMX219`。legacy Unicam は無効。【一次】 | CM0 の CSI1 は 2 lane。C154 V0.6.1 では CAM_3V3 LDO の EN は VSYS_5V に pull-up、CAM_GPIO は CM0 pin 44 に接続。CM0 DTS は CAM_GPIO を GPIO40 に割り当て、既定 `imx219` overlay は cam1 を使う。GPIO16 は v5 で PY32 reset 用であり、camera GPIO overlay は適用しない。【一次】 Lite 版の probe failure は想定内だが、実際の kernel message は未確認。【未確認】 | raw V4L2 module と `libv4l-utils` をビルド対象にした。DT checker は config の overlay を順に適用し、IMX219 が指定された場合だけ sensor / CSI1 を assert する。【一次】 | QEMU p5/p6 で三 module の load を確認。統制相対 ready-marker 中央値は +0.0510%（+1.0% 基準内）。QEMU では実機起動や撮像を検証しない。【実測・QEMU】【未確認】 | `dmesg` の sensor ID、`media-ctl -p` topology、2-lane raw capture、Lite の実際の probe-failure message。【未確認】 |
| Wi-Fi | `BRCMFMAC` / SDIO。【一次】 | Raspberry Pi firmware とボード config。【一次】 | kernel module と firmware を選択。【一次】 | 接続時まで遅延可能。【推測】 | 搭載無線チップ、firmware 適合、起動 daemon、接続。【未確認】 |
| Bluetooth | `BT_HCIUART` / BCM。【一次】 | firmware と UART 設定。【一次】 | kernel module 対象。BlueZ の選択は確認できない。【一次】【未確認】 | 使用時まで遅延可能。【推測】 | 対象モジュール、UART 配線、BlueZ、pairing。【未確認】 |
| USB hub | Linux USB hub core。【一次】 | GL852G は基板上の USB 2.0 hub。【一次】 | 汎用 USB core。専用 M5 module なし。【一次】 | USB 機器の列挙に必要で、個別遅延は対象外。【推測】 | host/device 切替、各ポートの列挙・給電。【未確認】 |
| SR9900A Ethernet | upstream `USB_NET_SR9700` の ID 対応は SR9900A と同一ではない。【一次】【未確認】 | 専用 overlay なし。 | SR9700 module の存在だけでは SR9900A 対応を示さない。【一次】 | 対応が確認できた後は USB net module を遅延ロード可能。【推測】 | USB VID:PID とドライバーの対応、通信。【未確認】 |
| HDMI | `DRM_VC4`。【一次】 | 現行 board config に HDMI 用 overlay の選択なし。【一次】 | kernel module を選択。【一次】 | HDMI を使うまで遅延可能。【推測】 | connector、モード、表示・音声、実機出力。【未確認】 |
| EXT / Grove | GPIO、I²C、SPI と M5IOE1。【一次】 | v5 overlay に拡張端子・rail 用の設定。【一次】 | 関連 driver と overlay を含む。【一次】 | 使用する bus / rail に応じて可能。【推測】 | ピン mux、電圧、既定 UART/I²C、周辺互換性。【未確認】 |
| LED／backlight | M5IOE1 GPIO/PWM と backlight 系統。【一次】 | v5 overlay。【一次】 | M5IOE1 と overlay 対象。【一次】 | 表示に必要な backlight は LCD 初期化時に必要。【推測】 | LED 数、極性、輝度制御、電源異常時の動作。【未確認】 |
| buzzer | 専用 driver / Kconfig を確認できない。【未確認】 | 専用 overlay を確認できない。【未確認】 | 専用機能のビルドを確認できない。【未確認】 | 専用機能なし。 | ブザー搭載有無と制御経路。音声 codec／speaker と同一視しない。【未確認】 |

### 目標との差分

- S2 は Unicam + IMX219 による raw V4L2 capture path を有効にし、`camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効化します。`libcamera`、VCHIQ/MMAL、`bcm2835-isp` は対象外です。Lite 版ではセンサー不在による probe failure は想定内ですが、実際の kernel message は未確認です。【一次】【未確認】[kernel fragment](../../board/cardputerzero/linux.fragment)／[board config](../../board/cardputerzero/config.txt)
- C154 V0.6.1 では CAM_3V3 LDO の EN は VSYS_5V に pull-up され、CM0 pin 44 の CAM_GPIO は CM0 DTS で GPIO40 に対応します。既定の `imx219` overlay は cam1 を使い、v5 の GPIO16-high camera overlay は適用しません。追加の GPIO hog は不要です。【一次】[C154 V0.6.1 schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)／[CM0 DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts)／[M5 Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile)
- QEMU では IMX219 と Unicam module のロードだけを確認します。実機で確認する項目は sensor ID、media topology、2-lane raw capture、Lite の probe-failure message です。【未確認】
- IR は既存の `media/rc` modules を維持しますが、S2 では IR overlay や実機の送受信を検証しないため、対応済みとは扱いません。【一次】【未確認】[kernel fragment](../../board/cardputerzero/linux.fragment)
- 回路図に IP2315 の充電経路がありますが、Buildroot の選択モジュールに charger driver がなく、充電状態の Linux 表示や制御は未確認です。【一次】【未確認】[M5 モジュール一覧](../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)
- GPIO6 の電源異常処理は SysRq `u`（読み取り専用再マウント）を呼びます。SysRq `s` と `o` はコメントアウトされており、通常の同期・shutdown を実装しているとは言えません。【一次】[M5 powerfail driver](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115)

### 出典

- 【一次】[M5 CardputerZero](https://docs.m5stack.com/en/CardputerZero)、[回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)。
- 【一次】[M5 Linux drivers and overlays](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero)、[Buildroot module list](../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)。
- 【一次】[board config](../../board/cardputerzero/config.txt)、[Linux fragment](../../board/cardputerzero/linux.fragment)、[Buildroot defconfig](../../configs/msd_cardputerzero_defconfig)。

### 対応表の根拠と短い抜粋

| 対象 | 公開 URL | 原文の短い抜粋 | 確度 |
|---|---|---|---|
| M5 driver / overlay のビルド一覧 | [Buildroot package](https://github.com/uist1idrju3i/MSD-Linux/blob/main/package/m5stack-cardputerzero/m5stack-cardputerzero.mk) | `modules/st7789v-1.0` / `modules/tca8418-1.0` / `modules/es8389-1.0` / `modules/bq27220-1.0` | 【一次】 |
| 現行 v5 overlay 選択 | [board config](https://github.com/uist1idrju3i/MSD-Linux/blob/main/board/cardputerzero/config.txt) | `dtoverlay=cardputerzero-v5-overlay` / `dtoverlay=bq27220_v5` / `dtoverlay=bmi270_bmm150_overlay` | 【一次】 |
| LCD firmware と M5 module | [Buildroot package](https://github.com/uist1idrju3i/MSD-Linux/blob/main/package/m5stack-cardputerzero/m5stack-cardputerzero.mk) | `cardputerzero,st7789v_lcd.bin` | 【一次】 |
| TCA8418 keymap と M5 compatible | [M5 v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts) | `compatible = "m5stack,tca8418c"` | 【一次】 |
| Audio overlay | [M5 v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts) | `compatible = "m5stack,cardputerzero-audio"` | 【一次】 |
| RTC support | [Raspberry Pi Linux RTC driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L1164) | `.compatible = "epson,rx8130"` | 【一次】 |
| IP2315 charge path | [CardputerZero schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf) | “The battery charging has a separate input path. Input priority: USB IN > EXT. IN” | 【一次】 |
| GPIO6 power-fail action | [M5 powerfail driver](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115) | `handle_sysrq('u')` / `// handle_sysrq('s');` | 【一次】 |
| camera/IR kernel support | [kernel fragment](../../board/cardputerzero/linux.fragment)、[camera config](../../board/cardputerzero/config.txt) | `CONFIG_MEDIA_SUPPORT=m`; Unicam / IMX219 を有効化し、既存の `media/rc` は変更しない。`config.txt` では `camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効にする | 【一次】 |
| USB hub / Ethernet chipset | [CardputerZero product page](https://docs.m5stack.com/en/CardputerZero) | “GL852G-OHY60 USB 2.0 Hub / SR9900A USB 2.0 to Ethernet chip” | 【一次】 |
| SR9700 driver identity | [Raspberry Pi Linux driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/sr9700.c) | `USB_DEVICE(0x0fe6, 0x9700)` | 【一次】 |

表中の「遅延ロード」は依存関係からの設計判断で、実機での起動時間や probe 順を測った結果ではありません。【推測】個別の hardware operation、無線の接続、charger telemetry、未掲載の buzzer の存在は実機確認が必要です。【未確認】

## 2. ハードウェア仕様

出典:【一次】公式 docs en/ja（2026-10-18）と回路図 V0.6.1（2026-07-02）。docs には「packaging and software development not yet complete」との注記があります。

### 2.1 搭載チップ・主要部品

【一次（Devin が 2026-10-18 に確認）】M5Stack の製品ページは Work in progress と表示されていました。掲載情報は更新される可能性があります。https://docs.m5stack.com/ja/CardputerZero

| 区分 | 部品 | 接続/備考 | 出典URL |
|---|---|---|---|
| SoC モジュール | **CM0**(RP3A0 / BCM2837、Cortex-A53 ×4、1GHz、aarch64) | DTS 名は bcm2710-rpi-cm0 | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/ja/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| メモリ | LPDDR2 512MB | CM0 内蔵 | https://docs.m5stack.com/en/CardputerZero |
| ストレージ | microSD | 標準版 C154 は 32GB 付属、Lite 版 C155 は付属なし | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/en/products/sku/C154 |
| Wi-Fi/BT | CYW43439（CM0 の**無線搭載版**に搭載。RP-009251-DS は CM0 のデータシート Release 3 で、無線は「オプション」。CM0Lite は eMMC なしで SDIO を持つ版だが、無線の有無はデータシートに明記されていない。M5 の実機がどの版かも未確認） | RPi 配布ファームには 43430/43436s/43439 がすべて含まれる。**実機の chip ID は未確認** | https://docs.m5stack.com/en/CardputerZero<br>RP-009251-DS: https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf |
| LCD | ST7789V3、320×170、SPI | MOSI G10、SCLK G11、DC G25、CS G8、TE G5、RST=M5IOE1 PYG12、BL=PYG10(PWM) | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| キーボード | TCA8418 @0x34 | INT G27、46 キー+LED(SHIFT/FN/SYM) | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| オーディオコーデック | ES8389 @0x10 | I2S G18〜21 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| アンプ | AW8737A | EN G24、1W スピーカー | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| マイク | MEMS マイク | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| ヘッドホン | TRRS | HP_DET G17、PYG6 で CTIA/OMTP を切替 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| IMU | BMI270 @0x68、BMM150 @0x10（docs 記載。ES8389 と同じ値） | Lite 版には IMU・カメラがなく、microSD スロットはあるがカードは付属しない（公式 docs の比較表） | https://docs.m5stack.com/en/CardputerZero<br>https://docs.m5stack.com/en/products/sku/C154 |
| RTC | RX8130CE @0x32 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 燃料計 | BQ27220 @0x55 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 充電 | IP2315 | バッテリ 1750mAh | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 電源系 | TPS2116、SY7088、SY8003 等 | — | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| IO エキスパンダ | M5IOE1 @0x4F | NRST G16 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| USB ハブ | GL852G(4 ポート) | リセットは **PYG3_KB_HUB_RST(TCA8418 キーボードと GL852G で共用)**(公式 docs に明記)。USB1=SR9900A(10/100M Ethernet)、USB2=USB-A、USB3=Type-C 左、USB4=HAT | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| USB モード | Host/Slave 物理スイッチ | Slave 時はハブを切断 | https://docs.m5stack.com/en/CardputerZero |
| 右 Type-C | CM0 直結 | — | https://docs.m5stack.com/en/CardputerZero |
| カメラ | IMX219（Lite 版を除く） | CM0 の CSI1、2 lane。`config.txt` で `camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効にする。C154 V0.6.1 の CAM_3V3 LDO EN は VSYS_5V に pull-up され、CM0 pin 44 の CAM_GPIO は DTS で GPIO40 に対応します。既定の cam1 overlay が使うため追加 hog は不要です。GPIO16 は v5 で PY32 reset 用です。【一次】 Lite 版の probe failure は想定内ですが、実際の kernel message は未確認。 | [M5 CardputerZero](https://docs.m5stack.com/en/CardputerZero)<br>[C154 V0.6.1 schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)<br>[CM0 DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts)<br>[CSI1 2-lane DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm283x-rpi-csi1-2lane.dtsi)<br>[M5 CardputerZero Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile) 【一次】【未確認】 |

| 電源状態検出 | PYG5_PWR_DET | 公式 docs の Power Status に記載（詳細な意味は未確認） | https://docs.m5stack.com/en/CardputerZero |
| IR | TX G12 / RX G13 | — | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| 拡張 | HY2.0-4P、EXT 14pin | Cap はホットスワップ不可 | https://docs.m5stack.com/en/CardputerZero |
| スイッチ検知 | SW_DET = G6 | [`powerfail_suo.c`](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c) が使用 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c |
| 映像出力 | **HDMI**(回路図 P10 J5、19pin、HDMI-001) | コネクタ形状(Type A か D か)は【**未確認**】。DSI/CVBS は未使用 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf<br>(ページ P10 J5 の再照合は今回未実施) |

一次資料の抜粋: [C154 V0.6.1 回路図 p.10](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf) は `CAM_3V3`、U36 (`SSP7615-33DFR`)、R190 (`100K`)、R192 (`NC`) を示し、U36 の EN が VSYS_5V に pull-up された常時有効の構成です。p.5 では CM0 pin 44、p.10 では JP5 pin 17 がそれぞれ `CAM_GPIO` と表示されています。upstream [CM0 DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts) は GPIO40 の line name を `CAM_GPIO` とし、`&cam1_reg` の `gpio = <&gpio 40 GPIO_ACTIVE_HIGH>` を設定します。M5 の [CardputerZero Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile) は GPIO16-high camera overlay を非 V0_5 側でのみ追加する構成です。したがって既定の cam1 overlay は CAM_GPIO に GPIO40 を使い、v5 では追加 hog が不要です。【一次】

### 2.2 ソフト開発上の留意点
- 【一次】PYG3 は TCA8418 キーボードと GL852G ハブの**共用リセット**です。ハブのリセットがキーボードにも波及する可能性があります。【推測】（出典: https://docs.m5stack.com/en/CardputerZero）
- 【未確認】HEAD `7551854` の `modules/tca8418-1.0` が `rest-gpios` を使うか、また `modules` 配下の C ソースに GL852G/USB ハブのリセット処理があるかは未確認です。確認先は [公開ソース](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20) です。
- 【一次】v5 overlay は `rest-gpios = <&m5ioe1 2 1>` を設定します。v3 overlay にも同様の記述があります。ドライバ側の扱いと v3/v5 の差は未確認です。出典: [v3 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90)、[v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100)。
- 【**推測**】 Linux 側からの GL852G の制御方法は、実機で確認する必要があります。

---
