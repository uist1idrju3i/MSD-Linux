# /data file system比較実験の生データ

このbranchは、`/data` のfile system比較実験（QEMU）の生データを保管するためのものです。`main` とは履歴を共有しないorphan branchで、mergeもしません。削除しないでください。

実験の条件・手順・集計・結論は、`main` 側の `docs/experiments/` にある各実験記録に書いています。このbranchには解釈を書かず、記録の根拠となるfileだけを置きます。

## 置いているもの

`fs-compare/<group>/` に、run directoryのtext fileをgroupごとにまとめたarchiveを置いています。

| file | 内容 |
|---|---|
| `<group>.tar.zst` | 各run directoryの `qemu.log`、`host.log`、`summary.csv`、`run-meta.txt`、`progress.log`、`host-load.txt`、`*.sha256` など。path、mtime、内容は採取した時のまま |
| `<group>.files.sha256` | archiveに入れた各fileのSHA-256 |
| `SHA256SUMS` | 各archiveのSHA-256 |

| group | 対象 |
|---|---|
| `phase0` | 第0段（計測器の検証、1回あたりの時間の測定） |
| `phase1-pilot-and-fixes` | 第1段のpilot、最初の本番（`phase1-main`、T1判定器の修正前に中止）、T1判定器の修正と再確認、matrix driverの確認 |
| `phase1-r2` | 第1段の本番（620行、622 attempt） |
| `t2fix-check` | T2判定器（W2、W3、鍵fileの永続化）を直した後の確認 |
| `phase1-r3-t2-invalid` | 開発用containerの外で起動したため、全行が `exit_127` で無効になった実行。測定値としては使わない |
| `phase1-r3-t2-retry` | T2の全構成とI2・E1のT1のやり直し（402件、`docker/msd-dev` で実行） |
| `phase2-smoke` | 第2段のvariant smokeと再試験 |
| `phase2-pilot` | 第2段のpilot |
| `phase2-j8-check` | `T4-sync` の `-j 8` 並列性確認 |
| `phase2-t4` | 第2段の `T4-sync` 行列 |
| `phase2-main` | 第2段の `T3`、`T5`、`T6` 行列 |
| `phase2-main-r2` | 第2段の残行再実行 |
| `phase2-stackfix` | stack reopen修正後の `T3`、`T6` 再実行 |
| `stackfix-smoke` | stack reopen修正の対象構成smoke |
| `phase2-analysis` | 第2段の集計script、最終行データ、分析記録 |
| `phase2-plans` | 第2段のplan、input、hash、監視script |
| `build-logs` | 各runの `build/` にあった `mksquashfs.log` と `unsquashfs.log`（4,350 file）。`build/` を削除する前に保存した |
| `phase2-build-logs` | 第2段runの `build/` にあった `mksquashfs.log` と `unsquashfs.log`（2,386 file） |
| `misc` | build結果をhard linkでまとめた時の `hardlink -v` のlog（`dedup-build-hardlink-20261111.log.zst`）、削除前の全imageの一覧（`images-inventory-20261111.tsv`：path、見かけのsize、disk上のsize、mtime）、VM上に残すimageのrun directoryの一覧（`images-kept-20261111.txt`） |

## 置いていないもの

次のfileは大きすぎるため、このbranchに置いていません。

- 各runのSD image（`sdcard.img`）と、T1で書き出したpartition image（`*.ext4` など）。`misc/images-kept-20261111.txt` に挙げたrun directoryの分だけを作業用のVM上に残し、それ以外は削除しました。残したのは、実験記録で参照しているrun、電源断の後にfsyncより後の追記や1つ新しい更新が残っていたrun、診断に使ったimageです。削除したimageは、電源を切った瞬間の状態なので再現できません。
- 各runに写した `build/`（rootfsの展開とsquashfs）。すべて削除しました。同じcommitから再生成できます。squashfsのhashは各runの `inputs.sha256` に記録しています。再生成して同じbyte列になるかは確かめていません。中のlogは `build-logs` に保存しています。
- 第2段の各runのSD imageと `build/` の展開済みfile。archiveにはimageを含めず、`build/` からはtext logだけを別groupに収録しました。元のfileはrun directoryに残しており、削除していません。

## 第2段の削除前の照合（2026-11-12）

