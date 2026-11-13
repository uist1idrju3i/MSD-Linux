# PQCとhybrid TLS groupsの判断資料（未決定）

[OpenSSL削減案](openssl-minimal.md) / [実行時設定](openssl-minimal-runtime.md) / [索引](README.md)。
2026-11-13の資料です。**採否は利用者が決めます。製品のConfigure引数・openssl.cnf・署名形式は変更していません。**

## 3.5.9の既定groups

外部overrideが選ぶ3.5.9の`ssl/t1_lib.c`は、`DEFAULT`を次へ展開します。

```text
?*X25519MLKEM768 / ?*X25519:?secp256r1 / ?X448:?secp384r1:?secp521r1 / ?ffdhe2048:?ffdhe3072
```

`:`はtuple内のgroup、`/`は比較可能なsecurity levelのtuple境界です。serverはtuple優先度とclient/server preferenceに従い、必要ならHRR（HelloRetryRequest）を要求します。単純な「最初の共通groupを選ぶ」だけではありません。clientはtuple境界を無視し、全体の順序とkeyshare指定を使います。

`*`はclientが先送するkeyshare、`?`は未実装groupを無視する指定です。3.5.9のDEFAULTでは、実装が利用可能なら**X25519MLKEM768とX25519の2 keyshare**を送ります。普通の`X25519MLKEM768:X25519`は同じではなく、`*`が一つもなければ左端の利用可能groupの1 keyshareだけです。明示keyshareは最大4個。`-group`は先行listからの削除、`DEFAULT`は組込みlistの展開を意味します。

`no-ml-kem`でhybridが消えた場合も、DEFAULTの`?`により残るclassical groupへ進めます。存在しないgroupを`?`なしで明示すれば設定エラーになり得ます。algorithmのbuild可否、providerのload、applicationのgroups設定を別に確認します。

### ClientHelloの大きさと接続互換性

X25519MLKEM768のclient key exchangeは、ML-KEM-768の公開encapsulation key 1184 byteとX25519の32 byte、計1216 byteです。server側はML-KEM ciphertext 1088 byteとX25519の32 byte、計1120 byteです。これは証明書やTLS record全体のsizeではありません。

X25519単独のkey exchangeは32 byteです。hybrid単独へ置き換えると1184 byte増え、DEFAULTのように独立したhybrid shareも加えるとentry header 4 byte込みで1220 byte増えます。およそ1.1 KiBのPQC公開鍵が加わるという目安と、全ClientHello増加量を区別します。supported_groups等の差も別にあります。

TLS recordがTCP segmentをまたぐこと自体は正常です。ただし経路MTU、TCP segmentation、IP fragmentation、不適切なmiddleboxのTLS解析を混同しません。3.5.9の公式文書も、大きいClientHelloをfirewallが誤処理する稀な失敗・timeoutを注意しています。今回の6 host成功は、他のWi-Fi・企業proxy・VPN経路の保証ではありません。

公式の回避案`?X25519MLKEM768:DEFAULT`は、hybridを候補に残しつつその予測keyshareを重複抑制します。serverが選ぶ場合はHRR後に送ります。最初からX25519だけに固定する案とは異なり、hybridへの到達性と追加roundtripを交換します。これも製品へは適用していません。

## build optionと利用者

3.5.9 Configureのdisablablesと照合したPQC固有tokenは下表の3つで、missing=0です。全Configure optionは[既存の148 token表](openssl-minimal-options.csv)へ分けています。Kconfigにはこの3つの個別switchがなく、単なる`LIBOPENSSL_CONF_OPTS`追加も固定recipeには効きません。[容量実験](../../experiments/2026-11-13-pqc-groups.md)では既存overrideの版・recipeの実引数とpatchを引き継いだ、target専用のout-of-tree Configureを使います。製品用Make override commandの実装とは区別します。

