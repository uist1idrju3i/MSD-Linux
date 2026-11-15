# 二セッション監査の追加保全

対象は03914・5917セッションの監査資料と、既存archiveに同一hashがなかったtext候補87件です。過去の測定結果自体は変更していません。

- `evidence.tar.gz`: `candidates/` に87件、`drivers/` にFEC確認器とbuild・実行log、`audit/` に抽出command・失敗command・file編集metadata・PR記録・CI log・監査本文、`attachments/` に復元添付を収録しました。
- `manifest.json`: 保存後のbyte数とSHA-256、保存前のSHA-256、秘匿処理した行数。元fileのhashは取得時点のもので、過去の測定時との同一性を保証しません。
- `evidence.files.sha256`: 展開後のmember hash。
- `SHA256SUMS`: このdirectory内の保存fileのhash。

認証情報が混入する可能性のあるraw events-details/decoded dumpは収録していません。指定された秘密情報patternを含む行は、値だけでなく行全体を秘匿しました。patternを検索するcommand自体も秘匿対象です。原本は変更していません。

添付の原文が取得できなかった版は、復元限界と確認可能な会話抜粋を収録しています。`attachments/manifest.csv` が原文hash一致と復元不能を区別します。秘匿処理したcopyは原文とbyte一致しないため、このarchiveのhashを優先します。

監査本文とcommand/log内の当時のpathは履歴資料の原文です。現物の保存先を保証するものではありません。画像本体・秘密鍵・実行binary・数GBのbuild treeは含めません。旧実験の全履歴保全や実機確認が完了したという意味ではありません。

検査は `sha256sum -c SHA256SUMS`、archive展開後に `sha256sum -c evidence.files.sha256` で行えます。
