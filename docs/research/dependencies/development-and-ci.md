# 開発環境とCIの依存監査

## OCIとAPT

対象はamd64の最終開発用image、`ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`。Dockerfileの列挙だけでなく、dpkg databaseの導入済み231件を調べた。architecture、multiarch suffix付きのpackage名、導入版、候補、suite、結果は[CSV](development-apt.csv)と[JSON](development-apt.json)に保存した。

Debian trixie、trixie-updates、trixie-securityのInReleaseをDebian archive keyringで `gpgv` 検証し、署名対象のSHA-256とbyte数をPackages.xzと照合した。署名検証したindexを読んだ結果、228件は同じで、次の3件に新しい配布版があった。upstreamの最新majorを比べる表ではない。

| package | 導入版 | trixie内の候補 | suite |
|---|---|---|---|
| libbrotli1:amd64 | 1.1.0-2+b7 | 1.1.0-2+deb13u1 | trixie-security |
| linux-libc-dev | 6.12.113-1 | 6.12.115-2 | trixie-security |
| tzdata | 2026e-0+deb13u1 | 2026f-0+deb13u1 | trixie-updates |

keyringのSHA-256、gpgvの版、各署名・indexのURLとhash、Date/Valid-UntilはJSONにある。今回の取得時点でupdates/securityのValid-Untilは未到来だった。通常のtrixie InReleaseには同じ期限欄がない。署名とhashだけでは古いmetadataの再送を排除できないため、継続監視では期限、信頼できる時刻、最大経過時間、取得失敗を判定する必要がある。今回の補助スクリプトは期限を自動強制するmonitorとして実装したものではない。

初回はdpkgの `name:amd64` とindexの `name` が一致せず127件を照合できなかった。照合キーからmultiarch suffixを外して再実行し、231件全てに候補があることを確認した。architecture自体の記録は削除していない。失敗した初回集計を最新版不明の件数として採用しない。

### scannerの結果と延期した修正

[run 41492762353](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41492762353)のsanitized report、image provenance、Trivy version、CIログを読んだ。Trivyは0.76.1、DB更新は2026-11-02 13:15:56 UTC。脆弱性のレコード2,184件（OS 2,183、Go 1）、credential検出0、misconfiguration検出0で、修正版のあるCRITICALはBrotliの `CVE-2026-111497` 一件だった。これは一意のCVE件数でも、製品rootfsの検出件数でもない。

