# CI とセキュリティレポート

## ワークフロー

| ワークフロー | 実行条件 | 内容と扱い |
|---|---|---|
| `build.yml` | PR、`main` への push、手動実行 | 変更ファイルを確認し、文書だけの変更では Buildroot ビルドを省きます。`msd-update` のテストは毎回実行します。ビルドと QEMU 起動確認はゲートです。 |
| `agent-docs.yml` | PR、`main` への push | エージェント指示ファイルとスキルのシンボリックリンクを検査するゲートです。 |
| `pins-check.yml` | 毎週月曜、手動実行 | 固定した Raspberry Pi カーネルと `rpi-6.18.y` の差を報告します。更新の有無では失敗しません。これはブランチ先端との差を調べるもので、カーネル tarball のハッシュ検査ではありません。Dependabot は submodule と GitHub Actions を監視しますが、Buildroot のカーネル tarball hash は追跡しません。 |
| `lint.yml` | PR、`main` への push | actionlint、ShellCheck、zizmor を実行するゲートです。ツールの版と取得物のハッシュを固定します。 |
| `security.yml` | 毎週月曜、手動実行 | Buildroot の defconfig から SBOM と CVE/VEX レポートを作ります。検出した CVE 数では失敗せず、ツールのエラーだけを失敗とします。 |

## ローカル検証と runner の注意

- 【CI で判明】`ubuntu-26.04` runner label は actionlint が認識しない時点がありました。runner image の preview 期間中は GitHub Actions で実際に job が開始できるかを確認します。label が queue されたままの場合、runner を独断で変更せず判断を依頼します。https://github.com/actions/runner-images
- 【環境固有】Devin VM は `no new privileges` 制約により sudo でホスト依存を追加できません。`sudo: The "no new privileges" flag is set, which prevents sudo from running as root.` が出た場合、この環境でのホスト依存追加と QEMU 実行はブロックされます。Buildroot / QEMU 検証は依存導入済みホストまたは CI で実施します。
- `board/cardputerzero/post-image.sh` の genimage `--rootpath` は **CI で判明し修正済み（#9）** です。
- `package/m5stack-cardputerzero/m5stack-cardputerzero.mk` は `KCFLAGS="$(LINUX_CFLAGS) -DCONFIG_CARDPUTERO_V0_5=1"` を指定し、`LINUX_MAKE_FLAGS` のコンパイラフラグを保ったまま基板の define を追加します。Buildroot は `LINUX_MAKE_FLAGS` の後に `MODULE_MAKE_OPTS` を渡すため、後者の `KCFLAGS` が前者を置き換えてもフラグは維持されます。
- QEMU の `raspi3b` は BCM2837 相当の起動、UART、init、SquashFS/ext4、ユーザー空間 A/B ロジックを検証できます。GPU firmware / tryboot、LCD、M5 I2C、実機起動時間は検証できません。[QEMU の検証範囲](BUILD.md#qemu-での起動確認)

## SBOM、VEX、カーネル設定

`build.yml` の成果物には CycloneDX SBOM とビルド時間ログを含めます。`security.yml` の `buildroot-security-report` 成果物には SBOM と VEX JSON を保存します。VEX の `analysis.state` は `exploitable`、`resolved`、`resolved_with_pedigree` などの判定です。ジョブサマリーにはコンポーネント別の exploitable 件数、CVSS 上位の CVE、解決済み件数を表示します。

`build.yml` のカーネル強化検査は固定した kernel-hardening-checker でビルド後の `.config` と起動コマンドラインを調べます。結果は OK/FAIL 件数と FAIL 項目をジョブサマリーに出し、JSON も成果物として保存します。この検査は報告のみで、結果によってビルドを失敗させません。

`lint.yml` の zizmor は `1.31.1` をハッシュ固定してインストールする監査ツールです。CI では `--offline` でワークフローを検査し、結果で合否を決めます。ネットワーク監査は実行しません。例外を認める場合は `.github/zizmor.yml` に対象と理由を記録します。

## 採用しないツール

| ツール | 採用しない理由 |
|---|---|
| Trivy | Buildroot の rootfs から OS パッケージを検出しにくく、設定検査の対象もありません。secret 検査は GitHub の secret scanning と重なり、最近の配布物侵害も踏まえて採用しません。 |
| Grype と Syft | Buildroot の VEX を読まず、修正済み CVE を誤検知するため採用しません。 |
| OSV-Scanner | 言語パッケージ向けで、C で構成する Buildroot パッケージには合いません。 |
| cve-bin-tool | 最終リリースが 2024 年 9 月のため採用しません。 |
| OpenSSF Scorecard と harden-runner | 少人数での運用に対して継続管理の負担が大きいため採用しません。 |
| artifact attestation と cosign | リリースワークフローを整備するときに導入します。 |
