# Yocto Project 移行の事前調査

MSD/Linux を Buildroot（BR2_EXTERNAL）から Yocto Project へ移す計画の、フェーズ0（外部情報の収集）の記録です。対象は M5Stack CardputerZero（CM0、BCM2710 系、Cortex-A53、aarch64）で、確認日は 2026-11-02 です。

この段階では実装も移行もしていません。依頼どおり、リリース系列も決めていません。決める前に、開発環境での構築試験と、M5 の BSP がビルドできるかの試験を行います。

## 1. 文書の一覧

| 文書 | 内容 |
|---|---|
| [releases-and-layers.md](releases-and-layers.md) | リリース系列とサポート期間、Poky の扱いの変化、meta-raspberrypi の machine とカーネル系列、ホスト要件 |
| [porting-map.md](porting-map.md) | defconfig、パッケージ、init、BSP、後処理、wks、fragment の対応表 |
| [verification-and-ops.md](verification-and-ops.md) | QEMU による起動確認、A/B 更新、ツールチェーンとハードニング、ライセンスと SBOM、CI、コミュニティ情報の収集結果 |
| [dev-environment.md](dev-environment.md) | 開発環境の構築手法（kas、kas-container、bitbake-setup、CROPS、buildtools、`docker/msd-dev` の拡張）の比較 |
| [summary-2026-11.md](summary-2026-11.md) | 総まとめ。2026-11-02 に移行せず Buildroot を維持すると決定 |
| [reevaluation.md](reevaluation.md) | Buildroot で不採用・保留にした案の Yocto 前提での再評価 |
| [migration-plan.md](migration-plan.md) | Wrynose 6.0 LTS を前提にしたゼロベースの移行計画（案・未着手） |
| [pros-cons-2026-11.md](pros-cons-2026-11.md) | 2026-11-02 の成果物の比較に基づく Buildroot と Yocto の Pros/Cons |
| [pros-cons-2026-10.md](pros-cons-2026-10.md) | 2026-10 に [PR #150](https://github.com/uist1idrju3i/MSD-Linux/pull/150) で行った Buildroot と Yocto の比較 |

## 2. 依頼の前提と調査結果の違い

依頼文の前提のうち、調べた結果が異なったものを先にまとめます。

| 依頼文の前提 | 調査結果 | 詳細 |
|---|---|---|
| Styhead、Whinlatter、Walnascar 系の LTS | 3 系列とも LTS ではなく、すでに EOL。サポート中は Scarthgap 5.0 LTS（2028-04 まで）、Wrynose 6.0 LTS（2030-04 まで）、Blacksail 6.1（2027-04 まで） | [releases-and-layers.md](releases-and-layers.md) §1 |
| poky をサブモジュールで管理 | Poky リポジトリの master は更新が止まり、Whinlatter 以降の系列のブランチがない。bitbake、openembedded-core、meta-yocto を個別に固定する | 同 §2 |
| meta-raspberrypi で RPi3 / CM0 を扱える | CM0 用の machine はない。`raspberrypi0-2w-64` か `raspberrypi3-64` を基に独自 machine を作り、`bcm2710-rpi-cm0.dtb` を加える | 同 §3.1 |
| `IMAGE_FSTYPES = "squashfs-zstd"` | 型名は `squashfs-zst` | [porting-map.md](porting-map.md) §6.1 |
| `LICENSE = "CLOSED"` | Wrynose では使えるが、Blacksail 6.1 で非推奨（警告）。`LicenseRef-` への移行が推奨されている | [verification-and-ops.md](verification-and-ops.md) §4.2 |
| `DELTA_KERNEL_DEFCONFIG` | oe-core にない。`SRC_URI` の `.cfg` か `KERNEL_FEATURES` を使う | [porting-map.md](porting-map.md) §7 |
| `board/cardputerzero/patches` を各レシピへ振り分ける | 中身はカーネル tarball の `linux.hash` だけ。パッチは M5 パッケージの 1 本だけ | 同 §1 |
| LTO は distro feature | `lto.inc` の require と `DISTRO_FEATURES` の追加の両方が要る。glibc や busybox は対象外 | [verification-and-ops.md](verification-and-ops.md) §3.2 |
| FORTIFY_SOURCE=3 相当 | oe-core の既定は 2。distro 設定で上書きする | 同 §3.2 |
| `qemu-wrapper` で外部 QEMU を指定 | 専用の仕組みはない。`runqemu` はビルド済みの QEMU がなければホストの QEMU を探す。既存の QEMU 試験に deploy 出力を渡す方法も候補 | 同 §1.2 |
| Bootlin 外部ツールチェーンと Poky 内部の比較 | Wrynose で使える外部ツールチェーン層は見つからなかった | 同 §3.1 |
| RPi + RAUC などの先例 | meta-rauc-raspberrypi も meta-mender-raspberrypi も U-Boot 方式。tryboot の先例は一次資料で確認できなかった | 同 §2 |
| 調査環境にブラウザと SNS がない | この VM からは HTTP で公式文書と git を取得できた。Reddit、Mastodon、X、メーリングリストは取得できなかったか、試していない | 同 §6 |
| イメージに入れるもの（busybox、kbd、v4l-utils など） | 現行の検査一覧には `sfdisk` なども含まれる。oe-core の BusyBox の inittab と rcS は現行と動きが違う | [porting-map.md](porting-map.md) §2、§3 |

## 3. フェーズ0の結論

- 2026-11-02 に、移行せず Buildroot を維持すると決まりました（[総まとめ](summary-2026-11.md)）。その前に、系列は利用者の判断で Wrynose 6.0 LTS に決まっていました。以下はフェーズ0の時点の判断材料です。サポート期限、meta-raspberrypi の 6.18 カーネル、Ubuntu 26.04 対応の三点では、Wrynose 6.0 LTS が最も条件に合います【推測】。Scarthgap は meta-raspberrypi に 6.18 のレシピがありません。Blacksail は 2027-04 で終わり、meta-raspberrypi に専用ブランチがありません。
- 構成管理は kas（YAML + ロックファイル）を第一候補にします（[dev-environment.md](dev-environment.md) §4）。
- A/B 更新は、最初の段階では tryboot と `msd-update` をそのまま移すのが最も変更が少ないと考えます【推測】。
- ツールチェーンは Poky 内部への切り替えが前提になり、起動時間とサイズの測り直しが要ります。
- PR #150 の比較（[pros-cons-2026-10.md](pros-cons-2026-10.md)）は「移行しない」と結論しました。そこで挙げた不利な点（固定イメージとパッケージ管理の不一致、ビルドの重さ、検証基盤の作り直し）は、今回の調査でも解消していません。移行するかどうかの判断は、構築試験の結果を踏まえて改めて行います。2026-11-02 に移行の方向が決まり、これらの不利な点への対策は [reevaluation.md](reevaluation.md) §2.1 と [migration-plan.md](migration-plan.md) に書きました。

## 4. 決めることと次の作業

| 項目 | 選択肢 | 決める時期 |
|---|---|---|
| リリース系列 | Wrynose 6.0 LTS / Scarthgap 5.0 LTS / Blacksail 6.1 | 決定済み（2026-11-02、Wrynose 6.0 LTS） |
| 構成管理 | kas + ロックファイル / bitbake-setup / サブモジュール | フェーズ1の開始時 |
| 開発コンテナ | kas-container / `docker/msd-dev` の拡張 | 構築試験の後 |
| A/B 更新 | tryboot + `msd-update` の移植 / RAUC の custom backend / U-Boot を使う既成レイヤー | フェーズ2 |
| QEMU | `qemu-system-native` の改修 / 既存の QEMU 試験に deploy 出力を渡す | フェーズ3 |
| CI の実行場所 | hosted runner + 外部キャッシュ / セルフホスト / 軽い検査と手動実行に限る | フェーズ3 |
| 不明ライセンスの M5 バイナリ | `CLOSED` + `LICENSE_FLAGS` / M5Stack への確認 | フェーズ2 |

この VM での構築試験（kas-container、暫定の Wrynose 6.0.4、`raspberrypi0-2w-64` の最小イメージ）と、M5 の BSP のビルド試験は通りました。MSD のカーネル固定（6.18.59）と `linux.fragment` を加えた試験も通りました。手順と結果は [実験記録](../../experiments/2026-11-02-yocto-wrynose-probe.md) にあります。構築試験ではビルドが通るかだけを見ました【一次: 実験記録】。その後、E のイメージが QEMU でログイン画面まで起動することを確かめました（[QEMU 起動確認](../../experiments/2026-11-02-yocto-qemu-boot.md)。getty を 1 行足した写しを使用）。

フェーズ4の受け入れ基準（六つの設計柱を退化させないこと）と、QEMU で確かめられる項目と実機でしか確かめられない項目の切り分けは、移植が進んでから [VERIFY.md](../../VERIFY.md) に書きます。
