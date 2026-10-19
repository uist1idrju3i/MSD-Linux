# CI とセキュリティレポート

## ワークフロー

| ワークフロー | 実行条件 | 内容と扱い |
|---|---|---|
| `build.yml` | PR、`main` への push、手動実行 | 文書だけの PR では Buildroot ビルドを省略します。`main` への push と手動実行は常にビルドします。ホストテストは毎回実行し、ビルドと QEMU 起動確認はゲートです。 |
| `agent-docs.yml` | PR、`main` への push | エージェント指示ファイルとスキルのシンボリックリンク、および Markdown の文字範囲と検査テストを確認するゲートです。 |
| `pins-check.yml` | 毎週月曜、手動実行 | 固定した Raspberry Pi カーネルと `rpi-6.18.y` の差を報告します。更新の有無では失敗しません。これはブランチ先端との差を調べるもので、カーネル tarball のハッシュ検査ではありません。Dependabot は submodule と GitHub Actions を監視しますが、Buildroot のカーネル tarball hash は追跡しません。 |
| `lint.yml` | PR、`main` への push | actionlint、ShellCheck、zizmor を実行するゲートです。ツールの版と取得物のハッシュを固定します。 |
| `security.yml` | 毎週月曜、手動実行 | Buildroot の defconfig から SBOM と CVE/VEX レポートを作ります。検出した CVE 数では失敗せず、ツールのエラーだけを失敗とします。 |

`build.yml` のホストテスト job は `fdisk`、`e2fsprogs`、`openssl` を導入し、更新処理、hwinfo、p7 拡張の各テストを実行します。Buildroot ビルドの docs-only gate とは独立して実行します。

Buildroot の post-build は、rootfs-overlay の実行スクリプトが使う外部コマンドが target の `bin`、`sbin`、`usr/bin`、`usr/sbin` にあることを確認します。BusyBox applet の symlink も追跡し、`dd`、`sha256sum -c`、`od -A` に必要な機能設定と、fstab の `/proc`、`/sys`、`/run`、`/tmp` の mount 定義も確認します。欠落があればビルドを失敗させます。スクリプトにコマンドや必要な applet 機能を追加する場合は、post-build の一覧も更新します。

`main` の同じ concurrency group では、保留中の実行が後続の実行に置き換わります。文書だけの push もビルドを省略すると、コード変更のビルドが実行されないまま残ることがあるため、`main` への push は常にビルドします。

## Markdown の文字範囲

`agent-docs.yml` は、Git で追跡している Markdown ファイルが JIS X 0213:2004 の範囲内にあるかを検査します。印字可能な ASCII と TAB、改行を除き、公式の対応表にない文字はエラーです。第3・第4水準漢字は表に含まれていても警告し、簡体字の混入がないか確認を促します。`--strict` を指定すると警告も失敗になります。

Python の `euc_jis_2004` などの codec は公式対応表と異なる文字を受理または拒否するため、判定には使いません。検査器は Project X0213 の対応表を同梱し、その SHA-256 を確認してから読み込みます。

```sh
python3 .github/scripts/check-jisx0213.py
python3 .github/scripts/check-jisx0213.py docs/CI.md
```

引数を省略した場合は `git ls-files -z -- '*.md'` が返す追跡済みファイルを検査します。パスを指定した場合はそのファイルだけが対象です。例外は `.github/jisx0213-allowlist.tsv` にタブ区切りの4列で記載し、理由を必ず添えます。

```text
file	<path-or-glob>	*	<reason>
quote	<exact-path>	<characters>	<reason>
```

`file` は一致するファイル内の範囲外文字をすべて許可します。`quote` は指定文字だけを、フェンス付きコードブロック、` {0,3}>` で始まる引用行、またはインラインコード内で許可します。インラインコードは同じ行にある、開始と同じ長さの次のバッククォート列で閉じる扱いです。複数行にまたがるインラインコードは解析しません。使われていない例外は stale としてエラーになります。

同梱表は [Project X0213 の JIS X 0213:2004 対応表](http://x0213.org/codetable/jisx0213-2004-std.txt) から取得しました。取得日は 2026-10-19、SHA-256 は `388ae7822cbf0aecff09b8466dd630ea343673d01a3c7df9d61947ad1ad5b2dd` です。表のライセンス表記には “You can use, modify, distribute this table freely” とあります。

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
