# AGENTS.md

Devin / Codex / Claude Code など、このリポジトリで作業するすべての AI エージェントと人間が守るルールです。

## 1. main ブランチ

- GitHub のルールセットにより、`main` への直接 push、force push、削除、PR なしのマージは拒否されます。
- `<agent>/<short>` ブランチで作業し、PR を作成します。
- ルールセットは承認 0 件でのマージを許可するため、エージェントは PR をマージしません。
- ルールセットやブランチ保護を変更しません。
- 作業前に `git branch --show-current` を確認し、`main` では作業しません。
- 誤って `main` にコミットした場合は push も reset もせず、新しいブランチに移して報告します。

## 2. 言語と書式

- ドキュメント、Issue、Pull Request のタイトルと本文は日本語で書きます。コミットメッセージも日本語を基本とします。
- コード、識別子、ファイル名は英語のままにします。
- 日本語の文章を書いたら、推敲スキル「yomiyasu」で読みやすさを整えてください（後述）。
- 追跡しているテキストファイルの文字は JIS X 0213:2004 の範囲に収めます。CI の `agent-docs` ワークフローが検査します。
- 範囲外の文字を残してよいのは、upstream 由来のファイルと原文の引用だけです。引用は原文を書き換えずにコードスパン・コードブロック・引用行（`>`）で囲み、`.github/jisx0213-allowlist.tsv` に理由を一行で書きます。手順は「jisx0213-text」スキルに従います。
- 文書は目的と読者で分け、一つのファイルが大きくなりすぎないようにします。UTF-8 で 20,000 バイトを超えたら分割を検討し、40,000 バイトを超えたら分割または `.github/doc-size-exceptions.tsv` への理由付き例外が必須です（`agent-docs` ワークフローが検査します）。行数での機械的な切断や、表・条件・失敗記録を分断する分割はしません。判断と移動の手順は「document-structure」スキルに従います。

## 3. 外部リポジトリ（vendor/）

- `vendor/` の外部コードは shallow submodule として管理し、ファイルを直接編集しません。`.gitmodules` の `shallow = true` を維持します。
- submodule やほかの依存を追加・更新するときは「vendor-update」スキルに従います。
- 上流への Issue・PR・push は人間の承認を得てから行います。

## 4. 依存関係の管理

- `.github/dependabot.yml` で submodule、GitHub Actions、pip を週次監視しています。Dependabot が扱えない固定値（カーネル、Buildroot の系列、CI ツール、runner）は「固定版の更新確認」ワークフローが週次で調べ、Issue で知らせます。依存を追加したら、同じ変更で監視対象に加えます。
- Dependabot の PR を含むすべての更新で「vendor-update」スキルの変更履歴確認と回帰テストを行います。マージは人間が行います。

## 5. エージェントスキル

- リポジトリ固有のスキルは `.agents/skills/<name>/` に置きます。vendor 内のスキルはコピーせず、`.agents/skills/<name>` からのシンボリックリンクにします。
- Claude Code は `.claude/skills/` しか読まないため、`.claude/skills/<name>` → `../../.agents/skills/<name>` のリンクも必ず作ります。スキルを追加・改名・削除したら、リンクも同じ PR で直します。CI の `agent-docs` ワークフローがリンクの解決を検査します。Windows で clone するときは、シンボリックリンクを有効にします（`git config core.symlinks true` と、開発者モードか管理者権限）。
- 個人用の設定はコミットしません（`CLAUDE.local.md`、`.claude/settings.local.json`、`AGENTS.override.md` は gitignore 済み）。

| スキル | 使う場面 |
|---|---|
| `yomiyasu` | 日本語文書の推敲（`vendor/yomiyasu` へのリンク） |
| `jisx0213-text` | 範囲外の文字の置き換え、引用と upstream ファイルの例外 |
| `vendor-update` | 依存関係の変更履歴、採否、ライセンス、回帰テストの確認 |
| `experiment-record` | 実験・測定・比較の計画、実行、再現できる記録 |
| `site-review` | 公式サイトの見え方（テキストブラウザー、小さな画面、明暗）の確認 |
| `document-structure` | 文書の棚卸し、現行と履歴の区別、重複の整理、分割とリンクの照合 |

## 6. yomiyasu（日本語推敲スキル）

`vendor/yomiyasu` にある、AI が生成した日本語を読みやすく整えるスキルです。意味と条件を保ったまま、不自然な比喩、曖昧な主述関係、不要な装飾を直します。

