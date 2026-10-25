# CI・Issue・リポジトリ設定の点検（2026-10-20）

[RESEARCH.md](../../RESEARCH.md) から分けた節です。CI のログ、Issue、DeepWiki、GitHub、AGENTS.md、GitHub Actions の設定を点検した結果と改善案をまとめます。設定の変更（ルールセット、Actions の allowlist、必須チェック）は利用者が行うので、ここでは提案にとどめます。

## 1. 点検の対象と方法

- CI: 各 workflow について、main 上の最新の完了 run を選びました。加えて、失敗した開発用イメージ公開の 3 run（39362964738、39364218477、39365153655）と、その後に成功した 39414913455 の job ログ、計 26 本を読みました。warning、error、deprecated の行を抜き出しています。
- ログの取り方: `gh` は認証していません。ログは Devin の CI ログ取得ツールで取りました。一部はツールの出力を並べ直したもので、GitHub の生のログファイルと同じものだとは確かめていません。
- Issue: 公開 API（`/repos/uist1idrju3i/MSD-Linux/issues?state=all`）で全件を見ました。2026-10-20 の時点で Issue は #59 だけです。
- 設定: `.github/workflows/`、`.github/dependabot.yml`、`.devin/wiki.json`、`AGENTS.md`、ルールセット（公開 API で読める範囲）を読みました。classic branch protection の API は HTTP 403 で読めませんでした。

## 2. CI のログで見つかったこと

| # | 見つかったこと | 根拠 | 改善案 |
|---|---|---|---|
| 1 | `actions/attest-sbom` が実行のたびに `actions/attest-sbom has been deprecated, please use actions/attest instead` を出す（amd64 と arm64 で 1 回ずつ） | run 39414913455 の build job | `actions/attest` に置き換える。先に Actions の allowlist に `actions/attest@<SHA>` を足す。run 39362964738 では allowlist にないため拒否された。composite action が中で呼ぶ action も allowlist に要る |
| 2 | 公開の 2 run が `Invalid image name: ghcr.io/uist1idrju3i/msd-dev:inputs-…-amd64` で失敗した | run 39364218477、39365153655 | run 39414913455 で成功しており、対処済み |
| 3 | 開発用イメージの build に amd64 で 465 秒（うちイメージ作成 413 秒）、arm64 で 666 秒（569 秒）かかる。大半は QEMU 11.1.2 のコンパイルで、ninja が約 3,300 段を実行し、`tests/unit` も作っている | run 39414913455 | QEMU を `qemu-system-aarch64` に必要なものだけ作る設定（ツールと試験を作らない）を、CI 高速化の実験の候補にする |
| 4 | 固定版の更新確認（2026-10-19 10:58 UTC の run 39241234179）は成功したが、Issue は作られていない | 公開 API | この run は、Issue を作る処理を加えた #37（2026-10-19 15:21 UTC にマージ）より前の版で動いた。次の定期実行（月曜 05:23 UTC）で Issue が作られるかを確かめる |
| 5 | 固定版の更新確認が、Trivy を「更新あり」と出す（固定値 `"0.76.0"`、最新 `v0.76.0`） | `check-pins.py upstream` を 2026-10-20 に手元で実行 | 引用符を外して比べるよう `check-pins.py` を直す。これは誤検知で、Trivy は最新 |
| 6 | 同じ実行で、カーネルの固定 commit（`2341883…`）より rpi-6.18.y の先頭（`5d64d1e…`）が新しい。Go は 1.27.2 → 1.27.3 | 同上 | vendor-update スキルの手順（変更履歴、回帰、ビルドと QEMU 起動）で更新する |
| 7 | GitHub Pages の deploy で Node の `DEP0040 punycode` 警告が出る | run 39311249087 | `actions/deploy-pages` の中の警告で、こちらでは直せない。新しい版が出たら更新する |
| 8 | `agent-docs` の JIS X 0213 検査が、`.agents/skills/jisx0213-text/SKILL.md` にある置き換え例の簡体字 2 字に、毎回 warning を出す | 手元の `check-jisx0213.py` | allowlist の引用に載った文字では warning を出さないようにする |
| 9 | 文書だけを変えた push では、`changes` の path filter で `build` job が skipped になる | run 39424719570 | 必須チェックは skipped を成功と見なすので、マージは止まらない。意図どおりなら `docs/CI.md` に書く |
| 10 | `site-status.yml` は schedule（月曜 05:41 UTC）と手動だけで、まだ一度も動いていない | 公開 API の run 一覧 | 初回の結果を次の月曜に確かめる |

git の `hint: … default branch` と、security の `confdata.c` の warning は動作に関係しません。

## 3. Issue #59（開発用イメージの脆弱性）

