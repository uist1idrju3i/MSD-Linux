# Yocto Wrynose 暫定環境と M5 BSP のビルド確認

- 状態: 完了
- 日付: 2026-11-02
- 担当: Devin
- 関連: [Yocto Project 移行の事前調査](../research/yocto-migration/README.md)、[開発環境の比較](../research/yocto-migration/dev-environment.md)、PR #171

## 目的と仮説

フェーズ0の調査で選んだ構築方法（kas-container と rootless Docker）で Yocto が動くかを確かめます。あわせて、調査文書で推測とした点を成果物で確かめます。系列は確認用に Wrynose 6.0.4 を仮に置いたもので、採用を決めたものではありません。

- E: `raspberrypi0-2w-64` の `core-image-minimal` がビルドでき、`squashfs-zst` 型、`INIT_MANAGER = "mdev-busybox"` の inittab と rcS、既定カーネル 6.18.33、既定で `bcm2710-rpi-cm0.dtb` を作らないことが成果物で確かめられる。
- B1: m5stack-linux-dtoverlays（MSD の固定コミット `37b42d9`）のモジュール 8 ディレクトリ、overlay 3 個、ファームウェア 2 個、キーマップ、powerfail パッチが、`inherit module` の試験レシピでビルドできる。
- B2: B1 に MSD のカーネル固定（6.18.59、`b3495ea`）と `board/cardputerzero/linux.fragment` を加えてもビルドできる。

## 採否の基準（結果を見る前に書く）

- E: 終了コードが 0 で、wic、squashfs-zst、Image、dtb ができること。調査の主張は 1 項目ずつ成果物で合否を付けます。
- B1・B2: Makefile の `obj-m` から求めた .ko 16 個がすべてでき、vermagic がカーネルの版と一致すること。dtbo 3 個が DTB として読めること。パッチで加えた文字列が `powerfail_suo.ko` に入っていること。
- 中止: 使用量が 300 GB を超えたとき、1 回のビルドが 8 時間を超えたとき、同じ失敗を 3 回直しても通らないとき。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | MSD-Linux `ec54778`（origin/main）。リポジトリのファイルは写しを作るために読んだだけです |
| ホスト | Ubuntu 26.04.1 LTS、カーネル 7.0.0-42-generic、12 スレッド、RAM 約 30 GB、sudo なし |
| コンテナ | rootless Docker 29.9.2、`ghcr.io/siemens/kas/kas@sha256:4b210b0be3c887875973c4f4c35470b4ecf3edd2346c9de1bdd33feae5b86e94`（kas 5.5、Debian 13）、kas-container スクリプト SHA-256 `5b352d554f6f43da727386f156ecff6f7db5df608b676f24a71da84557136210` |
| レイヤー | bitbake `51fd94a67fa17650a9ff623492005972bbc7d26f`（`yocto-6.0.4` タグの指す commit）、openembedded-core `0f03c732a0a2d0506b41b1abe60b3f368b2300dc`（同）、meta-raspberrypi `919588393f41b48cb6c5d832aa35e58a19b6762d`（wrynose） |
| GCC / カーネル | gcc 15.3.0（ログのレシピ名）、E・B1 は linux-raspberrypi 6.18.33（`95b85be`）、B2 は 6.18.59（`b3495ea`） |
| 出力先と状態 | `KAS_WORK_DIR`、`DL_DIR`、`SSTATE_DIR` はいずれもリポジトリの外の別々のディレクトリ（作業領域、取得物、sstate）。E は空の状態から、B1・B2 は E の出力を使い回しました |
| 変える条件 | E、B1、B2 の段（構成） |
| 変えない条件 | DISTRO は nodistro、`BB_NUMBER_THREADS = "6"`、`PARALLEL_MAKE = "-j 6"`、PSI 閾値 15000 |
| 繰り返し | 各段 1 回。性能の測定ではないため、時間は参考値です |

## 手順

kas の設定、試験レシピ、実行スクリプトは VM 上だけに置き、リポジトリには入れていません。全文を写します。

`probe-e.yml` の全文です。

