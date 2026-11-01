# Raspberry Pi ファームウェア仕様の調査（2026-11）

RPi ファームウェアの起動フロー・ファイル構成・tryboot/autoboot・OTP/secure boot・更新経路を一次資料（raspberrypi/documentation・firmware リポジトリ）で整理します。CM0 は BCM2710（BCM2837 系）なので**レガシーブート**が対象で、Pi4/5 の EEPROM ブートローダは参考情報です。

## 1. 起動フロー

### CM0 / BCM2837 系（レガシーブート）

1. OTP で有効なブートモードを決定（GPIO boot mode が有効なら GPIO 状態でさらに絞る。GPIO boot mode は既定で無効）
2. bootcode.bin を順に探索: primary SD（GPIO48-53、失敗まで約 5 秒）→ secondary SD → NAND → SPI → USB（host/device 判定は OTGID ピン。device モードは製造時既定で有効、host モードは `program_usb_boot_mode=1` で OTP 書換）
3. bootcode.bin を 128K L2 キャッシュで実行 → SDRAM 初期化 → `start.elf`（GPU ファームウェア）を読み込み
4. start.elf が `config.txt`（tryboot フラグ時は `tryboot.txt`）・DTB・カーネルを読み ARM を起動

**重要**: `bootcode.bin` / `start.elf` などのファームウェアファイルは microSD の boot パーティション（FAT）から読まれる。SPI EEPROM ブートローダは Pi4（BCM2711）以降のみで、CM0 にはない。

### Pi4 / Pi5（EEPROM ブートローダ、参考）

ROM → `recovery.bin` 経路（OTP/nRPIBOOT、SD、USB device）→ SPI EEPROM 内の second stage を実行 → `BOOT_ORDER`（32bit 整数、下位 nibble から順にブートモードを試行）に従って `boot.img` / `start4.elf` 等を読み込む。`recovery.bin` は EEPROM 再書き込み用の最小 second stage。

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
| `start.elf`（Pi4/5 は `start4.elf`） | GPU ファームウェア。SDRAM/周辺機器の初期化、DTB/config.txt の解釈、ARM 起動 |
| `fixup*.dat` | start.elf 用のリロケーション/補正データ |
| `*.dtb` | デバイスツリー。CM0 は `bcm2710-rpi-cm0.dtb`（firmware に同梱） |
| `overlays/` | DT overlay（`dtoverlay=` で適用） |
| `config.txt` / `tryboot.txt` / `autoboot.txt` / `cmdline.txt` | 起動設定（後述） |
| `kernel*.img` | ARM 側カーネルイメージ |
| `boot.img` / `tryboot.img` | secure boot の ramdisk イメージ（`boot_ramdisk`） |

## 3. tryboot / autoboot.txt

- `reboot '0 tryboot'` で one-shot フラグを立てると、次の起動で `tryboot.txt` が `config.txt` の代わりに読まれる。フラグはファームウェア起動前にクリアされるため、クラッシュ・リセットで元の `config.txt` に戻る（= MSD の A/B ロールバックの根幹）
- **全モデルで tryboot が使える**。例外は Pi 4B rev 1.0/1.1 のみで、EEPROM 書き込み禁止時は使えない（電源リセットで tryboot 状態が消えるため EEPROM に退避する設計のため）
- `autoboot.txt` は tryboot と組み合わせてパーティション選択を変数（`boot_partition`）で切り替える機構。`tryboot_a_b=1` で config.txt に戻す制御も可能
- `reboot 'N'` の N はパーティション番号で、`autoboot.txt` の条件評価と組み合わせて alternate パーティションを選ぶ
- secure boot 有効時は `tryboot.img` が読まれる（`tryboot.txt` ではなく img 側）

## 4. OTP / secure boot

- OTP ビット: GPIO boot mode 設定、USB host boot 許可などの製造時フラグ
- secure boot: OTP 47-54 に RSA 公開鍵の SHA256 を焼き、bit 15 で ROM RSA key 0 を無効化して有効化。**BCM2711（Pi4/CM4）・BCM2712（Pi5/CM5）系のみ対応**で、CM0（BCM2710）には secure boot の経路がない
- 結果、CM0 ではブートローダ段階の署名検証ができず、**MSD はユーザーランド側の Ed25519 署名（msd-update）が信頼の起点**になる設計で正当

## 5. ファームウェア更新経路

- `raspberrypi/firmware` リポジトリの `boot/` が配布本体（`bcm2710-rpi-cm0.dtb`・`start.elf` 系・`fixup*.dat`・`overlays/` を含む）。MSD はここから DTB を拾ってイメージに載せている
- Pi4/5 向けは `rpi-eeprom` パッケージ経由で `pieeprom-*.bin` を SPI に書き込む経路（`rpi-eeprom-update`、`default`/`latest` トレイン）
- MSD のカーネルは rpi-6.18.y pin で、`linux.fragment` 側に起動設定はない。ファームウェアファイルの更新は `vendor/` や `board/` 側の参照先（pi-gen と同じく raspberrypi/firmware の pin）に依存

## 6. MSD との関係まとめ

1. **ブートフローは bootcode.bin → start.elf → config.txt/tryboot.txt**: tryboot が全モデル対応で、MSD の A/B（`reboot '0 tryboot'` + autoboot.txt のパーティション分岐）と直結する公式機構。
2. **CM0 に EEPROM・secure boot はない**: Pi4/5 向けの機能と混同しない。信頼の起点はユーザーランドの Ed25519 署名。
3. **リフレッシュや SDRAM タイミングは start.elf 内部**: [メモリ信頼性の調査](memory-reliability-2026-11.md) の結論と一致（ユーザーランドから変更不可）。
4. **bootcode.bin 探索で 5 秒タイムアウト**: primary SD に bootcode.bin があれば即座に進むため、CardputerZero の起動時間には影響しないが、SD 不在時のフォールバック時間として記録。
5. **ファームウェアファイルは raspberrypi/firmware 由来を pin して配布**: 更新は「固定版の更新確認」ワークフローと同じく変更履歴確認の対象。

## 出典

- bootflow-legacy（BCM2837 系） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc 【一次】
- bootflow-eeprom（Pi4/5） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc 【一次】
- eeprom-bootloader（BOOT_ORDER・UART 等） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc 【一次】
- otp-bits https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/otp-bits.adoc 【一次】
- config_txt/boot.adoc（tryboot/boot.img/BOOT_ORDER 渡し） https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/config_txt/boot.adoc 【一次】
- `raspberrypi/firmware` `boot/` https://github.com/raspberrypi/firmware/tree/master/boot 【一次】
- 既存の起動経路設計は [boot 関連の調査](boot-and-kernel.md) を参照
