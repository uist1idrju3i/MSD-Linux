# 依存関係の一覧と監視範囲

## 結論と読み方

2026-11-02 UTCに、通常ビルドのSBOM、開発用OCI、GitHub Actionsのソース依存を照合した。最新版の候補を見つける調査であり、依存の更新や安全性の保証ではない。Brotliの修正版導入は今回の対象から外し、検出と監視を残す。

| 知りたいこと | 本文・全件の一覧 |
|---|---|
| 製品とビルドに使うpackage、外部toolchainの内包物、版と許諾 | [Buildrootとtoolchain](buildroot.md)、[67件のCSV](buildroot-packages.csv)、[出典・CPE・licenseを含むJSON](buildroot-packages.json) |
| OCI、Actions、Go、pip、runnerと監視漏れ | [開発環境・CI](development-and-ci.md) |
| OpenSSLの固定版・上流保守期限と週次通知の追加 | [OpenSSL保守監視](openssl-maintenance.md) |
| Debianの各packageの導入版と更新候補 | [231件のCSV](development-apt.csv)、[署名・indexの証拠を含むJSON](development-apt.json) |
| Actionsから呼ばれる子Actionとnpm依存 | [11 manifestとlockfile](actions-recursive.json)、[859 package名の最新版照合](actions-npm-latest.json) |
| actionlint binary内のGo module | [11 moduleの照合](actionlint-go-modules.json) |
| 固定値とupstreamの一次資料 | [固定値確認の取得結果](pinned-versions.md)、[packageごとの取得記録](upstream-checks.json)、[CI・入力hash・追加資料](source-record.json) |
| 一覧の構造と検査結果 | [検証記録と再照合コマンド](validation.md)、[68レコードの依存関係](buildroot-dependencies.json) |

一覧に記載する版は読みやすいように一律に変換せず、tag、commit、Debian版、module版を区別して残した。`latest_observed` は指定した資料と範囲で見つかった候補であり、採用可能版とは限らない。`same` も、その比較範囲内で同じという意味である。

## 2026-11-12の現況

基準は`main`の`1ffccae4d0ed5c2a3dc9ccc03cee4fbb46865169`です。以下の確認表、監視表、優先差分は11月2日の調査を残したものです。現況は次のとおりです。

