# Buildroot で見送った案の Yocto 前提での再評価

> 注記（2026-11-02）: 検討の結果、Yocto には移行せず Buildroot を維持すると決まりました（[総まとめ](summary-2026-11.md)）。本書は検討の記録として残します。

Buildroot の時期に不採用・保留・調査のみとした案を、Wrynose 6.0 LTS を使う前提で一つずつ見直した結果です（2026-11-02 時点）。系列は利用者の判断で Wrynose 6.0 LTS に決まっています。移行作業はまだ行っておらず、ここに書くのは判断と、判断に必要な証拠だけです。

判断の軸は、MSD/Linux の六つの設計柱（起動速度、電源断耐性、A/B 復帰、全ハードウェアの利用、セキュリティ、検証可能性）です。「Buildroot ではできなかったが Yocto ならできる」ことと、「ビルドシステムと関係なく、測定の結果で決まった」ことを分けて扱います。

凡例: 【一次】は公開資料・upstream のソースで確認したこと、【実測】は本リポジトリの実験で確かめたこと、【推測】は未検証の見込みです。

## 1. 結論の一覧

| 項目 | Buildroot での判断 | Yocto で変わること | 再評価 |
|---|---|---|---|
| ビルド基盤としての Yocto | 移行しない（[pros-cons-2026-10.md](pros-cons-2026-10.md)） | 系列 Wrynose を選択。SPDX・ライセンス・層の分離を製品の監査に使う | 移行の方向に変更。Buildroot の削除は §3 の受け入れ基準を満たしてから |
| 実行時のパッケージ管理 | 固定イメージと合わない | パッケージは作るが、イメージには入れない構成にできる | 不採用を維持（イメージに `package-management` を入れない） |
| RAUC | 調査のみ | `meta-rauc` に wrynose ブランチ。tryboot には custom backend が必要 | 再検討する。最初は `msd-update` を移し、RAUC は別の実験で比べる |
| SWUpdate・Mender | 調査のみ | 既成の RPi 構成は U-Boot | 不採用を維持 |
| U-Boot・UKI・FIT | 採用しない | `uki.bbclass`・`kernel-fit-image.bbclass` がある | 不採用を維持（起動段が増え、firmware 直接起動の利点を失う） |
| dm-verity | 後で評価（QEMU で破損の拒否は確認済み） | meta-security に `dm-verity-img.bbclass` | 再検討する。イメージ生成に組み込む候補 |
| EROFS | QEMU 比較で不採用（#126） | `erofs`・`erofs-lz4` の型がある | 不採用を維持（結論はファイルシステムの性質による） |
| cramfs | 実測で不採用 | 変化なし | 不採用を維持 |
| F2FS・btrfs（/data） | 保留 | 変化なし | 保留を維持（電断試験で決める） |
| systemd | 別フェーズ | `INIT_MANAGER` を変えるだけで別イメージを作れる | 比較実験の候補にする。最初は BusyBox init と mdev |
| musl | 検討なし（Bootlin glibc） | `TCLIBC` で切り替えられる | 比較実験の候補にする |
| 外部ツールチェーン | Bootlin glibc を採用 | 内部 GCC 15.3.0 が標準【実測】 | 内部ツールチェーンに切り替える |
| `-Os`・LTO・`_FORTIFY_SOURCE=3` | 採用済み（#141） | `lto.inc`・`security_flags.inc` で distro に書く | 維持する。distro 設定で再現し、生成物で確かめる |
| 任意ドライバーのモジュール化 | 見送り（#129、Image -3.6%） | カーネルモジュールが個別パッケージになる | 見送りを維持。比較は容易になる |
| PREEMPT_RT | 採用済み（`linux.fragment`） | 変化なし（B2 で vermagic を確認【実測】） | 維持 |
| SELinux | 不採用 | meta-selinux がある | 不採用を維持 |
| `modules_disabled=1` | 不採用 | 変化なし | 不採用を維持 |
| SSH・VPN | 実装しない方針 | レシピは揃っている | 方針を維持（イメージに入れない） |
| secure boot 対応 SoC | 優先しない | 変化なし（ハードウェアの問題） | 維持 |
| 再現可能ビルド | defconfig・SHA-256・Docker digest で構成 | `SOURCE_DATE_EPOCH` が既定、oeqa に再現性の試験 | 取り込む |
| SBOM・ライセンス | CI で `sbom.cdx.json` と `legal-info` | SPDX 3.0 が既定、`sbom-cve-check`、archiver、`license.manifest` | 取り込む |
| 読み取り専用 rootfs | 自前の設定 | `read-only-rootfs` の IMAGE_FEATURE、`overlayfs-etc` | 取り込む候補。挙動を比べてから決める |
| 標準版と Lite 版 | 同じイメージ | image recipe を分けるのは容易 | 同じイメージを維持。別 image は実験用だけ |