- 本文には、検出 1,955 件のうち先頭 100 件が 1 行ずつ並び、残りは「ほか 1855 件省略」とあります。並んだ 100 件はすべて LOW です。秘密情報と設定不備は 0 件、公開を止める対象も 0 件です。
- 重大度ごとの件数、修正版の有無、パッケージごとの集計、前回からの増減がありません。どの条件で公開を止めるかも、本文からはわかりません。
- 開発用イメージはビルドと試験だけに使い、製品のイメージには入りません。

改善案: 本文を「重大度 × 修正版あり・なし」の表と、件数の多いパッケージ 10 件にします。全件は SARIF と成果物へのリンクで示し、前回からの増減と、公開を止める条件も本文に加えます。

## 4. DeepWiki（`.devin/wiki.json`）

- `repo_notes` と「QEMU による検証」のページが、`raspi3b` を既定のように書いています。いまの既定は `raspi3ap`（512 MiB、CM0 の DTB）で、`raspi3b` は `QEMU_MACHINE=raspi3b` で選びます。
- 開発用コンテナー、QEMU のパッチ、実験の記録、文書の検査（yomiyasu、JIS X 0213、リンク）のページがありません。DeepWiki がページを独自に足しています。

改善案: 記述を `raspi3ap` に直し、上の 4 ページを足します（ページ数の上限は 30）。

## 5. GitHub の設定

- ルールセットの必須チェックは `build`、`changes`、`lint`、`zizmor`、`check`、`MSD tests in development image`、CodeQL（high 以上）です。承認は 0 件でマージできます。
- linear history を必須にしたまま、merge commit によるマージも許可しています。merge commit は linear history の条件に合わないので、選んでも失敗します。
- `agent-docs`（文書の規則とスキルのリンク）と、Pages の検査は必須チェックではありません。

改善案（利用者の操作）: マージ方式を squash と rebase に絞ります。`agent-docs` を必須チェックに加えます。なお、job 名を変えると必須チェックが「Expected — Waiting」のまま止まります。job 名を変える PR では、必須チェックの名前も合わせて変えてください。

## 6. AGENTS.md とスキル

- yomiyasu v2.1.0 は、名前を出して頼んだときに使われます。AGENTS.md の 2 節と 6 節は名前を出しているので、いまの書き方で動きます。
- site-review スキルは、w3m、lynx、日本語フォント、Playwright がある環境を前提にしています。sudo を使えない環境では入れられないので、Docker のコンテナーで w3m と lynx を動かすなどの代わりの方法を書いておくと、手順が止まりにくくなります。
- vendor-update スキルが求める「変更履歴の全件確認」は、yomiyasu の更新（#64）で行いました。upstream の試験のうち時間を測る 3 件は、同じ VM で Buildroot のビルドが動いている間に失敗しました。負荷が下がってから、その 3 件だけを 3 回試し、3 回とも通りました。

## 7. 未確認のこと

- 固定版の更新確認と `site-status` の定期実行の結果（次の月曜）。
- ルールセット以外の GitHub の設定（classic branch protection、Pages の詳細）は、権限がなく読めていません。

## 8. 2026-10-25 の追加点検

2026-10-20 以降の run を読み直しました。

### 8.1 対象と方法

- 公開 API で、2026-10-20 14:36 UTC から 2026-10-25 09:10 UTC までの run 300 件を取りました。内訳は success 284 件、failure 8 件、cancelled 8 件です。failure の run は、job ログをすべて読みました。
- Issue は #59 だけで、まだ開いています。最終更新は 2026-10-21 23:49 UTC です。
- `pins-check`（固定版の更新確認）と `security` の最後の run は、どちらも 2026-10-19 の定期実行です。次の定期実行は 2026-10-26 です。`site-status` は一度も動いていません。

### 8.2 見つかったこと

