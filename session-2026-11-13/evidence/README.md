# 2026-11-13 セッションの証拠保全

このdirectoryは同じリポジトリの`data/fs-compare-experiments` branchに置きます。mainへmergeするための変更ではありません。監査本文は`devin/1794550080-research-audit`の`docs/research/verification/session-audit-2026-11-13.md`と`session-evidence-2026-11-13.md`です。

## 収録物

| file | 内容 |
|---|---|
| `coverage.csv` | 選択した20,333 fileの元の相対path、bytes、SHA-256、保存状態、保存先。`existing`は既存のmain・PR #240/#241・data branchに同じ内容があるもの。`preserved-now`は今回のarchiveへの対応 |
| `inventory.json` | 対象別の件数・bytes、27 archiveのhashとsize。圧縮archiveの合計は100,354,408 bytes |
| `SHA256SUMS` | archive全体のSHA-256 |
| `*.tar.gz` | 従来の保存先と一致しなかった生ログ、metadata、失敗試行、入力設定、SDK summary等。元のfile内容を変えず、展開後のSHA-256を再照合した |
| `directory-census.json` | 監査開始時のoutput directoryの見かけのsize。fs-compareは関連作業tree等も含むため、必要な証拠だけのsizeではない |
| `remaining-binaries.csv` | Gitへ入れていないimage等のpath、見かけのbytes、割り当てbytes。fileごとの行を残す。SD image・電断状態を復元できるという意味ではない |
| `remaining-binaries.json` | 上記を対象別に集計。hard linkを別pathで数えるため合計は解放可能量ではない |

`repo/`は監査対象repo内の相対pathです。`fs-compare-local/`は以前のfs-compare作業領域を識別するための接頭辞で、個人環境の絶対pathを参照先にはしません。展開先の候補が重複する場合は、`coverage.csv`のSHA-256で内容を同定します。

## 照合した範囲

基準mainは`121e9ae1878252a675efb6714bc36e91f488e331`。PR #240は`c27b9a9b5dae5c32e9029250835c6990d8739a9a`、PR #241は`0c77ff9a92be9a2b2bdba7a0df26fb27be9234cf`です。CSVの`origin/...`はこの採取時点のrefであり、将来のbranch headを意味しません。

既存fs-compareのtar.zstを展開して25,417 memberのSHA-256を各`.files.sha256`と照合しました。現在の選択対象のfs-compare textは18,682 fileで、18,677 fileが既存保存物と一致し、残る5 file（監査・保持候補のscript等、38,686 bytes）を追加しました。678,361,912 bytesのhardlink logは、既存`fs-compare/misc/dedup-build-hardlink-20261111.log.zst`の展開内容と一致し、再収録しません。

OpenSSLのupstream展開source、別作業treeのGit object/cache、生成したbinaryは生ログと区別して除外しました。license原文・manifest・HTTPの取得応答・CVEのscan JSON・SBOM/VEX・build/QEMU/失敗のlog・Pagesの描画証拠等は選択対象です。原本を削除せず、生成済み補助packも未追跡のまま残しています。

本番鍵を収集していません。実験用の`msd-update-dev-key.pem`も、3 file各119 bytesをGitへ入れません。上流source内の試験鍵も今回のsource展開の収録対象外です。86 MBの本番release artifactやSD imageは含みません。

## 再確認

このdirectoryで`sha256sum -c SHA256SUMS`を実行できます。archive内の各fileは`coverage.csv`の`record`にある`#`以降のmember名で取り出し、同じ行のSHA-256と照合します。CSVが別の既存保存物を参照する場合は、その固定commitのfileまたはarchive memberを読みます。圧縮されたlogの参照は展開後のhashです。

archiveへの保存は、licenseの義務の完了、CVEの不存在、実機対応、今後のartifactの永続保管を保証しません。imageの未保存、失われた過去のimage、取得できなかったlogは、今回のtext保存で復元したとは扱いません。
