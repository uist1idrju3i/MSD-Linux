# A/B更新frameworkの代替比較

[代替比較](README.md) / [保存領域](filesystems.md) / [TUF・Uptane](update-metadata.md) / [署名の契約](signing.md) / [RESEARCH](../../../RESEARCH.md)

## 比較の前提

2026-11-13に[標準frameworkへの移行方針](../../design/product-decisions.md)を再確認しました。RAUC対SWUpdateの比較完了後に移行先を決め、移行後は公開`msd-update`を廃止します。現時点ではframeworkを採用・実装していません。比較・移行までCMSを残し、`msd-update`存続中はOpenSSL CLIを維持します。移行後に`no-apps`を再検討します。

現行の`msd-update`を、RAUC、SWUpdate、Mender等で置換・補完できるか比較します。更新framework、bootloaderのslot選択、配信server、署名metadataは役割が違います。frameworkを入れても、CM0のfirmware・SD・電源断・healthの検証は残ります。

2026-11-02にMSD/Linuxの`c0214b380c046100592cd427ab3013347dff1758`と固定Buildrootの`8b238854d909c9cce32ef9671d968b03e323b55d`を基準に確認しました。代替frameworkのbuild・実行、CM0でのslot切替、署名方式の相互運用、性能測定は本リポジトリでは試していません。製品設定と更新形式は変更しません。

固定Buildrootのoptionは[更新frameworkと暗号libraryのbuild option](update-build-options.md)、更新経路・配信制約・差分方式は[更新経路と差分配信](update-delivery.md)を参照してください。

## 現行処理を比較の基準にする

[msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)は4 memberのtar bundle、raw Ed25519のmanifest署名、imageのSHA-256、十進数の版比較、inactive rootfs・bootへの書込み、tryboot・commitを扱います。永続状態は`/data/msd-update`、selectorは共通boot領域です。[署名・鍵の比較](signing.md)に入力形式と異常系をまとめました。

| 現行を保つ利点 | 追加で設計・検証する責務 |
|---|---|
| 小さなshell処理と既存host試験を読める。配信serverや常駐serviceを必須にしない | parser・writerの特権分離、全書込み段階の電源断、設定migration、復旧、鍵rotation、鮮度・期限、永続anti-rollback、端末自身によるRelease取得 |

現行が小さいことは、欠けた責務を独自実装する総費用まで小さい証拠ではありません。一方、大きなframeworkへ移してもboard固有のboot連携が不要になるわけではありません。

## 候補の役割と費用

| 候補 | 利用できる仕組み | 本機で残る統合と背反 | 提案 |
|---|---|---|---|
| RAUC | signed bundle、slot group、health後のmark-good、custom bootloader backend。network/D-Bus等を選べる | GLib・OpenSSL等とbundle形式が増える。現行Ed25519 manifestをそのまま読めるものではない。CM0向けbackendと復旧試験が必要 | A/B image中心の有力な実験候補 |
| SWUpdate | `sw-description`、handler、複数payload、選択可能な暗号・download・server連携 | handler・scriptの自由度だけ管理対象と特権処理が増える。不要なwebserver、Lua、MTD等を落とした構成とboot連携が必要 | rootfs以外の周辺firmwareも統合するなら実験候補 |
| Mender | A/B rootfs、standalone更新、server連携、Update Modules | serverは必須ではない。現行Buildroot recipeと上流clientは世代が違う。artifact、bootloader、依存、署名方式を移す費用 | 端末群の管理が必要なら再検討 |
| Rugix Ctrl | READMEはA/B・復旧構成、差分更新、署名の事前検証、永続state管理を説明する | Bakeryは別のimage build system、Adminは別のUI。Ctrlだけを組み込む範囲、boot flow、署名と鍵、最終依存を調べる必要がある | Buildroot維持のまま比較する追加候補 |
| OSTree | content-addressed tree、incremental配信、deployment・rollbackを構成できる | 固定のraw rootfs/boot A/Bとは保存形式と運用が違う。kernel・boot配置、可変設定、署名、復旧を再設計する | 更新転送量・世代管理を重視する別構成の候補 |
| bootc | boot可能なOCI imageを扱うOS更新構成 | container build/distributionとhostの起動・更新基盤を含む。既存rootfs bundleの小さな差替えではない | OCI中心へ製品全体を変える場合の比較対象 |
| systemd-sysupdate | version付きresourceの取得・検証・更新を、file/directory/partition等へ構成できる | systemd導入・resource定義・boot切替・health・復旧を別々に統合する。単なるdownload commandではない | init選定と一緒に評価 |
| MCUboot等 | 別MCUのimage検証・boot切替で利用する仕組み | BCM2837のVideoCore起動段を置換できる根拠にはならない | 周辺MCUの更新等、用途限定 |

