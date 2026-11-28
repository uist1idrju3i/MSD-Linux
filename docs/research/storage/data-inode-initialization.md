# /dataのinode table初期化と書き込み時機

[保存領域の索引へ戻る](README.md)

以下の製品設定はPR C段1前のext4経路の記録です。現在の接続は[書込み台帳](../../design/write-policy.md)を参照してください。

## 判断と範囲

新規SDにはB1（`noinit_itable`でmountしてonline grow）とD（fallback mkfsのlazy初期化を無効化）を採用します。書き込みを消すのではなくformat・grow中へ移す変更です。progressはまだ実装しておらず、[AGENTS.md §10](../../../AGENTS.md)への適合は未達です。[書き込み台帳](../../design/write-policy.md)と[QEMU追試](../../experiments/2026-11-17-data-sync-itable.md)を参照してください。

この文書の「事実」は固定版source、「推論」はsourceと既存測定からの判断、「未確認」は実行していない範囲です。QEMUの実測は別記録へ分けます。

## 現行経路の事実

- [genimage.cfg](../../../board/cardputerzero/genimage.cfg)は64 MiBのext4を `use-mke2fs`、`-b 4096` で作ります。genimage v20自身が非lazyのextended optionを付けます（資料G）。
- [S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)はext4 magicを調べ、認識できず先頭64 MiBがゼロの時だけfallback formatします。変更前は両lazy optionを明示していませんでした。変更後は `-E lazy_itable_init=0,lazy_journal_init=0` を指定します。
- fsck後の明示mountに `noinit_itable` を追加し、[fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)にも同じ指定を残します。[msd-data-grow](https://github.com/uist1idrju3i/MSD-Linux/blob/73b7f3d6db239186c617c713b36bad53494cb96b/board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow)はpartition 4・7、kernelへの通知、`resize2fs` の順で処理します。grow自身の処理は変えません。
- overlay内のmount・remountを検索し、通常の `/data` mountはS02だけでした。msd-updateの一時mountはFAT用で、`/data` のremountはありません。管理者が別のoptionで手動mountする経路まで禁止する変更ではありません。

## 固定版sourceの事実

kernelはRaspberry Pi Linux `b3495ea401d709af0701a85babcba5e3d788a602`（6.18.59）、e2fsprogsは1.47.4です。

1. `noinit_itable` はbackground初期化を無効にします。`init_itable=0` はgroup間の意図的な待ちをなくすだけで、同期処理へは変わりません（K1・K2）。
2. online `resize2fs` はkernel ioctlへ渡します（E1）。kernelは `INIT_INODE_TABLE` が無効な時、新groupに `EXT4_BG_INODE_ZEROED` を設定する経路を選び、そのtableを `sb_issue_zeroout()` で同期初期化します。resize後のjournal flushと、optionが有効な場合だけのlazyinit登録もあります（K3・K4）。既存groupの未初期化table全てを処理する経路ではありません。
3. `ext4_has_group_desc_csum()` は `metadata_csum` と `gdt_csum` の両方を扱います。未初期化flagとchecksumは対応済みの管理方式です。新規inodeの割当では内容を初期化します（K5・K6）。未初期化tableを残すことは安全消去ではなく、生deviceの旧内容を消す保証にはなりません。
4. 有効な未初期化groupはe2fsckのinode scanでskipされるので、毎bootの `e2fsck -p` を全tableのzero完了処理とはみなせません。明示的discardと、discard後のゼロ読取りを保証するdeviceという条件ではzeroed扱いにする経路もあります（E2・E3）。後日の通常rw mountや `init_itable` を有効にするremountではbackground初期化が再開し得ます（K2）。unmount時に自動完了する保証はありません。
5. offline resizeも単にunmountすれば非lazyになるわけではありません。Eの実装には `RESIZE2FS_FORCE_ITABLE_INIT=1` で非lazyにする経路がありますが、公開manのoptionではなく版依存です。`resize2fs -p` の進捗表示はoffline専用です（E4・E5）。
6. mke2fsのitableは現代kernelでlazyが既定候補ですが、journalのprofile fallbackは0です。「両方が必ずlazy既定」とは言えません。明示的に両方0へ固定する変更で、未測定のjournal改善量を加算しません（E6・E7）。

`INODE_UNINIT` はinode未使用のflagで、tableのzero完了は `ITABLE_ZEROED`（kernel名 `EXT4_BG_INODE_ZEROED`）で別に判定します。旧SDに `INODE_UNINIT` があり、かつtableが未zeroなら、今回のmount optionでbackground処理を止めても未zeroのままです。既存SDの完了処理は未対応です。

## 案の比較

| 案 | 変更箇所 | 量・時間の推論 | 安全性と§10 |
|---|---|---|---|
| A: 常時noinit_itable | S02とfstab | 既存tableのbackground zeroを抑止。新規growの分は同期処理へ移る | 既存の未zero tableは残る。progressがない単独変更では不適合 |
| B1: noinit_itableでonline grow（採用） | S02とfstab。growは既存の呼出しを維持 | 旧QEMU条件の新tableなら約8 MiB＋metadata。grow時間へ移る | flagだけを偽装する案ではない。progress・成功判定を備えれば適合可能だが表示は未対応 |
| B2: init_itable=0で待機 | 初期設定と完了判定 | 量は原則同じ、group間待ちを短縮 | resize終了やsyncだけでは完了証明にならない。全group・error・flushの安全な判定は未確認 |
| B3: 強制同期offline resize | mount前へgrowを移し環境変数を設定 | 量は原則同じ、mount前の待ちが増える | 非公開変数に依存。progress付きなら適合可能だが今回は不採用 |
| C: build時pre-size | genimageのFS・partition寸法とgrow方針 | deviceでのgrowを除去、imageとflash量が増える。inode数も変わり得る | 固定容量向き。SD全容量を共通imageで使う用途とは両立しにくい |
| D: fallback mkfs非lazy（採用） | S02 | formatへtable・journal初期化を集める。量は寸法とfeature次第 | growの代策ではない。formatのprogressも依然必要 |

[旧測定](../../experiments/2026-11-15-data-first-boot-writes.md)のp7計16,952 sectorに対し、新table 2 groupの寸法は16,384 sectorでした。これが主因という仮説は支持されますが、比較側のinode数が異なり、約97%を独立した実測寄与量と断定しません。

## 未確認の点

実SDでの時間・FTL書き込み・電源断回復、既存SD全tableの完了処理、progressとLCDの表示は未確認です。metadata破損時の復旧に影響がないとは断定しません。journalやchecksumを無効化する案は採用しません。

## 一次資料

kernelのURLは全て上記固定commit、Eはv1.47.4です。

- K1: [ext4.rst:330–342](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/ext4.rst#L330-L342)
- K2: [super.cのlazyinit登録・remount](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/super.c#L3939-L3957)、同ファイル6746–6752行
- K3: [resize.cのzeroout](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/resize.c#L618-L629)、[flag選択](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/resize.c#L1648-L1673)
- K4: [ioctl.cのresize・flush・lazyinit登録](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/ioctl.c#L1733-L1770)
- K5: [ext4.hのchecksum判定](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/ext4.h#L3390-L3394)
- K6: [inode.cの新規inode初期化](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/inode.c#L5691-L5696)
- E1: [online.cのioctl](https://github.com/tytso/e2fsprogs/blob/v1.47.4/resize/online.c#L134-L145)
- E2: [inode.cの未初期化groupのskip](https://github.com/tytso/e2fsprogs/blob/v1.47.4/lib/ext2fs/inode.c#L639-L642)
- E3: [pass5.cのdiscard条件](https://github.com/tytso/e2fsprogs/blob/v1.47.4/e2fsck/pass5.c#L731-L742)
- E4: [resize2fs.cの環境変数](https://github.com/tytso/e2fsprogs/blob/v1.47.4/resize/resize2fs.c#L937-L943)、同ファイル1169–1220行
- E5: [resize2fs manのprogress](https://github.com/tytso/e2fsprogs/blob/v1.47.4/resize/resize2fs.8.in#L131-L136)
- E6: [mke2fs.cの既定値](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.c#L2611-L2629)
- E7: [mke2fs manのlazy初期化](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.8.in#L253-L266)
- G: [genimage v20の非lazy指定](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c#L67-L101)
