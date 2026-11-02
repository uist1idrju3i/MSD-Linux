# Release保護・Ed25519鍵・署名jobの調査

[RESEARCH](../../RESEARCH.md) / [管理者の設定手順](../RELEASE-SIGNING.md) / [権限設計](security/README.md)

## 対象と結論

2026-11-02時点の公開資料と、本リポジトリの `b9bea56b703c54d2cd0782481d2de7a73e13294b` を調べました。目的はReleaseの改変防止、初回導入imageと更新bundleの認証、秘密鍵をbuildから分離する構成の検討です。文書を追加しただけで署名運用を実装したとは扱いません。

推奨は、(1) GitHubのimmutable releases、(2) 保護されたEnvironmentでの独立した署名job、(3) 公開鍵だけを入れたimage、(4) 端末での署名・対象・版・hash・長さの検査です。異なる境界を守る仕組みであり、どれか一つで代用はできません。個人運用で追加承認者がいない場合の実行不能や、設定・運用の複雑さも費用に含めます。

## 1. 現行実装と閲覧できた設定

| 対象 | 確認結果 | 意味しないこと |
|---|---|---|
| `board/cardputerzero/post-build.sh` | `MSD_UPDATE_SIGNING_KEY` のファイルから公開鍵を生成。未指定なら開発鍵を生成・再利用し `key-origin=development` とする | 本番鍵がなくても安全に製品Releaseを作れる、という意味ではない |
| `board/cardputerzero/post-image.sh` | raw Ed25519でmanifestを署名。manifestは整数のversionとrootfs/bootのSHA-256を含む | `sdcard.img.xz`、SBOM、全Release assetへの署名ではない |
| `board/cardputerzero/rootfs-overlay/usr/sbin/msd-update` | 配備済み公開鍵でmanifest署名を検証し、SHA-256と整数の番号を検査 | GitHub上の最新Release発見、SemVer比較、鍵失効、物理交換対策の完成ではない |
| `docker/msd-dev` | 許可した環境変数だけを転送。署名鍵と更新番号は転送対象でない | ホストでのexportだけで、コンテナー内の署名が切り替わるわけではない |
| `.github/workflows/build.yml` | defaultの `contents: read`。Release署名Environmentを使うjobはない | Secretを登録すれば自動的に利用されるわけではない |
| Repository / Releases API | public。`v0.0.0` はprerelease、`immutable=false`。8assetにSD imageはあるがbundle・image署名metadataはない | 安定版、署名済みの初回導入、完成した自己更新の配布物ではない |
| release ruleset | active、`refs/tags/v*`、deletion / non_fast_forward | 新規タグの認可、SemVer、CI成功、Release assetの改変防止を全て強制する設定ではない |
| Environments API | 確認できた環境は `github-pages` | signing環境と承認付き署名jobがあるという証拠ではない |
| Secrets / workflow permissions API | いずれもHTTP 403 | Secretなし、既定権限が安全、とは判定しない |

現在のReleaseに含まれるAPIのasset digestは、取得物の照合には使えますが、発行者のEd25519署名や、端末にあらかじめ配備した信頼鍵の代わりではありません。既存imageの開発鍵から本番公開鍵への移行も必要です。

## 2. 防御ごとの役割と限界

| 防御 | 守る境界 | 残る条件・背反 |
|---|---|---|
| タグのruleset | タグ操作 | Release本文やassetを同時に固定するものではない。作成・更新の権限とworkflowの信頼も必要 |
| immutable Release | 公開後のasset・関連タグの変更防止 | 今後の公開分に適用。title、notes、latest、prerelease指定は変更可能。公開前の正しさは保証しない |
| Release attestation | GitHubによるタグ・commit・assetの対応の証明 | 利用者が検証して初めて意味がある。端末のraw Ed25519検証とは別の形式と信頼系統 |
| build / SBOM attestation | buildの出所、SBOMとsubjectの対応 | workflow・identity・digestの期待値を検証する必要。脆弱性がない証明ではない |
| Environment secretと承認 | 実行するjobと鍵へのアクセス | 許可されたjobのコードや管理者は信頼対象。Environment名を付けるだけでは安全にならない |
| Ed25519署名metadata | 鍵の保有者による、正確な署名対象の認証 | 間違った機種、古い版、失効鍵、サイズ不足、起動不能を署名だけでは防げない |
| オフラインbackupと復旧 | 秘密鍵の紛失・障害 | 暗号化、復元確認、担当者が必要。Secretから値を取り出す復旧は前提にしない |

immutable化後に不足assetを追加することはできません。draftへ全assetを添付して検査し、その後に公開します。過去の開発プレリリースの差し替えや、保護の迂回で済ませる案は採りません。

## 3. build・署名・公開を分ける設計案

