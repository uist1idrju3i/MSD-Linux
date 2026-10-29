# EROFS ルートファイルシステムの比較（QEMU）

SquashFS（zstd）の代替として EROFS を試し、サイズと起動を QEMU で比較した記録です。

## 条件

- 日付: 2026-10-29
- カーネル: 6.18.58-v8（`CONFIG_EROFS_FS=y`、`CONFIG_EROFS_FS_ZIP_ZSTD=y` は既に有効）
- Buildroot: 2026.08.x（`BR2_TARGET_ROOTFS_EROFS`、host-erofs-utils 1.8.10）
- QEMU: 11.1.2（patched、`QEMU_ICOUNT='shift=0,sleep=off'`、`QEMU_COPY_IMAGE=1`）
- defconfig からの差分は rootfs 形式の追加のみ（`output2/` 別ツリーで同一 defconfig をビルド）

## 手順

1. `make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output2" msd_cardputerzero_defconfig`
2. `.config` に `BR2_TARGET_ROOTFS_EROFS=y` を追加
3. `sdcard.img` の p5（rootfs-a、start=311296）に `rootfs.erofs` を `dd` で書き込み
4. `ROOT_FSTYPE=erofs` で `run-qemu.sh` を実行して起動を確認

## 生の値

| 項目 | SquashFS（zstd） | EROFS（lz4hc, level 9） |
|---|---|---|
| rootfs サイズ | 23,904,256 B | 30,851,072 B（+29.1%） |
| `VFS: Mounted root` のゲスト時刻 | 1.8608 s | 1.8268 s |
| 起動到達 | ready 到達 | ready 到達（`erofs (device mmcblk0p5): mounted` を確認） |

同じビルドツリーの SquashFS イメージと EROFS イメージで、root マウントのゲスト時刻に差は見られなかった。

## 失敗した試行

- `BR2_TARGET_ROOTFS_EROFS_CUSTOM_COMPRESSION=y` + `zstd`: host の `mkfs.erofs 1.8.10` が `Cannot find a valid compressor zstd` で失敗。Buildroot の host-erofs-utils は `--without-libzstd` 固定で、`BR2_PACKAGE_HOST_ZSTD` の選択肢もない。lz4hc（level 9）に切り替えて成功。
- `msd-qemu-test:local` イメージでは `qemu-system-aarch64` が PATH に無く run-qemu.sh が途中で終了する。QEMU 実行は `msd-dev:local`（`/usr/local/bin/qemu-system-aarch64`）で行う必要がある。

## 結論

- EROFS rootfs は現行カーネル設定のまま QEMU で起動できる（追加のカーネル変更は不要）。
- ただし利用可能な lz4hc では SquashFS+zstd より約 29% 大きく、起動時間にも有意差は見られない。rootfs 容量が直接パーティションサイズと読み込み量に効く現状では、SquashFS+zstd の維持が妥当。
- zstd での EROFS を試すには Buildroot の host-erofs-utils に libzstd を有効化する変更が要る（vendor/ の編集が必要なため今回は見送り）。

## 未検証

- zstd 圧縮の EROFS（host 側 libzstd 有効化後のサイズ・速度）
- 実機 SD カード上での読み込み速度差（QEMU のファイルベース drive では再現できない）
- lzma 圧縮（圧縮率は高いが解凍が遅いため見送り。未測定）
