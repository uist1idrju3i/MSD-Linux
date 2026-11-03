# GitHub Actions の実行境界と監視の監査

文書変更で製品buildが起動する理由、PR全体差分、cache・並列化の実行ログと改善候補は[追加調査](ci-build-scope-and-performance.md)にあります。以下の監査時点と区別します。

## 対象と判定方法

2026-11-02 UTC、`641a6f5` を起点に、`.github/workflows/` の9本と関連するスクリプトを確認した。表の「実行」は定義から読める条件であり、GitHub の組織設定や全ブランチの実行履歴を検証した意味ではない。変更後のローカル試験は後述する。実機、公開済みのOCI、GitHub上のワークフロー実行結果をこの監査の試験と混同しない。

| ワークフロー | 実行と権限 | 境界と残る確認事項 |
|---|---|---|
| `agent-docs.yml` | PR、main push。contents: read | 文書・サイト・スキル検査。外部サービスへの書き込みなし |
| `build.yml` | PR、main push、週次、手動。changes は read。テストと build は contents/actions/packages/attestations: read | PRの変更を実行。文書だけの変更では build を省略し、msd-update tests は実行する。必要な変更の検出に失敗したときは build。build は150分、PRの新しい実行で旧実行を中止。カーネル強化検査は continue-on-error。legal-infoの既知の警告はCI成功でも解消しない |
| `lint.yml` | PR、main push。lint/zizmor は contents/packages/attestations: read。Dockerfile検査は contents: read | PR由来のコードを固定開発OCIで実行。SHA固定のcheckoutで資格情報を残さない。zizmorはoffline。3ジョブ、各15分 |
| `pages.yml` | サイト関連のPRとmain push、手動。build は contents/pages: read、deploy は pages/id-token: write | PRではbuildのみ、mainで公開。ドメイン照合はPages APIに依存し、forkのPRで読めるかは未確認。buildとdeployの権限は分離 |
| `publish-dev-image.yml` | PR（常時）、OCI入力変更のmain push、手動。plan は contents: read。build/publish は contents: read、packages/attestations/id-token: write | PRでは差分が7種のOCI入力に触れる場合だけ2アーキテクチャを最大45分ずつ構築・検査し、常時起動する`dev-image gate`がbuildの結果を集約する。buildの書込権限はPRにも与えられ、最小権限の余地がある。手動実行は`dry_run=false`ならmain以外からでもlatestタグへ公開しうる。公開先をmain限定にするかは信頼境界の設計判断。イメージの固定digestとSBOM/provenanceはアーキテクチャdigestとindex digestを分ける |
| `dev-image-scan.yml` | mainのOCI入力変更、週次、手動。contents: read、issues: write | 公開されたlatestのamd64だけを検査。変更前は取得失敗の一部を成功扱いにしたため、失敗を検査失敗に変更。検出事項はIssue通知だがジョブ失敗にはしない。raw Trivy JSONは公開しない |
| `security.yml` | すべてのPR、2時間ごと、手動。scanはcontents/packages/actions/attestations: read、reportはissues: write等 | 開発用OCI内でBuildroot SBOM/VEXを作り、成功state・SBOM・VEX・show-infoを30日保存する。PRでは同じNVD feed cloneからbaseとheadのstateを作り、新規の修正可能CRITICALがあれば失敗させる。CVSS v3.x/v4.0の9.0以上を対象とし、CVSSv2のみと修正可否不明は失敗させない。新規CRITICALのNVD entry欠損は完全性エラーとして失敗する。mainの定期・手動実行では「製品SBOMの脆弱性監視」Issue本文を更新し、前回成功artifactとの差分だけをコメントする。空入力、24時間超のfeed、例外TSV不正・期限切れ、head/定期stateでの未使用例外は失敗させる一方、base stateではheadで追加された未使用例外を記録して比較を続ける。毎回depth-1 cloneし、2時間ごとのcacheは作らない |
| `pins-check.yml` | 週次、手動。contents: read、issues: write | GitHubの固定値と公開元を照合しIssueを更新。Release APIに載らないKHCのtagを取得するよう変更。更新不能は確認不能として通知対象に残す |
| `site-status.yml` | 週次、手動。contents/pages: read、issues: write | Pages・DNS・TLS・HTTPの異常をIssueに通知する。正常時には閉じる |

2026-11-03の現行設定では、PRの`dev-image gate`が入力差分の有無にかかわらず結果を報告し、対象差分がある場合に限って両archのbuildとTrivy検査を必須にする。`main`のrulesetにこのstatus checkを加える作業はmerge後にmaintainerが行う。rulesetの状態はworkflow YAMLから確認できない。追加前は必須checkではなく、mergeを止めない。paths filter付きworkflowは対象外PRでcheckを報告しないため、直接必須にはできない。

## 横断的な差分と背反

