# 暗号・TLSライブラリーの代替比較

[代替比較](README.md) / [署名・鍵・更新の信頼境界](signing.md) / [RESEARCH](../../../RESEARCH.md)

## 現行と比較の範囲

現行のOpenSSLを比較の基準にし、TLS、更新manifestの署名、imageのhashを別々に評価します。小さなライブラリーや新しい実装言語を選んだだけで、認証・入力検査・権限制限まで安全になるとは扱いません。

2026-11-02に、MSD/Linuxの`9f07c3b884ae4c63c22dc196fd02b6ee43932f6e`とBuildrootの`8b238854d909c9cce32ef9671d968b03e323b55d`を基準に確認しました。製品設定・固定版は変更していません。代替構成のbuild・実行・サイズ測定は本リポジトリでは試していません。

- [defconfig](../../../configs/msd_cardputerzero_defconfig)はOpenSSL libraryとCLIを選びます。固定Buildrootの`package/libopenssl/libopenssl.mk`は**3.6.5**です。targetの`msd-update`はCLIで署名を検証し、hostのpost-image処理もOpenSSL CLIで署名します。
- [post-build](../../../board/cardputerzero/post-build.sh)は、指定鍵がなければ開発用Ed25519鍵を生成し、公開鍵をrootfsへ入れます。[post-image](../../../board/cardputerzero/post-image.sh)はmanifestを`pkeyutl -sign -rawin`で署名します。開発用鍵の自動生成は、本番Releaseの鍵運用が完成している証拠ではありません。
- imageのSHA-256照合はBusyBox側の`sha256sum -c`です。署名だけを別libraryへ移しても、このhash処理を同時に置換する必要はありません。
- TLS libraryの存在と、CA・hostname・時刻を検証するHTTPS clientの配備は別です。Wi-FiやGitHub Releasesからの自動更新が完成したとも扱いません。

### 先に対処を検討する保守期限

