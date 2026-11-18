# /data初期設定の同期方式

[保存領域の索引へ](README.md)

2026-11-18。対象はgrow・mkdir後に残ったmetadataのwritebackです。mount policy、progress UI、実SDの電源断保証は別です。

## 一次資料で確認したこと

固定kernelの`fs/sync.c`では、`syncfs(fd)`はfdのsuperblockに対して`sync_filesystem()`を呼びます。同関数はinodeのwriteback、filesystemの`sync_fs(wait=1)`、最後に`sync_blockdev()`を呼び、block deviceのdirty bufferの完了を待ちます。ext4の`sync_fs()`によるjournal commit待ちだけで終了する経路ではありません。これはsource上の確認であり、対象metadataの本来位置への書き込みは別途QEMU traceで検証します。

Linux 5.8以降のsyncfsはfilesystemのwriteback errorも返します。一方、固定BusyBox 1.38.0の`sync_common()`は`syncfs(fd)`の戻り値を無視します。古い「EBADFだけ」というcommentのままで、EIOを成功と扱い得ます。

## 方式の比較

| 方式 | build・実行option | 対象とerror | 採否 |
|---|---|---|---|
| BusyBox既定sync | `CONFIG_SYNC=y`、`CONFIG_FEATURE_SYNC_FANCY`無効。引数なし | 全filesystem。sync syscall自体にerror戻り値がない | 対象外への同期を避けるため不採用 |
| BusyBox sync拡張 | `CONFIG_SYNC`、`CONFIG_FEATURE_SYNC_FANCY`を有効化。`-f FILE...`はsyncfs、`-d FILE...`はfdatasync、FILEだけならfsync、引数なしなら全体sync。`-d`と`-f`は排他 | `-f /data`は範囲を満たすが固定版では同期errorを無視する | vendor patchが必要になるため不採用。fragmentだけでは要件を満たさない |
| 専用helper | `BR2_PACKAGE_MSD_SYNCFS=y`。`msd-syncfs DIRECTORY`、環境変数・設定fileなし | directoryをread-onlyでopenしsyncfs。open・syncfs・close失敗をstderrと非zeroで返す | 採用。既存libcのみ。BuildrootのTARGET_CFLAGS/TARGET_LDFLAGSを継承する |
| 全体syncを自前呼出し | `sync()` | 全filesystem。同期errorを呼出し側で取得できない | 不採用 |

helperはrepo内のGPL-2.0-only sourceです。新しい外部依存・vendor更新はありません。固定BusyBoxの`CONFIG_FSYNC`は既に有効ですが、directoryのfsyncだけをfilesystem全体の同期の代用にはしません。fsync appletの`-d FILE...`はmetadataを同期しないため不採用です。上流の版更新・patchは今回行わず、固定版の挙動に基づいて選びます。

## 初回に限る条件

永続markerは追加しません。format、fsck修正、grow前後の実block数変化、必要directoryの不在をdirtyの根拠にします。grow・mkdirの途中失敗やblock数の読取り不能の場合は、書いた可能性があるため同期を省略しません。既に収録済みの`LC_ALL=C dumpe2fs -h DEVICE`の`Block count:`を比較します。headerを読むだけで、write optionはありません。両directoryとblock数が変わらない通常起動ではhelperを呼びません。mountそのものの書き込みをなくす変更ではありません。

最初は`df -Pk /data`で比較しましたが、固定Linuxの`ext4_statfs()`は総block数からmetadata overheadを引きます。filesystemの実block数とは異なり、未知のgeometryで増加を見落とさない根拠にできないため不採用としました。`resize2fs`は実block数が同じなら`Nothing to do!`から書換え前に終了します。固定sourceの分岐を根拠に、実block数を比較します。

dumpe2fsの実行optionは固定sourceの`-b`、`-f`、`-g`、`-h`、`-i`、`-m`、`-x`、`-V`、`-o`を照合しました。採用するのはheaderだけを読む`-h`です。bad block一覧、強制読取り、group一覧、image、MMP、16進表示、version、代替superblock指定は判定に使いません。open flagに`EXT2_FLAG_RW`はありません。errorでもheaderが出る経路があるため、pipelineの最終statusに頼らず、dumpe2fs自身の終了値と解析値の両方を検査します。

## 出典

- [固定Linuxのsync.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/sync.c)
- [固定Linuxのext4 super.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/super.c)
- [BusyBox 1.38.0 sync.c](https://git.busybox.net/busybox/tree/coreutils/sync.c?h=1_38_0)
- [BusyBox 1.38.0 df.c](https://git.busybox.net/busybox/tree/coreutils/df.c?h=1_38_0)
- [固定e2fsprogsのresize/main.c](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/resize/main.c?h=v1.47.4)
- [固定e2fsprogsのmisc/dumpe2fs.c](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/misc/dumpe2fs.c?h=v1.47.4)
- [Linux man-pages sync(2)](https://man7.org/linux/man-pages/man2/sync.2.html)
- [測定計画と結果](../../experiments/2026-11-18-data-syncfs.md)
