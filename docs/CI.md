# CI とセキュリティレポート

## ワークフロー

| ワークフロー | 実行条件 | 内容と扱い |
|---|---|---|
| `build.yml` | PR、`main` への push、毎週月曜 03:47 UTC、手動実行 | PR と `main` への push は変更箇所で Buildroot ビルドを絞り、週次と手動実行は常にビルドします。テスト、Buildroot ビルド、QEMU 起動確認は開発用イメージ内で実行し、ビルドと起動確認はゲートです。キャッシュと成果物の受け渡しは runner で行います。 |
| `publish-dev-image.yml` | 開発イメージの入力変更を含む PR、`main` への push、手動実行 | PR では amd64 と arm64 のイメージを作成して Trivy で検査します。修正版のある HIGH / CRITICAL の脆弱性と、HIGH / CRITICAL の秘密情報・設定不備を公開ゲートにします。`main` への push と手動実行では GHCR へ公開し、SBOM と provenance の attestation を付けます。手動実行では `dry_run` を有効にすると公開を省けます。 |
| `dev-image-scan.yml` | 毎週月曜 07:31 UTC、手動実行 | GHCR の `latest` を週次で検査し、検出事項を「開発用イメージの脆弱性」Issue に集約します。検出事項では失敗せず、イメージがまだ公開されていない場合も検査を省きます。 |
| `agent-docs.yml` | PR、`main` への push | エージェント指示ファイルとスキルのシンボリックリンク、および追跡テキストの文字範囲と検査テストを確認するゲートです。 |
| `pins-check.yml` | 毎週月曜、手動実行 | 固定したカーネル tarball SHA・系列、Buildroot、Bootlin ツールチェーン、Buildroot のポイントリリース、CI ツール、Trivy、runner を確認し、Dependabot が扱えない更新や確認不能を「固定版の更新確認」Issue に集約します。更新の有無や upstream の通信失敗では失敗しません。 |
| `site-status.yml` | 毎週月曜、手動実行 | GitHub Pages、DNS、ドメイン期限、HTTP リダイレクトを確認し、異常を「公開サイトの状態確認」Issue に集約します。 |
| `lint.yml` | PR、`main` への push | actionlint、ShellCheck、zizmor を開発用イメージ内で実行し、hadolint と `docker build --check` で開発用 Dockerfile を検査するゲートです。開発用イメージの lint pin は Dockerfile の固定値を使い、zizmor はオフラインで動かします。hadolint は digest 固定イメージを `docker run` で実行します。 |
| `pages.yml` | PR と `main` への push で `public_html/`、`docs/logo/`、`check-site.py`、workflow が変わったとき、手動実行 | `check-site.py` と Pages Settings のドメインを照合した後、`public_html/` だけを GitHub Pages に公開します。PR では build job だけを実行し、デプロイは `main` のみで行います。リポジトリにシンボリックリンクがあるため、ブランチからの公開は使いません。 |
| `security.yml` | 毎週月曜、手動実行 | Buildroot の defconfig から SBOM と CVE/VEX レポートを作ります。検出した CVE 数では失敗せず、ツールのエラーだけを失敗とします。 |

`check-links.py` は Markdown の相対リンクと HTML の `src`、`href`、`srcset`、見出しアンカーを検査します。URL と例外一覧を除き、`docs/`、`public_html/`、旧 `documentation/` で始まるパスが追跡対象を指していなければ CI を失敗させ、移動後の参照漏れを防ぎます。
`.github/link-check-allowlist.tsv` は他のリポジトリ内のパスに限って使う古いパス検査の例外一覧で、未使用の例外や追跡されていない対象ファイルはエラー扱いです。

## GitHub Pages サイト

`public_html/` は GitHub Pages で公開するサイト専用です。`pages.yml` は `check-site.py` の検査後、`public_html/` だけを GitHub Pages に公開します。リポジトリにシンボリックリンクがあるため、ブランチからの公開は使いません。GitHub の Settings → Pages では、Source に「GitHub Actions」を選びます。

ドメインは Pages の Settings に保存します。Actions 公開では `CNAME` と `.nojekyll` は不要です。build job は Pages API が返す `cname` を `SITE_ORIGIN` のホスト名と照合してから公開します。PR ではサイト検査、ドメイン照合、成果物の作成まで実行し、デプロイは行いません。`check-site.py` は `public_html/` に許可したファイルだけがあること、canonical と OGP の URL が `https://muromi.moe` と一致すること、JavaScript の実行や外部資源の読み込みがないこと、ロゴのコピーが `docs/logo/` のマスターと一致することを検査します。許可するのは `index.html`、`404.html`、`site.css` と `images/` 直下の SVG／PNG です。

`build.yml` は GHCR にログインして `docker/msd-dev ensure` を実行し、開発用イメージを準備します。タグが公開済みなら pull と attestation 検証を行い、未公開ならローカルビルドに切り替わります。認証、通信、pull、検証のエラーではビルドに切り替えず、job は失敗扱いです。