この照合では削除を実行していません。対象は `phase2-*`、`stackfix-*`、`t2fix-*` と、第1段のimage inventoryにない `build/` または `sdcard.img` を持つrunです。該当するdirectoryは1,270件で、追加のprefixはありませんでした。第1段の保持imageは変更しません。

- [coverage-phase2-20261112.tsv](fs-compare/misc/coverage-phase2-20261112.tsv): fileごとのSHA-256と一致したarchive。既存archiveの圧縮fileと各memberを読み、`SHA256SUMS` と `.files.sha256` の両方に一致することを確認しました。tarのhard link memberも元memberの内容で照合しました。archive内25,417 fileを検査し、対象のtext 10,762 fileはすべて保存済みの内容と一致しました。内訳は `build/` 内2,386、run直下7,105、run directory外のhost logなど1,271です。追加archiveは不要でした。
- [images-inventory-phase2-20261112.tsv](fs-compare/misc/images-inventory-phase2-20261112.tsv): 削除前のimage 2,381 fileのpath、見かけのsize、割り当てsize、mtime。`build/rootfs/` 内はimage収集・text照合から除外しました。binary扱いの拡張子は `.img`、`.squashfs`、`.ext2`、`.ext3`、`.ext4`、`.vfat`、`.fat`、`.f2fs`、`.btrfs`、`.erofs`、`.cramfs`、`.qcow2`、`.raw`、`.iso`、`.bin`、`.dtb` です。実際に対象内にあったimageは `sdcard.img` 1,192件と `build/` 内の `.squashfs` 1,189件です。
- [build-inventory-phase2-20261112.tsv](fs-compare/misc/build-inventory-phase2-20261112.tsv): `build/` 1,193 directoryのsize。各directory内では同じinodeを1回だけ数え、directoryとsymlink自身も含めています。異なるdirectory間のhard linkは各行に含まれるため、行の合計は解放容量とは限りません。
- [images-kept-phase2-20261112.txt](fs-compare/misc/images-kept-phase2-20261112.txt): 保持候補のrun名と理由をtabで区切った一覧です。保持するのは各runの `sdcard.img` だけで、`build/` は保持しません。main `49249878e9bb604dd4c12af723be30eea6c5e6a1` の第2段CSVに載る884 runはすべて現存し、全件を保持候補にしました。本文のj8/j4比較、E1/F1 smoke、stack reopen修正前の無効試行、失敗・中止・制約の診断、指定された追試の代表も含め、合計1,053件、割り当てsizeは185,635,528,704 bytesです。このうち3件は第1段から保護している `t2fix-*` です。
- [base-controls-phase2-20261112.tsv](fs-compare/misc/base-controls-phase2-20261112.tsv): 第1段の保持一覧から利用できるbase imageの対応です。T5のE1/B2は残っていますが、ほかのbase/testの組合せには該当する保持imageがありません。第2段のE1/F1 smokeは保持候補にしましたが、T4/T5のbase測定の代わりにはしません。失われたbase imageを再現済みとは扱いません。
- [deletion-candidates-phase2-20261112.txt](fs-compare/misc/deletion-candidates-phase2-20261112.txt): 承認待ちの削除候補です。run保存先からの相対pathで、`build/` 1,193件と非保持の `sdcard.img` 139件、合計1,332件を載せています。run直下とdirectory外のtext file、保持するimage、第0・第1段のrunは削除候補に含めていません。`build/` 内のlogはarchiveとの一致を確認済みで、`build/` と一緒に削除する候補です。
- [storage-audit-phase2-20261112.json](fs-compare/misc/storage-audit-phase2-20261112.json): 集計値と基準commitです。削除候補の全inodeを通してhard linkを重複排除し、削除対象外にlinkが残るinodeを除いた解放容量の見積もりは103,079,669,760 bytesです。候補外へのhard linkによって解放されない割り当ては0 bytesでした。実際に削除した後の空き容量は未確認です。

## archiveの検査

```sh
cd fs-compare
sha256sum -c SHA256SUMS
mkdir -p /tmp/x && zstd -dc phase1-r2.tar.zst | tar -xf - -C /tmp/x
(cd /tmp/x && sha256sum -c "$OLDPWD/phase1-r2.files.sha256")
```