| # | 見つかったこと | 根拠 | 改善案 |
|---|---|---|---|
| 1 | QEMU の watchdog の PR（S11）で、`0003-hw-misc-bcm2835_powermgt-add-watchdog-timer.patch` を当てられなかった（`2 out of 8 hunks FAILED`）。開発用イメージを作れなかったため、必須チェックの `lint`、`zizmor`、`MSD tests in development image`、`build` の 4 つが同じ理由で失敗した。どの job も、開発用イメージを手元で作り直していた（`ensure local-build`） | run 39641440561、39641440481、39641441138 | `docker/qemu-patches/` を変えたときだけ動く短い job を足し、QEMU の tarball に `patch --dry-run` を当てる。失敗したら、ほかの job より先に原因を示せる |
| 2 | 同じ run で、`build` の `Show ccache statistics` が `Unable to find image 'msd-dev:local'` で失敗した。`if: always()` なので、イメージがないときも動く | run 39641440481 の build job | `if:` に、開発用イメージの準備が成功したことを条件として加える。本当の原因（パッチ）が埋もれにくくなる |
| 3 | `agent-docs` の失敗 4 件は、どれもマージの前に文書の不備を止めたものだった。内訳は、VM のパスが 2 件、実験の一覧に載っていない記録が 1 件、追跡していないファイルへのリンクが 1 件 | run 39699188533、39699030891、39539945796、39525236708 | 検査は意図どおり動いている。必須チェックではないので、5 節の提案どおり必須に加えると、見落としてマージする余地がなくなる |
| 4 | `Lint` の失敗（run 39520933606）は、`build.yml` の jq 式に対する ShellCheck SC2016 だった | run 39520933606 | `# shellcheck disable=SC2016` で対処済み |
| 5 | cancelled 8 件はすべて `Buildroot build and QEMU smoke test`。PR の 5 件は、`concurrency` の `cancel-in-progress` で、新しい push に置き換えられたものと見ている。main の push の 3 件（run 39561756635、39536931697、39536893420）は、`cancel-in-progress` が PR だけで有効になる設定なので、別の理由で止まったはず | `build.yml` の `concurrency` | main の 3 件の理由は確かめていない。手動で止めたのか、timeout なのかを run の詳細で確かめる |
| 6 | 2026-10-21 に更新された Issue #59 の本文も、3 節の形のまま（検出 1,956 件、公開ゲート対象 1 件、先頭は LOW が並ぶ） | Issue #59 | 3 節の改善案のとおり |

### 8.3 この点検の間に、手元で見つかったこと

- `git worktree` で作った checkout では、`docker/msd-dev` の中の `git rev-parse HEAD` が submodule で失敗します。submodule の `.git` が checkout の外を指し、そこはコンテナーに mount されていないからです。そのため `M5STACK_CARDPUTERZERO_VERSION` が空になり、ビルドが止まります。通常の clone では起きません。worktree を使う手順を書くなら、この点を注記します。
- yomiyasu の upstream の試験（2,352 件）は、Buildroot のビルドと同時に走らせると 1 件が失敗しました。その 1 件は、単独で再実行すると通りました。6 節の 2026-10-20 の観察（時間を測る試験が負荷の下で失敗する）と同じ傾向です。[PR #89](https://github.com/uist1idrju3i/MSD-Linux/pull/89) で v2.4.0 に上げると、6 節の「v2.1.0」は古くなります。
- この点検に使った VM では、blueprint で入れるはずの ShellCheck が `PATH` にありませんでした。開発用イメージの中の ShellCheck（`docker/msd-dev shellcheck`）で代わりに検査しました。

### 8.4 設定の再点検（DeepWiki、GitHub、AGENTS.md、Actions）

4〜6 節の指摘が 2026-10-25 にも残っているかを、公開 API とリポジトリのファイルで確かめました。

| 対象 | 2026-10-25 の状態 | 改善案 |
|---|---|---|
| DeepWiki | `.devin/wiki.json` の 2 か所が、まだ `raspi3b` での起動確認と書いている。ページは 21 件で、開発用コンテナー、QEMU のパッチ、実験の記録、文書の検査のページはまだない | 4 節の改善案のとおり。`docs/research/` は 33 本に増えたので、「調査記録の読み方」のページに、分割後に最初に読む文書（RESEARCH.md）を書く |
| ルールセット | `pull_request` の `allowed_merge_methods` は merge、squash、rebase のまま。`required_linear_history` もあるので、merge commit を選ぶと失敗する。必須チェックは `build`、`changes`、`lint`、`zizmor`、`check`、`MSD tests in development image` の 6 つで、`agent-docs` は入っていない | 5 節の改善案のとおり（利用者の操作） |
| 必須チェックの `build` | 文書だけの PR では skipped になる。skipped は必須チェックを満たすので、マージできる | 意図した動きとして、`docs/` か AGENTS.md に一行書いておく |
| AGENTS.md | 8 節の確認コマンドは、通常の clone を前提にしている。`git worktree` の checkout では、`docker/msd-dev` の中で git が動かず、ビルドに使った commit の記録や `shellcheck-tracked.py` が失敗する | 8 節に「worktree ではなく clone を使う」と注記する。変更の前に計画をお見せする |
| Actions | `actions/attest-sbom` は非推奨で、`actions/attest` に移るよう案内されている | `actions/attest` に移る。vendor-update の手順で、出力の形が同じかを確かめる |

### 8.5 まだ確かめていないこと

- 2026-10-26 の `pins-check`、`security`、`site-status` の定期実行の結果。
- main の push で cancelled になった 3 件の理由。