| option | 3.5.9の既定・意味 | 今回の扱い |
|---|---|---|
| `no-ml-kem` | 指定なしではML-KEMをbuild。FIPS 203のKEMと、それを使うTLS hybridを削除 | 容量比較だけ。X25519等を残してもPQC機密保護は失う |
| `no-ml-dsa` | 指定なしではML-DSAをbuild。FIPS 204、Dilithium由来の署名 | TLS key exchangeの削除ではない。将来の更新署名・証明書対応とは別判断 |
| `no-slh-dsa` | 指定なしではSLH-DSAをbuild。FIPS 205、SPHINCS+由来のstateless hash署名 | ML-KEMともML-DSAとも別。今回のEd25519形式には不要だが将来性を失う |
| `no-lms`等 | **3.5.9に`lms`・`hss`・`xmss`のdisablableはない**。LMS用のflagを追加しない | 最新公開版4.1.0のConfigureには`lms`があり既定disabled。4系のoptionを3.5へ読み替えない |

`no-asm`、`no-ec`、`no-ecx`はPQCだけのswitchではありません。既存Ed25519等や速度を失うので今回の削減へ混ぜません。host OpenSSLも変えていません。系列更新・11月のadvisory対応は[保守調査](../dependencies/openssl-maintenance.md)の別課題です。

| consumer | 現状とPQCの到達性 |
|---|---|
| `msd-update` CLI | 現在は配備されたEd25519公開鍵によるraw署名検証。TLSを使わず、GroupsもML-KEMも現在の更新署名を強化しない。CLIがPQC commandを持つことと更新処理が使うことは別 |
| libkmod | 現在はlibcryptoをリンクし、PKCS7/X509等でmodule署名情報を解析。kernelのmodule署名検証とは別。TLS key exchangeをしないためGroupsのconsumerではない |
| openssl CLI | 現在はlibcrypto/libsslをリンク。任意の試験commandではPQCを使えるが、製品の通常処理が全algorithmを使うという意味ではない。更新framework移行後に`no-apps`を再検討 |
| 将来のwpa_supplicant | 現在未選択。OpenSSL backendのEAP-TLS等なら相手とapplication設定次第でhybridを使い得る。SAEのgroupとTLS Groupsは別で、TLSの設定だけでWPA3や無線dataをPQC化できない |
| 将来のRAUC／SWUpdate | 現在未選択。CMS署名とHTTPS取得は別層。ML-KEMは後者の機密性、ML-DSA等は将来の署名形式に関係する。framework・証明書・CMS・鍵typeが受理できるかは未試験 |
| 将来のSSH／API client | 現在未選択。OpenSSLを使うHTTPS APIはgroupsの影響を受け得る。SSHはTLSではなく、SSH側のKEX実装・設定を別に調べる。OpenSSL削減だけでSSHのPQC有無を判定しない |

