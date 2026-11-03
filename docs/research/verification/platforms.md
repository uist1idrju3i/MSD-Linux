# シミュレーター・代理機の役割と限界

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

現行の[QEMU起動script](../../../board/cardputerzero/qemu/run-qemu.sh)は`raspi3ap`が既定で、`raspi3b`も選択できます。
実際に使うQEMUの版は[開発用イメージ](../../../docker/msd-dev)の実行出力と、各実験のbinary hashで固定します。
以下は比較資料を取得した時点の記述です。冒頭のホスト6.2.0・CIのapt導入・当時の最新版という記述を、現在の固定環境の説明には使いません。
対応deviceの列挙と、CM0固有回路・firmware・実SD性能を確認できることは別です。

## 比較時の資料と候補

## シミュレーターと検証基盤の比較

QEMU 公式 release ページで確認できた最新 stable は 11.1.2（2026-09-28）です。手元の `/usr/bin/qemu-system-arm` は 6.2.0（Debian `1:6.2+dfsg-2ubuntu6.31`）。CI は `ubuntu-26.04` 上で unpinned の `apt-get install qemu-system-arm` を実行します。CI runner の package version は workflow に pin されず、実行ログにも version が保存されていないため【未確認】です。

QEMU 6.2 docs には `raspi3b` があり、`raspi4b` はありません。`raspi4b` は QEMU 9.0 で追加されました。同 release notes は Raspberry Pi の SPI と BSC I2C も追加したとします。QEMU 11.1.2 の raspi docs は UART、DMA、clock/reset、timer、GPIO、RNG、framebuffer、USB、SD/MMC host、thermal sensor、MBOX、SPI、I2C を実装 device として列挙します。watchdog は一覧にありません。SD/MMC host の正確な controller 実装（SDHCI か BCM SDHOST か）は概要資料から確定できず【未確認】です。`VideoCore firmware (property)` は property mailbox interface であり、実機 VideoCore firmware と boot path の再現ではありません。【一次】

TCG plugin の `insn` は guest 命令数、`hotblocks` は頻出 translation block、`cache` は指定 cache 構成での guest memory access の hit/miss を集計します。`libinsn` は plugin が instruction を decode / 表示するための補助 library で、独立した性能計測器ではありません。host 実時間や実 SD latency は測りません。QEMU `-icount` は guest instruction count に基づく仮想時間を進め、決定的な実行モードを提供しますが、wall-clock 性能比較の根拠にはなりません。plugin による同一入力の命令数・cache event 比較に用途を限定します。【一次】

QEMU `virt` は汎用 Arm machine と virtio block / network 等を提供し、更新処理・userspace の機能試験に使えますが、CM0 firmware、VideoCore、SD host、CardputerZero 固有 device を検証しません。`raspi3b` も target の RAM 容量・clock・実 microSD 性能を忠実に再現するものではありません。

gem5 の最新公式 release は 25.1.0.1（2026-04-21）。26.0 milestone は 2026-10-19 時点で release 済みと確認できませんでした。gem5 は `MinorCPU` や full-system Arm Linux 構成を提供します。Arm の HPI は「modern in-order Armv8-A implementation」の代表モデルで Cortex-A53 の cycle-accurate replica ではありません。`ex5_LITTLE` は Cortex-A7 based model と明記され、A53 proxy ではありません。full-system simulation は model・kernel・disk 準備と実行時間の負担が大きく、CM0 固有 device もありません。【一次】【推測】

Arm Fast Models の公開ページは Architecture FVP version 11.32（2026-07-30）と Base RevC AEMvA platform を掲載します。Base RevC は architecture envelope platform で Cortex-A53 microarchitecture model ではありません。Cortex-A53 FVP の説明も公開されていますが、download entitlement / license は【未確認】です。Renode 最新 release は 1.17.0（2026-09-07）。v1.17.0 の `platforms` tree から BCM2835 / BCM2837 / Raspberry Pi platform は見つかりませんでした。【一次】【未確認】

