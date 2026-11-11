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
| `build-logs` | 各runの `build/` にあった `mksquashfs.log` と `unsquashfs.log`（4,350 file）。`build/` を削除する前に保存した |
| `misc` | build結果をhard linkでまとめた時の `hardlink -v` のlog（`dedup-build-hardlink-20261111.log.zst`）、削除前の全imageの一覧（`images-inventory-20261111.tsv`：path、見かけのsize、disk上のsize、mtime）、VM上に残すimageのrun directoryの一覧（`images-kept-20261111.txt`） |

## 置いていないもの

次のfileは大きすぎるため、このbranchに置いていません。

- 各runのSD image（`sdcard.img`）と、T1で書き出したpartition image（`*.ext4` など）。`misc/images-kept-20261111.txt` に挙げたrun directoryの分だけを作業用のVM上に残し、それ以外は削除しました。残したのは、実験記録で参照しているrun、電源断の後にfsyncより後の追記や1つ新しい更新が残っていたrun、診断に使ったimageです。削除したimageは、電源を切った瞬間の状態なので再現できません。
- 各runに写した `build/`（rootfsの展開とsquashfs）。すべて削除しました。同じcommitから再生成できます。squashfsのhashは各runの `inputs.sha256` に記録しています。再生成して同じbyte列になるかは確かめていません。中のlogは `build-logs` に保存しています。

## 確かめ方

```sh
cd fs-compare
sha256sum -c SHA256SUMS
mkdir -p /tmp/x && zstd -dc phase1-r2.tar.zst | tar -xf - -C /tmp/x
(cd /tmp/x && sha256sum -c "$OLDPWD/phase1-r2.files.sha256")
```
