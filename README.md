# MSD/Linux

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/uist1idrju3i/MSD-Linux)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="documentation/logo/msd-linux-logo-dark.svg">
    <img src="documentation/logo/msd-linux-logo.svg" alt="MSD/Linux のロゴ。濃藍の円の中で室見川の流れが青海波の博多湾へ注ぐ。" width="480">
  </picture>
</p>

MSD/Linux は Muromi Software Distribution / Linux の略で、福岡県の室見川にちなんでいます。M5Stack CardputerZero 向けの Linux OS を開発しています。

## 目的

CardputerZero を、電源を入れたらすぐに使えて、乱暴に扱っても壊れない、ポケットに入る Linux 端末にすることが目的です。標準版と Lite 版をひとつのイメージでサポートし、LCD のテキストコンソールと内蔵キーボードで操作する CLI を提供します。

### 設計の柱

次の 6 つを同時に満たすことを目指します。どれか 1 つのために、ほかを大きく損なう変更は採りません。

| 柱 | 方針 | 主な手段 |
|---|---|---|
| すぐ使える | 電源を入れてからキーボード入力を受け付けるまでの時間を短くします。終点の定義と測定方法は RESEARCH に従い、改善は実測で確かめます。 | firmware とカーネルの設定の最適化、起動に不要なドライバの遅延ロード、軽量な init |
| 電源断で壊れない | 電池切れやケーブルの抜けでいつ電源が落ちても、次の起動で同じ状態に戻れるようにします。 | 読み取り専用の SquashFS rootfs、書き込みを ext4 の `/data` に限定、microSD の消去単位を考慮したパーティション配置 |
| 更新に失敗しても戻れる | 新しいイメージは試験起動し、ヘルスチェックに合格したときだけ確定します。起動できなければ、前のスロットへ自動で戻ります。 | A/B の 2 スロット、Raspberry Pi firmware の `tryboot` と `autoboot.txt`、`msd-update` |
| ハードウェアをすべて使える | 速さや軽さのために機能を削りません。LCD、キーボード、音声、センサー、RTC、電池、IR、カメラ、無線、USB、Ethernet、HDMI、拡張端子を利用できる状態に保ちます。 | 起動に必須のものだけ組み込み、ほかはモジュールとして必要時に読み込む |
| 費用に見合うセキュリティ | 取り外せる microSD があり、ハードウェアによる secure boot がない端末であることを前提に脅威を整理します。安価で効果の大きい対策から順に入れ、起動時間とメモリへの影響を測ってから採用します。 | カーネルと sysctl のハードニング、マウントオプション、更新イメージの署名、無線・USB の攻撃面の縮小 |
| 検証できる | QEMU で確認できることと、実機でしか確認できないことを分けて記録します。確認していないことを確認済みとは書きません。 | CI での Buildroot ビルドと QEMU 起動確認、実機での測定手順 |

デスクトップ環境、公式 LVGL ランチャー、公式 `.deb` アプリとの互換性は目標にしていません。SSH と VPN は調査対象にとどめ、実装しません。

## 開発状況

開発中です。Buildroot の外部ツリーと CardputerZero 用 defconfig を追加しました。CI では Buildroot のフルビルドと、QEMU（`raspi3b`）での A スロット・B スロットの起動確認を実行しています。QEMU では GPU firmware の `tryboot`、LCD、キーボード、M5 の I2C デバイス、実際の電源断を再現できないため、これらは実機での確認が必要です。実機は来月発売予定で、実機での起動は未確認です。

## 予定している構成

| 項目 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08 |
| カーネル | Raspberry Pi `rpi-6.18.y` |
| rootfs | Zstandard 圧縮の読み取り専用 SquashFS。書き込み領域に ext4 の `/data` を使用 |
| A/B 更新 | Raspberry Pi `autoboot.txt` と `tryboot` を使う構成を追加。実機での確認は未実施 |

実機での動作は未確認です。詳細な調査結果、出典、未確認事項は [RESEARCH.md](RESEARCH.md)、作業規約は [AGENTS.md](AGENTS.md) を参照してください。

ビルドと QEMU 起動確認の手順は [documentation/BUILD.md](documentation/BUILD.md)、更新手順と検証範囲は [documentation/UPDATE.md](documentation/UPDATE.md) を参照してください。

## 取得方法

```sh
git clone --recurse-submodules https://github.com/uist1idrju3i/MSD-Linux.git
```

既に clone 済みの場合は次を実行してください。

```sh
git submodule update --init
```

## ライセンス

本リポジトリの対象ファイルは GPL-2.0-or-later です。

```text
SPDX-License-Identifier: GPL-2.0-or-later
```

GPL-2.0 の全文は [LICENSE](LICENSE) にあります。ソースコードやビルド済みイメージを配布するときは、適用されるライセンス条件を確認してください。

### ライセンスに関する注意

| 対象 | ライセンスと配布方針 |
|---|---|
| `vendor/` submodule | 各 submodule 固有のライセンスを維持します。`vendor/yomiyasu` には MIT License と Unicode License V3（`UNICODE-LICENSE.txt`）が含まれています。 |
| Linux kernel / M5 ドライバ | 各ソースのライセンス表記に従います。M5 の GitHub license metadata は NOASSERTION です。`COPYING` は Linux kernel の `GPL-2.0 WITH Linux-syscall-note` に関する案内で、個々のファイルには別のライセンスが適用される場合があります。 |
| `cardputerzero,st7789v_lcd.bin` | **unknown**。vendor のファイルにライセンス表記がなく、README や確認した履歴にも由来・ライセンスの記載がありません。 |
| `bmi270-init-data.fw` | **unknown**。vendor のファイルにライセンス表記がなく、linux-firmware の `WHENCE` にも BMI270 用 firmware の記載を確認できませんでした。別ファイルの BMI260 firmware に記載された BSD-3-Clause は、このファイルの根拠にはなりません。 |
| `tca8418_keypad_m5stack_keymap.map` | **unknown**。vendor のファイルに著作権・ライセンス表記がなく、README や確認した履歴にも記載がありません。 |
| Raspberry Pi GPU firmware | `boot/LICENCE.broadcom` に従います。Buildroot 2026.08 の `rpi-firmware.mk` は `BSD-3-Clause` と記載しますが、実際の同ファイルは Raspberry Pi または認定派生機器での利用を条件とするバイナリ再配布条件です。 |
| Wi-Fi / Bluetooth firmware | Buildroot 2026.08 の `brcmfmac_sdio-firmware-rpi.mk` は `PROPRIETARY`、ライセンスファイル名を `LICENSE` としています。GPL のリポジトリライセンスとは別に、同梱バイナリ固有の条件が適用されます。 |
| 配布イメージ | GPL 対象ソフトウェアに対応するソースコードを提供できるようにします。今後イメージを公開するときは、Buildroot の `make legal-info` の出力も各イメージに添付する方針です。出力と実際のソース提供要件を照合し、配布物ごとに確認します。 |

この注意書きは法的助言ではありません。各コンポーネントのライセンスと配布条件を確認してから利用・再配布してください。
