# 構築基盤・開発環境・CI toolの代替

[比較の索引](README.md) / [hostの生成・補助依存](build-support.md) / [Yoctoからの還元](../yocto-migration/buildroot-lessons.md)

## 結論

製品を作る基盤、検査を実行する環境、検査tool、公開する証拠は別々に選びます。Buildrootから別基盤への移行やtoolの統合を、依存数の減少だけでは評価しません。MSD/Linuxの機能、再現性、秘密値の境界、失敗の検出、保守・実行費用が同等以上であることを条件にします。以下は2026-11-02 UTCに取得した資料による提案です。製品設定・固定版・workflowは変更しておらず、代替構成のbuild・実行は本リポジトリでは試していません。

## 構築基盤と実行環境

Buildrootを維持したままsourceの取得方式を変える案は、[shallow submodule・full clone・archive・subtreeの比較と容量の訂正](../verification/session-audit-2026-11-13.md)へ分けます。OS基盤の移行と同じ判断にはしません。

実行中のcache・並列化と費用、Docker内toolchainとBuildroot host packageの区別、改善案の優先順は[CIの追加調査](../operations/ci-build-scope-and-performance.md)を参照してください。候補の機能と、実際に設定・検証した範囲を分けています。

| 現行と候補 | 何を改善できるか | 費用・条件と再評価の結論 |
|---|---|---|
| Buildroot維持 / Yocto・OpenEmbedded | package単位の再構築、layer・SDK・license/SBOM等の仕組みを選べる | 現行はBuildrootを基準に維持。[過去の比較](../yocto-migration/README.md)には測定条件・未取得log・取りやめた計画がある。Yoctoは大きいという一般論だけでは排除しない。再現性、全周辺機能、A/B、time/RAM/storage、運用費用を同一条件で再実験する場合に候補へ戻す |
| OpenWrt | network appliance向けの構成・package・運用の統合 | [公式build system](https://openwrt.org/docs/guide-developer/toolchain/use-buildsystem)にはfeeds、toolchain、kernel、rootfsの構成がある。ただしCardputerZero全機能と現行更新形式への移植は別作業。network機能だけを理由に全面移行しない。router/AP用途を製品要件へ加える時に再評価 |
| PTXdist、Nix系、Debian系の縮小構成 | 別の構成管理・再現性・binary package運用 | [詳細比較](system-builders.md)でBSP、host固定化、target OS、rootfsの生成を分ける。PTXdistの旧about URLは404だが、公式download・manualは取得。いずれもCM0対応や現行read-only/A-B契約との同等性を証明するものではない |
| 固定Debian OCI / Alpine・musl系 / distroless | package・runtimeを減らす可能性 | nativeの配布tool、Buildroot host tool、glibc前提、QEMU build dependencyとの互換を確認する必要がある。distrolessは配布時の実行imageという役割が異なり、多数のcompiler・shellを使う開発用OCIの直接の代替とはしない |
| rootless Docker / Podman・Buildah系 | daemonやhost root権限の境界を見直せる | [Docker rootless](https://docs.docker.com/engine/security/rootless/)も利用候補。PodmanはOCI操作とrootlessを提供するが、CLI・socket・build cache・volume・UID mappingを無条件に互換とはしない。現在のwrapperを利用したbuild、bind mount、native両CPU試験、cache ownership、networkとエラー処理を独立検査してから選ぶ |
| GitHub-hosted / self-hosted runner | native architectureやcacheの使い方を選べる | self-hostedは未信頼PR、永続cache、秘密値、daemon socket、横移動の運用費用を増やす。速さだけで採用しない。hostedでも可変runner imageの版を保存し、固定OCIだけでhost全体が再現可能とは扱わない |

[Buildroot manual](https://buildroot.org/downloads/manual/manual.html)と[Yocto overview](https://docs.yoctoproject.org/overview-manual/yp-intro.html)は、機能・構成の所在の確認に用いました。可変の最新manualと固定Buildrootの実装が同じとは限りません。製品をOCI化する案と、開発をOCI内で行う現在の方法も別の判断です。

## compiler cacheとQEMU

| 現行と候補 | 評価 | 必須の試験 |
|---|---|---|
| Buildrootのhost ccache / cacheなし / sccache | ccacheはC/C++等の再コンパイルを削減する。sccacheは他言語・remote/distributed機能も持つが、server・storage・認証・key境界の管理が増える。現在のC中心の構成で速くなるかは未測定。まずcacheのhit/miss、容量、実時間を測る | cold/warm各5回以上。compiler・flags・sysroot・source変更でmissすること。untrusted PRからreleaseのcacheを上書きできないこと。cache破損・取得失敗でも正しい成果物を作るか、明確に失敗すること |
| 固定QEMU / 新版QEMU / `virt` machine / Renode / 実機 | QEMUは起動・A/B等の自動試験の基準に維持。`virt`はgeneric machineで、raspi3系のMMIO・boot契約をそのまま検証しない。Renodeは別のmodel群であり、対応一覧だけでCM0全体の代替とは言えない。実機は代替不能な確認を補う | QEMU版更新は[icountの調査](../../experiments/2026-10-31-qemu-1112-bisect.md)を読み、known-goodとの起動・plugin・命令数・実時間を比較。UART、SD、reset、firmware段階、M5周辺のcoverageを分ける。QEMU成功を実機のcamera/Wi-Fi/電源動作へ拡張しない |

[QEMUのRaspberry Pi model資料](https://www.qemu.org/docs/master/system/arm/raspi.html)には対応deviceと欠けるdeviceがあります。これは開発treeの説明で、固定11.1.2の全機能を確認した結果ではありません。[Renodeの対応一覧](https://renode.readthedocs.io/en/latest/introduction/supported-boards.html)の取得も、CardputerZero modelを作成・実行した証拠ではありません。

## lint・security・SBOMは相互の完全な代替ではない

| 現行のtool・処理 | 代替・補完候補 | 残す理由と条件 |
|---|---|---|
| actionlint | schema validation、汎用YAML lint、zizmor | actionlintは式の型、Action入出力、reusable workflow、shell等を検査する。YAMLの構文検査だけでは代替しない。zizmorのsecurity検査と重複はあるが同じ範囲ではない |
| ShellCheck | shfmt、実行試験、別shellの構文検査 | 書式・構文・実行された経路・静的な問題は別。`shfmt`導入でShellCheckを外さない。hostの古い版と固定OCIの版の結果を混ぜない |
| hadolint | Docker/BuildKitのbuild check、Trivyのmisconfiguration | Dockerfileの規則とRUN内のshell検査を持つ。image build成功やOS脆弱性scanだけでは置き換わらない。build checkを加えるなら、重複する指摘と実行環境の費用を確認 |
| zizmor | actionlint、CodeQL/汎用SAST、manual review | GitHub Actions等のsecurity上の問題を検査する。target Cコードや全supply chainの監査を代替しない。workflowの負のfixtureとoffline検査を基準に維持 |
| Trivy | Grypeを用いた独立比較、OS/vendor advisory、VEX | Trivyは脆弱性以外にsecret・misconfiguration等も扱う。GrypeでCVEを照合してもその全機能の代替にはならない。DB時刻、package同定、architecture、修正版、VEXの適用根拠を比べ、単純な件数一致を要求しない |
| Buildrootのshow-info・CycloneDX補正・照合 | SPDX出力、Syft等によるbinary側の別検査 | source/recipe側のSBOMと最終imageの検出には異なる取りこぼしがある。format変更だけでcoverageは増えない。両方を同じ生成元・image digestへ結び付ける補完が候補 |
| GitHubのattest-sbom・build provenance | 別のin-toto/SLSA・Sigstore発行/検証経路 | provenanceは誰が何から作ったかの主張を検証する材料で、脆弱性なし・再現可能・安全な公開を証明しない。検証側のidentity、repository、ref、workflow、digestのpolicyが要る。端末のraw Ed25519 bundle認可とは別 |
| リンク・JIS・文書サイズ・SKILL・site等の自作検査 | 汎用toolへの部分移行 / 現行の負の試験を保持 | repository固有の契約は一般的なMarkdown lintだけでは代替しない。既存fixture・unused exception・失敗伝搬を移植できる場合だけ削減候補にする。checkerが通るように過去の引用・測定値を改変しない |
| yomiyasu、ロゴ生成fonttools、w3m/lynx等の文書tool | 他の校正・描画・browser検査 | 日本語の意味保存、fontの出所、text browserでの導線、実画面の確認は異なる契約。自動検査やLLMの評価だけで視覚確認を済ませたことにしない。文書作業の依存を製品rootfsへ追加しない |

Grype等の追加は常時二重scanを決定したものではありません。まず固定した同じimage/SBOMで一度照合し、異なるpackage同定やadvisoryを発見できるか、CI費用に見合うかを確認する実験候補です。raw scanner出力に秘密値が入る可能性があるため、公開artifactは許可した項目のみとします。Brotli修正版の導入は指示どおり延期し、既知の検出やゲートを緩める理由にはしません。

## 取得した候補の版・license・security窓口

次表の版はGitHubの`releases/latest`が返した公開候補です。全tagの最大安定版、正式な保守期限、固定版の修正状況を保証する表ではありません。README等を取得した開発HEADとstable releaseも区別します。

| 候補 | 取得候補 | licenseの確認範囲 / securityの追跡 |
|---|---|---|
| ccache | v4.14.2 | 取得HEADのLICENSEはGPL-3.0系。remote backendと内包libraryの条件は別確認。公式manual・releaseを追う |
| sccache | v0.19.0 | 取得LICENSEはApache-2.0。storage provider・配布binaryの依存、serverの認証を別確認 |
| Podman | v6.1.4 | 取得LICENSEはApache-2.0。取得したSECURITY/SUPPORTとreleaseを追う。old repository URLのredirect先も台帳に残す |
| actionlint / ShellCheck / hadolint | v1.7.12 / v0.11.0 / v2.15.1 | MIT / GPL-3.0系 / GPL-3.0系の取得license。ソース、配布binary、Haskell/Go内包物を一つのlicense名で閉じない |
| zizmor | v1.31.1 | MITの取得LICENSE。wheelのRust crate等は別の監査対象 |
| Trivy / Grype | v0.76.1 / v0.121.1 | 各Apache-2.0の取得LICENSE。取得HEADのSECURITYは、Trivyが保守保証なしのbest effort、Grypeが最新releaseのみsecurity更新・best effortと説明する。scanner自身、DB供給経路、advisoryの更新を分ける |

詳細な固定版、OCIのAPT、Go module、Action manifest・npm source lockfileは[依存監査のPR](https://github.com/uist1idrju3i/MSD-Linux/pull/184)を参照します。231件のAPTや859個のnpm名を、それぞれ当リポジトリで別libraryに置換できるわけではありません。親Action/OCI/toolchainの変更を通じて比較します。npm lockfileの一覧を実bundleの完全なSBOMと呼ばず、runner全体、配布native binary、外部toolchain内包物の未確認範囲も残します。

## 再現性と採用の基準

- image digest、source revision、全固定値、hostとtarget、実行したnative architectureを対応づけます。tag、mutable runner label、可変DBの日付を混同しません。
- `SOURCE_DATE_EPOCH`等の入力統一は手段であり、再現性の証明ではありません。異なる独立buildの成果物を照合し、差があればmetadataと実内容を調べます。
- lint、脆弱性scan、signature/provenance、機能試験、実機試験は独立した判定にします。toolを一つにまとめた際に失う検査を先に列挙します。
- 費用はbuild時間だけでなく、cache容量・転送・保守・false positiveの調査・復旧・secret運用を含めます。機能を削除して速くなった構成を同等な成功とは数えません。

出典のURL・ref・bytes・hash・失敗は[sources.json](sources.json)にあります。GitHubの[workflow防御](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)、[attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)、[SPDX](https://spdx.dev/use/specifications/)、[CycloneDX](https://cyclonedx.org/specification/overview/)、[SOURCE_DATE_EPOCH](https://reproducible-builds.org/docs/source-date-epoch/)も所在と責務を照合しました。全schema・全security policy・全binaryの精読を終えたという意味ではありません。

[比較の索引へ戻る](README.md)
