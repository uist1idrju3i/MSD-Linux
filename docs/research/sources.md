# 出典 URL と取得記録

- 取得日は全て 2026-10-18 (JST) です。各表には公開 URL、取得日、HTTP 結果、確認度を記載しています。
- 「確認済み」は、URL が HTTP 200 で、その内容または同一コミットの公開ソースで該当事項を確認したことを指します。HTTP 200 でも内容を読んでいない場合は「到達のみ」と記載しています。
- 二次情報(検索要約・SNS)は確認度欄に『二次』と付けています。
- 出典一覧の短縮 ID は、この文書内で出典を参照するためのものです。

## 分割した出典記録

- [出典一覧と取得記録の読み方](sources-catalog.md)
- [本文を確認した URL](sources-verified-urls.md)
- [URL への到達結果（205 件）](sources-url-reachability.md)
- [URL への到達結果（205 件）の続き](sources-url-reachability-more.md)
- [その他の URL の到達結果（59 件）](sources-other-url-results.md)
- [追加 URL の取得結果（19 件）](sources-additional-url-results.md)

## 意図的に含めないもの

| 対象 | 理由 |
|---|---|
| 特定の外部製品を比較した記述 | 指定された調査範囲外の内容として除外 |
| 商標・候補名に関する個別情報 | 権利の個別照会と候補比較は対象外とし、関連 URL は掲載しない。URL 取得結果で残差が増えたものは、取得区分別に 4 件・2 件を含め、いずれもこのカテゴリとして意図的に除外する |
| 調査時の検索式・一時的な検証コマンド | 個別の作業手順は公開資料に基づく事実ではないため収録しない |
| 内部管理情報（ID、版履歴、監査記録、私的ファイル名、作業用パスなど） | 公開資料に基づく記録に不要な情報として除外し、個別の ID やファイル名は列挙しない |
| URL 抽出時の句読点による差分 2 件 | URL 直後の全角句点・括弧が抽出結果に含まれる差分です。正規の URL は本書に掲載済みで、出典の欠落ではありません |

### ストレージ・セキュリティ・機能対応表で追加した出典

次の URL は本文の新規記述に使った公開資料です。短い英文は取得した資料からの抜粋です。社内の計測ファイル名や作業用パスは本文・表に記載していません。

