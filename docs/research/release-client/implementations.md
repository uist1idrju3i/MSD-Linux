# TUF clientと公開側ツールの選定

[自己更新の設計](README.md) / [配信と取得](transport.md) / [信頼と復旧](trust-and-state.md) / [RESEARCH](../../../RESEARCH.md)

## 比較する役割と確認範囲

端末でmetadataを検証するclient、公開側でrepositoryを生成・署名するtool、SDへ書くA/B writerは別の役割です。[TUF公式の実装一覧](https://theupdateframework.io/docs/getting-started/)を入口に、Python-TUF、go-tuf、rust-tuf、toughと、公開側のtuf-on-ciを調べました。tuf-jsやphp-tufもありますが、JavaScript/PHP runtimeを製品へ入れていない本機の最初の実験対象にはしません。言語の違いだけで安全性や資源量を順位付けしません。

2026-11-02に、Release API、固定したcommitのREADME・依存定義・検証／保存処理・license、crates.ioの公開版を静的に照合しました。取得した資料と失敗は[sources.json](sources.json)に残します。取得成功は全機能の精読や脆弱性の不存在を意味しません。全候補のcross build、相互運用、AArch64上の実行、RSS・起動時間・転送量・最終依存の測定は本リポジトリでは試していません。

## 版を混同しない

| 候補 | 確認した版と固定commit | 読み違えない点 |
|---|---|---|
| Python-TUF | `v7.0.1`、`49eb1da48c58cf0cbb0f2e490f7ad39fbd8c1f15` | 既存比較の開発HEADとは別。公開Releaseを基準に今回のAPIを読む |
| go-tuf | `v2.4.2`、`f5edbde31e5507f46db2069402dc38903fe6d9d4` | import pathも`/v2`。古いv1のAPI・保存方法を流用しない |
| tough | crates.ioでは`0.24.0`。確認したソースは`98d8eb8b2ce63515d9b4981c938ef6453c5b5771` | GitHubのlatestは`tuftool-v0.17.0`。同じtreeのclient crateは`0.24.0`で、CLIと版が違う。古いdocs.rsの`0.17.1`を最新としない |
| rust-tuf | 開発treeは`219ca7d05818d5dd44ec4e32ab47c5ce64a7bf44`、crate定義は`0.3.0-beta15` | latest Release APIは404。crates.ioの直近公開は`0.3.0-beta14`、安定版fieldは`0.2.0`。開発treeの依存やMSRVを公開beta14の条件と読み替えない |
| tuf-on-ci | `v0.21.0`、`662382a8295b89a9d538390ce8b9bb85b207a93d` | OSのRelease版でも端末用clientの版でもない |

rust-tufのregistry応答は`newest_version=0.3.0-beta14`、`max_version=0.3.0-beta9`でした。公開日時とSemVerの順位を分けます。`beta14`と`beta9`は英数字の識別子であり、`beta.14`と`beta.9`の数値部分の比較とは異なります。404だけで保守停止とは判断しません。

## 端末側の候補

| 候補 | 固定ソースで確認した契約・依存 | 統合費用と残る検証 |
|---|---|---|
| Python-TUF | `ngclient`がclient、metadata APIが低水準処理。Python `>=3.10`、`securesystemslib~=1.0`、`urllib3~=2.0`。repository APIはstable APIの一部ではない | 参照実装として読みやすく、host側の比較対照に適する。targetへPython・暗号依存を追加する費用、最終image/RSSと起動時間は未測定 |
| go-tuf v2 | client API、delegation、consistent snapshotsを説明。`go.mod`はGo `1.25.0`。moduleにはsecuresystemslib、Sigstore、CLIや試験用の依存もある | clientだけのimport graphと最終binaryを採取する。moduleにある全依存が端末binaryへ入るとはしない。Go runtime、GC、CA store、cross buildと保守追従の費用を測る |
| tough | Rust clientとtuftoolを分離。`aws-lc-rs`、Tokio、serde等。HTTP featureはreqwest・rustlsの経路、FIPSは別feature | 現行OpenSSLだけで完結する差替えではなく、AWS-LC等のC部分を含むcross buildが増える。HTTP、CA、runtimeの選択を固定して測る。FIPSが本機に必要とは判断しない |
| rust-tuf | 開発treeはRust edition 2024、MSRV `1.88.0`、ring、chrono、serde等。repository I/Oを抽象化し、HTTP adapterは別crate | READMEはbeta・API不安定と警告する。I/Oや保存を狭い境界へ統合する余地がある反面、application側の責務を減らせるとは限らない。公開版との違い、adapter、interopの範囲を調べる |

主な一次資料は、[Pythonの依存定義](https://github.com/theupdateframework/python-tuf/blob/49eb1da48c58cf0cbb0f2e490f7ad39fbd8c1f15/pyproject.toml)、[GoのREADME](https://github.com/theupdateframework/go-tuf/blob/f5edbde31e5507f46db2069402dc38903fe6d9d4/README.md)と[go.mod](https://github.com/theupdateframework/go-tuf/blob/f5edbde31e5507f46db2069402dc38903fe6d9d4/go.mod)、[toughのCargo.toml](https://github.com/awslabs/tough/blob/98d8eb8b2ce63515d9b4981c938ef6453c5b5771/tough/Cargo.toml)、[rust-tufのCargo.toml](https://github.com/theupdateframework/rust-tuf/blob/219ca7d05818d5dd44ec4e32ab47c5ce64a7bf44/tuf/Cargo.toml)です。Buildrootの対応言語だけで、この版を現行Bootlin toolchainへ統合できると断定しません。

## 設定しなければ得られない保護

### 永続状態と電源断

[toughのloader](https://github.com/awslabs/tough/blob/98d8eb8b2ce63515d9b4981c938ef6453c5b5771/tough/src/lib.rs)は、指定したdatastoreをrollback検出に使います。未指定では一時directoryです。[datastore実装](https://github.com/awslabs/tough/blob/98d8eb8b2ce63515d9b4981c938ef6453c5b5771/tough/src/datastore.rs)には前回時刻の保存・後退検査がありますが、`tokio::fs::write`による保存を、そのままext4/SDでの電源断耐性や耐改ざん時計と認定しません。

[Goの保存処理](https://github.com/theupdateframework/go-tuf/blob/f5edbde31e5507f46db2069402dc38903fe6d9d4/metadata/updater/updater.go)と[Pythonの保存処理](https://github.com/theupdateframework/python-tuf/blob/49eb1da48c58cf0cbb0f2e490f7ad39fbd8c1f15/tuf/ngclient/updater.py)はtemporary fileからrename/replaceする経路です。確認した関数にはfileと親directoryの`fsync`がありません。renameの原子性と、実電源断後の永続性を区別し、上流の保存契約と本機のtransaction設計を照合します。独自にfileをコピーし直せば十分とも扱いません。

rust-tufは`RepositoryProvider`/`RepositoryStorage`へI/Oを委ねます。どのadapterでも永続・同期済みになるという契約ではありません。全候補で、root履歴、最高受理metadata版、時刻の下限、install transactionの各保存点を障害注入の対象にします。

### 期限・長さ・探索数

toughの`ExpirationEnforcement`は既定`Safe`で、`Unsafe`ではTUFの鮮度保証を失うと明記します。Goの`UnsafeLocalMode`も通常のonline refreshとは別経路です。時刻やnetworkの不具合を、これらのmodeへの自動切替で回避しません。

[PythonのUpdaterConfig](https://github.com/theupdateframework/python-tuf/blob/49eb1da48c58cf0cbb0f2e490f7ad39fbd8c1f15/tuf/ngclient/config.py)はroot更新256回、delegation 32、root 512,000 B、timestamp 16,384 B、snapshot 2,000,000 B、targets 5,000,000 Bが既定です。toughのLimitsはroot/timestamp/snapshot 1 MiB、targets 10 MiB、root更新1,024回です。これらは本機の推奨値ではなく比較用の既定値です。署名されたlengthがlibraryのfallback上限を置き換える場合もあるため、信用した署名者の誤設定にも耐える端末の絶対上限を別に設けます。

metadataを自作JSON処理へ置き換えず、libraryの検証順序・署名対象・delegationを維持します。applicationのfield、download上限、書込み先の認可は別に検証します。

## 公開側の再利用

[tuf-on-ciの運用文書](https://github.com/theupdateframework/tuf-on-ci/blob/662382a8295b89a9d538390ce8b9bb85b207a93d/docs/REPOSITORY-MAINTENANCE.md)は、署名event、root/targetsの承認、snapshot/timestampの生成、Pagesへのpublishを扱います。公開先を変える余地もあります。これは独自の署名儀式・期限監視を作る前の有力な比較対象です。

ただし、既定のartifact管理はgit内の`targets/`を使います。数百MiBのOS bundleをこのリポジトリへcommitする提案ではありません。Release上の不変payloadを参照する小さな署名済みdescriptorをTUF targetにする案と、外部payloadを直接targetにする構成を比較します。descriptor案はschema、hash/length、認可するURL、二段階検証、publisher改修が増えます。templateの高い権限を既存workflowへ丸ごとコピーせず、署名job・公開job・再署名jobを分離します。上流の「安全」という説明を本機での検証済みの保証には転用しません。

## license・保守・実験の提案

取得した先頭licenseは、Python-TUF、rust-tuf、toughがMIT/Apache-2.0の選択、go-tufがApache-2.0、tuf-on-ciがMITです。これはtop-levelの確認で、crypto provider、vendored code、生成binaryのlicense・NOTICE・source提供義務の閉包ではありません。採用時は実際のfeatures/import graphでSBOMとlicenseを出し、最新版・advisory監視へ追加します。

確認時に全5repositoryの`archived`はfalseでしたが、長期保守の保証ではありません。go-tufの[SECURITY](https://github.com/theupdateframework/go-tuf/blob/f5edbde31e5507f46db2069402dc38903fe6d9d4/SECURITY.md)は最新版本のみを対象とし旧版へ遡及修正しない方針です。他候補も報告窓口の存在だけで旧版のサポート期限を推定しません。

rust-tufの[README](https://github.com/theupdateframework/rust-tuf/blob/219ca7d05818d5dd44ec4e32ab47c5ce64a7bf44/README.md)はfull disclosure、[SECURITY](https://github.com/theupdateframework/rust-tuf/blob/219ca7d05818d5dd44ec4e32ab47c5ce64a7bf44/SECURITY.md)は非公開報告を指示し、同じtree内で食い違っています。公開報告を自動で実行する根拠にはせず、採用前に窓口を確認する項目として残します。

最初の実験は、**Python-TUFをhostの比較対照、go-tuf v2とtoughをtarget候補**にします。まず同じ小さなrepository・Ed25519鍵・障害fixtureで拒否結果を比べ、その後にAArch64のbuild・最終依存・RSS・起動・転送と永続化を測ります。rust-tufは公開betaと開発HEADのAPI・adapter差を解消してから同じ試験へ加えます。この順序は実験費用を抑える提案で、製品への採用決定ではありません。
