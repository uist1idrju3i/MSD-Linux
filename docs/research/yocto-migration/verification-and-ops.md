# Yocto 移行時の検証・更新・ツールチェーン・ライセンスの調査

QEMU による検証、A/B 更新、ツールチェーンとハードニング、ライセンスと SBOM、CI と開発コンテナを、Yocto へ移る前提で調べました。確認日は 2026-11-02 です。oe-core の記述は wrynose ブランチ `ae5a301`（2026-10-27）のファイルを読んで確かめました。

## 1. QEMU による起動確認

### 1.1 現行の方式

- MSD は QEMU の `raspi3ap`（Cortex-A53 ×4、512 MiB）と `raspi3b`（1 GiB）で起動を確かめています。QEMU の文書では、両機種とも GPIO、SD/MMC ホスト、USB（DWC2）を実装済みです【一次】。GPU ファームウェア、tryboot、LCD、M5 の I2C 機器、電源断は QEMU では確かめられません（[QEMUの検証範囲](../verification/qemu-coverage.md)）。
- `docker/msd-dev` の QEMU は 11.1.2 で、`docker/qemu-patches/` の 4 本のパッチ（ASB の未実装領域、GPIO 入力割り込み、電源管理の watchdog、温度設定）を当てています（[docker/README.md](../../../docker/README.md)）。icount の時間計測は、11.1.2 の遅延回帰を避けるため、`board/cardputerzero/tools/qemu-bisect/build-qemu.sh` で作る 11.0.2 を使います（[qemu-bisect/README.md](../../../board/cardputerzero/tools/qemu-bisect/README.md)）。

### 1.2 runqemu で再現できるか

- oe-core wrynose の QEMU は `qemu-system-native_10.2.0.bb` です【一次】。MSD が使う 11.1.2・11.0.2 も、4 本のパッチも含まれません。
- `runqemu` は `qemuboot.conf` の `QB_SYSTEM_NAME` で実行ファイル名を決め、まず `STAGING_BINDIR_NATIVE` から探します。見つからなければ PATH 上のホストの QEMU を試します（`scripts/runqemu` の「QEMU binary not found in %s, trying host's QEMU」）【一次】。
- 機種や引数は `qemuboot.bbclass` の `QB_MACHINE`、`QB_MEM`、`QB_DTB`、`QB_KERNEL_CMDLINE_APPEND`、`QB_OPT_APPEND`、`QB_ROOTFS_OPT`、`QB_SERIAL_OPT` で指定でき、実行時にも `qemuparams=` で足せます【一次】。
- 依頼文の `qemu-wrapper` に当たる、外部の QEMU を指定する専用の仕組みは oe-core に見当たりません。oe-core にある `qemuwrapper-cross`（`meta/recipes-devtools/qemu/qemuwrapper-cross_1.0.bb`）は、ビルド中にターゲット用プログラムを user mode QEMU で動かすためのもので、起動確認には使いません【一次: レシピの存在、推測: 用途】。
- 以上から、パッチ入り QEMU を使う方法は二つ考えられます【推測】。
  1. `qemu-system-native` に bbappend で版の更新と 4 本のパッチを当てる。版を Yocto 側で固定できますが、oe-core の QEMU レシピとの差分を保守し続けることになります。
  2. Yocto は deploy 出力（`Image`、dtb、wic イメージ）だけを作り、起動は既存の `board/cardputerzero/qemu/run-qemu.sh` と `test-*.sh` に任せる。`docker/msd-dev` の QEMU をそのまま使えます。入力パスを Yocto の `DEPLOY_DIR_IMAGE` に向ける改修が要ります。
- 現行の `run-qemu.sh` は、SD を `-drive if=sd` で渡し、firmware を通さず `-kernel` と `-dtb` で起動します（既定の機種は `raspi3ap`）。`runqemu` が想定する virtio の root デバイスや network 設定とは前提が違います。`QB_*` をすべて上書きするより、2 の方が既存の判定（`check-serial-log.sh`、`serial-allowlist.txt`、起動時間の計測）を保ちやすいと考えます【推測】。

## 2. A/B 更新

現行は p1 の `autoboot.txt`（`tryboot_a_b=1`）と firmware の tryboot で boot-a / boot-b を切り替え、署名付きの更新バンドルを `msd-update` が書き込みます。tryboot の仕様と既存方式の比較は [power-and-updates.md](../power-and-updates.md) §7 にあります。

