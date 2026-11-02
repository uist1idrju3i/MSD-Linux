# Buildroot 資産から Yocto への対応表

現行の Buildroot 資産を、Yocto のどの仕組みに移せるかを一つずつ調べました。確認日は 2026-11-02 です。Yocto 側の記述は oe-core wrynose `ae5a301`、meta-raspberrypi wrynose `9195883`、wic `610a61a`、meta-openembedded wrynose `c734c2c` のファイルで確かめました。本書は対応を示すだけで、レシピは書いていません。

## 1. defconfig の主な項目

| 現行（`configs/msd_cardputerzero_defconfig`） | Yocto での受け皿 | 注意点 |
|---|---|---|
| `BR2_aarch64`、`BR2_cortex_a53` | 独自 machine（仮称 `cardputerzero`）で `raspberrypi3-64` を基にする。`DEFAULTTUNE` は meta-raspberrypi と同じ `cortexa53-nocrypto` | meta-raspberrypi も RPi 3 系を nocrypto にしている【一次】 |
| Bootlin 外部ツールチェーン | Poky 内部ツールチェーン | [verification-and-ops.md](verification-and-ops.md) §3.1 |
| `BR2_FORTIFY_SOURCE_3`、`BR2_OPTIMIZE_S`、`BR2_ENABLE_LTO` | `lcl_maybe_fortify` の上書き、`FULL_OPTIMIZATION`、`lto.inc` | 同 §3.2。LTO の範囲は現行より狭い |
| `BR2_CCACHE` | `INHERIT += "ccache"`（`meta/classes/ccache.bbclass`） | 増分ビルドは主に sstate が担う【推測】 |
| `BR2_INIT_BUSYBOX`、`BR2_ROOTFS_DEVICE_CREATION_DYNAMIC_MDEV` | `INIT_MANAGER = "mdev-busybox"`（既定は `systemd`） | §3 の inittab と rcS の違いに注意 |
| `BR2_TARGET_GENERIC_HOSTNAME="msd"`、`ISSUE`、getty | `base-files` の hostname（既定は machine 名）、`/etc/issue` の bbappend、`SERIAL_CONSOLES` | |
| `BR2_LINUX_KERNEL_CUSTOM_TARBALL`（`b3495ea`、6.18.59） | `linux-raspberrypi_6.18.bbappend` で `SRCREV_machine` と `LINUX_VERSION` を上書き | [releases-and-layers.md](releases-and-layers.md) §3.2 |
| `BR2_LINUX_KERNEL_DEFCONFIG="bcm2711"` | `raspberrypi3-64` の `KBUILD_DEFCONFIG` が同じ `bcm2711_defconfig` | |
| `BR2_LINUX_KERNEL_INTREE_DTS_NAME`（cm0、3-b） | machine の `RPI_KERNEL_DEVICETREE` に `broadcom/bcm2710-rpi-cm0.dtb` と `broadcom/bcm2710-rpi-3-b.dtb` | 既定の一覧に cm0 はない |
| `BR2_PACKAGE_RPI_FIRMWARE_VARIANT_PI_CD`、`BOOTCODE_BIN` | `rpi-bootfiles` が全ファイルを deploy する。wic の `IMAGE_BOOT_FILES` で `start_cd.elf`・`fixup_cd.dat`・`bootcode.bin` を選ぶ | |
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_*` | `linux-firmware-rpidistro-*` | Synaptics 分は `LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"` が必要。CM0 の無線チップに合う分割パッケージは未確認 |
| `BR2_GLOBAL_PATCH_DIR`（`board/cardputerzero/patches`） | 中身は `linux/linux.hash`（カーネル tarball の sha256）だけ。Yocto では `SRCREV` か `SRC_URI[sha256sum]` が同じ役割を持つ | 依頼文にあった「パッチの振り分け」は不要。パッチは `package/m5stack-cardputerzero/0001-powerfail-sync-and-notify.patch` だけで、§4 のレシピの `SRC_URI` に入れる |

## 2. イメージに入れるもの

現行の `post-build.sh` は、実行時に必要なコマンドの一覧（`required_target_commands`）を検査しています。依頼文の一覧（busybox、kbd、v4l-utils、kmod、e2fsprogs、openssl、util-linux partx）に、次のものを加える必要があります。

