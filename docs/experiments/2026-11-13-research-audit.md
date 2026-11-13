# 2026-11-13 調査と生データの収録監査

[実験の索引](README.md) / [12主題の監査](../research/verification/session-audit-2026-11-13.md) / [保存先・未保存物](../research/verification/session-evidence-2026-11-13.md)

## 目的と条件

利用者が指定した12主題と、セッションの証拠出力を棚卸しします。依頼の手順A/B/Cを監査計画とし、研究本文の所在を確認してから、生ログ・metadataを既存の保存物と照合し、未保存分をdata branchへ保全します。内容のSHA-256が一致し、各fileの保存先を追跡できることを保存の判定条件にします。速度・製品性能の改善は判定しません。

基準mainは`121e9ae1878252a675efb6714bc36e91f488e331`。PR #240は`c27b9a9b5dae5c32e9029250835c6990d8739a9a`、PR #241は`0c77ff9a92be9a2b2bdba7a0df26fb27be9234cf`です。以前のdata branchは`5f75452`から読みました。hostの既存の作業treeと出力を対象にした1回の在庫・整合性監査で、cold build・warm buildの比較やQEMUの再実験ではありません。hashの整合性を調べるため、性能測定の5回反復は行いません。

## 手順と対照

1. `git branch -r | grep -i data`、固定refの`git ls-tree -r`と`git show`で本文・保存先を読みます。
2. docsのgzip/tar、data branchのtar.zstを読み、展開内容をSHA-256で照合します。既存のmanifestだけを読んで保存済みとはしません。
3. output directoryのtext・metadata・失敗trial・描画証拠等を選び、元のpath・bytes・hashと照合先をCSVへ残します。再生成用のbuild tree、上流source、cache、秘密鍵、image等は分けます。
4. 未保存の内容をgzip tarへまとめ、作成後に各memberを読み直して元のhashと照合します。既知のPQC archive一致と、未保存のseedrng/zram raw logの検出を、既存と未保存を区別できることの対照にしました。
5. 大きなimageは原本を残し、pathと見かけ・割り当てbytesを一覧にします。従来のraw logも削除しません。

初回の広い走査では関連する別作業treeやGit/cacheまで含んだため、upload対象にせず、run・診断領域と実験出力に絞った保全を別のdirectoryへ作りました。初回のpackも削除せず未追跡で保持しています。Pagesの過去の失敗job log取得は`Not Found`となり、原因は未確認です。失敗を成功へ置き換えません。

## 結果と制限

数値は[CSV](2026-11-13-research-audit.csv)、fileごとの対応はdata branchの`05d9e71320fd0abfaf9b831e8c1c992bd0a6d28a`の`session-2026-11-13/evidence/coverage.csv`にあります。選択した20,333 fileを追跡でき、今回27 archiveを追加しました。既存fs-compareの25,417 memberと、新規archive memberの内容を照合しました。

Buildrootの割り当て量と見かけの量は`du -s -B1`と`du -sb`による各1回の値です。shallow状態は`git -C vendor/buildroot rev-parse --is-shallow-repository`で確認しました。clean checkout・clone転送量の測定ではありません。

今回の保全は、実験で観測した値の正しさ、実機、物理SDの耐久性、license義務の完了、CVEの不存在、公開配信の成功を新たに確認するものではありません。大きなimageと実験用秘密鍵はGitへ入れていません。個々の未保存imageとsizeは保存監査の一覧を参照してください。
