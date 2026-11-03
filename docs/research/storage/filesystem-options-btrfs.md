# Btrfsのformat、mount、checksum

[保存領域へ戻る](README.md) / [option調査の索引](filesystem-options.md) / [調査の索引](../../../RESEARCH.md)

全mkfs alias、mount、feature、btrfstune tokenの照合は[追加option表](filesystem-options-btrfs-progs.md)を参照してください。

## 範囲と出典

固定版はbtrfs-progs 6.10とkernel 6.18.59、最新版はbtrfs-progs 7.3とmainline kernel 7.4-rc1です。一次資料は[btrfs-progs v6.10 mkfs manual](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/mkfs.btrfs.rst)、[v6.10 mount options](https://github.com/kdave/btrfs-progs/blob/v6.10/Documentation/ch-mount-options.rst)、[v7.3 mkfs manual](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/mkfs.btrfs.rst)、[v7.3 mount options](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/ch-mount-options.rst)、[v7.3 btrfstune](https://github.com/kdave/btrfs-progs/blob/v7.3/Documentation/btrfstune.rst)、[v7.3 release](https://github.com/kdave/btrfs-progs/releases/tag/v7.3)、[固定kernel Btrfs documentation](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/filesystems/btrfs.rst)、[mainline v7.4-rc1](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/filesystems/btrfs.rst)です。

`CONFIG_BTRFS_FS`は[製品kernel fragment](../../../board/cardputerzero/linux.fragment)で無効です。以下は候補の比較であり、MSD/LinuxがBtrfsを利用可能とする判断ではありません。固定版または最新版のoptionをBuildroot、kernel、QEMU、実機で試していません。

## 未操作時のwriteと長時間maintenance

scrubとbalanceはtimerで定期起動せず、user-initiated maintenanceとしてprogressを表示する。scrubのread/checkとrepair write、balanceのextent relocationがidle中に走らないことをblock traceで確認する。format、check、repairも長時間処理ならprogressを表示し、利用者の開始なしにSDを更新しない。

## mkfs、profile、feature

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-b` | filesystem size | device全体 | 可 | 同 | 既定のまま | `/data`の容量はpartition grow後のdevice sizeで決まる。`msd-data-grow`がpartitionを拡張してからfilesystemを拡張するため、mkfsで別sizeを固定しない。 |
| `-d` | data profile | single | 可 | 同 | 実験で比べる | profile別の容量・故障回復を仮想deviceで比較する。 |
| `-m` | metadata profile | device数で選択 | 可 | 同 | 実験で比べる | DUP/RAID1の容量・複製の意味を確認する。 |
| `-s` | sectorsize | kernel/device依存 | 可 | 同 | 既定のまま | 変更にはCardputerZeroのblock logical/physical sector sizeとBtrfs kernel対応の照合が必要。異なるsector sizeでmount/fsckできる確認が取れた場合だけ変える。 |
| `-n` | nodesize | sectorsize | 可 | 同 | 既定のまま | 小file数、metadata量、RAM使用量、directory操作の比較で既定値より利点が確認された場合に変える。 |
| `-L` | label | なし | 可 | 同 | 既定のまま | 現行の`/data` labelは`data`で固定され、Btrfsを使う場合も同じ識別名で足りる。 |
| `-f` | existing filesystemを上書き | 無効 | 可 | 同 | 除外 | format時の誤消去を避ける。 |
| `-O` | filesystem featureを選択 | tool既定 | 可 | 同 | 既定のまま | featureを追加するのは、CardputerZeroのkernel、mkfs、fsck全てが対応し、起動と復旧試験が通った場合に限る。 |
| `--nodiscard` | format時discardをしない | discardを試みる | 可 | 同 | 実験で比べる | 同じSD cardでdiscard有無のformat時間、discard error、続くrandom/sequential write latencyを測り、discardが遅いか失敗する場合に選ぶ。 |
| `--rootdir` | directoryからimageを作成 | なし | 可 | 同 | 除外 | 実行時block deviceのformatではない。 |
| `--csum crc32c` | 32-bit CRC checksum | crc32c | 可 | 同 | 実験で比べる | 既定かつhardware accelerationのあるCPUで高速。CRCの検出能力とCardputerZeroのread/write throughputを基準として測る。 |
| `--csum xxhash` | 64-bit non-cryptographic checksum | crc32c | 可 | 同 | 実験で比べる | upstream説明では高速でCRC32Cより衝突耐性が高い。速度・CPU負荷を実測する。 |
| `--csum sha256` | 256-bit cryptographic hash | crc32c | 可 | 同 | 実験で比べる | 衝突耐性を重視する候補だが、upstream測定ではCRC32Cより遅い。 |
| `--csum blake2` | BLAKE2b-256 checksum | crc32c | 可 | 同 | 実験で比べる | cryptographic-strengthで、upstream説明ではSIMD等で高速化可能。実機性能を測る。 |
| `single` | 1 data copy | data既定 | 可 | 同 | 実験で比べる | capacity効率は高いが、device内複製による修復を提供しない。 |
| `DUP` | 1 device内に2 logical copy | metadataの単一device既定 | 可 | 同 | 実験で比べる | metadata領域とwrite量が増える一方、SD FTLがcopyを同じphysical unitへ置く可能性がある。virtual-device error injectionでrepair動作を確認しても実カード上の独立性は保証できない。 |
| `RAID1` / `RAID1C3` / `RAID1C4` | 複数deviceへ複製 | single | 可 | 同 | 除外 | multi-device構成がない。 |
| `RAID0` / `RAID10` | 複数deviceへstripe | single | 可 | 同 | 除外 | multi-device専用で、data冗長化を満たさない。 |
| `RAID5` / `RAID6` | parity profile | single | 可 | 同 | 除外 | multi-device・parity recoveryの検証がない。 |
| `no-holes` | data extentにholeを作らない | feature既定 | 可 | 同 | 既定のまま | 新規formatする`/data`に既存Btrfs imageとの互換要件はなく、holeを省く利点もないためmkfs既定のsparse extent対応を使う。 |
| `skinny-metadata` | compact metadata extent | 有効 | 可 | 同 | 既定のまま | 既定featureを維持し、metadata使用量を比較して無効化に利点があると分かった場合だけ変える。 |
| `free-space-tree` | free-space cache tree | 有効 | 可 | 同 | 既定のまま | 新規`/data`のallocation時に既定のfree-space treeを使い、mount/space-allocation時間を測って差が出た場合にだけ変更する。 |
| `--compress <algo>[:<level>]` | `--rootdir`から作るimage内のfileを圧縮 | なし | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | image作成時のCPU時間と保存byte数を比較し、rootfs/data image作成に使う場合だけ評価する。 |
| `--subvol <type>:<subdir>` | `--rootdir`内のdirectoryをsubvolumeにする | なし | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | subvolume単位のsnapshot/rollback運用を採用しない限り`/data`の通常directory構成には不要。 |
| `--inode-flags <flags>:<path>` | `--rootdir`内のpathへ`nodatacow`/`nodatasum`を指定 | なし | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | 対象fileを限定してもdata checksumを失うため、検出範囲を狭める実測・要件がない限り有効化しない。 |
| `--reflink` | `--rootdir` imageへのfile extent cloneを試す | 無効 | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | sourceとimageが同一filesystem上にある場合のmkfs時間を比較する。実行環境の配置条件も満たす必要がある。 |

## btrfstune

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `--enable-simple-quota` | simple quota accountingを有効にする | 未確認（資料でdefault未整理） | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | subvolume単位の容量制限を運用する要件がない。導入するならquota更新負荷と容量制限の有効性を測る。 |
| `--remove-simple-quota` | simple quota構造を削除する | 未確認（資料でdefault未整理） | 固定版6.10では不可。7.3で追加 | 最新版で追加; 版上げで使える候補 | 実験で比べる | 通常起動時の設定ではなく、quota移行・復旧時だけ使う保守操作。 |
| `--version` | versionとbuiltin featuresを表示 | 未確認（資料でdefault未整理） | 固定版6.10では不可。7.3で追加 | 同 | 除外 | 診断用の表示optionで、filesystem formatやmount設定を変えない。 |

その他の`mkfs.btrfs`のUUID・label・device path・force・help/verbose指定は、識別値や実行制御です。現行data imageと比較する必要がない項目は設定候補にせず、UUIDを固定して複製しません。device複数指定とRAID profileはsingle-device製品layoutと合わないため除外します。

## mount option

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `compress=` | file data compression | 無効 | 可 | 同 | 実験で比べる | `/data`のfile-size/contents representative sampleでalgorithmごとのCPU時間、compressed bytes、read/write latencyを測り、容量節約がCPU負荷に見合う場合に設定する。 |
| `compress-force=` | compressible判定を越えて圧縮 | 無効 | 可 | 同 | 実験で比べる | `compress=`との保存量・CPU時間・低圧縮fileのlatencyを比較し、圧縮判定を越える分に追加の利点がある場合だけ使う。 |
| `datacow` / `nodatacow` | data copy-on-write | 有効 | 可 | 同 | 既定のまま | `nodatacow`はdata checksumも無効にするため。 |
| `datasum` / `nodatasum` | data checksum | 有効 | 可 | 同 | 既定のまま | `nodatasum`はdata破損検出を無効化する。 |
| `discard` / `discard=sync` / `discard=async` / `nodiscard` | freed blockのdiscard policy | async（device対応時） | 可 | 同 | 実験で比べる | 同一cardで同期/非同期/無効のdiscard時間、discard error、解放後のwrite latencyを記録し、controllerが処理できるmodeだけ選ぶ。 |
| `degraded` | device不足でもmount | 無効 | 可 | 同 | 除外 | single-device構成の通常bootで不足deviceを許容しない。 |
| `device=` | mount時に追加device指定 | 自動検出 | 可 | 同 | 除外 | multi-device layoutがない。 |
| `ro` / `rw` | read-only / read-write mount | rw | 可 | 同 | 既定のまま | `/data`の現行write pathを使うにはrwが必要。Btrfsを採用しない限り、現行ext4 mountは変えない。 |
| `acl` / `noacl` | POSIX ACLを有効化・無効化 | enabled（kernel config依存） | 可 | 同 | 既定のまま | permission policyを変える要件がない。 |
| `space_cache=` | free-space cache方式 | v2 | 可 | 同 | 既定のまま | 変更はmount後のallocation latencyとmemory使用量の比較でv2より改善した場合に限る。 |
| `autodefrag` | 小さいrandom writeを再配置 | 無効 | 可 | 同 | 実験で比べる | `/data`で小さなrandom rewriteが占めるbyte比と、autodefragのCPU/write amplification、read latencyを測り、read改善がwrite増加に見合う場合だけ有効化する。 |
| `flushoncommit` / `noflushoncommit` | transaction commit時のflushを選ぶ | 無効 | 可 | 同 | 実験で比べる | commit latency、dirty dataの電断時損失量、flush command処理時間を比較し、durability要件を維持できる設定だけ選ぶ。 |
| `commit=` | transaction commit interval | 30秒 | 可 | 同 | 実験で比べる | commit間隔ごとのwrite latency、dirty data量、電源断試験で現行値より改善する場合にだけ変更する。 |
| `barrier` / `nobarrier` | device cache flushを制御 | barrier on | 可 | 同 | 現行のまま | barrierを無効にすると電源断時にfilesystemを破損する可能性がある。 |
| `clear_cache` | free-space cacheを再構築 | 無効 | 可 | 同 | 除外 | recovery/maintenance専用で通常mountに使わない。 |
| `enospc_debug` / `noenospc_debug` | ENOSPC debug出力 | 無効 | 可 | 同 | 除外 | diagnostic用。 |
| `fatal_errors=` | fatal error時の動作 | `bug` | 可 | 同 | 既定のまま | `panic`はOS全体を停止させ、`remount-ro`はdata writeを止めるため、回復性と障害通知要件を決めずに動作を変えない。 |
| `fragment=` | debug用fragmentation injection | 無効（CONFIG_BTRFS_DEBUG依存） | 条件付き | 同 | 除外 | debug-only option。 |
| `check_int` / `check_int_data` / `check_int_print_mask=` | internal consistency checkと出力mask | 無効 | `check_int_print_mask=`は固定版で未記載、7.3で確認 | 同 | 除外 | kernel integrity checkerのdebug/testing用で、通常の`/data` mountには不要。 |
| `rescue=` | rescue mount modesを選択 | 無効 | 可 | 同 | 除外 | rescue用。`ignoredata/ignoremeta` checksum modeは破損検出を無効にする。 |
| `nologreplay` / `norecovery` | log replayを止める・read-onlyでmount | 無効 | 可 | 同 | 除外 | 通常bootではlog recoveryを維持する。 |
| `rescan_uuid_tree` | UUID treeを再走査して再構築 | 無効 | 可 | 同 | 除外 | one-time repair actionで通常mount policyではない。 |
| `skip_balance` | ongoing balanceを再開せずmount | 無効 | 可 | 同 | 除外 | interrupted maintenance専用。 |
| `ssd` / `ssd_spread` / `nossd` / `nossd_spread` | SSD allocation policy | rotational statusで自動判定 | 可 | 同 | 実験で比べる | 同じSD cardとfill levelでsequential/random throughput、GC pause、free-space fragmentationを比較し、heuristicによる差が再現した場合だけ明示する。 |
| `treelog` / `notreelog` | fsync用tree logを選ぶ | enabled | 可 | 同 | 既定のまま | fsync recoveryを維持する。 |
| `usebackuproot` / `recovery` | backup rootからmountを試行 | 無効 | 可 | 同 | 除外 | recovery専用。`recovery`はdeprecated alias。 |
| `inode_cache` / `noinode_cache` | inode-map cache policy | 無効 | 固定kernelでは不可（5.11で削除） | 同 | 除外 | stale optionは以前の使用によるinode cache dataをclearする場合だけ参照。 |
| `thread_pool=` | async worker数 | `min(NRCPUS + 2, 8)` | 可 | 同 | 既定のまま | CardputerZeroでparallel read/write時のCPU使用率、queue latency、RAM使用量を既定と比較し、改善が出た場合だけ変える。 |
| `subvol=` / `subvolid=` | mountするsubvolumeを選ぶ | default subvolume | 可 | 同 | 除外 | 製品data layoutにsubvolumeを使う設計がない。 |
| `user_subvol_rm_allowed` | userによるsubvolume削除 | 無効 | 可 | 同 | 除外 | subvolume運用を設計していない。 |

mount option名の比較で、v7.3文書に`check_int_print_mask=`が追加記載されていることを確認しました。v6.10文書に載る他のmount名はこの比較で同じでした。generic mount option `context`もv7.3文書に記載されていますが、SELinux label policyに関するoptionとして設定候補から除外します。説明や既定値の意味変更は、変更が判明した場合に下表へ追記します。

## data checksum、scrub、修復

Btrfsはdataとmetadataを既定でchecksumします。metadata checksumはB-tree node内、data checksumはchecksum treeに保存されます。`nodatasum`を指定するとdata checksumを無効にします。`nodatacow`はdata CoWとdata checksumを無効にするため、data破損検出を重視する場合は候補から外します。read時のchecksum mismatchはEIOとして利用者へ示し、scrubはtimerでなくuser-initiatedかつprogress表示ありで実行します。

read時のchecksum不一致はI/O errorになります。`btrfs scrub`はdevice上のdata/metadataを読み、checksumを検証します。scrubが修復できるのは別の有効なcopyが読める場合に限られます。DUP、RAID1等の複製がないsingle profileでは、checksumは破損を検出できても元dataを再構成できません。RAID5/6の修復特性をsingle-device候補へ外挿しません。

### single-device DUPとQEMU

upstreamの「DUP PROFILES ON A SINGLE DEVICE」は、logical blockを2か所へ書いても、SSDがblockを内部で再配置・統合し、FTLのwear levelingが同一physical storage unitへ寄せる可能性があると説明します。このためphysical copyが独立する保証はなく、DUPをbackupや確実な冗長性として扱えません。故障してDUP copyから回復したdeviceは交換対象とされています。

QEMUで確認できるのは仮想block device上のBtrfs profile、checksum error、仮想copyからのrepair動作です。SD controllerのFTL、deduplication、wear leveling、電源断、physical cellの独立性は模擬しません。QEMU試験も実機測定も未実施です。

## 最新版との差分とoption件数

btrfs-progs v7.3の`mkfs.btrfs`では`--compress`、`--subvol`、`--inode-flags`、`--reflink`がv6.10文書にない追加optionです。`btrfstune`では`--enable-simple-quota`、`--remove-simple-quota`、`--version`が追加されました。いずれも上表で固定版利用不可または範囲外とし、設定候補は`版上げで使える候補`としました。v7.3のmkfs manualは`-V/--version`の出力にbuiltin featuresを加えています。v7.3 mount文書は`check_int_print_mask=`を追加記載します。defaultが変わったoptionはこの3資料の差分で確認できませんでした。kernel mainline 7.4-rc1文書でも同じoption名を照合し、説明・既定値の変更を検出した場合は該当rowに記します。

表の行数は設定候補と上流追加optionを数え、診断用`--version`は範囲外として明記しています。option列は互換表記を同じ行にまとめます。source tokenとoption列の機械照合結果はhandoff coverage scriptの出力を参照します。
