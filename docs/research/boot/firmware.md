# Raspberry Pi ファームウェア仕様の調査（2026-11）

[調査の索引](../../../RESEARCH.md) / [構築手順](../../BUILD.md)

以下は公開資料と過去の検証の記録です。数値の測定条件と未確認事項を保ち、現在の配備設定や実機での検証とは区別します。

RPi ファームウェアの起動フロー・ファイル構成・tryboot/autoboot・OTP/secure boot・更新経路を一次資料（raspberrypi/documentation・firmware リポジトリ）で整理します。CM0 は BCM2710（BCM2837 系）なので**レガシーブート**が対象で、Pi4/5 の EEPROM ブートローダは参考情報です。

2026-11-02 UTC に公式文書のコミット `daf1ca791713d5f1346556122a2b6942bcc7b1d7` と再照合しました。以前の誤記は末尾の訂正表に残しています。設定・ファイルの照合と、実機での起動確認は別です。QEMU は GPU ファームウェアを実行しないため、この設定で CM0 が起動するかは実機で確認する必要があります。

## 1. 起動フロー

### CM0 / BCM2837 系（レガシーブート）

1. OTP で有効なブートモードを決定（GPIO boot mode が有効なら GPIO 状態でさらに絞る。GPIO boot mode は既定で無効）
2. bootcode.bin を順に探索: primary SD（GPIO48-53、失敗まで約 5 秒）→ secondary SD → NAND → SPI → USB（host/device 判定は OTGID ピン。device モードは製造時既定で有効、host モードは `program_usb_boot_mode=1` で OTP 書換）
3. bootcode.bin を 128K L2 キャッシュで実行 → SDRAM 初期化 → `start.elf`（GPU ファームウェア）を読み込み
4. start.elf が `config.txt`（tryboot フラグ時は `tryboot.txt`）・DTB・カーネルを読み ARM を起動

**重要**: `bootcode.bin` / `start.elf` などのファームウェアファイルは microSD の boot パーティション（FAT）から読まれる。SPI EEPROM ブートローダは Pi4（BCM2711）以降のみで、CM0 にはない。

### Pi4 / Pi5（EEPROM ブートローダ、参考）

ROM → `recovery.bin` 経路（OTP/nRPIBOOT、SD、USB device）→ SPI EEPROM 内の second stage を実行 → `BOOT_ORDER`（32bit 整数、下位 nibble から順にブートモードを試行）に従って起動ファイルを読み込む。Pi4 は start4 系を使いますが、Pi5 の GPU ファームウェアは EEPROM 内で完結します。`recovery.bin` は EEPROM 再書き込み用の最小 second stage。

### 主な EEPROM 設定（Pi4/5 のみ）

| キー | 内容 |
|---|---|
| `BOOT_ORDER` | ブートモード列を nibble 単位で右から順に試行（最大 8 桁） |
| `BOOT_UART` / `UART_BAUD` | ブートローダのデバッグ出力を primary UART に出す / ボーレート変更 |
| `POWER_OFF_ON_HALT` / `WAKE_ON_GPIO` | PM_RSTS を見て HALT 時の挙動を決める |
| `rpi-eeprom-update` | `default`（工場出荷・安定）と `latest`（最新）のリリーストレインで EEPROM を更新 |

## 2. ブートパーティション上のファイル

| ファイル | 役割 |
|---|---|
| `bootcode.bin` | BCM2837 系の first-stage bootloader（SD から読まれる） |
| `start.elf`（Pi4 は `start4.elf`） | GPU ファームウェア。周辺機器の初期化、DTB/config.txt の解釈、ARM 起動。Pi5 は EEPROM 内完結 |
| `fixup*.dat` | start.elf 用のリロケーション/補正データ |
| `*.dtb` | デバイスツリー。CM0 は `bcm2710-rpi-cm0.dtb`（firmware に同梱） |
| `overlays/` | DT overlay（`dtoverlay=` で適用） |
| `config.txt` / `tryboot.txt` / `autoboot.txt` / `cmdline.txt` | 起動設定（後述） |
| `kernel*.img` | ARM 側カーネルイメージ |
| `boot.img` / `tryboot.img` | ブートファイル用の ramdisk イメージ（`boot_ramdisk`）。署名なしの用途もある |

