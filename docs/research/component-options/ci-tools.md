# OCI・CIツールの設定と監視

[調査の入口](README.md)へ戻る。

## 231 APT packageと直接導入するtool

[APTの設定面の台帳](apt-surfaces.csv)は、固定した開発用OCIの231 packageについて、版、機能概要、upstream、実在する実行file・`/etc` file・manual pathを記録する。83 packageに実行file、35 packageに設定fileがあり、slim imageの中にはmanual fileは残っていなかった。packageにCLIがないことと、調整項目がないことは異なる。

APTのfile一覧はsystem imageの全設定ではない。直接導入するbinary、pip、Go module、QEMUのbuild/runtime library、GitHub Actionsの同梱コード、runnerの既存tool、Buildrootが生成するhost toolも別に確認する。[依存一覧・最新版・監視の監査](https://github.com/uist1idrju3i/MSD-Linux/pull/184)と[Actions境界の監査](https://github.com/uist1idrju3i/MSD-Linux/pull/185)に対応し、ここでは設定面を扱う。

| 対象 | 主な設定・引数 | 現行の確認経路と候補・背反 |
|---|---|---|
| OCI/Docker | base digest、stage、ARG/ENV、USER、mount、network、cache、secret、platform、provenance | Dockerfileとwrapper、最終imageの実体を照合する。intermediate stageとruntime bundleを最終APT一覧だけで済ませない |
| QEMU | buildのtarget/backend/features、実行時のmachine・CPU・RAM・SD・console・network・watchdog・monitor | 固定11.1.2。default試験はraspi3ap。machineの対応と実機のfirmware・I2C等の再現を分ける。不要backend削減は診断能力とbuild費用との比較 |
| actionlint・Go | 対象workflow、shellcheck等との連携、出力・除外、Go buildのCGO・toolchain・trimpath・ldflags | actionlint 1.7.12。Dockerfileは`CGO_ENABLED=0 GOTOOLCHAIN=local GOFLAGS=-trimpath`、`-ldflags='-s -w'`を指定。hostのGoへ暗黙更新しない |
| ShellCheck | dialect、severity、source探索、外部source、出力format、除外code | 0.11.0。追跡scriptの選定も検査範囲の一部。誤検出の個別説明なしにseverityを下げない |
| zizmor | offline、format、対象workflow、監査条件・除外 | requirementsとhashで固定。offline検査とGitHub側の権限設定・実行時の信頼境界は別 |
| Trivy | scanner、vuln type、severity、DB、ignore-unfixed、ignore policy、exit code、format、timeout | 0.76.1のimage digestを固定。SPDX出力とvulnerability scanは別の実行。検出器、公開する情報、blocking判定を分離する |
| kernel-hardening-checker | kernel config、cmdline、sysctl、出力・mode | toolの提案をCPU・運用・費用・kernel固定版で検討する。全提案への機械的一致を製品の安全性としない |
| Python・pip | interpreter、venv、requirements/hash、index、build isolation、cache、環境変数 | direct/transitive依存と生成wheelを区別。単なるversion一覧ではnative libraryやbundleを覆わない |
| CMake・Ninja・Make | generator、cache、cross/toolchain file、buildtype、jobs、install先 | Buildroot内とOCI内で版が異なり得る。configureの自動検出がhost依存にならないか確認する |
| Git・GitHub CLI・curl等 | ref/commit、credential、protocol、redirect、retry、timeout、TLSとCA | 資格情報を必要な送信先だけへ渡す。任意URLへのtoken転送やログへの秘密値出力をしない |
| GitHub Actions | manifestのinputs、env、permissions、if、shell、timeout、concurrency、cache/artifact、実行主体 | 最上位のSHA pinだけでnested actionやbundle全体を固定したとしない。`uses`のソースと同梱`dist`の一致も別問題 |
| runner | label、OS/arch、同梱tool、更新頻度、権限 | `ubuntu-26.04`等のlabelはimage digest固定ではない。毎回のimage versionと実tool versionを証拠へ残す |

固定OCIのhelpを採取しても、別revisionでbuildしたOCIやGitHub hosted runnerの既定値は確認したことにならない。対象image、command、終了状態、出力hashを[採取記録](reproduction.md)で分ける。

## 優先する改善候補

- 設定値の更新だけでなく、CLIの破壊的変更、既定値の変更、runtime廃止、runner更新を監視する。上流の全major比較と、製品が採用できる系列は別の判定にする。
- scan・build・reportの取得失敗を成功にしない。pipelineの末尾だけで成否を判断せず、実workflow stepと壊した模擬入力の回帰試験を行う。
- secret検出の生の値をartifactへ出さない。検出ID・分類・位置等の公開可能な情報と、秘匿すべき内容を選別する。
- host/target、各OCI stage、bundle、SDK、SBOM、最終imageの母集団を対応づける。記録が存在しないものを「検出なし」と集計しない。

これらは監視範囲と失敗の扱いの改善であり、既知のBrotli検出を除外する理由にはならない。修正版導入は利用者の指定で延期しており、gateを緩めない。

## 根拠

- [開発用Dockerfile](../../../docker/msd-dev.Dockerfile)、[wrapper](../../../docker/msd-dev)、[依存監視の設定](../../../.github/dependabot.yml)、[版の固定値を読む検査](../../../.github/scripts/check-pins.py)
- [QEMUの試験仕様](../../BUILD.md#qemu-での起動確認)、[OCIの脆弱性と監視](../operations/development-image-security.md)、[SBOMの範囲](../operations/sbom-coverage.md)
- [各packageのmetadataとfile一覧](apt-surfaces.csv)。help・manual・sourceは版を合わせて参照する。全APT libraryに独立CLIがあるとはしない。