- 外部Actionはcheckout、cache、Pages、artifact、attestのcommit SHA固定で、通常のcheckoutは`persist-credentials: false`。`publish-dev-image.yml`のbuildをPR用の読取専用ジョブと公開用の書込ジョブに分離すれば、PR実行時の権限を下げられる。ただし2アーキテクチャのイメージ転送または重複ビルドが必要になり、artifact容量・時間の費用が増える。現在の境界で安全性が証明されたわけではない。
- 公開フローの未加工Trivy JSONには検出された秘密値やコードが含まれうる。変更後は既存の選別器で全件の分類情報を残し、生の検出内容をartifactから除いた。SPDX SBOMは別の生成物であり、内容を機密情報がないと個別検査したわけではない。
- 2時間ごとのBuildroot CVE報告は67要素のSBOMを基礎とするが、開発用OCIのTrivyとは対象が異なる。Buildrootのhost依存、外部ツールチェーンの内包物、最終OCI以外のbuild stage、Actionの実配布bundle、runner image、固定OCI digestは、個々の最新値と監視範囲を[依存監査のPR #184](https://github.com/uist1idrju3i/MSD-Linux/pull/184)に分けて記録した。全て自動監視できているという判定にはしない。
- `gh issue list --limit 100`で同題Issueを探す複数の監視は、open Issueが100件を超えた場合の重複作成と、重複実行の競合を排除していない。Issue照合のページングと監視workflowの同時実行制限は次の改善候補。APIの権限・rule set・必要なCheckの設定はworkflow YAMLからは確定できない。
- cacheはBuildrootのダウンロードに用い、NVD feedは毎回浅くcloneする。artifactはSBOM・イメージ・ログ・報告に限定して用途が異なる。PRから復元できるcacheは未信頼入力として扱う。署名鍵、GitHub Releaseの公開権限と証明書、image更新鍵の設定は別途監査が必要。

## 変更の検証範囲と次の順番

修正後の`tests/check-pins/run.sh`では、タグだけを公開する上流、複数ページ・メジャー、未完成のページ、draft、pre-release、壊れた応答の検査が通った。`tests/trivy-gate/run.sh`では、週次image取得の3種類の失敗と成功、公開フローのartifact選択、および秘密値を含む模擬入力からの安全な出力を検査した。開発用OCI内でactionlint、ShellCheck、zizmor offlineとPython構文検査を実行した。公開されたCIの実行結果は別途確認する。

製品SBOMの2時間ごとのIssue監視とPR-sideの新規修正可能CRITICAL gateは実装済みだが、このフォローアップのCI・mergeは未確認で、mainではまだ有効になっていない。merge後にmaintainerが`product CVE scan`をrulesetへ追加する。次に公開権限をmainへ限定する運用判断、PR用OCIジョブの権限分離、残る依存の監視漏れ、Pagesのfork動作を確認する。監視に失敗したことと脆弱性が0件であることを同じ状態にしない。

## CI生成物による追加確認

[PR #185のamd64実行](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41497577953/job/125456551427)は`d5f4f5d`の段階で成功したが、[保存したartifact](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41497577953/artifacts/13167557308)には2,184件の脆弱性と1件の公開ゲート対象があった。対象は`libbrotli1 1.1.0-2+b7`の`CVE-2026-111497`。Trivyは0.76.1、DBの更新日時は2026-11-02 13:15:56 UTC、image IDは`sha256:f5b68684722c8e1eb157693695e69e9aba1053e932179e6590f7e4fff6bb4d63`だった。

未指定のrun shellは`bash -e`で、ゲートの非ゼロ終了をパイプ末尾の`tee`が隠していた。この成功をゲート合格とは扱わない。公開ゲートと週次報告に`set -o pipefail`を追加し、実際のステップを`bash -e`で実行する回帰試験を加えた。ゲート対象ありでは失敗、対象なしでは成功、週次報告のJSONが壊れていたら失敗することを検査する。`build.yml`のensureステップは既に`shell: bash`を明示しており、この問題とは異なる。

artifact内は選別済みJSON、報告、image情報、Trivy版、SPDXの5ファイルだけで、未加工のTrivy JSONはなかった。Brotliの更新は利用者の指定で延期しており、この修正で公開ゲートが失敗することは未対応の検出を正しく示す。除外やゲート緩和は行わない。

2026-11-03のR25ローカル検証ではsnapshotを`20261103T023120Z`へ進め、amd64を再構築してTrivy 0.76.1 gateの対象0件を確認した。その後、PR #194とmerge後のmain CIでamd64/arm64のgate、各archのSBOM attestation、multi-arch indexのBuild Provenance、Buildroot build、`scan`が成功した。`dev-image gate`はPR #195でmainに入ったが、rulesetの必須checkへの追加は上記のとおりmaintainerの作業として残る。job IDと初回のBrotliだけの試行を含む結果は[実験記録](../experiments/2026-11-03-dev-image-security-update.md)を参照する。
