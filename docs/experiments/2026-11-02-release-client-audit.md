# Release自己更新方式の静的調査と提出前検査

- 状態: 静的照合と既存host回帰試験を完了。静的調査であり、製品の自己更新実装ではない
- 日付: 2026-11-02
- 担当: Devin
- 関連: [設計と比較](../research/release-client/README.md)、[資料台帳](../research/release-client/sources.json)、[生の検査値](2026-11-02-release-client-audit.csv)

## 目的と仮説

CardputerZeroが匿名のGitHub Releasesを発見し、署名済みの対象を非稼働slotへ導入する構成を調べます。既存TUF clientと公開側toolを再利用する案を優先し、metadata認証、取得、書込み、health・commit、復旧を別の契約として整理します。

検査の仮説は、保存した出典bytesが台帳と一致し、改変・誤ったhash・欠落を検出できることです。TUFの動作・性能が正しいという仮説を、この静的検査で試したとは扱いません。

## 採否の基準と条件

出典の最初の取得は、この検査計画より前です。取得前に計画していたとは扱いません。取得後・反復検査前に、次を固定しました。

- 全取得成功資料のlength/SHA-256、判明しているGit blob IDが一致し、不一致0件。
- 取得失敗を成功へ混ぜず、そのURL・理由を保持する。
- 固定入力のA/Aを5回行い、件数と終了状態が一致する。改変bytes・誤ったexpected hash・資料欠落の3対照を全て拒否する。
- リンク、JIS文字、サイズ、skill、site、該当checkerの回帰試験、固定OCIのShellCheck/actionlint、offline zizmorが終了値0。警告はerrorと分けて読む。
- 新規文書は40,000 B未満、20,000 B超は主題で再検討する。日本語のlint/run/verifyと、数値・否定・条件の目視照合を行う。

| 条件 | 値・範囲 |
|---|---|
| 基準commit | `9fbc7767ccc475d67fba5e7d1d9e9968c12131bd`。この上への文書と静的検査runnerの追加 |
| host | Ubuntu 22.04.5 LTS、Python 3.12.13、Git 2.34.1 |
| 固定開発OCIで実行したtool | ShellCheck 0.11.0、actionlint v1.7.12、OpenSSL 3.5.7 |
| OCIのimage ID | `sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`。新規構築・公開の証拠ではない |
| その他のtool | zizmor 1.31.1、yomiyasu lint 2.4.0 |
| 入力 | 台帳71件。上流の固定commit、API・公式webの取得時刻、bytes、SHA-256を台帳へ保存 |
| 変更・固定条件 | 台帳と保存bytesを固定。負の対照だけをmemory内で変え、原本は編集しない |
| 反復 | 台帳照合5回。文書・lint等は機能検査で、速度の統計には使わない |
| build・QEMU | 本段階では実行しない。Buildroot `O=`・ccache warm/coldの比較、候補binaryのサイズ・RSS測定ではない |

## 再実行の手順

台帳の`file`に対応する取得bytesを一つのdirectoryへ保存し、`CAPTURES`にその場所を指定します。台帳のraw URLは固定commitですが、Release API、registry、web本文は可変です。後日の再取得値を当日の取得bytesと同一と仮定せず、新しい取得時刻・台帳で別の試行として記録します。API応答は加工後のJSONではなく取得bytesを使います。

```sh
for repeat in 1 2 3 4 5; do
    python3 docs/experiments/release-client-audit.py \
        --ledger docs/research/release-client/sources.json \
        --captures "$CAPTURES" --negative-tests || exit 1
done
docker/msd-dev tests/msd-update/run.sh
python3 .github/scripts/check-links.py
python3 .github/scripts/check-jisx0213.py
python3 .github/scripts/check-doc-size.py
python3 .github/scripts/check-skills.py
python3 .github/scripts/check-site.py
tests/check-links/run.sh
tests/check-jisx0213/run.sh
tests/check-doc-size/run.sh
tests/check-skills/run.sh
tests/check-site/run.sh
docker/msd-dev sh -c 'actionlint .github/workflows/*.yml;'
docker/msd-dev sh -c 'git ls-files -z -- "*.sh" | xargs -0 shellcheck'
"$HOME/.cache/msd-linux-zizmor/bin/zizmor" --offline --format=github .github/workflows/
```

日本語は各変更文書を`yomiyasu_lint.py`、`yomiyasu_check.py run --final <文書>`、`verify --final <文書>`で検査します。既存本文を推敲したときは、その改稿前の写しを`run --source`へ渡します。検査記録は意味の正しさの自動認定ではありません。

## 結果・失敗の扱い

終了値・出力のbytes/SHA-256は同名CSVへ記録しています。初回失敗と修正後の検査を別のrunとして残し、失敗の行を消しません。

出典取得71試行のうち、70件を取得、rust-tufのlatest Release APIは404でした。404は未保守の証明でも、開発treeが公開版である証明でもありません。固定Git blobを照合できる資料は43件です。top-levelのlicense確認は生成binaryのlicense closureではありません。

台帳照合5回は全て`retrieved=70 recorded_failures=1 git_blobs=43 errors=0`、三つの負の対照は毎回拒否しました。全5回のstdoutは159 Bで同じSHA-256でした。速度の中央値・最小・最大は計測しておらず、性能や統計的同等性の結論は出しません。

既存更新処理のhost試験20件、各checkerの回帰試験、固定OCIのactionlint/ShellCheck、offline zizmorは通りました。リンクの初回検査は、台帳内の上流原文パス3件を本リポジトリの古いpathとみなして失敗しました。取得記録を書き換えず、理由付き例外を3件追加した後は通りました。未使用の例外があれば既存checkerが失敗する方式です。JISと文書サイズの既存警告はerrorへ数えず、今回の新規文書には20,000 B超のものはありません。

yomiyasuの初回実行では、`--reader`に自由記述を渡したため11文書のrunが終了値2となり、続くverifyも全件で未検査または改稿後の不一致を検出しました。許される値`expert`へ直した後は、全11文書のlint/run/verifyを実行できました。製品の不具合とは区別しますが、提出前検査の失敗としてCSVに保持します。

残った候補は、表・手順の箇条書き比率、専門用語、文末と読点、資料にない語・数値の照合候補です。箇条書きは拒否条件と手順を区別するため、専門語は意味を変えないため残しています。新規本文は台帳だけでは仕様・実験結果を説明しきれないため、自動の資料照合には多数の候補が出ます。固定ソースと既存実装へ戻って数値・否定・提案と現行の区別を確認しており、終了値0を事実の自動認定にはしません。既存本文の「未照合」を追加調査へ更新した差分も、意図した変更です。

## 未確認の点とログ

候補のbuild・実行・conformance、通信の拒否試験、実SDへの書込み、実機tryboot・電源断・rollback、Wi-Fi、時計の保持、本番鍵移行、GitHub設定変更は本リポジトリでは試していません。既存更新処理のhost回帰試験を、新しいTUF clientの検証には数えません。

取得原文と検査stdoutは永続領域に保管し、台帳・CSVにlengthとSHA-256を残します。第三者の原文全文や巨大なAPI treeは転載しません。可変URLはhashだけで当時の全文を再生成できない限界があり、原本を再取得できたこととも区別します。今回の台帳照合、初回リンク失敗、host試験、lintとcheckerのstdoutを読み、失敗を含むCSV全列と照合しました。過去の実験の生ログを読み直したという意味ではありません。
