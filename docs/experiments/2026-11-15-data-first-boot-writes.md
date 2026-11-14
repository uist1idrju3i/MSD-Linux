# /data 初回起動の書き込み帰属

- 状態: QEMUで測定。原因は ext4lazyinit による新規groupのinode table初期化と特定
- 日付: 2026-11-15
- 担当: Devin
- 関連: [書き込みの台帳](../design/write-policy.md)、[起動後idleのpartition別書き込み](2026-11-12-write-inventory.md)

## 目的と仮説

前回の棚卸しで、初回boot後の最初の120秒でp7に8320 sectorの書き込みが残りました。
sfdiskのpartition書き換え・resize2fs・ext4lazyinitのどれが書いたかを、host側で段階的に処理済みのSD imageを作って分離します。
仮説は「大部分はresize2fsが残した未初期化inode tableへのext4lazyinitの書き込み」です。

## 採否の基準（計測前）

- 各variantを独立した3回のbootで測り、中央値・最小・最大を記録します。正の値は隠しません。
- variant間の差で、sfdiskのpartition表・resize2fs・ext4lazyinitの寄与を分離します。
- 判定の副証拠として、前後のp7領域をhost側でbyte比較し、dumpe2fsのgroup flagと照合します。
- disk positive controlは従来どおり `/data` への1 MiB書き込みでmmcblk0p7が2048 sector以上増えること。

## 条件と手順

基準は `733d27e66c8499aa306325cb4ce928c6ed2f1034`、Buildrootは `8b238854d909c9cce32ef9671d968b03e323b55d`。
`O=output-openssl-lts` のwarm treeをdefconfigから再構築して使いました（sdcard.img 771,751,936 bytes）。
実際のQEMUは11.1.2、kernelは6.18.59-v8、hostのe2fsprogsは1.47.4、hostのsfdiskはutil-linux 2.41.3です。

計測器と1区間120秒のprobeは [write-inventoryのrunnerとguest](../../board/cardputerzero/tools/bench/write-inventory/) をそのまま使い、`--windows 3` に変えました。
variantごとに `output-dwcause/input-<variant>/` へ `sdcard.img` と `Image`・`rootfs.squashfs`・`bcm2710-rpi-cm0.dtb`・`.config`・`host` を揃え、`--output` に渡しました。

| variant | 入力画像に施したhost側処理 | guestで残る処理 |
|---|---|---|
| base | なし（生成物のまま） | sfdisk＋resize2fs＋lazyinit |
| grown-fs64 | p4・p7を1 GiB末尾までsfdiskで拡張 | resize2fs＋lazyinit |
| pregrown | grown-fs64＋hostのresize2fs | lazyinitのみ |
| pregrown-nolazy | p4・p7拡張＋grown寸法でlazy無効mkfs | なし（全group初期化済み） |
| mature | baseのboot後imageを再利用 | なし（2回目以降の状態） |

grown系の拡張は `sfdisk --no-reread -N` を `msd-data-grow` と同じ引数列（`start=…, size=…, type=…`）で行い、partxによるkernel通知だけは除きました。
pregrown-nolazyは `mke2fs -t ext4 -F -b 4096 -L data -E lazy_itable_init=0,lazy_journal_init=0` で352 MiB分を作り直してp7へ書き戻しています。
resize2fs 1.47.4では新規groupが `INODE_UNINIT` のまま残ることをdumpe2fsで確認済みです（group 1・2）。
inode数はresize後49,152（16384/group）で、pregrown-nolazyの新規mkfsは90,144です。inode tableの総量が違うためpregrown-nolazyは別のFSですが、「初期化済みか」の条件比較には使えます。

## 結果

p7のwrite_sectors差分（512 bytes単位）。bootはprobe開始時の累積、idleNは各120秒区間の増分です。

| variant | boot | idle1 | idle2 | idle3 | 計 | n |
|---|---:|---:|---:|---:|---:|---|
| base | 8648 | 8304 | 0 | 0 | 16952 | 3 |
| grown-fs64 | 8648 | 8304 | 0 | 0 | 16952 | 3 |
| pregrown | 8320–8328 | 8304 | 0 | 0 | 16624–16632 | 3 |
| pregrown-nolazy | 120 | 72 | 0 | 0 | 192 | 3 |
| mature | 424 | 0 | 0 | 0 | 424 | 3 |

