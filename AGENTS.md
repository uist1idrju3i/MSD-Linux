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

## 3. 外部リポジトリ（vendor/）

- `vendor/` の外部コードは shallow submodule として管理し、ファイルを直接編集しません。`.gitmodules` の `shallow = true` を維持します。
- submodule やほかの依存を追加・更新するときは「vendor-update」スキルに従います。
- 上流への Issue・PR・push は人間の承認を得てから行います。

## 4. 依存関係の管理

- `.github/dependabot.yml` で submodule と GitHub Actions を週次監視しています。pip などの依存を追加したら、同じ変更で監視対象にも加えます。
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

## 6. yomiyasu（日本語推敲スキル）

`vendor/yomiyasu` にある、AI が生成した日本語を読みやすく整えるスキルです。意味と条件を保ったまま、不自然な比喩、曖昧な主述関係、不要な装飾を直します。

- 呼び出し方: `/yomiyasu`、`$yomiyasu:yomiyasu`（Codex 系）、`yomiyasu:yomiyasu`（Claude Code）。依頼の文に「yomiyasu で」と書いても呼べます。
- 用途: 日本語のドキュメントや Issue・PR の説明文の推敲。
- 検査ツールは Python の標準ライブラリだけで動き、外部へ通信しません。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>`: AI の文章に多い表現の候補を出します。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_check.py run --source <原文> --final <最終稿>`: 推敲の前後を比べ、数値・否定・主述が変わっていないかを確かめます。記録は git 最上位の `.yomiyasu/` に残ります（gitignore 済み）。
- 自動フックの `yomiyasu_hook.py` は各開発者の個人設定でだけ有効化し、リポジトリにはコミットしません。

## 7. 作業の進め方

- 自明でない作業は調査して深い計画を立ててから着手します。計画はリポジトリにコミットせず、チャットで共有します。
- 実験・測定・比較を行うときは「experiment-record」スキルに従い、条件、手順、生の値、結論、失敗した試行を `docs/experiments/` に残します。結果を PR 本文だけに書きません。
- 文書の根拠に、VM や個人環境のパスを書きません。リポジトリ内のファイル、CI の成果物、公開 URL を示します。
- 変更は小さく、主題ごとにまとめます。
- GitHub の stacked PR は、同一リポジトリ内で PR を積み重ね、先行 PR の変更を後続ブランチに含める運用です。各 PR の base は利用者が設定し、エージェントは指示なしに base を変更したり、PR を merge したりしません。https://docs.github.com/en/pull-requests/reference/stacked-pull-requests、https://docs.github.com/en/pull-requests/get-started/about-stacked-prs

## 8. 確認コマンド

```sh
git submodule update --init             # submodule の取得
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig && make -C output  # defconfig とビルド
tests/msd-update/run.sh                  # 更新処理のホストテスト
board/cardputerzero/qemu/test-boot.sh    # A スロットの QEMU 起動確認
board/cardputerzero/qemu/test-ab.sh      # B スロットの QEMU 起動確認
python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>  # 日本語文書の候補検査
actionlint .github/workflows/*.yml
git ls-files -z -- '*.sh' | xargs -0 shellcheck
python3 -m venv "$HOME/.cache/msd-linux-zizmor"
"$HOME/.cache/msd-linux-zizmor/bin/pip" install --require-hashes -r .github/zizmor-requirements.txt
"$HOME/.cache/msd-linux-zizmor/bin/zizmor" --offline --format=github .github/workflows/
```