## 3. tryboot / autoboot.txt

- `reboot '0 tryboot'` で one-shot フラグを立てると、次の起動で `tryboot.txt` が `config.txt` の代わりに読まれる。フラグはファームウェア起動前にクリアされるため、クラッシュ・リセットで元の `config.txt` に戻る（= MSD の A/B ロールバックの根幹）
- **全モデルで tryboot が使える**。例外は Pi 4B rev 1.0/1.1 のみで、EEPROM 書き込み禁止時は使えない（電源リセットで tryboot 状態が消えるため EEPROM に退避する設計のため）
- `autoboot.txt` は tryboot と組み合わせてパーティション選択を変数（`boot_partition`）で切り替える機構。`tryboot_a_b=1` で config.txt に戻す制御も可能
- `reboot 'N'` の N はパーティション番号で、`autoboot.txt` の条件評価と組み合わせて alternate パーティションを選ぶ
- `boot_ramdisk` を使う構成では、tryboot 時に `boot.img` の代わりに `tryboot.img` が読まれる。secure boot 専用ではない

## 4. OTP / secure boot

- OTP ビット: GPIO boot mode 設定、USB host boot 許可などの製造時フラグ
- 公式 OTP 表は 47-54 を secure boot の RSA 公開鍵の SHA256 とし、ROM RSA key 0 を無効化する bit 15 は BCM2711 の項目です。この記述を CM0 の設定手順へ流用しません。OTP 書換は不可逆なので、この調査のためには実行しません。
- CM0 の公式な署名付きブート経路は本調査では確認していません。Pi4/5 向けの secure boot 機構を、CM0 が備える保護として数えません。
- `msd-update` の Ed25519 検証は、信頼できる OS と公開鍵が動いている状態で、更新バンドルの署名を検査するものです。microSD を交換・直接改変できる相手は boot ファイル、rootfs、公開鍵も置き換えられるため、ハードウェアに固定された信頼の起点や secure boot の代わりにはなりません。

## 5. ファームウェア更新経路

- `raspberrypi/firmware` リポジトリの `boot/` が配布本体（`bcm2710-rpi-cm0.dtb`・`start.elf` 系・`fixup*.dat`・`overlays/` を含む）。MSD はここから DTB を拾ってイメージに載せている
- Pi4/5 向けは `rpi-eeprom` パッケージ経由で `pieeprom-*.bin` を SPI に書き込む経路（`rpi-eeprom-update`、`default`/`latest` トレイン）
- MSD のカーネルは rpi-6.18.y pin です。ファームウェアは Buildroot の `rpi-firmware` パッケージが固定するコミットを使います。ボードの [config.txt](../../../board/cardputerzero/config.txt) を Buildroot がコピーし、[post-image.sh](../../../board/cardputerzero/post-image.sh) が対応するファイルと boot イメージへ収録します。

## 6. ファームウェアファイルの全バリアント

`raspberrypi/firmware` `boot/` にある start/fixup のバリアントを整理します。通常は `start_x` / `start_debug`、または対応する `start_file` / `fixup_file` で選びます。ただし cut-down 版は例外で、公式文書はファイル名で直接選ぶと起動に失敗すると説明しています。MSD は `gpu_mem=16` で `start_cd.elf` と `fixup_cd.dat` を自動選択します。以前の `start_file=start_cd.elf` / `fixup_file=fixup_cd.dat` は削除しました。

### BCM2837 系（CM0 / Zero 2 W / Pi3）

| ファイル | 内容 | 用途 |
|---|---|---|
| `start.elf` | フル機能の VideoCore ファームウェア | カメラ（MMAL/V4L2 旧来）・コーデック（MPEG-2/VC-1 はライセンスキーで有効化）・フル HDMI |
| `start_x.elf` | 「extra」拡張版 | ファームウェア側のカメラ機能。起動時間・サイズ差は本リポジトリでは比較していない |
| `start_cd.elf` | cut-down 版 | **MSD が選択**。`gpu_mem=16` が選択条件。コーデック・3D・デバッグログを省き、初期 framebuffer は最大 1080p / 16bpp。KMS での後段の設定は別。実機の起動時間差は未測定 |
| `start_db.elf` | debug 版 | assert/ログ付きのデバッグビルド。製品では使わない |
| `fixup.dat` / `fixup_x.dat` / `fixup_cd.dat` / `fixup_db.dat` | 各 start バリアント用のリロケーション/補正データ | start と必ず対応させる |