Buildrootのrecipeと保存済みrootfsの依存走査は[既存調査](openssl-minimal.md#利用者と残す機能)にあります。将来consumerの全組合せを今回build・接続したわけではありません。

## endpointの観測

管理者の原文と同じVMからの1回の再確認を[実験記録](../../experiments/2026-11-13-pqc-groups.md)へ保存しました。clientはhost OpenSSL **3.5.5**で、target 3.5.9のWAN試験ではありません。比較するのは`X25519MLKEM768:X25519`と`X25519MLKEM768`です。後者は**hybridのみ**であって、単独ML-KEMではありません。

| host | hybrid＋X25519候補 | hybridのみ |
|---|---|---|
| github.com / api.github.com / codeload.github.com | X25519 | alert 40、handshake failure |
| objects.githubusercontent.com / release-assets.githubusercontent.com / muromi.moe | X25519MLKEM768 | X25519MLKEM768 |

再確認は管理者の観測と一致しました。ただしDNS/IP・edge・経路は固定していません。rawの`-brief`はHRR回数を測っておらず、colon listはDEFAULTの2 keyshareと同じ条件でもないため、latency比較にはしません。HTTP download・GitHub認可・attestation・public deliveryの成功も測っていません。

## HNDLと更新署名

HNDL（Harvest Now, Decrypt Later）は、暗号化通信を今記録して将来復号するリスクです。classical ECDHEのforward secrecyは、将来の量子計算で離散対数を解かれる場合まで守る保証ではありません。hybridはclassicalとML-KEMを組み合わせ、少なくとも一方が安全という構成上の仮定に備えます。標準化やlibraryへの収録だけで、実装の無欠陥や将来の安全性を認定しません。

現在の更新bundleは公開され、別途署名されています。payloadの機密性を長期に守る価値は小さい一方、取得履歴・接続metadata・認可token等が常に公開とは限りません。public bundleという理由で、将来の利用者API・credential・個人dataのHNDLも低リスクと扱うことはできません。Wi-Fi認証、SSH、APIはそれぞれprotocol、保存期間、相手の対応を決めて評価します。

TLS key exchangeをPQC化しても、現在のEd25519更新署名は量子耐性署名に変わりません。署名では将来の偽造・信頼鍵の長寿命が課題です。ML-DSAをbuildに残すだけでも解決しません。新しい署名形式、trust anchorの配備、旧／新鍵の重複期間、鍵IDとalgorithmの拘束、失効・rollback防止、旧端末の復旧を設計する必要があります。RAUC／SWUpdateのCMS受理形式・TLS signature scheme・単独EVP署名APIを同一視しません。[鍵と信頼状態](../release-client/trust-and-state.md)の未実装事項を先に詰めます。

## 選択肢と推奨（利用者の判断待ち）

| 案 | 利点 | 失うもの・確認事項 |
|---|---|---|
| DEFAULTと3 algorithmを維持 | 対応相手ではhybrid、非対応相手ではclassical。将来の署名検討も可能 | 容量・暗号演算・ClientHello増大を受け入れる。実機速度、企業middlebox、将来のEAP-TLSは未確認 |
| algorithmは残し`Groups=X25519` | 小さいClientHello。今回の6 hostでclassic候補を使える見込み | **library容量は減らない**。TLSのPQCを失い、P-256/P-384等しか使えないEAP相手も除外。今回X25519-onlyの全接続試験はしていない |
| `no-ml-dsa no-slh-dsa`、ML-KEMは維持 | TLS hybridを残し、現在未使用のPQC署名実装を削る | 将来の更新署名・証明書実験でrebuildが必要。双方削除の合算値は今回の単独削減値から推定しない |
| `no-ml-kem`または三つ全部を削除 | 容量と実装面を小さくする | hybrid接続・将来の署名選択を失う。残存DEFAULTのfallbackと全consumerの回帰が必要 |
| algorithmを残しhybridの予測shareだけ抑制 | 公式のClientHello縮小策として候補を維持 | 対応相手で追加roundtrip。自動で全middleboxを救う保証はない |

**暫定推奨はDEFAULTとML-KEMの維持を比較の基準にすること**です。速度優先の製品方針、将来の利用者通信、未測定の実機・経路互換を考え、容量だけでhybridを外さない案です。ML-DSA／SLH-DSAの削減は署名移行の方針と別に決められます。これは採用決定でも、実機性能が十分という判定でもありません。利用者には、公開更新専用機として機能を狭めるか、将来の機密通信を含めるかを容量実測と合わせて選んでもらいます。

## 一次資料

- 3.5.9の[groups APIとtuple・keyshare](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man3/SSL_CTX_set1_curves.pod)、[DEFAULT実装](https://github.com/openssl/openssl/blob/openssl-3.5.9/ssl/t1_lib.c)、[Configure](https://github.com/openssl/openssl/blob/openssl-3.5.9/Configure)、[INSTALL](https://github.com/openssl/openssl/blob/openssl-3.5.9/INSTALL.md)。
- [default providerのKEM／signature登録](https://github.com/openssl/openssl/blob/openssl-3.5.9/providers/defltprov.c)、[ML-KEM hybrid実装](https://github.com/openssl/openssl/blob/openssl-3.5.9/providers/implementations/kem/mlx_kem.c)、[ML-KEM](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man7/EVP_PKEY-ML-KEM.pod)、[ML-DSA](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man7/EVP_PKEY-ML-DSA.pod)。
- [最新版の配布表](https://openssl-library.org/source/)、[4.1.0 Configure](https://github.com/openssl/openssl/blob/openssl-4.1.0/Configure)。2026-11-13の取得時点で4.1.0と3.5.9を確認。系列を変更する提案ではない。
