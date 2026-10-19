# SoC・メモリ・SD 特性と圧縮方式

調査日: 2026-10-19。製品仕様と公開ベンチマークは記載した版・条件の範囲で扱い、実機の周波数、SD速度、性能差は別途測定します。外部プロジェクトの値は本リポジトリでは試していません。

## CM0 と CardputerZero

| 項目 | 確認結果 |
|---|---|
| SoC / CPU | CardputerZero の製品資料は RP3A0（BCM2837）、Cortex-A53 4コア、最大 1 GHz、ARMv8-A と記載します。【一次】CM0 datasheet Release 3（2026-07-08）と M5Stack CardputerZero 製品ページ。 |
| 起動時周波数 | 製品資料の 1 GHz は定格値です。`config.txt` は `arm_boost=1` を設定しますが、CM0 の起動中・負荷中の実クロックは【未確認】です。 |
| L1 / L2 | Cortex-A53 TRM r0p4 は L1 I/D を各 8/16/32/64 KiB、共有 L2 を任意の 128 KiB–2 MiB とします。BCM2837/RP3A0 の実装値は同資料では特定できず【未確認】です。【一次】 |
| NEON / FP・暗号拡張 | 同 TRM では Advanced SIMD/FP と Cryptography Extension は実装時選択です。BCM2837 での搭載有無は【未確認】です。 |
| GPU / ブート | BCM2837 の GPU は VideoCore IV です。Raspberry Pi firmware の `start_file` は VideoCore GPU に渡す firmware、`fixup_file` は GPU メモリ split に合わせた修正ファイルです。【一次】firmware は Linux 起動前に動きます。 |
| RAM | CM0 datasheet Release 3 は 512 MB LPDDR2 と記載します。RAM クロック、バス幅、理論帯域は公開資料で確認できず【未確認】です。DDR2 とは記載しません。 |
| GPU memory split | 本リポジトリの `config.txt` に `gpu_mem` はありません。Raspberry Pi の boot docs は cut-down firmware に `gpu_mem=16` を要求しますが、CM0 での実際の split は【未確認】です。 |
| microSD host | CardputerZero 資料と CM0 datasheet から、CM0 固有の最大クロック、実配線の bus 幅、UHS / 1.8 V signal 対応を確定できませんでした。【未確認】Pi 4/5 の SD 規格値を CM0 に流用しません。実機の読込速度も未測定です。 |

Arm Cortex-A53 は構成可能な IP であり、TRM の範囲値を SoC の確定値として扱いません。Cortex-A53 の PMU による sampling はコア仕様上の候補ですが、CM0 firmware / kernel 上の `perf` 使用可否は【未確認】です。BCM2837 に ETM / CoreSight trace が実装・配線されるかも【未確認】です。

## Kernel image と firmware の圧縮

Raspberry Pi firmware の公開 boot docs（raspberrypi/documentation commit `ddea98e98dafe9419feb4fd82710c2fbdef7dc44`）は arm64 kernel image を「uncompressed image files」または「gzip archives of an image」としています。bootloader は先頭 signature bytes で gzip を認識します。ほかの圧縮形式を `kernel8.img` に使えるという公式根拠は見つかりませんでした。【一次】【未確認】

