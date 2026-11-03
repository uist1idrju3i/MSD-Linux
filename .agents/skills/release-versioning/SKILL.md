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
3. 利用者がそのcommitにtagを付け、`MSD_UPDATE_VERSION` を設定せずにbuildします。
4. Releaseをdraftで作成 → 全assetをupload → publishの順に進め、公開後にimmutableにします。
5. follow-upの台帳PRでCSV行と `docs/releases/<tag>.sha256` を追加します。GitHub APIのasset `digest` と、downloadしたfileに対する `sha256sum` の値を照合し、一致を確認します。
6. 署名は [Releaseの保護と署名鍵の設定](../../../docs/RELEASE-SIGNING.md) に従います。

## 禁止事項

- エージェントはtagやReleaseを作成・公開しません。エージェントが作るのはCHANGELOGと台帳のPRだけです。
- SemVerを再発行したり、同じcommitへ複数のSemVerを割り当てたりしません。
- Release buildで `MSD_UPDATE_VERSION` を設定したり、手動の内部番号fileを作ったりしません。
- `-rc.N` を実機検証済みと表現せず、immutabilityが既存Releaseにも適用されると扱いません。
- digestを確認せずに台帳へ転記しません。APIのdigestとdownload後の `sha256sum` が違う場合は停止します。

## 検証

```sh
python3 .github/scripts/check-releases.py
python3 .github/scripts/check-releases.py --require-tags
tests/check-releases/run.sh
python3 .github/scripts/check-links.py
python3 .github/scripts/check-jisx0213.py
```

台帳の列と既存Releaseの値は [docs/releases/](../../../docs/releases/README.md) を参照します。