各 job の末尾では、完了した step の所要時間を `=step-time=`、job 開始時刻や開発用イメージと ccache の状態を `=ci-meta=` として出力します。長いログは閲覧ツールで途中が省略されることがあるため、末尾にも集約し、各 step の時間とキャッシュ状態を確認できるようにします。

更新処理、hwinfo、p7 拡張、開発イメージのタグ、Trivy の公開判定を含むテストと Buildroot/QEMU の処理はイメージ内で実行します。テストは Buildroot ビルドの docs-only 判定にかかわらず毎回実行されます。

Buildroot の post-build は、rootfs-overlay の実行スクリプトが使う外部コマンドが target の `bin`、`sbin`、`usr/bin`、`usr/sbin` にあることを確認します。BusyBox applet の symlink も追跡し、`dd`、`sha256sum -c`、`od -A` に必要な機能設定と、fstab の `/proc`、`/sys`、`/run`、`/tmp` の mount 定義も確認します。欠落があればビルドを失敗させる設定です。スクリプトにコマンドや必要な applet 機能を追加する場合は、post-build の一覧も更新します。

Buildroot ビルドは時間がかかるため、`changes` job は PR と `main` への push で変更ファイルを見て、必要な場合だけビルドを実行します。文書（`*.md`、`docs/`）、サイト（`public_html/`）、エージェント設定（`.agents/`、`.claude/`、`.devin/`）、`vendor/yomiyasu`、`LICENSE`、検査専用の `tests/check-*` はスキップ対象です。`.github/` 配下も `build.yml` 自身を除いて対象から外します。それ以外のファイルに変更があれば Buildroot のビルド対象です。開発用イメージ内のテストは変更判定と独立して毎回実行します。

`main` への文書だけの push ではビルドを省略するため、最新のビルド成果物は過去の commit に対応したままです。新しい `main` の成果物が必要な場合は `workflow_dispatch` で手動実行してください。毎週月曜 03:47 UTC のビルドは、ダウンロード URL や runner image の変化を検出するために実行します。

## 追跡テキストの文字範囲

`agent-docs.yml` は、Git で追跡しているテキストファイルが JIS X 0213:2004 の範囲内にあるかを検査します。印字可能な ASCII と TAB、改行を除き、公式の対応表にない文字はエラーです。第3・第4水準漢字は表に含まれていても警告し、簡体字の混入がないか確認を促します。`--strict` を指定すると警告も失敗になります。

Python の `euc_jis_2004` などの codec は公式対応表と異なる文字を受理または拒否するため、判定には使いません。検査器は Project X0213 の対応表を同梱し、その SHA-256 を確認してから読み込みます。

```sh
python3 .github/scripts/check-jisx0213.py
python3 .github/scripts/check-jisx0213.py docs/CI.md
```

引数を省略した場合は `git ls-files -z` が返す追跡済みファイルを検査します。シンボリックリンク、先頭 8 KiB に NUL byte を含むバイナリファイル、および対応表 `.github/scripts/data/jisx0213-2004-std.txt` は対象外です。submodule の gitlink は通常ファイルではないため対象外です。バイナリ判定を通ったファイルの UTF-8 エラーは検査エラーになります。パスを指定した場合はそのファイルだけが対象です。例外は `.github/jisx0213-allowlist.tsv` にタブ区切りの4列で記載し、理由を必ず添えます。

```text
file	<path-or-glob>	*	<reason>
quote	<exact-path>	<characters>	<reason>
```

`file` は一致するファイル内の範囲外文字をすべて許可します。`quote` は Markdown（`.md`）だけで有効で、指定文字をフェンス付きコードブロック、` {0,3}>` で始まる引用行、またはインラインコード内で許可します。Markdown 以外のファイルでは `quote` は適用されません。インラインコードは同じ行にある、開始と同じ長さの次のバッククォート列で閉じる扱いです。複数行にまたがるインラインコードは解析しません。使われていない例外は stale としてエラーになります。

