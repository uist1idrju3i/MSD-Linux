# AGENTS.md

このリポジトリで作業するエージェント（Devin、Codex、Claude Code など）と開発者が守る規約です。

## このリポジトリについて

MSD-Linux（Muromi Software Distribution / Linux）は、Muromi Software の Linux ディストリビューション関連の作業場です。

## 言語

- ドキュメント、Issue、Pull Request、コミットメッセージは日本語で書きます。
- コード、識別子、ファイル名は英語のままにします。
- 日本語の文章を書いたら、推敲スキル「yomiyasu」で読みやすさを整えてください（後述）。

## 外部リポジトリ（vendor/）

- 外部のコードやスキルは `vendor/` に git submodule の shallow clone として追加します。

  ```sh
  git submodule add --depth 1 https://github.com/<owner>/<repo>.git vendor/<name>
  ```

  `.gitmodules` には `shallow = true` を記録します。
- `vendor/` 内のファイルは直接編集しません。修正は上流のリポジトリへ提案し、取り込みは submodule の更新で行います。
- 取得: `git clone --recurse-submodules`。取得済みの場合は `git submodule update --init`。CI は `actions/checkout` の `submodules: true` で取得します。
- 更新: Dependabot が週次で更新の Pull Request を開きます。手動で更新する場合は `git submodule update --remote` を使い、動作確認してから PR にしてください。

## 依存関係の管理

- `.github/dependabot.yml` で `gitsubmodule` と `github-actions` を週次監視しています。
- 新しい種類の依存（npm、pip、Docker など）を追加したときは、同じ PR で Dependabot の監視対象に加えてください。

## エージェントスキル

- リポジトリ固有のスキルは `.agents/skills/<name>/` に置きます。vendor 内のスキルはコピーせず、`.agents/skills/<name>` からのシンボリックリンクにします。
- Claude Code は `.claude/skills/` しか読まないため、`.claude/skills/<name>` → `../../.agents/skills/<name>` のリンクも必ず作ります。CI の `agent-docs` ワークフローがリンクの解決を検査します。
- 個人用の設定はコミットしません（`CLAUDE.local.md`、`.claude/settings.local.json`、`AGENTS.override.md` は gitignore 済み）。

## yomiyasu（日本語推敲スキル）

`vendor/yomiyasu` にある、AI が生成した日本語を読みやすく整えるスキルです。意味と条件を保ったまま、不自然な比喩、曖昧な主述関係、不要な装飾を直します。

- 呼び出し方: `/yomiyasu`、`$yomiyasu:yomiyasu`（Codex 系）、`yomiyasu:yomiyasu`（Claude Code）。依頼の文に「yomiyasu で」と書いても呼べます。
- 用途: 日本語のドキュメントや Issue・PR の説明文の推敲。
- 検査ツールは Python の標準ライブラリだけで動き、外部へ通信しません。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>`: AI の文章に多い表現の候補を出します。
  - `python3 .agents/skills/yomiyasu/scripts/yomiyasu_check.py run --source <原文> --final <最終稿>`: 推敲の前後を比べ、数値・否定・主述が変わっていないかを確かめます。記録は git 最上位の `.yomiyasu/` に残ります（gitignore 済み）。
- 自動フックの `yomiyasu_hook.py` は各開発者の個人設定でだけ有効化し、リポジトリにはコミットしません。

## 作業の進め方

- 自明でない作業は調査して深い計画を立ててから着手します。計画はリポジトリにコミットせず、チャットで共有します。
- 変更は小さく、主題ごとにまとめます。