### BCM2711 系（Pi4 / CM4）

`start4.elf` / `start4x.elf` / `start4cd.elf` / `start4db.elf` + 対応する `fixup4*.dat`。BCM2712（Pi5/CM5）のファームウェアはブートローダ EEPROM 内で完結し、start4 系を使うという以前の説明は誤りです。

### その他の boot/ ファイル

| ファイル | 内容 |
|---|---|
| `bootcode.bin` | BCM2837 系の first-stage。バリアントなし |
| `kernel*.img` | firmware リポジトリ同梱の公式カーネルバイナリ: `kernel.img`（armv6/32bit）、`kernel7.img`（armv7/32bit）、`kernel7l.img`（LPAE/32bit）、`kernel8.img`（arm64）、`kernel8_rt.img`（arm64 PREEMPT_RT ビルド）、`kernel_2712.img`（BCM2712 16K ページ）。MSD は自前ビルドの `kernel8.img` を使うため不採用（`kernel8_rt.img` は参考情報: PREEMPT_RT 公式ビルドが存在する） |
| `LICENCE.broadcom` | ソース非公開のファームウェアバイナリの再配布条件。Buildroot の分類は BSD-3-Clause。ソース公開の有無と再配布許諾を混同しない |

### セルフビルドの余地

- **bootcode.bin / start*.elf はセルフビルド不可**: Broadcom VideoCore 向けの閉鎖バイナリで、ソースは公開されていません（`LICENCE.broadcom` 下のバイナリ再配布のみ）。
- **オープンな代替**: `hermanhermitage/rpi-open-firmware` などの候補について、現在の保守状況、CM0 の起動、必要な VideoCore サービスは未確認です。U-Boot/ATF を ARM 側へ追加しただけで、手前の起動コードや GPU ファームウェアが不要になるとは扱いません。以前の「start.elf なしの起動はできない」という断定も、代替実装を検証した結果ではありません。
- **調整幅**: できるのは ①バリアント選択（MSD は最小の `start_cd.elf`）②バージョン固定（`raspberrypi/firmware` のコミット pin）③config.txt/DTB/overlay 側の設定、です。

## 7. 設定可能項目（config.txt・autoboot.txt・OTP）

`config_txt` ドキュメント（what_is_config_txt / boot / common / conditional / gpio / memory / video / audio / camera / overclocking / autoboot）から、CM0 で有効な項目を整理します。`boot/` のファイルバリアント選択と重複する項目は省略します。

### ブート・カーネル系（boot.adoc）

