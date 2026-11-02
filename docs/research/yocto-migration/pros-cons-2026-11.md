# Buildroot と Yocto の Pros/Cons（2026-11、成果物の比較から）

2026-11-02 に同じホストで作った成果物を並べ、Buildroot（現行）と Yocto（Wrynose 6.0.4）の長所と短所をまとめ直しました。数値は [成果物の比較](../../experiments/2026-11-02-buildroot-yocto-artifacts.md)、[構築試験](../../experiments/2026-11-02-yocto-wrynose-probe.md)、[QEMU 起動確認](../../experiments/2026-11-02-yocto-qemu-boot.md) によります。2026-10 の比較（[pros-cons-2026-10.md](pros-cons-2026-10.md)）は当時の記録として残します。

Yocto 側には、まだ CardputerZero の完成イメージがありません。そのため、イメージのサイズは比べていません。起動時間は、カーネルと rootfs を入れ替えた組み合わせで QEMU で比べました（[起動時間の比較](../../experiments/2026-11-02-buildroot-yocto-boottime.md)）。Buildroot と同じ形を目指すのではなく、Yocto で何が得られ、MSD/Linux の設計柱のどこに手当てが要るかを見ます。

凡例: 【実測】本リポジトリで確かめた、【一次】公開資料・upstream のソース、【推測】未検証。

## 1. 観点ごとの比較

| 観点 | Buildroot（現行） | Yocto（Wrynose） | どちらに利があるか |
|---|---|---|---|
| 構成の単位 | defconfig、fragment、overlay、後処理スクリプトが一つの tree にある | 層、machine、distro、image、レシピに分かれる | Yocto。BSP と製品の方針を分けて再利用・監査できる。ただし読むファイルは増える |
| cold ビルドの時間 | 完成イメージで 3,280.65 s【実測】 | 最小イメージで 7,444 s。ツールチェーンも作る【実測】 | Buildroot |
| 2 回目以降 | 設定を変えると作り直しが広がる場面がある | sstate と hash equivalence で再利用できる【一次】。本リポジトリでは測っていない | 測ってから判断 |
| ディスク | 作業 6.9 GB、取得物 0.7 GB【実測】 | 作業 約 42 GB、取得物 約 8.1 GB、sstate 約 3.6 GB【実測】 | Buildroot |
| ツールチェーン | Bootlin のビルド済み GCC 14.3.0。`legal-info` のライセンスは `unknown`【実測】 | 自分でビルドする GCC 15.3.0。SPDX と sstate に含まれる【実測】 | Yocto（追跡できる） |
| ライセンス・SBOM | `legal-info`（13 パッケージ）と CI の CycloneDX【実測】 | `license.manifest`（16 パッケージ）、SPDX 3.0.1（9,119 ファイル）、`sbom-cve-check`、archiver【実測・一次】 | Yocto |
| 再現性 | defconfig、URL と SHA-256 の固定、Docker digest | kas のロック、`SOURCE_DATE_EPOCH` の既定、再現性の試験（oeqa）【一次】 | Yocto（仕組みが標準） |
| カーネル | defconfig と fragment で最終 `.config` が決まる | 同じ defconfig と fragment でも 544 項目が違い、`CONFIG_THERMAL` が `n` になった【実測】 | Buildroot（Yocto では差を潰す作業が要る） |
| 起動時間（QEMU） | 同じソースと fragment のカーネルなら差は見えない【実測】 | 同左。既定のカーネル設定のままだと icount で `t_init` が約 1 s 長い【実測】 | 同等。完成イメージでは未比較 |
| init と rootfs | BusyBox init、mdev、自前の読み取り専用設定 | `mdev-busybox` が動く【実測】。`read-only-rootfs`、`overlayfs-etc` の仕組みがある【一次】 | 同等。Yocto は init を変えた比較が容易 |
| A/B 更新 | tryboot と `msd-update` が動いている（QEMU の A/B 試験に合格）【実測】 | 既成のレイヤーは U-Boot 前提。tryboot は自前のレシピにする | Buildroot（Yocto では移植が要る） |
| QEMU の起動確認 | `test-boot.sh`・`test-ab.sh` がある | 同じ考え方で起動確認できた。ASB パッチと `ttyAMA1` の扱いは同じく必要【実測】 | 同等。試験の移植が要る |
| 複数の製品・派生 | defconfig を増やして対応 | image と machine を足すだけで同じ層から作れる | Yocto |
| 長期の保守 | 安定系列を自分で追う | LTS が 2030-04 まで。移行ガイドがある【一次】 | Yocto |
| パッチの品質管理 | 決まりなし | `Upstream-Status` がないとビルドが止まる【実測】 | Yocto（手間は増える） |

## 2. Yocto に移る利点

- 層・レシピ・machine・distro・image の分離により、CardputerZero の BSP を製品の方針から切り離せます。他の distro や派生機種でも BSP を使えます。
- ツールチェーンを含むすべての部品が、SPDX、ライセンス、ソースの追跡に入ります。Buildroot ではツールチェーンのライセンスが `unknown` でした【実測】。
- init、libc、更新方式、dm-verity などを変えた比較用の image を、同じ層から作れます（[reevaluation.md](reevaluation.md)）。
- LTS の期間が長く、パッチの由来を記録する決まりがあります。

## 3. Yocto に移る欠点と手当て

| 欠点 | 手当て |
|---|---|
| cold ビルドが長く、ディスクを多く使う | sstate のミラーと hash equivalence を使い、2 回目以降を測ってから CI の置き場を決める |
| カーネルの最終 `.config` が Buildroot と一致しない | Y2 で差を一つずつ説明し、必要な項目を fragment に足す |
| tryboot・`msd-update`・QEMU の試験を作り直す | meta-msd のレシピにし、既存の試験の判定方法を引き継ぐ |
| ファイルが増え、読む量が増える | 層を二つに絞り、`yocto-check-layer` で層の決まりを確かめる |

## 4. 判断

利用者は 2026-11-02 に Wrynose 6.0 LTS への移行を方針として決めました。今回の比較は、その方針を変える事実を示していません。一方、ビルドの重さと `.config` の差は、移行計画で手当てが要る点として確かめられました。Buildroot は、[移行計画（案）](migration-plan.md) の受け入れ基準を満たすまで残します。
