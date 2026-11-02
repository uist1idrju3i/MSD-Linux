# Buildroot と Yocto の成果物の比較（同じ日の cold ビルド）

- 状態: 完了（ビルドと QEMU のみ、各 1 回）
- 日付: 2026-11-02
- 担当: Devin
- 関連: [Yocto Wrynose の構築試験](2026-11-02-yocto-wrynose-probe.md)、[Yocto の QEMU 起動確認](2026-11-02-yocto-qemu-boot.md)、[Pros/Cons（2026-11）](../research/yocto-migration/pros-cons-2026-11.md)

## 目的と仮説

Buildroot と Yocto（Wrynose 6.0.4）の成果物を、同じホストで同じ日に作って並べます。性能の測定ではなく、移行の判断に使う事実（何ができ、何が違うか）を集めることが目的です。

Yocto 側は CardputerZero の完成イメージではありません。E は `raspberrypi0-2w-64` の `core-image-minimal`、B2 は MSD のカーネル（6.18.59）と M5 の BSP を加えたビルドです。rootfs の中身も、ツールチェーンの作り方（Buildroot は Bootlin のビルド済み、Yocto は GCC を自分でビルド）も違うため、ビルド時間とサイズは同じものを比べた値ではありません。

## 採否の基準（結果を見る前に書く）

- Buildroot: `make` と `legal-info` の終了コードが 0、`test-boot.sh` と `test-ab.sh` が合格すること。
- 比べる値: ビルド時間、使ったディスク、主な成果物のサイズと SHA-256、ライセンスの成果物、カーネルの最終 `.config`。
- 繰り返し: 各 1 回（cold ビルドの所要時間は参考値）。

## 条件

| 項目 | Buildroot | Yocto |
|---|---|---|
| 基準の commit | `c26028c38076e008e3e6f649cdc0cc38818b63da` | 同左（kas の設定は構築試験の記録） |
| ホスト | Ubuntu 26.04.1、Linux 7.0.0-42-generic、12 CPU、RAM 32,468,656,128 bytes | 同左 |
| 環境 | `docker/msd-dev`（`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`） | kas-container 5.5（rootless Docker） |
| 版 | Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`、Bootlin GCC 14.3.0 | oe-core yocto-6.0.4、GCC 15.3.0 |
| 並列度 | `make -j6` | `BB_NUMBER_THREADS=6`、`PARALLEL_MAKE="-j 6"` |
| キャッシュ | `dl/` と ccache は空から | `DL_DIR` と `SSTATE_DIR` は空から（E） |

## 手順

```sh
git clone https://github.com/uist1idrju3i/MSD-Linux msd-baseline
cd msd-baseline
git checkout c26028c38076e008e3e6f649cdc0cc38818b63da
git submodule update --init
BR2_DL_DIR="$PWD/dl" BR2_CCACHE_DIR="$PWD/.ccache" \
  docker/msd-dev bash -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig'
BR2_DL_DIR="$PWD/dl" BR2_CCACHE_DIR="$PWD/.ccache" CCACHE_MAXSIZE=3G \
  docker/msd-dev bash -c '
    make -C output host-ccache
    ccache_bin=output/host/bin/ccache
    [ -x "$ccache_bin" ] || ccache_bin=output/per-package/host-ccache/host/bin/ccache
    CCACHE_DIR="${BR2_CCACHE_DIR}" "$ccache_bin" -z
    make -C output -j6
    make -C output legal-info'
board/cardputerzero/qemu/test-boot.sh
board/cardputerzero/qemu/test-ab.sh
```

Yocto 側は [構築試験の記録](2026-11-02-yocto-wrynose-probe.md) の手順です。カーネルの `.config` は、両方を `CONFIG_X=値` と `# CONFIG_X is not set`（`n` とみなす）に正規化し、ないものを `n` として比べました。

## 結果

生の値は [2026-11-02-buildroot-yocto-artifacts.csv](2026-11-02-buildroot-yocto-artifacts.csv) にあります。

### ビルド

| 項目 | Buildroot（CardputerZero の完成イメージ） | Yocto E（最小イメージ） |
|---|---|---|
| cold ビルドの時間 | 3,280.65 s（`legal-info` は別に 27.22 s） | 7,444 s |
| 作業領域 | `output/` 6,890,992,124 bytes | 約 42 GB |
| 取得物 | `dl/` 703,965,897 bytes | `DL_DIR` 約 8.1 GB |
| キャッシュ | ccache 294,705,322 bytes | sstate 約 3.6 GB |
| QEMU | `test-boot.sh`・`test-ab.sh` とも合格 | getty を 1 行足した写しでログイン画面まで（[記録](2026-11-02-yocto-qemu-boot.md)） |

### 成果物