| 項目 | 意味 | CM0 での位置づけ |
|---|---|---|
| `kernel` | カーネルファイル名 | 使用中（`kernel8.img`） |
| `arm_64bit` | 64bit 起動 | 使用中（`1`） |
| `armstub` | ARM stub ローダ指定 | 未使用（既定で十分） |
| `cmdline` | cmdline ファイル名 | 使用中（boot_partition 条件で `cmdline_rootfs_a/b.txt`） |
| `initramfs` / `auto_initramfs` / `ramfsfile` / `ramfsaddr` | initramfs の配置と自動ロード | 未使用（squashfs 直接起動） |
| `os_prefix` | OS ファイルの prefix ディレクトリ | 未使用（A/B は `boot_partition` で分岐） |
| `overlay_prefix` | overlay ファイルの prefix | 未使用 |
| `boot_delay` | ブート遅延（秒） | 使用中（`0`） |
| `disable_splash` | 起動スプラッシュを抑止 | 使用中（`1`） |
| `enable_uart` | シリアルコンソールを有効化 | 使用中（`1`） |
| `force_eeprom_read` | `0` で ID_SD / ID_SC の I²C HAT EEPROM 読込を抑止 | Pi4 の SPI ブート EEPROM とは別。ボードへの適用は未検証 |
| `otg_mode` | USB OTG モード制御 | 未使用 |
| `boot_ramdisk` / `boot_load_flags` | ramdisk 形式 boot.img 制御 | unsigned boot.img も公式用途に含む。secure boot 専用ではない。CM0 では未検証 |
| `kernel_watchdog_timeout` / `kernel_watchdog_partition` | ブートローダ内 watchdog | 検討価値あり（CM0 での対応は未確認） |
| `os_check` | OS 起動チェック | 未使用 |
| `bootloader_update` | EEPROM 更新許可（Pi4 系） | CM0 非対象 |
| `eeprom_write_protect` | EEPROM 書き込み禁止（Pi4 系） | CM0 非対象 |
| `program_pubkey` `revoke_devkey` `program_rpiboot_gpio` `program_jtag_lock` | secure boot 関連 | BCM2711/2712 のみ・CM0 非対象 |
| `set_reboot_arg1` / `set_reboot_order` | reboot 後の boot_order/arg1 渡し（Pi5） | CM0 非対象 |
| `uart_2ndstage` | second stage と start.elf の UART デバッグログ | 未使用。Linux の serial console 用 `enable_uart` とは役割が異なる |
| `sha256` | 読み込んだファイルの SHA256 をログへ出力 | 未使用。署名・期待値との一致検査ではない。起動に数秒以上の負担が加わり得る |
| `erase_eeprom` | EEPROM 消去（Pi4 系） | CM0 非対象 |
| `disable_poe_fan` | PoE ファン制御 | CM0 非対象 |
| `pciex4_reset` | PCIe リセット（Pi5） | CM0 非対象 |
| `enable_rp1_uart` | RP1 UART（Pi5） | CM0 非対象 |

### 汎用（common.adoc）

| 項目 | 意味 | CM0 での位置づけ |
|---|---|---|
| `dtoverlay` | DT overlay 適用 | 使用中（cardputerzero-v5・bq27220_v5・bmi270_bmm150・imx219） |
| `dtparam` | DT パラメータ | 使用中（`i2c_arm`/`i2s`/`spi` = on） |
| `camera_auto_detect` / `display_auto_detect` | カメラ/ディスプレイの自動検出 | 使用中（camera_auto_detect=0） |
| `arm_boost` | ブースト許可（Pi4 系は DVFS ブースト） | 使用中（`1`）。CM0 での実効はファームウェア依存 |
| `power_force_3v3_pwm` | 3.3V 供給強制（Pi4 系） | CM0 非対象 |
| `hdmi_enable_4kp60` | 4K60 有効化（Pi4 系） | CM0 非対象 |

### 条件フィルタ（conditional.adoc）

| 項目 | 意味 | CM0 での位置づけ |
|---|---|---|
| `[all]` | 全モデル | 使用中 |
| `[pi0]` `[pi0w]` `[pi02]` `[pi02w]` `[pi3]` `[pi4]` `[pi5]` `[cm3]` `[cm4]` `[cm5]` 等 | モデル条件 | CM0 は `[cm0]` が使えるか要確認（公開表に `cm0` の項目は明示されていない【未確認】） |
| `[boot_partition=N]` | ブートパーティション条件 | 使用中（`2`/`3` で A/B 切替） |
| `[boot_count=N]` | 起動回数条件 | autoboot 制御の参考 |
| `[partition=N]` | パーティション条件 | 同上 |
| `[boot_arg1]` `[bootvar0]` `[cust_otpN]` | 引数・カスタム OTP 条件 | 参考 |
| `include` | 別設定ファイルの取り込み | 参考 |

### GPIO・メモリ・映像・音声・カメラ・オーバークロック

| ファイル | 主な項目 | CM0 での位置づけ |
|---|---|---|
| gpio.adoc | `gpio=`（ピン機能設定）、`enable_jtag_gpio` | `gpio=` は pin 調整に有用。JTAG は開発用途 |
| memory.adoc | `total_mem`（合計メモリサイズ制限）、`gpu_mem`（GPU メモリ） | `gpu_mem=16` は cut-down (`start_cd`) の選択条件。`total_mem` はテスト用 |
| video.adoc | HDMI/コンポジット/LCD 系（`hdmi_*`、`sdtv_*`、`ignore_lcd`、`disable_fw_kms_setup`、`enable_tvout` 等） | CardputerZero は SPI LCD で HDMI は使わないが、`ignore_lcd` などの調整余地はある。多くは Pi4/5 向け |
| audio.adoc | `audio_pwm_mode`、`disable_audio_dither`、`pwm_sample_bits` | PWM 音声の調整。CardputerZero の I2S 経路とは別レイヤ |
| camera.adoc | `disable_camera_led`、`awb_auto_is_greyworld` 等 | imx219 を使う場合の調整余地 |
| overclocking.adoc | `arm_freq`、`core_freq`、`gpu_freq`、`over_voltage`、`sdram_freq`、`force_turbo`、`temp_limit` | `sdram_freq` は周波数でリフレッシュ周期ではない。OC は保証範囲外のため本機では非推奨、記録のみ |

