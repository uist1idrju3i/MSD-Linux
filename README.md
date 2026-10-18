# MSD-Linux

Muromi Software Distribution / Linux

## 開発規約

作業のルールは [AGENTS.md](AGENTS.md) を参照してください。

- ドキュメント・Issue・Pull Request は日本語で作成します。
- 外部リポジトリは `vendor/` へ git submodule（shallow）で追加します。
- 依存関係の更新は Dependabot が週次で Pull Request を開きます。

## 取得方法

```sh
git clone --recurse-submodules https://github.com/uist1idrju3i/MSD-Linux.git
```

既に clone 済みの場合は次を実行してください。

```sh
git submodule update --init
```
