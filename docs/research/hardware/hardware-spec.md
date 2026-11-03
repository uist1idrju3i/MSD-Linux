# ハードウェア仕様

[RESEARCH](../../../RESEARCH.md) の機能対応表です。2026-11-02の資料再照合、全U1〜U37の部品台帳、電源・接続と実装との差異は [部品と回路接続の監査](hardware-wiring-audit.md) を参照してください。公式OSとMSD/Linuxの差異は [BSP比較](official-software.md)、生成DTBO・最終設定・moduleの検査は [生成物の確認記録](../../experiments/2026-11-02-hardware-artifact-audit.md) に分けます。実機動作は未確認です。

## ハードウェア機能の対応表

「ビルド済み」は設定・パッケージにドライバーや overlay が含まれることを指し、実機で機能したことを意味しません。遅延ロード欄は機能依存からの設計判断であり、起動時間や動作は未測定です。【推測】[Buildroot の M5 モジュール一覧](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)／[ボード設定](../../../board/cardputerzero/config.txt)

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
| IR | upstream `IR_GPIO_CIR` / `IR_PWM_TX`。【一次】 | 現行 config に IR overlay なし。【一次】 | `MEDIA_CEC_RC` / `RC_CORE` と既存の `media/rc` module は維持する。S2 では変更しない。【一次】 | IR 使用時まで遅延可能。【推測】 | ピン配置、受信・送信、必要な media/RC 設定。【未確認】 |
| カメラ | upstream `VIDEO_BCM2835_UNICAM` と `VIDEO_IMX219`。legacy Unicam は無効。【一次】 | CM0は4 lane対応でD0〜D3が配線されるが、固定DTSと既定IMX219 overlayは2 lane設定。C154 V0.6.1 では CAM_3V3 LDO の EN は VSYS_5V に pull-up、CAM_GPIO は CM0 pin 44 に接続。CM0 DTS は CAM_GPIO を GPIO40 に割り当て、既定 `imx219` overlay は cam1 を使う。GPIO16 は v5 で PY32 reset 用であり、camera GPIO overlay は適用しない。【一次】 Lite 版の probe failure は想定内だが、実際の kernel message は未確認。【未確認】 | raw V4L2 module と `libv4l-utils` をビルド対象にした。DT checker は config の overlay を順に適用し、IMX219 が指定された場合だけ sensor / CSI1 を assert する。【一次】 | 過去の [S2比較](../../experiments/2026-10-19-s02-camera.md) と現行の [A/Bログ確認](../../experiments/2026-11-02-hardware-artifact-audit.md) はQEMUのみ。実機起動や撮像の証拠にはしない。【実測・QEMU】【未確認】 | `dmesg` の sensor ID、`media-ctl -p` topology、2-lane raw capture、Lite の実際の probe-failure message。【未確認】 |
| Wi-Fi | `BRCMFMAC` / SDIO。【一次】 | Raspberry Pi firmware とボード config。【一次】 | kernel module と firmware を選択。【一次】 | 接続時まで遅延可能。【推測】 | 搭載無線チップ、firmware 適合、起動 daemon、接続。【未確認】 |
| Bluetooth | `BT_HCIUART` / BCM。【一次】 | firmware と UART 設定。【一次】 | kernel module 対象。BlueZ の選択は確認できない。【一次】【未確認】 | 使用時まで遅延可能。【推測】 | 対象モジュール、UART 配線、BlueZ、pairing。【未確認】 |
| USB hub | Linux USB hub core。【一次】 | GL852G は基板上の USB 2.0 hub。【一次】 | 汎用 USB core。専用 M5 module なし。【一次】 | USB 機器の列挙に必要で、個別遅延は対象外。【推測】 | host/device 切替、各ポートの列挙・給電。【未確認】 |
| SR9900A Ethernet | upstream `USB_NET_SR9700` の ID 対応は SR9900A と同一ではない。【一次】【未確認】 | 専用 overlay なし。 | SR9700 module の存在だけでは SR9900A 対応を示さない。【一次】 | 対応が確認できた後は USB net module を遅延ロード可能。【推測】 | USB VID:PID とドライバーの対応、通信。【未確認】 |
| HDMI | `DRM_VC4`。【一次】 | 現行 board config に HDMI 用 overlay の選択なし。【一次】 | kernel module を選択。【一次】 | HDMI を使うまで遅延可能。【推測】 | connector、モード、表示・音声、実機出力。【未確認】。詳細は[HDMI 外部ディスプレイ出力の調査](hdmi-output.md)。 |
| EXT / Grove | GPIO、I²C、SPI と M5IOE1。【一次】 | v5 overlay に拡張端子・rail 用の設定。【一次】 | 関連 driver と overlay を含む。【一次】 | 使用する bus / rail に応じて可能。【推測】 | ピン mux、電圧、既定 UART/I²C、周辺互換性。【未確認】 |
| LED／backlight | M5IOE1 GPIO/PWM と backlight 系統。【一次】 | v5 overlay。【一次】 | M5IOE1 と overlay 対象。【一次】 | 表示に必要な backlight は LCD 初期化時に必要。【推測】 | LED 数、極性、輝度制御、電源異常時の動作。【未確認】 |
| buzzer | 専用 driver / Kconfig を確認できない。【未確認】 | 専用 overlay を確認できない。【未確認】 | 専用機能のビルドを確認できない。【未確認】 | 専用機能なし。 | ブザー搭載有無と制御経路。音声 codec／speaker と同一視しない。【未確認】 |

