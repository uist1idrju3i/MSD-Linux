---
name: release-versioning
description: MSD-Linux のCHANGELOG、公開版、Release台帳を準備・検査するときに使う。
---

# リリース版と台帳

## 版の上げ方

| 種類 | 条件 |
|---|---|
| MAJOR（1.0以降）／MINOR（0.y） | bundleまたはmanifest形式、partition layout、再flashが必要な署名鍵変更、利用者向けcommandの削除・非互換変更、自己更新互換性の破壊 |
| MINOR | 互換性を保つ機能追加 |
| PATCH | formatを変えない修正 |
| `-rc.N` | 実機検証に進める候補。tagだけで実機検証済みとはしない |

公開版はSemVer 2.0.0です。tagは `vMAJOR.MINOR.PATCH` または `vMAJOR.MINOR.PATCH-rc.N` とし、build metadataは付けません。最初の公開版は `v0.1.0` です。`v0.0.0` は開発用pre-releaseです。

内部更新番号はtag commitのcommit時刻（`%ct`）です。Release buildでは `MSD_UPDATE_VERSION` を設定せず、手動の番号ファイルを追加しません。開発buildもcommit時刻を使いますが、開発用鍵で署名します。immutabilityは過去のReleaseへ遡って適用されません。

## 手順

1. release-prep PRで `CHANGELOG.md` の `[Unreleased]` の項目を `## [x.y.z] - YYYY-MM-DD` へ移します。
2. merge後、利用者がmerge commitの `%ct` が台帳の最後の `update_number` より大きいことを確認します。
3. 利用者がそのコミットに署名なしの正式版タグ `vX.Y.Z` または RC タグ `vX.Y.Z-rc.N` を作成し、push します。署名ワークフローは `MSD_UPDATE_VERSION` を上書きせずに構築し、`production` の承認後に署名します。正式版は RC と同じコミットを使わず、内部更新番号が大きいコミットから構築します。
4. Releaseをdraftで作成 → 全assetをupload → publishの順に進めます。Release immutabilityが有効なら、publishした時点でimmutableになります。
5. follow-upの台帳PRでCSV行と `docs/releases/<tag>.sha256` を追加します。GitHub APIのasset `digest` と、downloadしたfileに対する `sha256sum` の値を照合し、一致を確認します。
   公開済みの Release が台帳にないと `agent-docs` が失敗します。台帳 PR は公開直後に出します。公開していないタグや下書きだけのタグは、台帳への追加を求めません。
6. 署名は [Releaseの保護と署名鍵の設定](../../../docs/RELEASE-SIGNING.md) に従います。

RC の署名に失敗し、修正が必要な場合は、失敗したタグを削除したり付け替えたりしません。その RC は公開せず、修正 PR で `CHANGELOG.md` の版見出しも次の RC（例: `## [1.2.3-rc.2] - YYYY-MM-DD`）に更新します。PR を `main` にマージし、コミット時刻が台帳の内部更新番号より大きいことを確認してから、新しい RC タグを作成して push します。未公開の RC を台帳に追加する必要はありません。

## 禁止事項

- エージェントはtagやReleaseを作成・公開しません。エージェントが作るのはCHANGELOGと台帳のPRだけです。
- SemVerを再発行したり、同じcommitへ複数のSemVerを割り当てたりしません。
- Release buildで `MSD_UPDATE_VERSION` を設定したり、手動の内部番号fileを作ったりしません。
- `-rc.N` を実機検証済みと表現せず、immutabilityが既存Releaseにも適用されると扱いません。
- digestを確認せずに台帳へ転記しません。APIのdigestとdownload後の `sha256sum` が違う場合は停止します。

## 検証

```sh
python3 .github/scripts/check-releases.py
tests/check-releases/run.sh
python3 .github/scripts/check-links.py
python3 .github/scripts/check-jisx0213.py
```

全タグを台帳と照合する場合は `--require-tags` を付けます。CI と同じ範囲を調べる場合は、さらに `--published-tags` に公開済み Release のタグを1行ずつ書いたファイルを渡します。

台帳の列と既存Releaseの値は [docs/releases/](../../../docs/releases/README.md) を参照します。