## 2. 項目ごとの理由

### 2.1 Yocto への移行そのもの

PR #150 の比較は、固定イメージとパッケージ管理の不一致、ビルドの重さ、検証基盤の作り直しを理由に「移行しない」と結論し、再検討の条件に「CRA 向けの正式な SBOM が必須になった場合」を挙げていました。今回、利用者が Wrynose 6.0 LTS を選びました。

- パッケージ管理の不一致は、パッケージを「ビルドの単位とメタデータ」として使い、イメージには `package-management` を入れないことで避けられます。Yocto の `core-image-minimal` の rootfs は 16 パッケージで、パッケージ管理のファイルは入っていませんでした【実測: [実験記録](../../experiments/2026-11-02-yocto-wrynose-probe.md)】。
- ビルドの重さは解消しません。空の状態からの最小イメージで 2 時間 4 分、作業領域は約 54 GB でした【実測】。sstate と共有ミラーで 2 回目以降を短くする設計が必要です（§3 のフェーズ Y3）。
- 検証基盤の作り直しは必要です。ただし、既存の QEMU 試験の考え方（ログイン行と slot の marker を見る）は、Yocto の deploy 出力にもそのまま使えました【実測: [QEMU 起動記録](../../experiments/2026-11-02-yocto-qemu-boot.md)】。

### 2.2 更新方式（RAUC・SWUpdate・Mender・U-Boot）

- RAUC の Raspberry Pi firmware 用 bootchooser（PR #1599）は、2026-11-02 の確認でも open のままで、最終更新は 2026-08-14 です【一次: https://github.com/rauc/rauc/pull/1599】。最新リリースは v1.15.2（2026-03-27）です【一次: https://github.com/rauc/rauc/releases】。
- tryboot と組み合わせるなら、RAUC の custom bootloader backend で `autoboot.txt` を書き換える handler を作ることになります（[verification-and-ops.md](verification-and-ops.md) §2）。得られるのは、署名・検証済みの bundle 形式、slot の状態管理、Yocto の `bundle` レシピによる生成です。失うものは、`msd-update` の小ささと、BusyBox だけで完結する構成です【推測】。
- 採否は実験で決めます。比べる指標は、更新途中の電源断から前の世代に戻れる割合（現行の電断試験と同じ回数）、イメージに増えるサイズと RAM、起動時間です。U-Boot を入れないことを前提条件にします。
- SWUpdate と Mender は、既成の Raspberry Pi 構成が U-Boot を前提にしており、CM0 の構成もありません（[power-and-updates.md](../storage/README.md) §7.4）。Yocto に移っても、この前提は変わりません。
- `uki.bbclass` と `kernel-fit-image.bbclass` は Wrynose の oe-core にありますが、EFI か U-Boot を前提にしています【一次: oe-core `meta/classes-recipe/`】。firmware がカーネルを直接起動する MSD の経路には合いません。

### 2.3 dm-verity

QEMU では、rootfs の破損を dm-verity が拒否することを確かめています（[実験記録](../../experiments/2026-10-21-qemu-dm-verity.md)）。Buildroot では、ハッシュの生成と root digest の受け渡しを自前のスクリプトで組む必要があり、後回しにしていました。

meta-security の wrynose ブランチには `dm-verity-img.bbclass` があり、ハッシュを付けたイメージと root hash を書いた `.env` を作ります。このクラス自身が「root hash は信頼できる場所に置くか、署名して検証すること」と書いています【一次: https://git.yoctoproject.org/meta-security/tree/classes/dm-verity-img.bbclass?h=wrynose】。meta-security は `openembedded-layer`（meta-oe）に依存します【一次: 同 `conf/layer.conf`】。

BCM2837 には OTP の secure boot がないため、カードごと差し替える攻撃への信頼点にはなりません（[security-hardening.md](../security-hardening.md)）。それでも、microSD の劣化や書き込み途中の破損を起動時に検出し、A/B の前の世代へ戻す判断材料になります。Yocto ではクラス一つで生成に組み込めるため、優先度を上げます。採否は、実機での起動時間の増分と読み込み遅延を測ってから決めます。

### 2.4 ファイルシステム（EROFS・cramfs・F2FS・btrfs）

