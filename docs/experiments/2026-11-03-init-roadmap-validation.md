# init調査・実測計画・残件台帳の静的照合

[実験一覧](README.md) / [init実測の計画](2026-11-03-init-comparison-plan.md) / [残件と将来計画](../research/roadmap.md)

## 目的・条件・採否

systemdの代替調査・未実施の実測計画・残件を、ID・参照・依存と原問いへ対応づけます。**これは製品OSのbuild、代替initの起動・性能測定・実機試験ではありません。** 元の問いを別名で漏らしたり、計画を動作の証拠へ読み替えたりしないことを目的にします。

基準commitは`1670bdd3994bfbf0ae33568700aea6a628aa5f31`、Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`です。変更対象は調査文書・CSV・出典metadata・静的検査器だけです。製品defconfig、kernel、toolchain、vendor、update形式、鍵、login、workflowは変えません。

固定OCIはamd64の`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、RepoDigestは`ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、実行したPythonは3.13.5です。VM側Python 3.12.13で取得済みrawとの照合も行いました。compilerやQEMUは今回使用しておらず、その版を計測済みとは書きません。Buildrootの`O=`、ccache、warm/cold buildは対象外です。

判定基準は、参照するfileとIDが存在し、状態が定義内、依存が循環せず、全work item・31主題・原Q/R・S実験の対応が過不足なく、5回の出力が一致し、故障した入力を全て拒否することです。外部資料の取得失敗は隠さず、取得済みrawのbytes/hashは台帳と一致を要求します。この静的検査が通っても、機能の同等性・licenseの適法性・全チャットの精読は証明しません。

## 実行と結果

[検査器](2026-11-03-init-roadmap-audit.py)を固定OCIで実行しました。

```sh
docker/msd-dev python3 docs/experiments/2026-11-03-init-roadmap-audit.py --self-test
```

[raw CSV](2026-11-03-init-roadmap-validation.csv)は5回の全結果です。各回44残件、79の対応行、31主題、79原Q/R、17実験、69の取得記録を検査しました。終了状態は5回とも`passed`、全出力のSHA-256は`9035616545e9836d1f50fe024b4712178fc1b3d5884fe053444719ff5289e15a`で一致しました。raw CSVの`scope=static-only`を除いて値を引用しません。

各回、以下の8負対照を拒否しました。正しい入力へ対照の破損を残していません。

1. 自分自身へ依存するcycle。
2. 存在しない残件への依存。
3. 存在しない根拠file。
4. 定義外の状態`passed`を残件へ指定。
5. 主題の対応行を一つ削除。
6. 原Q/RのIDを変更。
7. 成功した出典のhashを削除。
8. 出典IDを重複。

取得済みrawの保存内容も、`--verify-sources`で各URLのbytes/hashへ照合しました。外部URLを5回再取得したという意味ではありません。原文の内容確認と取得の成功も別です。HTTP 404/403、Savannah取得失敗、Shepherd manualのsoft-200を出典台帳から消していません。最初の索引追加ではpatchの最終hunkが一致せず、一部だけ適用されました。適用済み差分を確認し、未適用の索引だけを追加しました。製品の失敗試行ではありません。

## 再検査・再取得

repo rootから上のコマンドを実行します。`--output`には未使用のCSV名を渡せます。既存fileへの上書きは拒否します。URLを再取得する場合は、存在する親directoryの下に未使用の出力directoryを指定します。

```sh
python3 docs/experiments/2026-11-03-init-roadmap-audit.py --fetch-sources new-init-sources
python3 docs/experiments/2026-11-03-init-roadmap-audit.py --verify-sources new-init-sources
```

再取得は認証情報を渡さず、HTTP状態・final URL・body hash・取得時刻を新しいmetadataへ保存します。GitHub API等が403になっても旧metadataを上書きしません。可変な公式siteやbranchが変わった場合、旧台帳とのhash照合は失敗します。これは最新内容が誤りという意味ではなく、別の取得記録として内容を再確認します。保守情報は固定repository名に対する`gh api repos/OWNER/REPO`、`commits/BRANCH`、`releases/latest`の読み取り結果を必要なfieldだけ保存したもので、未取得のlatest-releaseを最新版確認済みにはしません。

## 残る確認

新旧本文を読み比べ、条件・未確認の意味を照合しました。リンク・JIS X 0213・文書サイズと各検査器の回帰試験、日本語推敲、Python構文、既存更新処理・data拡張のhost試験、build workflowのactionlint、差分の空白検査は通りました。推敲の警告は一覧・文字どおりの台帳・必要な否定・文末の繰り返しを個別に確認し、一括除外は加えていません。Pythonの専用type checkerはこの固定imageに見つからず、構文検査を型検査の成功とは呼びません。

今回の検査器は、原Q/Rの保存とID対応の完全性を検査しますが、対応先の意味の正しさ、全原文の自動理解、取得した上流文書の全仕様、未入手の実物は検証しません。全要求・承認計画・チャット・成果物・最終CIの総監査はR33、実装・本実測は各残件とR20です。