hawkBit等の配信・端末群管理serviceや[TUF metadata](update-metadata.md)は、block-device writerやbootchooserの直接の代替ではありません。手元でReleaseを選び端末に渡す方式と、端末が自動取得する方式も分けます。

## RAUC: 解消できた未確認と残る範囲

[固定したintegration資料](https://github.com/rauc/rauc/blob/e1b95d538c41178d3ac19069a2602988fe339fb8/docs/integration.rst)で、custom backendの次の契約を確認しました。

| 呼出し | 期待する応答 |
|---|---|
| `get-primary` | primary slotのbootnameと終了値0。失敗は非0 |
| `set-primary <bootname>` | primaryを設定し、成功0・失敗非0 |
| `get-state <bootname>` | `good`または`bad`と終了値0。取得失敗は非0 |
| `set-state <bootname> <state>` | slot状態を設定し、成功0・失敗非0 |

これはAPIを確認した結果で、CM0向け実装を確認した結果ではありません。firmware連携の[PR #1599](https://github.com/rauc/rauc/pull/1599)は2026-11-02のAPI確認でもopen、`merged=false`でした。PRの存在をstable releaseの公式対応とは数えません。trybootで失敗した新slotへ戻らないこと、primary自体が起動不能な場合、共通p1破損、状態の保存失敗をbackendの試験条件にします。

[advanced資料](https://github.com/rauc/rauc/blob/e1b95d538c41178d3ac19069a2602988fe339fb8/docs/advanced.rst)はCMS/X.509によるbundle認証と`plain`/`verity`の差、検証後にbundleを変えられる危険を説明しています。`verity` bundleの読取り検証と、インストール先rootfsのdm-verityは別です。暗号libraryの対応算法だけで現行raw Ed25519との互換性を判断せず、host生成からtarget拒否条件まで試します。

固定BuildrootはRAUC 1.15.2を持ち、TLS実装としてlibopensslを強制し、ENGINE、GLib、target squashfsを選びます。D-Bus、network/libcurl、JSON/json-glib、streaming/libnl、GPTは条件別です。systemdまたはD-Busが全構成で必須とはしません。release選択、固定recipe、最終link、常駐process、mount権限を別々に記録します。

## SWUpdate: 自由度を安全な構成へ絞る

[署名資料](https://github.com/sbabic/swupdate/blob/e2a1f3764cd9e8730ffdabc7993a457d248a37f3/doc/source/signed_images.rst)と[crypto Kconfig](https://github.com/sbabic/swupdate/blob/e2a1f3764cd9e8730ffdabc7993a457d248a37f3/crypto/Kconfig)を確認しました。署名した`sw-description`とpayload hashを結び付け、`CONFIG_SIGNED_IMAGES`を有効にするとruntimeで検査を無効にできない契約です。RSA/CMSでは鍵指定が必要です。

取得したKconfigにはraw RSA、RSA-PSS、CMS、GPGの項目があります。raw Ed25519専用選択肢はこの資料では確認できません。これをCMSの全算法が非対応という意味には広げません。現行のOpenSSL CLI署名を無変更で使えるとはせず、archive・署名・鍵形式を含めた移行試験を要件にします。期限・証明書purposeを無視する設定は、互換性のために安易に有効にしません。

固定Buildrootは2026.05.1で、json-c・libconfig・libubootenvを基本依存に持ちます。既定の設定fileはembedded webserverやraw NAND/NOR handlerを含むため、それをMSD/Linuxの最小で安全な既定値とはしません。必要なpayloadと入口を先に限定し、download、Lua、webserver、remote handler、MTD、暗号backendを各々選びます。

[bootloader interface資料](https://github.com/sbabic/swupdate/blob/e2a1f3764cd9e8730ffdabc7993a457d248a37f3/doc/source/bootloader_interface.rst)とbootloader Kconfigは取得しましたが、CM0 + trybootの完成したbackendはこの比較では確認できませんでした。以前の「tryboot連携がない」という未出典の断定にはせず、独自handler等を含む実装範囲と、本機の未確認を分けます。

## Mender: 版・server・署名を分ける

[上流README](https://github.com/mendersoftware/mender/blob/149ec597e7476f33a9f31b5a95eee87ec2d3b96a/README.md)はstandalone、server不要の更新を明記します。「クラウド必須」だけを不採用理由にはできません。server認証とartifact署名も別です。

- 固定Buildrootの`package/mender`は3.5.3です。上流READMEのC++ clientと同じ世代ではなく、READMEに挙がるC++、Boost、libarchive、LMDB、OpenSSL、D-Bus/systemdの開発依存を古いrecipeの対応実績に読み替えません。
- 2026-11-02のGitHub `releases/latest`応答はupdater repoで5.2.0、mender-convertで5.3.0でした。製品Mender Clientの6.1表記とは対象が違います。一つの数字を全componentの最新版にしません。
- [公式署名手順](https://docs.mender.io/artifact-creation/sign-and-verify)はRSA PKCS#1 v1.5とECDSA P-256を説明し、`ArtifactVerifyKey(s)`を設定すると未署名・検証失敗を拒否するとしています。未設定でも強制検証するとの説明にはしません。raw Ed25519の既存形式との相互運用は未検証です。
- mender-convertのRaspberry Pi構成例は、CM0の公式・実機対応を意味しません。bootloaderとpartition layout、rootfsとbootの同期、trybootの維持か変更かを調べる必要があります。

## Rugix: Ctrlとimage buildを分けて再検討する

[固定README](https://github.com/rugix/rugix/blob/6d7fc277919b0048893c80d7e1e6e488ddc7b27b/README.md)は、CtrlをBuildroot等の既存buildへ統合できる端末側更新・state管理toolと説明しています。Bakeryは別repositoryのimage build、Adminは別のbrowser UIです。既存文書で未確認だったCtrlとBakeryの区別を解消し、Bakeryへの移行をCtrl採用の前提にはしません。

2026-11-02のrepoのlatest応答はv1.4.0で、旧文書のv1.3.0は当時の値です。READMEはRust toolchainと、native buildにC compiler・pkg-config・OpenSSL・liblzmaを挙げ、cross buildにはDocker/Podman、差分生成等には追加host toolを説明します。これは採用するtargetの全runtime依存を確定した結果ではありません。READMEの署名事前検証・任意boot flow対応の説明も、本機で試した契約には数えません。raw Ed25519形式、slot上限、boot flow、state migration、build recipe、最小構成のサイズと負の試験は採用前に残ります。

## 保守・license・監視

| 対象 | 原文とrecipeで確認した範囲 | 採用前に残る確認 |
|---|---|---|
| RAUC | upstreamはLGPL-2.1-or-later。固定recipeは`LGPL-2.1`と記録 | 本体・GLib・OpenSSL・target/host toolのlicenseとlink、版監視 |
| SWUpdate | recipeはGPL-2.0/GPL-2.0+、LGPL-2.1+、MIT、ISC、BSD、CC0、CC-BY-SA、OFL等を列記 | 選択した本体・IPC library・web資産・font・handlerごとの配布物と義務 |
| Mender | upstream本体はApache-2.0。旧recipeは内包物の複数licenseも列記 | C++世代の全依存、artifact tool、Update Module、商用拡張・serverとの境界 |
| Rugix Ctrl | READMEはMITまたはApache-2.0の選択を明記 | Ctrl・host Bundler・全crate/native依存を分けたlicenseとSBOM、監視、Buildroot統合 |
| OSTree | READMEはcode/man/APIをLGPLv2+とし、manualには別licenseを示す | file単位SPDXと実際のbuild・署名backend・bootloader統合 |
| bootc・sysupdate等 | 機能資料を比較した範囲 | 採用構成の全依存、license、SBOM、Buildroot recipeの追加範囲。機能資料だけで配布可否を確定しない |

Buildroot submoduleの更新通知は、未採用候補を含む各framework・内包依存・pluginの全版と脆弱性を継続監視する保証ではありません。採用時は[依存台帳とSBOM](../operations/sbom-coverage.md)と監視経路を同じ変更で更新し、hostのsigning toolも対象にします。

## 実験の優先順

第一候補はRAUCの最小構成です。ただし採用決定ではありません。署名・CMS・依存とcustom backendの費用が、現行更新処理を安全に拡張する費用より低いか比較します。周辺firmwareも一括で扱う必要が強ければSWUpdate、端末群管理ならMender、OCI中心への転換ならbootc等の優先度を上げます。

1. 現行の正常系・異常系host testと、署名・board・版・長さ・inactive slotの不変条件を候補へ移します。公開SemVerと内部番号は未決定で、比較だけで変更しません。
2. signed manifestとpayloadの結合、download中断、署名後の書換え、設定migration、disk-full、active slot拒否を試します。streaming時は書込み開始と認証完了の順序を別に記録します。
3. network/parser/verifierと特権writerの実process・uid・capability・IPCを確認します。rootで動くserviceが一つ増えただけなら、特権分離の達成とはしません。
4. QEMUの全slot・health失敗・状態破損、実機のfirmware・watchdog・SD flush・各書込み段階の電源断を分けます。共通boot領域の復旧と、失敗した設定変更からの回復も試します。
5. host/targetのサイズ、RAM、起動、転送・書込み量、再現性、保守手順を同じ基準で比較し、5回以上の測定と失敗を[実験記録](../../experiments/README.md)へ保存します。

原文の固定HEAD・Release応答・取得時刻・hashは[sources.json](sources.json)にあります。開発HEADをstable releaseへ読み替えず、GitHubのlatest応答だけで全系列の保守状態を確定しません。
