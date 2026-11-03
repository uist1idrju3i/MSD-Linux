# Release台帳

`releases.csv` は、公開tag、SemVer、内部更新番号、署名鍵の区分、Release URL、assetのSHA-256一覧を対応づける台帳です。tagとReleaseの作成・公開は利用者が行います。

| 列 | 内容 |
|---|---|
| `tag` | GitHub Releaseに対応するtag |
| `semver` | `v`を除いたSemVer |
| `prerelease` | GitHub Releaseがpre-releaseなら `true` |
| `commit` | tagが指すcommitの40桁SHA |
| `update_number` | tag commitのcommit時刻（UNIX秒、`%ct`） |
| `signing_key` | imageが信頼する署名鍵の区分 |
| `release_url` | GitHub ReleaseのURL |
| `assets_sha256` | `sha256sum`形式のasset hash一覧へのrepo相対path |
| `note` | Releaseの状態や検証範囲 |

各checksum fileは `sha256sum` の形式で保存します。GitHub APIのasset `digest` と、downloadしたassetの `sha256sum` が一致することを確認してください。開発用pre-releaseの署名鍵は開発用です。実機での起動確認とReleaseのimmutabilityは別々に記録します。