| URL | HTTP / 取得状況 | 短い抜粋 | 確度 |
|---|---|---|---|
| https://github.com/pengutronix/genimage/blob/v20/README.rst | 200・本文確認 | “the final offset rounded up to the partition's `align` value” | 【一次】 |
| https://docs.kernel.org/admin-guide/ext4.html | 200・本文確認 | “All data are committed into the journal prior to being written into the main file system.” | 【一次】 |
| https://man7.org/linux/man-pages/man8/mke2fs.8.html | 200・本文確認 | “Configure the file system for a RAID array with stride-size file system blocks” | 【一次】 |
| https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/ | 200・本文確認 | “the number of 4KB read/write commands can be executed per second” | 【一次】 |
| https://www.sdcard.org/developers/sd-standard-overview/speed-class/ | 200・本文確認 | “All speed class types assures minimum sequential card access performance” | 【一次】 |
| https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797 | 200・本文確認 | `MMC_DEV_ATTR(preferred_erase_size` | 【一次】 |
| https://lwn.net/Articles/428584/ | 200・本文確認 | “reverse engineering based on timing data” | 【二次】 |
| https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md | 200・本文確認 | “how secure-boot works on a Raspberry Pi 4 (or newer)” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc | 200・本文確認 | “check primary SD for `bootcode.bin`” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc | 200・本文確認 | “All Raspberry Pi models support `tryboot`” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271 | 200・本文確認 | “enables a hardware watchdog timer that is handed over to the operating system” | 【一次】 |
| https://docs.kernel.org/admin-guide/device-mapper/verity.html | 200・本文確認 | “This hash should be trusted as there is no other authenticity beyond this point.” | 【一次】 |
| https://docs.kernel.org/admin-guide/sysctl/kernel.html | 200・本文確認 | `dmesg_restrict` / `kptr_restrict` / `unprivileged_bpf_disabled` | 【一次】 |
| https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token= | 200・PDF 本文確認 | “The optional Cryptography Extension is not included in the base product.” | 【一次】 |
| https://docs.m5stack.com/en/CardputerZero | 200・本文確認 | “GL852G-OHY60 USB 2.0 Hub / SR9900A USB 2.0 to Ethernet chip” | 【一次】 |
| https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 200・PDF 本文確認 | “The battery charging has a separate input path. Input priority: USB IN > EXT. IN” | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/etc/fstab | 200・本文確認 | `/dev/mmcblk0p7 /data ext4 noauto,noatime,data=journal,errors=remount-ro 0 2` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/usr/sbin/msd-update | 200・本文確認 | `sha256sum -c manifest` / `rootfs read-back SHA-256 mismatch` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog | 200・本文確認 | `watchdog -T 15 -t 5 /dev/watchdog` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/linux.fragment | 200・本文確認 | `CONFIG_BCM2835_WDT=y` / `# CONFIG_MEDIA_SUPPORT is not set` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/config.txt | 200・本文確認 | `dtoverlay=cardputerzero-v5-overlay` / `dtoverlay=bq27220_v5` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/package/m5stack-cardputerzero/m5stack-cardputerzero.mk | 200・本文確認 | `modules/st7789v-1.0` / `modules/tca8418-1.0` / `modules/es8389-1.0` | 【一次】 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115 | 200・本文確認 | `handle_sysrq('u')` / `// handle_sysrq('s');` | 【一次】 |
| https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327 | CI artifact 取得済み | `p1=1, p2=32769, p3=163841, p4=294913, p5=294914, p6=819203, p7=1343492` | 【実測】 |
| https://man7.org/linux/man-pages/man5/mke2fs.conf.5.html | 200・本文確認 | `small = { blocksize = 1024` | 【一次】 |
| https://man7.org/linux/man-pages/man8/mke2fs.8.html | 200・本文確認 | “heuristically determined by the file system size and the expected usage” | 【一次】 |
| https://kspp.github.io/Recommended_Settings | 200・本文確認 | `CONFIG_STACKPROTECTOR_STRONG=y` / `CONFIG_HARDENED_USERCOPY=y` | 【一次】 |
| https://documentation-service.arm.com/static/5e9075f9c8052b1608761519?token= | 本文確認 | “The Cortex-A53 processor implements the ARMv8-A architecture.” | 【一次】 |
| https://support.arm.com/documentation/102433/0200/Return-oriented-programming | 本文確認 | Armv8.3-A で pointer authentication を導入 | 【一次】 |
| https://developer.arm.com/documentation/109697/latest/Feature-descriptions/The-Armv8-5-architecture-extension | 本文確認 | `FEAT_BTI` は Armv8.4-A で optional | 【一次】 |
| https://github.com/raspberrypi/firmware/issues/694 | 本文確認 | 試験用 firmware が `/chosen/kaslr-seed` を 8 byte の乱数として追加したとの記録 | 【一次・履歴】 |
| https://github.com/raspberrypi/firmware/issues/1595 | 本文確認 | “There is a new firmware available ... that adds `/chosen/rng-seed`.” | 【一次・履歴】 |
| https://github.com/raspberrypi/rpi-eeprom/commit/cbd599e30dd3a8e7bbc7646364f3d3907f3027e0 | 本文確認 | Pi 5 の `kaslr-seed` / `rng-seed` が正しい entropy source を使うよう修正 | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/os/graphics-utilities.adoc | 本文確認 | `0x10000` は過去の undervoltage、`0x80000` は過去の soft temperature limit | 【一次】 |

### 割り当て単位・小さいファイル調査（2026-10-19）