base・grown-fs64・pregrown-nolazy・matureは3回とも全く同じ値で、QEMUのcounterはこの規模ではほぼ決定的です。pregrownはr3のみbootに+8 sectorの揺らぎがありました。

### host側のbyte比較（base-r1）

- pristine p7（64 MiB）とboot後p7の先頭64 MiBの差分: 実byteで約11.9 KBのみ。
- hostでresize済みのp7（352 MiB）とboot後p7の全領域差分: 15,305 byteのみ。
- boot後のgroup flag: group 0・1は `[ITABLE_ZEROED]`、group 2は `[INODE_UNINIT, ITABLE_ZEROED]`。

書き込みsector数（16,952 ≈ 8.3 MiB）に対し実byte差は約12〜15 KBしかありません。
growで広げた領域はsparse（ゼロ）のため、lazyinitが未初期化のinode tableへゼロを書いてもbyte差分として現れないことが分かります。

## 帰属

- **ext4lazyinit**: 16,384 sector（新規2 group × 8192 sectorのinode table）。初回書き込みの約97%。pregrownでも残るためresize2fs自身の書き込みではなく、mount後のkernel threadの処理です。pregrown-nolazyで消えたことが裏付けです。
- **sfdiskのpartition表**: 16 sector（8 KiB）。partition表はp7ではなく `mmcblk0` 側（先頭のMBRと拡張領域先頭のEBR）へ書かれるため、p7のcounterには出ません。baseのmmcblk0全体とp7の差は全3回とも16 sector、grown-fs64は0で、guest内のsfdisk分がそのままこの差として分離できました。
- **resize2fs**: baseとpregrownのboot差 328 sectorが、hostへ移したresize2fs自身の書き込みに相当します。同じ処理をguest内でやるかhostで済ませるかだけで、lazyinitの仕事量は変わりません。
- **fsck＋mount＋mkdir・journal等の実書き込み**: pregrown-nolazyのboot=120、matureのboot=424が下限と典型値です。
- baseの16952（p7）＋16（disk側のpartition表）＝16,968が初回bootの書き込み量で、その内訳は「実処理 約570 sector＋lazyinit 16,384 sector＋partition表 16 sector」です。

初回bootの書き込みは、ほぼ全量が「resizeで追加されたgroupのinode tableを埋める」lazyinit由来と確定しました。
write-policy.mdの「online resize後の書き込み」の未対応項目は、この帰属に更新します。

## 失敗・限界

| 試行・確認 | 結果と扱い |
|---|---|
| grown-fs64-r1・pregrown-r1・pregrown-nolazy-r1（初回） | input内のsymlinkをhostの絶対pathで作り、開発OCIの `/work` から解決できずFileNotFoundError。失敗したrun dirは保存し、相対symlinkに直して再試行・完走 |
| mature-r1 | 測定中にrun dirを移動してしまい後処理が失敗。serial.logからraw.csvを再生成して救済。値は正常範囲 |
| QEMUのcounter | guestから見たblock書き込みで、SD実機・FTLの書き込み量ではありません。sparse imageのため「ゼロへのゼロ書き込み」はbyte差分に出ませんが、sector数の帰属は成立します |
| 実機 | 未測定。実SDでは新規領域の内容がゼロとは限らず、lazyinitの書き込み量自体は同じでも消費・寿命への意味づけは別途評価が要ります |
| 測定の並行負荷 | fs-compare matrix・kernel buildと同時実行。sector counterはhost負荷で変わらないが、wall timeは伸びています |

## 再生成

```sh
# 画像の再生成（warm build）
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-openssl-lts msd_cardputerzero_defconfig && make -C output-openssl-lts -j8'
# variant入力の生成と測定ドライバー（収録スクリプト。出力先はoutput-dwcause）
sh docs/experiments/2026-11-15-data-first-boot-writes-prepare-variants.sh
sh docs/experiments/2026-11-15-data-first-boot-writes-run.sh
# host側比較・集計
sh docs/experiments/2026-11-15-data-first-boot-writes-forensic-p7.sh <run dir>
docker/msd-dev python3 docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py
```

raw CSVは [2026-11-15-data-first-boot-writes.csv](2026-11-15-data-first-boot-writes.csv)。run directoryのmetadata.jsonに入力hash、serial.logにQEMU provenanceが入っています。
大きなsdcard.img・serial logはcommitせず、data branch `data/fs-compare-experiments` 側へ移すか上記で再生成します。