| 方式 | Yocto レイヤー（wrynose 対応） | RPi での起動切替 | MSD との関係 |
|---|---|---|---|
| tryboot + `msd-update` を移植 | 不要（自前レシピ） | firmware の tryboot | 現行の設計を保つ。`msd-update` と鍵埋め込みを .bb にする |
| RAUC | `meta-rauc` に wrynose ブランチあり。`meta-rauc-community` の `meta-rauc-raspberrypi` は `LAYERSERIES_COMPAT` が `wrynose blacksail` | 例は U-Boot（`system.conf` が `bootloader=uboot`、`u-boot-fw-utils` に依存） | tryboot を使うには RAUC の custom bootloader backend（`bootloader=custom`）で handler を自作 |
| Mender | `meta-mender-community` の wrynose ブランチに `meta-mender-raspberrypi`（compat `wrynose`） | U-Boot | U-Boot 導入で起動経路が変わり、起動時間の再測定が必要 |
| SWUpdate | `meta-swupdate` に wrynose・blacksail ブランチあり。`meta-swupdate-boards` は master と scarthgap のみ | 主に U-Boot / EFI Boot Guard 系【未確認】 | tryboot 連携は [power-and-updates.md](../power-and-updates.md) で未確認と記録済み |

- RAUC の文書は custom backend の handler が `get-primary`、`set-primary`、`get-state`、`set-state` などに応答する仕組みを説明しています【一次: integration.rst、reference.rst】。RAUC の文書に tryboot の記述はありません【一次】。
- Rtone の tryboot 用 RAUC backend の評価は [power-and-updates.md](../power-and-updates.md) に未確認として記録済みで、今回も一次資料は確かめていません。
- 移行の最初の段階では、tryboot と `msd-update` をそのまま移すのが最も変更が少ないと考えます。RAUC などを使うかは、移行後に別途判断できます【推測】。U-Boot を使う既成レイヤーを選ぶと、firmware から直接カーネルを起動する現行の起動経路（[RESEARCH.md](../../../RESEARCH.md) の概略アーキテクチャ案）が変わり、起動時間を測り直すことになります。

## 3. ツールチェーンとハードニング

### 3.1 Bootlin 外部ツールチェーン

- 現行は Bootlin の aarch64 glibc stable 版を使っています。Bootlin のツールチェーンは Buildroot で作られ、stable と bleeding-edge の 2 系統があります【一次: toolchains.bootlin.com】。
- oe-core の `TCMODE` 用ファイルは `tcmode-default.inc` だけで、外部ツールチェーン用の設定は含まれていません【一次】。
- 汎用の外部ツールチェーン層 `MentorEmbedded/meta-external-toolchain` の最終コミットは 2020-08-25 で、`LAYERSERIES_COMPAT` は `thud warrior zeus dunfell` です【一次】。Wrynose では使えません。Bootlin 用に保守されている Yocto レイヤーは、今回の調査では見つかりませんでした【未確認】。
- このため、移行後は Poky 内部のツールチェーン（Wrynose なら GCC 15.2、glibc 2.43）を使うのが現実的です【推測】。ツールチェーンが変わるため、起動時間とイメージサイズを測り直す必要があります。

### 3.2 最適化・LTO・FORTIFY

| 現行（Buildroot） | Yocto での指定 | 根拠 |
|---|---|---|
| `BR2_OPTIMIZE_S=y` | `FULL_OPTIMIZATION`（`bitbake.conf` 既定は `"-O2 ${DEBUG_LEVELFLAG}"`）を distro 設定で `-Os` に上書き | 【一次】bitbake.conf L669、上書き方法は【推測】 |
| `BR2_ENABLE_LTO=y` | `require conf/distro/include/lto.inc` と `DISTRO_FEATURES:append = " lto"` | 【一次】lto.inc のコメント |
| （同上） | lto.inc は glibc、busybox、libxcrypt、curl、libcap などで LTO を外す | 【一次】`LTO:pn-busybox = ""` ほか。現行より LTO の範囲が狭くなる |
| `BR2_FORTIFY_SOURCE_3=y` | `security_flags.inc` の `lcl_maybe_fortify` は `-D_FORTIFY_SOURCE=2` を既定にする（`?=`）。distro 設定で 3 に上書きする | 【一次】wrynose と blacksail の security_flags.inc、上書き方法は【推測】 |
| PIE、`-fstack-protector-strong`、`-z relro -z now` | `security_flags.inc` の既定（`SECURITY_CFLAGS`、`SECURITY_LDFLAGS`）。`require conf/distro/include/security_flags.inc` で有効 | 【一次】 |