| 項目 | 版・日付 | URL | 短い抜粋 | 確認度 |
|---|---|---|---|---|
| e2fsprogs 最新版 | 1.47.4、2026-03-06 | https://github.com/tytso/e2fsprogs/releases/tag/v1.47.4 | “e2fsprogs 1.47.4” / “Mar 6, 2026” | 【一次】 |
| mke2fs の既定と ext4 profile | e2fsprogs 1.47.4 | https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in | `[defaults] blocksize = 4096` / `small { blocksize = 1024` / `orphan_file` | 【一次】 |
| small profile の比較 | e2fsprogs 1.46.5／1.47.4 | https://github.com/tytso/e2fsprogs/blob/v1.46.5/misc/mke2fs.conf.in<br>https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in | 両タグで `small` は `blocksize = 1024`、`inode_ratio = 4096` | 【一次】 |
| mke2fs.conf のサイズ型の説明 | e2fsprogs upstream、issue #74 | https://github.com/tytso/e2fsprogs/issues/74 | small は 3–512 MiB、floppy は 3 MiB 未満という maintainer の説明 | 【一次】 |
| Buildroot package | 2026.08 | https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/e2fsprogs/e2fsprogs.mk | `E2FSPROGS_VERSION = 1.47.4` | 【一次】 |
| mke2fs の blocksize 選択 | mke2fs(8)、2026-10-19 取得 | https://man7.org/linux/man-pages/man8/mke2fs.8.html | “heuristically determined by the file system size and the expected usage” | 【一次】 |
| genimage の ext4 引数 | v20 | https://github.com/pengutronix/genimage/blob/v20/image-ext2.c | `const char *extraargs = cfg_getstr` / `usage_type` があれば `-T` を付加 | 【一次】 |
| ext4 blocksize／inline data／bigalloc／orphan file | docs.kernel.org 現行ページ、2026-10-19 取得 | https://docs.kernel.org/filesystems/ext4/ | “Blocks can range in size from 1KiB to 64KiB” / “Bigalloc” / “Inline Data” / “Orphan file” | 【一次】 |
| ext4 inline-data 対応 | e2fsprogs 1.43、2016-05-17 | https://github.com/tytso/e2fsprogs/blob/v1.43/RELEASE-NOTES | “Add support for ... inline data” | 【一次】 |
| dosfstools の FAT cluster 選択 | 4.2 | https://github.com/dosfstools/dosfstools/blob/v4.2/src/mkfs.fat.c | “fs size <= 260M: 0.5k clusters” / FAT32 cluster-size 条件表 | 【一次】 |
| mkfs.fat の option／内部整列 | dosfstools 4.2 man page | https://man.cgr.dev/os/dosfstools/4.2-r46/man8/mkfs.fat.8.md | “align all the data structures to cluster size”; `-s`, `-S`, `--offset` | 【一次】 |
| genimage vfat handler | v20 | https://github.com/pengutronix/genimage/blob/v20/image-vfat.c | `mkdosfs` option と `extraargs` を取得して formatter に渡す | 【一次】 |
| Microsoft exFAT specification | 現行公開ページ、2026-10-19 取得 | https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification | cluster の最大値は 32 MiB。default-size table は見つからず | 【一次】【未確認】 |
| SD Association Formatter | 公開 FAQ／解説、2026-10-19 取得 | https://www.sdcard.org/downloads/formatter/faq/<br>https://www.sdcard.org/press/thoughtleadership/the-sd-memory-card-formatterhow-this-handy-tool-solves-your-memory-card-formatting-needs/ | formatter は容量に応じ FAT／exFAT を選び、internal flash boundary に合わせる説明 | 【一次】 |
| SD Association 仕様 PDF | Part 1、2026-10-19 取得 | PDF URL は HTTP 403 | SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 | 【未確認】 |
| exfatprogs の default cluster／boundary-align | 1.4.3、2026-08-14 | https://github.com/exfatprogs/exfatprogs/releases/tag/1.4.3<br>https://github.com/exfatprogs/exfatprogs/blob/1.4.3/lib/libexfat.c<br>https://github.com/exfatprogs/exfatprogs/blob/1.4.3/man/mkfs.exfat.8.in | cluster default は volume size により選択。`--boundary-align` は FAT／cluster heap の境界を指定 | 【一次】 |
| SquashFS tools | 4.7.5、2026-03-01 | https://github.com/plougher/squashfs-tools/releases/tag/4.7.5<br>https://github.com/plougher/squashfs-tools/blob/4.7.5/README.md | `-b`、fragment、`-no-fragments`、`-always-use-fragments` | 【一次】 |
| EROFS tools | 1.9.4、2026-08-19 | https://github.com/erofs/erofs-utils/blob/v1.9.4/ChangeLog<br>https://erofs.docs.kernel.org/en/latest/mkfs.html | “erofs-utils 1.9.4” / `ztailpacking`／fragments | 【一次】 |
| F2FS small-file handling | docs.kernel.org 現行ページ、2026-10-19 取得 | https://docs.kernel.org/filesystems/f2fs.html | inline data／inline dentry を説明。kernel tag はページ上で未確認 | 【一次】【未確認】 |
| SD small-write 例 | LWN、2011-01-27 | https://lwn.net/Articles/428584/ | “small writes were slower than aligned larger writes” | 【二次】 |