| 成果物 | Buildroot | Yocto |
|---|---|---|
| rootfs | `rootfs.squashfs` 20,729,856 bytes（zstd、ブロック 131072、inode 2,006） | E の `squashfs-zst` 2,420,736 bytes（zstd、ブロック 131072、inode 525）。M5 のモジュールなどは入っていない |
| カーネル | `Image` 18,016,768 bytes、`kernel8.img`（gzip）7,431,286 bytes。6.18.59-v8 | B2 の `Image` 15,280,640 bytes（6.18.59-v8）。E の wic の `kernel8.img` は 6.18.33 の非圧縮で 27,052,544 bytes |
| ディスクイメージ | `sdcard.img` 771,751,936 bytes（A/B、7 区画） | E の wic（vfat と ext4 の 2 区画、bz2 で 26,116,676 bytes） |
| 更新 | `msd-update-bundle.tar` 87,848,960 bytes（署名付き） | なし |
| ライセンス | `legal-info`（`manifest.csv` 13 パッケージ、ソース、ライセンス文）。SBOM は CI で `generate-cyclonedx` から作る | `license.manifest` 16 パッケージ、SPDX 3.0.1 の文書 9,119 ファイル（ビルドした全レシピ分） |

SHA-256（Buildroot）: `sdcard.img` `117370a1c8376eda74e9d4e1245f79c6d2e00210788c97151ee3e266a621324a`、`rootfs.squashfs` `09192db9a20594dd1ec45d869c4d2b4f803b3428bb0ac22e6b75856feafab7bd`、`Image` `5e730f3da4b4ab31bff38fc2c1bff7a9d9dfb48127d7722e3976c01a5a5fed63`、`kernel8.img` `35f00a9707ae75f863d56d727f8601fe721976827a40a74e88932e1827617184`、`bcm2710-rpi-cm0.dtb` `f6c9ee59ccc5adb164ddba6508acc99e8038d2fe2017bd1f5fd5567af4999094`。Yocto 側の SHA-256 は [QEMU 起動確認](2026-11-02-yocto-qemu-boot.md) にあります。

Buildroot の `manifest.csv` では、`toolchain-external-bootlin` のライセンスが `unknown`、`brcmfmac_sdio-firmware-rpi` が `PROPRIETARY` でした。

### カーネルの `.config`

どちらも `bcm2711_defconfig` を元にし（Buildroot は `BR2_LINUX_KERNEL_DEFCONFIG="bcm2711"`、meta-raspberrypi は `KBUILD_DEFCONFIG:raspberrypi3-64 ?= "bcm2711_defconfig"` と `KCONFIG_MODE = "--alldefconfig"`）、同じ `linux.fragment`（518 行）を当てています。それでも、正規化した項目のうち 544 個の値が違いました（全項目は [2026-11-02-buildroot-yocto-kconfig-diff.csv](2026-11-02-buildroot-yocto-kconfig-diff.csv)。片方にない項目は `(absent)`）。多くは Buildroot で `m` の項目が Yocto にない（`6LOWPAN`、`BRIDGE_EBT_*` など）ものです。

CardputerZero に関係する主な項目（ウォッチドッグ、I2C、SPI、fbcon、DRM、SquashFS の zstd、dm-verity、zram、PREEMPT_RT、モジュール署名の強制など）は一致しました。違ったのは `CONFIG_THERMAL` で、Buildroot は `y`、Yocto は `n` でした（Buildroot では `BCM2835_THERMAL` と `BCM2711_THERMAL` も `y`）。`linux.fragment` に THERMAL の行はありません。原因は特定していません。Yocto の `--alldefconfig` による処理の違いと考えていますが、確かめていません【推測】。温度の監視に関わるため、移行計画の Y2 では最終 `.config` を Buildroot と突き合わせることを完了の条件にします。

### 失敗した試行

| 試行 | 内容 | 原因 |
|---|---|---|
| BR1 | `git worktree` で作った作業ツリーでビルド | submodule の `.git` が作業ツリーの外の metadata を指し、`docker/msd-dev` の `/work` から見えない。`M5STACK_CARDPUTERZERO_VERSION is empty` で停止。単独の clone に変えて BR2 で通った |

## 結論

- 同じ commit から Buildroot の完成イメージを cold でビルドし、QEMU の A/B 起動試験まで通ることを確かめました。比較の基準として使えます。
- Yocto は、ツールチェーンを自分でビルドすることもあり、最小イメージでも cold ビルドの時間と作業領域が大きくなります。2 回目以降の時間（sstate の効果）は測っていません。
- Yocto は SPDX をレシピごとに出し、`license.manifest` にもパッケージごとのライセンスが並びます。Buildroot の `legal-info` より細かい監査ができます。
- 同じ defconfig と fragment でも、カーネルの最終 `.config` は 544 項目で違いました。移行ではこの差を一つずつ説明する必要があります。
- 確かめていないこと: 完成イメージ同士のサイズ・起動時間の比較（Yocto の完成イメージはまだない）、実機。

## 再実行の方法

ビルドのログと QEMU のシリアルログはリポジトリに入れていません。正規化した `.config` の差は上の CSV に入れました。上の手順で再生成できます。
