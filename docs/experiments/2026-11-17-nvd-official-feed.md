# NVD公式feedのlocal bootstrapとconsumer確認

[実験一覧](README.md) / [取得元比較](../research/operations/nvd-source-options.md)

## 目的と条件

公式JSON 2.0を年別＋modifiedで取得し、meta照合・既存配置への展開・Buildroot consumerへの受け渡しが実際に完了するかを確認しました。利用者が指定した単回の接続・構築試験です。性能の採否基準、A/A比較、5回反復は設けておらず、所要時間をCIの性能保証に使いません。事前登録fileも作成していません。

- 基準commit: `f132f3c4e3c1165632e4549834a930bd242e5afc`とこの変更の作業ツリー。
- host: Linux `7.0.0-43-generic`、Python `3.14.4`。bootstrapはhostで実行。
- consumerと差分更新: 開発用image `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`、Python `3.13.5`。
- 入力は公式HTTPS feed。API key・fallbackなし。bootstrapのcacheは空。
- SBOMはwarmな`O=output-openssl-lts`のshow-infoから再生成。kernelは6.18.59へ補正しました。製品imageや依存をこの試験用に再buildしたわけではありません。
- 出力は`output-nvd-official-feed/`。製品SD・QEMU・UIは対象外です。

## bootstrapの生値

| 項目 | 値 |
|---|---|
| 取得開始 | 2026-11-17 17:25:34 UTC |
| 検証済み同期完了 | 2026-11-17 17:29:34 UTC |
| 取得器の経過時間 | 239.622秒 |
| feed数 | 26（2002〜2026の25年分＋modified） |
| gzip合計 | 255,549,328 byte |
| 展開後JSON合計 | 3,023,313,539 byte |
| feed entry合計 | 437,357件（重複を含む） |
| snapshotの固有CVE数 | 426,444件 |
| modified entry数 | 11,035件 |
| modified meta時刻 | 2026-11-17 17:00:05 UTC |
| snapshot ID | `04dc4f3ccce1e0ed72fea7203efb8b87711e5e55e821e25d0d2541b1a3b6af4d` |
| 終了値 | 0 |

gzip・展開後サイズは、各feedで実際に受け取ったbyte数をmetaと照合した後の合計です。meta転送量、HTTP header、保存時に正規化した個別JSONの合計ではありません。[CSV](2026-11-17-nvd-official-feed.csv)にも同じ生値を保存しました。初回bootstrapに失敗・再試行・警告はありませんでした。

bootstrap後、異常JSON、展開error、同期終了時の差分窓の検査と、manifest直下の`retrieved_at`を追加しました。最終版は、保存した同snapshotを読み直す差分更新で別途実行しています。bootstrap時のsource写しとhashは実行前に保存しておらず、証拠のsource hashは最終版です。正常なfeedの照合・展開方式は同じですが、最終版の全年度再取得とは区別します。

最終版の差分更新は17:31:55〜17:35:14 UTCで終了0でした。内容hashと426,444件は不変です。logの131.921秒はstaging開始後の時間で、cache内容の再検証を含む全体は時刻差で199秒です。既存snapshotを検証・copyするI/Oもあり、差分取得の転送時間だけを表す値ではありません。

## consumer

`cve-monitor.py cve-check --no-nvd-update --include-resolved`と`state`がともに終了0でした。VEXは16,191件、解決済みは16,038件、影響ありは152件、未評価は2件です。構成要素は79件。これは「脆弱性0」やRelease許可を意味しません。PRの新規CRITICAL gateはbase入力を用意しておらず、実データでは未実行です。

## 再現コマンドと保存した証拠

```sh
python3 .github/scripts/fetch-nvd.py --nvd-path output-nvd-official-feed/live/current
docker/msd-dev make -s -C output-openssl-lts show-info > output-nvd-official-feed/buildroot-show-info.json
docker/msd-dev python3 vendor/buildroot/utils/generate-cyclonedx \
  --in-file output-nvd-official-feed/buildroot-show-info.json \
  --project-name msd-linux --project-version "$(git rev-parse HEAD)" \
  > output-nvd-official-feed/sbom.cdx.json
docker/msd-dev python3 .github/scripts/set-kernel-version.py \
  output-nvd-official-feed/sbom.cdx.json \
  --show-info output-nvd-official-feed/buildroot-show-info.json \
  --project-version "$(git rev-parse HEAD)"
docker/msd-dev python3 .github/scripts/cve-monitor.py cve-check \
  --nvd-path /work/output-nvd-official-feed/live/current \
  --no-nvd-update --include-resolved \
  --in-file /work/output-nvd-official-feed/sbom.cdx.json \
  --out-file /work/output-nvd-official-feed/vex.cdx.json
docker/msd-dev python3 .github/scripts/cve-monitor.py state \
  --sbom output-nvd-official-feed/sbom.cdx.json \
  --vex output-nvd-official-feed/vex.cdx.json \
  --exceptions .github/cve-exceptions.tsv \
  --feed-manifest output-nvd-official-feed/live/current/manifest.json \
  --now "$(date -u +%s)" --output output-nvd-official-feed/state.json
```

初回は上記のproject versionに基準commitを明示しました。後の実行で同じ上流feedが得られる保証はありません。小さい証拠は[archive](2026-11-17-nvd-official-feed/evidence.tar.gz)に保存し、bootstrap manifest、log、show-info、SBOM、state、最終sourceとhashを含めます。VEX（46,526,370 byte）と全CVE JSONは大きいため収録せず、作業出力に保持しました。VEXのSHA-256は`2557063a3fcf5ce196dfcef6237cf64b7c7d8b12bd09b171a94417da7bbc61d3`です。元snapshotを失えば、そのVEXを同じ入力から再生成できるとは限りません。

fixture試験では正常更新、空差分、hash不一致、gzip切断、cache欠損、7日窓超過、feed名とID年の不一致、archiveからのcache復元を確認しました。負のfixtureで公開先が変わらず、空差分で内容hashが変わらないことを照合しています。実Actions cacheの保存・権限・保持期間は未確認です。

archiveは15 fileを元fileとbyte照合しました。96,976 byte、SHA-256は`909f8e2d3ef468b925a1338940186d314527fbf1a16f5ef7e862450f77e4f5a0`です。
