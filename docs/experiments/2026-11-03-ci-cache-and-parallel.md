# CIの起動条件・開発OCIキャッシュ・host回帰並列化の検証

[実験の一覧](README.md) / [CIの調査](../research/ci-build-scope-and-performance.md)

## 目的と事前の判定条件

文書変更だけで製品buildを起動せず、製品入力・未知のpath・差分の判定失敗ではbuildすることを確認します。PRの累積差分と改名・削除、週次・手動の入口も対象です。開発OCIは公開済みなら毎回pullとattestation検証を行い、未公開の場合に限り完全一致のcacheを使用します。独立したhost回帰7組は、同じ固定OCI内で最大2組ずつ並列実行します。

正式反復は`tests/check-ci-cache/run.py`の15 methodと`tests/check-ci-scope/run.py`の7 methodを各5回実行し、全回終了値0、入力hashの一致を採用条件とします。改変archive、metadata、別platform、公開imageのpull/認証/attestation失敗、cache部分一致、容量超過、build/load/save失敗、差分取得失敗、並列runnerのtimeout・遅い失敗を負の対照にします。期待する拒否も含めた回帰の成功であり、製品の安全性全体を認定しません。

基準commitは`7a0d52b2f20889ac23dd6a8fa585a44c3a373866`です。開発OCIは`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、Linux/amd64を用います。Pythonは実binaryで3.13.5です。正式記録には使用したscriptとworkflowのhash、tool版、全行の終了状態、ログのhashを残します。Buildroot/GCC/kernel/QEMUの新しいbuildや起動はこのローカル回帰に含めません。

既存の7組も実際の並列runnerで確認します。実Dockerのarchive save/loadは1回の機能確認とし、GitHub cacheの転送やcold/warmの性能実験に転用しません。長期hit率・総費用・速度の改善率は未測定です。生ログは上書きしない出力先へ保持します。

## 予備実行で分かった問題

最初のactionlintはcache世代出力の個別redirectをSC2129として検出したため、出力を一つのblockへまとめました。zizmorはworkspace相対actionを指摘したため、[GitHub公式のself-repository構文](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsuses)に変更しました。ただし固定版actionlint 1.7.12はこの構文に未対応です。該当する一つのaction pathの構文誤認だけを理由付き例外とし、pin・path・他actionには効かないことを回帰で検査します。例外を外すには対応版への更新と再検査が必要です。

scope回帰の初回は、コンテナーにGitのauthor設定がないため仮の履歴作成に失敗しました。fixture専用のauthor/committer環境変数を使う方式へ直し、実リポジトリの設定は変更していません。同じ予備試行で出たCSV streamの閉じ忘れも修正しました。正式反復と予備失敗を分けて記録します。

## 正式実行と未確認

正式反復・実Docker・既存host回帰の結果、CSV、metadata、再実行手順は検証後に追記します。現時点では検査途中です。GitHub runner上の実cache hit・転送時間、mainへの反映、新しい製品Buildroot/QEMUの結果は、ローカル回帰と区別して確認します。Brotliの更新延期、公開検査、署名検証は変更しません。
