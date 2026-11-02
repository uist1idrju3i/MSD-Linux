# Yocto Project 移行検討の総まとめ（2026-11）

- 結論: Yocto Project には移行せず、Buildroot を維持します（2026-11-02、利用者の判断）。
- 対象期間: 2026-10 の比較（PR #150）から 2026-11-02 の検証まで
- 関連する PR: #150、#171、#172、#173、#174

## 1. 経緯

| 時期 | 内容 | 記録 |
|---|---|---|
| 2026-10 | Buildroot と Yocto を机上で比べ、「移行しない」と結論 | [pros-cons-2026-10.md](pros-cons-2026-10.md) |
| 2026-11-02 | フェーズ0の調査（系列、層、QEMU、A/B、ツールチェーン、ライセンス、開発環境） | [README.md](README.md) と同じディレクトリの各文書 |
| 2026-11-02 | kas-container で Wrynose 6.0.4 の最小イメージと M5 BSP をビルド | [構築試験](../../experiments/2026-11-02-yocto-wrynose-probe.md) |
| 2026-11-02 | 系列を Wrynose 6.0 LTS に決め、移行の方向で計画を作成 | [移行計画（案）](migration-plan.md)、[再評価](reevaluation.md) |
| 2026-11-02 | QEMU 起動、成果物、起動時間を Buildroot と比較 | [QEMU 起動確認](../../experiments/2026-11-02-yocto-qemu-boot.md)、[成果物の比較](../../experiments/2026-11-02-buildroot-yocto-artifacts.md)、[起動時間の比較](../../experiments/2026-11-02-buildroot-yocto-boottime.md)、[Pros/Cons（2026-11）](pros-cons-2026-11.md) |
| 2026-11-02 | 利用者が、移行せず Buildroot を維持すると判断 | 本書 |

## 2. 分かったこと

### 2.1 実測で確かめたこと

- Wrynose 6.0.4 で `raspberrypi0-2w-64` の最小イメージは、空の状態から 7,444 s でビルドできました。作業領域は約 42 GB、取得物は約 8.1 GB、sstate は約 3.6 GB です。同じ日の Buildroot の完成イメージは 3,280.65 s、作業領域 6.9 GB でした。
- M5Stack の BSP（`.ko` 16 個、dtbo 3 個、ファームウェアとキーマップ）は、`inherit module` の試験レシピでビルドできました。MSD のカーネル 6.18.59 と `linux.fragment` でも通りました。
- Yocto の最小イメージは QEMU でログイン画面まで起動しました。ただし、QEMU では PL011 が `ttyAMA1` になります。meta-raspberrypi の既定の getty（`ttyS0`）のままでは、ログイン画面は出ません。標準の QEMU で `raspi3ap` を使うと、Buildroot と同じく ASB のところで止まります。
- 同じ `bcm2711_defconfig` と fragment を使っても、カーネルの最終 `.config` は 544 項目が違いました（`CONFIG_THERMAL` が `n` になるなど）。それでも QEMU の起動時間には差が見えませんでした。
- ライセンスの追跡は Yocto のほうが細かくできます。SPDX 3.0.1 の文書が 9,119 ファイルできました。Buildroot の `legal-info` では、ツールチェーンのライセンスが `unknown` です。

### 2.2 調べて分かったこと

- 現在サポートされている系列は Scarthgap 5.0 LTS、Wrynose 6.0 LTS、Blacksail 6.1 です。Wrynose 以降は poky リポジトリにブランチがありません。
- meta-raspberrypi には CM0 用の machine がありません。既定では `bcm2710-rpi-cm0.dtb` も作られません。
- RAUC・SWUpdate・Mender の既成の Raspberry Pi 構成は U-Boot を前提にしています。RAUC の tryboot 対応（PR #1599）は、2026-11-02 の時点で未マージです。
- Wrynose では、パッチに `Upstream-Status` がないとビルドが止まります。イメージの型名は `squashfs-zst` です。

## 3. 移行しない理由

Yocto の利点（層の分離、SPDX、LTS、比較用イメージの作りやすさ）は確かめられました。一方で、今の MSD/Linux の目的には次の負担のほうが大きいと判断しました。

- ビルドに時間とディスクがかかる（cold ビルドで約 2.3 倍、作業領域で約 6 倍）。
- tryboot と `msd-update`、QEMU の試験、検査スクリプト、AGENTS.md とスキルのすべてを作り直す必要がある（[移行計画](migration-plan.md) §6）。
- 起動時間は、同じカーネルなら変わらない。Yocto に移っても速くはならない。
- 2026-10 の比較で挙げた不利な点（固定イメージとパッケージ管理の不一致、検証基盤の作り直し）は、今回の検証でも解消していない。

## 4. Buildroot に持ち帰れること

| 項目 | 内容 | 扱い |
|---|---|---|
| ツールチェーンのライセンス | `legal-info` でツールチェーンが `unknown` | 配布物の監査で補う必要があるか、別途確かめる |
| カーネル設定の確認 | `.config` は fragment 以外の項目でも変わりうる | カーネルを更新するときは、最終 `.config` 全体の差を見る |
| dm-verity、systemd などの比較 | Yocto 前提で優先度を上げた候補 | Buildroot でも同じ比較はできる。必要なら [simulation-plan.md](../simulation-plan.md) の候補として扱う |
| 計測スクリプト | `board/cardputerzero/tools/bench/yocto-compare/` | Buildroot のイメージ同士の比較にも使える |

## 5. 再検討する条件

- CRA などで、ツールチェーンを含む SPDX 形式の SBOM が配布の条件になった場合。
- CardputerZero 以外の機種や派生製品を同じ構成で作る必要が出た場合。
- Buildroot の安定系列の追従が保守の負担になった場合。

再検討するときは、本ディレクトリの調査、計画、実験記録から始められます。検証環境（作業領域、キャッシュ、比較用の clone）は 2026-11-02 に片付けました。再現の手順と入力の SHA-256 は、各実験記録にあります。
