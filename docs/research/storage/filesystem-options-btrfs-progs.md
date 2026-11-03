# Btrfs progsのformat・mount・tune option

[保存領域へ戻る](README.md) / [filesystem option調査](filesystem-options.md) / [Btrfs checksum調査](filesystem-options-btrfs.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版はbtrfs-progs 6.10、最新版は7.3です。一次資料は[固定版mkfs manual](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/mkfs.btrfs.rst)、[固定版mount option](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/ch-mount-options.rst)、[固定版btrfstune](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/btrfstune.rst)、および[v7.3 mkfs](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/mkfs.btrfs.rst)、[v7.3 mount option](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/ch-mount-options.rst)、[v7.3 btrfstune](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/btrfstune.rst)です。実際のkernel supportは製品kernelで未確認です。

## mkfs optionとalias

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-b` / `--byte-count` | filesystem容量 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `/data`容量は`msd-data-grow`がpartition拡張後のdevice sizeに合わせる。mkfsで別sizeを固定しない。 |
| `-d` / `--data` | data profile | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | single/DUP等の容量とcopy repair能力を比較する。SD FTLがDUP copyの物理独立性を保証しない点は[checksum比較](filesystem-options-btrfs.md#data-checksumscrub修復)のとおり。 |
| `-m` / `--metadata` | metadata profile | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | DUPのmetadata追加write・容量とmetadata破損時のread/repairをQEMUと実SDで比較し、SD上のcopy独立性は保証されないと扱う。 |
| `-l` / `-n` / `--nodesize` / `--leafsize` | B-tree node/leaf size | 未確認（資料でdefault未整理） | 可 | `--leafsize`は最新版で廃止 | 実験で比べる | metadata容量、small-file数、RAM、directory latencyを測り、kernel/progs双方で扱える値を選ぶ。 |
| `-s` / `--sectorsize` | filesystem sector size | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | CardputerZeroのlogical/physical sectorとkernel対応を照合し、異なるsizeでformat/mount/fsckを通せる測定がない限り既定を使う。 |
| `-L` / `--label` | filesystem label | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `/data`の既存識別はpartition label `data`。volume labelを追加するならboot時の識別・recovery手順が必要。 |
| `-f` / `--force` | 既存filesystemを上書き | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | production SDで既存signatureを強制無視すると誤消去するため、通常format経路で有効化しない。 |
| `-O` / `--features` | filesystem featureを指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | kernel、mkfs、fsckすべての対応と電断後recoveryを確認したfeatureだけを有効化する。 |
| `-M` / `--mixed` | data/metadataを同一block groupへ配置 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | mixed profileはsmall filesystem向けで、容量、fragmentation、metadata/data更新のwrite amplificationを実SDで比較してから選ぶ。 |
| `-R` / `--runtime-features` | runtime featureを指定 | 未確認（資料でdefault未整理） | 可 | 最新版で廃止 | 除外 | current sourceで廃止されたfeature指定なので、通常のformat設定には加えない。 |
| `-K` / `--nodiscard` | mkfs中のdiscardを抑止 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | discardが未操作時間のdevice commandになる。format時間、discard error、後続write latencyをSD cardで測って選ぶ。 |
| `-U` / `--uuid` / `--device-uuid` | filesystem/device UUIDを指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | image複製時のUUID衝突を避け、`/data`のpartition labelを維持する。 |
| `-r` / `--rootdir` | directory treeからfilesystemを作成 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | rootdir image生成用で、製品起動時にSD上のdata partitionを初期化する用途とは異なる。format時のtree copyを行わない。 |
| `--checksum` / `--csum` | data checksum algorithmを選択 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | CRC32C、xxhash、SHA-256、BLAKE2の速度・CPU時間・checksum collision strengthをCardputerZeroで比較する。algorithmごとの詳細は親文書に記す。 |
| `--shrink` / `-S` | filesystem size/feature conversionを調整 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | format/copy時の容量と変換後のmount/fsckを確認し、`msd-data-grow`後の拡張と干渉しない場合だけ試す。 |

## btrfstuneとfeature

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-u` / `-U` | filesystem UUIDを更新または指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | live dataの識別子を変えるoffline操作。`data` labelを識別に使う製品で通常起動時に実行せず、UUID変更後のfstab/recoveryを同時更新する。 |
| `-M` / `-S` / `-r` / `-x` | btrfstune metadata, seeding, feature conversion controls | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | offline mutationでmetadataを書き換える。実データのcopy、backup、mount/fsck、scrub後の比較が取れる保守作業以外で実行しない。個別featureのkernel対応を検証する。 |
| `--convert-from-block-group-tree` / `--convert-to-block-group-tree` / `--convert-to-free-space-tree` | block group/free-space tree layoutを変換 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | conversionはmetadataを更新しrecovery riskがある。対象image copyで変換前後の容量、mount、fsck、電断復旧を検証する。 |
| `block-group-tree` / `extref` | block-group-tree、extended inode reference feature | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | feature metadataとkernel/progs互換性を確認する。古いkernelでmountできないimageにすると復旧経路を失うため、version matrix試験後に選ぶ。 |
| `raid-stripe-tree` | RAID stripe metadata tree | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | RAID profileを使わない単一SDでは機能を使わず、metadata/write量を増やさない。 |
| `raid56` | RAID5/6 profile support/feature | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | single-device `/data`のprofileではなく、parity repairとmulti-device故障試験がないため対象外。 |
| `zoned` | zoned-device mode | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | CardputerZeroのSDをhost-managed zoned deviceとして使用しない。zone geometryがないdeviceで有効化しない。 |
| `mixed-bg` / `quota` / `squota` | mixed block group、quota、simple quota | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | mixed profileはsmall filesystem向け。quotaを使うpolicy・管理toolはなく、accounting metadataとwriteを追加しない。 |

## mount option

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `max_inline` | inline file dataの上限 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | inline化によるmetadata writeとsmall-file readの差、B-tree node容量を比較し、実際のfile size分布で改善が確認された場合だけ変える。 |
| `metadata_ratio` | data blockに対するmetadata割当比率 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 小さなSDでmetadata reservationによるdata容量損失を計算し、free-space不足やmetadata ENOSPCを再現した場合にだけ調整する。 |
| `noatime` | access time更新を止める | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 未操作readによるmetadata writeを抑える候補。Btrfs mount後のwrite traceと既存atime依存がないことを確認する。 |
| `noautodefrag` | automatic defragを無効化 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | defragは読み取り後のdata再配置writeを起こし得る。`/data`のfragmentationとread latency改善が測れない場合は自動defragを走らせない。 |
| `nospace_cache` | free-space cacheを無効化 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | cache writeの抑制とmount/allocation時のscan量を比較し、mount latency・metadata read・write traceが改善する場合だけ設定する。 |
| `context` | SELinux context mount override | 未確認（資料でdefault未整理） | v7.3資料に記載 | 最新版で追加; 版上げで使える候補 | 既定のまま | generic VFS security optionであり、Btrfs固有の容量・checksum動作を変えない。SELinux policyを導入しない現行imageでは指定しない。 |

v7.3の追加optionとして`--compress`、`--subvol`、`--inode-flags`、`--reflink`、btrfstuneのquota/feature conversion、mount文書の`context`を扱います。`--inode-flags`の`nodatacow`はdata checksumを無効にし得るため、破損検出を優先する`/data`には適用しません。その他の新optionと既存optionのdefault変更はsource tokenとrelease docsで差分を確認し、default変更は見つかりませんでした。Linux mainlineのBtrfs kernel documentationは[7.4-rc1](https://github.com/torvalds/linux/tree/v7.4-rc1/Documentation/filesystems/btrfs)です。
