# CI とセキュリティレポート

## ワークフロー

| ワークフロー | 実行条件 | 内容と扱い |
|---|---|---|
| `build.yml` | PR、`main` への push、毎週月曜 03:47 UTC、手動実行 | PR と `main` への push は変更箇所で Buildroot ビルドを絞り、週次と手動実行は常にビルドします。テスト、Buildroot ビルド、QEMU 起動確認は開発用イメージ内で実行し、ビルドと起動確認はゲートです。キャッシュと成果物の受け渡しは runner で行います。 |
| `release-sign.yml` | `main`上の手動実行だけ | 公開鍵だけで構築し、同じcommitとtar hashを確認したEnvironment `release-signing`の別jobでmanifestに署名します。tag・Releaseは作成しません。 |
| `publish-dev-image.yml` | PR（常時）、入力変更を含む `main` push、手動 | PRでは常に`dev-image gate`を実行し、入力差分があれば両archを読取専用jobでbuild・検査します。公開ゲートは修正可能なHIGH/CRITICAL脆弱性とHIGH/CRITICALの秘密情報・設定不備が対象です。push・attestationはmain限定の別jobで実行します。手動の`dry_run`とmain以外の実行は公開しません。 |
| `dev-image-scan.yml` | 開発用OCIの入力変更を含む `main` push、毎週月曜 07:31 UTC、手動実行 | `latest`のindex digestを一度だけ解決し、amd64とarm64を検査します。arch別の選別済みJSONとimage・検査器の情報を保存し、mainでは一つのIssueへ集約します。検出事項では失敗しませんが、片方でも検査失敗・資料欠落なら未確認として失敗します。 |
| `agent-docs.yml` | PR、`main` への push | エージェント指示ファイルとスキルのシンボリックリンク、および追跡テキストの文字範囲と検査テストを確認するゲートです。 |
| `pins-check.yml` | 毎週月曜、手動実行 | 固定したカーネル tarball SHA・系列、Buildroot、Bootlin ツールチェーン、Buildroot のポイントリリース、CI ツール、Trivy、runner を確認し、Dependabot が扱えない更新や確認不能を「固定版の更新確認」Issue に集約します。更新ありは通知のみ、upstream の通信失敗・未照合はjobを失敗させます。 |
| `lint.yml` | PR、`main` への push | actionlint、ShellCheck、zizmor を開発用イメージ内で実行し、hadolint と `docker build --check` で開発用 Dockerfile を検査するゲートです。開発用イメージの lint pin は Dockerfile の固定値を使い、zizmor はオフラインで動かします。hadolint は digest 固定イメージを `docker run` で実行します。 |
| `security.yml` | 全 PR、2時間ごと、手動実行 | OCIでSBOM/VEX/stateを生成し成果物を30日保存。全PRで同一NVD feedのbase/headを比較し、新規修正可能CRITICAL（CVSS v3.x/v4.0が9.0以上）のみ失敗。CVSSv2のみ・修正可否不明は失敗せず、feed鮮度・入力・例外・NVD entryの整合性エラーは失敗。mainの定期・手動実行は「製品SBOMの脆弱性監視」Issueを更新して差分をコメント（自動closeなし）。 |

3系統の通知は共通scriptで処理します。ページ送り、同時実行、失敗時の本文保持、未評価stateの扱いと回帰の範囲は[監視Issueの運用](ci-monitoring.md)を参照してください。

## main の必須チェック

`main`では次のstatus checkを必須にします。

`build`（Buildroot）、`changes`、`lint`、`zizmor`、`check`、`MSD tests in development image`、`dev-image gate`。

最後のcheckはmerge後にmaintainerがrulesetへ追加します。エージェントはrulesetを変更しません。

paths filter付きworkflowは対象外PRでcheckを報告せず、必須にするとmergeを妨げます。PRは常時起動し、入力差分がない場合はbuildを省略します。

merge後にmaintainerが`product CVE scan`をmain rulesetへ追加できます（エージェントは変更しません）。

`check-links.py` は Markdown の相対リンクと HTML の `src`、`href`、`srcset`、見出しアンカーを検査します。URL と例外一覧を除き、`docs/`、`public_html/`、旧 `documentation/` で始まるパスが追跡対象を指していなければ CI を失敗させ、移動後の参照漏れを防ぎます。
`.github/link-check-allowlist.tsv` は他のリポジトリ内のパスに限って使う古いパス検査の例外一覧で、未使用の例外や追跡されていない対象ファイルはエラー扱いです。

## 公開サイト

