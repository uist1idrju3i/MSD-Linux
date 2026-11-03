# F2FSのformat、mount、実行時設定

[保存領域へ戻る](README.md) / [option調査の索引](filesystem-options.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版と最新版のf2fs-toolsは1.16.0です。kernelは固定版6.18.59とmainline 7.4-rc1を比較します。主な一次資料は[f2fs-tools v1.16.0](https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git/tree/?h=v1.16.0)、[固定kernelのF2FS documentation](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/filesystems/f2fs.rst)、[mainline v7.4-rc1](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/filesystems/f2fs.rst)です。現行defconfigでF2FS kernel/packageが選択済みかは未確認です。候補設定のbuild、QEMU、実機試験はしていません。

## 未操作時の書込みと進捗

GC、discard、checkpoint、lazy initはidle中もwriteし得る。timer/background writerを有効化せず、block traceでwrite時刻・byte数、foreground latency、recoveryを測る。長時間のformat/fsck/resize/maintenanceはuser起動・progress表示を必須にする。

## mkfsとfeature

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-a` | heap-based allocationを選ぶ | 有効 | 可 | 同 | 既定のまま | `/data`の連続書込みとrandom更新を測り、heap allocationの容量・GC負荷が既定より悪い場合だけ切り替える。 |
| `-c` | deviceを追加 | なし | 可 | 同 | 除外 | multi-device用。 |
| `-d` | debug level | 無効 | 可 | 同 | 除外 | debug専用。 |
| `-e` | cold fileとして扱うextension list | multimedia等 | 可 | 同 | 既定のまま | `/data`のextension別write frequencyを記録し、長期間更新されないfile種別が確認された場合にだけcold listへ追加する。 |
| `-E` | hot fileとして扱うextension list | database等 | 可 | 同 | 既定のまま | `/data`のextension別write frequencyとGC移動量を測り、頻繁に更新されるfile種別に分離効果が出る場合にだけ追加する。 |
| `-f` | force format | 無効 | 可 | 同 | 除外 | 誤消去を防ぐため、製品初期化手順に導入しない。 |
| `-g` | preset option groupを選ぶ | なし | 可 | 同 | 除外 | Android向けpresetは製品構成と異なる。 |
| `-i` | extended node bitmapを有効にする | 無効 | 可 | 同 | 既定のまま | file/inode数の上限、bitmapの追加容量、fsck時間を測り、標準bitmapで必要数を扱えない場合にだけ有効化する。 |
| `-l` | volume label | なし | 可 | 最新版で廃止 | 既定のまま | 現行`/data`のlabelは`data`で固定されるため、F2FS候補でも同じlabelを使う。 |
| `-m` | zoned featureを有効にする | 無効 | 可 | 同 | 除外 | 製品mediaはzoned deviceではない。 |
| `-o` | overprovisioning割合 | partition依存で自動 | 可 | 同 | 実験で比べる | 空き領域率ごとのhost write amplification、GC latency、実効容量を同じSD cardで測り、寿命または遅延の改善がある場合に変更する。 |
| `-O` | feature list | tool既定 | 可 | 同 | 実験で比べる | 各featureについてkernel、mkfs、fsck、resizeの対応を確認し、format/mount/fsck/upgrade試験が通ったfeatureだけ追加する。 |
| `-C` | casefold encodingとflags | なし | 可 | 同 | 除外 | filename semanticsを変える。 |
| `-q` | formatterのmessage表示を止める | 無効 | 可 | 同 | 既定のまま | filesystem policyではなく出力制御。 |
| `-r` | checkpoint seedを0にする | random | 可 | 同 | 既定のまま | 同一sourceの生成imageを比較し、再現可能なfilesystem imageが必要になった場合に使う。 |
| `-R` | initial root uid/gid | process uid/gid | 可 | 最新版で廃止 | 既定のまま | ownershipを別値にする要件がない。 |
| `-s` | sectors per section | 1 | 可 | 同 | 既定のまま | device geometryに合わせて変える必要がある場合に、logical/physical sector sizeとformat/mount互換性を確認する。 |
| `-S` | sparse mode | 無効 | 可 | 同 | 除外 | production block deviceの初期化用ではない。 |
| `-t` | discard policy | 有効 | 可 | 同 | 実験で比べる | SD controllerへの効果を実カードで測る。 |
| `-T` | inode timestamp | 現在時刻 | 可 | 同 | 実験で比べる | reproducible buildでfilesystem内のtimestamp固定が必要か確認し、mtime/ctimeを保持する利用要件と比較する。 |
| `-w` | sector size | device依存 | 可 | 同 | 既定のまま | CardputerZeroのblock logical/physical sector sizeとkernel対応を確認し、異なる値でmount/fsckできる試験が通った場合だけ変える。 |
| `-z` | sections per zone | 1 | 可 | 同 | 除外 | zoned device用geometry設定。 |
| `encrypt` | fscryptを有効化 | 無効 | 可 | 同 | 除外 | key lifecycleとrecoveryが未設計。 |
| `extra_attr` | extended inode attributes | 無効 | 可 | 同 | 既定のまま | dependent featureの前提。 |
| `project_quota` | project ID tracking | 無効 | 可 | 同 | 除外 | quota policy/toolが未導入。 |
| `inode_checksum` | inode checksum | 無効 | 可 | 同 | 実験で比べる | inode corruption検出の範囲、追加write/format容量、fsck挙動を有効・無効で比較する。 |
| `flexible_inline_xattr` | flexible inline xattr | 無効 | 可 | 同 | 既定のまま | `/data`のxattrサイズ分布を取り、通常inline領域を超えるmetadataが容量またはI/Oを増やす場合だけ評価する。 |
| `quota` | quota support | 無効 | 可 | 同 | 除外 | quota policy/toolが未導入。 |
| `inode_crtime` | creation timeを記録 | 有効 | 可 | 同 | 既定のまま | tool既定のtimestamp featureを維持。 |
| `lost_found` | lost+foundを作る | 有効 | 可 | 同 | 既定のまま | fsck recovery用directory。 |
| `verity` | fs-verityを有効化 | 無効 | 可 | 同 | 除外 | verity image作成・署名手順がない。 |
| `sb_checksum` | superblock checksum | 無効 | 可 | 同 | 実験で比べる | superblock corruption検出、既存imageとのmount互換性、追加write量を比較し、検出範囲が要件に合う場合に有効化する。 |
| `casefold` | case-insensitive lookup | 無効 | 可 | 同 | 除外 | filename semanticsを変える。 |
| `compression` | filesystem compression | 無効 | 可 | 同 | 実験で比べる | CPU、write amplification、容量を実測する。 |
| `android` | Android向けformat preset | 無効 | 可 | 同 | 除外 | Androidのmount/feature policyを持ち込まず、同じSDでformat後のcapacity・GC・fsck結果が現行候補より良い証拠がある場合だけ別途評価する。 |
| `encoding` / `utf8` / `strict` | filename encoding・UTF-8・厳密なencoding検査を指定 | 無効 | 可 | 同 | 除外 | filename semanticsと正規化を変え、既存fileを開けなくするriskがある。encoding要件が生じた場合だけ検討する。 |
| `sectors` | section当たりsector数 | device依存 | 可 | 同 | 既定のまま | logical sector、write amplification、fsck/mount互換性を実SDで測り、geometry変更に利点がある場合だけ変える。 |

`mkfs.f2fs`の残りの`-V`、help、version、progressやdevice geometry指定は表示・診断・formatter操作用です。format結果の比較対象にしないものは、採否候補にしません。image生成方式の検証は未実施です。

## mount optionとchecksum範囲

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `background_gc=` | background GC policy | `on` | 可 | 同 | 実験で比べる | idle中のblock移動/write量とforeground latencyを測り、idle write禁止とfree-space回復を比較する。 |
| `disable_roll_forward` | roll-forward recoveryを止める | 無効 | 可 | 同 | 除外 | crash recovery機能を無効にする。 |
| `discard` / `nodiscard` | mount時のdiscard/TRIMを有効化・無効化 | 未確認 | 可 | 同 | 実験で比べる | 未操作時のcommand時刻・所要時間・後続write latencyを実SDで測る。周期実行せず、必要ならuser-initiated maintenanceでprogressを表示する。 |
| `heap` / `no_heap` | heap allocationを選ぶ | 有効 | 可 | 同 | 既定のまま | 既定のallocation policyを使う。 |
| `user_xattr` / `nouser_xattr` | user xattr | 有効 | 可 | 同 | 既定のまま | xattr要件を変更する指示がない。 |
| `acl` / `noacl` | POSIX ACL | kernel/config依存 | 可 | 同 | 既定のまま | access policyを変更しない。 |
| `inline_xattr` / `noinline_xattr` | inline xattr | 有効 | 可 | 同 | 既定のまま | `/data`のxattrサイズとinode spaceを比較し、inline化によるinode圧迫またはI/O削減が確認された場合に変更する。 |
| `inline_data` / `noinline_data` | 小file dataをinode内へ格納 | 有効 | 可 | 同 | 実験で比べる | 小fileの速度・spaceを測る。 |
| `inline_dentry` / `noinline_dentry` | 小directory entryをinline化 | 有効 | 可 | 同 | 実験で比べる | 実dataのentry数/name長とlookup/create latencyを測り、容量か時間が改善する場合に選ぶ。 |
| `flush_merge` | flush requestを統合 | 有効 | 可 | 同 | 既定のまま | flush回数、flush latency、power-loss後の整合性を比較し、mergeによる改善が確認できた場合だけ変更する。 |
| `barrier` | cache flushを許す | 有効 | 可 | 同 | 既定のまま | write orderingを維持する。 |
| `nobarrier` | cache flushを出さない | 無効 | 可 | 同 | 除外 | deviceがvolatile cacheに書かない保証を確認していない。 |
| `fastboot` | unmount時flushを抑える | 無効 | 可 | 同 | 除外 | 安全なunmount時のflushを弱める。 |
| `extent_cache` / `noextent_cache` | extent cache | 有効 | 可 | 同 | 既定のまま | RAM使用量とextent lookup latencyを測り、cacheを外す利点がある場合だけ無効化する。 |
| `data_flush` | unmount時にdata blockをflush | 無効 | 可 | 同 | 実験で比べる | unmount latencyと永続性を比較する。 |
| `mode=` | adaptive/log-structured allocation | `adaptive` | 可 | 同 | 既定のまま | random/sequential latencyとGC/write amplificationを比較し、adaptiveより改善する場合だけ変える。 |
| `fsync_mode=` | fsync semantics | `posix` | 可 | 同 | 既定のまま | updaterとdata writerのfsync/recovery試験を各modeで行い、POSIX durability要件を満たした場合だけ変更する。 |
| `checkpoint_merge` | concurrent checkpointをmerge | 無効 | 可 | 同 | 実験で比べる | checkpoint頻度とlatencyを測る。 |
| `nocheckpoint_merge` | checkpoint mergeを無効にする | 有効 | 可 | 同 | 既定のまま | checkpoint頻度、flush latency、CPU時間を測り、mergeを無効にしたときの改善がなければ既定を保つ。 |
| `atgc` | age-threshold GC | 無効 | 可 | 同 | 実験で比べる | workloadと長期fragmentation試験が必要。 |
| `gc_merge` | background GCでforeground GC requestを処理 | 無効 | 可 | 同 | 実験で比べる | foreground latencyを測る。 |
| `nogc_merge` | GC mergeを無効にする | 無効 | 可 | 同 | 既定のまま | foreground/background GC latencyとwrite amplificationを比較し、mergeによる悪化が確認された場合だけ変更する。 |
| `norecovery` | roll-forward recoveryを無効化してread-only mount | 無効 | 可 | 同 | 除外 | 通常bootでrecoveryを止めない。 |
| `active_logs=` | active log数を指定 | 6 | 可 | 同 | 実験で比べる | hot/cold separationとmetadata容量を測る。 |
| `disable_ext_identify` | mkfs extension listを使わない | 無効 | 可 | 同 | 実験で比べる | extensionごとの配置効果を測る。 |
| `inline_xattr_size=` | inline xattr領域サイズ | inode feature依存 | 可 | 同 | 実験で比べる | inode spaceとxattr workloadを比較する。 |
| `reserve_root=` / `reserve_node=` | privileged user用block/node予約 | 各々12.5%上限 | 可 | 同 | 実験で比べる | 通常利用可能量と復旧用領域を比較する。 |
| `resuid=` / `resgid=` | 予約領域を使えるUID/GID | 0 | 可 | 同 | 既定のまま | 権限policyを別途定めていない。 |
| `usrquota` / `grpquota` / `prjquota` / `quota` / `noquota` | quotaを有効化・無効化 | feature/config依存 | 可 | 同 | 除外 | quota policyと管理toolがない。 |
| `usrjquota` / `grpjquota` / `prjjquota` | user/group/project journaled quota | feature/config依存 | 可 | 同 | 除外 | metadata/accounting writeを追加する。quota policyと管理toolがないため有効化しない。 |
| `checkpoint` | checkpoint intervalまたはdisable modeを選ぶ | kernel既定 | 可 | 同 | 実験で比べる | 無操作時のmetadata write時刻・byte数と電断recoveryを測る。periodic checkpointがidle write禁止に反しないことを確認する。 |
| `alloc_mode=` | block allocation mode | `adaptive` | 可 | 同 | 実験で比べる | LFS/adaptiveのrandom write latency、GC時間、write amplificationを実機比較し、random更新が改善する場合に選ぶ。 |
| `test_dummy_encryption=` | dummy fscrypt mode | 無効 | 可 | 同 | 除外 | testing optionであり製品暗号化ではない。 |
| `compress_algorithm=` | compression algorithm | `lzo`等 | 可 | 同 | 実験で比べる | CPUと容量を実測する。 |
| `compress_log_size=` | compressed cluster log size | tool/kernel既定 | 可 | 同 | 実験で比べる | allocation granularityとwrite costを測る。 |
| `compress_chksum` | compressed clusterのraw data checksum検証 | 無効 | 可 | 同 | 実験で比べる | 固定kernel文書どおり圧縮clusterのraw dataを検証する。全file data/metadataは対象外で、ext4・dm-integrityと範囲を分けて比較する。 |
| `compress_mode=` | filesystem/user compression mode | `fs` | 可 | 同 | 実験で比べる | automatic compressionの影響を測る。 |
| `compress_extension=` / `nocompress_extension=` | extensionごとに圧縮対象を指定 | なし | 可 | 同 | 実験で比べる | extension別保存量、CPU時間、I/O latencyを比べる。 |
| `compress_cache` | compressed block cache | 無効 | 可 | 同 | 既定のまま | RAM増加量、cache hit率、再読込latencyを測り、memory budget内でread latencyが下がる場合だけ有効化する。 |
| `inlinecrypt` | inline crypto pathを利用 | 無効 | 可 | 同 | 除外 | device/key supportとhardware integrationが未確認。 |
| `discard_unit=` | discard粒度を指定 | `block` | 可 | 同 | 実験で比べる | SD firmwareへの負荷を測る。 |
| `memory=` | memory usage modeを選択 | kernel既定 | 可 | 同 | 実験で比べる | RAM制約とGCの性能を比較する。 |
| `age_extent_cache` | age-based extent cache | 無効 | 可 | 同 | 実験で比べる | atgcと併用するGC behaviorを測る。 |
| `errors=` | filesystem error時の動作 | `continue` | 可 | 同 | 実験で比べる | recovery / remount policyを比較する。 |
| `nat_bits` | NAT bits featureを使う | 無効 | 可 | 同 | 既定のまま | checkpoint容量、mount/recovery時間、異常停止後のroll-forward結果を有効・無効で比較し、起動または復旧が改善する場合に使う。 |
| `lookup_mode=` | directory lookup policy | `default` | 可 | 同 | 既定のまま | 実際の`/data` directory構造でlookup throughput、CPU時間、memory使用量を比較し、defaultより改善する場合に変える。 |
| `fault_injection=` / `fault_type=` | debug用filesystem fault injectionを設定 | 無効 | 可 | 同 | 除外 | fault-injection test専用。 |
| `resizable_tail_secno=%u` | resizable tail sectionを指定 | 設定時のみ | 固定kernelでは未対応。mainline 7.4-rc1 docsにあり | 最新版で追加; 版上げで使える候補 | 実験で比べる | 固定版利用可能とは扱わない。 |

固定kernelの説明では`compress_chksum`は「compressed cluster内のraw dataのchecksumを検証する」としています。inode checksumおよびsuperblock checksumとは別の範囲です。checksum不一致時の具体的なerror、repair動作、対象となる全compression formatは未確認です。

## sysfs、fsck、resize、f2fs_io

sysfs pathは個別のruntime knobであり、format後に変更するとmount中のGC、discard、checkpoint、writebackなどに作用します。全attributeと用途、未操作時writeへの関係は[sysfs option一覧](filesystem-options-f2fs-sysfs.md)にまとめました。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `gc_urgent`、`gc_idle` | runtime GC mode | idle/default | 可 | 同 | 既定のまま | sysfs値はbootごとに再設定が必要。現行起動policyに加えない。 |
| `gc_min_sleep_time`、`gc_max_sleep_time`、`gc_urgent_sleep_time` | GC sleep interval | kernel既定 | 可 | 同 | 実験で比べる | background writeとlatencyを測る。 |
| `ipu_policy`、`ipu_util` | in-place update policy | kernel既定 | 可 | 同 | 既定のまま | 固定値の性能根拠がない。 |
| `max_victim_search`、`migration_granularity` | GC victim/移動量を調整 | kernel既定 | 可 | 同 | 既定のまま | GC時間、移動量、foreground latencyを長期write負荷で測り、defaultより改善する場合だけ変える。 |
| `trim_sections`、`discard_granularity` | trim範囲と単位 | kernel/device依存 | 可 | 同 | 既定のまま | 実カードでtrim所要時間、discard後のwrite latency、discard errorを記録し、deviceに利点がある場合だけ変える。 |
| `fsck.f2fs -a` / `-f` | 自動修復 / 強制検査 | 対話 / clean時省略 | 可 | 同 | 実験で比べる | 起動時repair policyを比較する。 |
| `fsck.f2fs -M` / `-p` | multi-device fsck、問題の自動修復 | 無効 | 可 | 同 | 除外 | F2FS multi-device構成ではなく、通常起動は既存の安全なfsck経路を使う。修復の無条件承認やdevice集合変更を追加しない。 |
| `resize.f2fs` | filesystemを拡張・縮小 | 明示実行 | 可 | 同 | 既定のまま | 更新・data領域layoutに適用する計画がない。 |
| `f2fs_io` | test/debug用I/O・compression操作 | 該当なし | 可 | 同 | 除外 | production filesystem設定ではなく実験tool。 |

sysfs項目はmount後に変更するruntime knobであり、filesystem imageに永続化される設定ではありません。`f2fs_io`の測定値やcommand結果は本調査では取得していません。

## 最新版差分とoption件数

f2fs-tools 1.16.0は固定版と最新版で同一です。Linux mainline v7.4-rc1のF2FS mount documentationには固定版6.18.59にない`resizable_tail_secno=%u`が1項目あり、他にこの比較で削除されたmount option名はありません。最新版のみの行は上表に明記しました。kernel documentationの説明文や全sysfs項目の意味変更は未確認です。

表の行数はoptionの総数や一次資料とのcoverageを示しません。mount optionのaliasや互換表記は一行にまとめています。未記載の項目がある場合は、その採否を評価済みとは扱いません。