| 必要なコマンド | 現行の提供元 | Yocto の候補 |
|---|---|---|
| `sfdisk` | `BR2_PACKAGE_UTIL_LINUX_BINARIES` | util-linux の分割パッケージ（`util_linux_binpackages` が実行ファイルごとに分ける）【一次: 分割の仕組み、推測: パッケージ名】 |
| `partx` | `BR2_PACKAGE_UTIL_LINUX_PARTX` | 同上（`--enable-partx` で構成）【一次】 |
| `fsck.ext4`、`resize2fs`、`mkfs.ext4` | e2fsprogs | e2fsprogs の分割パッケージ【推測: パッケージ名】 |
| `v4l2-ctl`、`media-ctl`、`ir-keytable`、`ir-ctl` | libv4l の utils | meta-oe の `v4l-utils_1.32.0.bb` は `media-ctl`・`ir-keytable`・`rc-keymaps`・`qv4l2`・`qvidcap` を分けるが、`v4l2-ctl` と `ir-ctl` は本体（`${bindir}` 全体）に残る【一次】 |
| `openssl` | `BR2_PACKAGE_LIBOPENSSL_BIN` | `openssl-bin`【推測: パッケージ名】 |
| `loadkeys` | kbd | kbd の分割パッケージ【推測】。現行は M5 のキーマップ以外のキーマップ・フォントを `post-build.sh` で消している |

- v4l-utils の本体に残る不要なツール（`cec-*`、`v4l2-compliance` など）は、現行と同じく rootfs の後処理で消すことになります【推測】。

## 3. init と rootfs-overlay

- oe-core の BusyBox の `inittab` には `::sysinit:/bin/mount -o remount,rw /` があります【一次】。現行は `BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW` を無効にしており、dm-verity の検討では、読み取り専用の dm デバイスへの remount が `-EACCES` になることを記録しています（[2026-10-21-qemu-dm-verity.md](../../experiments/2026-10-21-qemu-dm-verity.md)）。移行では `busybox-inittab` の bbappend で、この行を除く必要があります【推測】。
- oe-core の BusyBox の `rcS` は `/etc/rcS.d/S??*` と `/etc/rc5.d/S??*` を順に起動します【一次】。現行の `S01msd-watchdog` から `S99msd-health` までは `/etc/init.d/` に直接置いており、そのままでは起動されません。`update-rc.d` クラス（`INITSCRIPT_NAME`・`INITSCRIPT_PARAMS`）でリンクを作るか、`rcS` を差し替えます【推測】。
- 現行の init スクリプトは、`rcK` が `stop` で呼ぶことに備えて、起動専用の書き方にしています（`case "${1:-start}"`）。oe-core の `inittab` も `::shutdown:/etc/init.d/rcK` を持つため、この備えは移行後も要ります【一次: inittab】。
- `rootfs-overlay` の中身（init スクリプト 8 本、`fstab`、`default/seedrng`、`libexec/msd/` の 2 本、`sbin/msd-*` の 3 本）は、役割ごとのレシピ（例: `msd-update`、`msd-hwinfo`、`msd-data-grow`、`msd-initscripts`）に分けるのが自然です【推測】。`msd-update` には `tests/msd-update/` のホスト試験があり、レシピの `do_install` で同じファイルを入れれば試験を流用できます。
- `read-only-rootfs` の image feature は `read_only_rootfs_hook` を加えます【一次】。現行の `/etc` overlay（`S03msd-etc-overlay`）と重なるため、どちらを使うかは移植時に決めます。oe-core には `overlayfs-etc.bbclass` もあります【一次】。

## 4. M5Stack の BSP（`package/m5stack-cardputerzero`）

| 現行 | Yocto での受け皿 |
|---|---|
| `SITE_METHOD = local`（`vendor/m5stack-linux-dtoverlays`）と `git rev-parse` による版 | `SRC_URI` に GitHub の git と `SRCREV`（サブモジュールと同じ SHA）を書く。開発中は `externalsrc` でサブモジュールを直接使う方法もある【推測】 |
| `kernel-module`（8 つのサブディレクトリ） | `inherit module`。複数ディレクトリは `do_compile` と `do_install` で順に回す【推測】 |
| `KCFLAGS="... -DCONFIG_CARDPUTERO_V0_5=1"`、`CONFIG_BMI270=m` など | `EXTRA_OEMAKE` に同じ値を渡す【推測】 |
| post-rsync hook でのパッチ適用 | `SRC_URI += "file://0001-powerfail-sync-and-notify.patch"`。git から取得すれば `do_patch` が走るため、hook は不要【推測】。`externalsrc` では `SRCTREECOVEREDTASKS`（既定 `do_patch do_unpack do_fetch`）が外れ、パッチが当たらない【一次: externalsrc.bbclass L28】 |
| `dtc -@` による overlay 3 個 | `dtc-native` を使って `do_compile` で作り、`do_deploy` で deploy する。boot パーティションへは `IMAGE_BOOT_FILES` か `RPI_SDIMG_EXTRA_DEPENDS` で入れる【一次: 変数の存在、推測: 組み方】 |
| ファームウェア 2 個とキーマップ | `do_install` で `/lib/firmware/` と `/usr/share/keymaps/` へ。ライセンスは [verification-and-ops.md](verification-and-ops.md) §4.2 |
| `sign-modules.sh`（post-build） | 外部モジュールの署名は、カーネルの署名鍵を共有する仕組みを別に用意する。oe-core の kernel・module クラスに、署名の専用設定は見当たらない【未確認】 |

