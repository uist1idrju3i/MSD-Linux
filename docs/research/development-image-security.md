# 開発用OCIの脆弱性と監視の確認

[RESEARCH](../../RESEARCH.md) / [CIの運用](../CI.md)

## 対象と確認の限界

開発用OCIと、CardputerZeroへ配布するBuildrootのrootfsは別の検査対象です。この記録のTrivyの件数を、配布OSの脆弱性件数とは扱いません。

2026-11-02の[週次検査](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41466543726)と[追跡Issue](https://github.com/uist1idrju3i/MSD-Linux/issues/59)を読み、固定したOCIをローカルで再検査しました。修正版の導入を確認した記録ではありません。

| 項目 | 確認値 |
|---|---|
| OCIの参照 | `ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77` |
| 基準のリポジトリcommit | `916a45e80545fb5ecf3546873ce332093b0501f2` |
| Trivy | `0.76.1`、`sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c` |
| DB | version 2、UpdatedAt `2026-11-02T13:15:56.441126560Z` |
| 検出されたOSとpackage数 | Debian 13.7、231個 |
| 脆弱性 | OSの2183件とGo binaryの1件、計2184件 |
| 公開ゲートの基準に当たる脆弱性 | 1件 |
| ローカル再検査のscanner | `vuln`のみ。秘密情報と設定不備は再検査していない |
| 週次検査のscanner | `vuln,secret,misconfig`。秘密情報0件、設定不備0件と報告 |

同じOCIとTrivyの版でも、DBが更新されると件数は変わります。これは走査と報告経路の確認を各1回行った記録であり、性能や統計的な再現性の測定ではありません。

## Brotliの修正がある検出

`libbrotli1`の`1.1.0-2+b7`に、`CVE-2026-111497`が検出されました。Trivyの重大度はNVD由来のCRITICALです。[Debian Security Tracker](https://security-tracker.debian.org/tracker/CVE-2026-111497)でも、trixieの`1.1.0-2`はvulnerable、trixie-securityの`1.1.0-2+deb13u1`はfixedと確認しました。Brotli decoderの不正な圧縮入力の処理に関する修正です。開発環境での具体的な攻撃到達性や、悪用の成立は試していません。

現行のDockerfileはDebian snapshotを`20261019T190000Z`に固定しています。再現可能な取得先を保つことと、固定後のセキュリティ修正を取り込むことは別の要件です。更新検知だけでなく、修正版を含むsnapshot・base imageと生成後のpackage版を確認する必要があります。

修正方法の比較ではsnapshot全体の更新を基本候補とします。Brotliだけの追加取得は変更範囲を絞れますが、取得先・署名またはhash・依存解決・版の監視を二重管理します。全体更新では実際に変わる全packageの変更履歴、QEMUの構築・実行、Buildrootの構築、ライセンスと再走査を比較します。snapshotの日付を変えただけで、修正版の導入が済んだとは判定しません。

この検出がtarget rootfsにも当たるかは、target/hostを分けた依存一覧と最終rootfsで調べます。開発用OCIの結果だけで、配布OSも影響を受ける、または影響がないとは断定しません。

## Goの版照合と適用範囲

もう1件はactionlintに含まれる`golang.org/x/sys v0.42.0`の`CVE-2026-39824`です。Trivyは修正版を`0.44.0`、重大度をUNKNOWNと報告しました。[Go公式のアドバイザリ](https://pkg.go.dev/vuln/GO-2026-5024)は`golang.org/x/sys/windows`の`NewNTUnicodeString`を対象としています。

OCIから取り出したactionlintのbuild情報は`GOOS=linux`でした。moduleの版が該当することと、このLinux binaryで対象のコードが実行されることは区別します。この確認だけで検出を非表示にしたり、一般的な除外規則を追加したりはしません。

## 見つかった報告経路の欠落と改修

従来の報告は入力順の先頭100件だけをIssueとjob summaryに載せていました。今回のBrotliの検出はその範囲から外れ、件数欄の「公開ゲート対象1件」に対応する詳細を本文から読めませんでした。全件のartifactも保存していませんでした。

次のように改修します。

- 公開ゲート対象を先に、各群の中では重大度の高い順に表示します。本文の上限100件は維持し、省略件数を示します。
- `trivy-gate.py --findings-json`で、全件の分類・識別子・対象・重大度・installed/fixed versionと、公開ゲート対象の一覧を保存します。
- 秘密情報の`Match`、`Code`、任意の診断`Message`、imageの環境変数を含む元JSONは公開しません。保存するのは、検査器が選び直した項目だけです。
- 週次workflowは`development-image-findings` artifactに、全件JSON、本文、OCIのimage ID・RepoDigests・platform、TrivyとDBの版情報を保存します。
- mutableな`latest`はpullした後でimage IDへ解決し、そのIDから保存・検査します。後から変わるタグだけを証拠にしません。

公開前ゲートの基準は変えません。修正版のあるHIGH/CRITICALの脆弱性と、HIGH/CRITICALの秘密情報・設定不備を対象にします。週次の報告は検出事項だけでは失敗させず、Issueに集約する現行の運用を保ちます。秘密情報の値を出さないことは、生成物の全ファイルに秘密情報がないことの証明ではありません。

回帰テストでは120件のLOWの後ろにHIGH/CRITICALを置き、重要項目が本文に残ること、100件を超えた残りもJSONに保存することを確認します。秘密値を模した文字列を`Match`、`Code`、環境変数、診断文へ入れ、本文と保存JSONに出ないことも検査します。ローカルの実データでは、改修後の本文の先頭にBrotliの検出が表示されました。入力hashと報告器の5回のA/A試行は[確認記録](../experiments/2026-11-02-dev-image-scan.md)に残します。新しいworkflowの実行結果とは区別します。

## 再検査の手順

リポジトリのルートで実行します。出力先には走査結果とimageのtarを置き、コミットしません。ここでは脆弱性だけを検査します。秘密情報の元JSONを含む走査を行う場合、その元JSONを共有しないでください。

```sh
image=ghcr.io/uist1idrju3i/msd-dev@sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77
trivy=ghcr.io/aquasecurity/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
out="$PWD/output-trivy-audit"
umask 077
mkdir -p "$out/trivy-cache"
docker pull --platform linux/amd64 "$image"
docker save --output "$out/msd-dev.tar" "$image"
docker run --rm --volume "$out:/work" \
  --volume "$out/trivy-cache:/root/.cache/trivy" "$trivy" \
  image --input /work/msd-dev.tar --scanners vuln \
  --format json --output /work/trivy.json
docker run --rm --volume "$out/trivy-cache:/root/.cache/trivy" \
  "$trivy" --version > "$out/trivy-version.txt"
python3 .github/scripts/trivy-gate.py report "$out/trivy.json" \
  --findings-json "$out/trivy-findings.json" > "$out/report.md"
tests/trivy-gate/run.sh
```

この調査で、Cから手動構築したQEMUや外部toolchainの内包物まで、Trivyがすべて認識すると確認したわけではありません。package一覧、SBOM、固定版の更新確認、上流のadvisoryと併用します。

## arm64に残ったRustビルド用キャッシュ

[公開前検査のarm64 artifact](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41499766995/artifacts/13169865900)には、Brotli以外にも38件のblocking検出があった。対象はいずれも`root/.cache/puccinialin/cargo/registry/src/`内のlockfileであり、実行バイナリーの38件の脆弱性と同一視しない。

同版のarm64 wheelは公開されていたが許可hashがなく、CIはsdistから構築していた。対応hashを加え、OCIではwheel限定・pip cache無効化・同じレイヤーでの不要cache除去と、除去後のoffline監査を行う。版・snapshot・脆弱性gateは変更しない。source lockfileとの照合、配布物のhash・license、回帰試験・変異試験・5回の選択結果と確認範囲は[検証記録](../experiments/2026-11-02-zizmor-wheel-cache.md)を参照する。
