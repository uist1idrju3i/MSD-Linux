# AGENTS.md

Devin / Codex / Claude Code など、このリポジトリで作業するすべての AI エージェントと人間が守るルールです。

## このリポジトリについて

MSD-Linux（Muromi Software Distribution / Linux）は、Muromi Software の Linux ディストリビューション関連の作業場です。

## 1. main ブランチの保護（最優先・例外なし）

- **`main` への操作は一切禁止します。** 具体的には次のとおりです。
  - `main` への直接コミット、直接 push
  - `main` への force push（`--force`、`--force-with-lease`、`+main` を含む）
  - `main` の削除（`git push origin --delete main`、`:main`）
  - `main` での rebase、reset、amend、履歴の書き換え
  - ブランチ保護やルールセットの変更
- **変更は必ず作業ブランチで行い、PR を作成します。** ブランチ名は `<agent>/<短い説明>` にします（例: `devin/add-docs`）。
- PR のマージは人間が行います。エージェントは明示的に指示されない限りマージしません。
- 作業を始める前に `git branch --show-current` を実行し、`main` でないことを確認してください。`main` にいたら、何かを変更する前に `git switch -c <branch>` で作業ブランチを作ります。
- 誤って `main` にコミットしてしまった場合は、push せずに作業ブランチへ移し（`git branch <new>` → `git switch <new>`）、報告してください。`main` を reset して直そうとしないでください。

## 2. 言語と書式

- ドキュメント、Issue、Pull Request のタイトルと本文は日本語で書きます。コミットメッセージも日本語を基本とします。
- コード、識別子、ファイル名は英語のままにします。
- 日本語の文章を書いたら、推敲スキル「yomiyasu」で読みやすさを整えてください（後述）。

## 3. 外部リポジトリ（vendor/）

- 外部のコードやスキルは `vendor/` に git submodule の shallow clone として追加します。

  ```sh
  git submodule add --depth 1 https://github.com/<owner>/<repo>.git vendor/<name>
  ```

  `.gitmodules` には `shallow = true` を記録します。
- `vendor/` 内のファイルは直接編集しません。修正が必要なら上流のリポジトリへ提案します。上流への書き込み（Issue・PR・push）は人間の承認を得てから行います。
- 取得: `git clone --recurse-submodules`。取得済みの場合は `git submodule update --init`。CI は `actions/checkout` の `submodules: true` で取得します。
- 更新: Dependabot が週次で更新の Pull Request を開きます。Dependabot の PR も、内容（変更履歴と影響）を確認してから人間がマージします。手動で更新する場合は `git submodule update --remote` を使い、動作確認してから PR にしてください。

## 4. 依存関係の管理

- `.github/dependabot.yml` で `gitsubmodule` と `github-actions` を週次監視しています。
- 新しい種類の依存（npm、pip、Docker など）を追加したときは、同じ PR で Dependabot の監視対象に加えてください。
- 依存を更新するときは、更新される側の変更履歴を全部読み、使える新機能や注意点があれば PR に書きます。

## 5. エージェントスキル

- リポジトリ固有のスキルは `.agents/skills/<name>/` に置きます。vendor 内のスキルはコピーせず、`.agents/skills/<name>` からのシンボリックリンクにします。
- Claude Code は `.claude/skills/` しか読まないため、`.claude/skills/<name>` → `../../.agents/skills/<name>` のリンクも必ず作ります。スキルを追加・改名・削除したら、リンクも同じ PR で直します。CI の `agent-docs` ワークフローがリンクの解決を検査します。Windows で clone するときは、シンボリックリンクを有効にします（`git config core.symlinks true` と、開発者モードか管理者権限）。
- 個人用の設定はコミットしません（`CLAUDE.local.md`、`.claude/settings.local.json`、`AGENTS.override.md` は gitignore 済み）。

| スキル | 使う場面 |
|---|---|
| `yomiyasu` | 日本語文書の推敲（`vendor/yomiyasu` へのリンク） |

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
- 変更は小さく、主題ごとにまとめます。

## 8. 確認コマンド

```sh
git submodule update --init             # submodule の取得
python3 .agents/skills/yomiyasu/scripts/yomiyasu_lint.py <file>  # 日本語文書の候補検査
```