### 目標との差分

- S2 は Unicam + IMX219 による raw V4L2 capture path を有効にし、`camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効化します。`libcamera`、VCHIQ/MMAL、`bcm2835-isp` は対象外です。Lite 版ではセンサー不在による probe failure は想定内ですが、実際の kernel message は未確認です。【一次】【未確認】[kernel fragment](../../../board/cardputerzero/linux.fragment)／[board config](../../../board/cardputerzero/config.txt)
- C154 V0.6.1 では CAM_3V3 LDO の EN は VSYS_5V に pull-up され、CM0 pin 44 の CAM_GPIO は CM0 DTS で GPIO40 に対応します。既定の `imx219` overlay は cam1 を使い、v5 の GPIO16-high camera overlay は適用しません。追加の GPIO hog は不要です。【一次】[C154 V0.6.1 schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)／[CM0 DTS](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts)／[M5 Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/37b42d9451495b5597dd7e50cab502da8028f9c2/modules/CardputerZero/Makefile)
- QEMU では IMX219 と Unicam module のロードだけを確認します。実機で確認する項目は sensor ID、media topology、2-lane raw capture、Lite の probe-failure message です。【未確認】
- IR は既存の `media/rc` modules を維持しますが、S2 では IR overlay や実機の送受信を検証しないため、対応済みとは扱いません。【一次】【未確認】[kernel fragment](../../../board/cardputerzero/linux.fragment)
- 回路図に IP2315 の充電経路がありますが、Buildroot の選択モジュールに charger driver がなく、充電状態の Linux 表示や制御は未確認です。【一次】【未確認】[M5 モジュール一覧](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)
- 上流のGPIO6電源異常処理はSysRq `u`を呼び、SysRq `s` と `o` はコメントアウトされています。MSD/Linuxの [local patch](../../../package/m5stack-cardputerzero/0001-powerfail-sync-and-notify.patch) はfilesystemのsyncとuserspace通知を加えますが、通常shutdownや実機の保持時間を保証しません。【一次】[M5 powerfail driver](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/37b42d9451495b5597dd7e50cab502da8028f9c2/modules/CardputerZero/powerfail_suo.c)

### 出典

- 【一次】[M5 CardputerZero](https://docs.m5stack.com/en/CardputerZero)、[回路図 V0.6.1](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)。
- 【一次】[M5 Linux drivers and overlays](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/37b42d9451495b5597dd7e50cab502da8028f9c2/modules/CardputerZero)、[Buildroot module list](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)。
- 【一次】[board config](../../../board/cardputerzero/config.txt)、[Linux fragment](../../../board/cardputerzero/linux.fragment)、[Buildroot defconfig](../../../configs/msd_cardputerzero_defconfig)。

## 部品・接続情報の本文

IC、電源rail、GPIO、I2C経路、reset・enable、Standard/Lite差は [部品と回路接続の監査](hardware-wiring-audit.md) と [U1〜U37台帳](hardware-components.csv) を正本とします。機能表への仕様の重複転記は避けます。HDMIコネクタの型、外部CAPの電源投入・取り外し、USBの各ポートは、実機の形状・給電・列挙を別々に確認します。機能の実装と物理コネクタの存在も区別します。

PYG3はTCA8418とGL852Gの共有resetです。M5IOE1のGPIO resetコードとTCAのproperty消費を調べた結果、公開LinuxソースだけではMCU側との責務を確定できませんでした。調べた版と採否は [resetの未解決事項](official-software.md#resetの未解決事項) に記録しています。
