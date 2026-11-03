# CIの起動条件・開発OCIキャッシュ・host回帰並列化の検証

[実験の一覧](README.md) / [CIの調査](../research/ci-build-scope-and-performance.md)

## 目的と事前の判定条件

文書変更だけで製品buildを起動せず、製品入力・未知のpath・差分の判定失敗ではbuildすることを確認します。PRの累積差分と改名・削除、週次・手動の入口も対象です。開発OCIは公開済みなら毎回pullとattestation検証を行い、未公開の場合に限り完全一致のcacheを使用します。独立したhost回帰7組は、同じ固定OCI内で最大2組ずつ並列実行します。

正式反復は`tests/check-ci-cache/run.py`の15 methodと`tests/check-ci-scope/run.py`の7 methodを各5回実行し、全回終了値0、入力hashの一致を採用条件とします。main統合後は`tests/check-build-scope/run.py`の6 methodも各5回確認します。改変archive、metadata、別platform、公開imageのpull/認証/attestation失敗、cache部分一致、容量超過、build/load/save失敗、差分取得失敗、並列runnerのtimeout・遅い失敗を負の対照にします。期待する拒否も含めた回帰の成功であり、製品の安全性全体を認定しません。

基準commitは`7a0d52b2f20889ac23dd6a8fa585a44c3a373866`です。開発OCIは`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、Linux/amd64を用います。Pythonは実binaryで3.13.5です。正式記録には使用したscriptとworkflowのhash、tool版、全行の終了状態、ログのhashを残します。Buildroot/GCC/kernel/QEMUの新しいbuildや起動はこのローカル回帰に含めません。

既存の7組も実際の並列runnerで確認します。実Dockerのarchive save/loadは1回の機能確認とし、GitHub cacheの転送やcold/warmの性能実験に転用しません。長期hit率・総費用・速度の改善率は未測定です。生ログは上書きしない出力先へ保持します。

## 予備実行で分かった問題

最初のactionlintはcache世代出力の個別redirectをSC2129として検出したため、出力を一つのblockへまとめました。zizmorはworkspace相対actionを指摘したため、[GitHub公式のself-repository構文](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsuses)に変更しました。ただし固定版actionlint 1.7.12はこの構文に未対応です。該当する一つのaction pathの構文誤認だけを理由付き例外とし、pin・path・他actionには効かないことを回帰で検査します。例外を外すには対応版への更新と再検査が必要です。

scope回帰の初回は、コンテナーにGitのauthor設定がないため仮の履歴作成に失敗しました。fixture専用のauthor/committer環境変数を使う方式へ直し、実リポジトリの設定は変更していません。同じ予備試行で出たCSV streamの閉じ忘れも修正しました。正式反復と予備失敗を分けて記録します。

## 正式実行

[最終CSV](2026-11-03-ci-cache-and-parallel.csv)と[入力metadata](2026-11-03-ci-cache-and-parallel.json)はformal-v6です。3 suite各5回、tool同定、実Dockerのsave/loadの18行が全てpassed・終了値0でした。全列・ログ・入力hashを照合しています。7組のhost回帰も実runnerで全て成功し、Trivy gate、SBOM、署名CLIの試験鍵5組・60 commandの期待値一致を確認しました。actionlint、ShellCheck、zizmor、Python構文検査も成功しました。

一覧CSVは公開時に改行をLFへそろえ、全セルが原記録と一致することを確認しました。ZIP内にはCRLFの原CSVをそのまま保存しています。

最終入力はmain統合commit `08e191b`の対象ファイルとhashが一致します。metadataの`base_commit`は採取開始時のHEADであり、当時の作業差分を含むcommit全体の同定ではありません。実際の入力は`inputs`各行で固定します。ローカル回帰の成功を、未実行の製品buildやQEMUの成功とは扱いません。

Python 3.13.5、actionlint 1.7.12、ShellCheck 0.11.0、zizmor 1.31.1を使用しました。binaryのhashと版出力は生ログの`tools.log`にあります。archiveは266,478,080 bytes、SHA-256は`942893e4ecffa20d5f205c945d3b28c327b845232847ef6532e4f75c3408f88d`、入力タグは`inputs-fcf14a3abc4d89ac`です。これはDocker save/loadの機能確認であり、sourceからのbit単位の再現性証明ではありません。

[生ログ・過去試行のCSV・metadata](2026-11-03-ci-cache-and-parallel-logs.zip)も保存します。ZIPのSHA-256は`6f75fe4a6b365866558dd7eac8322a3e7cdc26c63cdbc9b7be0b7d3b3c728f25`です。formal-v1/v2は統合前の成功記録です。formal-v3ではcache 5回は成功しましたが、workflowの対象を全workflowへ広げた後も旧文字列を消すmutationが残り、scope 5回が失敗しました。修正後のformal-v4、mainの署名試験を統合したformal-v5、仮の文書pathをPathで組み立てたformal-v6は別の試行として保持しています。失敗を成功値へ混ぜません。

文書pathの検査は、最初にテスト用の架空pathを実在する文書への参照と判定しました。実Git fixture内のpathをPathで構成し、検査の例外を増やさず再確認しました。main統合時には、署名CLIの常時実行と、改名前の製品入力を見落とさない`--no-renames`の契約を両方残しています。

## 再実行と未確認

Docker daemonを利用できるLinux cloneで、既存の出力先を上書きせず実行します。

```sh
docker/msd-dev ensure
python3 tests/check-ci-cache/record.py --output-dir output/ci-validation/new-trial --repetitions 5 --check-docker-archive
docker/msd-dev python3 .github/scripts/run-host-tests.py --jobs 2 --output-dir output/ci-host-tests/new-trial
```

cache制御scriptはDocker CLIを操作するためhost上で動かし、回帰suiteは固定OCI内で実行します。GitHub runner上の実cache hit・転送時間、mainへの反映、新しい製品Buildroot/QEMUの結果は、ローカル回帰と区別して確認します。cold/warmの壁時間・runner時間・転送/保存費用の各5回比較と、総費用の最適化はR29で未完了です。

Brotli修正版の保留は利用者が解除しました。R25を実行対象へ戻しましたが、この変更では依存版を変えていません。両archのbuild・scan・SBOM・attestationと公開ゲートの再確認は、CI改善のmain反映後に進めます。公開検査・署名検証は緩めません。