この節の受け皿が実際にビルドできるかは、VM での構築試験で確かめます。

## 5. 後処理スクリプト

### 5.1 `post-build.sh` → `ROOTFS_POSTPROCESS_COMMAND`

| 現行の処理 | Yocto での扱い |
|---|---|
| 必要コマンドの検査 | rootfs の後処理関数で同じ検査をする【推測】 |
| seedrng の S01 → S05 改名 | Buildroot の seedrng パッケージ固有の処理。Yocto では `INITSCRIPT_PARAMS` で順序を決める【推測】 |
| kbd・v4l の不要ファイル削除 | §2 のとおり、パッケージ分割で減らし、残りを後処理で消す |
| mdev 規則の挿入と重複検査 | `busybox` の bbappend で `mdev.conf` を差し替える（oe-core に `files/mdev.conf` がある）【一次: ファイル、推測: 方法】 |
| BusyBox の必須オプション検査 | busybox の `.cfg` fragment（`merge_config.sh` で結合）と、後処理での検査【一次: busybox.inc L149】 |
| 更新鍵の埋め込み、更新版数 | 専用レシピ。`MSD_UPDATE_SIGNING_KEY` は `BB_ENV_PASSTHROUGH_ADDITIONS` で渡すことになる。鍵がビルドのハッシュに入らないようにする工夫が要る【推測】 |
| `mksquashfs -sort` の差し込み | `oe_mksquashfs` が `EXTRA_IMAGECMD` を引数に足すため、`EXTRA_IMAGECMD:squashfs-zst` に `-sort` を書けば wrapper が不要になる【一次: image_types.bbclass、推測: `@KVER@` の置換方法】 |

### 5.2 `post-image.sh` → `IMAGE_POSTPROCESS_COMMAND` と wic

| 現行の処理 | Yocto での扱い |
|---|---|
| `pigz -11 -n` で `kernel8.img` を作り、`gunzip -c` と `cmp` で確認 | カーネルの `do_deploy:append` か、イメージの後処理【推測】 |
| bootsel と boot の staging、`check-dt-overlays.sh` | wic の `bootimg_partition` を二つ使い、§6 の label 別 `IMAGE_BOOT_FILES` で中身を分ける。検査は後処理に残す |
| genimage | §6 の `.wks` |
| 更新バンドル（manifest、Ed25519 署名、tar） | イメージ完了後に動く処理（`IMAGE_POSTPROCESS_COMMAND` か専用のタスク）【推測】 |

## 6. ルートファイルシステムとパーティション

### 6.1 SquashFS

- 型名は `squashfs-zst` です（依頼文の `squashfs-zstd` ではありません）。実行されるのは `mksquashfs … -noappend -comp zstd ${EXTRA_IMAGECMD}` で、`SOURCE_DATE_EPOCH` を rootfs の時刻に合わせます【一次】。
- 現行の `BR2_TARGET_ROOTFS_SQUASHFS_EXTREME_COMP` は、zstd のとき `-Xcompression-level 22` を足します。Buildroot は `-processors`、`-b`（ブロック長）、既定の 4K パディングも指定します【一次: Buildroot の fs/squashfs】。同じ結果にするには `EXTRA_IMAGECMD:squashfs-zst = "-Xcompression-level 22 -b <現行の値> -sort <file>"` のように書きます【推測】。
- 同じ入力から同じイメージになるか（再現性）と、現行とのサイズ差は、構築試験で比べます。

### 6.2 genimage → wks

| genimage（現行） | wic での書き方 | 根拠 |
|---|---|---|
| `hdimage { align = 4M; partition-table-type = "mbr"; extended-partition = 4 }` | `bootloader --ptable msdos`。各 `part` に `--align 4096`（単位は KiB）。msdos で 5 個以上のときは wic が拡張パーティションを自動で作る | 【一次】ksparser の `--align`、help の単位、direct.py L433-L496 |
| p1 bootsel（vfat 16M、`autoboot.txt` と `bootcode.bin`、bootable） | `part --source bootimg_partition --fstype vfat --label bootsel --active --fixed-size 16M` と `IMAGE_BOOT_FILES_label-bootsel` | 【一次】bootimg_partition.py L54 の `_label-%s` |
| p2・p3 boot-a / boot-b（vfat 64M、同じ中身） | 同じ書き方で label を分ける（`IMAGE_BOOT_FILES_label-boot-a` など） | 同上 |
| p5・p6 rootfs-a / rootfs-b（squashfs 256M） | `part --source rawcopy --sourceparams="file=<イメージ名>.squashfs-zst" --fixed-size 256M` | 【一次】rawcopy の `file` 引数【推測】書き方 |
| p7 data（ext4 64M、`-b 4096`、空） | `part --fstype ext4 --label data --fixed-size 64M --mkfs-extraopts "-b 4096"`。`--source` なしでも size があれば作れる | 【一次】ksparser の `--mkfs-extraopts`、partition.py L199-L205 |

