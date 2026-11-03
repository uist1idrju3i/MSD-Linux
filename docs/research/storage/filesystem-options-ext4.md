# ext4のformat、mount、維持設定

[保存領域へ戻る](README.md) / [option調査の索引](filesystem-options.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

e2fsprogsは固定版・最新版とも1.47.4です。kernelは固定版6.18.59とmainline 7.4-rc1を比較対象にします。一次資料は[e2fsprogs v1.47.4](https://github.com/tytso/e2fsprogs/tree/v1.47.4)の`misc/ext4.5.in`と[固定kernel `Documentation/admin-guide/ext4.rst`](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/ext4.rst)、[mainline v7.4-rc1 `Documentation/admin-guide/ext4.rst`](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/admin-guide/ext4.rst)です。kernel mount optionは[ext4 mount option](filesystem-options-ext4-mount.md)、CLI optionは[formatter・保守tool](filesystem-options-ext4-tools.md)に分けました。

表は`/data`の作成、feature、mount、永続設定に関係するoptionです。診断・復旧用のCLI optionも含め、抽出された項目は[別表](filesystem-options-ext4-tools.md)に用途と理由を記します。

## formatとfeature

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `-b` | block size | 4096 byte | 可 | 同 | 現行のまま | genimageと`mkfs.ext4`が4096を指定。 |
| `-F` | device確認を強制 | なし | 可 | 同 | 現行のまま | 初期化scriptが既定のdevice確認を越えてformatする。 |
| `-L` | label | 空 | 可 | 同 | 現行のまま | 現行labelは`data`。 |
| `-m` | reserved blockの割合 | 5% | 可 | 同 | 実験で比べる | 小容量data領域で利用可能量とroot予約の影響を測る。 |
| `-i` | inode当たりbyte数 | filesystem依存 | 可 | 同 | 既定のまま | `/data`で同時に保持する最大file数とinode余裕を数え、inode枯渇または過大なinode tableが確認された場合に変える。 |
| `-I` | inode size | 256 byte | 可 | 同 | 既定のまま | inode featureの互換性に加え、format容量とmetadata read量を比較し、現行256 byteより改善した場合だけ変える。 |
| `-J size=` | journal size | filesystem依存 | 可 | 同 | 実験で比べる | CardputerZero上で更新頻度、journal write量、異常停止後のfsck時間を測ってから選ぶ。 |
| `-O` | filesystem featureを指定 | 既定feature | 可 | 同 | 既定のまま | featureを追加するのはkernelとe2fsprogs双方の対応を確認し、生成imageのmount/fsck試験が通った場合に限る。 |
| `-E stride=` | allocation stride | なし | 可 | 同 | 既定のまま | SDのNAND geometryはcontroller/FTLに隠れる。geometryが公開され、実カードでstride変更によるwrite量またはlatency改善を測れた場合だけ設定する。 |
| `-E stripe_width=` | RAID stripe幅 | なし | 可 | 同 | 除外 | 単一SDのdata filesystemでRAID stripeを指定しない。 |
| `-E lazy_itable_init=` | inode tableを遅延初期化 | 有効 | 可 | 同 | 既定のまま | format時間、初回mountのbackground I/O、初回write latencyを比較し、遅延初期化の不利益が出た場合だけ無効化する。 |
| `-E lazy_journal_init=` | journalを遅延zero化 | 有効 | 可 | 同 | 既定のまま | format時間と初回mount時間を測り、初回I/Oを許容できない場合に同期初期化へ変える。 |
| `-E discard` | format時にdiscardを試みる | 有効 | 可 | 同 | 既定のまま | 同一カードでformat所要時間、後続write latency、discard実行の有無を比較し、遅延や失敗があれば`nodiscard`に変える。 |
| `-E nodiscard` | format時のdiscardを抑止 | 無効 | 可 | 同 | 実験で比べる | `-E discard`と同じカード・同じimageでformat時間と後続write latencyを測り、discardが遅いか失敗する場合に選ぶ。 |
| `metadata_csum` | metadata checksum | 有効 | 可 | 同 | 既定のまま | metadata破損検出を維持。file data checksumではない。 |
| `64bit` | 64-bit block number | 有効 | 可 | 同 | 既定のまま | e2fsprogs既定featureを使う。 |
| `extent` | extent mapを利用 | 有効 | 可 | 同 | 既定のまま | 通常のext4既定feature。 |
| `has_journal` | journalを作成 | 有効 | 可 | 同 | 既定のまま | 現行data filesystemのjournalを維持。 |
| `bigalloc` | cluster単位で割当 | 無効 | 可 | 同 | 実験で比べる | `/data`のfile-size分布からsmall-file内断片化を見積もり、metadata減少分よりspace浪費が小さい場合に限り候補にする。 |
| `casefold` | case-insensitive directory | 無効 | 可 | 同 | 除外 | 現行のfilename semanticsを変える理由がない。 |
| `encrypt` | fscrypt対応feature | 無効 | 可 | 同 | 除外 | 製品側の鍵管理・復旧設計が未実装。 |
| `inline_data` | 小fileをinode内へ格納 | 無効 | 可 | 同 | 実験で比べる | `/data`の小file個数、inode更新量、mount後のread/write latencyを測り、容量または時間が改善した場合だけ選ぶ。 |
| `orphan_file` | orphan inodeをまとめて管理 | 有効 | 可 | 同 | 既定のまま | e2fsprogs既定値を維持。 |
| `fast_commit` | journalのfast-commit recordを使う | tool/kernel既定 | 可 | 同 | 実験で比べる | fsync負荷の実測と電断後のreplay/fsck試験を行い、journal write量と復旧時間がordered dataの要件を保ったまま改善する場合に有効化する。 |
| `orphan_file_size` | orphan fileのinode数を指定 | tool既定 | 可 | 同 | 既定のまま | crash時に同時に処理するorphan inode数、format metadata量、fsck/recovery時間を測り、既定サイズが不足または過大と分かった場合だけ変える。 |
| `large_dir` / `dir_index` / `dir_nlink` | 大規模directory、HTree index、link count上限を制御 | feature依存 | 可 | 同 | 既定のまま | `/data`の最大directory entry数とlookup時間を測り、indexまたはlink-count制限が実際の容量・性能問題になる場合だけfeature構成を変える。 |
| `ea_inode` / `ext_attr` / `extra_isize` | xattrをinode内外へ格納し、追加inode fieldを使う | tool既定 | 可 | 同 | 既定のまま | xattrサイズ分布、inode table容量、metadata read/write量を測り、xattrがinode内に収まらずI/Oや容量を圧迫する場合だけ変更する。 |
| `filetype` / `flex_bg` / `meta_bg` / `resize_inode` / `sparse_super` / `sparse_super2` / `uninit_bg` | directory type、block group配置、backup superblock、拡張用metadataを制御 | feature依存 | 可 | 同 | 既定のまま | e2fsprogsと固定kernelの既定featureを保つ。変更はbackup metadata容量、mount/fsck時間、`msd-data-grow`後の拡張試験で差が出た場合に限る。 |
| `huge_file` / `large_file` / `64bit` / `stable_inodes` / `metadata_csum_seed` | 大容量file・block address・metadata checksum seedを扱う | tool既定 | 可 | 同 | 既定のまま | 現行imageのfeatureを維持し、生成imageがkernelでmountできることを確認する。`metadata_csum_seed`はmetadata保護でありfile data checksumではない。 |
| `verity` / `project` | fs-verityとproject ID trackingを使う | 無効 | 可 | 同 | 除外 | verity対象の署名済みimmutable fileやproject quota運用がなく、対象file・quota管理toolのない状態でmetadataを追加しない。 |

`mke2fs.conf`の`base_features`、`default_features`、`blocksize`、`inode_size`、`reserved_ratio`、`lazy_itable_init`等のprofile値は、用途profileと既定値の定義です。MSD/Linuxはmkfs optionで設定した値以外を独自に上書きせず、固定版の既定値を使います。profile項目の変更はe2fsprogs更新と併せて比較します。

## mountと永続設定

mount optionの全行は[ext4 mount optionと永続設定](filesystem-options-ext4-mount.md)に分けました。

## 点検と調整

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `e2fsck -p` | 安全な修復を自動適用 | 対話 | 可 | 同 | 現行のまま | 起動時の現行検査方式。 |
| `e2fsck -n` | 読取専用で検査 | 対話 | 可 | 同 | 実験で比べる | 検査のみの運用と復旧手順を比較する。 |
| `e2fsck -f` | cleanでも強制検査 | cleanなら省略 | 可 | 同 | 既定のまま | 起動ごとの全scanによるboot時間と、clean flagに頼らず検査する運用上の利点を測り、定期検査が必要になった場合に実行間隔を選ぶ。 |
| `e2fsck -c` | bad block scan | 無効 | 可 | 同 | 除外 | SD全域のscanを通常bootで行わない。 |
| `e2fsck -D` | directory最適化 | 無効 | 可 | 同 | 除外 | 運用時のrebuild用途で通常起動に使わない。 |
| `tune2fs -c` | mount間隔でfsck | 無効 | 可 | 同 | 既定のまま | expected boot count、異常停止頻度、全scan時間を記録し、mount回数で周期検査する必要が確認された場合だけ閾値を設定する。 |
| `tune2fs -i` | 時間間隔でfsck | 無効 | 可 | 同 | 既定のまま | uptime、電断/異常停止記録、fsck所要時間から時間周期の検査が必要と判断された場合に、許容できるmaintenance時間に合わせて設定する。 |
| `tune2fs -L` | label変更 | 既存値 | 可 | 同 | 除外 | image format時の`data` labelを維持。 |
| `tune2fs -O` | feature追加・削除 | 既存値 | 可 | 同 | 除外 | offline変換を伴い、image作成時に固定する。 |
| `tune2fs -m` | reserved block割合変更 | 既定5% | 可 | 同 | 実験で比べる | 実使用量を測ってから評価する。 |
| `tune2fs -o` | default mount option変更 | filesystem default | 可 | 同 | 除外 | mount policyはscriptとfstabで明示する。 |
| `tune2fs -E` | extended setting変更 | 設定依存 | 可 | 同 | 既定のまま | 変更する個別fieldが `/data` のrecovery、format latency、I/O量に与える効果を特定できた場合だけ、そのfield単位で互換性と回復試験を行う。 |

### 最新版との差分と個数

e2fsprogsは固定版・最新版とも1.47.4で、tool optionに版差はありません。kernel documentationは固定版6.18.59からmainline 7.4-rc1へ更新されています。現行ext4設定に対して新たに有効化すべきoptionの既定値変更はこの調査では確認していません。最新版mainlineでの全mount項目の意味差分は未確認です。本文の個別表は固定版・最新版で共通のoptionを扱います。

表の行数はoptionの総数や一次資料とのcoverageを示しません。CLI flag、filesystem feature、mount option、mke2fs.conf relationは同じ名前を重複排除して機械照合します。
