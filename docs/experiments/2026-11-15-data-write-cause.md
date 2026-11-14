# 起動直後の `/data` 書き込みの原因分解

- 状態: 計画
- 日付: 2026-11-15
- 担当: Devin
- 関連: [起動後idleのpartition別書き込みとtimezone](2026-11-12-write-inventory.md)、[書き込みの台帳](../design/write-policy.md)

## 目的と仮説

2026-11-12-write-inventoryで、初回bootの最初の120秒に `/data`（mmcblk0p7）へ8320 sector（約4.1 MiB）が書き込まれ、その後は0だった。拡張済みimageの再bootでは64 sectorだけだった。起動直後に重なっている候補は次の3つで、寄与を変種で分解する。

- `msd-data-grow` が行う p7 の拡張と `resize2fs`（新しいgroupのdescriptor・bitmap・inode tableなど）
- mkfs時に初期化を後回しにされた inode tableなどを kernel の `ext4lazyinit` worker が埋める処理
- `fsck -p`、`mkdir -p /data/etc /data/msd-update`、mount時のjournal処理などの残差

仮説：resize2fsとlazyinitの合計が8320 sectorの大部分を説明する。どちらが主な原因かは事前には断定しない。

## 採否の基準（計測前）

- 各変種の最初の120秒区間で、mmcblk0p7の書き込みsector差分を測る。変種の差から次の寄与を算出する。
  - grow+resizeの寄与 = nolazy − nolazy-nogrow
  - lazyinitの寄与 = nogrow − nolazy-nogrow
  - 残差 = nolazy-nogrow
- baselineは8320 sectorを±20%の範囲で再現すること。外れた場合は、製品の変更（seedrngの非保存など）による差として記録し、分解の比較はこのbuild内で完結させる。
- 全量が分解できなくても、各変種の実測値とlogをそのまま記録する。寄与が分かれなかった場合は「未分解」と結論し、block単位の追跡を追加計画に残す。
- どの変種でもdisk positive controlが2048 sector以上を登録すること。満たさない試行は無効として扱い、run IDと理由を残す。
- serial logの `msd-data-grow:` 行で、growが実際に走ったか（`extending partition 7`）を各runで確認し、想定と違う場合はその変種を無効の扱いとせず別の結論として記録する。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | 733d27e（main、PR #243 merge後） |
| ホスト | Ubuntu（VM。版は記録時に埋める） |
| QEMU | （`run-qemu:` 行から記録時に埋める） |
| Buildroot / GCC / カーネル | `8b238854d909c9cce32ef9671d968b03e323b55d` / （記録時） / （記録時） |
| 使ったツールの版 | genimage・mke2fsは `output/host/` の実binaryから取る |
| 出力先と状態 | `O=output`、このVMでのcold build |
| 変える条件 | (a) data.ext4のmke2fs lazy init（`lazy_itable_init=0,lazy_journal_init=0` の有無）、(b) SD imageを2のべき乗に拡張するか（growの有無） |
| 変えない条件 | kernel、DTB、rootfs、probe、QEMUの引数、120秒×5区間 |
| 繰り返し | 各変種1回。原因分解は観測量の大小ではなく変種間の差で行う。baselineが前回と大きく違う場合だけ追加試行する |
| 入力とバイナリ | runごとの `metadata.json`（入力hash）と serial logの `run-qemu:` 行 |
| 初回と失敗の扱い | timeout・control失敗の試行は生logを残して次のrun IDで再試行 |

## 手順

```sh
# lazy init無効の変種だけを作る（lazy側はstockの output/images をそのまま使う）
docker/msd-dev board/cardputerzero/tools/bench/write-inventory/variant-image.sh \
  output "-E lazy_itable_init=0,lazy_journal_init=0" output-data-cause/nolazy

# 各run（--pad none はimageを2のべき乗に拡張しない）
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output                  --run-dir output-data-cause/runs/base           --variant base           --pad pow2
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-data-cause/nolazy --run-dir output-data-cause/runs/nolazy        --variant nolazy         --pad pow2
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output                  --run-dir output-data-cause/runs/nogrow         --variant nogrow         --pad none
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-data-cause/nolazy --run-dir output-data-cause/runs/nolazy-nogrow --variant nolazy-nogrow  --pad none
```

`nolazy` は `data.ext4` のmke2fs引数だけを変えた写しで、それ以外（kernel、DTB、rootfs、imageの他partition）はstockと同じgenimage出力から作る。variant-image.shはgenimage.cfgの写しで `data.ext4` のextraargsだけを書き換えてgenimageを再実行し、run.py互換の入力dir（symlink + 変種sdcard.img）を作る。run.pyには `--pad` 選択を追加した（このPRに含む）。

## 計測器の検証

- 前回の実績：RAM controlが0、disk controlがmmcblk0・p7で2048 sector超を登録。
- 今回も各runで同じpositive controlを行い、serialの `msd-data-grow:` 行でgrowの有無を確認する。
- baselineが8320 sectorに対して大きくずれた場合は、計測器のA/Aとして同じ条件の再試行を1回行う。

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
