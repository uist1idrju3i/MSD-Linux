# ext4 formatter・保守toolのoption

[保存領域へ戻る](README.md) / [filesystem option調査](filesystem-options.md) / [ext4 mountとfeature](filesystem-options-ext4.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版・最新版ともe2fsprogs 1.47.4です。一次資料は[e2fsprogs v1.47.4](https://github.com/tytso/e2fsprogs/tree/v1.47.4)の`mke2fs(8)`、`mke2fs.conf(5)`、`tune2fs(8)`、`e2fsck(8)`です。製品のdata partition labelは`data`で、容量は[`msd-data-grow`](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow)がpartitionとfilesystemを拡張して決めます。

CLIの保守optionは起動時のmount値とは分けました。通常bootで実行するoption、offline repairのoption、filesystem作成時だけ適用するprofileを区別します。診断名も省略せず、必要な運用・追加書込み・復旧上の影響を表に記します。

## `mke2fs`と`mke2fs.conf`

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-C` / `-G` / `-g` | cluster size、flex group数、block group内block数 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `bigalloc`やgroup geometryを変える。4096-byte blockの現行formatを維持し、inode table容量・小file空間浪費・fsck時間を測って差が出た場合に限る。 |
| `-N` | inode数を直接指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `msd-data-grow`後の最大file数、inode消費率、inode table容量を数え、ratio計算でinode枯渇または過大なmetadataが見込まれる場合だけ固定する。 |
| `-M` | last-mounted directoryを記録 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | diagnostic metadataでありmount先や`data` labelは変更しない。稼働中の識別にはpartition labelを使う。 |
| `-T` / `-t` | usage profileとfilesystem typeを選択 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | profileがblock/inode/featureのdefaultを変える。`mkfs.ext4`の現行typeを保ち、生成imageのfeature、fsck時間、実容量をprofileごとに比較した場合だけ変える。 |
| `-U` / `clear` / `random` / `time` | UUIDを指定・消去・生成 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | clone imageで固定UUIDを共有するとdevice識別が衝突する。UUIDはformatごとに生成し、起動時の識別は既定のpartition label `data`を使う。 |
| `-d` | directoryやtarballから初期fileをcopy | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | data imageを空で作る製品の初期化経路ではない。初期内容を入れるとformat時にSDへ書く量が増え、初回起動と利用者操作を区別しにくくなる。 |
| `-e` | filesystem error時のbehaviorを指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | error後の継続・remount policyを変えるため、発生頻度、kernel log、read-only化後の復旧を測ってから選ぶ。 |
| `-j` | internal journalを作成 | 未確認（資料でdefault未整理） | 可 | 同 | 現行のまま | 現行ext4のmetadata recoveryにjournalを使う。journalを外すと電断後のcheck・recovery負荷が変わるため、通常設定では維持する。 |
| `-l` | bad-block listをformat時に登録 | 未確認（資料でdefault未整理） | 可 | 最新版で廃止 | 除外 | 不良block検査の結果ファイルとblock sizeが必要。SD全域を通常formatでscanせず、媒体異常はdevice交換・offline診断で扱う。 |
| `-S` | superblockとgroup descriptorだけを再初期化 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 最終手段の復旧用で、誤ったformat parameterでは残存dataをさらに破損させる。通常の初期化・起動に使わない。 |
| `-z` / `force_undo` / `undo_dir` | 変更前blockをundo fileへ保存 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | sidecar保存先と復旧手順がなく、SDへの追加read/writeも増える。消去前にimage copyを作る保守作業と分ける。 |
| `assume_storage_prezeroed` | storageをzero済みと仮定してformat | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | SD全領域が実際にzero済みとの証拠がない。未初期化blockを既存dataと誤認しないよう、ゼロ化を省略しない。 |
| `encoding` / `encoding_flags` | casefold用filename encodingを指定 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | case-sensitiveな既存filename semanticsを変えるため、名前比較要件がなく文字列互換を失う変更をしない。 |
| `fast_commit_size` / `orphan_file_size` / `mmp_update_interval` | journal fast-commit領域、orphan file容量、MMP更新間隔を指定 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | `fast_commit_size`はjournal領域を使い、`orphan_file_size`はmetadata容量・recovery対象数を変える。MMPはmount中の周期writeを生むため、各々fsync latency、crash recovery時間、MMP有効時のblock write traceを測ってから設定する。 |
| `location` / `offset` / `num_backup_sb` / `packed_meta_blocks` | journal位置、metadata offset、backup superblock数、metadata packingを制御 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | block layout変更は`msd-data-grow`後の拡張・fsck互換性に影響する。現行block sizeでformat/mount/拡張/復旧試験を通し、metadata容量の差が確認された場合だけ指定する。 |
| `no_copy_xattrs` / `root_owner` / `root_perms` / `root_selinux` | rootdirからのxattr、root ownership、permission、SELinux labelを制御 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `/data`はrootdir imageを展開せず、初回起動時に必要なownershipを通常の初期化で設定する。imageに初期treeを入れる設計へ変えた場合にのみ差を確認する。 |
| `hash_seed` / `hash_alg` | directory hash seed・algorithmを指定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | directory lookup特性を変える。複数seedで大directoryのlookup latency、CPU時間、再現性を比較し、実際に差が出た場合だけ固定する。 |
| `base_features` / `default_features` / `features` | global・filesystem別feature defaultを構成 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 設定ファイルのprofileが明示format optionを越えてfeatureを変えないか生成imageの`dumpe2fs`で比較する。現行kernel/e2fsprogs双方に対応する組合せだけを維持する。 |
| `default_mntopts` / `mount_opts` | filesystemにdefault mount optionを保存 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 起動scriptとfstabが`noatime,nodev,nosuid,data=ordered,errors=remount-ro`を明示する。image内defaultとの競合を避け、生成superblockと実mount値を比較する。 |
| `blocksize` / `cluster_size` / `flex_bg_size` / `inode_ratio` / `inode_size` / `reserved_ratio` | profileのblock・cluster・group・inode・reserved-space geometry | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | block sizeは現在4096 byte。capacityはgrow後のpartitionで決まり、file数・small-file分布・free spaceの測定がgeometry変更を正当化した場合だけ再formatする。 |
| `auto_64-bit_support` / `creator_os` / `fs_type` / `usage_types` / `enable_periodic_fsck` / `warn_y2038_dates` | auto feature、creator、用途・periodic check・date warning policy | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | profile変更で生成featureやfsck周期が変わらないよう、format時のconfigとsuperblockを照合する。日付・fsckの実要件が変わる場合に別途評価する。 |
| `journal_location` / `set_raid_stride` / `set_raid_stripe` / `num_backup_sb` / `packed_meta_blocks` | journal・stripe geometry・backup metadataを構成 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 単一SD上に外部journal/RAID stripeはない。FTLが隠すNAND geometryを推定せず、layout変更後にgrow、mount、fsckができる証拠がある場合に限る。 |
| `hugefiles_align` / `hugefiles_align_disk` / `hugefiles_digits` / `hugefiles_dir` / `hugefiles_gid` / `hugefiles_name` / `hugefiles_size` / `hugefiles_slack` / `hugefiles_uid` / `hugefiles_umask` / `make_hugefiles` / `num_hugefiles` / `zero_hugefiles` | test用の巨大file群を作成・整列・所有権設定 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | option groupの目的は巨大fileで容量・割当を試験すること。製品`/data`はgrow後に利用者が作るfileで埋まり、format時の事前allocationは初回の意図しない書込みと使用可能量減少を招く。 |
| `clear_mmp` / `force_fsck` | MMP stateのclear、次回fsckの強制 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | `clear_mmp`はmounted filesystemの保護stateを消し、`force_fsck`は次回bootの全checkを要求する。single-mount運用の通常起動で適用せず、明示したoffline recoveryでのみ使う。 |
| `continue` / `panic` / `remount-ro` / `resize` / `revision` / `test_fs` / `^test_fs` / `time` / `read-only` | config内のerror action、resize flag、revision、test image、featureを外す指定、UUID/time値 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 値はformat/layoutやerror時の動作を変える。`remount-ro`以外のerror actionは通常のdata運用で採らず、resize/revisionはgrow・offline repair時にのみ試験する。 |
| `proceed_delay` / `sync_kludge` / `usage_types` / `undo_dir` / `force_undo` | formatterの待機、sync互換、用途profile、undo設定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | format時のwrite orderingや実行時間を変える。媒体固有のsync問題を再現し、初期化時write traceと復旧を確認した場合だけ設定する。 |

## `tune2fs`と`e2fsck`

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `tune2fs -C` / `-T` | mount count・last-check時刻を設定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | startup fsck policyに関わる。起動回数・異常停止数・full scan時間を測り、periodic checkの実運用が必要な場合にだけ閾値を設定する。 |
| `tune2fs -M` / `-U` | last-mounted path・filesystem UUIDを変更 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `-M`はdiagnostic metadataで実mount先を変えず、`-U`固定は複製時の識別衝突を起こし得る。`data` labelを維持しUUIDを不用意に複製しない。 |
| `tune2fs -e` / `-g` / `-r` / `-u` | error behavior、reserved-block group/count/userを設定 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | `-r`は通常利用できる容量、`-g/-u`は予約領域を使える主体、`-e`は障害後の動作を変える。実容量、root/service UID/GID、error recoveryを確認してから値を変える。 |
| `tune2fs -j` / `-Q` | journal追加、quota feature設定 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 現行imageはjournal付き。quota policy・起動toolがなく、追加metadataとaccounting writeを導入する理由がない。 |
| `tune2fs -l` | superblock contentsを表示 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 読み取り診断で、filesystem formatやmount policyを変えない。 |
| `tune2fs -z` | superblock変更前のundo fileを作成 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | undo fileを別媒体へ安全に保存する運用がなく、SDの追加writeも増える。必要なoffline変更では先にdata imageのbackupを作る。 |
| `e2fsck -B` / `-r` | block sizeを指定、互換修復modeを選択 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 通常の起動時fsckではなく、既知のblock geometryを用いたoffline recovery向け。誤った値でsuperblock検出・repairを進めない。 |
| `e2fsck -C` / `-d` / `-t` | progress fd、debug output、timing statistics | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 進捗・診断の表示を制御し、filesystem policyを変えない。`/data`のwrite量評価は外部block traceで記録する。 |
| `e2fsck -a` / `-y` | promptを省略してrepairを承認 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | `-a`は`-p`と同等の互換option、`-y`は全修復を無条件承認する。現行の安全修復`e2fsck -p`を維持し、確認できない修復を自動承認しない。 |
| `e2fsck -k` / `-l` | bad-block listを保持・追加 | 未確認（資料でdefault未整理） | 可 | 最新版で廃止 | 除外 | block listと同じfilesystem block sizeが必要。SDのmedia error時はdataを別媒体へ退避し、通常bootでbad-block scanを繰り返さない。 |
| `e2fsck -z` | repair前blockをundo fileに保存 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | undo保存先とrollback手順がなく、破損したSDへ追加writeを行う。repair前のblock image backupが取れるoffline作業でのみ評価する。 |
| `bmap2extent` / `check_encoding` / `ea_ver` / `fixes_only` / `fragcheck` / `inode_count_fullmap` / `journal_only` / `no_inode_count_fullmap` / `no_optimize_extents` / `optimize_extents` / `readahead_kb` / `unshare_blocks` | e2fsck `-E`のextent変換、encoding/xattr check、repair範囲、fragment・memory・readahead調整 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | 全てoffline checkerの検査・修復動作を変える。対象errorを再現したimage copyで、repair結果、read/write block数、peak memory、再度の`e2fsck -fn`結果を記録するまで起動時のrepair policyへ加えない。 |

`e2fsck -E discard`/`nodiscard`はfree block discardの可否を選び、defaultはdiscardしない設定です。discardは通常file writeとは別のdevice commandであり、実カード上の所要時間、error、解放後write latencyを測らず起動時に有効化しません。固定版・最新版e2fsprogsは同じ1.47.4ですが、filesystemに保存された値、toolの既定値、kernel mount動作は別々に確認します。
