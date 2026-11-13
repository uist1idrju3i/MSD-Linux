# 2026-11-13 生データの保存監査

[12主題の監査](session-audit-2026-11-13.md) / [検証の索引](README.md)

## 保存先と対象

`git branch -r | grep -i data`には`origin/data/fs-compare-experiments`と開発branchの`origin/devin/1793717866-data-fs-options`が現れました。前者のREADMEは、mainとは別履歴のdata branchへtextをarchiveとして保存し、main側には条件・集計・結論を置く方式を説明しています。今回はこの保存方式を継続し、通常pushで追加しました。mainへのmergeやforce pushはしていません。

監査時の全`output-*` directoryと4件のdriver log、`output/host-tests-version`、以前のfs-compareのrunと診断imageを調べました。新しく作った監査用の`output-research-audit`は、元の実験出力と区別します。build source・host/target tree・cache・生成imageと、再取得できないlog・入力metadata・失敗試行を分けました。

保存先は[data branchのセッションdirectory](https://github.com/uist1idrju3i/MSD-Linux/tree/05d9e71320fd0abfaf9b831e8c1c992bd0a6d28a/session-2026-11-13/evidence)です。archiveを追加した`62551ff`に、未保存のDB・OCI入力のmetadataを追記した`05d9e71320fd0abfaf9b831e8c1c992bd0a6d28a`まで通常pushしました。`coverage.csv`に各fileのbytes・SHA-256・既存保存先または今回のarchive memberを記録し、`inventory.json`に件数を集計しています。`directory-census.json`は各output directory全体の見かけのsizeで、保全対象textのsizeとは別です。

## 照合と追加

既存のmain、PR #240、PR #241の実験fileとgzip/tar内の内容を読んで照合しました。PR枝の固定commitは[監査本文](session-audit-2026-11-13.md)にあります。PR #240/#241の本文・CSV・生ログは、その枝で収録済み・merge待ちとして扱い、研究本文をここへ複製しません。

| 対象 | 今回選択したfile数 | 保存の結果 |
|---|---:|---|
| 開発image scan/snapshot | 52 / 175 | APTの署名付きindex・取得metadata・CVE JSON・旧新build/scan/QEMU log等の未保存分を追加 |
| legal-infoの先行調査 / collector | 14 / 338 | HTTP応答・source metadata・hash参照・元と補足のlegal-info・license本文・失敗を含むcollector log等を追加。SDKの原summary/config/READMEも別途3 file追加 |
| OpenSSL evidence / LTS / main / minimal研究 | 49 / 267 / 208 / 15 | build、target probe、QEMU、SBOM/VEX、実legal-info、入力設定等を追加。上流の展開sourceとbuild/host/target cacheは除外 |
| Pages | 200 | 応答header/HTML、check結果、描画比較等を追加。これをproduction Analytics注入の確認へ読み替えない |
| PQCの4出力とdriver log | 33 | PR #241の保存物と内容が一致。失敗した初回を含み、同じ生ログを再収録しない |
| 本番署名QEMU | 32 | 主要serial等はPR #240に一致。追加の入力metadata・検査log等を保全。大きな配布artifactは含めない |
| seedrng/zram | 107 | bootの反復・crng・pressure・idle・build入力・失敗したidle probe等の生ログを追加。既存CSVだけでraw保存済みとはしなかった |
| write inventory | 108 | 初回失敗とretry、120秒idle、成熟image、build入力等を追加 |
| `in_triage`監視 | 42 | 監視状態・Issue生成の入力・CVE/SBOM/VEX artifact等を追加 |
| vendor COPYING hash調査 / host test出力 | 2 / 9 | hash更新調査・回帰test logを保全 |
| fs-compare | 18,682 | 18,677 fileは既存data branchに一致。未保存の監査・保持script等5 file、38,686 bytesを追加 |

選択対象は計20,333 fileです。今回追加した27 archiveは圧縮後100,354,408 bytesで、同一内容はhashでまとめています。archive作成後に各memberを読み、元fileのSHA-256と照合しました。既存fs-compare archiveも実際に読み、25,417 memberを各manifestと照合しました。678,361,912 bytesのhardlink logは、既存の圧縮logを展開して同じhashを得たため追加不要でした。

## Gitへ入れず残したもの（削除前の監査時点）

測定値・選択対象の生ログの未保存は、今回の追加で解消しました。ただし、**binary imageまで遠隔保存済みという意味ではありません**。`remaining-binaries.csv`に個々のpathとsizeを残しました。集計は次のとおりで、単位はbytesです。

| 対象 | file数 | 見かけのbytes | 割り当てbytes |
|---|---:|---:|---:|
| OpenSSL evidence / LTS / mainのimage等 | 30 | 2,907,001,688 | 377,978,880 |
| PQCのrootfs image | 6 | 124,088,320 | 124,088,320 |
| PQC QEMUの2試行の作業image等 | 4 | 2,415,919,104 | 1,628,168,192 |
| 本番署名QEMU | 13 | 3,706,318,525 | 2,846,859,264 |
| seedrng/zram | 22 | 11,063,380,312 | 5,152,882,688 |
| write inventory | 35 | 8,275,604,590 | 3,824,709,632 |
| fs-compareのrun image等 | 132 | 1,062,467,534,848 | 33,629,392,896 |
| fs-compareの第1段診断image | 6 | 49,425,678,336 | 279,072,768 |
| 開発imageの旧・新OCI tar | 2 | 515,809,792 | 515,821,568 |
| 比較に使ったTrivy DB | 1 | 1,764,192,256 | 1,764,196,352 |

sparse fileの見かけと割り当て量は大きく違います。hard linkを別pathで数える場合もあるため、合計を空き容量や解放量に使いません。生成物は入力hashを記録したものもありますが、再生成でbyte一致するとは未確認です。特に電断・更新後の作業imageの当時の状態は、textから完全復元できるとはしません。

Trivy DBの今回のSHA-256は元の実験記録の`99fdc77556d4c2870c4288db54e6cddc88a7234a3db6e6895d101d441ed86e57`と一致しました。DBと旧新OCI tarのhash・size、DBの更新時刻を`remaining-scan-inputs.json`へ保存しましたが、大きな本文は今回Gitへ入れていません。JSONの走査結果を保全したことと、同じDB本文を遠隔保存したことは別です。

実験用の`msd-update-dev-key.pem`は3 file各119 bytesを意図して除外しました。本番秘密鍵の値は調べていません。取得し直せる上流source、別作業tree、Git object/cache、展開rootfs等も保全対象とは分けました。大きなimageを通常Gitへ入れず、原本・診断image・初回の広い走査で作った補助packも削除していません。

Pagesの`530d91d`の失敗job logはAPIで`Not Found`となり、取得できませんでした。失敗checkと利用者の`Build failed.`報告は[監査本文](session-audit-2026-11-13.md)へ残しています。失われた過去のfs-compare imageに関する既存data READMEの制限も、今回の照合で解消したとは扱いません。

## 削除前snapshotと承認後の限定削除

以前の記録と報告は、251件全体をhash記録済みと読める点が不正確でした。`remaining-binaries.csv`はpathと容量だけで、`coverage.csv`の直接対応は0件、`remaining-scan-inputs.json`の個別hashは3件でした。textやarchiveのhashを、収録していないbinary本文のhashへ読み替えません。

利用者の2026-11-13の承認を受け、全251件の現在のSHA-256・size・mtimeを[data枝の削除前CSV](https://github.com/uist1idrju3i/MSD-Linux/blob/5375e420a6d0704f651f5f285c8345d658f88b34/session-2026-11-13/evidence/remaining-binaries-sha256.csv)へ記録しました。**これは削除前のsnapshotで、過去の測定時との同一性を証明しません。** 同commitの通常push後、remote SHA一致と取得したmanifestのSHA-256 `cc4c444a20e6d29aaebc48b17fda232d4d6cf7c9aded5bbec527000212d93573`を確認してから、一覧の251 pathだけを削除しました。保持は0件です。

[削除結果JSON](https://github.com/uist1idrju3i/MSD-Linux/blob/8802310d8572b6062ea7a95de0c636dbd1aa75ac/session-2026-11-13/evidence/binary-deletion-report.json)と[data README](https://github.com/uist1idrju3i/MSD-Linux/blob/8802310d8572b6062ea7a95de0c636dbd1aa75ac/session-2026-11-13/evidence/README.md)も通常pushし、remote SHAを照合しました。削除前に全pathのsize・mtime・ctime・device・inodeを照合し、symlinkと追跡file、秘密鍵らしい名前を拒否しました。参照できたprocessのFDには対象がありませんでしたが、200 processのFD directoryは権限不足で読めず、全processで未使用だったという保証はしません。

同一filesystemの`df -B1`は次のとおりです。同期処理を前後に行いましたが、他processの書き込みを止めた測定ではありません。

| 時点 | 使用bytes | 空きbytes |
|---|---:|---:|
| 削除前 | 174,867,914,752 | 299,157,540,864 |
| 削除後 | 124,724,764,672 | 349,300,690,944 |
| 空きの観測増加 | — | 50,143,150,080 |

見かけの合計1,142,665,527,771 bytes、path別割り当て合計50,143,170,560 bytesとは分けます。上の容量表と「削除していない」は元監査時点の記録です。現在は承認対象の本文を削除済みで、hashから復元はできません。秘密鍵、一覧外のfileやdirectory、保存済みの生ログは削除していません。
