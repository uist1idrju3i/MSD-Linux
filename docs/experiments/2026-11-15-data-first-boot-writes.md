# /data 初回起動の書き込み帰属

- 状態: このQEMU条件ではext4lazyinitが主因と考えられる。単独の寄与量には比較条件の差が残る
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
inode数はresize後49,152（16384/group）で、pregrown-nolazyの新規mkfsは90,144です。inode tableの総量・FS metadataも異なり、lazy初期化だけを切り替えた対照ではありません。差の全量をlazyinitだけへ帰属することはできません。

## 結果

p7のwrite_sectors差分（512 bytes単位）。bootはprobe開始時の累積、idleNは各120秒区間の増分です。前回の8320はboot後最初の120秒のidle増分で、この表のbase合計16952（boot累積8648＋idle1の8304＋idle2/3の0）とは測定範囲が違います。同じ量の再測定値として比較しません。

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

- **ext4lazyinit**: 新規2 group × 8192 sectorのinode tableは16,384 sectorで、base合計の約97%に相当します。pregrownでも書き込みが残り、初期化済みFSで減ることは主因という仮説を支持します。ただし別mkfsとの比較なので、この数値を独立に測った寄与量とはしません。
- **sfdiskのpartition表**: 16 sector（8 KiB）。partition表はp7ではなく `mmcblk0` 側（先頭のMBRと拡張領域先頭のEBR）へ書かれるため、p7のcounterには出ません。baseのmmcblk0全体とp7の差は全3回とも16 sector、grown-fs64は0で、guest内のsfdisk分がそのままこの差として分離できました。
- **resize2fs**: baseとpregrownのboot差は320〜328 sectorです。hostで処理を済ませた条件との差であり、起動順序・metadata状態の影響を含み得ます。
- **fsck＋mount＋mkdir・journal等**: pregrown-nolazyのboot=120、matureのboot=424を観測しました。FSと起動履歴が違うため一般的な下限や典型値とはしません。
- baseの16952（p7）＋16（disk側のpartition表）＝16,968がこの条件で観測した合計です。以前の「実処理約570＋lazyinit 16,384＋partition表16」は推定内訳で、全処理を個別に測った値ではありません。

このQEMU条件では、resize後のinode table初期化が主因と考えられます。別image・実機への一般化と、lazy設定以外を揃えた寄与量の測定は未実施です。書き込み台帳にもこの限界を残します。

## 失敗・限界

| 試行・確認 | 結果と扱い |
|---|---|
| grown-fs64-r1・pregrown-r1・pregrown-nolazy-r1（初回） | input内のsymlinkをhostの絶対pathで作り、開発OCIの `/work` から解決できずFileNotFoundError。失敗したrun dirは保存し、相対symlinkに直して再試行・完走 |
| mature-r1 | 測定中にrun dirを移動してしまい後処理が失敗。serial.logからraw.csvを再生成して救済。値は正常範囲 |
| QEMUのcounter | guestから見たblock書き込みで、SD実機・FTLの書き込み量ではありません。sparse imageのため「ゼロへのゼロ書き込み」はbyte差分に出ません。counterだけでは書いたprocessを特定できません |
| 実機 | 未測定。実SDでは新規領域の内容がゼロとは限らず、lazyinitの書き込み量自体は同じでも消費・寿命への意味づけは別途評価が要ります |
| 測定の並行負荷 | fs-compare matrix・kernel buildと同時実行。sector counterはhost負荷で変わらないが、wall timeは伸びています |

## 再生成

```sh
# 画像の再生成（warm build）
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-openssl-lts msd_cardputerzero_defconfig && make -C output-openssl-lts -j8'
# variant入力の生成と測定ドライバー（収録スクリプト。出力先はoutput-dwcause）
docker/msd-dev sh docs/experiments/2026-11-15-data-first-boot-writes-prepare-variants.sh
docker/msd-dev sh docs/experiments/2026-11-15-data-first-boot-writes-run.sh
# host側比較・集計
sh docs/experiments/2026-11-15-data-first-boot-writes-forensic-p7.sh <run dir>
docker/msd-dev python3 docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py output-dwcause/runs
```

raw CSVは [2026-11-15-data-first-boot-writes.csv](2026-11-15-data-first-boot-writes.csv)。run directoryのmetadata.jsonに入力hash、serial.logにQEMU provenanceが入っています。
serial log・metadata・失敗試行は[data枝のE1 archive](https://github.com/uist1idrju3i/MSD-Linux/blob/ab61a9ffa86635b02e0382f357d7da9e7d084077/session-2026-11-15/evidence/e1-data-first-boot.tar.zst)に保存済みです。archiveのSHA-256は `df346838ac22c9fe5d0dcf1a1fe7b116fe7bb8cd8a1207008d97d062a71f946b`。image本体は含みません。

### 再現用scriptの修正（監査後）

上記は新しい出力先で行う手順です。既存の `input-*` は上書きせず停止し、中間imageも実行ごとの別directoryへ保持します。入力のp4/p7位置はsfdiskから取得し、DOS/512 byte sector・64 MiB p7という前提を検査します。相対symlinkと `inputs.sha256` を作り、container内でも参照できるようにしました。別の出力先を使う場合は、同じcontainer内で `env E1_WORK_DIR=<新規作業先> E1_OUTPUT_DIR=<build出力>` をscriptに渡します。

run driverはrunner成功後に全8 deviceのboot・idle・RAM/disk controlのphase数、単調counter、区間長、正の対照、serial完了markerを検査し、raw・serial・metadataのhashを `e1-complete.json` に記録します。この記録と条件が一致したrunだけ再利用します。不完全runは一意の `.failed-*` 配下へ退避し、1件でも失敗した実行は終了値1にします。集計は既定で5 variant各3回も検査し、一部のrunだけで要約を出しません。条件を変えた場合は `--windows`・`--seconds`・`--repeats`・`--variants` を揃えます。既存の測定中directoryへ並行実行しません。

旧runにはこの完了記録がありません。旧rawの構造だけを再検査する場合は集計に `--legacy` を明示します。このmodeは旧fileを変更せず、当時のrunner終了値の成功を新たに証明しません。mature-r1の救済履歴も消しません。集計器のfixtureは `python3 tests/e1-write-attribution/run.py`。今回はscriptのhost検査だけで、新しいQEMU測定は行っていません。

未保全text87件、FEC確認器/build driver、監査と復元限界付き添付は[data枝の追加保全](https://github.com/uist1idrju3i/MSD-Linux/tree/5bc9844af3b39212252ed6361ff7c5e66f8bc110/sessions-2026-11-15)に保存しました。`manifest.json` と `evidence.files.sha256` で保存内容を照合できます。
