# cramfs と XIP（Execute-In-Place）の調査

CardputerZero の起動高速化の候補として、ROM 向けファイルシステム cramfs と、ストレージ上のコードをコピーせず直接実行する XIP を調査した。判定を先にまとめる。

- **cramfs**: mainline に残る read-only 圧縮 FS。block device 経由で QEMU 検証は可能だが、zlib 圧縮・16MB/ファイル制限・メタデータ簡素化という古い仕様で、現行 SquashFS+zstd を上回る根拠がない。実測して不採用を確定した（末尾の実測）。
- **XIP**: ストレージを CPU のメモリ空間に直接マップする必要があり、SD カード（block device）では実現できない。カーネル本体の XIP は 32bit ARM の NOR flash 前提で arm64/BCM2837 では対象外。代替の AXFS も上流から外れて消滅。**適用不能として除外**。

## cramfs の仕様と制約

Linux 6.18 でも `CONFIG_CRAMFS` として mainline に存在する。構成は Buildroot の `BR2_TARGET_ROOTFS_CRAMFS` で提供される（生成ツールは npitre/cramfs-tools の mkcramfs）。

| 項目 | 仕様 |
|---|---|
| 圧縮 | zlib。1 ページずつ圧縮しランダムアクセス可能。メタデータは非圧縮 |
| 書き込み | 不可（作り直し更新のみ） |
| ファイルサイズ | 16MB 未満 |
| ファイルシステム | 256MB 強（末尾ファイルのみ超過可） |
| gid | 下位 8bit のみ保存（mkcramfs が切り詰めるためセキュリティ上の注意あり） |
| ハードリンク | 保存されない（link count 常に 1、内容重複は共有） |
| タイムスタンプ | 保存されない（常に epoch=1970 に戻る） |
| エンディアン | host 依存（`mkcramfs -B/-L` で強制可能） |
| ブロックサイズ | 4096 固定 |

SquashFS（zstd・>16MB 可・xattr・連続 file data packing）と比較して、圧縮率・機能ともに劣る。現行イメージ（squashfs 約 22MB）は 256MB 制約内ではあるが、優位点がない。

## XIP の要件と MSD/Linux への適用可否

XIP は「ROM/flash 上のコードを RAM にコピーせず、そのまま実行する」方式で、非常に小さな RAM の組込み機器を対象とする。3 経路を検討したが、いずれも CardputerZero の SD 起動では成立しない。

1. **CRAMFS_MTD + XIP**: `CONFIG_CRAMFS_MTD` は cramfs image を block device ではなく物理リニアメモリ（NOR flash 等）から直接読み、非圧縮でアライメントされたデータブロックを user space へ直接マップして XIP を提供する。前提として、image の物理アドレスを指定した MTD デバイスと、`point` メソッドを持つマップドライバー（`cfi_cmdset_0001`・`physmap`）が必要で、`root=mtd:name` で起動する。CardputerZero の rootfs は SD カードの block device 上にあり、物理メモリにマップされた flash が存在しないため適用できない。
2. **CONFIG_XIP_KERNEL**: カーネル自体を flash 上で実行する `CONFIG_XIP_KERNEL` は `depends on !ARM_LPAE` の 32bit ARM 専用で、非圧縮カーネルを NOR flash の固定物理アドレスに置く前提。arm64 の BCM2837 では対象外であり、Raspberry Pi の起動系は firmware が SD からカーネル Image を RAM に読み込む方式で、XIP の経路も存在しない。
3. **AXFS**: XIP 専用 FS（Advanced XIP File System）は mainline に入らず out-of-tree のまま 2019 年以降更新がなく、Buildroot 側も廃止した。現行 vendor の Buildroot では `Config.in.legacy` に `BR2_TARGET_ROOTFS_AXFS = "AXFS root filesystem has been removed"` とだけ残っており、選択肢として消滅している。

残る XIP 系の選択肢（RomFS on NOR 等）も、メモリマップ可能な flash ストレージがないという同じ前提で不適となる。

## 結論

- rootfs の圧縮 RO 領域は SquashFS+zstd（現行）が cramfs・AXFS より適切。例外として cramfs は block 経由で動作するため QEMU 比較だけは可能であり、実測で不採用を確定させた。
- XIP はストレージ形態（SD = block device・メモリマップ不可）とアーキテクチャ（arm64）の両面で適用不能。起動高速化は XIP 以外（既採用の quiet・FTRACE off・squashfs -sort 等）で積み上げる方針を維持する。

## QEMU での cramfs rootfs 実測

`CONFIG_CRAMFS=y` を追加したカーネルと host-cramfs の mkcramfs で rootfs.cramfs（25,198,592 B、squashfs 22.3MB に対し約 13% 増）を生成し、sdcard p5 に書き込んで QEMU 起動を確認した。`MSD/Linux ready`・login・/data マウント・serial チェックの全ゲートを通過するが、サイズと制限（file<16MB、gid 8bit、timestamp なし）で優位点がなく、不採用を確定した。詳細は [実験記録](../../experiments/2026-10-31-cramfs-rootfs.md)。

## 出典

- [Linux cramfs documentation](https://docs.kernel.org/6.18/filesystems/cramfs.html)【一次】仕様・制約・CRAMFS_MTD の XIP 要件
- `vendor/buildroot/fs/cramfs/Config.in`【一次】`BR2_TARGET_ROOTFS_CRAMFS`・`BR2_TARGET_ROOTFS_CRAMFS_XIP` と `CRAMFS_MTD` の要否
- `vendor/buildroot/Config.in.legacy`【一次】`BR2_TARGET_ROOTFS_AXFS` の廃止記述
- [npitre/cramfs-tools](https://github.com/npitre/cramfs-tools)【一次】mkcramfs