### autoboot.txt（autoboot.adoc）

| 項目 | 意味 |
|---|---|
| `boot_partition` | 起動パーティション番号の決定（条件付き） |
| `tryboot_a_b` | A/B パーティション構成時に `config.txt` 相当を読む制御（`boot.img` 内では暗黙に `1`） |

## 8. MSD との関係まとめ

1. **ブートフローは bootcode.bin → start.elf → config.txt/tryboot.txt**: tryboot が全モデル対応で、MSD の A/B（`reboot '0 tryboot'` + autoboot.txt のパーティション分岐）と直結する公式機構。
2. **起動の信頼境界**: Pi4/5 の SPI ブート EEPROM・secure boot を CM0 の保護として数えない。ユーザーランドの更新署名は microSD を交換できる相手に対する信頼の起点にはならない。
3. **リフレッシュや SDRAM タイミングは start.elf 内部**: [メモリ信頼性の調査](../tuning/memory-reliability-2026-11.md) の結論と一致（ユーザーランドから変更不可）。
4. **bootcode.bin 探索で 5 秒タイムアウト**: primary SD に bootcode.bin があれば即座に進むため、CardputerZero の起動時間には影響しないが、SD 不在時のフォールバック時間として記録。
5. **ファームウェアファイルは raspberrypi/firmware 由来を pin して配布**: 更新は「固定版の更新確認」ワークフローと同じく変更履歴確認の対象。

## 出典

設定・役割の再確認に使った固定コミットの一次資料は次の2件です。

- [boot.adoc](https://github.com/raspberrypi/documentation/blob/daf1ca791713d5f1346556122a2b6942bcc7b1d7/documentation/asciidoc/computers/config_txt/boot.adoc): cut-down 選択、Pi5、HAT EEPROM、unsigned boot.img、hash 出力、UART ログ。
- [otp-bits.adoc](https://github.com/raspberrypi/documentation/blob/daf1ca791713d5f1346556122a2b6942bcc7b1d7/documentation/asciidoc/computers/raspberry-pi/otp-bits.adoc): OTP 47-54、BCM2711 の RSA key 0 無効化。

以前の記載からの主な訂正は次のとおりです。これは仕様照合と設定の修正であり、実機での成功記録ではありません。

| 以前の記載 | 訂正理由 |
|---|---|
| cut-down を `start_file` / `fixup_file` で直接選択 | 公式仕様の選択条件は `gpu_mem=16` |
| Pi5 も start4 系、`force_eeprom_read` は Pi4 専用 | EEPROM 内完結の GPU ファームウェアと、別用途の HAT EEPROM の混同 |
| `sha256` は検証、`boot_ramdisk` は secure boot 専用、UART 設定は代替可能 | hash の記録と検証、署名ありとなし、GPU と Linux のログを混同 |
| Ed25519 が信頼の起点、cut-down は高速、start.elf の代替は不可能 | 物理改変の限界と実機未測定・代替未検証を反映して限定 |

- bootflow-legacy（BCM2837 系） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc 【一次】
- bootflow-eeprom（Pi4/5） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc 【一次】
- eeprom-bootloader（BOOT_ORDER・UART 等） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc 【一次】
- otp-bits https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/otp-bits.adoc 【一次】
- config_txt/boot.adoc（tryboot/boot.img/BOOT_ORDER 渡し） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/config_txt/boot.adoc 【一次】
- `raspberrypi/firmware` `boot/` https://github.com/raspberrypi/firmware/tree/master/boot 【一次】
- 既存の起動経路設計は [boot 関連の調査](sequence.md) を参照