- meta-raspberrypi の既定の wks（`files/wic/sdimage-raspberrypi.wks`）は、boot と rootfs の 2 個を `--align 4096` で並べるだけです【一次】。MSD の 7 区画は独自の wks になります。
- `check-image-layout.sh` は、現行と同じ配置かを機械的に比べる検査として流用できます【推測】。

### 6.3 `config.txt` と `cmdline`

- 現行の `config.txt` は `[boot_partition=2]`・`[boot_partition=3]` の条件節で cmdline を切り替えます。`rpi-config` は Evilpaul/RPi-config の雛形を `sed` で書き換える方式で、条件節の順序までは制御できません【一次: レシピ、推測: 制約】。`rpi-config` の bbappend で、雛形を MSD の `config.txt` に丸ごと置き換えるのが確実です【推測】。
- `rpi-cmdline` は `cmdline.txt` を一つだけ作ります【一次】。`cmdline_rootfs_a.txt`・`cmdline_rootfs_b.txt` は自前のレシピで deploy します【推測】。
- `autoboot.txt` は bootsel 区画にだけ入れるため、これも自前のレシピで deploy し、`IMAGE_BOOT_FILES_label-bootsel` で選びます【推測】。

## 7. カーネルと BusyBox の fragment

- `board/cardputerzero/linux.fragment`（544 行）は、bbappend の `SRC_URI += "file://msd.cfg"` で渡せます。`linux-yocto.inc` の fragment 機構が結合します【一次】。依頼文の `DELTA_KERNEL_DEFCONFIG` という変数は oe-core にありません【一次: oe-core の meta を検索した結果】。
- 結合後に消えた設定は `do_kernel_configcheck` が報告します。報告の細かさは `KCONF_AUDIT_LEVEL`（既定 1）と `KCONF_BSP_AUDIT_LEVEL`（既定 0）で変わります【一次: kernel-yocto.bbclass L26-L27】。現行の `check-kernel-fragment.sh` に当たる検査で、両方を使えば二重の確認になります【推測】。
- `board/cardputerzero/busybox.fragment`（4 行）は busybox の bbappend の `.cfg` にします【一次】。

## 出典（確認日 2026-11-02）

- https://github.com/openembedded/openembedded-core/tree/ae5a301091f5b0574ea7444aab40b309b6d9f3f2 【一次】`meta/classes-recipe/image_types.bbclass`、`image.bbclass`、`rootfs-postcommands.bbclass`、`kernel-yocto.bbclass`、`overlayfs-etc.bbclass`、`meta/classes/externalsrc.bbclass`、`meta/recipes-core/busybox/`（`busybox.inc`、`files/inittab`、`files/rcS`、`files/mdev.conf`）、`meta/recipes-core/util-linux/util-linux_2.41.6.bb`、`meta/conf/distro/include/init-manager-mdev-busybox.inc`、`meta/conf/distro/defaultsetup.conf`、`meta/recipes-core/base-files/`
- https://git.yoctoproject.org/wic （コミット `610a61a25e5fad0b62abd19d60f0b0e210b1df34`）【一次】`src/wic/ksparser.py`、`help.py`、`partition.py`、`plugins/imager/direct.py`、`plugins/source/bootimg_partition.py`、`rawcopy.py`。Web 表示はこの VM から 403 のため、git で取得して確認した
- https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d 【一次】`conf/machine/`、`recipes-bsp/bootfiles/`、`classes/sdcard_image-rpi.bbclass`、`files/wic/sdimage-raspberrypi.wks`
- https://github.com/openembedded/meta-openembedded/blob/c734c2cb9713dbd6d50697a9f6c25ebdf3ae589e/meta-oe/recipes-multimedia/v4l2apps/v4l-utils_1.32.0.bb 【一次】v4l-utils のパッケージ分割
- https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/fs/squashfs/Config.in 【一次】extreme compression の中身
- https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/fs/squashfs/squashfs.mk 【一次】mksquashfs の引数
