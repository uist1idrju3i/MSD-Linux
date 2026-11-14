# 起動直後の `/data` 書き込みの原因分解

- 状態: 計画
- 日付: 2026-11-15
- 担当: Devin
- 関連: [起動後idleのpartition別書き込みとtimezone](2026-11-12-write-inventory.md)、[書き込みの台帳](../design/write-policy.md)

## 目的と仮説

2026-11-12-write-inventoryで、初回bootの最初の120秒に `/data`（mmcblk0p7）へ8320 sector（約4.1 MiB）が書き込まれ、その後は0だった。拡張済みimageの再bootでは64 sectorだけだった。起動直後に重なっている候補は次の3つで、寄与を変種で分解する。

- `msd-data-grow` が行う p4・p7 の拡張と `resize2fs`（新しいgroupのdescriptor・bitmap・inode tableなど）
- mkfs時に初期化を後回しにされた inode tableなどを kernel の `ext4lazyinit` worker が埋める処理
- `fsck -p`、`mkdir -p /data/etc /data/msd-update`、mount時のjournal処理などの残差

仮説：resize2fsとlazyinitの合計が8320 sectorの大部分を説明する。どちらが主な原因かは事前には断定しない。

## 採否の基準（計測前）

- 各変種の最初の120秒区間で、mmcblk0p7の書き込みsector差分を測る。変種の差から次の寄与を算出する（各変種の中央値で計算する）。
  - grow+resizeの寄与 = nolazy − nolazy-nogrow
  - lazyinitの寄与 = base − nolazy（fs約960 MiB規模）で、参考として nogrow − nolazy-nogrow（fs約350 MiB規模）も併記する
  - 残差 = nolazy-nogrow
- baselineの中央値が8320 sectorを±20%の範囲で再現すること。外れた場合は、製品の変更（seedrngの非保存など）による差として記録し、分解の比較はこのbuild内で完結させる。
- 全量が分解できなくても、各変種の実測値とlogをそのまま記録する。寄与が分かれなかった場合は「未分解」と結論し、block単位の追跡を追加計画に残す。
- どの変種でもdisk positive controlが2048 sector以上を登録すること。満たさない試行は無効として扱い、run IDと理由を残す。
- serial logの `msd-data-grow:` 行で、growが実際に走ったか（`extending partition 7`）を各runで確認し、想定と違う場合はその変種を無効の扱いとせず別の結論として記録する。
- nogrow系の変種では、p7の末尾がdisk末尾と一致することを、variant作成時の `sfdisk -d` 出力で確認する。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | 733d27e（main、PR #243 merge後） |
| ホスト | Ubuntu（VM。版は記録時に埋める） |
| QEMU | （`run-qemu:` 行から記録時に埋める） |
| Buildroot / GCC / カーネル | `8b238854d909c9cce32ef9671d968b03e323b55d` / （記録時） / （記録時） |
| 使ったツールの版 | genimage・mke2fsは `output/host/` の実binaryから取る（variant-image.shがPATHの先頭に置く） |
| 出力先と状態 | `O=output`、このVMでのcold build |
| 変える条件 | (a) data.ext4のmke2fs lazy init（`lazy_itable_init=0,lazy_journal_init=0` の有無）、(b) 初回boot時点でp4・p7がdisk末尾まで拡張済みか（growの有無） |
| 変えない条件 | kernel、DTB、rootfs、probe、QEMUの引数、120秒×5区間 |
| 繰り返し | 各変種5回。寄与の計算には中央値を使い、最小・最大も併記する |
| 入力とバイナリ | runごとの `metadata.json`（入力hash）と serial logの `run-qemu:` 行 |
| 初回と失敗の扱い | timeout・control失敗の試行は生logを残して次のrun IDで再試行 |

## 手順

nogrow条件の作り方が計測の肝なので、先に説明する。QEMUのSDは2のべき乗サイズしか受け付けないため、「imageを拡張しない」は起動しない。代わりに、host側で `msd-data-grow` と同じsfdisk操作をbase imageの写しに適用し、guestが「拡張済み」と見なす状態を作る。さらに `msd-data-grow` はgrowの有無に関わらず `resize2fs` を無条件で呼ぶため、resize2fsがno-opになるよう、data.ext4自体をp7の新しい大きさまで拡げた変種を使う。このときlazyinitの規模はfsの大きさに依存するため、寄与の算出では規模の違いを明記する。

`variant-image.sh` はgenimage.cfgの写しで `data.ext4` のextraargsとsizeだけを書き換えてgenimageを再実行し、できたdata.ext4をbase imageの写しのp7位置にddで差し替える。p1〜p6はbase imageとbyte単位で同じになるため、変種間で変わるのはp7の中身と、nogrow変種のpartition tableだけである。同一性の証拠は `partition-hashes.txt` に各partition領域のSHA-256を残す。

```sh
# 変種の作成（TOTAL_BYTES を付けると image を pow2 に切り詰め、p4・p7 を末尾まで
# sfdisk で拡張し、p7 を埋める大きさの data.ext4 を差し込む）
docker/msd-dev board/cardputerzero/tools/bench/write-inventory/variant-image.sh \
  output "-E lazy_itable_init=0,lazy_journal_init=0" output-data-cause/nolazy
docker/msd-dev board/cardputerzero/tools/bench/write-inventory/variant-image.sh \
  output "" output-data-cause/nogrow 1073741824
docker/msd-dev board/cardputerzero/tools/bench/write-inventory/variant-image.sh \
  output "-E lazy_itable_init=0,lazy_journal_init=0" output-data-cause/nolazy-nogrow 1073741824

# 各変種5回（iは1..5）
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output <variant_dir> --run-dir output-data-cause/runs/<variant>-<i> --variant <variant>
```

base は `output`、nolazy は `output-data-cause/nolazy`、nogrow は `output-data-cause/nogrow`、nolazy-nogrow は `output-data-cause/nolazy-nogrow` を `--output` に渡す。TOTAL_BYTES はrun.pyが行うpow2切り詰めと同じ1 GiBを選び、base・nolazyと同じdiskサイズで比較する。

## 計測器の検証

- 前回の実績：RAM controlが0、disk controlがmmcblk0・p7で2048 sector超を登録。
- 今回も各runで同じpositive controlを行い、serialの `msd-data-grow:` 行でgrowの有無を確認する。
- baselineの中央値が8320 sectorに対して大きくずれた場合は、計測器のA/Aとして同じ条件の再試行を1回行う。
- variant作成時に `partition-hashes.txt` でp1〜p6がbaseとbyte同一であることを確認する。

## 結果

（実施後に書く）

## 捨てた試行と経緯

（実施後に書く）

## 結論

（実施後に書く。QEMUでの値であり実機の値ではない）

## 未確認の点

- 実機のSDとFTLの書き込み量、shutdown時の書き込み、別容量のSD。
- process別のblock帰属（dm-log-writesなど）。分解が不十分なら追加計画とする。

## ログ

（実施後：run dirの一覧とSHA-256、data branchへの保存先）
