# OpenSSL 3.6.5から3.5.9への系列変更

2026-11-12。版・保守・4系の判断は[保守記録](../dependencies/openssl-maintenance.md)、生成物と回帰は[実験記録](../../experiments/2026-11-12-openssl-3.5-lts.md)に分けます。3.5 LTS採用は利用者の決定です。別TLS library、自作暗号実装への置換は[既存の暗号比較](../alternatives/crypto.md)と単一OpenSSL方針により今回の対象外です。

## 全変更履歴の比較範囲

[3.6.5 CHANGES](https://github.com/openssl/openssl/blob/openssl-3.6.5/CHANGES.md)の3.6.0から3.6.5までと、[3.5.9 CHANGES](https://github.com/openssl/openssl/blob/openssl-3.5.9/CHANGES.md)の3.5.0から3.5.9までを参照しました。系列番号の大小を更新順に並べるのではなく、共通の3.5基盤、3.6追加機能、両系列の後続修正を分けます。表の件数はCHANGESの最上位項目数で、CVE件数ではありません。

| release日 | 3.6側（項目数） | 3.5側（項目数） | 分類・扱い |
|---|---|---|---|
| 2025-04-08 - 09-30 | 3.5から分岐 | 3.5.0（37）、.1（2）、.2（1）、.3（8）、.4（6） | 共通基盤を比較。ML-KEM/ML-DSA/SLH-DSA、QUIC server、複数key share、DRBG/provider選択、CLIのAES既定値、Ed25519のrawin暗黙指定は3.5にもあり、3.6専用ではない |
| 2025-10-01 | 3.6.0（35） | 3.5.4が直前 | 下の新機能・既定値の後退を許容。3.6専用APIを新規に使わない |
| 2026-01-27 | 3.6.1（19） | 3.5.5（15） | PKCS12/CMS/ASN1/TS/BIO、TLS圧縮証明書、dgst切捨て等のsecurity修正は3.5側にも収録。3.6のOCSP regression修正を共通機能の修正と誤認しない |
| 2026-04-07 | 3.6.2（11） | 3.5.6（9） | RSA KEM、DANE、delta CRL、CMS、hex、proxy、平文HTTP検出を保持。3.6のAVX-512 AES-CFB修正・性能regression修正は別 |
| 2026-06-09 | 3.6.3（21） | 3.5.7（19） | PKCS7/CMS/QUIC/ASN1/CRMF/FFC-DH、AEAD、PSK、kTLS等を保持。3.6新OCSP確認機能の2修正は別 |
| 2026-08-25 | 3.6.4（15） | 3.5.8（14） | QUIC/CMS/CMP/RPK/DTLS/AEAD、ticket期限7日、armcap文書、icx対応を保持。OCSP確認のleak修正だけは3.5側の項目にない |
| 2026-09-29 | 3.6.5（17） | 3.5.9（17） | DTLS、CRLDP、QUIC、EC/SM2、SSL_CTX切替、CMP、EVP復号の戻り値、HTTP downgrade、FIPS advertised algorithm、MSVC flagの変更を保持 |

3.6側にのみ記載されたCVEは`CVE-2026-28386`、`CVE-2026-35188`、`CVE-2026-42765`、`CVE-2026-54876`です。最初の3件は[4月7日](https://openssl-library.org/news/secadv/20260407.txt)・[6月9日](https://openssl-library.org/news/secadv/20260609.txt)のadvisoryが3.5を対象外と明記します。最後のOCSP leakは3.5 CHANGESに記載がなく、対象外の明文は未確認です。番号がないだけで安全とは認定しません。3.5側の2025年CVE修正も、3.6側に同名項目がないだけで未修正とは解釈しません。

11月10日の5修正はどちらの公開版にも収録されていません。今回backportしない決定と、3.5.10を別途追う計画は保守記録に記載します。licenseは両版ともApache-2.0で、LICENSE.txtのhashは同じです。

## 3.6専用の新機能・option・既定値を失う範囲

| 機能・token | 3.6.5から3.5.9で変わること | 現行・計画利用者と採否 |
|---|---|---|
| `EVP_KDF_CTX_set_SKEY`、`EVP_KDF_derive_SKEY`、`EVP_PKEY_derive_SKEY` | opaque対称鍵によるderive/exchange拡張を失う。EVP_SKEY本体は3.5にもある | 現行のCLI Ed25519検証・kmod署名表示には不要。計画packageでの採用を確認しておらず、追加時にAPIを再確認 |
| `i2d_PKCS8PrivateKey`、NIST security category、配列allocation、`OPENSSL_sk` free thunk、thread-local API拡張、`X509_CRL_get0_tbs_sigalg`、HKDF digest OID | 3.6追加APIと内部実装を失う | 現行buildを回帰対象とする。計画packageの全source/API使用の網羅検査は未実施。必要になれば系列判断を再開 |
| `lms`、FIPS SLH-DSA import PCT、FIPS deterministic ECDSA | LMS検証、FIPS向け追加処理を失う。3.6の`lms`は既定無効 | 現行はEd25519署名でLMS/FIPS認証を要件にしない。SAE/EAPを検証済みとはしない |
| QUIC FIN ACK完了通知、`SSL_poll`、TLS 1.3 OCSP multi-stapling、`-ocsp_check_leaf`、`-ocsp_check_all`、`-status_all`、複数`-status_file` | 新通知・確認CLIを失う | 現行はQUIC/TLS serviceを提供していない。curl等で必要になった時に再確認。3.5のQUIC自体は残る |
| CMS `KEMRecipientInfo` / ML-KEM | CMSの追加形式を失う | 現行bundleはraw Ed25519で不要。RAUC/SWUpdateの将来のbundle形式・相手を選ぶ時に再確認 |
| `SSL_OP_SERVER_PREFERENCE`、`SSL_OP_LEGACY_EC_POINT_FORMATS` | 前者の新名と後者のflagを失う。EC point formatはuncompressedだけという3.6既定から以前の既定へ戻る | TLS利用者を製品へ入れる前にpolicyを明示。今回、互換性を既定値に任せた接続成功とは主張しない |
| PKCS12 `macsaltlen` | 既定16から8へ戻る | 現行更新形式にPKCS12は使わない。将来の証明書生成では必要なsalt長を明示 |
| `file:relative/path`、`openssl pkey -outform DER` / `-traditional` | OSSL_STOREの絶対path要件に戻り、旧鍵種のDER出力は既定PKCS8ではなくtraditional形式へ戻る | 現行署名処理は固定の鍵fileとPEM、`pkeyutl`を使う。予定toolのURI/DER処理は導入前に検査 |
| `configutl`、`CRYPTO_MEM_SEC`、`CRYPTO_MEM_SEC_MINSIZE`、`openssl-env(7)` | 設定dump tool、CLIのsecure heap初期化用環境変数、新文書を失う | 現行起動・更新scriptは使わない。秘密情報の扱いはsecure heapの有無だけで保証しない |
| C99要件、VxWorks削除、`build_inst_sw`、`build_inst_programs`、`allocfail-tests` | build要件・target・make test分離が旧状態へ戻る | AArch64/Linuxとhost Linuxを対象とし、既存recipeの通常buildを維持。VxWorks/追加test targetは使わない |
| AArch64 AES-CBC+HMAC、LoongArch/RISC-V SHA/SM3/MD5、x86 SM3/SM4/SHA512/AES-CFB最適化 | 3.6の高速化を失う | targetはAArch64。CBC+HMACの性能差を許容するが未測定。host最適化差も性能保証しない |
| EC keygen error queue、OSSL_PARAM parser生成、JSON stdbool、Win64 warning修正 | 内部実装・診断の改善を失う | 現行処理の正常・拒否試験で回帰を確認。内部最適化を保守期限より優先しない |
| 3.6.1以降の系列固有修正 | `X509_V_FLAG_CRL_CHECK_ALL`単独指定、OCSP応答の生成・所有権、`x509 -checkend`終了値、3.6の性能regression等 | 元の3.6変更と、その後の修正を一緒に評価する。3.5側に同名の項目がないだけで同じregressionがあるとはしない。現行署名経路はこれらを呼ばず、予定のTLS・証明書操作は採用時に再検査 |

この表の「不要」は現行用途についての判断です。wpa_supplicant、curl、RAUC、SWUpdate、OpenSSH、Python sslをこの変更でbuildしたわけではありません。各packageの4系影響は保守記録にあります。将来の設定で3.6専用APIを使っていないことまでは証明していません。

## build optionの機械照合

[Configure token表](openssl-configure.csv)は両tagの`@disablables`とTLS/DTLS列挙から抽出した全150 tokenです。3.5.9は148、3.6.5は150、表へのmissingは0です。3.6追加は`lms`と`allocfail-tests`だけで、どちらも既定無効です。共通tokenの`%disabled`に差はありません。これは依存cascade、platform、実行時policyまで同じという意味ではありません。

一次資料は両tagの[Configure](https://github.com/openssl/openssl/blob/openssl-3.5.9/Configure)、[INSTALL](https://github.com/openssl/openssl/blob/openssl-3.5.9/INSTALL.md)と、固定Buildrootの[Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libopenssl/Config.in)・[recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libopenssl/libopenssl.mk)です。全CLIの引数をこの150件へ含めたとはしません。

| 層 | 現行指定・公開範囲 | 判断 |
|---|---|---|
| targetの共通引数 | `linux-aarch64`、`--prefix=/usr`、`--openssldir=/etc/ssl`、`threads shared`、`no-rc5 enable-camellia no-docs no-tests no-fuzz-libfuzzer no-fuzz-afl no-afalgeng no-engine zlib-dynamic` | 既存recipeを維持。3.5のconfigureが受理するかを実buildで確認 |
| Buildroot公開option | algorithm、SSL/SSL3/weak SSL、PSK、ENGINE、compression、Argon2、cached fetch、CMP、thread pool、ECX、module、QUIC、secure memory、SIV、SM2 precomp、trace | 版変更と削減を混ぜない。token表のrecipe列は条件付き引数の存在であり、選択結果ではない |
| host | `--prefix` / `--openssldir`はhost tree、`shared zlib-dynamic no-docs no-tests no-fuzz-libfuzzer no-fuzz-afl` | targetと引数は別。host版も3.5.9をbuildして実行 |
| recipe非公開option | `lms`、`allocfail-tests`等 | 今回追加しない。別途渡す場合、単なる`LIBOPENSSL_CONF_OPTS`追加はこのrecipeに読まれない。外部overrideでconfigure commandを替える設計・試験が必要 |
| 実行時 | `openssl.cnf`、provider load、algorithm property、TLS cipher/group、`OPENSSL_CONF` / `OPENSSL_MODULES`等 | build可否と許可は別。今回は設定を替えない。3.6追加の環境変数・CLIと既定値の差は上表 |

`no-tests`は製品の検証が不要という意味ではありません。[従来のユーザー空間option調査](userspace.md#openssl旧機能の削減と実行時policy)にあるlegacy/provider削減は、引き続き別の検証候補です。出典の取得時刻・hash・失敗は[記録](../dependencies/sources.json)を参照してください。

build後のsourceからのtoken照合は次で再現できます。表のdefault列は`Configure`の`%disabled`を読み、依存cascadeを適用する前の値です。非tokenのplatform名、alias、内部`crmf`、値を取るdirectory/API指定はこの母集団に含めません。

```sh
python3 - <<'PY'
import csv
import re
from pathlib import Path
tokens = set()
for variant, version in [('main', '3.6.5'), ('lts', '3.5.9')]:
    source = Path(f'output-openssl-{variant}/build/libopenssl-{version}/Configure').read_text()
    block = source.split('my @disablables = (', 1)[1].split(');', 1)[0]
    tokens.update(re.findall(r'"([\w+.-]+)"', block))
    for kind in ['tls', 'dtls']:
        block = re.search(r'my @' + kind + r'\s*=\s*qw\(([^)]+)\)', source)[1]
        for token in block.split():
            tokens.add(token)
            if token != 'tls1_3':
                tokens.add(token + '-method')
with open('docs/research/component-options/openssl-configure.csv') as stream:
    recorded = {row['option'] for row in csv.DictReader(stream)}
assert recorded == tokens, (tokens - recorded, recorded - tokens)
print(f'Configure tokens={len(tokens)} missing=0 extra=0')
PY
```