### SoC・圧縮・最適化・シミュレーターの出典

この節は 2026-10-19 に確認しました。release tag がないページは取得日を記録し、固定 revision ではなく取得時点の公開資料として扱います。

| 項目 | 版・日付 | URL | 確認した抜粋・事実 | 信頼度 |
|---|---|---|---|---|
| CM0 | datasheet Release 3、2026-07-08 | https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf | 「Compute Module Zero」Release 3 | 【一次】 |
| CardputerZero | 2026-10-19 取得 | https://docs.m5stack.com/en/CardputerZero | “Quad-core Cortex-A53 @ 1 GHz”; “512 MB LPDDR2” | 【一次・製品資料】 |
| Cortex-A53 | TRM r0p4 | https://support.arm.com/documentation/ddi0500/j/Introduction/Implementation-options | L1/L2 実装範囲、SIMD/FP と暗号拡張は optional | 【一次】 |
| Raspberry Pi kernel image format | documentation commit `ddea98e98dafe9419feb4fd82710c2fbdef7dc44` | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | arm64 image は非圧縮または gzip archive | 【一次】 |
| arm64 boot protocol | Linux v6.18.57 | https://github.com/torvalds/linux/blob/v6.18.57/Documentation/arch/arm64/booting.rst | arm64 Image の bootloader 要件 | 【一次】 |
| Buildroot 選択版 Bootlin toolchain | stable 2025.08-1 / GCC 14.3.0 | https://toolchains.bootlin.com/releases_aarch64.html | AArch64 glibc stable 2025.08-1 は GCC 14.3.0 | 【一次】 |
| Bootlin 最新 stable toolchain | 2026.08-1 / GCC 15.3.0 | https://toolchains.bootlin.com/releases_aarch64.html | 最新 stable は 2026.08-1 | 【一次】 |
| GCC 最適化 / AArch64 | GCC 14.3.0 | https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Optimize-Options.html<br>https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/AArch64-Options.html | `-Os`, `-Oz`, `-O2`, A53 tuning / errata options | 【一次】 |
| GCC PGO / instrumentation | GCC 14.3.0 | https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Instrumentation-Options.html | `-fprofile-generate` / `-fprofile-use` / `-fprofile-update` / `GCOV_PREFIX` | 【一次】 |
| Buildroot optimization / LTO | Buildroot 2026.08 commit `d5180309b1b66ef3b8eaccca70ad69be8e0729a1` | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/Config.in | `BR2_OPTIMIZE_2` default and LTO option | 【一次】 |
| SquashFS ARM64 BCJ | squashfs-tools 4.7.5 | https://github.com/plougher/squashfs-tools/blob/4.7.5/squashfs-tools/xz_wrapper_extended.c | source registers `"arm64"` BCJ filter | 【一次】 |
| XZ | XZ Utils 5.8.3 | https://github.com/tukaani-project/xz/releases/tag/v5.8.3 | release 5.8.3; ARM64 BCJ filter | 【一次】 |
| Linux kernel AutoFDO / Propeller / LTO | Linux v6.18.57 | https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/autofdo.rst<br>https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/propeller.rst<br>https://github.com/torvalds/linux/blob/v6.18.57/arch/Kconfig | arm64 sampling / Clang requirements / `LTO_CLANG` | 【一次】 |
| AutoFDO profile tools | commit `f95d1a170dfe24ec5ce4117aa4b0f6d836841703`、2026-09-30 | https://github.com/google/autofdo/tree/f95d1a170dfe24ec5ce4117aa4b0f6d836841703 | `create_gcov` toolset と GCC AutoFDO の手順 | 【一次】 |
| Kernel AutoFDO / Propeller merge | Linux 6.13、2024-11-30 報道 | https://www.phoronix.com/news/AutoFDO-Propeller-Linux-6.13 | upstream merge を報道 | 【二次】 |
| Clang kernel instrumentation PGO | 2021-06-03 | https://www.phoronix.com/news/Clang-PGO-Linux-Shot-Down | Linux 5.14 patch の撤回を報道 | 【二次】 |
| Zstandard benchmark | zstd 1.5.4、PTS result 2024-08-28 | https://mail.openbenchmarking.org/result/2408281-BOMM-240826011%26gru%26sro%26export=html | Pi 3B+ / A53、level 19 展開 67.9 MB/s | 【二次】 |
| LZ4 benchmark | lzbench 1.7.3、LZ4 1.8.3 | https://github.com/lz4/lz4/pull/713 | 投稿された A53 測定、Silesia `dickens` 展開 448 MB/s。board / clock 未記載 | 【二次】 |
| QEMU 最新 release | 11.1.2、2026-09-28 | https://github.com/qemu/qemu/releases/tag/v11.1.2 | latest stable release | 【一次】 |
| QEMU Raspberry Pi models | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/system/arm/raspi.html | DMA、SD/MMC host、MBOX、SPI、I2C と未実装 device | 【一次】 |
| QEMU Raspberry Pi model changes | QEMU 9.0 | https://wiki.qemu.org/ChangeLog/9.0 | `raspi4b`、SPI / BSC I2C 支援 | 【一次】 |
| QEMU Raspberry Pi models 6.2 | QEMU 6.2.0 | https://qemu.readthedocs.io/en/v6.2.0/system/arm/raspi.html | `raspi3b` model docs | 【一次】 |
| QEMU TCG plugins | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/devel/tcg-plugins.html | plugin callback、instruction / translation-block instrumentation | 【一次】 |
| QEMU cache plugin | QEMU v11.1.2 source | https://github.com/qemu/qemu/blob/v11.1.2/contrib/plugins/cache.c | guest cache hit/miss counter | 【一次】 |
| QEMU `-icount` | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/system/invocation.html | instruction-count virtual clock | 【一次】 |
| gem5 latest release | 25.1.0.1、2026-04-21 | https://github.com/gem5/gem5/releases/tag/v25.1.0.1 | hotfix release。取得時点で 26.0 release 未確認 | 【一次】 |
| gem5 HPI | gem5 commit `c8222cc6` | https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/HPI.py | “representative of a modern in-order ARMv8-A implementation” | 【一次】 |
| gem5 ex5_LITTLE | gem5 commit `c8222cc6` | https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/ex5_LITTLE.py | Cortex-A7 based model | 【一次】 |
| Arm FVP | Fast Models 11.32、2026-07-30 | https://support.arm.com/tools-and-software/fixed-virtual-platforms/arm-architecture-fvps | Architecture FVP / Base RevC release list。license entitlement 未確認 | 【一次】【未確認】 |
| Renode | 1.17.0、2026-09-07 | https://github.com/renode/renode/releases/tag/v1.17.0 | release page と platform tree。BCM2835/2837 model は未発見 | 【一次】【未確認】 |
| Raspberry Pi Zero 2 W | 2026-10-19 取得 | https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ | RP3A0、quad-core 1 GHz A53、512 MB LPDDR2 | 【一次・製品資料】 |
