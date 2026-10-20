# シミュレーターと検証計画

measurement-and-planning.md から分割した節です。

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

## シミュレーション検証計画（S1–S17）

この表を S1–S17 の試験状況の source of truth とし、根拠・成果物・担当範囲を記録する。Filesystem の書き込み fault・速度模擬 S17 の詳細と取得済み出典は[読み取り専用領域と FS 比較](readonly-data-and-fs.md#s17-ストレージの障害速度の模擬)を参照する。

| ID | 対象 | 主な方法・成果物 | 状態 | PR | 記録 |
|---|---|---|---|---|---|
| S1 | Linux kernel option sweep | 一候補ずつ変更して baseline `.config` と依存差分、`Image` size、build log を保存する。 | ツールのみ・本番未実施 | #25 | [2026-10-19-s01-kernel-sweep-trial](../experiments/2026-10-19-s01-kernel-sweep-trial.md) |
| S2 | camera | Unicam + IMX219 raw V4L2 path と utilities を実装し、`camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効化。C154 V0.6.1 は CAM_3V3 LDO の EN を VSYS_5V に pull-up し、CM0 DTS は CAM_GPIO を GPIO40 に割り当てます。v5 の GPIO16 は PY32 reset 用で、追加 camera GPIO overlay は適用しません。【一次】Lite 版の probe failure は想定内ですが、実際の kernel message は未確認。統制 QEMU 再測定は相対中央値 +0.0510% で +1.0% 基準内のため tier A を採用。実機では sensor ID、topology、2-lane raw capture、Lite の probe-failure message を確認します。 | 実装済み（実機未確認） | — | [2026-10-19-s02-camera](../experiments/2026-10-19-s02-camera.md) |
| S3 | `/data` format/options | ext4 block size、`noatime`、`lazytime`、`data=`、mount flags の組合せを比較する。 | 完了 | #27 | [2026-10-19-s03-data-ext4-writes](../experiments/2026-10-19-s03-data-ext4-writes.md) |
| S4 | ext4/F2FS/btrfs | 同じ data set と update/fsync workload で create, sync, mount, fsck, power-cut recovery、write volume を記録する。 | 未着手 | — | — |
| S5 | OverlayFS mode | `/etc`-only、full-root、`/data` bind/symlink 案を比較し、xattr、whiteout、rename、A/B lower update を試す。 | 未着手 | — | — |
| S6 | kernel hardening | `kernel-hardening-checker` を使い設定差を記録し、必要機能と boot regression を確認する。 | 完了 | #31; #28 | [2026-10-19-s06-kernel-hardening](../experiments/2026-10-19-s06-kernel-hardening.md); [2026-10-19-s06-modules-dep-xz](../experiments/2026-10-19-s06-modules-dep-xz.md)（#28） |
| S7 | IR | IR driver/DT input/output、既存機能と競合する GPIO を調査し、実機送受信を確認する。 | 未着手 | — | — |
| S8 | charger IC | IC driver/DT、状態読み出し、充電状態・電圧表示を実機で検証する。 | 未着手 | — | — |
| S9 | power-fail shutdown | 実電源を切る前後の `powerfail_suo`、shutdown deadline、filesystem recovery を反復測定する。QEMU は GPIO/電源回路を代替しない。 | 未着手 | — | — |
| S10 | update signature rejection | 署名不正・破損・古い bundle を host test と QEMU で与え、非 active slot と state が変化しないことを確認する。 | 未着手 | — | — |
| S11 | watchdog fallback | 起動中 hang、health failure、watchdog reset 後の slot selection と recovery を QEMU・実機で分けて確認する。 | QEMU 実験済み（実機未確認） | — | [S11 watchdog 実験](../experiments/2026-10-20-s11-qemu-watchdog.md) |
| S12 | SquashFS codec/block size | gzip/xz/zstd/lz4 と block size ごとに image size、decode throughput、SD I/O、RAM を記録する。 | 未着手 | — | — |
| S13 | userland `-O2`/`-Os`/LTO | 同一 GCC/config で package/rootfs size、CPU workload、boot timing、build time を比較する。 | 未着手 | — | — |
| S14 | CPU specialization | `-mcpu`/`-mtune` と kernel CPU options を一つずつ変え、`Image`/package size、命令数、実機時間、全機能を検証する。 | 未着手 | — | — |
| S15 | QEMU versions | version と machine/device model 差を記録し、同一 image/command line の機能・virtual-time regression を比較する。 | 未着手 | — | — |
| S16 | normally-RO `/etc` and `/data` | boot、persistent config, seedrng, updater, fsck/recovery の各 writer が maintenance RW window だけで動くか試験する。 | 設計のみ | #24 | — |
| S17 | storage fault/speed emulation | `dm-log-writes` + `replay-log`、`dm-flakey`/`dm-delay`、QEMU `blkdebug`/throttle/cache mode を使い、error/replay/prefix ごとに fsck・data invariant を記録する。実 card FTL/timing は含まない。 | 調査のみ | #24 | — |

### S2 実機カメラ確認チェックリスト

- [ ] `dmesg` から IMX219 の sensor ID を採取する。
- [ ] IMX219 overlay 適用後に `media-ctl -p` を実行し、sensor → Unicam の media topology と link 状態を記録する。
- [ ] CSI1 の 2-lane 接続で対応する raw format を選び、`v4l2-ctl --stream-mmap` による capture を実施して format、解像度、frame 数、drop/error を記録する。
- [ ] カメラのない Lite 版で IMX219 probe が失敗する場合の実際の kernel message を採取し、想定内であることを確認する。【未確認】

### 検証ツールと実行境界

- **Buildroot differential build:** まず baseline image、kernel `.config`、Buildroot config、`Image`/rootfs size を保存し、その後に一 option ずつ変える。build log と変更理由を S ID に結び付ける。
- **QEMU function test:** `board/cardputerzero/qemu/run-qemu.sh` と `raspi3b` を使い、rootfs、init、A/B、update、watchdog の再現可能な機能範囲を確認する。標準 boot の成功と実機機能の保証を混同しない。
- **仮想時間・initcall:** CPU option 比較では QEMU `-icount shift=0` と `initcall_debug` を使い、ready marker までの virtual time と initcall 数・所要時間を記録する。これは real-time benchmark ではない。
- **filesystem fault:** 使い捨て image 上で forced QEMU stop、`kill -9`、dm-log-writes の replay、QEMU block statistics を使う。`kill -9` や `cache=unsafe` は実機の給電遮断と同じではない。再生前後に fsck とアプリケーション invariant を確認する。
- **hardening/host tests:** `kernel-hardening-checker` と `tests/msd-update/run.sh` 等の対象 host tests を実行し、結果を該当 S ID に紐付ける。
- **実機測定:** CM0/CardputerZero でのみ、電源断、物理 SD 性能、温度・周波数、camera/IR/charger、周辺機器の全機能を確認する。Zero 2 W は software timing の proxy にとどめ、同一 SoC でも board 差を別に記録する。

### 実施順と抜け防止

1. Baseline config/image、kernel version、firmware、DT、measurement endpoints を固定して保存する。
2. S1 と S2/S7/S8 の hardware/driver inventory を行い、変更候補が製品機能に触れるか特定する。
3. S3–S5 と S16 の filesystem/mount policy を、S17 fault matrix と組み合わせて検証する。
4. S9–S11 の power/update recovery を続け、最後に S12–S15 の image/CPU/simulator 比較を行う。実測候補を選ぶ場合は実機で再確認する。
5. 試験票に S ID、hypothesis、source URL、config/hash、command、device/card、始点・終点、artifact path、結果、未確認点を記録する。変更した config key と六つの製品要件の影響を照合し、各要件に「試験済み/未試験」の根拠が一つ以上あるまで完了扱いにしない。

この計画で CI に追加するのは日本語 lint、relative-link、host test など軽い回帰検査に限り、既存 workflow は変更しない。kernel option sweep、複数 filesystem の電断/replay、full differential Buildroot、実機試験はローカルで行い、CI に長時間の sweep を追加しない【推測】。

### QEMU で検証できる範囲の網羅表（2026-10-20 時点）

この節は、調査文書に挙げた項目を QEMU で検証できるかどうかで分け、状況をまとめたものです。照らし合わせた文書は、上の S1〜S17 の表、[アイデア総覧](ideas-overview.md)、[高速化のアイデア一覧](fastboot-ideas.md)、[高速起動記事と Cortex-A53 調整](fastboot-and-cpu-tuning.md)、[SoC・メモリ・SD 特性と圧縮方式](soc-memory-compression.md)、[CPU・割り込み・sysctl](cpu-irq-and-sysctl.md)、[セキュリティ対策](security-hardening.md)です。QEMU の秒数は版どうしの比較にだけ使い、実機の秒数とはみなしません。項目が済んだら、ここと上の S1〜S17 の表を同じ PR で更新します。

#### QEMU で検証済み

| 項目 | 確かめたこと | 記録 |
|---|---|---|
| S3 `/data` の ext4 設定 | mount option ごとの書き込み量と、SIGKILL 後の回復 | [2026-10-19-s03-data-ext4-writes](../experiments/2026-10-19-s03-data-ext4-writes.md) |
| S6 カーネル hardening（tier A） | kernel-hardening-checker の結果と起動の回帰 | [2026-10-19-s06-kernel-hardening](../experiments/2026-10-19-s06-kernel-hardening.md) |
| S2 カメラ（QEMU の範囲） | 起動時間の回帰。センサーの動作は実機で確かめる | [2026-10-19-s02-camera](../experiments/2026-10-19-s02-camera.md) |
| S9 のうち GPIO6 の経路 | QEMU に足した GPIO6 の割り込みで、通知、remount、fsck を確認 | [2026-10-20-qemu-powerfail-gpio6](../experiments/2026-10-20-qemu-powerfail-gpio6.md) |
| 起動時間の内訳と K1・K2・U1 | initcall と init script ごとの時間。K2（ftrace の無効化）だけが基準を満たした | [2026-10-20-qemu-boottime](../experiments/2026-10-20-qemu-boottime.md) |
| 調整項目の既定値 | sysctl、ブロックデバイス、モジュールパラメーター | [2026-10-19-tunables-dump](../experiments/2026-10-19-tunables-dump.md) |
| `kernel8.img` の gzip 再圧縮 | 実装済み。`post-image.sh` が `pigz -11 -n` で圧縮し、展開結果を `cmp` で比べる。読み込み時間は実機で測る | #8（[BUILD.md](../BUILD.md)） |
| `align = 4M` | 実装済み。CI の `check-image-layout.sh` が全開始位置の 8192 sector 境界を検査する。性能は実機で測る | #19（[ストレージ](storage-and-flash.md)） |
| Lynis による監査（QEMU のみ） | 製品イメージの監査を 3 回行い、結果が同じこと。指摘の分類。対応は sysctl 候補と S1・S14 で行う | [2026-10-21-qemu-lynis](../experiments/2026-10-21-qemu-lynis.md) |
| S1（試運転だけ） | sweep ツールの動作。本番は未実施 | [2026-10-19-s01-kernel-sweep-trial](../experiments/2026-10-19-s01-kernel-sweep-trial.md) |
| `/data` の `noexec`（QEMU のみ） | 起動・`/data` の準備・serial 検査が変わらないこと。直接実行は拒否されるが、`sh` 経由と `/etc` overlay 経由は防げないこと。アプリの互換性は実機で確認する | [2026-10-21-qemu-data-noexec](../experiments/2026-10-21-qemu-data-noexec.md) |
| zram（QEMU のみ） | zstd・lz4 とも `modprobe` から `swapon -p 100` まで動き、zswap は無効のまま。圧縮できないデータでは OOM になる。CPU の負荷は実機で確認する | [2026-10-21-qemu-zram](../experiments/2026-10-21-qemu-zram.md) |

#### QEMU で検証できるが未実施

| 項目 | QEMU で確かめること | 規模 |
|---|---|---|
| S11 watchdog | 給餌が止まったときの reset、reboot、poweroff | 実施中 |
| init script の stop 処理 | 再起動のときに起動時の処理をやり直さないこと（S11 のログで見つけた不具合） | 実施中 |
| S10 更新の署名の拒否 | 不正・破損・古い bundle で、非 active slot と状態が変わらないこと | 中 |
| 温度 | QEMU に温度の値を足し、読み出しと記録の経路を確かめる | 小 |
| S15 QEMU の版の比較 | 11.0.2 と 11.1.2、`raspi3b` と `raspi3ap`、plugin の命令数 | 中 |
| sysctl の候補 | `kernel.sysrq=32` でも電源断時の remount が動くこと、`panic=` と `panic_on_oops` と watchdog の経路、情報漏えい対策の値 | 小 |
| ramoops | panic のログを再起動後に読めるか（QEMU で RAM が保たれる範囲） | 小 |
| S12 SquashFS の圧縮方式と block size、EROFS | image のサイズ、mount、A/B 起動、icount での起動時間。読み込み速度は実機で測る | 中 |
| S1・S14 カーネル option の本番 | 約 80 候補を 1 つずつ変え、`Image` のサイズと icount での起動時間を比べる。NUMA、A53 以外の ISA、CM0 にない機能（NVMe、PCIe、KVM など）、`CC_OPTIMIZE_FOR_SIZE`、カーネルの圧縮方式を含む | 大（ビルドだけで約 1 日の見込み） |
| S6 tier B | 低コストの hardening 候補の、サイズと icount での起動コスト | 中（S1 と同じ仕組みで測る） |
| `quiet`、`lpj=`、PREEMPT、printk | icount での起動時間の差 | 小（S1 と同じ仕組みで測る） |
| 任意機能のドライバーをモジュールにする | K2 のあとに残る `dwc_otg_driver_init` などを遅らせたときの差。LCD とキーボードは実機で確かめる | 中 |
| S13 ユーザーランドの `-O2`、`-Os`、LTO | rootfs のサイズと、icount での起動時間 | 大（全体の再ビルドが複数回） |
| S16 `/etc` と `/data` を通常は読み取り専用にする | 各 writer が書き込み可能な期間だけで動くか | 中 |
| S4 ext4・F2FS・btrfs、S5 OverlayFS の方式 | 同じ負荷での fsck、mount、SIGKILL 後の回復、書き込み量 | 大 |
| S17 ストレージの障害と速度の模擬 | dm-log-writes の再生、dm-flakey、QEMU の blkdebug | 大 |
| 起動時のファイルアクセスの観測と `mksquashfs -sort` | 起動時に読むファイルとその順番（ftrace を残した版で） | 中 |
| dm-verity | QEMU で改ざん拒否を確認した。実機性能、A/B 復旧、信頼できる root digest、製品統合は未実施（[記録](../experiments/2026-10-21-qemu-dm-verity.md)）。 | 中 |
| BusyBox の applet を減らす、静的リンク | QEMU で静的リンクと 63 applet を比較した。製品用 applet の範囲は未決である（[記録](../experiments/2026-10-21-qemu-busybox.md)）。 | 中 |

#### 実機でしか検証できない項目

config.txt の設定（`boot_delay`、`start_cd.elf`、`gpu_mem`、`max_framebuffers`、`core_freq`、`initial_turbo`、`arm_boost`）、tryboot と A/B の slot 選択、firmware から OS への watchdog の引き継ぎ、CPU の governor と `maxcpus=1` と温度、I/O スケジューラーと `read_ahead_kb`、SD の速度と erase の単位、`get_throttled`、実際の電源断（S9 の残りと 200 回試験）、LCD の fbcon、カメラ（S2）、IR（S7）、充電 IC（S8）、CMA の量。

#### 調査だけの項目と採用しない項目

SSH と VPN（実装しない方針）、irqbalance、VPS 向けの設定、secure boot に対応した SoC への移行、更新フレームワーク（RAUC など）の比較。

#### 実施順（2026-10-20 時点）

下の「次の作業計画（2026-10-19 時点）」を次の順に置き換えます。

1. S11 watchdog と init script の stop 処理
2. 小さい項目: S10、温度、sysctl の候補、ramoops、S15
3. S12 と EROFS
4. S1・S14 の本番（S6 tier B、`quiet`・`lpj=`・PREEMPT、カーネルの圧縮方式を含む）と、任意機能のドライバーのモジュール化
5. S13
6. S16 → S4・S5・S17
7. 起動時のファイルアクセスを観測し、`mksquashfs -sort` と小項目（zram、dm-verity、BusyBox、Lynis）の記録を進める

### 次の作業計画（2026-10-19 時点）

S2（#36）を出した時点での残りの作業と、その順番です。セッションをまたいでも抜けないように、ここを正とします。各項目は experiment-record スキルに従って記録し、結果が出たら上の表の「状態」を更新します。

| 順 | 作業 | 内容と完了の条件 |
|---|---|---|
| 1 | S2 の続き | v4l-utils から `v4l2-ctl` と `media-ctl` だけを残し、ほかのツールと RC keymap を外す（#36 の実験記録では、ツール類が展開後で約 3.1 MB）。S7 で `ir-keytable` を使うかを先に決める。実機でカメラを確かめるスクリプトと手順書を用意する（`dmesg` のセンサー ID、`media-ctl -p`、`v4l2-ctl --list-formats-ext`、`--stream-mmap` での raw の取得、PC での RAW10 の現像）。 |
| 2 | S6 tier B | 下の「S6 tier B の分類」の 3 を、サイズと QEMU の命令数での起動コストを測ってから採否を決める。1 と 2 は根拠を確かめて S6 の記録に「対処しない理由」として残す。 |
| 3 | S7 → S9 → S8 | S7 IR（M5 の Makefile は v3・v5 の両方で、受信に `gpio-ir,gpio_pin=13,gpio_pull=up`、送信に `gpio-ir-tx,gpio_pin=12` を追加する。v0.6.1 の回路図を画像で読み、GPIO12・13 の配線を確かめてから入れる）。S9 powerfail の正常 shutdown を設定で選べるようにし、QEMU で uevent を注入して試す。S8 IP2315 の driver を調べる。 |
| 4 | S1・S14 本番 | 80 候補の総当たり。始める前に `kernel-variant-sweep.sh` を直し、QEMU が失敗した試行のログを残す（今は一時ディレクトリごと消える）。`NUMA=n` はログを残して測り直す。結果の文書の PR と、`linux.fragment` を削減する PR を分ける。S6 tier B の 5 は、ここで影響を測って決める。 |
| 5 | S10・S11 | 更新の署名が不正・破損・古い場合に拒否されることの試験と、watchdog による hang からの復帰の QEMU 試験。 |
| 6 | S16 → S4・S5・S17 | `/etc` と `/data` を通常は読み取り専用にする設計を QEMU の電源断で確かめ、その上で FS（ext4・F2FS）と overlayfs の方式を比べる。ストレージの障害と速度の模擬（S17）を同じ枠組みで使う。 |
| 7 | S12・S13・S15 | SquashFS の圧縮方式と block size、ユーザーランドの `-O2`・`-Os`・LTO、QEMU の版の比較。 |
| 8 | 監査 | 各段階で、チャット・計画書・この表を origin/main と照らし合わせ、済んだものと済んでいないものを報告する。 |

保留: libcamera と VideoCore の ISP（カメラの tier B）は、VCHIQ と firmware の変更が必要で、起動時間と RAM への影響が大きいため、使う場面が決まるまで入れません。Raspberry Pi Zero 2 W は用意しません。CardputerZero が手に入らない場合に限り、代わりの実機として検討します。

実機が届いたら、上の「実機が届いたら最初に測る項目」に加えて、実際の周辺機器（Wi-Fi、Bluetooth、音声、USB ネットワーク）でモジュールが自動でロードされることを確かめます。

#### S6 tier B の分類

S6（#31）のあとの kernel-hardening-checker v0.6.17.1 の FAIL は 111 件です（cmdline・sysctl の項目と、同じ項目の重複判定を含みます）。分類は次のとおりで、【要確認】は実装の前にビルドで確かめます。

1. **A53（ARMv8.0）では使えないため対処しない:** `ARM64_BTI_KERNEL`（ARMv8.5）、`KASAN_HW_TAGS`（MTE、ARMv8.5）、`ARM_SMMU` 系（BCM2837 に SMMU はない）、`EFI_DISABLE_PCI_DMA`・`RESET_ATTACK_MITIGATION`・cmdline の `efi`（EFI 起動ではない）、`SCHED_CORE`・`nosmt`（SMT はない）、`CFI_CLANG`・`CFI_PERMISSIVE`（Clang が必要）。
2. **ツールチェーンしだい【要確認】:** `SHADOW_CALL_STACK`（GCC の aarch64 対応）、`RANDSTRUCT_FULL`・`GCC_PLUGIN_LATENT_ENTROPY`（GCC plugin を作れるか）、`ARM64_SW_TTBR0_PAN`（A53 に PAN がなくソフトウェアで模擬するため、システムコールのコストを測る）。
3. **低コストの候補（tier B として測る）:** `SLAB_FREELIST_HARDENED`、`SLAB_FREELIST_RANDOM`、`SLAB_MERGE_DEFAULT=n`、`RANDOM_KMALLOC_CACHES`、`LIST_HARDENED`、`BUG_ON_DATA_CORRUPTION`、`SHUFFLE_PAGE_ALLOCATOR`、`FORTIFY_SOURCE`、`ZERO_CALL_USED_REGS`、`RANDOMIZE_KSTACK_OFFSET_DEFAULT`、`RODATA_FULL_DEFAULT_ENABLED`、`DEBUG_WX`、`DEFAULT_MMAP_MIN_ADDR=65536`、`ARCH_MMAP_RND_BITS` の最大化、`SECURITY_DMESG_RESTRICT`、`LEGACY_TIOCSTI=n`、`LDISC_AUTOLOAD=n`、`PROC_MEM_NO_FORCE`、`STRICT_DEVMEM`・`IO_STRICT_DEVMEM`・`DEVPORT=n`、`SECURITY_LANDLOCK`、`SECURITY_LOCKDOWN_LSM`（integrity モード）、`MODULE_SIG_SHA512`、`BLK_DEV_WRITE_MOUNTED=n`（msd-update と両立するかを試験で確かめる）。
4. **コストが大きいため既定では入れず、開発用イメージの選択肢にする:** `INIT_ON_ALLOC_DEFAULT_ON`、`INIT_ON_FREE_DEFAULT_ON`、`KSTACK_ERASE` 系、`UBSAN` 系、`KFENCE` 系、`PAGE_TABLE_CHECK` 系、`DEBUG_VIRTUAL`・`DEBUG_SG`・`DEBUG_NOTIFIERS`、`WERROR`。
5. **機能を削るもの:** `MODULES`、`VT`、`FB` は CardputerZero の機能（後から挿す USB 機器、コンソール、LCD）に使うので残します。`STATIC_USERMODEHELPER` と `RSEQ` は、mdev と glibc への影響を確かめてから決めます。`DEBUG_FS`、`FTRACE`・`KPROBES` 系、`KALLSYMS`、`BPF_SYSCALL`、`USER_NS`、`IO_URING`、`AIO`、`MAGIC_SYSRQ`、`COREDUMP`、`CHECKPOINT_RESTORE`、`COMPAT` などは S1 の削減候補と重なるため、S1 の本番で影響を測ってから決めます。
