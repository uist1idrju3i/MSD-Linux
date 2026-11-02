# GitHub Actions の実行境界と監視の監査

## 対象と判定方法

2026-11-02 UTC、`641a6f5` を起点に、`.github/workflows/` の9本と関連するスクリプトを確認した。表の「実行」は定義から読める条件であり、GitHub の組織設定や全ブランチの実行履歴を検証した意味ではない。変更後のローカル試験は後述する。実機、公開済みのOCI、GitHub上のワークフロー実行結果をこの監査の試験と混同しない。

| ワークフロー | 実行と権限 | 境界と残る確認事項 |
|---|---|---|
| `agent-docs.yml` | PR、main push。contents: read | 文書・サイト・スキル検査。外部サービスへの書き込みなし |
| `build.yml` | PR、main push、週次、手動。changes は read。テストと build は contents/actions/packages/attestations: read | PRの変更を実行。文書だけの変更では build を省略し、msd-update tests は実行する。必要な変更の検出に失敗したときは build。build は150分、PRの新しい実行で旧実行を中止。カーネル強化検査は continue-on-error。legal-infoの既知の警告はCI成功でも解消しない |
| `lint.yml` | PR、main push。lint/zizmor は contents/packages/attestations: read。Dockerfile検査は contents: read | PR由来のコードを固定開発OCIで実行。SHA固定のcheckoutで資格情報を残さない。zizmorはoffline。3ジョブ、各15分 |
| `pages.yml` | サイト関連のPRとmain push、手動。build は contents/pages: read、deploy は pages/id-token: write | PRではbuildのみ、mainで公開。ドメイン照合はPages APIに依存し、forkのPRで読めるかは未確認。buildとdeployの権限は分離 |
| `publish-dev-image.yml` | OCI入力変更のPRとmain push、手動。plan は contents: read。build/publish は contents: read、packages/attestations/id-token: write | PRでも2アーキテクチャを最大45分ずつ構築・検査するがpushはしない。書込権限はPRのbuildにも与えられ、最小権限の余地がある。手動実行は`dry_run=false`ならmain以外からでもlatestタグへ公開しうる。公開先をmain限定にするかは信頼境界の設計判断。イメージの固定digestとSBOM/provenanceはアーキテクチャdigestとindex digestを分ける |
| `dev-image-scan.yml` | mainのOCI入力変更、週次、手動。contents: read、issues: write | 公開されたlatestのamd64だけを検査。変更前は取得失敗の一部を成功扱いにしたため、失敗を検査失敗に変更。検出事項はIssue通知だがジョブ失敗にはしない。raw Trivy JSONは公開しない |
| `security.yml` | 週次、手動。contents: read | BuildrootのSBOMとVEXを成果物に保存する。CVEがあってもゲート・Issue通知はなく、実行ログとartifactの確認が必要。NVDは週番号別cache、週内復元の鮮度は別途確認が必要 |
| `pins-check.yml` | 週次、手動。contents: read、issues: write | GitHubの固定値と公開元を照合しIssueを更新。Release APIに載らないKHCのtagを取得するよう変更。更新不能は確認不能として通知対象に残す |
| `site-status.yml` | 週次、手動。contents/pages: read、issues: write | Pages・DNS・TLS・HTTPの異常をIssueに通知する。正常時には閉じる |

## 横断的な差分と背反

- 外部Actionはcheckout、cache、Pages、artifact、attestのcommit SHA固定で、通常のcheckoutは`persist-credentials: false`。`publish-dev-image.yml`のbuildをPR用の読取専用ジョブと公開用の書込ジョブに分離すれば、PR実行時の権限を下げられる。ただし2アーキテクチャのイメージ転送または重複ビルドが必要になり、artifact容量・時間の費用が増える。現在の境界で安全性が証明されたわけではない。
- 公開フローの未加工Trivy JSONには検出された秘密値やコードが含まれうる。変更後は既存の選別器で全件の分類情報を残し、生の検出内容をartifactから除いた。SPDX SBOMは別の生成物であり、内容を機密情報がないと個別検査したわけではない。
- 週次のBuildroot CVE報告は67要素のSBOMを基礎とするが、開発用OCIのTrivyとは対象が異なる。Buildrootのhost依存、外部ツールチェーンの内包物、最終OCI以外のbuild stage、Actionの実配布bundle、runner image、固定OCI digestは、個々の最新値と監視範囲を[依存監査のPR #184](https://github.com/uist1idrju3i/MSD-Linux/pull/184)に分けて記録した。全て自動監視できているという判定にはしない。
- `gh issue list --limit 100`で同題Issueを探す3本の監視は、open Issueが100件を超えた場合の重複作成と、重複実行の競合を排除していない。Issue照合のページングと監視workflowの同時実行制限は次の改善候補。APIの権限・rule set・必要なCheckの設定はworkflow YAMLからは確定できない。
- cacheはBuildrootのダウンロードとNVD、artifactはSBOM・イメージ・ログ・報告に限定して用途が異なる。PRから復元できるcacheは未信頼入力として扱う。署名鍵、GitHub Releaseの公開権限と証明書、image更新鍵の設定は別途監査が必要。

## 変更の検証範囲と次の順番

修正後の`tests/check-pins/run.sh`では、タグだけを公開する上流、複数ページ・メジャー、未完成のページ、draft、pre-release、壊れた応答の検査が通った。`tests/trivy-gate/run.sh`では、週次image取得の3種類の失敗と成功、公開フローのartifact選択、および秘密値を含む模擬入力からの安全な出力を検査した。開発用OCI内でactionlint、ShellCheck、zizmor offlineとPython構文検査を実行した。公開されたCIの実行結果は別途確認する。

次に、公開権限をmainへ限定する運用判断と、PR用OCIジョブの権限分離に必要な転送費用を比較する。続いてBuildroot CVEをIssueへ通知する条件、残る依存の監視漏れ、Pagesのfork動作を確認する。監視に失敗したことと脆弱性が0件であることを同じ状態にしない。

## CI生成物による追加確認

[PR #185のamd64実行](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41497577953/job/125456551427)は`d5f4f5d`の段階で成功したが、[保存したartifact](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41497577953/artifacts/13167557308)には2,184件の脆弱性と1件の公開ゲート対象があった。対象は`libbrotli1 1.1.0-2+b7`の`CVE-2026-111497`。Trivyは0.76.1、DBの更新日時は2026-11-02 13:15:56 UTC、image IDは`sha256:f5b68684722c8e1eb157693695e69e9aba1053e932179e6590f7e4fff6bb4d63`だった。

未指定のrun shellは`bash -e`で、ゲートの非ゼロ終了をパイプ末尾の`tee`が隠していた。この成功をゲート合格とは扱わない。公開ゲートと週次報告に`set -o pipefail`を追加し、実際のステップを`bash -e`で実行する回帰試験を加えた。ゲート対象ありでは失敗、対象なしでは成功、週次報告のJSONが壊れていたら失敗することを検査する。`build.yml`のensureステップは既に`shell: bash`を明示しており、この問題とは異なる。

artifact内は選別済みJSON、報告、image情報、Trivy版、SPDXの5ファイルだけで、未加工のTrivy JSONはなかった。Brotliの更新は利用者の指定で延期しており、この修正で公開ゲートが失敗することは未対応の検出を正しく示す。除外やゲート緩和は行わない。