- `_FORTIFY_SOURCE=3` は GCC 12 以降で使えます。Wrynose の GCC 15.2 は条件を満たします【推測: GCC の版の比較】。
- 依頼文では LTO を「distro feature」と書いていますが、実際には lto.inc の require と `DISTRO_FEATURES` の追加の二つが必要です。

## 4. ライセンス・ソース提供・SBOM

### 4.1 現行との対応

| 現行 | Yocto での受け皿 | 根拠 |
|---|---|---|
| `make legal-info`（ソースとライセンスの一式） | `INHERIT += "archiver"`。`ARCHIVER_MODE[src]` は `original`・`patched`（既定）・`configured`・`mirror`。`COPYLEFT_LICENSE_INCLUDE`/`EXCLUDE` と `COPYLEFT_RECIPE_TYPES` で範囲を決める | 【一次】archiver.bbclass |
| 配布物に添付するライセンス一覧 | `license_image.bbclass` がイメージごとに `license.manifest` を出す。`-lic` パッケージは `LICENSE_CREATE_PACKAGE` が前提 | 【一次】 |
| CycloneDX SBOM（`utils/generate-cyclonedx`） | SPDX 3.0 の SBOM（`create-spdx-image-3.0`）。形式が CycloneDX から SPDX に変わる | 【一次】classes の一覧、リリースノート |
| CVE 確認（`support/scripts/cve-check`） | `sbom-cve-check` クラス（Wrynose で追加、Blacksail でオフライン動作に対応） | 【一次】リリースノート |
| 禁止ライセンスの検査 | `INCOMPATIBLE_LICENSE`（例外は `INCOMPATIBLE_LICENSE_EXCEPTIONS`）。ワイルドカード（`*GPL-3.0*` など）も使える | 【一次】license_image.bbclass L115-L121、documentation.conf L218。値の設計は未実施 |

### 4.2 ライセンス不明の M5Stack バイナリ

- `package/m5stack-cardputerzero` は `cardputerzero,st7789v_lcd.bin`、`bmi270-init-data.fw`、`tca8418_keypad_m5stack_keymap.map` を `unknown` として扱っています。
- 依頼文の案は `LICENSE = "CLOSED"` です。Wrynose ではそのまま使えますが、Blacksail 6.1 の移行ガイドは `CLOSED` を非推奨とし、警告を出すとしています。代わりに、`LicenseRef-` で始まる独自ライセンスを `NO_GENERIC_LICENSE` と `LIC_FILES_CHKSUM` で示す方法を推奨しています【一次】。
- 不明なライセンスに `LicenseRef-` の本文を自作すると、権利者の許諾を示すように読めてしまう恐れがあります。候補は次の二つです【推測】。
  1. 当面は `CLOSED` とし、`LICENSE_FLAGS`（例: `m5stack-unknown`）を付けて、`LICENSE_FLAGS_ACCEPTED` で明示的に受け入れたときだけビルドする。
  2. M5Stack にライセンスを確認し、判明した条件を `LicenseRef-` と本文で記録する。
- 同じ仕組みは meta-raspberrypi の Synaptics ファームウェア（`synaptics-killswitch`）でも使われています【一次】。

## 5. CI と開発コンテナ

- GitHub-hosted の標準 Linux runner の SSD は 14 GB です【一次】。Yocto 6.0 の文書は空き 140 GB を求めています【一次】。CI で毎回フルビルドするのは難しく、次のいずれかが必要です【推測】。
  - sstate とダウンロードのキャッシュを CI の外（成果物やオブジェクトストレージ）に置き、ハッシュ等価サーバーも使う（kas 5.5 で hashserv の設定に対応）
  - セルフホスト runner を使う
  - 毎回は軽い検査（`bitbake -p` での解析、レイヤー検査）にとどめ、フルビルドは `workflow_dispatch` と週次に限る（現行の「CI を重くしない」方針と一致）