EROFS と cramfs の不採用は、QEMU でのサイズと起動の測定から決めたもので、ビルドシステムには依存しません（[fs-candidates.md](../storage/filesystem-candidates.md)、[cramfs-xip.md](../cramfs-xip.md)）。Yocto の `image_types.bbclass` には `erofs`、`erofs-lz4`、`erofs-lz4hc` があるため、比べ直す手間は小さくなります【一次】。結論を変える新しい証拠はないので、不採用を維持します。F2FS と btrfs は電源断耐性の根拠が足りないための保留で、これも変わりません。

### 2.5 init と libc（systemd・musl）

M5Stack の公式構成は、表示の `fb_load.service` と LED の udev ルールで systemd と udev を前提にしています（[userspace-and-security.md](../userspace-and-security.md)）。Buildroot では init を差し替えた構成を並べて保つ手間が大きく、BusyBox init と mdev に絞っていました。

Yocto では `INIT_MANAGER` を変えた image を同じ層から作れます。`mdev-busybox` の構成は Wrynose で動き、QEMU でログイン画面まで起動しました【実測】。最初の製品構成は BusyBox init と mdev のままにし、systemd 版を比較用の image として作ります。比べる指標は、ログインまたは `MSD/Linux ready` までの時間、RAM、rootfs のサイズ、電源断の後の起動です。musl（`TCLIBC = "musl"`）も同じ方法で比べられますが、M5Stack のユーザー空間ソフトとの互換性は確かめていません【推測】。

### 2.6 ツールチェーンと最適化

Yocto では内部ツールチェーン（Wrynose では GCC 15.3.0【実測】）を使うのが標準です。Bootlin の外部ツールチェーンを使い続けると、sstate、SPDX、ライセンスの追跡からツールチェーンが外れます。そこで内部ツールチェーンに切り替えます。

Buildroot で採用した `-Os`、LTO、`_FORTIFY_SOURCE=3`（#141）は、distro の設定で再現します。oe-core の既定は `_FORTIFY_SOURCE=2` です（[verification-and-ops.md](verification-and-ops.md) §3.2）。`lto.inc` は oe-core にあります【一次】。適用の結果は、ELF のヘッダーと `checksec` 相当の検査で確かめます。

### 2.7 ライセンス・SBOM・再現性

Wrynose の oe-core は `INHERIT_DISTRO` の既定に `create-spdx` を含み、SPDX 3.0 のクラスと `sbom-cve-check` を持ちます【一次: `meta/conf/distro/defaultsetup.conf`、`meta/classes-recipe/`】。`SOURCE_DATE_EPOCH` も既定で設定されます【一次: `meta/conf/bitbake.conf`】。Buildroot の `legal-info` と CycloneDX の SBOM は、archiver、`license.manifest`、SPDX に置き換えられます。これは Buildroot ではできなかった水準の監査で、Yocto に移る主な理由の一つです。

M5Stack のライセンス不明のバイナリ（st7789v の初期化データ、BMI270 のファームウェア、TCA8418 のキーマップ）は、Wrynose で非推奨になった `CLOSED` ではなく、`LicenseRef-` と `NO_GENERIC_LICENSE` で扱います（[verification-and-ops.md](verification-and-ops.md) §4.2）。配布の可否は M5Stack への確認が必要です。

## 3. 移行計画への反映

上の結論は [移行計画（案）](migration-plan.md) に反映しています。比較実験の候補（RAUC、dm-verity、systemd、musl、`overlayfs-etc`）は、計画のフェーズ Y5 にまとめています。

## 出典（確認日 2026-11-02）

- RAUC PR #1599: https://github.com/rauc/rauc/pull/1599
- RAUC releases: https://github.com/rauc/rauc/releases
- meta-security `dm-verity-img.bbclass`（wrynose）: https://git.yoctoproject.org/meta-security/tree/classes/dm-verity-img.bbclass?h=wrynose
- meta-security `conf/layer.conf`（wrynose）: https://git.yoctoproject.org/meta-security/tree/conf/layer.conf?h=wrynose
- oe-core（yocto-6.0.4、`0f03c732a0a2d0506b41b1abe60b3f368b2300dc`）の `meta/classes-recipe/image_types.bbclass`、`overlayfs-etc.bbclass`、`uki.bbclass`、`kernel-fit-image.bbclass`、`rootfs-postcommands.bbclass`、`meta/conf/distro/defaultsetup.conf`、`meta/conf/distro/include/lto.inc`、`meta/conf/bitbake.conf`: https://git.openembedded.org/openembedded-core/tree/?id=0f03c732a0a2d0506b41b1abe60b3f368b2300dc