```yaml
header:
  version: 23
machine: raspberrypi0-2w-64
distro: nodistro
target: core-image-minimal
repos:
  bitbake:
    url: https://git.openembedded.org/bitbake
    commit: 51fd94a67fa17650a9ff623492005972bbc7d26f
    layers:
      .: disabled
  openembedded-core:
    url: https://git.openembedded.org/openembedded-core
    commit: 0f03c732a0a2d0506b41b1abe60b3f368b2300dc
    layers:
      meta:
  meta-raspberrypi:
    url: https://github.com/agherzan/meta-raspberrypi
    commit: 919588393f41b48cb6c5d832aa35e58a19b6762d
local_conf_header:
  probe: |
    INIT_MANAGER = "mdev-busybox"
    IMAGE_FSTYPES:append = " squashfs-zst"
    LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"
    ENABLE_UART = "1"
    BB_NUMBER_THREADS = "6"
    PARALLEL_MAKE = "-j 6"
    BB_PRESSURE_MAX_CPU = "15000"
    BB_PRESSURE_MAX_IO = "15000"
    BB_DISKMON_DIRS = "STOPTASKS,${TMPDIR},10G,1M STOPTASKS,${DL_DIR},10G,1M STOPTASKS,${SSTATE_DIR},10G,1M"
```

`probe-b1.yml` の全文です。

```yaml
header:
  version: 23
  includes:
    - probe-e.yml
target: m5stack-cardputerzero-probe
repos:
  probe-cfg:
    layers:
      meta-msd-probe:
```

`probe-b2.yml` の全文です。

```yaml
header:
  version: 23
  includes:
    - probe-b1.yml
repos:
  probe-cfg:
    layers:
      meta-msd-probe:
      meta-msd-probe-kernel:
```

`meta-msd-probe/conf/layer.conf`（`meta-msd-probe-kernel` も同じ形で、名前と優先度 11 だけが違います）。全文を次に示します。

```text
BBPATH .= ":${LAYERDIR}"
BBFILES += "${LAYERDIR}/recipes-*/*/*.bb ${LAYERDIR}/recipes-*/*/*.bbappend"
BBFILE_COLLECTIONS += "msd-probe"
BBFILE_PATTERN_msd-probe = "^${LAYERDIR}/"
BBFILE_PRIORITY_msd-probe = "10"
LAYERDEPENDS_msd-probe = "core raspberrypi"
LAYERSERIES_COMPAT_msd-probe = "wrynose"
```

`meta-msd-probe/recipes-bsp/m5stack-cardputerzero-probe/m5stack-cardputerzero-probe_git.bb` の全文です。

