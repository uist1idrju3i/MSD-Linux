# 既知の全構成要素と代替比較の対応を照合する

## 目的と事前の基準

Buildrootの67行だけで開発OCI・Actionsまで覆ったと誤認しないため、既存の依存台帳を比較本文へ対応づける。全候補のlicense・EOL・実bundleの監査や、代替構成の実行確認とは別の照合である。製品設定・CI・依存版は変えない。

- 基準commit: `5d5b275f27da0cf2de6402eeb21b36fb9095a02a`。
- 入力: Buildrootの67行、最終amd64 OCIの231 APT、Actionの11参照、npmの859名・1,574 name/version、actionlintの11 Go module。外部toolchain・別OCI・runner等は有限の一覧と網羅できていない層を分ける。
- 合格基準: 既存台帳と名前・版・architecture・親参照の集合が一致する。重複キー、欠落、存在しない比較先、未知の分類を許可しない。
- 計測器: 名前の欠落、版の改変、親の消失、分類外のsourceを与える負の対照は必ず拒否する。同じ固定入力の出力を5回照合しbyte一致を確認する。
- OCIを読むのはmetadataの照合であり、5回のbuild・性能測定ではない。build出力、ccache、cold/warm、QEMU、実機は使用しない。
- 実行scriptと入力hash、実際のPython・OCI識別子、CSV、失敗記録を結果と一緒に保存する。既存結果は上書きせず、新しい出力先を使う。

## 初回の失敗と訂正の方針

1. `docker/msd-dev python3 -`へheredocを渡した初回は、wrapperが標準入力を転送しないため出力が空だった。JSONの読込みが失敗したので、採取成功に数えない。再試行はscriptを`python3 -c`の引数へ渡す。
2. `dpkg-query`の`${Package}`と、既存台帳のmultiarch suffix付きの名前をそのまま比べた初回は、それぞれ127キーが一致しなかった。architectureの列を残し、名前のsuffixを照合時だけ分離すると231件の名前と版は一致した。空出力と名前の不一致は、package版の差や比較の成功に読み替えない。
3. 初回runnerはcomposite Actionの`package-lock.json`が明示的に`not-present`である3件を想定せず、`KeyError`で停止した。Node Actionの欠測とは分け、compositeの子参照を辿る。初回のtracebackを残し、新しい出力先で再実行する。

## 実行結果

既存台帳と実体の名前・版・architectureは231件全て一致した。129 sourceの分類に欠落・重複はない。Dockerfileの最終stageで明示するAPTは48件で、残る183件を不要と判定したわけではない。Depends/Pre-Dependsは原文を残し、導入済みの候補への逆依存を別列に記録した。Provides・実行時loadを含む完全なsolverではない。

Buildroot 67行、直接8と子3のAction、npmの859名・1,574組、Go module 11件を既存台帳と対応づけた。Actionは現行workflowの固定参照とも一致した。npmの親contextにはdev/optional/licenseを保存し、欠測の`null`を`false`やMITへ変換しなかった。固定commitのAction root LICENSEは10原文ともMITだった。全npmのlicenseを認定した結果ではない。

[raw CSV](2026-11-03-alternative-coverage.csv)は5回の同一入力再生成と4負対照の全列を記録する。全て`passed=True`で、負対照はpackage欠落・版改変・未知source・親Action欠落を拒否したことを表す。[初回の失敗](2026-11-03-alternative-coverage-first.csv)は3件を残した。最初の2件と初回runnerの内側の終了値は採取していないので、`not-recorded`とし成功へ数えない。

[入力・出力hashと件数](2026-11-03-alternative-coverage-summary.json)に基準を固定した。VM側Python 3.12.13と固定OCIのPython 3.13.5で、4生成CSV・検査CSV・summaryはbyte一致した。公開scriptでOCI metadataを再採取し、保存したJSONとのbyte一致も確認した。既存のbuild treeやcacheは使っていない。compiler・QEMU・製品image・実機を新たに実行した結果ではない。

固定OCI内の[提出前13検査](2026-11-03-alternative-coverage-local-checks.csv)も全て終了値0だった。SKILL、JIS、リンク、文書サイズ、siteと各fixture、設定調査のunit test、actionlint、zizmorを実行した。既存の文字・文書サイズのwarningと、fixtureで期待したerrorはCI失敗と区別した。追加した索引でRESEARCHが20,000 bytesを超えたため、本文は残し、重複する長い案内を短縮した。文書全体の分割・再編は別の継続作業である。

環境はLinux 6.8.0-1061-aws x86_64、Docker client/server 29.7.2、OCIはlinux/amd64だった。QEMU・GCC等のbinaryはこの照合では呼んでおらず、版を実測したとの主張には含めない。

## 再実行

作業はrepositoryのrootで行う。Docker wrapperの`msd-dev:local`が、監査した`ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`を指すことを`docker image inspect`のID・RepoDigestsで確認した。snapshotの別のimageを暗黙に取得・buildする手順ではない。

```sh
docker image inspect msd-dev:local --format '{{.Id}} {{json .RepoDigests}}'
docker/msd-dev python3 --version
mkdir -p .yomiyasu
(set -C; docker/msd-dev python3 -c "$(cat docs/experiments/2026-11-03-alternative-coverage.py)" --collect-oci > .yomiyasu/oci-metadata-new.json)
cmp .yomiyasu/oci-metadata-new.json docs/research/alternatives/oci-package-metadata.json
docker/msd-dev python3 docs/experiments/2026-11-03-alternative-coverage.py \
  --oci-metadata docs/research/alternatives/oci-package-metadata.json \
  --licenses docs/research/alternatives/action-license-sources.json \
  --output-dir .yomiyasu/alternative-coverage-new
```

出力先は未使用の名前を選ぶ。既存のdirectoryがあれば停止する。4生成CSVは[OCI](../research/alternatives/oci-coverage.csv)、[Action](../research/alternatives/action-coverage.csv)、[npm](../research/alternatives/npm-coverage.csv)、[Go](../research/alternatives/go-coverage.csv)と比較する。summaryは実行script・workflow・既存台帳のhashも含むため、入力を変えた再試行を同一試行とは扱わない。

## 未確認範囲

これは既知母集団の対応・所有境界と文書の静的照合である。実bundle、全stage/両CPU OCI、配布binary、外部toolchain/firmware内包物、runner全体の独立SBOM、全licenseの法的解釈、全upstreamの保守/EOL、代替構成のbuild・機能・性能・実機動作は未確認として残る。[全体の範囲と追加確認](../research/alternatives/inventory-boundaries.md)へ対応づけた。Brotli更新、製品/CI設定の変更、外部repositoryへの書込みはしていない。

[実験の索引へ戻る](README.md)