同梱表は [Project X0213 の JIS X 0213:2004 対応表](http://x0213.org/codetable/jisx0213-2004-std.txt) から取得しました。取得日は 2026-10-19、SHA-256 は `388ae7822cbf0aecff09b8466dd630ea343673d01a3c7df9d61947ad1ad5b2dd` です。表のライセンス表記には “You can use, modify, distribute this table freely” とあります。

## ローカル検証と runner の注意

- 【CI で判明】`ubuntu-26.04` runner label は actionlint が認識しない時点がありました。runner image の preview 期間中は GitHub Actions で実際に job が開始できるかを確認します。label が queue されたままの場合、runner を独断で変更せず判断を依頼します。https://github.com/actions/runner-images
- 【環境固有】Devin VM は `no new privileges` 制約により sudo でホスト依存を追加できません。`sudo: The "no new privileges" flag is set, which prevents sudo from running as root.` が出た場合、この環境でのホスト依存追加と QEMU 実行はブロックされます。Buildroot / QEMU 検証は依存導入済みホストまたは CI で実施します。
- `board/cardputerzero/post-image.sh` の genimage `--rootpath` は **CI で判明し修正済み（#9）** です。
- `package/m5stack-cardputerzero/m5stack-cardputerzero.mk` は `KCFLAGS="$(LINUX_CFLAGS) -DCONFIG_CARDPUTERO_V0_5=1"` を指定し、`LINUX_MAKE_FLAGS` のコンパイラフラグを保ったまま基板の define を追加します。Buildroot は `LINUX_MAKE_FLAGS` の後に `MODULE_MAKE_OPTS` を渡すため、後者の `KCFLAGS` が前者を置き換えてもフラグは維持されます。
- QEMU の標準設定は `raspi3ap`（512 MiB、CM0 DTB）です。起動には ASB パッチを含む開発用イメージ内の QEMU が必要です。1 GiB の `raspi3b` と Pi 3 DTB は `QEMU_MACHINE=raspi3b` で選べます。QEMU では BCM2837 相当の起動、UART、init、SquashFS/ext4、ユーザー空間 A/B ロジックを検証できます。GPU firmware / tryboot、LCD、M5 I2C、実機起動時間は検証できません。[QEMU の検証範囲](BUILD.md#qemu-での起動確認)

## SBOM、VEX、カーネル設定

`build.yml` の成果物には CycloneDX SBOM とビルド時間ログを含めます。`security.yml` の `buildroot-security-report` 成果物には SBOM と VEX JSON を保存します。VEX の `analysis.state` は `exploitable`、`resolved`、`resolved_with_pedigree` などの判定です。ジョブサマリーにはコンポーネント別の exploitable 件数、CVSS 上位の CVE、解決済み件数を表示します。

`build.yml` のカーネル強化検査は固定した kernel-hardening-checker でビルド後の `.config` と起動コマンドラインを調べます。結果は OK/FAIL 件数と FAIL 項目をジョブサマリーに出し、JSON も成果物として保存します。この検査は報告のみで、結果によってビルドを失敗させません。

`lint.yml` の actionlint と ShellCheck は開発用イメージの Dockerfile ARG で版を固定します。zizmor は `.github/zizmor-requirements.txt` でハッシュ固定し、イメージ内で `--offline` によりワークフローを検査します。ネットワーク監査は実行しません。例外を認める場合は `.github/zizmor.yml` に対象と理由を記録します。

## 固定版の整合性と更新確認

`lint.yml` の `check-pins.py consistency` は、複数箇所に現れる固定値の不一致を PR 時に検査します。対象は、defconfig のカーネル SHA と `linux.hash`、M5 ドライバーの版（`.mk` に SHA を書かず submodule から読むこと）、全 workflow の runner と `.github/actionlint.yaml`、README と `.gitmodules` の Buildroot の版、チェックアウト済み Buildroot における defconfig 選択中の Bootlin ツールチェーンです。毎週の `固定版の更新確認` は upstream の最新版を表にまとめます。Bootlin の新しい安定版は、最新の安定版 Buildroot ブランチが提供しているかも確認します。Buildroot のポイントリリースは、`.gitmodules` の系列に属する最新タグの commit と submodule の gitlink の比較です。「更新あり」か「確認できず」の行があれば、同じ題名の Issue を作るか本文を更新します。「Buildroot 安定版待ち」は情報表示のみで Issue の対象にせず、ほかに対応が必要な行がなければ Issue を閉じます。

## 公開サイトの状態確認

`site-status.yml` は Pages API の独自ドメイン、HTTPS 強制、証明書の状態・対象ドメイン・残り日数を確認します。DNS は `1.1.1.1` と `8.8.8.8` の回答を `.github/site-dns.tsv` と照合し、ワイルドカード回答の有無も検査対象です。IANA の RDAP 登録情報で得たドメイン期限は、残り 60 日以上が合格条件です。HTTP と HTTPS の応答およびリダイレクト先を検査します。証明書の残り日数は 14 日以上が基準です。

異常があれば「公開サイトの状態確認」Issue を作成するか本文を更新します。すべて正常になった後の実行では、開いている Issue にコメントを付けて閉じます。DNS を意図的に変更したときは、期待値を `.github/site-dns.tsv` に反映してください。

## 採用しないツール

| ツール | 採用しない理由 |
|---|---|
| Trivy | Buildroot の rootfs は検査せず、開発用イメージの公開前ゲートと週次検査に使います。 |
| Grype と Syft | Buildroot の VEX を読まず、修正済み CVE を誤検知するため採用しません。 |
| OSV-Scanner | 言語パッケージ向けで、C で構成する Buildroot パッケージには合いません。 |
| cve-bin-tool | 最終リリースが 2024 年 9 月のため採用しません。 |
| OpenSSF Scorecard と harden-runner | 少人数での運用に対して継続管理の負担が大きいため採用しません。 |
| cosign | 開発用イメージには GitHub Actions の attestation を使います。リリース成果物への cosign の導入は別途判断します。 |