[OpenSSLの公式方針](https://openssl-library.org/policies/releasestrat/)にある3.6系列の通常保守期限は**2026-11-01**で、今回の確認日には過ぎています。3.5 LTSは2030-04-08までと記載されています。固定Buildrootや別契約による継続保守は未確認です。「成熟した現行実装なので維持すればよい」とは結論しません。

候補は、保守されるOpenSSL系列への移行と機能削減、署名専用verifierとTLSの分離、TLS実装自体の置換です。API互換性だけで選ばず、全client、生成物、更新・復旧の試験を採用条件にします。3.5 LTSを含む候補系列の最新patch、全変更履歴、下流patchは、実際の更新PRで再確認します。ここでは期限の発見と比較までです。

## ライブラリーの比較

表のlicenseは、固定Buildroot recipeまたは取得した上流LICENSE・READMEで確認した代表表記です。file別例外、リンクする全依存、配布物のnotice・source提供条件まで確認したという意味ではありません。上流READMEのサイズ・速度や認証実績を本機の測定値・認証へ転用しません。

| 候補 | TLS・署名に使う機能 | 固定Buildrootと追加費用 | 再評価 |
|---|---|---|---|
| OpenSSL | TLSと広い暗号API、現行のEd25519 CLI。Apache-2.0 | `libopenssl`。現行はCLIとlibcrypto等を含む。hostとtargetの両方を調べ、不要な算法・provider・engine・protocolを減らす | **保守期限への対応が必要な比較基準**。library変更前に、対応系列と最小構成で得る効果を測る |
| LibreSSL | OpenBSD由来の整理、libtls、libssl/libcrypto。ISCと旧OpenSSL/SSLeay等が混在 | `libressl`は3.9.2。仮想`openssl`のtarget providerに選べるが、host providerは`host-libopenssl`に固定される。上流はOpenSSL 3 API非対応、OpenSSLとのABI互換なしを明記 | **実験候補**。OpenBSDの思想を採り入れることと、LibreSSLへの一括置換を同一視しない。現行`pkeyutl -rawin`等のCLI契約も未確認 |
| mbed TLS / TF-PSA-Crypto | TLS・X.509と設定で機能を選ぶ構成。代表licenseはApache-2.0 OR GPL-2.0-or-later | `mbedtls`は3.6.7。取得した新系列のREADMEでは暗号部がTF-PSA-Cryptoへ分離し、3.6 LTSとは構成が違う。署名用Ed25519 API・設定・CLI互換性は、この調査では確定していない | **TLSの実験候補**。4.xの説明を3.6の機能へ流用しない。上流の枝別保守方針と、別repository・submodule・生成tarballの内包物も監視する |
| wolfSSL / wolfCrypt | TLS 1.3、wolfCryptのEd25519。互換APIや算法を選べる | `wolfssl`は5.9.4。recipeは`--enable-all`と`--disable-all`を分ける。AArch64ではARM asmも選ぶ。GPL-3.0+というrecipeと、上流のGPLv3・指定software例外・商用licenseを区別する | **実験候補**。FIPS認証案件だけに用途を狭めた旧評価を改める。必要なAPI、証明書検証、CPU命令、license、返り値の扱いを確認する |
| GnuTLS | TLS 1.3、X.509、PKCS #11等。coreはLGPL-2.1+ | `gnutls`は3.8.13。libtasn1・libunistring・Nettle等を依存に持ち、OpenSSL互換部やtoolsは別条件。現在の署名CLI契約は置換できると確認していない | **実験候補**。TLS policyやtoken連携等の利点があり、単に「OpenSSLと同じなので利得なし」とはしない。一方、依存削減になるかは実測が必要 |
| Rustls + crypto provider | TLS 1.2/1.3。TLSのRust実装と暗号providerを分離。Rustls本体はApache-2.0 OR MIT OR ISC | `rustls`の専用recipeは今回の固定treeにない。Rust・Cargo、provider、CA検証、HTTP client、必要ならFFIを統合する。`aws-lc-rs`や`ring`等のC/asm・build依存も別に調べる | **実験候補**。全体をpure Rustと呼ばない。`pkeyutl`の代替でも汎用のbundle署名CLIでもない |
| BoringSSL | TLSとEd25519等のAPIを提供するOpenSSL系fork。LICENSEに複数の由来を含む | 専用recipeは固定treeにない。上流は一般利用を目的とせず、第三者へのAPI/ABI安定性を保証しないと明記 | **組み込む用途に限定して比較**。製品全体を同時に再buildできる未リリースOSでも、追随費用は残る。更新専用verifierだけのために増やす利点は未確認 |
| AWS-LC | libcrypto・libssl、Ed25519、Arm向け最適化。OpenSSL/ISC/Apache系等の混在 | 専用recipeは固定treeにない。libcryptoはC、libsslはC++。取得したREADMEにはdistribution packagingのSONAME・symbol versioning・共存headersがある | **実験候補**。BoringSSLと同じ理由だけで除外しない。Graviton等での試験・形式検証をCortex-A53上の全機能保証へ広げない |
| Botan | C++のTLS 1.3、X.509、Ed25519、PKCS #11等。BSD-2-Clause | `botan`は3.11.1。C++20、GCC 11以上、libstdc++、threads等が条件。機能別buildは可能だが、TLS・CLI・C++依存を含めた費用を測る | **実験候補**。複数の暗号用途・hardware連携が必要なら再評価。小さな署名helperだけの第一候補にはしない |
| BearSSL | TLS 1.2系の小さなC実装。MIT | `bearssl`は0.6。取得したsupport文書はTLS 1.3をdraftとする古い説明を含み、現在の全機能表として扱えない。TLS 1.3の提供は今回確認できていない | **用途限定**。サイズの説明だけでTLS 1.3前提の更新clientに選ばない。非対応の断定と、最新実装を確認できていないことを分ける |

Rustlsは、取得した開発READMEが0.24以降のprovider明示選択・crate分離を説明する一方、Release APIの観測tagは`v/0.23.46`でした。新しいREADMEの手順をそのtagのAPIだとは扱いません。取得したSECURITYの保守方針も、互換系列の最初のcrate公開日を基準にしており、最後のpatch公開日だけで保守期間を判断できません。

## 署名専用の候補

TLSを不要にできるかは、署名専用のhelperと、ほかのclientが必要とするlibraryを分けて考えます。OpenSSLにリンクする別の製品componentが残るなら、verifier追加だけではOpenSSLを削除できず、二重の保守が必要になる可能性があります。

| 候補 | 現行のraw Ed25519への対応 | 費用・注意点 |
|---|---|---|
| libsodium | `crypto_sign_verify_detached`系のsingle-part APIが候補。TLSは提供しない | 固定recipeは1.0.22、ISC。raw公開鍵・署名の長さ、初期化、失敗の終了値、PEMからの変換をhelper側で管理する。multi-part APIはEd25519phなので、そのまま置換しない |
| Monocypher | optionalの`monocypher-ed25519.c/.h`にRFC 8032のEd25519がある | 固定treeにrecipeなし。BSD-2-Clause OR CC0-1.0。基本のEdDSAとoptionalのEd25519を取り違えない。入力長の検査は呼出し側の責任で、公式manualも範囲外の入力をundefined behaviourとする。自作recipe・固定・試験・監視が必要 |
| Nettle / libgcrypt | 暗号primitiveとして再評価するが、現行CLI・鍵形式との接続は未確認 | recipeはNettle 3.10.2（GPL-2.0+ OR LGPL-3.0+、GMP依存）、libgcrypt 1.12.2（LGPL-2.1+、libgpg-error依存）。TLSではなく、bundleのparserや鍵運用も提供しない |
| wolfCrypt / Botan / AWS-LC等 | 上記libraryのEd25519 APIをhelperから使う候補 | TLS全体を入れずに切り出せる範囲を、その版のbuild設定・link mapで確認する。APIがあることと、小さなverifierを安全に配備できることは別 |
| libhydrogen | 取得したREADMEはCurve25519とGimliを基礎とし、他libraryとの相互運用をnon-goalに挙げる | ISC、固定treeにrecipeなし。小さい署名libraryという理由で、OpenSSLのEd25519署名を検証できる候補へ一括分類した旧記述を訂正する。現行署名の置換候補とはしない |

MonocypherのREADMEには、単体Makefileの既定として`-march=native`が記載されています。host向けの指定を本機へ持ち込まず、Buildrootのcross compiler・Cortex-A53向けflagsを渡す必要があります。署名専用helperでも、AArch64という名前だけではCPU命令・stack・alignment・syscallの適合を保証できません。

## 旧暗号を減らす場合の条件

目標は「legacy providerを使わない」と宣言することではなく、不要な実装を配布せず、必要な通信と更新が正しく成立する構成です。

1. Buildrootのsymbol、最終`.config`、上流Configure引数、リンクされたobject、実行時のprovider・protocol・cipherを別々に記録します。symbolが有効でも上流で既定無効の場合があり、逆も調べます。
2. 固定Buildrootの`wpa_supplicant/Config.in`と`wget/Config.in`には、OpenSSLのDES・MD4を`select`する箇所があります。未導入のclientを後から加えて旧算法が戻らないよう、EAP等の要件とrecipeの依存を照合します。`defconfig`で消す指定だけでは解決しません。
3. 更新署名用Ed25519、TLS key exchange用X25519、証明書署名、imageのSHA-256は用途が違います。EC系をまとめて無効にして、更新が検証できなくなる構成を合格にしません。
4. TLS 1.3専用を第一の試験案とし、接続先の証明書chain・hostname・SNI・署名algorithm、HTTP redirect先まで確認します。RSAを一括削除すると必要な証明書検証を失う可能性があります。古いendpointのための無条件fallbackは設けません。
5. PQC対応は別の比較軸です。PQCの機能名やFIPS認証版の存在を、本機のbuild・暗号module・更新署名の認証や耐量子性へ置き換えません。

## 採用前の検証と判断

まず、保守されるOpenSSLの最小構成を基準に、署名専用helper案と、HTTPS clientを含む別TLS案を比較する提案です。版更新、算法削減、library置換を一度に変えず、それぞれ失敗の原因を追える構成にします。

- **機能**: host署名とtarget検証の相互運用、改変・誤鍵・異常長の拒否、[署名側の試験](signing.md#採用前に行う試験)を通します。上流testsと、本機の更新・起動・rollbackを別々に実行します。
- **HTTPS**: CA未配備、誤hostname、期限切れ、未確定の時刻、未知のCA、redirect、切断・再開、size超過で安全に失敗するかを試します。`--insecure`等で試験を通しません。
- **CPU**: 実際のCortex-A53と同条件の命令・auxv、asmのdispatchとfallbackを確認します。別のArm CPUでの成功を流用しません。
- **費用**: 全clientを含めたrootfs圧縮前後のサイズ、library重複、常駐・最大RSS、stack、TLS handshake、署名検証、build時間を、条件を固定して5回以上測ります。機能を削っただけの差と区別します。
- **保守・配布**: target/host、provider、Cargo、FFI、生成tarball、CA dataをSBOM・license記録・版／脆弱性／保守期限の監視へ入れます。専用recipeがない候補は、その統合費用も含めます。

測定記録は[実験一覧](../../experiments/README.md)から辿れる形で、基準commit・実際のtoolとbinary hash・最終設定・生の値・失敗を保存します。今回は資料比較のみで、この試験の成功を報告するものではありません。

## 一次資料と未確認範囲

[sources.json](sources.json)に、取得時刻、固定ref、Git blob SHAとraw bytesのSHA-256、Release API、取得失敗を記録しました。次は判断に使った主な範囲です。

- [OpenSSL保守方針](https://openssl-library.org/policies/releasestrat/)と[3.6 EdDSA manual](https://docs.openssl.org/3.6/man7/EVP_SIGNATURE-ED25519/)。系列の保守期限とPureEdDSA／prehashの違いを確認しました。
- [LibreSSL README](https://github.com/libressl/portable/blob/65e21df9a3c62da3824cd261c60604f6d75eed2c/README.md)、[mbed TLS README](https://github.com/Mbed-TLS/mbedtls/blob/eff4330ae387a694b49848777a8a426daf74fdb2/README.md)と[保守枝](https://github.com/Mbed-TLS/mbedtls/blob/eff4330ae387a694b49848777a8a426daf74fdb2/BRANCHES.md)、[wolfSSL README](https://github.com/wolfSSL/wolfssl/blob/b1038eec768f7df0a7f3eb6b242df2b018ad1df8/README)と[license条件](https://github.com/wolfSSL/wolfssl/blob/b1038eec768f7df0a7f3eb6b242df2b018ad1df8/LICENSING)。API、依存分離、license・設定条件を確認しました。各repositoryの全変更履歴・全脆弱性の監査ではありません。
- [Rustls README](https://github.com/rustls/rustls/blob/f10706bf98de666bf3dafd9a5356e63b7520a1a5/README.md)と[SECURITY](https://github.com/rustls/rustls/blob/f10706bf98de666bf3dafd9a5356e63b7520a1a5/SECURITY.md)、[BoringSSL README](https://github.com/google/boringssl/blob/17b5a42023a2220f6b0912139e31ebccd9b98aad/README.md)、[AWS-LC README](https://github.com/aws/aws-lc/blob/dc2ba66ef7ef78c2e3f4d42444d17febb677215a/README.md)、[Botan README](https://github.com/randombit/botan/blob/cddfb873a793059aec58f19574cb2f7a615997e8/readme.rst)、[GnuTLS manual](https://www.gnutls.org/manual/html_node/Introduction-to-GnuTLS.html)。provider、保守・API・配布の制約、TLSと署名の役割を確認しました。
- [libsodium署名manual](https://libsodium.gitbook.io/doc/public-key_cryptography/public-key_signatures)、[Monocypher Ed25519 manual](https://monocypher.org/manual/ed25519)と[README](https://github.com/LoupVaillant/Monocypher/blob/907e90ddd4c78f02e0d49e90384e4197f7dcdf26/README.md)、[libhydrogen README](https://github.com/jedisct1/libhydrogen/blob/264bf429021972c83b2a1a0cda13a765ddc3e11f/README.md)、[BearSSL support文書](https://www.bearssl.org/support.html)。署名の種類・入力条件・用途と、資料が古い場合の限界を確認しました。

GitHubのlatest Release APIは取得時点の公開metadataであり、全major・LTSのサポート判定ではありません。Botanの同APIは404でしたが、READMEにはtarballと版の案内があり、公開停止とは判断しません。Monocypherの`manual/sign`は取得失敗として残し、取得できた`manual/ed25519`等と区別します。全sourceの精読・全licenseの閉鎖、候補binaryの検査は未完了です。
