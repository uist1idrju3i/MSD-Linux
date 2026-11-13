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

2026-11-13の追加調査は`decisions-analytics.tar.gz`へ保存しました。productionのroot・404のHTMLとheader、Cloudflare一次資料、browserのrequest記録、before/afterのサイト写し・描画・text出力と計測scriptを含みます。全memberを原本のbyte列と照合しました。注入scriptも実送信も観測しておらず、描画比較をproduction Analyticsの成功とは扱いません。binary削除時の補助scriptも監査用に含めますが、削除を再実行する指示ではありません。

### 2026-11-13の削除承認と削除前snapshot

`remaining-binaries.csv`は251 pathの容量一覧で、個別hashの表ではありませんでした。従来の`coverage.csv`と`SHA256SUMS`は選択したtextやarchiveを対象とし、binary 251件を直接覆うものではありません。削除前から個別hashが別記されていたscan入力は3件です。

利用者の2026-11-13の承認に従い、`remaining-binaries-sha256.csv`へ251件の削除直前のSHA-256・size・mtimeを記録します。これは現在の状態のsnapshotで、測定時と同一だったことの証明ではありません。remoteへ通常pushして確認した後、一覧のpathだけを削除し、実施結果と`df`の前後値を`binary-deletion-report.json`へ記録します。秘密鍵・一覧外のfile・directoryは削除対象ではありません。

snapshot commit `5375e420a6d0704f651f5f285c8345d658f88b34`を通常pushし、remote SHAとmanifestのSHA-256一致を確認してから、2026-11-13に251 pathだけを削除しました。保持対象は0件です。削除直前にsize・mtime・ctime・inode・deviceを全件照合し、symlink・秘密鍵らしい名前・追跡fileを拒否し、参照可能なprocessのFDに対象がないことを確認しました。

`df -B1`の空きは299,157,540,864から349,300,690,944 bytesへ増え、観測差は50,143,150,080 bytesです。前後の同期処理を含む観測で、他processの書き込みを排除した測定ではありません。見かけの合計1,142,665,527,771 bytesやpath別割り当て合計50,143,170,560 bytesとは分けます。削除した本文はGitから復元できません。上の未遠隔保存一覧は、削除前の監査時点の記録として残しています。

このdirectoryで`sha256sum -c SHA256SUMS`を実行できます。archive内の各fileは`coverage.csv`の`record`にある`#`以降のmember名で取り出し、同じ行のSHA-256と照合します。CSVが別の既存保存物を参照する場合は、その固定commitのfileまたはarchive memberを読みます。圧縮されたlogの参照は展開後のhashです。

archiveへの保存は、licenseの義務の完了、CVEの不存在、実機対応、今後のartifactの永続保管を保証しません。imageの未保存、失われた過去のimage、取得できなかったlogは、今回のtext保存で復元したとは扱いません。
