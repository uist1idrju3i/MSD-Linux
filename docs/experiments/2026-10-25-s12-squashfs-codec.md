# S12 SquashFS の圧縮方式と block size

- 状態: 実施中
- 日付: 2026-10-25
- 担当: Devin
- 関連: [シミュレーション検証計画](../research/simulation-plan.md)、[起動時間の QEMU 測定](2026-10-20-qemu-boottime.md)、`board/cardputerzero/tools/bench/s12-squashfs-codec.sh`

## 目的と仮説

rootfs の SquashFS は、いまは zstd、block size 128 KiB です（`BR2_TARGET_ROOTFS_SQUASHFS4_ZSTD`、`BR2_TARGET_ROOTFS_SQUASHFS_BS_128K`）。圧縮方式と block size を変えたときの rootfs のサイズと、QEMU の icount での起動時間を測ります。

仮説は次のとおりです。

- サイズは xz が最も小さく、lz4 と lzo が最も大きい。
- icount の起動時間は、展開の命令数が少ない lz4 が最も短く、xz が最も長い。ただし、起動で読む量は rootfs の一部なので、差は数 % に留まる。
- block size を大きくすると、サイズは小さくなる。起動時間は、小さなファイルを読むたびに大きな block を展開するので、長くなる。

## 採否の基準（結果を見る前に書く）

- 主指標は、通常起動 5 回の `t_ready` の中央値（icount）です。基準は zstd128a（いまの設定）です。
- 差が「A/A の差（zstd128a と zstd128b の中央値の差）の 2 倍」と「基準の 5 %」の両方を超えたときだけ、差があるとみなします。
- サイズは、mksquashfs の出力のバイト数をそのまま比べます。rootfs の A/B パーティションに入らない条件は不採用とします。
- QEMU は SD カードの読み出しの速さを模していません。icount の仮想時間は、ゲストの命令数を表します。そのため、QEMU の結果だけでは既定の設定を変えません。差があった条件は、実機で測る候補として残します。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `87aadf5c27846838d2eb16f2f81bb62675569b16`（ビルド）。runner は `703beec11b29c9bc68698f5a4d461cb70838c7d6`（S12 のブランチ。`run-boottime.sh` に `--squashfs-comp` と `--squashfs-block` を足しただけ） |
| ホスト | Ubuntu 26.04.1 LTS、12 CPU。開発用イメージ（`docker/msd-dev`）の中で実行 |
| QEMU | `QEMU emulator version 11.1.2`（開発用イメージ）、machine `raspi3ap`、`QEMU_ICOUNT=shift=0` |
| mksquashfs / unsquashfs | `mksquashfs version 4.7.5 (2026/03/01)`（Buildroot の `output/host/bin`） |
| カーネル | `rpi-6.18.y` の `234188315037848e5b07d65b85d38edc64095caa`。`CONFIG_SQUASHFS_ZLIB`、`_LZ4`、`_LZO`、`_XZ`、`_ZSTD` がすべて `y`、`CONFIG_SQUASHFS_DECOMP_SINGLE=y` |
| 入力 | `Image` SHA-256 `1c085405fedf067be7c8efeadd1f1a779896baa7de60d6ed139f7faf3c5eb8a3`、基準の rootfs `28164bdda81a7ca44e87c444937d01db62cee29a41b33a75e7a4231f7678434b`、DTB `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` |
| 変える条件 | 圧縮方式（zstd、gzip、xz、lz4、lzo）と block size（128 KiB、256 KiB、1 MiB）。block size を変えるのは zstd だけ |
| 変えない条件 | rootfs の中身（基準の rootfs を展開し、起動時間の測定用の `rcS` と `S99zz-boottime-dump` を足したもの）、mksquashfs の他の option（`-noappend -all-root -no-xattrs`）、カーネル、DTB、カーネルの引数 |
| 繰り返し | 条件ごとに初回起動 1 回と通常起動 5 回。集計は通常起動 5 回の中央値と最小・最大。ホストでの展開時間（`unsquashfs -processors 1`）は 5 回 |