- CROPS の `crops/poky-container` の最終コミットは 2024-09-07 です【一次】。Ubuntu 26.04 系の更新は確認できませんでした。kas が配布する `ghcr.io/siemens/kas/kas` イメージ（5.5 タグ）は取得できました【一次: docker pull】。開発コンテナは、`docker/msd-dev` を拡張するか kas-container を使うかを、フェーズ3で比べます。
- 現行の `build.yml` には `changes`、`msd-update-tests`、`build` の 3 ジョブがあり、`build` で `legal-info` と CycloneDX SBOM も作っています。移行では archiver、`license.manifest`、SPDX に置き換えます。

## 6. コミュニティ情報の収集

| 収集先 | 結果 |
|---|---|
| docs.yoctoproject.org、wiki.yoctoproject.org、yoctoproject.org | 取得できた（本書と [releases-and-layers.md](releases-and-layers.md) の出典） |
| layers.openembedded.org | 今回は使わず、各レイヤーの git を直接確認した |
| meta-raspberrypi・meta-rauc・meta-mender・meta-swupdate・kas の GitHub | `git ls-remote` と `git clone` で確認できた |
| git.openembedded.org、git.yoctoproject.org の Web 表示 | この VM からは HTTP 403。git での取得はできたため、出典には GitHub のミラーかリポジトリ URL とコミットを示した |
| Bootlin（トレーニング資料、toolchains） | 取得できた。Yocto トレーニングの lab 資料は 2026-11-01 に更新されていた |
| yocto@lists.yoctoproject.org | 今回は検索していない【未確認】 |
| Reddit r/embeddedlinux | 検索 API が JSON 以外を返し、取得できなかった【未確認】 |
| Mastodon（mastodon.social） | 未認証の検索は 0 件を返した【未確認】 |
| X | アクセスしていない【未確認】 |
| raspberrypi.com の config.txt 文書 | この VM からは HTTP 403。tryboot の一次資料は [power-and-updates.md](../power-and-updates.md) が引く GitHub の文書を使った |

コミュニティの移行事例（Buildroot から Yocto へ、RPi + RAUC tryboot）は、今回は一次資料を見つけていません。メーリングリストと SNS は、アクセスできる環境で追加調査するときの残課題です。

## 出典（確認日 2026-11-02）

- https://www.qemu.org/docs/master/system/arm/raspi.html 【一次】raspi3ap・raspi3b の仕様と実装済みデバイス
- https://github.com/openembedded/openembedded-core/tree/ae5a301091f5b0574ea7444aab40b309b6d9f3f2 【一次】wrynose の oe-core（`scripts/runqemu`、`meta/classes-recipe/qemuboot.bbclass`、`meta/conf/bitbake.conf`、`meta/conf/distro/include/lto.inc`、`security_flags.inc`、`meta/classes/archiver.bbclass`、`meta/classes-recipe/license_image.bbclass`、`meta/recipes-devtools/qemu/`）
- https://github.com/openembedded/openembedded-core/blob/d3494922ad3e10a8880fa349366eb22e1f9f24ca/meta/conf/distro/include/security_flags.inc 【一次】blacksail の FORTIFY 既定
- https://github.com/rauc/rauc/blob/e1b95d538c41178d3ac19069a2602988fe339fb8/docs/integration.rst 【一次】custom bootloader backend
- https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a 【一次】meta-rauc-raspberrypi（U-Boot 方式、compat）
- https://github.com/mendersoftware/meta-mender-community/tree/ebad311b35c45b420e354a24c9ce5e1ee709a25e 【一次】wrynose の meta-mender-raspberrypi
- https://github.com/MentorEmbedded/meta-external-toolchain/tree/bb754cb0a131d1a40f2a746e344cec49981173b3 【一次】外部ツールチェーン層の最終コミットと compat
- https://toolchains.bootlin.com/ 【一次】Bootlin ツールチェーンの構成
- https://bootlin.com/doc/training/yocto/ 【一次】Yocto トレーニング資料の一覧
- https://github.com/crops/poky-container/tree/cad5d17d3bad6d105adda2be1e398f4fae70e282 【一次】CROPS コンテナの最終コミット
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners 【一次】hosted runner の容量
- https://docs.yoctoproject.org/dev/migration-guides/migration-6.1.html 【一次】`CLOSED` の非推奨と `LicenseRef-`
- https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/docs/ipcompliance.md 【一次】`synaptics-killswitch`
- meta-rauc・meta-swupdate・meta-swupdate-boards のブランチは `git ls-remote` で確認しました（https://github.com/rauc/meta-rauc 、https://github.com/sbabic/meta-swupdate 、https://github.com/sbabic/meta-swupdate-boards ）。