CM0 と Raspberry Pi Zero 2 W は RP3A0 SiP 系で、公開資料はどちらも 1 GHz quad-core Cortex-A53、512 MB LPDDR2 を記載します。Zero 2 W の microSD host / board routing が CM0 と同一とは扱いません。SD interface の clock、bus 幅、UHS / 1.8 V 対応も未確認のため、software-level proxy に留めます。【一次】

| 基盤 | 目的・忠実度 | 速度・コスト | 検証できる範囲 / できない範囲 |
|---|---|---|---|
| QEMU `raspi3b` | BCM2837 系の機能試験・中 | TCG は比較的高速、導入コスト低 | 起動、UART、rootfs、init、A/B userspace / VideoCore boot、実 tryboot、CM0 device、SD 性能・実時間は対象外 |
| QEMU `virt` | generic Arm userspace・低～中 | 高速、導入コスト低 | updater、filesystem、サービス / BCM2837・firmware・M5 hardware は対象外 |
| QEMU TCG plugin + `-icount` | 命令量・cache event の比較 | 実時間性能は対象外 | build option 間の instruction/cache 傾向 / A53 cycle・SD latency は対象外 |
| gem5 | CPU/cache pipeline の詳細化・設定依存 | 遅く、model 構築コスト高 | 合成 workload の CPU/cache 感度 / 実機 firmware・board は対象外 |
| Arm FVP / Renode | Arm architecture / 対応 platform の検証 | 入手条件・model 構築に依存 | architecture または Renode 対応 platform / CM0 board 固有経路は未確認 |
| Zero 2 W / CardputerZero | RP3A0 software proxy / 実 target | 遅く、装置と測定治具が必要 | software timing・SD・温度・周辺機器。board 間差を無視して一般化できない |

**提案（【推測】）:** 第1段は QEMU `raspi3b` で機能・起動 regression、第2段は QEMU TCG instruction-count/cache events と build size で option の傾向を比較、第3段は Zero 2 W を proxy とし最終判断は CardputerZero/CM0 実機で boot time・SD・温度・RAM を測ります。QEMU の instruction count だけで実時間の最適化を採択しません。

### 次の比較測定

| 比較 | 記録項目 | 条件 |
|---|---|---|
| SquashFS codec / 128 KiB・1 MiB block | image bytes、CPU decode throughput、SD sequential/random read、起動時刻 | 同じ rootfs・カード・温度。cache cold/warm を分ける |
| SD / CPU / RAM | 実 read rate、decoder throughput、RAM・cache miss、CPU clock / 温度 | CM0 と Zero 2 W を別機種として記録 |
| Buildroot `-O2` / `-Os` | package size、rootfs size、起動時刻、CPU workload、build time | 同一 GCC 14.3.0 toolchain・config・rootfs |
| kernel compressor removal / optimize option | `Image` / `vmlinux` bytes、boot milliseconds、feature regression | `CONFIG_SQUASHFS_XZ/LZ4`、`EROFS_FS`、size/performance config を一つずつ変更 |
| LTO / PGO | build time、profile 生成・回収時間、binary size、CPU workload、再現性 | 実機 profile と QEMU profile を分離し、profile source と生成条件を保存 |

出典: [QEMU 11.1.2 release](https://www.qemu.org/download/)、[raspi machine models](https://qemu.readthedocs.io/en/v11.1.2/system/arm/raspi.html)、[TCG plugins](https://qemu.readthedocs.io/en/v11.1.2/devel/tcg-plugins.html)、[gem5 25.1.0.1](https://github.com/gem5/gem5/releases/tag/v25.1.0.1)、[Arm HPI model](https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/HPI.py)、[Arm FVP 11.32](https://support.arm.com/tools-and-software/fixed-virtual-platforms/arm-architecture-fvps)、[Renode 1.17.0](https://github.com/renode/renode/releases/tag/v1.17.0)、[CM0 datasheet](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)、[Zero 2 W product page](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)。
