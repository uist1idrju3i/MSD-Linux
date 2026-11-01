# CardputerZero 向け MSD/Linux 調査記録

## 目的と前提

MSD/Linux は Muromi Software Distribution / Linux の略で、開発場所の近くを流れる福岡県の室見川から名前をとりました（[名称](#名称)）。M5Stack CardputerZero（標準版・Lite 版の両方）向けに、再現可能な Linux イメージを作ることを目指します。

外部の事前調査を出発点に公開資料で再確認し、確認度は各行の出典に基づいて示しています。

### 決定済みの方針

- ベースは Buildroot。M5 のドライバと Raspberry Pi カーネルを組み込む。
- UI は LCD のテキストコンソールと内蔵キーボードによる CLI のみ。公式 LVGL ランチャー、公式アプリ、Debian `.deb` 互換は目標にしない。
- 標準版と Lite 版を同じイメージで扱う。Lite 版にも microSD スロットはあるが、microSD カードは付属しない。
- 起動を速くし、突然の電源断に備えて rootfs を読み取り専用にし、更新失敗時は A/B の前のスロットへ自動復帰することを目指す。
- SSH・VPN は調査対象にとどめ、実装しない。
- リポジトリのライセンス方針は GPL-2.0-or-later。配布物ごとのライセンスとソース提供に注意する。
- 開発中。実機の出荷は 2026 年 11 月に始まる予定（[最新動向](docs/research/scope-and-hardware.md#9-最新動向2026-10-18-時点)）。起動イメージは CI で作り QEMU で起動を確かめているが、実機では試していない。起動時間の目標値は実機測定後に決める。

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

SoC・ストレージ・LCD・キーボード・I2C・音声・USB・電源などの公開資料確認表は、 [hardware-spec.md](docs/research/hardware-spec.md) に分けました。

## 公式ソフトウェア構成

公式イメージ（pi-gen による Raspberry Pi OS 派生）、カーネル、M5 ドライバの構成と、よくある誤解の訂正は、[公式ソフトウェア構成](docs/research/official-software.md) に分けました。

### 詳細な調査記録

本文の条件、数値、確認度、根拠 URL を含む調査記録は、次の文書に分割しています。

- [調査の前提・ハードウェア・候補](docs/research/scope-and-hardware.md)
- [起動高速化・カーネル](docs/research/boot-and-kernel.md)
- [起動時間の実測と分析](docs/research/boot-time-measurements.md)
- [カーネル縮小](docs/research/kernel-size.md)
- [ハードウェア仕様と機能対応表](docs/research/hardware-spec.md)
- [シミュレーション検証計画](docs/research/simulation-plan.md)
- [sysctl の既定値](docs/research/tunables-sysctl.md)
- [モジュールパラメーター](docs/research/tunables-module-params.md)
- [公式サイトの HTML・CSS](docs/research/site-html-css.md)
- [電源断耐性・A/B 更新](docs/research/power-and-updates.md)
- [ストレージ・SD カード・フラッシュ測定](docs/research/storage-and-flash.md)
- [セキュリティ・ハードニング](docs/research/security-hardening.md)
- [セキュリティ強化項目の調査（2026-11）](docs/research/security-2026-11-hardening-list.md)
- [再実装ライブラリとアロケータの調査](docs/research/reimplemented-libraries.md)
- [CardputerZero / Raspberry Pi CM0 エコシステム調査](docs/research/community-2026-11.md)
- [メモリ信頼性（EDAC / MCE / DRAM リフレッシュ）の調査](docs/research/memory-reliability-2026-11.md)
- [Raspberry Pi ファームウェア仕様の調査](docs/research/rpi-firmware-spec.md)
- [ハードウェア機能の対応表](docs/research/hardware-spec.md#ハードウェア機能の対応表)
- [公式ソフトウェア構成](docs/research/official-software.md)
- [フォントの調査](docs/research/fonts.md)
- [ロスレス再圧縮ツールの調査](docs/research/lossless-recompression.md)
- [フレームバッファ端末とテキストブラウザの調査](docs/research/fb-terminals-and-text-browsers.md)
- [ユーザー空間・libc 調査](docs/research/userspace-and-security.md)
- [SSH・VPN・鍵保管の調査](docs/research/ssh-vpn-and-keys.md)
- [SSH サーバー・クライアント実装の調査](docs/research/ssh-implementations.md)
- [未確認事項・測定・調査限界](docs/research/measurement-and-planning.md)
- [未確認事項の追跡表](docs/research/open-questions.md)
- [OS 候補の比較](docs/research/os-candidates.md)
- [カーネル版と起動方針](docs/research/kernel-policy.md)
- [訂正済み事項](docs/research/corrections.md)
- [出典一覧と URL 取得記録](docs/research/sources.md)
- [高速起動記事とCortex-A53調整](docs/research/fastboot-and-cpu-tuning.md)
- [CPU・割り込み・sysctl の調整余地](docs/research/cpu-irq-and-sysctl.md)
- [調整項目の全一覧（QEMU で取得した既定値）](docs/research/tunables-defaults.md)
- [開発環境と CI の選定・予備的な測定](docs/research/dev-environment-and-ci.md)
- [CI・Issue・リポジトリ設定の点検（2026-10-20）](docs/research/repo-operations-review.md)
- [作業の振り返りと残タスク（2026-10-22）](docs/research/retrospective-2026-10.md)
- [作業の振り返りと残タスク（2026-10-25）](docs/research/retrospective-2026-10-25.md)
- [読み取り専用領域・ファイルシステム・障害試験](docs/research/readonly-data-and-fs.md)
- [ファイルシステムの候補と設計例](docs/research/fs-candidates.md)
- [和柄（日本の伝統文様）の調査とロゴ・サイトでの採否](docs/research/wagara.md)

### この記録に含めないもの

特定の外部製品比較、商標の個別確認、レポートの版管理情報は収録対象外です。名称の由来は本書に残します。

## 起動時間（実測値と分析）

詳しくは [boot-time-measurements.md](docs/research/boot-time-measurements.md) を参照してください。実機では未測定です。QEMU での段階ごとの測定では、`CONFIG_FTRACE` を無効にすると `MSD/Linux ready` が icount で 37.88 %、TCG で 5.68 % 早くなりました（[実験記録](docs/experiments/2026-10-20-qemu-boottime.md)。製品の設定は未変更）。

## 高速化のアイデア一覧

詳しくは [fastboot-ideas.md](docs/research/fastboot-ideas.md) を参照してください。

## 電源断耐性

読み取り専用 rootfs、永続領域、F2FS/btrfs/UBIFS/ext4 の採否、powerfail_suo、dm-verity、zram など電源断耐性の方針と候補、電源断試験の計画は、 [power-and-updates.md](docs/research/power-and-updates.md) に分けました。

## A/B 更新

tryboot と制約、更新フレームワーク（SWUpdate / RAUC / Mender / rauc-hawkbit-updater）の比較は、 [power-and-updates.md](docs/research/power-and-updates.md) に分けました。

## ストレージとフラッシュの要点

現行 CI イメージの MBR パーティション開始セクターは p1–p7 = `1 / 32769 / 163841 / 294913 / 294914 / 819203 / 1343492` です。各値の 4 KiB 境界からの余りは `1 / 1 / 1 / 1 / 2 / 3 / 4` セクターで、4 MiB 境界からの余りも同じです（1 セクター = 512 bytes）。genimage v20 で測定した `align=4M` 案では全開始位置が 4 MiB 境界にそろい、イメージは 736 MiB（現行より約 16 MiB 増）になりました。速度・寿命・電断耐性への効果は実機で未確認です。【実測】【未確認】[詳細と比較表](docs/research/storage-and-flash.md)

FAT データ領域はパーティション開始位置から 292 セクター（149,504 bytes）後に始まります。現行 p2 の絶対位置は 4 MiB 境界から 150,016 bytes ずれ、パーティション整列だけでは FAT 内部の BPB／データ領域 offset は変わりません。現行 `/data` は `data=journal` で、ext4 の現行文書はこの mode を非推奨とし、2028 年 1 月の削除予定を記載しています。`data=ordered` は移行候補ですが、アプリの `fsync`／rename と電断試験なしに同等の耐久性は主張できません。discard／fstrim、A1／A2、AU・消去単位はカードとホストで実測します。【一次】【実測】【推測】[用語、ext4、discard、測定計画](docs/research/storage-and-flash.md)

CI artifact の `/data` ext4 は `dumpe2fs` で 1,024 B ブロックと実測しました。これは 4 KiB page より小さい設定です。genimage の `extraargs` と実行時 formatter の両方に `-b 4096` を指定する案がありますが、page 境界との整合が性能や耐久性を高めるかは未測定で、効果は【推測】です。[実測値と mke2fs の選択理由](docs/research/storage-and-flash.md)

## セキュリティとハードニングの要点

microSD を物理交換できる攻撃者は Linux より前の起動ファイルを差し替えられます。Raspberry Pi の secure-boot 手順は Pi 4 以降が対象で、BCM2837 向け経路は文書化されていません（物理的に不可能とは断定しません）。現行 updater は `manifest.sig` を検証し、SHA-256 manifest と書込み後の read-back を確認します。鍵や dm-verity root digest を同じカードに置いても、カード全体の交換を防げません。【一次】【未確認】[脅威モデルと A/B/C 案](docs/research/security-hardening.md)

署名検証と読み取り専用 rootfs への公開鍵配置は実装済みです。今後は署名鍵のリリース・更新・失効手順、カーネル／sysctl のハードニング、不要な無線／USB 機能の採否を検討します。dm-verity は信頼できる digest の保管が条件です。起動・RAM・保守コストとハードウェア機能への影響、QEMU で検証できる更新処理と実機でしか検証できない BootROM／OTP・周辺機器を区別します。【一次】【推測】【未確認】[詳細と検証境界](docs/research/security-hardening.md)

## アイデア総覧

詳しくは [ideas-overview.md](docs/research/ideas-overview.md) を参照してください。

## QEMU で検証できる範囲

QEMU の `raspi3ap` と `raspi3b` は BCM2837 SoC をエミュレートしますが、Raspberry Pi の GPU ファームウェアや `tryboot`、CardputerZero の LCD・内蔵キーボード・M5 I2C デバイスは再現しません。`test-boot.sh` と `test-ab.sh` は p5／p6 の rootfs 起動後に `MSD/Linux ready` marker と login prompt を確認します。ホストテストでは更新処理の slot 判定・切替ロジックを確認します。ファームウェアによる tryboot、自動 rollback、実機周辺機器は実機検証の対象です。

## OS ベース比較

公開資料による OS 候補の比較表は、 [os-candidates.md](docs/research/os-candidates.md) に分けました。

## カーネル

kernel8.img の生成と検査、rpi-6.18.y 基準、PREEMPT、7.x 比較、overlay 依存、圧縮形式の評価は、 [kernel-policy.md](docs/research/kernel-policy.md) に分けました。

## init・libc

init と周辺デバイス、init の比較、libc / toolchain の調査は、 [userspace-and-security.md](docs/research/userspace-and-security.md) に分けました。

## ログと観測

開発中の観測方法は、 [measurement-and-planning.md](docs/research/measurement-and-planning.md) に分けました。

## SSH・VPN（調査のみ・実装しない）

SSH・VPN・鍵保管の調査は、 [ssh-vpn-and-keys.md](docs/research/ssh-vpn-and-keys.md) に分けました。

## 名称

MSD/Linux は Muromi Software Distribution / Linux の略です。

名付け方は、ぷらっとホームの [SSD/Linux](https://www.plathome.co.jp/support/labo/ssdlinux/) にならいました。公式ページによれば、SSD は「BSD (Berkeley Software Distribution) にならい、開発場所である外神田 (Sotokanda) を冠した名称」です。SSD/Linux は、開発者が中学3年生だった 2004 年に初めて触れた Linux です。

MSD/Linux も同じように、開発場所の近くを流れる福岡県の室見川（Muromi）から名前をとりました。ロゴは、室見川が博多湾へ注ぐ姿を描いています（[ロゴの意匠](docs/logo/README.md#意匠)）。ロゴと公式サイトの文様を選んだ調査は、[和柄（日本の伝統文様）の調査](docs/research/wagara.md)にまとめました。

名前には、もう一つの由来があります。開発者が好きなライトノベル『なれる!SE』（夏海公司、電撃文庫、2010〜2017 年）に登場する、室見立華（むろみ りっか）です。作中では、ネットワーク系のシステムエンジニアとして描かれています。作中の主要な登場人物の苗字は、どれも福岡市地下鉄の駅名からとられていて、室見立華は空港線の室見駅に由来します（[Wikipedia「なれる!SE」](https://ja.wikipedia.org/wiki/%E3%81%AA%E3%82%8C%E3%82%8B!SE)）。

## 公式サイトの HTML・CSS

詳しくは [site-html-css.md](docs/research/site-html-css.md) を参照してください。

## 未確認事項

未確認事項の追跡表は [open-questions.md](docs/research/open-questions.md) に、測定・調査限界は [measurement-and-planning.md](docs/research/measurement-and-planning.md) に分けました。

## 出典一覧

本文で引用した主要な一次資料・技術資料の一覧と URL 取得記録は、 [sources.md](docs/research/sources.md) に分けました。