```text
SUMMARY = "Probe build of the M5Stack CardputerZero BSP (VM-only experiment, not for distribution)"
LICENSE = "GPL-2.0-only & CLOSED"
LIC_FILES_CHKSUM = "file://COPYING;md5=bbea815ee2795b2f4230826c0c6b8814"

SRC_URI = "git://github.com/m5stack/m5stack-linux-dtoverlays.git;protocol=https;nobranch=1 \
           file://0001-powerfail-sync-and-notify.patch"
SRCREV = "37b42d9451495b5597dd7e50cab502da8028f9c2"
PV = "0+git"

inherit module deploy
DEPENDS += "dtc-native"

M5_MODULE_DIRS = "modules/CardputerZero modules/st7789v-1.0 modules/m5ioe1-1.0 modules/tca8418-1.0 \
                  modules/es8389-1.0 modules/bq27220-1.0 modules/imu-1.0/bmi270 modules/imu-1.0/magnetometer"
M5_MODULE_OPTS = "CONFIG_BMC150_MAGN=m CONFIG_BMC150_MAGN_BMI270=m CONFIG_BMI270=m CONFIG_BMI270_I2C=m"
M5_OVERLAYS = "modules/CardputerZero/cardputerzero-v5-overlay.dts modules/bq27220-1.0/bq27220_v5.dts \
               modules/imu-1.0/bmi270_bmm150_overlay.dts"

do_compile() {
    unset CFLAGS CPPFLAGS CXXFLAGS LDFLAGS
    for d in ${M5_MODULE_DIRS}; do
        oe_runmake -C ${STAGING_KERNEL_DIR} M=${S}/$d O=${STAGING_KERNEL_BUILDDIR} \
            CC="${KERNEL_CC}" LD="${KERNEL_LD}" AR="${KERNEL_AR}" OBJCOPY="${KERNEL_OBJCOPY}" \
            STRIP="${KERNEL_STRIP}" ${M5_MODULE_OPTS} KCFLAGS="-DCONFIG_CARDPUTERO_V0_5=1" modules
    done
    install -d ${B}/overlays
    for o in ${M5_OVERLAYS}; do
        base=$(basename "$o" .dts)
        ${BUILD_CPP} -E -nostdinc -undef -x assembler-with-cpp -DCONFIG_CARDPUTERO_V0_5=1 ${S}/$o -o ${B}/overlays/$base.dts.tmp
        dtc -@ -I dts -O dtb -o ${B}/overlays/$base.dtbo ${B}/overlays/$base.dts.tmp
    done
}

do_install() {
    unset CFLAGS CPPFLAGS CXXFLAGS LDFLAGS
    for d in ${M5_MODULE_DIRS}; do
        oe_runmake -C ${STAGING_KERNEL_DIR} M=${S}/$d O=${STAGING_KERNEL_BUILDDIR} DEPMOD=echo \
            INSTALL_MOD_PATH=${D} INSTALL_MOD_DIR=extra ${M5_MODULE_OPTS} modules_install
    done
    install -D -m 0644 ${S}/modules/st7789v-1.0/cardputerzero,st7789v_lcd.bin ${D}${nonarch_base_libdir}/firmware/cardputerzero,st7789v_lcd.bin
    install -D -m 0644 ${S}/modules/imu-1.0/bmi270-init-data.fw ${D}${nonarch_base_libdir}/firmware/bmi270-init-data.fw
    install -D -m 0644 ${S}/modules/tca8418-1.0/tca8418_keypad_m5stack_keymap.map ${D}${datadir}/keymaps/tca8418_keypad_m5stack_keymap.map
}

do_deploy() {
    install -d ${DEPLOYDIR}/m5stack-overlays
    install -m 0644 ${B}/overlays/*.dtbo ${DEPLOYDIR}/m5stack-overlays/
}
addtask deploy after do_install

PACKAGES += "${PN}-firmware"
FILES:${PN}-firmware = "${nonarch_base_libdir}/firmware ${datadir}/keymaps"
LICENSE:${PN}-firmware = "CLOSED"
```

パッチは `package/m5stack-cardputerzero/0001-powerfail-sync-and-notify.patch` の写しで、ヘッダーに `Upstream-Status: Inappropriate [MSD/Linux product-specific]` を 1 行加えました（理由は「捨てた試行と経緯」を参照）。

`meta-msd-probe-kernel/recipes-kernel/linux/linux-raspberrypi_6.18.bbappend`（`files/msd.cfg` は `board/cardputerzero/linux.fragment` の写し）。全文を次に示します。

```text
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
LINUX_VERSION = "6.18.59"
SRCREV_machine = "b3495ea401d709af0701a85babcba5e3d788a602"
SRC_URI += "file://msd.cfg"
```

実行スクリプト（`run-e.sh`。`run-b1.sh`、`run-b2.sh` は YAML とログ名だけが違います）。全文を次に示します。

```sh
#!/bin/sh
cd "$HOME/yocto-work"
unset DOCKER_HOST
export DOCKER_CONTEXT=rootless
export KAS_WORK_DIR="$HOME/yocto-work/work" DL_DIR="$HOME/yocto-cache/downloads" SSTATE_DIR="$HOME/yocto-cache/sstate"
export KAS_CONTAINER_IMAGE="ghcr.io/siemens/kas/kas@sha256:4b210b0be3c887875973c4f4c35470b4ecf3edd2346c9de1bdd33feae5b86e94"
date -u +%FT%TZ > logs/e.start
./kas-container build cfg/probe-e.yml > logs/e.log 2>&1
echo "exit=$?" > logs/e.done
date -u +%FT%TZ >> logs/e.done
```

