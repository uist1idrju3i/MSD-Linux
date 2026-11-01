# cramfs ルートファイルシステムの QEMU 起動確認

- 日付: 2026-10-31
- 目的: docs/research の FS 候補表で「reference」としていた cramfs を、block device 経由の rootfs として実際に起動し、現行 SquashFS との優劣を実測で確定する。

## 条件

- ベース: main（kernel 6.18.58-v8、PREEMPT_RT、hardening 16 件・`-Os`+LTO 適用済み）
- カーネル: 現行 product 構成に `CONFIG_CRAMFS=y` を追加して再構築（`output/build/linux-custom`、#107 SMP PREEMPT_RT）
- rootfs: `output/host/bin/mkcramfs output/target output/images/rootfs.cramfs`（Buildroot の `host-cramfs` で生成、`BR2_TARGET_ROOTFS_CRAMFS` 相当）
- sdcard 注入: sdcard.img をコピーし、`dd bs=512 seek=311296 conv=notrunc` で p5（rootfs-a）に cramfs を書き込み
- 起動: `ROOT_FSTYPE=cramfs KERNEL_IMAGE=<再構築 Image> QEMU_ICOUNT=shift=0,sleep=off test-qemu.sh <image>`（msd-dev コンテナ内。`ROOT_FSTYPE` は msd-dev の環境変数フォワード対象外のためコンテナ内で指定）

## 生の値

| 項目 | cramfs | squashfs（現行） |
|---|---:|---:|
| rootfs image | 25,198,592 B | 約 22.3 MB（`-sort`+zstd22） |
| QEMU ready | 177 s（実時間、build 並走） | 同条件下の測定では数秒〜十数%の範囲 |
| 起動 | `MSD/Linux ready` 到達・login・/data mount・serial ゲート全通過 | — |

mkcramfs の警告: `gids truncated to 8 bits (this may be a security concern)`（mkcramfs が gid を 8bit に切り詰める既知の制限）。

## 失敗した試行

- ホストの `test-boot.sh` は `ROOT_FSTYPE=squashfs` をハードコードするため override できず、`test-qemu.sh` を直接呼んだ
- `ROOT_FSTYPE=cramfs` を msd-dev の起動引数側に置くとコンテナへ伝わらず、`rootfstype=squashfs` のまま起動して `Unable to mount root fs` で panic。コンテナ内で環境変数を指定して解決
- `CONFIG_CRAMFS=y` 化は autoconf.h が変わるためほぼ全再ビルドになった

## 結論

block device 経由の cramfs rootfs は QEMU で正常に起動する。ただし image は squashfs（zstd）より約 13% 大きく、file<16MB・fs 256MB 強・gid 8bit・timestamp なしという制限のため優位点がない。**不採用を確定**し、rootfs は現行 SquashFS+zstd を維持する。XIP 系は SD の block device では適用不能（[cramfs と XIP の調査](../research/cramfs-xip.md)）。

## 再現

1. `output/build/linux-custom` の `.config` に `CONFIG_CRAMFS=y` を加えて `olddefconfig`→`Image` を再構築
2. `make -C output host-cramfs` で mkcramfs を作り、`output/host/bin/mkcramfs output/target rootfs.cramfs`
3. sdcard.img コピーの p5（offset 311296×512）に dd で書き込み、`ROOT_FSTYPE=cramfs` で QEMU 起動
