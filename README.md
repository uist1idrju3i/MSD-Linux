# MSD/Linux

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/uist1idrju3i/MSD-Linux)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/msd-linux-logo-dark.svg">
    <img src="docs/logo/msd-linux-logo.svg" alt="MSD/Linux のロゴ。濃藍の円の中で室見川の流れが青海波の博多湾へ注ぐ。" width="480">
  </picture>
</p>

MSD/Linux は Muromi Software Distribution / Linux の略で、開発場所の近くを流れる福岡県の室見川から名前をとりました。名付け方は SSD/Linux にならっています（[名前の由来](RESEARCH.md#名称)）。M5Stack CardputerZero 向けの Linux OS を開発しています。

公式サイト: <https://muromi.moe/>

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
| 費用に見合うセキュリティ | OpenBSDの最小特権・特権分離と放棄・多層防御・安全な既定値・単純さを設計の基本にします。取り外せるmicroSDと、独立した起動時の信頼点を確認できていないBCM2837を前提に脅威を分け、効果・起動時間・メモリ・保守費用を測って採用します。 | 署名更新、module署名、RO rootfsとmount保護を基礎に、serviceごとのUID・device・書込み・通信の最小化と、通信開始前のpolicy強制を設計。実装・未実装の区別は[権限設計](docs/research/security/README.md) |
| 検証できる | QEMU で確認できることと、実機でしか確認できないことを分けて記録します。確認していないことを確認済みとは書きません。 | CI での Buildroot ビルドと QEMU 起動確認、実機での測定手順 |

デスクトップ環境、公式 LVGL ランチャー、公式 `.deb` アプリとの互換性は目標にしていません。SSH と VPN は調査対象にとどめ、実装しません。

## 開発状況

開発中です。Buildroot の外部ツリーと CardputerZero 用 defconfig があり、CI で Buildroot のフルビルドと、QEMU での A スロット・B スロットの起動を確かめています。QEMU の標準設定は `raspi3ap`（512 MiB、CM0 DTB）で、ASB パッチを含む開発用イメージ内の QEMU が必要です。1 GiB の `raspi3b` と Pi 3 DTB は `QEMU_MACHINE=raspi3b` で選べます。

CI とは別に、QEMU で実験を重ねています。watchdog による再起動、QEMU の強制終了で模した電源断からの回復、`/data` の ext4 の設定、dm-verity による改ざんの検出、zram などです。条件、生の値、結論は [docs/experiments/](docs/experiments/) にあります。dm-verity と zram は QEMU で試しただけで、製品の設定には入れていません。

QEMU では GPU firmware の `tryboot`、LCD、キーボード、M5 の I2C デバイス、実際の電源断を再現できません。これらは実機で確かめます。CardputerZero の出荷は 2026 年 11 月に始まる予定です（M5Stack の Kickstarter の更新 13 による。[最新動向](docs/research/hardware/scope-and-hardware.md#9-最新動向2026-10-18-時点)）。実機での起動はまだ試していません。

## 予定している構成

| 項目 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08 |
| カーネル | Raspberry Pi `rpi-6.18.y` |
| rootfs | Zstandard 圧縮の読み取り専用 SquashFS。書き込み領域に ext4 の `/data` を使用 |
| A/B 更新 | Raspberry Pi `autoboot.txt` と `tryboot` を使う構成を追加。実機での確認は未実施 |

## 共通の開発環境

MSD/Linuxは、ローカル開発とCI/CDで同じ開発環境を使うため、開発用Docker imageを構築・配布しています。開発者のOSが標準で提供する版とは独立して、ビルド・テスト・静的解析に必要なツールの版とパッチを管理します。CIだけの環境ではなく、手元でも同じDockerfileと固定した入力に基づく環境で作業できます。

製品の構築、host回帰、QEMU起動確認は`docker/msd-dev`経由で実行します。target用のBootlin toolchainはBuildrootがコンテナー内で取得・使用し、ビルド補助ツールやQEMUもコンテナー内のものを使います。開発hostへ個別にcompilerやQEMUを導入する手順を標準にはしません。公開済みimageの取得、未公開時のローカルbuild、CPU architectureの制約は[開発用Docker image](docker/README.md)、構築コマンドは[ビルド手順](docs/BUILD.md)を参照してください。

## microSDへのインストール

**開発用の手順です。CardputerZero実機での起動は未確認で、本番向けの署名済みSD imageはまだ提供していません。書き込みはカード全体を消去します。**

1. PCで [構築手順](docs/BUILD.md) に従い、`output/images/sdcard.img` を作ります。CIの成果物を使う場合は、対象commitのBuildroot buildが成功した実行から `msd-cardputerzero-build` を取得し、ZIPと `sdcard.img.xz` を展開します。文書だけのPRではbuildが省略されるため、CIが緑でもimageがあるとは限りません。
2. microSDの内容を別の媒体へバックアップし、ほかの外付けディスクを外します。[Raspberry Pi Imager](https://www.raspberrypi.com/software/) の **Use Custom** で `sdcard.img` を選び、容量・製品名を確認して書き込み先のmicroSDを選びます。**Exclude system drivesを無効にしないでください。** Raspberry Pi OS用のユーザー・Wi-Fi・SSHのカスタマイズは適用しません。
3. imageと書き込み先を再確認し、書き込みと検証を最後まで行います。完了後はPCで安全に取り外し、電源を切ったCardputerZeroへ挿入して起動します。PCがカードの未認識パーティションのフォーマットを求めても拒否します。
4. 起動できた場合は端末で次を確認します。操作できなければ成功とせず、[実機確認](docs/VERIFY.md) の記録を残します。Wi-Fiの接続管理とGitHubからの自動取得は未実装です。

   ```sh
   msd-update status
   cat /etc/msd-update/key-origin
   cat /etc/msd-update/version
   df -h /data
   ```

書くのはSD全体用の `sdcard.img` です。`Image`、`kernel8.img`、`boot.vfat`、更新用tarを単独でSDへ書いてもインストールにはなりません。出所の確認、容量、初回起動、再導入時のデータ消去は [導入手順](docs/INSTALL.md) を参照してください。

## A/Bアップデート

**以下は現行実装の操作手順であり、実機のtryboot・自動復帰を確認したものではありません。SD全体の再書き込みはA/B更新ではなく、`/data` も失います。**

1. `/data` のバックアップと安定した電源を用意します。端末が信頼する公開鍵に対応した `msd-update-bundle.tar` を準備し、手元で `/data/update.tar` に配置します。現行CIのSD image用artifactにはこのtarは含まれません。秘密鍵は端末へ置かず、署名エラー時に検証を無効にしないでください。
2. 端末の管理権限で次を一行ずつ実行します。`install` が失敗したら止め、`try` は実行しません。

   ```sh
   msd-update status
   df -h /data /tmp
   msd-update install /data/update.tar
   msd-update try
   ```

3. `install` は非稼働スロットへ書き、`try` は再起動します。試験起動後は `S99msd-health` がrootfs・`/data`・ready markerを確認し、合格すると **自動でcommit** します。利用者が周辺機能を確認するまで待つ仕組みではありません。
4. 起動後に次を確認し、`committed` の番号が表示中の `partition` と一致し、保留中の `installed` がないことを確かめます。commit後もその起動中は `tryboot=1` のままです。その後、通常の `reboot` を行い、同じ新スロット・`tryboot=0` で起動するか確認します。

   ```sh
   msd-update status
   cat /data/msd-update/committed
   test ! -e /data/msd-update/installed
   ```

失敗時の復帰、鍵の照合、空き領域と更新番号の制限は [A/B更新の詳細](docs/UPDATE.md#更新する前に) を参照してください。古い番号や署名不一致の拒否を、通常手順で回避しません。公開バージョンはSemVerで運用する方針ですが、現行manifestの番号は整数であり、SemVer文字列をそのまま渡せません。

## 文書

| 文書 | 内容 |
|---|---|
| [docs/README.md](docs/README.md) | 利用・構築・検証・調査・実験の文書案内 |
| [RESEARCH.md](RESEARCH.md) | 調査の要約、出典、未確認事項。節ごとの詳細は [docs/research/](docs/research/) |
| [docs/BUILD.md](docs/BUILD.md) | ビルドと QEMU 起動確認の手順 |
| [docs/UPDATE.md](docs/UPDATE.md) | 更新手順と検証範囲 |
| [docs/CI.md](docs/CI.md) | CI の構成と運用 |
| [docs/VERIFY.md](docs/VERIFY.md) | 実機でのカメラ・周辺確認の手順 |
| [docs/experiments/](docs/experiments/README.md) | 実験・測定の記録と生の値 |
| [docker/README.md](docker/README.md) | CI と同じ開発用コンテナー |
| [AGENTS.md](AGENTS.md) | 作業規約（AI エージェントと人間に共通） |

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