## 計測器の検証

確認は成果物そのものを読んで行いました。.ko は `xz -d` で展開してから `strings` で vermagic を読みました。dtbo は先頭 4 バイトが DTB のマジック `d00dfeed` であることを確かめました。B2 の `.config` は、Python で `linux.fragment` の要求値と 1 項目ずつ比べました。同じ項目が 2 回あるときは後の値を有効とします。

## 結果

生の値は [CSV](2026-11-02-yocto-wrynose-probe.csv) にあります。

| 段 | 結果 | 時間（参考） | 確認した内容 |
|---|---|---|---|
| E | 合格 | 2 時間 4 分（空の状態から） | 下の表 |
| B1 | 合格 | 約 2 分（E の出力を使用） | .ko 16 個、vermagic `6.18.33-v8 SMP`、dtbo 3 個、ファームウェア 2 個、キーマップ |
| B2 | 合格 | 約 21 分（カーネルの再ビルドを含む） | .ko 16 個、vermagic `6.18.59-v8 SMP preempt_rt mod_unload modversions aarch64`、fragment の要求 490 項目 |

E で確かめた調査の主張は次のとおりです。

| 主張 | 結果 | 根拠 |
|---|---|---|
| 型名は `squashfs-zst` | 確認 | `core-image-minimal-raspberrypi0-2w-64.rootfs.squashfs-zst`（2,420,736 B）ができた |
| wic、Image、dtb ができる | 確認 | `.wic.bz2`、`.wic.bmap`、`Image-1-6.18.33+git0+6d012fbc35_95b85bebbe-...bin`、`bcm2710-rpi-zero-2.dtb` |
| 既定カーネルは 6.18.33 | 確認 | レシピ `linux-raspberrypi-1_6.18.33+git`、モジュールの版 `6.18.33-v8` |
| 既定では `bcm2710-rpi-cm0.dtb` を作らない | 確認 | deploy の dtb は `bcm2710-rpi-zero-2.dtb`、`hat_map.dtb`、`overlay_map.dtb` だけ |
| inittab に `remount,rw` 行がある | 確認 | rootfs の `/etc/inittab` 7 行目 `::sysinit:/bin/mount -o remount,rw /` |
| rcS が `rcS.d` と `rc5.d` を読む | 確認 | `/etc/init.d/rcS` 7 行目 `for i in /etc/rcS.d/S??* /etc/rc5.d/S??* ;do` |

B1・B2 でできた .ko は次の 16 個です。`powerfail_suo`、`cardputerzero-audio`、`gpio-forwarder`、`st7789v_m5stack`、`pwm_bl_m5stack`、`panel-mipi-dbi-m`、`m5ioe1`、`tca8418_keypad_m5stack`、`es8389_m5stack`、`simple-amplifier`、`bq27xxx_battery`、`bq27xxx_battery_i2c`、`bmi270_core`、`bmi270_i2c`、`bmc150_magn`、`bmc150_magn_bmi270`。dtbo は `cardputerzero-v5-overlay.dtbo`（9,550 B）、`bq27220_v5.dtbo`（626 B）、`bmi270_bmm150_overlay.dtbo`（873 B）です。`powerfail_suo.ko` には、パッチで加えた `cannot resolve %s for sync: %d` と `sync of %s failed: %d` が入っていました。

ほかに分かったことは次のとおりです。

