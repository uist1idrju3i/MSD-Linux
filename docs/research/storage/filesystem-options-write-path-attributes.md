# fileごとの属性とF2FS ioctl

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 範囲と出典

e2fsprogs 1.47.4の`chattr(1)`、btrfs-progs 6.10/7.3の`btrfs property`、Linux固定版6.18.59とmainline 7.4-rc1のF2FS ioctl関連記述を比較しました。file attributeはfilesystemとkernelの組み合わせで可否が異なります。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
|---|---|---|---|---|---|---|
| `chattr:a` `chattr:i` `chattr:A` `chattr:d` `chattr:E` `chattr:F` `chattr:I` `chattr:e` `chattr:N` `chattr:P` `chattr:t` `chattr:T` `chattr:u` `chattr:x` `chattr:X` | append-only、immutable、atime、backup hint、encryption/casefold/project/extents等の属性 | filesystem/file依存 | e2fsprogs可、kernel supportはfs依存 | 同 | 既定のまま | `chattr`が受理することとfilesystemが設定可能なことは別。attribute変更はuser operation中だけ行い、権限・backup・unlock回復を確認する。 |
| `chattr:D` `chattr:S` | directory/file変更を同期する | 無効 | fs依存 | 同 | 実験で比べる | 書き込みは操作中に完了するがSDのwrite量・回数とwearが増える可能性がある。同期性と電断窓を測る。 |
| `chattr:c` `chattr:m` `chattr:C` `chattr:j` `chattr:s` | compression、CoW、journal、secure deletion | fs依存 | fs依存 | 同 | 実験で比べる | data layoutとjournal量に影響する。file単位のbackground write、復旧性、SD write amplificationを測り、未操作時writeがないことを確認する。 |
| `btrfs:compression` | Btrfs per-file compression | filesystem default | 可 | 同 | 実験で比べる | compression gain、CPU cost、writeback時機を利用者操作中に測る。 |
| `btrfs:label` | filesystem label | filesystem作成時 | 可 | 同 | 既定のまま | format時に固定label `data` を設定し、稼働中に変更しない。 |
| `btrfs:ro` | Btrfs propertyでread-onlyを設定 | read/write | 可 | 同 | 実験で比べる | maintenance/recovery時に利用者が開始しprogressを表示する操作に限定する。 |
| `F2FS_IOC_SET_PIN_FILE` | F2FS fileをpinned扱いにする | 未設定 | 可 | 同 | 実験で比べる | GCによる移動を抑える効果と空き領域・wear偏りを測る。 |
| `F2FS_IOC_COMPRESS_FILE` `F2FS_IOC_DECOMPRESS_FILE` `F2FS_IOC_RESERVE_COMPRESS_BLOCKS` `F2FS_IOC_RELEASE_COMPRESS_BLOCKS` | file compressionと圧縮領域の予約/解放 | mount/feature依存 | 可 | 同 | 実験で比べる | compression/space reservationはuser-requested file operationとして進捗を表示し、処理後のwrite量と未操作時のbackground writeを測る。 |
| `chattr:V` | chattrのversion表示 | 実行時だけ | 可 | 同 | 除外 | 診断用の表示optionであり、filesystem属性の設定・write pathの判断対象ではない。 |

`chattr`の文字は実装の有無を表す一覧ではありません。最終判断には各filesystemのprimary documentationと実機でのioctl結果を使います。

## 出典

- [e2fsprogs v1.47.4 chattr.1](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/chattr.1.in)
- [btrfs-progs v6.10 btrfs-property](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/btrfs-property.rst)、[v7.3](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/btrfs-property.rst)
- [固定版 F2FS documentation](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/filesystems/f2fs.rst)、[Linux v7.4-rc1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/filesystems/f2fs.rst?h=v7.4-rc1)
