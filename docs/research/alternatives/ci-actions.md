# Actionsと内包npmの代替を選ぶ単位

[比較の索引](README.md) / [全体の範囲](inventory-boundaries.md) / [開発・CI tool](development.md)

## 結論と証拠

[11参照の表](action-coverage.csv)は直接8参照とcompositeの子3参照を、repository・commit・subpathで区別します。同じ名前でも別commitなら別の入力です。[npmの表](npm-coverage.csv)は859名・1,574 name/versionを、元のlockfileに記載された親Actionとdev/optional/licenseへ対応づけます。これは実bundleのSBOMや全内包物の監査ではありません。

固定commitの10個のroot LICENSEはMITでした。cacheのrestore/saveは同一repository・commitのため、一つの原文を共有します。[URL・時刻・bytes・hash](action-license-sources.json)を保存し、root MITを全npmのlicenseへ拡張しません。比較の基準とlockfileの全原値は[依存監査](../dependencies/development-and-ci.md)を参照してください。

## 機能別の置換と背反

| 固定参照・責務 | 候補と得られるもの | 失う契約・増える費用と結論 |
|---|---|---|
| `actions/checkout` | 明示的な`git init/fetch/checkout`、別のcheckout Action、source archive取得 | Git履歴、merge ref、submodule、shallow、LFS、safe.directory、credentialの保存/消去、後始末を自分で保証する必要がある。archiveは履歴とsubmoduleを代替しない。既存の`persist-credentials: false`等を失わず、まず公式Action更新を基準に比較する |
| `actions/upload-artifact`の直接参照とPages内部の別commit | 別のartifact用Action、object storage、Release asset | retention、immutability、digest、上限、hidden file、権限、取得UI、同名/再実行の挙動が異なる。Release公開と一時artifactは別の機能。秘密を含み得るraw reportは、保存先の変更でも公開不可。専用API実装は自作認証・retry・後始末を増やす |
| `actions/upload-pages-artifact` | tar生成とartifact登録を明示的に構成、Pages以外のhosting | Pages所定のarchive、symlink/permission、hidden file、artifact名・ID、deployとの引渡しを保つ必要がある。子upload-artifactだけを当リポジトリで更新したことにしない。上流compositeの更新か自前workflowへの移行として検査する |
| `actions/deploy-pages` | branchからのPages公開、別hosting、直接APIによる公開 | OIDC、`pages: write`、environment、deploy状態・失敗・cancel、保護規則、公開先の契約が変わる。branch公開はcommit/pushの権限と公開物管理が増える場合がある。Node依存数だけでは移行を決めない |
| `actions/cache/restore`と`save` | cacheなし、ccache remote backend、OCI layer cache、別storage | download cacheとcompiler cacheとDocker layerは別。key/version、restore prefix、PRのread/write範囲、保存条件、容量・転送・eviction、未信頼PRを跨ぐ所有権を保つ。公式cacheからの移行だけで高速・安全になる根拠はない |
| `actions/attest-sbom`と子`actions/attest` | 別のSigstore/in-toto発行経路、builderからのattestation | predicateのschemaとformat、subject digest、OIDC identity、certificate/透明性記録、検証policy、registry/取得経路、書込み権限を合わせる。SBOMが存在することと署名されたこと、その内容が完全なことは別 |
| `actions/attest-build-provenance`と別commitの子`actions/attest` | builder統合provenance、SLSA向けの別builder/発行手順 | 誰が何から作ったかの主張、builder identity、source/materials、trusted workflow、再現可能性を別々に検査する。署名を発行しただけでSLSA levelや安全性を認定しない。端末のEd25519更新認可の代替でもない |

比較は機能と信頼境界によるもので、代替workflowや別hostingへの移行を実装したものではありません。APIの引数、利用プランの費用、現行の最大容量、全candidateのlicense/EOLは採用時に公式仕様を再確認します。異なる機能を「同じAPIの完全互換」と呼びません。

## 全npm行をどう読むか

`contexts`はJSON配列で、親のID、dev、optional、licenseを記録します。同じname/versionでも親やflagが違う場合をまとめて真偽値一つへ潰しません。flagやlicenseの`null`は元の台帳に記載がないことであり、`false`やMITへの推測ではありません。元のnested path・integrity等は[再帰的な台帳](../dependencies/actions-recursive.json)にあります。

各行の交換単位は、その依存を含む親Actionのsourceとbuild済みbundleです。全859名をこのrepositoryのrequirementsへ移し、最新版で上書きする案ではありません。Node24、JavaScript bundle、source lockfileのdev dependency、runnerのNode runtimeを分けます。`dev: false`だけでも、実行されるコードと未使用コードを完全には確定できません。

候補を選ぶ順は次です。

1. 親Actionの保守された固定版を更新し、source・bundle・advisory・権限差分を検査する。
2. 問題のlibraryが不要な機能にだけ使われるなら、親の機能削減・build option・別Actionを比べる。
3. 親sourceの改修が必要なら、上流修正か保守するforkを候補とする。API、error、runtime、license、bundleの再生成と配布を引き受ける。外部repositoryへの書込みは承認前に行わない。
4. HTTP、YAML、glob、archive、GitHub API等のlibrary間の置換は、親sourceの設計変更として評価する。同じ分野でもoption、resource制限、encoding、retry、認証・権限の意味は異なる。Node組込みへの移行も振舞いの試験が必要。

最新版・deprecated・engineの調査は[全859名のregistry照合](../dependencies/actions-npm-latest.json)にあります。古い・deprecatedというmetadataだけで到達可能な脆弱性や機能の不要を確定しません。個別1574組のAPI移植案、配布bundleとの突合、内包licenseの全文監査は未確認です。

## 最小化と実験条件

現時点の提案は、まず公式Actionの固定SHA、権限最小化、監査・通知を維持し、実bundleのinventoryと入力/出力契約を確認することです。依存の件数を減らす目的だけでshellやHTTPの自作へ移すと、第三者の保守を自分が引き受けます。一方、互換性を永久に優先する提案でもありません。目的に合えばActionの廃止や公開方式の変更も候補です。

実験では同じcommit・権限・成果物を使い、正常、HTTP失敗、timeout、cancel、未信頼PR、再実行、改変、権限不足を試します。削除する検査・provenance・artifactは必ず列挙します。時間・転送・課金・保守・復旧費用を比較するまで高速化の効果とはしません。代替構成のbuild・実行は本リポジトリでは試していません。

[比較の索引へ戻る](README.md)