報告の成功は脆弱性ゼロを意味しない。Brotliは今回更新せず、[Issue #59](https://github.com/uist1idrju3i/MSD-Linux/issues/59)で未対応を追う。重要な検出が先頭100件の打ち切りで隠れない報告と、秘密値を含めない全件記録は[PR #183](https://github.com/uist1idrju3i/MSD-Linux/pull/183)で扱う。raw Trivy JSON、秘密値、image tar、DBはリポジトリへ保存していない。

2026-11-03にR25の範囲を開発用OCIの公開ゲート解消へ広げ、`DEBIAN_SNAPSHOT=20261103T023120Z`でamd64を再構築した。旧imageから変わったのは`libbrotli1`と`linux-libc-dev`で、Trivy 0.76.1の公開ゲート対象は0件だった。arm64とCIの確認は未完了である。snapshot選択、package差分、変更履歴、検証範囲は[実験記録](../../experiments/2026-11-03-dev-image-security-update.md)に記録した。

Goの `CVE-2026-39824` はx/sys moduleの検出である。公式[Go advisory](https://pkg.go.dev/vuln/GO-2026-5024)の対象OS・symbolと、対象binaryのGOOSを別に確認する。module版が古いという情報だけでLinuxの当該binaryに到達可能な脆弱性があると決めない。

### final image以外の対象

[Dockerfile](../../../docker/msd-dev.Dockerfile)にはGoのactionlint stage、DebianのQEMU build stage、最終msd-dev stageがある。Go builderは1.27.3-trixie、Debian baseはtrixie-slimでdigest固定。固定値確認で各digestを照合するが、最終imageの231件だけで中間stageのAPT・Go module・compilerを網羅したとはいえない。bootstrap時のCA取得とsnapshotからの取得も区別する。

QEMU 11.1.2に対する候補は11.1.3。actionlint 1.7.12、ShellCheck 0.11.0、hadolint 2.15.1、Trivy 0.76.1、Go 1.27.3は今回の比較範囲では同じ。全固定値とbase digestは[取得結果](pinned-versions.md)にある。snapshotの日付が意図どおりであることは、snapshot内のpackageが最新であることを意味しない。

kernel-hardening-checkerはv0.6.17.1、固定commitは `afc376f2a935994793343cfeb05953583cc30191`。upstreamはtagで公開しており、Release APIでの失敗とは別に[tags](https://github.com/a13xp0p0v/kernel-hardening-checker/tags)を照合して同じ安定tagを確認した。tag公開方式をmonitorへ反映する必要がある。

## pipとGo module

最終OCIのpip一覧ではzizmor 1.31.1のみだった。別途、[ロゴ生成用requirements](../../logo/tools/requirements.txt)のfonttools 4.68.0もPyPIの候補と同じだった。Dependabotの監視ディレクトリはそれぞれ別であり、ロゴ生成用packageが標準OCIに入っているとは扱わない。zizmorのwheel内のRust crate、ShellCheck・hadolintの配布binary内の依存は、pip/dpkg/moduleの三一覧だけでは完全に列挙できていない。

actionlintの `go version -m` を読んだ結果は[11 moduleの一覧](actionlint-go-modules.json)にまとめた。module pathごとのGo proxy `@latest` では、例えばx/sysはv0.42.0からv0.49.0、x/syncはv0.20.0からv0.24.0、go.yaml.in/yaml/v4はv4.0.0-rc.3からrc.9という候補があった。pre-releaseをstableと読み替えず、module pathのmajorが変わる候補は別途比較する。依存更新はactionlint upstreamの組み合わせと回帰試験を優先し、監査のためにbinaryを勝手に差し替えない。

## Actionsの再帰的な一覧

workflowの `uses:` からSHAを読み、固定commitのaction.ymlを取得し、compositeの子 `uses:` を再帰的に辿った。8直接参照と3子参照、計11 manifestである。Nodeを使うmanifestの `runs.using` はnode24だった。checkoutやcache等のnameだけでなく、subpathとcommitをキーに重複を判断した。[actions-recursive.json](actions-recursive.json)にmanifestの取得証拠とlockfileのpackage全件がある。

| 参照 | 固定tag相当 | 子参照 |
|---|---|---|
| actions/checkout | v7.0.1 | なし |
| actions/upload-pages-artifact | v5.0.0 | actions/upload-artifact v7.0.0 |
| actions/deploy-pages | v5.0.1 | なし |
| actions/upload-artifact | v7.0.2 | なし |
| actions/cache/restore | v6.1.0 | なし |
| actions/cache/save | v6.1.0 | なし |
| actions/attest-sbom | v4.1.0 | actions/attest v4.1.0 |
| actions/attest-build-provenance | v4.2.2 | actions/attest v4.2.1 |

直接参照は今回見つかった安定releaseと同じ。cacheはreleaseの時刻順の先頭がv5.1.0でも、v6.1.0が存在するため先頭だけを採用しない。子Actionの版が直接参照より古い例もあるが、upstream compositeを当リポジトリで勝手に書き換える提案ではない。

### lockfileと実bundleを分ける

source package-lock.jsonを読むと859 package名、1,574組のname/versionがある。restore/saveの同じlockfile、複数commit、nested node_modulesの重複をそのまま合算して「依存の種類数」にしない。各packageの `dev`、`optional`、license、integrityは取得できた範囲で原値を保存した。

registryの全versionから、pre-releaseを除く数字三つの安定版の最大値と、dist-tag `latest` を別々に読んだ。[全859件の結果](actions-npm-latest.json)にはURL・時刻・応答hash・source_versions・候補・engine・deprecated情報がある。取得失敗は0件、候補の `latest` tagと最大安定版が異なるものが5件、最大安定版にdeprecated記載のあるものが15件だった。tagやdeprecatedの意味はpackageごとに確認する。

lockfileのdev dependencyにはtest・build用もある。反対に実行されるdist/index.jsにはbundledコードが入るため、`dev: false` の抽出だけでも実行範囲を確定できない。今回の一覧を実bundleのSBOMやnpm脆弱性scanと呼ばない。ソース依存を直接当リポジトリで更新するのではなく、Actionの更新判断、upstream advisory、必要なら実bundleの別検査に使う。

## runnerと今後のCI監査

今回のscanログはubuntu-26.04、OS 26.04.1、runner 2.338.2、image版20261025.179.1だった。labelの固定とimageの不変性は別である。[runner-images](https://github.com/actions/runner-images)の一覧・included softwareを参照し、実行ごとのimage版も記録する。runner全体の依存を今回列挙したわけではない。

hadolintとTrivyは開発用OCIとは別のdigest固定containerでも動く。これらの内包package、中間stage、arm64 OCI、wheel/native binary、実bundleは、最終amd64 OCIのscanで全て覆えるとは限らない。GitHub Actionsの全権限、実行条件、cache境界、費用、失敗時通知はこの依存監査とは別に見直す。

再確認する場合は、固定commitのmanifestとlockfileを取り直しhashを照合する。npmのJSONはコードとして実行せずmetadataとして読み、HTTP errorやtimeoutを「最新」と処理しない。APTでは署名・index hash・size・期限を別々に検証し、multiarch名の負の試験を含める。今回の一覧は監視プログラムではなく、取得時点と範囲を固定した監査記録である。

[依存関係の一覧へ戻る](README.md)