`public_html/` は Cloudflare Pages で公開するサイト専用です。公開は Cloudflare 側で行い、このリポジトリの GitHub Actions はサイトをデプロイしません。ドメイン `muromi.moe` の DNS と HTTPS 証明書は Cloudflare で管理します。

`agent-docs.yml` が PR と `main` への push で `check-site.py` を実行します。`check-site.py` は `public_html/` に許可したファイルだけがあること、canonical と OGP の URL が `https://muromi.moe` と一致すること、JavaScript の実行や外部資源の読み込みがないこと、ロゴのコピーが `docs/logo/` のマスターと一致することを検査します。許可するのは `index.html`、`404.html`、`site.css` と `images/` 直下の SVG／PNG／WebP です。

## 共通の開発環境とキャッシュ

ローカル開発とCI/CDは、[開発用Docker image](../docker/README.md)と`docker/msd-dev`を共用します。開発hostやrunnerのOS標準版とは独立して、構築・テストに必要なツールの版とパッチを管理するためです。Buildrootが使うtarget用のBootlin toolchainもコンテナー内で取得・使用します。checkout・差分判定・cache管理等はrunner上で行いますが、runner側のcompilerで製品を構築しません。

`build.yml`と`lint.yml`、`release-sign.yml`のbuild jobは共通の開発image準備actionを使います。GHCRに対応する入力タグが公開済みなら、毎回pullとattestation検証を行います。未公開の場合だけ、OS・runner arch・入力タグ・形式版が完全一致するcacheを復元し、archiveのmetadata・サイズ・SHA-256・platformと、load後のimage IDを確認します。認証・通信・pull・検証のエラーを、cacheやローカルbuildへの切替で隠しません。

cacheがなければ同じDockerfileをbuildし、512 MiB以下のarchiveを保存します。初回の独立jobはそれぞれbuildする場合があり、全jobで一回の構築だけを共有する設計ではありません。開発imageのcacheは破損検出を伴う再利用であり、署名やbit単位の再現性の証明ではありません。秘密情報やraw scanは保存せず、PRからmainへのcache移送も行いません。

ccacheはOS・host arch・target・Buildroot revision・開発image入力・defconfigから世代を分け、同じ世代内で復元します。保存keyにrun IDとrun attemptを含め、成功build後だけ保存します。download cacheにもhost archとBuildroot revisionを含め、Buildrootのhash検証は省きません。PRの古いbuild・lint・文書検査は取り消しますが、main・週次・手動を一括で取り消しません。

各 job の末尾では、完了した step の所要時間を `=step-time=`、job 開始時刻や開発用イメージと ccache の状態を `=ci-meta=` として出力します。長いログは閲覧ツールで途中が省略されることがあるため、末尾にも集約し、各 step の時間とキャッシュ状態を確認できるようにします。
build job の `=br-time=` は、Buildroot の `output/build/build-time.log` を step 別の合計と package 別の所要時間上位15件にまとめた値です。

更新・init・hardware情報・data拡張・QEMUログ・電源断ログ・開発imageのhost回帰7組は、一つの開発image内で最大2組ずつ並列実行します。各組のログとCSVは`host-test-results` artifactに保存し、途中で失敗した組があっても他の結果を回収します。一つでも失敗・timeoutならjobを失敗させます。Trivyの公開判定等の既存検査も維持し、これらのテストは製品buildの変更判定にかかわらず毎回実行します。

Buildroot の post-build は、rootfs-overlay の実行スクリプトが使う外部コマンドが target の `bin`、`sbin`、`usr/bin`、`usr/sbin` にあることを確認します。BusyBox applet の symlink も追跡し、`dd`、`sha256sum -c`、`od -A` に必要な機能設定と、fstab の `/proc`、`/sys`、`/run`、`/tmp` の mount 定義も確認します。欠落があればビルドを失敗させる設定です。スクリプトにコマンドや必要な applet 機能を追加する場合は、post-build の一覧も更新します。

## 製品buildの起動条件

`release-sign.yml`はmain上の手動起動専用です。公開鍵だけで構築する`build`と、Environment `release-signing`で承認後にmanifestへ署名する`sign`を分けます。通常の`build.yml`へ本番秘密鍵は渡しません。artifact名、fingerprint、公開前の確認は[署名手順](RELEASE-SIGNING.md)を参照してください。tag・Releaseの自動作成は行いません。

`changes` jobはPR全体の累積差分を調べます。改名は削除と追加として扱い、製品入力を文書側へ移す変更も見落としません。製品directory内のMarkdownは拡張子で除外せず、未知のpath、base/head取得失敗、fetch・diff失敗ではbuildします。週次・手動は常にbuildします。

