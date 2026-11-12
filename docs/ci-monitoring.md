# 監視Issueの更新と失敗

[CIの一覧](CI.md)へ戻る。

2026-11-12に、Issueへ通知する3系統を見直しました。対象は「製品SBOMの脆弱性監視」「固定版の更新確認」「開発用イメージの脆弱性」です。[共通script](../.github/scripts/tracking-issue.py)はopen Issueを100件ずつページ送りし、PRを除いて題名の完全一致で既存Issueを探します。作成直前にも再検索します。定期・手動実行は監視ごとの固定concurrency groupで直列化し、実行中のjobは自動中止しません。製品CVEのPR用groupはrefごとに分け、Issueを更新しません。別のscriptや人間による同時作成までAPI側で排他する仕組みではありません。

scan、feed・artifactの取得、SBOM/VEX・Trivy入力の検証、reportの準備に失敗した場合は、成功した検出なしと区別します。失敗時の通知は`always()`で実行し、job summaryに「監視に失敗」「未確認」を表示して非ゼロ終了します。既存Issueの本文は保持し、本文が最後に確認できた結果であることと失敗通知・run URLをコメントします。Issueがない場合だけ失敗本文で作成します。検出件数や解消を報告せず、Issueを閉じません。通信・権限の問題でIssue自体を更新できない場合もsummaryとjobの失敗に残します。runnerやcheckout自体が動かない場合の通知を保証するものではありません。

固定版の「確認できず」はreportを保存したうえで終了値2となり、正常な「全て最新」から分けます。Trivyの対象なし・不正な結果を検出なしとは扱いません。製品CVEでは、空のSBOM/VEX、未知のcomponent参照、欠落・未知のanalysis stateを拒否し、stateの検証後にだけ件数をsummaryへ載せます。前回成功stateの取得失敗も初回の基準作成と区別します。成功履歴がない場合のみ初回基準を作ります。CPEなしの依存を含む全件照合や安全性を証明する変更ではありません。

Buildrootの`IGNORE_CVES`に由来する`in_triage`は有効な状態です。影響あり・解消・scan失敗とは分け、stateの`in_triage`とIssue・step summaryの「未評価（Buildrootの無視指定）」欄へCVE、component、組み合わせの件数を残します。PR #230以前はこの状態を`findings`にも解消件数にも記録していませんでした。schema 2と`findings`の意味、PR gateの対象は維持し、新しい欄だけを追加します。旧stateに欄がない場合は空として読み、初回差分での追加は新しい脆弱性の発生を示しません。影響ありと未評価の移動は「状態変更」で通知し、未評価の一覧から除外されたことだけで解消とは断定しません。

回帰は`python3 tests/check-cve-monitor/run.py`、`tests/check-pins/run.sh`、`tests/trivy-gate/run.sh`で確認します。Issue検索・作成はmockを使い、live Issueへの試験投稿や同時workflowの実行はしていません。
