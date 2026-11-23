# OpenSSLの限定した4機能を削る比較

[component option索引](README.md) / [既存の最小化調査](openssl-minimal.md) /
[実験の条件と結果](../../experiments/2026-11-23-openssl-features.md)

## 範囲

OpenSSL 3.5.9 LTSを維持し、CMP、QUIC、SSL trace、OpenSSLのcompressionだけを比較する。
C1のTLS最低版1.2・SECLEVEL=2、既存algorithm、provider、asm、DEFAULT groups、PQC、
thread pool、cached fetch、SM2 precomputed tableは変更しない。
性能設定の削減を容量の改善に混ぜず、C2への変更もしない。
LibreSSL等への置換、自前の署名検証器、CLI廃止は既存調査の却下・保留を引き継ぐ。

固定Buildrootの`package/libopenssl/Config.in`は公開・内部の38 symbolを定義する。
この比較ではBuildroot `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`を使う。
既存の大きい調査表が対象にした2026-11-12時点のcommitとは分ける。
全symbolの現行値、比較値、Configure指定と理由は[38行の表](openssl-features-buildroot.csv)にある。
Kconfigの`y`は上流での有効化を保証しない。ENGINE、MD2、SSL3等は上流既定やcascadeで無効になる。
固定版の全148 Configure tokenは[既存CSV](openssl-minimal-options.csv)を再利用する。
CSVの168行は最新版だけの20 tokenも含む。固定版の母集団へ混ぜない。
今回の比較は下表の4 tokenに限り、それ以外の採否を変更しない。
値を取るoption、alias、環境変数は[既存本文](openssl-minimal.md#値を取るoptionalias環境変数)を参照する。

## 利用者と一次資料

現行CI artifact `14813627892`の165 ELFを監査した。
OpenSSLを直接参照するのは`openssl`、`libssl`、`libcryptsetup`、`libkmod`、`legacy.so`。
cryptsetup、integritysetup、veritysetupはlibcryptsetupを経由する。
配送scriptでは`msd-update`が`pkeyutl -verify -pubin -rawin`を呼ぶ。
同梱の`tsget.pl`はPerlを必要とする補助scriptで、現行製品にはPerlがない。
module一覧中の`libcrypto`という文字列はkernel module名で、ユーザー空間のlink依存ではない。

OpenSSH、curl/libcurl、RAUC、wpa_supplicantはこのartifactでは未選択。
未選択であることを将来の不要の根拠にはしない。
[RAUC契約](../../design/rauc-update-contract.md)のCMS、X.509、TLS 1.2/1.3、
Ed25519/ECDSA/RSAを残す。固定RAUC 1.15.2の`src/signature.c`はCMS・X509 APIを使い、
CMPによる証明書の取得・更新は行わない。`src/network.c`はlibcurlの通常のHTTP転送を設定し、
HTTP/3を要求する`CURLOPT_HTTP_VERSION`を指定しない。

| 比較するtoken | 意味・現在の既定 | 利用者がない根拠と維持する境界 |
|---|---|---|
| `no-cmp` | CMPとCRMFを無効化。Buildrootは既定y | msd-updateのraw署名、libkmodのPKCS7解析、cryptsetupのKDF/cipherにCMP呼出しなし。RAUCのCMSとCMPは別機能。RAUCのCMS署名・X.509検証とcurlのTLS backendにCMP APIなし。CMSやCA/CSR節は削らない |
| `no-quic` | OpenSSLのQUICを無効化。Buildrootは既定y | 現行配送にQUIC consumerなし。RAUCはHTTP/3を要求しない。固定curl 8.23.0の`configure.ac`はHTTP/3にngtcp2とnghttp3等の追加backendを要求し、今回の契約はそれらを選ばない。curl全般がQUIC非対応という意味ではない。TCP上のTLS 1.2/1.3を残す |
| `no-ssl-trace` | `SSL_trace()`とs_client/s_serverの`-trace`を除く。Buildrootは既定y | 配送scriptと上記consumerに`SSL_trace()`や`-trace`の呼出しなし。curlの通信traceやOpenSSLの`-brief`は別。診断機能を一つ失うため、必要になれば再有効化する |
| `no-comp` | OpenSSLのSSL/TLS・証明書compressionを無効化。Buildrootは既定y | curlの`SSL_OP_NO_COMPRESSION`はTLS record圧縮を禁じる根拠に限る。TLS 1.3証明書圧縮の未利用は証明できない。下記の暗黙経路を別に調べる。RAUCのSignedDataとHTTP Content-Encoding、SquashFS、他packageのzlibは別機能 |

根拠は[OpenSSL 3.5.9 INSTALL.md](https://github.com/openssl/openssl/blob/openssl-3.5.9/INSTALL.md)、
[Configure](https://github.com/openssl/openssl/blob/openssl-3.5.9/Configure)、
[RAUC signature.c](https://github.com/rauc/rauc/blob/v1.15.2/src/signature.c)、
[network.c](https://github.com/rauc/rauc/blob/v1.15.2/src/network.c)、
[curl OpenSSL backend](https://github.com/curl/curl/blob/curl-8_23_0/lib/vtls/openssl.c)、
[curl configure.ac](https://github.com/curl/curl/blob/curl-8_23_0/configure.ac)。
固定sourceの公開URLとhash、API監査は本文と実験の証拠に残す。

### compressionの注意

`SSL_OP_NO_COMPRESSION`とTLS 1.3の証明書圧縮を混同しない。
固定3.5.9の`ssl/ssl_lib.c`は、利用可能な圧縮algorithmから証明書圧縮の既定の順序を作る。
`ssl/statem/extensions.c`の`tls_construct_compress_certificate()`は、圧縮algorithmがあり、
`SSL_OP_NO_RX_CERTIFICATE_COMPRESSION`で禁止されていなければ拡張を送る。
curl sourceに証明書圧縮APIの直接呼出しがないことだけでは、この暗黙経路を否定できない。
[固定版のAPI文書](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man3/SSL_CTX_set1_cert_comp_preference.pod)も、
明示設定がなければ利用可能な既定の順序をpeerへ送ると説明する。

現行配送にcurl/RAUCはない。一方、計画中のHTTPSでは同じOpenSSL backendを使うので、
この機能を「利用者なし」と断定しない。target probeのClientHelloも保存する。
TLS record圧縮が不要という根拠を、証明書圧縮も不要という採用理由へ拡張しない。
通信量・遅延の変化は今回の容量測定だけでは評価できない。
実targetでもbaselineだけが拡張27でzlibを広告し、candidateでは消えた。
全回帰と容量基準を満たしても、この根拠不足により4項目組の製品採用は見送った。
全38 symbolのCSVにあるcandidate列は実験条件であり、製品への採用値ではない。

## 残すもの

cryptsetup 2.8.7の`openssl_backend_init()`は独自contextにdefaultとlegacyを明示loadする。
legacyのloadはoptionalであり、欠けると全commandが必ず失敗するとは言えないが、
名前を指定して取得するcipher/digestと既存volumeの互換を監査せず削らない。
OpenSSL 3対応の`openssl_argon2()`は`EVP_KDF_fetch()`を使うので、
外部libargon2も選択されていることだけを理由にOpenSSLのArgon2を落とさない。
ENGINEは現行で無効だが、RAUCのBuildroot symbolは将来ENGINESをselectする。
RAUCの`pkcs11_engine=false`だけでそのselectが消えるとは扱わない。

providerの自動loadをC1で変えることと、buildからproviderを除くことは区別する。
`no-module`ではlegacyがbuilt-inへ移る場合があり、独立fileの削除量をそのまま利益に数えない。
暗号の名前を実行時に組み立てる未知のdlopenまで、文字列検索で否定したとはしない。

## vendorを編集しない適用

4項目ともBuildrootに公開symbolがあるので、追加patchやConfigure commandのoverrideは不要。
比較では生成した`.config`だけを切り替え、現時点のdefconfigは変更していない。
full build・容量・回帰による採否は実験記録に記した。
host-libopensslは別recipeであり、targetの4 flagをhostへ追加しない。
`zlib-dynamic`はrecipeに残るが、他consumerのzlibと混同して外さない。
実Configureでは追加引数はこの4個だけだった。cascadeでCRMF、qlog/unstable-qlog、
OpenSSL内のzlib/zlib-dynamicも無効になる。algorithm/providerの追加削除ではない。
上流の最新版とのtoken差・既定値差は既存CSVの4.1.0欄と分け、系列更新は行わない。