文書のMarkdown・既知の画像/表等、サイト、エージェント設定、`vendor/yomiyasu`、`LICENSE`、検査専用の`tests/check-*`等は製品buildから除外します。`docs/`全体を無条件には除外せず、既知のロゴ生成script以外の実行script・未知の設定入力はbuildへ倒します。製品入力・workflow・共通action・開発imageのcache helper変更はbuild対象です。正確なpath条件は[build workflow](../.github/workflows/build.yml)、正常系と異常系は[検証記録](experiments/2026-11-03-ci-cache-and-parallel.md)を参照してください。

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

開発用OCIの週次検査は、全件の選別済みJSONを`development-image-findings-amd64`と`development-image-findings-arm64`へ保存します。元のTrivy JSONはアップロードしません。集約Issue、失敗時の扱い、公開jobの権限と受け渡しは[開発用コンテナーのCI運用](../docker/README.md#ociの監視と公開)にまとめます。検出範囲の限界は[開発用OCIの調査](research/operations/development-image-security.md)を参照してください。

公開前の`publish-dev-image.yml`も元のTrivy JSONをartifactへアップロードせず、選別した全件、レポート、image IDと検査器の版、SPDX SBOMを保存します。SBOMそのものの機密情報の有無を確認したという意味ではありません。[GitHub Actionsの監査](research/operations/github-actions-audit.md)に権限・実行条件・監視漏れを記録しています。

`build.yml` の成果物には CycloneDX SBOM とビルド時間ログを含めます。`security.yml` の `product-cve-state` 成果物にはstate、SBOM、VEX JSON、show-infoを保存します。VEX の `analysis.state` は `exploitable`、`resolved`、`resolved_with_pedigree` などの判定です。ジョブサマリーにはコンポーネント別の exploitable 件数、CVSS 上位の CVE、解決済み件数を表示します。CPEがないcomponentは照合対象外になり得るため、検出0件を安全の証明とは扱いません。

`build.yml` のカーネル強化検査は固定した kernel-hardening-checker でビルド後の `.config` と起動コマンドラインを調べます。結果は OK/FAIL 件数と FAIL 項目をジョブサマリーに出し、JSON も成果物として保存します。この検査は報告のみで、結果によってビルドを失敗させません。

`lint.yml` の actionlint と ShellCheck は開発用イメージの Dockerfile ARG で版を固定します。zizmor は `.github/zizmor-requirements.txt` でハッシュ固定し、イメージ内で `--offline` によりワークフローを検査します。ネットワーク監査は実行しません。例外を認める場合は `.github/zizmor.yml` に対象と理由を記録します。

## 固定版の整合性と更新確認

`lint.yml` の `check-pins.py consistency` は、複数箇所に現れる固定値の不一致を PR 時に検査します。対象は、defconfig のカーネル SHA と `linux.hash`、M5 ドライバーのバージョン（`.mk` に SHA を書かず submodule から読むこと）、全 workflow の runner と `.github/actionlint.yaml`、README と `.gitmodules` の Buildroot のバージョン、チェックアウト済み Buildroot における defconfig 選択中の Bootlin ツールチェーンです。毎週の `固定版の更新確認` は upstream の最新版を表にまとめます。Bootlin の新しい安定版は、最新の安定版 Buildroot ブランチが提供しているかも確認します。Buildroot のポイントリリースは、`.gitmodules` の系列に属する最新タグの commit と submodule の gitlink の比較です。「更新あり」か「確認できず」の行があれば、同じ題名の Issue を作るか本文を更新します。「Buildroot 安定版待ち」は情報表示のみで Issue の対象にせず、ほかに対応が必要な行がなければ Issue を閉じます。

## 採用しないツール

| ツール | 採用しない理由 |
|---|---|
| Trivy | Buildroot の rootfs は検査せず、開発用イメージの公開前ゲートと週次検査に使います。 |
| Grype と Syft | Buildroot の VEX を読まず、修正済み CVE を誤検知するため採用しません。 |
| OSV-Scanner | 言語パッケージ向けで、C で構成する Buildroot パッケージには合いません。 |
| cve-bin-tool | 最終リリースが 2024 年 9 月のため採用しません。 |
| OpenSSF Scorecard と harden-runner | 少人数での運用に対して継続管理の負担が大きいため採用しません。 |
| cosign | 開発用イメージには GitHub Actions の attestation を使います。リリース成果物への cosign の導入は別途判断します。 |