- 呼び出し方: `/yomiyasu`、`$yomiyasu:yomiyasu`（Codex 系）、`yomiyasu:yomiyasu`（Claude Code）。依頼の文に「yomiyasu で」と書いても呼べます。
- 用途: 日本語のドキュメントや Issue・PR の説明文の推敲。
- 検査ツールは Python の標準ライブラリだけで動き、外部へ通信しません。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>`: AI の文章に多い表現の候補を出します。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_check.py run --source <原文> --final <最終稿>`: 推敲の前後を比べ、数値・否定・主述が変わっていないかを確かめます。記録は git 最上位の `.yomiyasu/` に残ります（gitignore 済み）。
- 自動フックの `yomiyasu_hook.py` は各開発者の個人設定でだけ有効化し、リポジトリにはコミットしません。

## 7. 作業の進め方

- 現行基盤は Buildroot です。Yocto 移行検討は見送りの記録であり、過去の移行計画を現在の作業指示として実行しません。現在の方針は [RESEARCH.md](RESEARCH.md)、判断の経緯は [Yocto 総まとめ](docs/research/yocto-migration/summary-2026-11.md) を確認します。
- 自明でない作業は調査して深い計画を立ててから着手します。計画はリポジトリにコミットせず、チャットで共有します。
- 実験・測定・比較を行うときは「experiment-record」スキルに従い、条件、手順、生の値、結論、失敗した試行を `docs/experiments/` に残します。結果を PR 本文だけに書きません。
- `public_html/` は GitHub Pages で公開するサイト専用です。文書は `docs/` に置き、`public_html/` にはサイトのファイル以外を置きません。`public_html/` を変えたら「site-review」スキルで、テキストブラウザーと小さな画面での見え方を確かめます。
- 文書の根拠に、VM や個人環境のパスを書きません。リポジトリ内のファイル、CI の成果物、公開 URL を示します。
- `output*/` など数 GB の untracked ディレクトリが常にあるため、`git stash -u` は使いません（走査で無応答になります）。ブランチ切替は対象ファイルを add/commit するだけで済ませ、untracked はそのまま残します。
- `vendor/` submodule の dirty（ビルド由来の変更）は commit しません。
- 変更は小さく、主題ごとにまとめます。
- 調査では、現在の決定、当時の判断、一次資料、実測、推測、未確認を分けます。引用・生データ・失敗記録を、新しい検査に通すために書き換えません。文書の整理は「document-structure」スキルに従います。
- 検証結果は、実行した commit、入力とバイナリ、変更した写しの範囲を示します。QEMU の起動成功を、LCD・キーボード・I2C・firmware tryboot・実機の電源断の検証と扱いません。
- 実行中の実験スクリプトを編集しません。出力先を消す前に、追跡されていない証拠を永続的な場所に保存して照合します。再取得できないログは、未確認と明記します。
- 完了報告では、依頼と計画の各項目を変更・検証・未確認に照らし合わせます。CI の合否とログを確認し、未実施の試験を実施済みとは書きません。
- GitHub の stacked PR は、同一リポジトリ内で PR を積み重ね、先行 PR の変更を後続ブランチに含める運用です。各 PR の base は利用者が設定し、エージェントは指示なしに base を変更したり、PR を merge したりしません。https://docs.github.com/en/pull-requests/reference/stacked-pull-requests、https://docs.github.com/en/pull-requests/get-started/about-stacked-prs

## 8. 確認コマンド

```sh
git submodule update --init             # submodule の取得
docker/msd-dev build                    # 開発用イメージの作成
docker/msd-dev <command>                # 固定ツール環境でコマンドを実行
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig && make -C output  # defconfig とビルド
tests/msd-update/run.sh                  # 更新処理のホストテスト
board/cardputerzero/qemu/test-boot.sh    # A スロットの QEMU 起動確認
board/cardputerzero/qemu/test-ab.sh      # B スロットの QEMU 起動確認
python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>  # 日本語文書の候補検査
python3 .github/scripts/check-skills.py && tests/check-skills/run.sh
python3 .github/scripts/check-links.py && tests/check-links/run.sh
python3 .github/scripts/check-doc-size.py && tests/check-doc-size/run.sh
python3 .github/scripts/check-jisx0213.py && tests/check-jisx0213/run.sh
python3 .github/scripts/check-site.py && tests/check-site/run.sh
docker/msd-dev actionlint .github/workflows/*.yml
docker/msd-dev python3 .github/scripts/shellcheck-tracked.py
docker/msd-dev zizmor --offline --format=github .github/workflows/
```

変更した対象の検査と、その検査器のテストを実行します。依存・イメージの変更は「vendor-update」のビルド・QEMU・監査結果も比較します。コマンドが通ることと、意味・見え方・実機動作の確認は区別します。
