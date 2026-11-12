# SBOMの生成と確認範囲

## 何を確認したか

[固定CI生成物の確認](../../experiments/2026-11-02-hardware-artifact-audit.md)に続き、[run 41477653658](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41477653658) のSBOMとlegal-infoを読んだ。これは全依存の最新版・脆弱性・配布許諾を確認し終えた報告ではない。

| 項目 | 確認した値と限界 |
|---|---|
| 形式 | CycloneDX 1.6。generatorの既定値1.6.2はSPDXライセンス一覧の版にも使われ、SBOMのspecVersionは先頭2桁になる |
| 構成要素 | 67件。BR_TYPEはtarget 18件、host 49件。hostはイメージに入るアプリケーション数ではない |
| 依存関係 | 68個のdependencyレコード、267本の参照。レコード数と辺の数は異なる |
| project version | 実checkoutのmerge commit `c96e5faf015c828a213c8ea64f613b4a429196c7`。PR headとは区別する |
| Linux | 元の通常ビルドSBOMはversionとCPEが `custom`。以前は定期securityだけに補正処理があり、生成経路が異なった |
| purl / hash | purlとcomponent直下のhashは0件。ただし59 componentのexternalReferencesにはsource hashがある。「hashが全くない」ではない |
| ライセンス欄 | 67件に欄があるが、unknownを含む。欄の存在は配布許諾の確認ではない |
| legal-info | target manifest 13行、host manifest 48行。SBOMとの件数差を依存の欠落と即断せず、package単位で照合する |

## 生成時の検査

通常buildと定期securityの両方で、同じ呼び出しの `show-info` をJSONとして保存し、そのJSONからSBOMを生成する。LinuxのversionとCPEは同じスクリプトで補正する。通常buildは展開したkernelのMakefileを読み、securityはdefconfigで固定したcommitのMakefileを取得する。source commitは `msd:linux:source-commit` に残す。

補正時に、project version、構成要素の過不足・重複、名前・版、host/target、依存関係の参照先とpackageごとの接続を照合する。Buildrootのgeneratorと同様にvirtual packageをproviderへ解決し、rootfs項目はcomponentに数えない。検査に失敗したらSBOMを書き換えず、CIを止める。元のshow-infoもartifactへ保存する。

これは内容の照合であり、CycloneDX全schemaの適合検査、実ファイルからの独立したSBOM生成、署名や配布許諾の検証ではない。修正の試験条件・入力hash・失敗した照合は[検証記録](../../experiments/2026-11-02-sbom-generation.md)にある。

## 監視対象と残る確認

その後の通常buildの版補正と実artifactの再照合、全67 componentの最新版候補、開発用OCIとActionsの依存、監視の差分は[依存関係の一覧](../dependencies/README.md)にまとめた。以下の初回調査と、その後の検証を区別する。

- `security.yml`は2時間ごとに補正後のSBOMをBuildroot `cve-check`へ渡し、NVD feedと照合してVEXとstateをartifactへ保存する。mainでは「製品SBOMの脆弱性監視」Issueを更新し、前回成功時との差分をコメントする。PRでは同じfeed cloneからbaseとheadを比較し、新規の修正可能CRITICAL（CVSS v3.x/v4.0で9.0以上）だけを失敗条件にする。CVSSv2のみ、NVDに修正境界がないfinding、CPEがないcomponentはゲートを通すが、結果は安全を示さず修正可否不明として報告する。修正境界はhead SBOMのcomponent versionを含む同一vendor/productのCPE rangeで確認する。新規CRITICALのNVD entry欠損は整合性エラーとして失敗する。source packageのCPEによる照合なので、CPEを持たないpackage、外部ツールチェーン内部、M5配布ファイルは見えないことがある。一覧にないことは安全の証明ではない。
- `toolchain-external-bootlin`のlicenseはunknown。一部M5配布物もunknown、Wi-Fi firmwareはPROPRIETARYとして記録される。toolchain内部のGCC・binutils・glibcの版と許諾、個々のfirmwareの出典・許諾は別に確認する。
- 通常buildのlegal-infoログには、LinuxのCOPYING等に対するhash欠落も記録されている。build成功を、これらのライセンスファイルのhash確認済みと読み替えない。
  2026-11-12追記：Linuxのlicense 3 fileとM5のCOPYINGにhashを追加し、同一出力の`legal-info`で検証成功と対象4行の消失を確認しました。[変更前後の記録](../../experiments/2026-11-12-legal-info-hashes.md)を参照してください。元のログは保持し、Buildroot source未保存・Bootlin license file未定義・全配布物の許諾確認とは区別します。
- 開発用OCIのapt・pip・Go依存、GitHub Actionsとそのruntime、runner、CI専用ツール、ロゴ生成依存は、製品のBuildroot SBOMだけでは一覧にならない。別の一覧と版・CVE監視の照合が必要である。
- SPDXなど別形式を追加するかは、必要な受け渡し先と照合可能な情報を比較して決める。形式を増やすだけでは、上記の欠落は埋まらない。

## 根拠となる実装

- [Buildroot generator](https://gitlab.com/buildroot.org/buildroot/-/blob/8b238854d909c9cce32ef9671d968b03e323b55d/utils/generate-cyclonedx)
- [version補正と内容照合](../../../.github/scripts/set-kernel-version.py)
- [通常build](../../../.github/workflows/build.yml)、[2時間ごとのsecurity](../../../.github/workflows/security.yml)
- [回帰テスト](../../../tests/check-sbom/test_sbom.py)
