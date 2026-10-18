# MSD-Linux

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/uist1idrju3i/MSD-Linux)

MSD-Linux は、福岡県の室見川にちなんだ Muromi Software Distribution Linux の略称です。M5Stack CardputerZero 向けの Linux OS を開発しています。

## 目的

標準版と Lite 版をひとつのイメージでサポートし、LCD のテキストコンソールと内蔵キーボードで使える CLI を目指します。起動を速くし、読み取り専用 rootfs で突然の電源断に備え、A/B 更新に失敗した場合は前のスロットへ自動で戻すことを目標にしています。

デスクトップ環境、公式 LVGL ランチャー、公式 `.deb` アプリとの互換性は目標にしていません。SSH と VPN は調査対象にとどめ、実装しません。

## 開発状況

開発中です。Buildroot の外部ツリーと CardputerZero 用 defconfig を追加しましたが、フルビルド・QEMU 起動・実機起動はいずれも未確認です。実機は来月発売予定で、まだ起動イメージはありません。

## 予定している構成

| 項目 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08 |
| カーネル | Raspberry Pi `rpi-6.18.y` |
| rootfs | 読み取り専用 SquashFS を第一候補とし、EROFS と比較予定 |
| A/B 更新 | Raspberry Pi `autoboot.txt` と `tryboot` を使う方式を検証予定 |

詳細な調査結果、出典、未確認事項は [RESEARCH.md](RESEARCH.md) を参照してください。作業規約は [AGENTS.md](AGENTS.md) にあります。

ビルドと QEMU 起動確認の手順は [docs/BUILD.md](docs/BUILD.md) を参照してください。

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
| Raspberry Pi GPU firmware | `boot/LICENCE.broadcom` に従います。Buildroot 2026.08 の `rpi-firmware.mk` は `BSD-3-Clause` と記載しますが、実際の同ファイルは Raspberry Pi または認定派生機器での利用を条件とするバイナリ再配布条件です。 |
| Wi-Fi / Bluetooth firmware | Buildroot 2026.08 の `brcmfmac_sdio-firmware-rpi.mk` は `PROPRIETARY`、ライセンスファイル名を `LICENSE` としています。GPL のリポジトリライセンスとは別に、同梱バイナリ固有の条件が適用されます。 |
| 配布イメージ | GPL 対象ソフトウェアに対応するソースコードを提供できるようにします。今後イメージを公開するときは、Buildroot の `make legal-info` の出力も各イメージに添付する方針です。出力と実際のソース提供要件を照合し、配布物ごとに確認します。 |

この注意書きは法的助言ではありません。各コンポーネントのライセンスと配布条件を確認してから利用・再配布してください。