Linux arm64 の標準 `Image` は bootloader が展開してから実行する形式で、x86 の `bzImage` のような arm64 自己展開 stub を含みません。対象 kernel の boot 文書は、圧縮 image を使う場合に bootloader 側で展開することを規定します。【一次】[Linux v6.18.57 arm64 booting](https://github.com/torvalds/linux/blob/v6.18.57/Documentation/arch/arm64/booting.rst)

本リポジトリの `board/cardputerzero/post-image.sh` は `Image` から `gzip -9n` の候補と `pigz -11 -n` の `kernel8.img` を作り、後者を展開して `cmp` で元データとの一致を検査します。サイズも出力します。したがって実装済みの方式は gzip で、非圧縮との実機比較は未実施です。【実測・コード確認】

## Kernel / SquashFS 圧縮設定

Buildroot defconfig は `BR2_TARGET_ROOTFS_SQUASHFS4_ZSTD=y` を選択します。`board/cardputerzero/linux.fragment` は `CONFIG_SQUASHFS=y`、`CONFIG_SQUASHFS_XZ=y`、`CONFIG_SQUASHFS_LZ4=y`、`CONFIG_SQUASHFS_ZSTD=y`、`CONFIG_EROFS_FS=y`、`CONFIG_OVERLAY_FS=y` を指定します。`S03msd-etc-overlay` は overlayfs を実際に mount するため、`OVERLAY_FS` は未使用ではありません。

現在の rootfs image は Zstandard です。XZ/LZ4 と EROFS は現行の rootfs 生成経路では使っていませんが、kernel fragment で有効な理由・将来 image との互換性を含めて除去可否を測る候補です。更新処理は SquashFS image を扱います。実際の mount code はその image の compressor を要します。

`CONFIG_RD_GZIP`、`CONFIG_RD_BZIP2`、`CONFIG_RD_LZMA`、`CONFIG_RD_XZ`、`CONFIG_RD_LZO`、`CONFIG_RD_LZ4`、`CONFIG_RD_ZSTD`、SquashFS decompressor threading、`CONFIG_SQUASHFS_FILE_DIRECT`、crypto decompressor の `=y` / `=m` / unset は `linux.fragment` に明記されていません。CI の生成済み `.config` は手元にないため有効値を断定しません。【未確認】CI artifact に入手できたのは `sdcard.img` で、Buildroot/Linux の config 出力ではありません。

SquashFS tools 4.7.5 の `mksquashfs` は `-comp` で codec、`-Xcompression-level` で codec 固有 level、`-b` で 4 KiB–1 MiB の block size を選びます。fragment は小さい file の末尾をまとめ、`-no-fragments` は無効化、`-always-use-fragments` は大きい file にも fragment を使います。XZ option `-Xbcj arm64` は squashfs-tools 4.7.5 の source にあります。XZ Utils 5.8.3（Buildroot 2026.08）は ARM64 BCJ filter を含む世代です。ローカル mksquashfs 4.5 には ARM64 BCJ がなく、今回のローカル xz 測定では使っていません。【一次】

## 公開された展開速度

異なる入力・OS・CPU 条件の値を同じ順位表として比較しません。

| 測定 | 条件と報告値 |
|---|---|
| Zstandard level 19 の展開 | Phoronix Test Suite の公開結果（zstd 1.5.4）は Raspberry Pi 3B+、Cortex-A53 1.40 GHz 4コア、Raspbian 11、Linux 6.1.21-v7+ で 67.9 MB/s と報告します。ベンチマーク内の展開速度であり、microSD からの起動時間ではありません。【二次】 |
| LZ4 1.8.3 の展開 | lzbench 1.7.3、64-bit Linux、投稿者が Cortex-A53 と記した測定で Silesia `dickens` は 448 MB/s、圧縮後／原文比 63.07% です。CPU clock、board、kernel は記載されず【未確認】です。【二次・投稿者測定】 |
| gzip / xz / Zstandard / LZ4 の同一 CM0 比較 | 同一 CM0・同一 rootfs・同一条件の公開値は【未確認】です。 |

読み込み時間は圧縮 image size / 実測 SD read rate と、展開後データ量 / CPU decoder throughput の合計として近似できます。【推測】 cache、read-ahead、並列処理、firmware の測定区間により単純和から外れるため、起動終点を実機で測ります。

## ローカル rootfs image サイズ

入力は CI artifact `/home/ubuntu/work/art/images/sdcard.img` の p5（start sector 294914、512 byte sector、256 MiB partition）から SquashFS を展開した同一 tree です。元 image は zstd、128 KiB block、15,627.37 KiB、1,844 inodes でした。host の mksquashfs / unsquashfs は 4.5（2021-07-22）です。生成した image は外部の `/home/ubuntu/work/research/measure/comp/images/` に保存しました。展開ログと各コマンドは `~/work/research/measure/comp/logs/` にあります。

| Codec / option | block | image bytes |
|---|---:|---:|
| gzip `-Xcompression-level 9` | 128 KiB | 16,343,040 |
| gzip `-Xcompression-level 9` | 1 MiB | 16,314,368 |
| xz (host default preset、BCJ なし) | 128 KiB | 15,405,056 |
| xz (host default preset、BCJ なし) | 1 MiB | 15,048,704 |
| zstd level 19 | 128 KiB | 15,998,976 |
| zstd level 19 | 1 MiB | 15,646,720 |
| zstd level 22 | 128 KiB | 15,998,976 |
| zstd level 22 | 1 MiB | 15,646,720 |
| lz4 high compression | 128 KiB | 17,383,424 |
| lz4 high compression | 1 MiB | 17,276,928 |

これは一つの CI rootfs のサイズ比較で、圧縮・展開時間や SD 性能の測定ではありません。ホストと target の実行時間は【未確認】です。zstd level 19 と 22 が同じサイズだったこともこの入力・host tools での結果に限ります。【実測】

## Compiler・Buildroot・kernel option

| 設定 | 現状 |
|---|---|
| architecture / CPU | `configs/msd_cardputerzero_defconfig` は `BR2_aarch64=y`、`BR2_cortex_a53=y`。Buildroot 2026.08 の Bootlin selector / package file は stable 2025.08-1 を選び、GCC 14.3.0、binutils 2.43.1、glibc 2.41 の toolchain archive を指定します。Bootlin の最新 stable 2026.08-1 は GCC 15.3.0 ですが、この Buildroot source の選択版ではありません。CI 生成物内の compiler binary は未確認です。【一次】 |
| target optimization | defconfig は `BR2_OPTIMIZE_*` を選んでいません。Buildroot 2026.08 `Config.in` の既定は `BR2_OPTIMIZE_2`（`-O2`）。`BR2_TARGET_OPTIMIZATION` も指定なしです。 |
| CPU flags | `BR2_cortex_a53=y` は Buildroot CPU selection です。実際の compile command / toolchain wrapper から `-mcpu` / `-mtune` を採取できておらず、出力 flag は【未確認】です。 |
| LTO / debug / strip | defconfig に `BR2_ENABLE_LTO`、`BR2_ENABLE_DEBUG` はありません。Buildroot は LTO を選んだ package が明示対応する場合に限り使い、Config.in は build time が最大 5 倍になる場合を警告します。`BR2_STRIP_strip` は既定 `y` です。 |
| kernel | Buildroot は raspberrypi/linux commit `234188315037848e5b07d65b85d38edc64095caa` の `bcm2711` defconfig に `linux.fragment` を重ねます。fragment は `CONFIG_CC_OPTIMIZE_FOR_SIZE`、`CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE`、Clang LTO、`DEBUG_INFO*`、FTRACE/KPROBES、KALLSYMS、printk の値を明記しません。生成後 `.config` の実効値は【未確認】です。 |
| localization / BusyBox | `board/cardputerzero/busybox.fragment` は `CONFIG_FSYNC=y` のみです。locale/BusyBox の追加選択はこの fragment からは確認できません。 |

Buildroot 2026.08 の `BR2_ENABLE_LTO` は package が明示対応する場合に限り有効です。`vendor/buildroot` で `BR2_ENABLE_LTO` の利用を確認できたのは `log4cplus`、`flutter-engine`、Cargo package infrastructure、`unbound`、`valgrind`、`fastd`、`netdata`、`wireshark`、`flutter-pi` です。toolchain が GCC LTO plugin / linker に対応する必要があり、external toolchain では package build がその能力を利用できることも要件です。MSD の build では LTO を有効化しておらず、実際の link invocation も未確認です。Buildroot は build time が通常の最大 5 倍になる場合があると警告します。Buildroot に package-wide PGO 設定は見つかりませんでした（2026.08 `Config.in`、manual、package 設定を検索）。GCC 14.3 docs では `-Os` は通常 size を増やさない `-O2` 最適化を使い、`-Oz` は `-Os` よりさらに size を小さくします。`-Oz` は選択 toolchain 版の GCC online manual にあります。【一次】

GCC 14.3 AArch64 options は `-mcpu=cortex-a53` を CPU tuning / architecture selection として文書化し、Cortex-A53 erratum 835769 / 843419 の修正 option も説明します。Buildroot defconfig は `BR2_cortex_a53=y` ですが、CI compiler command に実際に出る `-mcpu` / `-mtune` / erratum flags は【未確認】です。修正 option が命令列・binary size・速度に与える機種固有効果も測定していません。【一次】

Userland PGO の候補は GCC `-fprofile-generate` で instrument して代表 workload を動かし、収集した profile を `-fprofile-use` で再buildする方法です。GCC docs は並列実行時の `-fprofile-update`、build path を正規化する `-fprofile-prefix-path`、target から profile file を回収するための `GCOV_PREFIX` / `GCOV_PREFIX_STRIP` も説明しています。sampling 型 AutoFDO は `perf` sample を `create_gcov` で変換し、GCC `-fauto-profile` に渡す方式です。QEMU 収集は機能経路の profile には使えても、A53 実機の cache、周波数、SD・周辺機器の重みを代表しません。【一次】【推測】

Linux v6.18.57 の `arch/Kconfig` では `LTO_CLANG` が Clang compiler に依存します。GCC を選ぶ現行 external toolchain では kernel LTO を有効化できません。【一次】

Linux kernel 6.13 では Clang AutoFDO と Propeller の upstream 対応が merge されました（2024-11-30 の報道）。kernel docs は LLVM 17 以上を要求し、AutoFDO / Propeller の arm64 sampling を SPE または ETM 経由としています。upstream kernel integration は `CONFIG_AUTOFDO_CLANG` / `CONFIG_PROPELLER_CLANG` であり GCC kernel build には適用できません。Clang instrumentation PGO を Linux 5.14 に入れる提案は merge されず取り下げられたとの報道があり、後に merge された sampling 型 AutoFDO / Propeller と区別します。【一次・kernel docs】【二次・merge 報道】

この製品の起動に対する PGO/LTO の効果は【推測】です。zstd/xz 展開、暗号処理、アプリ処理の CPU-bound 区間には寄与する可能性があります。一方、起動全体には GPU firmware、SD 読込、driver probe、initcall が含まれます。条件が同一と確認できる Cortex-A53 / CardputerZero 向け LTO・PGO 効果の数値は【未確認】です。unused library の削除より `initcall_debug` などで遅い probe/initcall を特定する方が起動時間の調査に直結します。build size・boot ms は本リポジトリで未測定です。

### 削除・最適化候補

| 候補 | 現状 | 予想効果 | 主なリスク | 検証 |
|---|---|---|---|---|
| SquashFS XZ/LZ4 | fragment で `=y`、現在の image は ZSTD | kernel bytes は減る可能性。KiB / boot ms は【推測・未測定】 | 別 compressor image の起動・更新後の互換性 | 各 codec image を mount、update、A/B 起動し `Image` / `vmlinux` 差を記録 |
| EROFS | `CONFIG_EROFS_FS=y`。現 rootfs は SquashFS | kernel bytes は減る可能性、KiB / boot ms は【推測・未測定】 | 将来 rootfs 形式・recovery 手順 | EROFS mount consumer と update input を監査、削除 build を起動 |
| `CONFIG_OVERLAY_FS` | `=y`、`S03msd-etc-overlay` が使用 | 削除候補ではない | `/etc` の永続設定 overlay が動かない | 起動後 mount と `/data/etc` の反映を回帰試験 |
| kernel `CC_OPTIMIZE_FOR_SIZE` / `CC_OPTIMIZE_FOR_PERFORMANCE` | fragment に指定なし、生成 `.config` は未入手 | `Image` size / CPU time は【推測・未測定】 | boot CPU path や code-size / speed trade-off | 各 option を単独変更して build、機能・boot・CPU workload を測定 |
| `-O2` / `-Os`、LTO | userland は Buildroot `-O2` 既定、LTO 未選択 | image size / CPU time は【推測・未測定】 | build time、package ごとの LTO 対応差、再現性 | 同一 toolchain・config で A/B build、size・boot・CPU workload を比較 |
| GCC PGO / AutoFDO | Buildroot に共通 PGO option なし | hot userland path の CPU time は【推測・未測定】 | profile 収集・古い profile・環境依存・再現性 | 実機の代表 workload から profile を採り、同一条件で再計測 |
| Kernel AutoFDO / Propeller | Clang 17+ 向け、kernel は GCC toolchain | hot kernel path は【推測・未測定】 | 別 toolchain/patch、ETM/SPE 未確認、profile 運用 | まず実機 `perf` / trace 対応と boot bottleneck を確認 |
| LTO / PGO の運用コスト | 現在は未選択 | build time・profile collection・再現性に直接のサイズ / boot 効果なし | profile が実 workload とずれる、stale profile、CI 再現性 | build と profile の所要時間・採取条件・更新周期を記録 |

Kernel build と 2–3 候補の `vmlinux` / `Image` size 差は、現作業環境に生成済み kernel `.config` がなく、40 分以内に完了する build を見積もれないため実施しませんでした。実サイズ差は次の測定項目です。

## 実機測定計画

1. `perf stat` / `perf record` が Cortex-A53 PMU を使えるかを確認し、権限、kernel config、sampling event を記録します。ETM/CoreSight は搭載・配線・driver を個別に調べ、未確認のまま AutoFDO に使えるとしません。
2. firmware 開始、kernel entry、initcall 終了、rootfs mount、`MSD/Linux ready` を同一 clock source で記録します。`initcall_debug` で probe/initcall を分離します。
3. 同一カードで kernel raw/gzip、SquashFS codec/block size、実 read rate、展開 CPU throughput を測ります。cache cold/warm、RAM 使用量、CPU 温度・clock を分けて記録します。
4. Buildroot `-O2` / `-Os`、LTO、PGO と kernel codec removal は同一 commit・toolchain・rootfs で比較します。各 build の `Image`、`vmlinux`、SquashFS size、build time、CPU-bound workload、A/B boot time を保存します。
5. PGO は実機 workload と QEMU workload を別 profile として扱います。起動、更新、fsck、無線・表示などの機能試験を通し、profile 生成条件と stale profile の有無を記録します。

## 出典と短い抜粋

| 出典・版 | 確認した抜粋 | 信頼度 |
|---|---|---|
| [CM0 datasheet Release 3, 2026-07-08](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf) | 「Compute Module Zero」datasheet, Release 3 | 【一次】 |
| [CardputerZero product page](https://docs.m5stack.com/en/CardputerZero)（2026-10-19 取得） | 「Quad-core Cortex-A53 @ 1 GHz」「512 MB LPDDR2」 | 【一次・製品資料】 |
| [Cortex-A53 TRM r0p4](https://support.arm.com/documentation/ddi0500/j/Introduction/Implementation-options) | 「Advanced SIMD and floating-point Extension … Included or not」「Cryptography Extension … Included or not」 | 【一次】 |
| [Raspberry Pi config boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc) | 「uncompressed image files」「gzip archives of an image」 | 【一次・commit pinned】 |
| [Linux v6.18.57 arm64 booting](https://github.com/torvalds/linux/blob/v6.18.57/Documentation/arch/arm64/booting.rst) | bootloader が kernel image を準備し、圧縮 image は展開してから引き渡す手順 | 【一次・tag pinned】 |
| [Bootlin aarch64 toolchains](https://toolchains.bootlin.com/releases_aarch64.html) | Buildroot 選択版 `stable-2025.08-1` は GCC `14.3.0`、最新 stable `2026.08-1` は GCC `15.3.0` | 【一次】 |
| [GCC 14.3 optimize options](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Optimize-Options.html), [AArch64 options](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/AArch64-Options.html), [instrumentation options](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Instrumentation-Options.html) | `-Os`, `-Oz`, `-mcpu=cortex-a53`, errata options, `-fprofile-generate` / `-fprofile-use` | 【一次】 |
| [Buildroot 2026.08 `Config.in`](https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/Config.in) | LTO は package が対応する場合に有効。build time が「sometimes 5 times longer」になり得る | 【一次】 |
| [SquashFS tools 4.7.5 ARM64 BCJ](https://github.com/plougher/squashfs-tools/blob/4.7.5/squashfs-tools/xz_wrapper_extended.c) | `"arm64", LZMA_FILTER_ARM64` | 【一次】 |
| [XZ Utils 5.8.3](https://github.com/tukaani-project/xz/releases/tag/v5.8.3) | release tag 5.8.3。liblzma ARM64 BCJ は 5.4.0 で stable 化 | 【一次】 |
| [Linux v6.18.57 AutoFDO](https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/autofdo.rst), [Propeller](https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/propeller.rst), [LTO Kconfig](https://github.com/torvalds/linux/blob/v6.18.57/arch/Kconfig) | arm64 sampling、Clang / LLVM 要件、`LTO_CLANG` | 【一次】 |
| [AutoFDO / Propeller merged for Linux 6.13](https://www.phoronix.com/news/AutoFDO-Propeller-Linux-6.13) | 2024-11-30 に merge を報告 | 【二次】 |
| [Clang PGO for Linux 5.14 withdrawn](https://www.phoronix.com/news/Clang-PGO-Linux-Shot-Down) | Linux 5.14 前の instrumentation PGO patch を取り下げた経緯 | 【二次】 |
| [Phoronix zstd benchmark](https://mail.openbenchmarking.org/result/2408281-BOMM-240826011%26gru%26sro%26export=html) | Raspberry Pi 3B+ Cortex-A53、zstd 1.5.4 level 19、67.9 MB/s | 【二次】 |
| [LZ4 ARM64 benchmark report](https://github.com/lz4/lz4/pull/713) | lzbench 1.7.3 / Cortex-A53 投稿者測定。Silesia `dickens` 展開 448 MB/s | 【二次・測定条件の一部未確認】 |
| [AutoFDO tools](https://github.com/google/autofdo/tree/f95d1a170dfe24ec5ce4117aa4b0f6d836841703) | `create_gcov` toolset と GCC AutoFDO の手順。commit `f95d1a170dfe24ec5ce4117aa4b0f6d836841703` | 【一次】 |
