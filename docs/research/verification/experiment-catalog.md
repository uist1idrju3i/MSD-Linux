# S1–S17の試験台帳

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

実施の記録、現行設定、未確認範囲を対応づける更新先です。過去のQEMU結果を現在のbinary・実機の合格に読み替えません。
個々の条件・反復数・失敗はリンク先の実験記録を読みます。旧表の状態と省略した重複行は[原記録](research-records.csv)に残しました。
S17の手法と取得済み出典は[読み取り専用領域とFS](../storage/fault-injection-s17.md#s17-ストレージの障害速度の模擬)を参照します。

## シミュレーション検証計画（S1–S17）

| ID | 対象 | 主な方法・成果物 | 状態 | 関連情報 | 記録 |
|---|---|---|---|---|---|
| S1 | Linux kernel option sweep | 一候補ずつ変更して baseline `.config` と依存差分、`Image` size、build log を保存する。 | 本番比較の記録あり。失敗・不一致と集計数の留保は下記を参照。 | #25 | [2026-10-19-s01-kernel-sweep-trial](../../experiments/2026-10-19-s01-kernel-sweep-trial.md); [本番比較](../../experiments/2026-10-30-kernel-sweep-s1-s14.md) |
| S2 | camera | Unicam + IMX219 raw V4L2 path と utilities を実装し、`camera_auto_detect=0` と `dtoverlay=imx219` を既定で有効化。C154 V0.6.1 は CAM_3V3 LDO の EN を VSYS_5V に pull-up し、CM0 DTS は CAM_GPIO を GPIO40 に割り当てます。v5 の GPIO16 は PY32 reset 用で、追加 camera GPIO overlay は適用しません。【一次】Lite 版の probe failure は想定内ですが、実際の kernel message は未確認。統制 QEMU 再測定は相対中央値 +0.0510% で +1.0% 基準内のため tier A を採用。実機では sensor ID、topology、2-lane raw capture、Lite の probe-failure message を確認します。 | 実装済み（実機未確認） | — | [2026-10-19-s02-camera](../../experiments/2026-10-19-s02-camera.md) |
| S3 | `/data` format/options | ext4 block size、`noatime`、`lazytime`、`data=`、mount flags の組合せを比較する。 | QEMUの書き込み量比較の記録あり。実SDの電断耐性は未確認。 | #27 | [2026-10-19-s03-data-ext4-writes](../../experiments/2026-10-19-s03-data-ext4-writes.md) |
| S4 | ext4/F2FS/btrfs | 同じ data set と update/fsync workload で create, sync, mount, fsck, power-cut recovery、write volume を記録する。 | QEMUでmkfs・読み書き・usable容量を比較。phase1-r3では20構成すべてT2 recovered/manifest_ok 20/20。実SDのFTL・物理電断は未確認 | — | [S4予備比較](../../experiments/2026-10-30-s4-fs-compare.md)（#128）、[phase1-r2](../../experiments/2026-11-10-phase1-matrix-r2.md)、[T2再測定](../../experiments/2026-11-11-phase1-t2-rerun.md) |
| S5 | OverlayFS mode | `/etc`-only、full-root、`/data` bind/symlink 案を比較し、xattr、whiteout、rename、A/B lower update を試す。 | 現行構成の QEMU 確認済み（xattr・full-root・A/B 差し替えは未検証） | #24 | [2026-10-29-s5-overlayfs](../../experiments/2026-10-29-s5-overlayfs.md)（#124 で追加） |
| S6 | kernel hardening | `kernel-hardening-checker` を使い設定差を記録し、必要機能と boot regression を確認する。 | tier A・tier Bの記録あり。全FAILの解消や製品機能との両立を意味しない。 | #31; #28 | [2026-10-19-s06-kernel-hardening](../../experiments/2026-10-19-s06-kernel-hardening.md); [2026-10-19-s06-modules-dep-xz](../../experiments/2026-10-19-s06-modules-dep-xz.md)（#28）; [tier B](../../experiments/2026-10-30-s6-tierb-hardening.md) |
| S7 | IR | IR driver/DT input/output、既存機能と競合する GPIO を調査し、実機送受信を確認する。 | 公式BSP・設定の照合あり。実機送受信は未実施。 | — | — |
| S8 | charger IC | IC driver/DT、状態読み出し、充電状態・電圧表示を実機で検証する。 | 回路・公式BSPの照合あり。充電・状態読み出しの実機試験は未実施。 | — | — |
| S9 | power-fail shutdown | 実電源を切る前後の `powerfail_suo`、shutdown deadline、filesystem recovery を反復測定する。QEMU は GPIO/電源回路を代替しない。 | GPIO6経路のQEMU記録あり。実電断・hold-up・200回反復は未実施。 | — | —; [GPIO6経路](../../experiments/2026-10-20-qemu-powerfail-gpio6.md) |
| S10 | update signature rejection | 署名不正・破損・古い bundle を host test と QEMU で与え、非 active slot と state が変化しないことを確認する。 | 署名拒否と番号比較のQEMU/host記録あり。2026-11-13は本番署名artifactの同一version受理・standby write・B指定起動と改変signature/未署名拒否を確認。実機firmware tryboot・実SDは未確認。 | — | [2026-10-25-s10-update-rejection](../../experiments/2026-10-25-s10-update-rejection.md); [番号比較v2](../../experiments/2026-10-25-s10-version-check.md); [本番署名QEMU受入](../../experiments/2026-11-13-release-signing-qemu.md) |
| S11 | watchdog fallback | 起動中 hang、health failure、watchdog reset 後の slot selection と recovery を QEMU・実機で分けて確認する。 | commit `c01f6e7` の patch から build した QEMU で v3 の 6 mode × 5 回を実施し、判定対象 mode は全て基準を満たした。slot selection と実機は未確認。v2 は別 build の参考値として保持。 | — | [S11 watchdog 実験](../../experiments/2026-10-20-s11-qemu-watchdog.md) |
| S12 | SquashFS codec/block size | gzip/xz/zstd/lz4 と block size ごとに image size、decode throughput、SD I/O、RAM を記録する。 | QEMU とホストで完了（SD I/O と RAM は実機待ち）。icount の `t_ready` で差があったのは xz（+24 %、rootfs −6.1 %）だけで、既定の zstd・128 KiB は変えない | — | [2026-10-25-s12-squashfs-codec](../../experiments/2026-10-25-s12-squashfs-codec.md) |
| S13 | userland `-O2`/`-Os`/LTO | 同一 GCC/config で package/rootfs size、CPU workload、boot timing、build time を比較する。 | 3構成の予備比較の記録あり。n=1・構成差の留保は下記を参照。 | — | —; [3構成比較](../../experiments/2026-10-30-s13-optimize.md) |
| S14 | CPU specialization | `-mcpu`/`-mtune` と kernel CPU options を一つずつ変え、`Image`/package size、命令数、実機時間、全機能を検証する。 | S1と共通のkernel sweep記録あり。mcpu/mtune全体と実機効果の完了ではない。 | — | —; [S1/S14本番](../../experiments/2026-10-30-kernel-sweep-s1-s14.md) |
| S15 | QEMU versions | version と machine/device model 差を記録し、同一 image/command line の機能・virtual-time regression を比較する。 | QEMU 実験済み | 11.0.2 → 11.1.2 で `t_ready` +4.1 %（差あり）。build、machine、plugin は差なし | [2026-10-25-s15-qemu-versions](../../experiments/2026-10-25-s15-qemu-versions.md) |
| S16 | normally-RO `/etc` and `/data` | boot、persistent config, seedrng, updater, fsck/recovery の各 writer が maintenance RW window だけで動くか試験する。 | QEMU で writer 失敗様式・window primitive・電断差を確認（init 設計の実装は未着手） | #24 | [2026-10-29-s16-ro-mounts](../../experiments/2026-10-29-s16-ro-mounts.md)（#122 で追加） |
| S17 | storage fault/speed emulation | `dm-log-writes` + `replay-log`、`dm-flakey`/`dm-delay`、QEMU `blkdebug`/throttle/cache mode を使い、error/replay/prefix ごとに fsck・data invariant を記録する。実 card FTL/timing は含まない。 | QMP throttleとゲストのdm-flakeyによるdrop_writes・error_readsの記録あり。試したQEMU SDモデルではblkdebugのホスト側発火をゲストへ伝播しなかった。これを全てのゲスト障害試験が不可能という意味へ広げない。dm-log-writes再生は5回とも完全一致。実cardのFTL・電断は未確認。 | #24 | [2026-10-29-s17-qmp-throttle](../../experiments/2026-10-29-s17-qmp-throttle.md)（#125）; [2026-10-30-s17-error-injection](../../experiments/2026-10-30-s17-error-injection.md)（#128）; [実験記録](../../experiments/2026-11-01-s17-dmlw-blkdebug.md)（#160 で追加） |

## 状態を訂正するときの留保

- S1/S14の本番記録はPASS 61、QEMU_FAILED 12、TARGET_MISMATCH 5、KEEP_CHANGED 1で、合計79です。題名の80候補とは一致しません。全12件を誤検出と再分類できる証拠は本文から確認できず、成功へ振り替えません。S6のvermagicに関する記述だけで、S1全件の失敗原因を確定しません。
- S13は`-O2`、`-Os`、`-O2+LTO`のn=1比較です。`output4`はFTRACE=yで、厳密な同一構成比較ではありません。`-Os + LTO`同時適用の単独効果と5反復の性能評価は未測定です。製品設定にあることと、効果を分離して測ったことを区別します。
- S10の最初の記録は番号比較前のものです。v2では古い番号・番号なしを既定で拒否し、`--allow-downgrade`でのみ許可します。不正形式は同optionでも拒否します。これは現在の最大番号を改ざんから保護する完全なanti-rollback実装の証拠ではありません。
- S6の`BLK_DEV_WRITE_MOUNTED=n`は製品の`/data`自動拡張と衝突した記録があります。checkerの指摘を減らすだけでは採用しません。

### S13の予備比較で記録された値

[元の結果表](../../experiments/2026-10-30-s13-optimize.md)のQEMUは11.1.2、`icount shift=0,sleep=off`、n=1です。表の到達確認とサイズをそのまま記し、仮想時計の1回測定から同等性や実機速度を判断しません。

| 構成 | rootfs.squashfs | 対`-O2` | 起動の記録 |
|---|---:|---:|---|
| `-O2` | 28,770,304 B | 基準 | `MSD/Linux ready`到達 |
| `-Os` | 22,392,832 B | -22.2% | `ready`到達、root mount 0.74 s |
| `-O2+LTO` | 23,764,992 B | -17.4% | `ready`到達、root mount 1.85 s |

`output4`だけFTRACE=yで、厳密な同一構成ではありません。元の「ノイズ範囲内」「安定性リスクが小さい」という評価を、n=1から確認済みの統計的結論へ引き継ぎません。`-Os + LTO`の同時適用は別の比較が必要です。

## 検証ツールと実行境界

製品buildはbaselineの最終Buildroot/kernel設定・生成物hashを保存してから一つずつ比較します。
[起動script](../../../board/cardputerzero/qemu/run-qemu.sh)の既定機種は`raspi3ap`で、`raspi3b`も選択できます。
QEMUでrootfs・init・更新・watchdogを試しても、GPU firmware、実tryboot、CM0周辺回路・電断・SD性能は確認できません。
仮想時間は`-icount shift=0,sleep=off`等の実際の引数とbinary hashを記録し、実時間性能へ換算しません。
filesystemの障害・速度模擬は[手法と適用範囲](../storage/fault-injection-s17.md#s17-ストレージの障害速度の模擬)を参照します。
各試験の条件・負の対照・5回以上の反復・失敗を[実験一覧](../../experiments/README.md)から辿れる形で保存し、設定採用と試験完了を分けます。

## 実機へ引き継ぐ確認

[カメラの確認手順](../../VERIFY.md)と[実機測定](hardware-measurements.md)で、sensor ID、media topology、CSI1 2-lane raw capture、Liteのprobe failureを採取します。
S番号以外のQEMU記録は[確認範囲](qemu-coverage.md)、当時の実施順は[計画履歴](planning-history.md)に分けています。