- 製品SBOMのCVE監視は[security.yml](../../../.github/workflows/security.yml)で2時間ごとに実行する設定です。mainの定期・手動実行ではIssueを更新し、PRでは新規の修正可能CRITICALをgateで判定します。下表の「週次security」と、通知をartifactだけで終えないという改善案は当時の記述です。取得失敗・未照合を追う通知、CPEなし・別名・backport等の扱いは残ります。
- kernel-hardening-checkerのtag取得は[固定版チェッカー](../../../.github/scripts/check-pins.py)へ反映済みです。下記の優先差分1は実装済みで、全依存の監視完了を示すものではありません。
- host/targetのOpenSSLは外部overrideで3.5.9 LTSへ変更済みです。[保守判断](openssl-maintenance.md)のとおり、3.5.10とBuildrootの段階更新は別作業です。
- 冒頭のBrotli修正除外も11月2日の調査範囲です。その後のR25でOCIを更新し、両archのgate・SBOM attestation等の成功を[後続の確認](development-and-ci.md#scannerの結果と延期した修正)に記録済みです。公開ゲートは維持します。
- Actionsの旧11参照・859 npm名は当時の母集団です。現行workflowの直接参照は外部6参照とローカルAction 1参照で、現行の再帰的な母集団と実bundleは再監査していません。詳細は[開発環境・CIの現況](development-and-ci.md#2026-11-12の現況)を参照してください。

## 今回確認した範囲

2026-11-12のR24追加対応：3監視のIssue検索を全ページ送りへ改め、定期・手動実行を同じ監視のconcurrency groupで直列化しました。作成前にも再検索します。取得・走査・照合の失敗はIssueとsummaryへ未確認と通知し、jobを失敗させます。固定版の「確認できず」も終了値2です。以前の現況にある失敗通知の残件のうち、この3系統の到達可能な経路を扱う変更です。[実装と回帰の範囲](../../CI.md#監視issueの更新と失敗)を別記し、以下の当時の表は保持します。CPEのない内包物、別名・backportの網羅、GitHub上での同時実行と通知の実動作は未確認です。

| 層 | 確認結果 | 限界 |
|---|---|---|
| 通常ビルドのSBOM | 67 component、target 18、host 49。68 dependencyレコード、267本の参照。実artifactと生成元show-infoを既存検査で再照合し一致 | package単位の情報であり、配布ファイルの独立走査ではない |
| Buildroot内包package | 32 componentに新しい版の候補、26件は比較範囲内で同じ、7件は独立版のない内部package、1件はDebian側の候補、1件はfirmwareのcommit差 | target/hostの同名packageを含む。32件は32製品や32件の脆弱性という意味ではない |
| 最終開発用OCIのAPT | amd64の231件をtrixie、trixie-updates、trixie-securityと照合。228件同一、3件に新しい配布版 | Debianの保守系列内の比較。各sourceのupstream最新版とは別。arm64と中間stageは含まない |
| 最終OCIのpip | zizmor 1.31.1。ロゴ生成用fonttools 4.68.0は別のrequirements | wheel内部のRust crateや全native依存までpip一覧で説明できるわけではない |
| Actions | 直接8参照と子3参照を、固定commitのmanifestまで再帰照合 | 同じrepositoryの異なるsubpath・commitは別の参照 |
| npm | 上記ソースlockfileの859 package名、1,574組のname/version。全859名をregistryと照合 | dev/optionalを含むソース一覧であり、実際のbundled JavaScriptの一覧ではない |
| actionlint | Go binaryのmodule情報から依存11件を照合 | Go標準ライブラリーはcompiler版とも対応する。将来の別major module pathまでの比較ではない |

## 監視の差分

| 対象 | 版の自動監視 | 脆弱性の自動監視 | 残る差分 |
|---|---|---|---|
| Buildroot、M5 overlay、yomiyasuのsubmodule | Dependabot。Buildroot系列は固定値確認も実行 | Buildrootの選択packageはSBOMをNVDと照合 | submodule更新だけでは全内包packageの最新版を個別に知らせない |
| target/host package | Buildroot更新へ間接的に追従 | 週次securityでCPE照合・VEX生成 | CPEなし、unknown license、外部toolchain内包物、別名・backportの判断が残る。VEXのartifact保存とIssueによる通知も別 |
| 最終開発用OCI | base digestとtool固定値を監視 | 固定digestを週次Trivy scan、[Issue #59](https://github.com/uist1idrju3i/MSD-Linux/issues/59)で通知 | snapshot内の231件ごとの新しい配布版や、中間stageを同じ方法では監視していない |
| Actionsの直接参照 | Dependabot | GitHub側のadvisoryとworkflow静的検査 | 子Action、npm lockfile、実bundleの内包物を当リポジトリのDependabotが直接更新するわけではない |
| pip requirements | Dependabot | OCIに入るzizmorはTrivy検出範囲 | ロゴ生成用環境、wheel内のnative依存は別途確認が必要 |
| Go module | actionlintの版更新へ間接追従 | OCI内のGo binaryをTrivyで検出 | packageの存在と、Linuxで脆弱な処理を呼ぶことを区別する |
| runner | labelの固定値確認 | GitHub管理環境 | labelはimmutableなimage digestではない。全同梱ソフトのSBOMや最新版監視を本調査で作ったわけではない |

実際の設定は[Dependabot](../../../.github/dependabot.yml)、[固定値確認](../../../.github/workflows/pins-check.yml)、[Buildroot security](../../../.github/workflows/security.yml)にある。固定値確認は[Issue #112](https://github.com/uist1idrju3i/MSD-Linux/issues/112)に集約する。表は監視設定の範囲であり、未検出を安全性の証明には使わない。

## 優先して埋める差分

1. kernel-hardening-checkerのtag公開方式に版監視を合わせる。Release APIが404でも「最新」と扱わない。
2. BuildrootのCVE報告をartifactだけで終わらせず、取得失敗・未照合・要調査も追える通知にする。
3. 外部toolchainのGCC・binutils・glibc・GDBと配布許諾を、toolchain一件のSBOMから分離して追跡する。
4. OCIの最終stageと中間stage、Actionsのソースlockfileと実bundleを別の対象として管理する。ツールの追加前に、既存のSBOMとTrivyで得られる情報を再利用する。
5. 自動監視を増やす前に、同名package、tagのみの公開、pre-release、backport、取得失敗、期限切れmetadataの負の試験を用意する。

これらは提案であり、この一覧追加で監視機能を全て実装したわけではない。代替技術、設定項目、CI全体の権限と費用の検討は別の調査へ引き継ぐ。

[調査の索引へ戻る](../../../RESEARCH.md)