- `core-image-minimal` の rootfs には `/etc/rcS.d` も `/lib/modules` もありませんでした。モジュールは既定では入りません。
- deploy に `grub-efi-bootaa64.efi`、`systemd-bootaa64.efi` などの EFI 用ファイルもできていました。MSD では使いません。
- モジュールは `.ko.xz` で圧縮されて入りました。Buildroot 版と同じ形式かは確かめていません。
- B2 の `.config` で要求と違ったのは `CONFIG_NODES_SHIFT=1` だけでした。`CONFIG_NUMA` が無効なので現れない項目です。`CONFIG_EROFS_FS` は fragment に `=y`（28 行目）と `is not set`（511 行目）の両方があり、後の無効が効いていました。`do_kernel_configcheck` はどちらも警告しませんでした。
- E の警告 3 件は、SSTATE_DIR の共有と、`gnu-config` と `yocto-kernel-cache` の取得がミラーに切り替わったことです。
- 使用量は作業ディレクトリ 42 GB、DL_DIR 8.1 GB、SSTATE_DIR 3.6 GB でした（E の後、`du`）。
- 負荷は 6 タスク × `-j 6` で、ロードアベレージが 14 前後になりました。

## 捨てた試行と経緯

- E-1: 1 秒で `PermissionError: [Errno 13] Permission denied: '/work/build'`。kas-container は `docker context show` が `rootless` のときだけ rootless 用の処理（所有者の変更）をします。この VM は `DOCKER_HOST` で接続しており、コンテキストは `default` でした。実行スクリプトで `DOCKER_HOST` を外し、`DOCKER_CONTEXT=rootless` を指定して直しました。
- B1-1: `bblayers.conf` に `/work/build/../meta-msd-probe` が入り、レイヤーが見つかりませんでした。kas は `path:` を作業ディレクトリ基準で解きますが、設定のディレクトリは `/repo` に読み取り専用で付きます。`url` も `path` も書かない（設定ファイル自身の場所を指す）形に直しました。
- B1-2: パッチは当たりましたが、`do_qa_patch` が `Missing Upstream-Status in patch [patch-status]` で止めました。Wrynose では致命的な QA です。写しのヘッダーに `Upstream-Status` を加えました。フェーズ2で移植するときはリポジトリのパッチにも必要です。
- B1-3: 加えた直後に同じエラーで止まりました。ホスト上の写しは oe-core の判定用の正規表現に合っていました。原因は特定できていません。設定を変えずに再実行した B1-4 は通りました。

## 結論

kas-container と rootless Docker で、仮置きの Wrynose 6.0.4 を使って `raspberrypi0-2w-64` の最小イメージと M5 の BSP をビルドできました。MSD のカーネル固定と `linux.fragment` を加えても通りました。系列の採用はまだ決めていません。今回はビルドが通るかだけを見ており、QEMU でも実機でも起動していません。

## 未確認の点

- イメージの起動（QEMU `raspi3ap`、実機）、モジュールの読み込み、overlay の適用。
- CM0 用の `bcm2710-rpi-cm0.dtb` を足したときのビルドと起動。
- Buildroot 版と同じ `.config` になるか（元にする defconfig が同じかは比べていません）。
- B1-3 の失敗の原因。
- Scarthgap 5.0 など、ほかの系列での結果（本リポジトリでは試していません）。

## ログ

ログはリポジトリに入れていません（大きなログはコミットしない方針）。上の手順で再生成でき、各ログの SHA-256 を下に記します。`b1.log` は B1-4 のログです。

| ファイル | SHA-256 |
|---|---|
| `logs/b1.log` | `c65050baf30326398f2df7ad5db533408d95f7905b6434c0e9b8dd71a184073f` |
| `logs/b1-try1.log` | `811791be95b292091601d9cfbd44c17a26ec012c929f0340fa0a6ec3c7a03ed0` |
| `logs/b1-try2.log` | `cebf9595073a43e77aa2aefff698229a1ade9cd7c29d823d9c49832a433fe469` |
| `logs/b1-try3.log` | `e95b642bec33c8b294b3a47eb32860353fdebee38f678a3aa3f3ffee78110aab` |
| `logs/b2.log` | `a5734b6882c4830602612cd69e2199409cc6354f0f8476794f3b4a63ee2cc09e` |
| `logs/e.log` | `faac4c26d3368aeea53909d55897bfb3169a9980c10aad7409941f20b80ebc37` |
| `logs/e-try1.log` | `eab2ddccf493bb408037fb4576580153b07995d141afc7fdddc3a270d2e9e052` |
