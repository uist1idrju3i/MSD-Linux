# ext4 mount optionと永続設定

[保存領域へ戻る](README.md) / [filesystem option調査](filesystem-options.md) / [ext4 format・feature](filesystem-options-ext4.md) / [formatter・保守tool](filesystem-options-ext4-tools.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定kernelは6.18.59 commit `b3495ea401d709af0701a85babcba5e3d788a602`、最新版はmainline v7.4-rc1です。一次資料は[固定版 ext4 admin guide](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/ext4.rst)と[mainline v7.4-rc1 ext4 admin guide](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/admin-guide/ext4.rst)です。実機kernelのsupport/defaultは未確認です。

## mountと永続設定

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `noatime` | access timeを更新しない | `relatime`相当 | 可 | 同 | 現行のまま | 書込み抑制の現行設定。 |
| `nodev` | device nodeを解釈しない | 解釈する | 可 | 同 | 現行のまま | `/data`上のdevice nodeを禁止する。 |
| `nosuid` | setuid/setgidを無効化 | 有効 | 可 | 同 | 現行のまま | `/data`上の特権昇格を防ぐ。 |
| `data=ordered` | dataをjournal metadataより先に書く | ordered | 可 | 同 | 現行のまま | fstabと初期化scriptの現行値。 |
| `ordered` / `writeback` | data journaling modeの短縮名・mode名 | `ordered` | 可 | 同 | 既定のまま | `writeback`では直前に書いたfile dataが電断後に古い内容へ戻る可能性がある。現行の`data=ordered`を保ち、mode変更は電断試験で整合性を確認できた場合だけ検討する。 |
| `errors=remount-ro` | error時read-only化 | `errors=continue`等のsuperblock値 | 可 | 同 | 現行のまま | error後の追加書込みを抑える。 |
| `relatime` | atimeを条件付き更新 | kernel既定 | 可 | 同 | 既定のまま | 現行では明示せず`noatime`を使う。 |
| `strictatime` | 毎回atime更新 | 無効 | 可 | 同 | 除外 | 書込み増加の必要性がない。 |
| `discard` | discardを即時送信 | 無効 | 可 | 同 | 実験で比べる | discard commandが未操作時間にも発行され得るため、時刻、所要時間、error、後続write latencyをtraceする。progressを表示する利用者起点のmaintenanceで実益を確認できない限り定期実行しない。 |
| `nodiscard` | discardを送らない | 既定 | 可 | 同 | 既定のまま | 未操作時のdevice commandを避ける。 |
| `commit=seconds` | journal commit間隔 | 5秒 | 可 | 同 | 実験で比べる | journal timerがuser operation後のdirty stateをcommitする時刻とhost writeを記録する。未操作時にcommit writeが出る条件を確認し、電断時のloss windowとno-idle-write要件の両方を満たす値を選ぶ。 |
| `journal_checksum` | journal transaction checksumを有効化 | kernel/superblock依存 | 可 | 同 | 既定のまま | journal破損の検出を保ち、data block checksumとは区別する。checksum有無で電断後のreplay結果とkernel/e2fsprogs互換性を試験する。 |
| `journal_async_commit` | commit blockをdescriptor待ちなしで出す | 無効 | 可 | 同 | 実験で比べる | journal I/Oの待ち時間を減らせる一方、古いkernelとの互換性を失いchecksumを有効化する。user operation時のcommit latencyと電断replayが改善する場合だけ選ぶ。 |
| `journal` / `journal_dev` / `journal_path` | journal inodeまたは外部journalの場所を選ぶ | 内部journal | 可 | 同 | 除外 | 外部journal用の別deviceはない。同じSD上へ移しても独立性・電源断耐性は増えず、追加の永続writeを避ける。 |
| `journal_data` / `journal_data_ordered` / `journal_data_writeback` | journal data modeのsuperblock defaultを選ぶ | filesystem設定依存 | 可 | 同 | 既定のまま | modeを変えるとwrite量と電断後のdata整合性が変わる。現行の`data=ordered`を維持する。 |
| `max_batch_time` | journal transaction batchingの最大待ち時間 | 15000 us | 可 | 同 | 実験で比べる | flush待ち、commit回数、未commit期間をtraceし、ユーザー操作への応答と電断時の損失幅を両立する場合に変更する。timerで新たなidle writeを起こさないことも確認する。 |
| `min_batch_time` | journal transaction batchingの最小待ち時間 | 0 us | 可 | 同 | 実験で比べる | batch待ちの有無ごとにcommit回数とp99 fsync latencyを測る。不要な遅延がなく、ユーザー操作外のwriteを生まない値だけ選ぶ。 |
| `init_itable` / `noinit_itable` | inode tableの遅延初期化を調整・停止 | 有効 | 可 | 同 | 実験で比べる | lazy initializationは初回mount後の未操作時間にもinode tableを書き得る。初回起動のblock write trace、mount時間、同期初期化時間を比較し、同期処理を行う場合はuser-initiated provisioningのprogressを表示する。 |
| `auto_da_alloc` | rename/truncate置換時にdelayed blockを確保 | 有効 | 可 | 同 | 既定のまま | `/data`のtemporary-file renameとtruncate更新後の電断試験を行い、commit前のdata整合性を確認する。削除すると中断時に旧dataへ戻るriskが増える。 |
| `block_validity` | allocatorがblock referenceの妥当性を検査 | 有効 | 可 | 同 | 既定のまま | 検査を維持し、異常block referenceの検出を保つ。metadata負荷と破損注入試験で費用を確認できた場合だけ変える。 |
| `dioread_lock` / `dioread_nolock` | direct-I/O readのinode lock方式 | lockあり | 可 | 同 | 実験で比べる | `data=ordered`でdirect-I/O throughput、lock待ち、unwritten extent conversion後の整合性を測り、実 workloadで改善する場合だけ変更する。 |
| `inlinecrypt` | filesystem encryptionをinline crypto pathへ渡す | 無効 | 可 | 同 | 除外 | SDにinline crypto engineがあることは未確認。`/data`暗号化は初回bootにdevice固有keyを生成するdm-crypt/LUKS2方針で評価する。 |
| `dax` | direct access mappingを使う | 無効 | 可 | 同 | 除外 | DAX-capable persistent-memory deviceではないSD block deviceで使う経路ではない。 |
| `max_dir_size_kb` | directoryの最大sizeを制限 | 既定で制限なし | 可 | 同 | 既定のまま | `/data`のdirectory entry数、lookup時間、低RAM時のmetadata memoryを測り、巨大directoryでpressureが起きる場合だけ上限を設定する。 |
| `minixdf` / `bsddf` | `statfs`でfree blockを数える方式 | `minixdf`相当 | 可 | 同 | 既定のまま | 空き容量の算出方法で、partition容量や`msd-data-grow`のsizeは変えない。 |
| `bsdgroups` / `grpid` / `nogrpid` | 新規fileのgroup inheritanceを選ぶ | kernel/superblock依存 | 可 | 同 | 既定のまま | `/data`のownershipとservice groupのpermission semanticsを変える。UID/GID設計に基づくcreate/rename試験が必要で、書込み削減の設定ではない。 |
| `nouid32` / `uid16` | 16-bit UID/GID互換動作を選ぶ | 無効 | 可 | 同 | 除外 | legacy filesystem/userland互換用で、現行LinuxのUID/GID範囲を狭める。 |
| `resuid` / `resgid` | reserved blockを利用できるUID/GIDを指定 | root / root group | 可 | 同 | 既定のまま | reserved block利用者を変えてもpartition容量は増えない。service userが満杯時も書ける要件ができた場合に権限とquotaを合わせて設定する。 |
| `quota` / `usrjquota` / `grpjquota` / `jqfmt` / `project` / `quotatype` | user/group/project journaled quotaを構成 | 無効 | 可 | 同 | 除外 | quota policyと起動時に管理するtoolがない。accounting metadata/writeを増やすため、容量制限導入時にだけ評価する。 |
| `stripe` | allocatorが一度に使うstripe幅 | 未指定 | 可 | 同 | 既定のまま | SD controllerのNAND stripe geometryは公開されない。geometryが判明し、実カードでwrite amplificationまたはlatencyが改善する場合だけ指定する。 |
| `oldalloc` | legacy block allocatorを使う | 無効 | 可 | 同 | 既定のまま | 現行allocatorへの利点が未測定。fragmentationとrandom/sequential write latencyを実SDで比較する。 |
| `i_version` | inode versionを更新・公開する | 無効 | 可 | 同 | 既定のまま | NFS等のconsumerがないため、inode updateのmetadata workを増やさない。exportまたはversion-based cache validationを導入する場合だけ有効化する。 |
| `mmp` | multiple-mount protectionを有効化 | 無効 | 可 | 同 | 除外 | MMPはmounted中にsuperblockを周期更新する。単一OSで一枚のSDをmountする構成に、user requestのない定期writeを加えない。 |
| `data_err` | data journaling時のI/O error処理 | report | 可 | 同 | 既定のまま | `data=journal`時のerror通知/abort動作を変える。ordered modeで効果を仮定せず、journaled-dataを試す際にerror injectionで再mount結果を比べる。 |
| `nombcache` | metadata block cacheを使わない | 無効 | 可 | 同 | 実験で比べる | cacheを外すとRAM使用は下がる一方metadata readが増える。cold/warm lookupのread量、RAM、latencyを測り、低RAM時に利点がある場合だけ使う。 |
| `abort` / `debug` | filesystemをabortする、debug出力を増やす | 無効 | 可 | 同 | 除外 | `abort`はfault testing、`debug`は診断用で通常mount policyを変えない。 |
| `check` | mount時のfilesystem check要求 | 無効 | 可 | 同 | 除外 | mountごとの全checkは起動時間とread量を増やす。長時間点検を行う場合はuser-initiatedとし、progressを表示する。 |
| `ro` | read-only mountを要求 | read-write | 可 | 同 | 実験で比べる | ext4はread-onlyでもjournal replayでwriteする場合がある。実write traceを確認し、未操作時のwrite禁止にはblock device側のread-only保証も設計する。 |
| `sb` | alternate superblockを選ぶ | primary | 可 | 同 | 除外 | recovery時に限る。通常起動で指定するとmetadata世代の不一致を隠すおそれがある。 |
| `norecovery` / `noload` | journal replayを止める | replay有効 | 可 | 同 | 除外 | dirty filesystemのmetadata inconsistencyを残す。write抑制のためにrecoveryを止めない。 |
| `remount-ro` | error時にread-onlyへ再mount | mount error policy依存 | 可 | 同 | 現行のまま | 現行`errors=remount-ro`と同じくerror後の追加writeを止める。 |
| `data=journal` | dataとmetadataをjournal | ordered | 可 | 同 | 実験で比べる | `data=journal`はdelayed allocationとO_DIRECTを無効にする（[kernel ext4 documentation](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/Documentation/admin-guide/ext4.rst?id=b3495ea401d709af0701a85babcba5e3d788a602)）。電断時のdata損失幅とjournal write量・回数を利用者操作中に測り、SD wearへの影響は推測として評価する。 |
| `data=writeback` | data順序保証を弱める | ordered | 可 | 同 | 除外 | 電断後の整合性を弱める。 |
| `barrier` / `nobarrier` | flush/FUAによる順序保証 | 有効 | 可 | 同 | 既定のまま | flush無効化にはdevice supportと電源断試験の証拠が必要。現状は順序保証を維持する。 |
| `delalloc` / `nodelalloc` | delayed allocationを使う/停止する | 有効 | 可 | 同 | 実験で比べる | power loss前に未確保のdirty dataを失う窓と、write timing・回数を比較する。`data=journal`では`nodelalloc`が強制される。 |
| `lazytime` | timestamp更新を遅延 | 無効 | 可 | 同 | 実験で比べる | timestamp write量と異常停止後の許容差を測る。timer flushがidle時間にwriteしないか確認し、user operation起点でないwriteを許容する場合だけ有効化する。 |
| `acl` / `noacl` | POSIX ACL | kernel/config依存 | 可 | 同 | 既定のまま | 製品のACL要件を変更する指示がない。 |
| `user_xattr` / `nouser_xattr` | user xattr | 有効 | 可 | 同 | 既定のまま | 現行imageとの互換性を保つ。 |
| `usrquota` / `grpquota` / `prjquota` | quota accounting | 無効 | 可 | 同 | 除外 | quota policy・管理toolが未導入。 |
| `journal_ioprio=` | journal threadのI/O優先度 | 3 | 可 | 同 | 既定のまま | foreground latencyとjournal flushをCardputerZeroで測り、priority変更が改善する場合だけ調整する。 |
| `inode_readahead_blks=` | inode tableの先読み | 32 | 可 | 同 | 既定のまま | cold-cache lookup latencyとmemory使用量を比較し、32 blockから変える効果がある場合だけ調整する。 |

### 最新版との差分

抽出したext4 option tokenは固定kernel 6.18.59とmainline 7.4-rc1で同一です。既定値変更は一次資料の全文比較で未確認です。長時間fsck、discard、recoveryはuser-initiatedの操作としてprogressを表示し、timer起動しません。