1. **buildと試験**: 秘密鍵を持たず、固定した公開鍵とソースから生成する。現行post-buildには公開鍵だけを受け取る経路がないため、先に改修が必要です。
2. **対象の確定**: 承認するcommit、公開版、内部番号、機種、公開鍵fingerprint、asset名・hash・長さ、必要なCI結果を対応付ける。PR番号やlatestという名前だけでは選ばない。
3. **署名**: 信頼できるworkflowの小さなjobがEnvironment承認後に鍵を受け取り、0600の一時ファイルからraw Ed25519署名する。欠落、型の相違、公開鍵不一致では停止する。開発鍵へのfallbackは禁止します。
4. **公開**: 署名jobとは別に、公開に必要な `contents: write` を持つjobがdraftへ全assetを置き、検査後にpublishする。OIDCやattestationの書き込み権限も、必要なjobに限ります。
5. **利用者・端末の検証**: 別経路で信頼した公開鍵、metadata、正確なassetを照合する。GitHub CLIによるattestation検査と、端末内のEd25519検査を区別する。

build出力や別workflowのartifactは未信頼です。署名jobは、それらに含まれるscript、設定、archive展開の指示を実行しません。対象run・commit・workflow・digestの対応を検査し、名前衝突、path traversal、過大入力、競合、再実行を拒否する実装が必要です。署名後にassetを再圧縮・再生成しません。

Environmentのref制限はworkflowを動かすrefに適用され、入力したタグやcheckout先を自動で保証しません。`workflow_run` や `pull_request_target` を使っても未信頼コードが信頼済みにはなりません。署名jobと無関係な第三者Action、Docker socket、共有cache、PRのcheckoutを鍵のある実行環境へ持ち込まない方針とします。

秘密鍵を全buildへ渡す案は現在のpost-buildを使いやすい反面、compiler・依存のbuild scriptまで信頼範囲が拡大するため不採用を推奨します。別案のオフライン署名はオンライン鍵の露出を減らせますが、人の作業と配布の待ち時間が増えます。HSM/KMSは秘密鍵を取り出さない選択肢ですが、Ed25519の正確な方式・鍵形式の対応、driver、費用は未調査であり、導入済みとはしません。

## 4. 初回導入imageと更新bundleを混同しない

現行manifestが認証するのはrootfsとboot imageです。初回導入用SD imageにはselector、partition table、dataなどもあり、圧縮ファイル全体は別の対象です。

将来のRelease metadataでは、schema、機種、公開SemVer、内部番号、最低updater版、鍵の識別子、assetの正確な名前・長さ・SHA-256を署名対象に含める案を検討します。初回導入では圧縮した配布imageを、更新ではbundleとその検証対象を対応付けます。鍵をReleaseと同時に取得して無条件に信頼する方式は採りません。

raw Ed25519、Ed25519ph、SHA-256を先に計算して別メッセージとして署名する方式は同一ではありません。現在の `openssl pkeyutl -sign/-verify -rawin` と、署名する正確なバイト列、鍵の符号化を固定する必要があります。SemVerと内部番号の分離、metadata schema、image用署名形式は、この調査だけで確定・実装しません。[更新方式の比較](alternatives/updates.md) も参照してください。

## 5. 鍵の更新・失効・復旧

単一鍵のファイルを新しい鍵へ交換するだけでは、長期間未更新の端末や旧スロットが残ります。旧鍵から新鍵を認証する移行、重複受理の期間、最低限必要なupdater、失効した鍵の拒否、未更新端末の復旧を設計します。旧署名鍵が漏えいした場合は、その鍵で作った移行更新自体も無条件には信用できません。

GitHub Secretを交換しても、既存端末の信頼鍵は変わりません。緊急時の信頼の回復には、独立した復旧鍵、閾値署名、TUF系metadata、信頼できる媒体での再導入などを比較する必要があります。これは現在未実装です。物理的に同じSD上のrootfs・鍵・検証コードを交換できる条件では、hardware secure bootや耐改ざん領域によるanti-rollbackと同等の保護にはなりません。

## 6. 確認したことと次の完了条件

試験鍵でのCLI手順は、OpenSSL 3.0.2で5回、鍵生成・導出・署名・検証と、改変・別鍵による拒否を確認しました。既存mutableな `v0.0.0` に対する `gh release verify` は終了値1で、`no attestations for tag` でした。公開済みの署名運用の成功例にはしません。条件と生の終了値は [確認記録](../experiments/2026-11-02-release-key-audit.md) にあります。

本番鍵、Secret登録、Environment設定、署名・公開job、image署名、端末のGitHub取得、実機での鍵移行は試していません。今後の完了条件は次のとおりです。

- 試験鍵で正常系と拒否系を実行し、秘密鍵がlog、cache、artifact、imageへ残らないことを確認する。
- 公開鍵だけのbuild、署名job、公開jobを分離し、Secretなし・異なる鍵・別commit・古いrun・asset不一致・署名後の変更を拒否する。
- 初回imageとA/B bundleの双方を、配備した公開鍵で検証し、開発鍵からの移行と未更新端末の復旧を確認する。
- 署名後の再取得・hash・長さ・署名の照合、draftからimmutable公開、attestationの検証を実際のReleaseで確認する。
- 端末のmetadata、機種、版、失効、空き容量、通信断、A/B試験起動を別に検証し、実機が必要な結果を明示する。

## 出典と取得範囲

[出典台帳](release-security-sources.json) は公式文書と設定APIの取得日時、状態、応答bytesとSHA-256を記録します。可変ページのhashは取得内容を識別するもので、将来の再取得一致を保証しません。必要な節を読み、関連するCLI helpと実装を照合した範囲であり、文書・実装・licenseの全文監査ではありません。403は取得失敗として残し、推測で埋めません。
