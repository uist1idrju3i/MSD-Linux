# CardputerZero 向け MSD/Linux 調査記録

## 目的と前提

MSD/Linux は Muromi Software Distribution / Linux の略で、開発場所の近くを流れる福岡県の室見川から名前をとりました（[名称](#名称)）。M5Stack CardputerZero（標準版・Lite 版の両方）向けに、再現可能な Linux イメージを作ることを目指します。

外部の事前調査を出発点に公開資料で再確認し、確認度は各行の出典に基づいて示しています。

### 決定済みの方針

- 現行の実装のベースは Buildroot。M5 のドライバと Raspberry Pi カーネルを組み込む。
- Yocto Project への移行を検討・検証した結果、2026-11-02 に移行せず Buildroot を維持すると決めた。経緯、分かったこと、理由、再検討の条件は [総まとめ](docs/research/yocto-migration/summary-2026-11.md) にある。
- UI は LCD のテキストコンソールと内蔵キーボードによる CLI のみ。公式 LVGL ランチャー、公式アプリ、Debian `.deb` 互換は目標にしない。
- 標準版と Lite 版を同じイメージで扱う。Lite 版にも microSD スロットはあるが、microSD カードは付属しない。
- 起動を速くし、突然の電源断に備えて rootfs を読み取り専用にし、更新失敗時は A/B の前のスロットへ自動復帰することを目指す。
- SSH・VPN は調査対象にとどめ、実装しない。
- リポジトリのライセンス方針は GPL-2.0-or-later。配布物ごとのライセンスとソース提供に注意する。
- 開発中。実機の出荷は 2026 年 11 月に始まる予定（[最新動向](docs/research/scope-and-hardware.md#9-最新動向2026-10-18-時点)）。起動イメージは CI で作り QEMU で起動を確かめているが、実機では試していない。起動時間の目標値は実機測定後に決める。

### 概略アーキテクチャ案

現行の実装は [BUILD.md](docs/BUILD.md) を正本とします。以下には設計候補も含み、実機で成立を確認した構成という意味ではありません。

| 層 | 方針 |
|---|---|
| ビルド | Buildroot 2026.08、BR2_EXTERNAL として管理（Yocto への移行は検討の結果見送り） |
| カーネル | Raspberry Pi `rpi-6.18.y` を基準にし、コミットを固定 |
| 起動 | Raspberry Pi firmware と `autoboot.txt` / `tryboot` による A/B を調査・実装する。CM0 実機で要検証 |
| rootfs | 現行は読み取り専用 SquashFS + zstd。EROFS は比較候補であり、実機での採否試験は未実施 |
| 可変データ | 現行は `/data` ext4 と `/etc` の tmpfs overlay。電断耐性・寿命は実機で確認する |
| UI | ST7789V3 の LCD に fbcon を使う CLI と、TCA8418 内蔵キーボード |

## ハードウェア

SoC・ストレージ・LCD・キーボード・I2C・音声・USB・電源などの機能対応表は [hardware-spec.md](docs/research/hardware-spec.md) にあります。公式資料の版・全U1〜U37の部品・電源と信号の接続・実装との差異・確認結果は [部品と回路接続の監査](docs/research/hardware-wiring-audit.md) にまとめました。

## 公式ソフトウェア構成

公式イメージ（pi-gen による Raspberry Pi OS 派生）、カーネル、M5 ドライバ、DeviceTree・権限・運用の差異は [公式OS・BSP比較](docs/research/official-software.md) にまとめました。固定したCI生成物のDTBO、modules、firmware、最終設定、QEMUログを調べた範囲と失敗試行は [生成物の確認記録](docs/experiments/2026-11-02-hardware-artifact-audit.md) にあります。実機動作や公式配布image全体の検証とは区別します。

### 詳細な調査記録

本文の条件、数値、確認度、根拠 URL は主題文書にあります。操作は [文書案内](docs/README.md)、証拠は [実験一覧](docs/experiments/README.md)、更新する本文の置き場は [文書の配置](docs/research/document-map.md) を参照してください。

#### 対象・ハードウェア・表示と入力

- [調査の前提・ハードウェア・候補](docs/research/scope-and-hardware.md)
- [ハードウェア仕様と機能対応表](docs/research/hardware-spec.md)
- [CardputerZero / Raspberry Pi CM0 エコシステム調査](docs/research/community-2026-11.md)
- [ハードウェア機能の対応表](docs/research/hardware-spec.md#ハードウェア機能の対応表)
- [公式ソフトウェア構成](docs/research/official-software.md)
- [フォントの調査](docs/research/fonts.md)
- [フレームバッファ端末とテキストブラウザの調査](docs/research/fb-terminals-and-text-browsers.md)
- [HDMI 外部ディスプレイ出力の調査](docs/research/hdmi-output.md)
- [表示サーバー・描画基盤の調査（X11 / Wayland / 代替技術）](docs/research/display-servers.md)
- [ウェブブラウザの調査](docs/research/web-browsers.md)

#### 起動・カーネル・CPU とメモリ

- [起動高速化・カーネル](docs/research/boot-and-kernel.md)
- [起動時間の実測と分析](docs/research/boot-time-measurements.md)
- [カーネル縮小](docs/research/kernel-size.md)
- [sysctl の既定値](docs/research/tunables-sysctl.md)
- [モジュールパラメーター](docs/research/tunables-module-params.md)
- [メモリ信頼性（EDAC / MCE / DRAM リフレッシュ）の調査](docs/research/memory-reliability-2026-11.md)
- [Raspberry Pi ファームウェア仕様の調査](docs/research/rpi-firmware-spec.md)
- [カーネル版と起動方針](docs/research/kernel-policy.md)
- [高速起動記事とCortex-A53調整](docs/research/fastboot-and-cpu-tuning.md)
- [CPU・割り込み・sysctl の調整余地](docs/research/cpu-irq-and-sysctl.md)
- [調整項目の全一覧（QEMU で取得した既定値）](docs/research/tunables-defaults.md)

#### 保存・電源断・更新

- [電源断耐性・A/B 更新](docs/research/power-and-updates.md)
- [ストレージ・SD カード・フラッシュ測定](docs/research/storage-and-flash.md)
- [読み取り専用領域・ファイルシステム・障害試験](docs/research/readonly-data-and-fs.md)
- [ファイルシステムの候補と設計例](docs/research/fs-candidates.md)

#### ユーザー空間・セキュリティ

- [OpenBSDの考え方とLinuxの具体的な権限設計](docs/research/security/README.md) — 原則、処理別の権限・可変設定、通信開始前の防御、未実装部分の検証条件。
- [セキュリティ・ハードニング](docs/research/security-hardening.md)
- [セキュリティ強化項目の調査（2026-11）](docs/research/security-2026-11-hardening-list.md)
- [再実装ライブラリとアロケータの調査](docs/research/reimplemented-libraries.md)
- [ユーザー空間・libc 調査](docs/research/userspace-and-security.md)
- [SSH・VPN・鍵保管の調査](docs/research/ssh-vpn-and-keys.md)
- [SSH サーバー・クライアント実装の調査](docs/research/ssh-implementations.md)

#### 開発・測定・未確認事項

- [SBOMの生成・確認範囲と監視の限界](docs/research/sbom-coverage.md)
- [シミュレーション検証計画](docs/research/simulation-plan.md)
- [未確認事項・測定・調査限界](docs/research/measurement-and-planning.md)
- [未確認事項の追跡表](docs/research/open-questions.md)
- [開発環境と CI の選定・予備的な測定](docs/research/dev-environment-and-ci.md)
- [開発用OCIの脆弱性と監視の確認](docs/research/development-image-security.md)

#### 比較・履歴・出典と意匠

- [使用部品・ツールの代替比較](docs/research/alternatives/README.md)（コンパイラー・runtime・libc、基本コマンド・init、暗号・TLS・署名、filesystem・更新framework・TUF metadata、[通信](docs/research/alternatives/network.md)、[周辺機能](docs/research/alternatives/peripherals.md)、[圧縮・host依存](docs/research/alternatives/build-support.md)、[開発・CI](docs/research/alternatives/development.md)を比較。[67構成要素との対応](docs/research/alternatives/coverage.csv)は役割別の索引で、全候補の同等性・license・実機動作の認定ではない）
- [公式サイトの HTML・CSS](docs/research/site-html-css.md)
- [ロスレス再圧縮ツールの調査](docs/research/lossless-recompression.md)
- [Yocto Project 移行の検討記録（移行見送り）](docs/research/yocto-migration/README.md)
  - [総まとめ（2026-11、移行しないと決定）](docs/research/yocto-migration/summary-2026-11.md)
  - [Buildroot への還元と証拠の確認範囲](docs/research/yocto-migration/buildroot-lessons.md)
  - [移行計画（案、中止）](docs/research/yocto-migration/migration-plan.md)
  - [Buildroot で見送った案の再評価](docs/research/yocto-migration/reevaluation.md)
  - [Buildroot と Yocto の Pros/Cons（2026-11）](docs/research/yocto-migration/pros-cons-2026-11.md)、[成果物の比較](docs/experiments/2026-11-02-buildroot-yocto-artifacts.md)、[QEMU での起動時間の比較](docs/experiments/2026-11-02-buildroot-yocto-boottime.md)
  - [構築試験（Wrynose、M5 BSP）](docs/experiments/2026-11-02-yocto-wrynose-probe.md)、[QEMU 起動確認](docs/experiments/2026-11-02-yocto-qemu-boot.md)
- [OS 候補の比較](docs/research/os-candidates.md)
- [訂正済み事項](docs/research/corrections.md)
- [出典一覧と URL 取得記録](docs/research/sources.md)
- [CI・Issue・リポジトリ設定の点検（2026-10-20）](docs/research/repo-operations-review.md)
- [作業の振り返りと残タスク（2026-10-22）](docs/research/retrospective-2026-10.md)
- [作業の振り返りと残タスク（2026-10-25）](docs/research/retrospective-2026-10-25.md)
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

パーティションと FAT 内部の整列、ext4 のブロックサイズと journal、discard、SD カードの測定条件は [storage-and-flash.md](docs/research/storage-and-flash.md) にあります。記録中の 1,024 B ブロックなどは当時の値です。現行 CI は 4,096 B を検査しており、現在の生成条件は [build workflow](.github/workflows/build.yml) と [ボード設定](board/cardputerzero/) で確認します。整列だけで速度・寿命・電断耐性が向上したとは判断しません。

## セキュリティとハードニングの要点

microSD を物理交換できる攻撃者は Linux より前の起動ファイルを差し替えられます。Raspberry Pi の secure-boot 手順は Pi 4 以降が対象で、BCM2837 向け経路は文書化されていません（物理的に不可能とは断定しません）。現行 updater は `manifest.sig` を検証し、SHA-256 manifest と書込み後の read-back を確認します。鍵や dm-verity root digest を同じカードに置いても、カード全体の交換を防げません。【一次】【未確認】[脅威モデルと A/B/C 案](docs/research/security-hardening.md)

署名検証と読み取り専用 rootfs への公開鍵配置は実装済みです。ただし可変なetcが公開鍵やpolicyを隠す境界も設計対象です。OpenBSDの最小特権・特権分離と放棄・多層防御・安全な既定値・単純さを、[処理ごとの権限と検証条件](docs/research/security/README.md)へ具体化しました。専用user・分離helper・firewall・新しいsandbox policyは未実装です。鍵のリリース・更新・失効、不要な無線／USB機能、信頼できるdigestを要するdm-verityを引き続き検討し、QEMUと実機の証拠を分けます。【一次】【推測】【未確認】[脅威モデルと費用](docs/research/security-hardening.md)

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
