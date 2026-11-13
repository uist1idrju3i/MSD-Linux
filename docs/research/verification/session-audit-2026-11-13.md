# 2026-11-13 調査と証拠の最終監査

[検証の索引](README.md) / [生データの保存監査](session-evidence-2026-11-13.md)

## 対象と読み方

利用者から指定された12主題について、本文と生データの所在を照合しました。基準は`origin/main`の`121e9ae1878252a675efb6714bc36e91f488e331`です。PR #240は`c27b9a9b5dae5c32e9029250835c6990d8739a9a`、PR #241は`0c77ff9a92be9a2b2bdba7a0df26fb27be9234cf`を読みました。両PRは監査時点でopenであり、mainへの収録済みとは扱いません。

下表のmainは、この固定した基準にある文書です。今回の追記と、既存の研究・実験結果を分けます。新しいbuild、QEMU、実機測定、公開サイトの通信測定は行っていません。

| 主題 | 記録先と収録状態 | 不足・未確認 |
|---|---|---|
| 1. OpenSSL最小化・`openssl.cnf` | mainの[最小化](../component-options/openssl-minimal.md)、[runtime](../component-options/openssl-minimal-runtime.md)、[option CSV](../component-options/openssl-minimal-options.csv) | Wi-Fiのlegacy EAP/TLS-PSK不要、asm維持、CLIは移行までという条件を記録済み。`openssl.cnf`のTLS 1.2下限・SECLEVEL等は未適用の草案で、全consumerへの強制ではない。option候補の全採用・将来consumer・実機の速度も未確認 |
| 2. PQC/hybrid | [PR #241](https://github.com/uist1idrju3i/MSD-Linux/pull/241)の`docs/research/component-options/openssl-pqc-groups.md`と`docs/experiments/2026-11-13-pqc-groups.*`。merge待ち | 採否は利用者の判断待ち。5構成の容量・QEMUの演算・ClientHello・接続先の観測を、実機や全serverの互換性へ広げない |
| 3. seed非保存 | mainの[製品判断](../../design/product-decisions.md)、[書き込み台帳](../../design/write-policy.md)、[実験](../../experiments/2026-11-13-seedrng-zram.md) | hwrngとjitterへの依存、弱いhwrng時のbackup喪失、平文seedを残さずSD書き込みを避ける利点を記録済み。QEMUのcrng時刻は実機entropy品質を示さない |
| 4. zram | 同じmainの製品判断・台帳・seedrng/zram実験 | 圧縮CPU、thrash、小さいmetadata RAMの費用を記録済み。`=y`対`=m`だけの起動比較は未実施。複合変更のbefore/afterで代用しない |
| 5. RAUC対SWUpdate | mainの[比較](../alternatives/updates.md)、[更新build option](../alternatives/update-build-options.md)、製品判断 | 資料比較と試験計画はあるが採用・移行は未実装。比較完了後に選定し、移行後に公開`msd-update`を廃止する。比較・移行までCMS、現行updater存続中はCLIを残し、移行後に`no-apps`を再検討 |
| 6. legal-info A | mainの[補足収集](../operations/legal-info-supplement.md)、[SBOM](../operations/sbom-coverage.md)、[先行調査](../../experiments/2026-11-12-legal-info-hashes.md)、[実装実験](../../experiments/2026-11-13-legal-info-supplement.md) | 27 recordと25 componentの数え方、23 archive、Linux headers 5.4.296、Makefileの無条件警告を今回も明記。archive本文・patch・builder tree等は未収集で、再配布許諾確認の完了ではない |
| 7. Buildrootの管理方式 | mainの[構築基盤比較](../alternatives/development.md)と、下の管理方式比較を今回追加 | shallow submoduleを維持。過去の約100 MBという見積もりを採用せず、tree約830 MiB、Git約290 MiBの規模と今回のbyte値を区別。代替方式のbuildや取得時間は未測定 |
| 8. 本番署名とQEMU | mainの[Environment手順](../../RELEASE-SIGNING.md)と[署名job実験](../../experiments/2026-11-12-release-signing-job.md)。初回run `43331379685`のQEMU受入は[PR #240](https://github.com/uist1idrju3i/MSD-Linux/pull/240)の`docs/experiments/2026-11-13-release-signing-qemu.*`。merge待ち | Environmentの設定手順と実行証拠は別。署名workflowがあることだけで本番Secret実行済みとはしない。PR側の同版受理・負試験・B起動は、実firmware tryboot・実SD・電断の確認ではない |
| 9. Cloudflare Pages | mainの[サイト調査](../presentation/site-html-css.md)、[header実験](../../experiments/2026-11-12-pages-headers.md)と、今回の補足 | CSP例外はCloudflareだけ。production HTMLでAnalytics注入は未確認で、FAQだけを理由に`connect-src 'self'`を追加しない。DNSSEC/CAA/DMARC/redirectの推奨と、`530d91d`の失敗を下記へ追記。現在のDNS・配信設定の合格を主張しない |
| 10. `/data` | mainの[write inventory](../../experiments/2026-11-12-write-inventory.md)、[方針とS03/S4/GPIO6/rootfs-roの資料・追加計画](../../design/write-policy.md)、[storage研究](../storage/write-policy-and-s3.md) | 最初の120秒の8320 sectorsは原因未分離。resize/ext4lazyinit等は候補で、帰属の確認ではない。seed変更後の8304との差16 sectorsもseed量と断定しない。具体的なrw/journal/commit値は未決定 |
| 11. stacked PRとCHANGELOG | mainの[AGENTS §7](../../../AGENTS.md)と、下の利用者方針を今回追加 | PR作成・base設定・mergeの権限を区別。CHANGELOG fragment方式は採用しない。エージェントはmergeしない |
| 12. 開発imageと監視 | mainの[Debian snapshot実験](../../experiments/2026-11-12-dev-image-snapshot.md)、[開発環境の依存](../dependencies/development-and-ci.md)、[OCI security](../operations/development-image-security.md)、[`in_triage`の扱い](../../ci-monitoring.md) | 当時のDB・arch・gate対象の差と、全CVE不存在は別。`in_triage`は有効な状態で、finding・解決済み・scan失敗と混ぜない。将来の監視は継続が必要。DB本文・OCI tarはGit未保存で、[size/hashの一覧](session-evidence-2026-11-13.md)へ分けた |

## Buildrootのsource管理方式

これはOS基盤の置換とは別の比較です。固定sourceをどう取得・更新・配布資料へ対応付けるかを扱います。[AGENTS](../../../AGENTS.md)と[`.gitmodules`](../../../.gitmodules)はshallow submoduleを現行方式とします。製品側gitlinkとBootlin builderのcommitは別物です。

| 方式 | 利点 | 費用・制約 | 現在の扱い |
|---|---|---|---|
| 固定commitのshallow submodule | Gitの固定値と更新差分を追跡できる。対象objectがあればlegal-info用`git archive`も可能 | 初回取得が必要。shallowは履歴を削るだけで、作業tree・download・build出力を小さくする機能ではない | 維持。固定値と対象objectの存在を検査する |
| full cloneのsubmodule | 古い履歴や任意commitの比較を手元で行える | Git履歴の取得・保存が増える。必要なobjectが既にある収集処理のためだけに全履歴化する必要はない | 必要な調査に限定。容量差は未測定 |
| hash固定のrelease/source archive | Git履歴が不要で取得物のhashを固定できる | 展開・配置・更新監視・patch対応・sourceと生成物の対応を別管理する。gitlinkからcommitを読む現在のcollector等も変更が必要 | 代替案。取得とbuildは未試験 |
| subtreeまたはsourceを直接vendor | 親repoだけでsourceを取得できる | 親repoの履歴と更新差分が大きくなる。shallowとは別方式で、上流更新とlicense/source管理の責任は残る | 代替案。移行の決定なし |

以前の約100 MBという見積もりは、この作業環境の容量説明には使いません。利用者が監査対象に指定した約830 MBのtree／約290 MBのGitという値を、今回は単位を明示して再採取しました。

| 2026-11-13の1回の採取 | `vendor/buildroot` | `.git/modules/vendor/buildroot` |
|---|---:|---:|
| `du -s -B1`の割り当てbytes | 870,383,616 | 303,972,352 |
| `du -sb`の見かけのbytes | 800,057,001 | 302,690,297 |

割り当て量は約830.1 MiBと289.9 MiBです。対象submoduleの`--is-shallow-repository`は`true`でした。treeにはこの環境のdownload等が含まれ、clean checkoutや初回cloneの容量ではありません。見かけと割り当て量、MBとMiBを混ぜず、別環境の一定値として使いません。source archive 7,166,761 bytesの値とも別です。

## Pages・DNSの未完了項目

推奨はDNSSECの有効化と検証、実際に使うCAに合ったCAA、mailを使うかどうかに合ったDMARC、`pages.dev`からcanonicalなcustom domainへのredirectです。設定の存在、DNSSECの検証chain、mailの運用、redirect loopとpreviewへの影響は未確認です。推奨を書いたことを適用済みとはしません。

mainの`530d91d6ffbc1624a7c05ffc845bd1d811f98a86`について、利用者はPagesの`Build failed.`を報告しました。今回のcommit checks照会でもCloudflare Pagesのfailureを確認しました（9 passed / 1 failed / 0 pending / 1 skipped、check ID `131211622894`）。GitHub job log APIは`Not Found`で、失敗理由は取得できませんでした。これをGitHub Actions内の製品build失敗や、現在の配信失敗と同一視しません。既存記録のpreview成功も、この当時の失敗原因やproduction HTMLのAnalytics注入を説明しません。

## 利用者が指定した作業方針

2026-11-13の依頼では、新しいstackの最初のbranchをfresh `origin/main`から作り、後続branchを直前のPR headから作る方針です。先行PRがmergeされた後の取り込みは指示に従い通常mergeで行い、履歴を勝手にrebase・force pushしません。今回の監査branchは依頼どおりfresh mainが基点です。

PRは利用者が開き、baseも利用者が設定します。エージェントは指示なしにPRを作成せず、mergeもしません。CHANGELOG fragment方式は利用者が退けた案として記録し、導入しません。必要な変更は既存の`CHANGELOG.md`のUnreleasedへ記録し、stackで競合したときは両側の項目を保持します。今回の文書・保存監査では製品動作を変えないため、新しい利用者向けCHANGELOG項目は追加しません。
