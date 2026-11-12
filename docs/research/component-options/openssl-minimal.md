# OpenSSL 3.5.9の削減と設定強化（調査草案）

[component option索引](README.md)へ戻る。2026-11-12、基準は`d7d9d622eae2f5f78dc0b891203f3641f334123b`。**製品設定・recipe・binaryは変更していない。以下の「採用候補」は実験後の提案であり、採用済みという意味ではない。**

## 現在の入力と保存済みrootfs

固定Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`、recipe上は3.6.5。[外部override](../../../board/cardputerzero/package-overrides.mk)がtarget/hostの版を3.5.9へ固定する。[系列判断](openssl-series.md)と[保守記録](../dependencies/openssl-maintenance.md)は変更しない。3.5.9に未収録のadvisory修正を、機能削減で代替したとは扱わない。

サイズと実引数は[3.5 LTS実験](../../experiments/2026-11-12-openssl-3.5-lts.md)の保存済み`output-openssl-lts`から再採取した。現在のHEADから新しく構築したrootfsではない。[今回の採取値・hash](../../experiments/2026-11-12-openssl-minimal-plan.csv)は過去のfile一覧と一致する。圧縮率、RAM、速度の比較はしていない。

| rootfsの通常file | 論理byte数 |
|---|---:|
| `/usr/lib/libcrypto.so.3` | 5,200,792 |
| `/usr/lib/libssl.so.3` | 929,336 |
| `/usr/bin/openssl` | 959,488 |
| 上記3 ELFの合計（symlinkを含めない） | 7,089,616 |
| `/etc/ssl/openssl.cnf` | 12,411 |

保存済み`.config`は`BR2_SHARED_LIBS=y`、`BR2_OPTIMIZE_S=y`、`BR2_cortex_a53=y`、`BR2_PACKAGE_LIBOPENSSL=y`、`BR2_PACKAGE_LIBOPENSSL_BIN=y`。defconfigが明示するOpenSSL機能は後二者で、algorithm等の多数の`ENABLE_*`はKconfig既定の`y`を継承している。ENGINE本体は未選択である。

**Kconfigの`y`は上流機能の有効化を保証しない。** SSL3、weak SSL、MD2、dynamic ENGINE等のsymbolが`y`でも、recipeはそれらを明示enableせず、上流既定やcascadeによって無効になる。`UNSECURE=y`も「全ての弱い暗号が有効」という意味ではない。全OpenSSL Kconfig値と実際の無効理由は[採取JSON](../../experiments/2026-11-12-openssl-minimal-plan.json)の`buildroot_options`と`configdata.disabled`に分けて残す。

`configdata.pm`の`perlargv`が記録したtarget Configure引数は次のとおり。Make変数の未展開値やhostの引数ではない。

```text
linux-aarch64 --prefix=/usr --openssldir=/etc/ssl threads shared
no-rc5 enable-camellia no-docs no-tests no-fuzz-libfuzzer
no-fuzz-afl no-afalgeng no-engine zlib-dynamic
```

記録されたCFLAGSは`-D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64 -Os -g0 -D_FORTIFY_SOURCE=3`。compiler wrapperの今回のpreprocess呼出しでは、さらに`-mcpu=cortex-a53`、stack protector、PIE、RELRO等の付加を確認した。これは過去の全compile commandを回収したという意味ではない。host用recipeは別であり、targetの削減をhostへ一律に適用しない。

## 利用者と残す機能

全通常ELFの`DT_NEEDED`を走査すると、直接参照は`openssl`、`libssl.so.3`、`libkmod.so.2.5.1`、`ossl-modules/legacy.so`の4 fileだった。symlinkの重複は除いた。shellによるCLI起動、`dlopen`、静的リンクの全利用をこの走査だけで網羅したとはしない。

| 利用者 | 現在／予定と必要機能 | 削減時の条件 |
|---|---|---|
| [msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) | 現在。`openssl pkeyutl -verify -pubin -rawin`でEd25519署名を検証。payloadのSHA-256はBusyBoxの`sha256sum`を呼び、OpenSSL CLIのSHA-256ではない | CLI、PEM/DER鍵読取、Ed25519と内部SHA-512を残す。`no-ec`も`no-ecx`もEdDSA実装を落とすため却下 |
| kmod 34.2 | 現在。libkmodがlibcryptoをリンク。`libkmod-signature.c`の`d2i_PKCS7_bio`、X509、ASN1、OID等はmodule署名情報の解析・表示に使う | **kernelによるmodule署名検証とは別**。raw Ed25519だけを理由にPKCS7/X509を削除しない。CMSとPKCS7も同一APIではない |
| openssl CLI | 現在。libcryptoとlibsslをリンク | 更新処理がTLSを呼ばないことだけでは、現在のCLIからlibsslを外せない。`no-apps`は却下 |
| wpa_supplicant 2.12 | 現在未選択。固定recipeはOpenSSLがあれば`CONFIG_TLS=openssl`を選ぶ。WPA3 optionはSAE、SAE_PK、OWE、DPP、SuiteB等を一括enable | SAEはEC／必要ならFFC-DH、SHA/HMAC/HKDF等。EAP-TLSはX509、RSA/ECDSA、ECDH、AES等。全SAE group・全EAP methodの実装監査／接続試験は未実施 |
| EAP-PEAP/MSCHAPv2、FAST等 | 将来の相手ネットワーク次第 | MSCHAPv2のMD4/DES等とlegacy provider、FAST等のTLS-PSK利用を確認する。**WPAのPSKとTLS-PSKは別**。`no-psk`だけでWPA2-PSKを禁止するという解釈は誤り |
| Python ssl／hashlib | Python3は現在未選択。将来の`_ssl`はlibssl、`_hashlib`はlibcryptoを利用し得る | TLS 1.2/1.3、X509、digest、providerと実際の標準library試験を追加する |
| RAUC／SWUpdate | 現在未選択。導入時にはCMS署名、証明書とchain、RSA/ECDSA等の採用形式を決める | `no-cms`を採用する前に更新方式を決める。現在のraw Ed25519形式をRAUCでそのまま使えるとはしない |
| OpenSSH／Dropbear | 両方とも現在未選択。OpenSSHはlibcryptoの利用を想定し、TLS自体はSSH要件ではない。Dropbearの固定recipeはOpenSSLをdependencyにしない | OpenSSHではEd25519、X25519、RSA/ECDSA、AES、ChaCha20/Poly1305等を再確認。別backendや自前暗号実装へ置換しない |

将来の行はprotocolと固定recipeに基づく要求の整理であり、そのpackageの全optionを3.5.9でbuildしたという記録ではない。代替品は[既存の比較](../alternatives/README.md)も参照する。LibreSSL、wolfSSL、mbed TLSへの置換はCLI・provider・Buildroot依存の再統合を伴う。Ed25519専用の自前検証器も鍵parser・署名検証・保守責任を増やし、kmodや将来TLSを置き換えない。本件は利用者が選んだOpenSSL 3.5 LTS内で調整する案を推奨する。

## Configure optionの採否

全tokenの既定値、今回の無効状態、Buildroot公開面、採否・理由は[option表CSV](openssl-minimal-options.csv)を参照。3.5.9の`@disablables`とTLS/DTLS列挙の148 tokenを照合する。下表は判断の要点で、CSVの代用ではない。

| Configure指定 | 推奨判断 | 理由・注意 |
|---|---|---|
| `no-engine no-afalgeng`、devcryptoをenableしない | 採用維持 | 現在すでに無効。ENGINE、loader、PadLock等のcascadeも確認する。ARMという理由でkernel暗号backendを有効にしない |
| `no-legacy`、`no-rc2 no-rc4 no-md4 no-mdc2 no-idea no-seed no-bf no-cast no-rmd160 no-whirlpool` | 現行更新専用構成の削減候補。EAP方針の承認待ち | legacyをbuildしないことと、configで自動loadしないことは別。EAP互換を残すなら一律削除できない。MD2/RC5はすでに無効 |
| `no-des`、`no-dsa`、`no-camellia no-aria no-sm2 no-sm3 no-sm4` | 要測定・相手の要求確認 | 現行更新では不要だが、証明書・無線・SSH等の条件を限定してから削る。Camelliaの削減はrecipeの`enable-camellia`固定も処理する |
| `no-ec no-ecx`、`no-apps` | 却下 | 更新CLIのEd25519を失う。providerの`signature/build.info`は`!disabled{ec}`と`!disabled{ecx}`の両条件で`eddsa_sig.c`を組み込む |
| `no-chacha no-poly1305 no-ecdh no-ecdsa no-dh` | 初期案では却下 | 将来TLS/SAE/SSHを狭める。特に暗号命令のないA53ではChaCha20を残して実測する |
| `no-deprecated`、`--api=3.0.0`等 | 要測定。初期案では保留 | `--api`単独は削除ではない。併用時に指定版以下のdeprecated APIを落とす。省略時のAPI levelは現在のminor版。全consumerのcompile／実行確認が必要 |
| `no-ssl3`、`no-weak-ssl-ciphers` | 明示して維持する候補 | 現状も上流既定で無効。KconfigのSSL3=`y`は有効化の証拠ではない。`no-ssl`はSSL3のaliasであり、TLS全削除ではない |
| `no-tls1 no-tls1_1`、対応する`-method` | 採用候補／method削除はAPI試験後 | 前者はversion negotiationを止めるだけ。method APIもなくす指定とは分ける。TLS 1.2/1.3を残す |
| `no-dtls`、`no-dtls1-method no-dtls1_2-method`、`no-quic no-srp no-srtp` | 現行用途の削減候補 | TCP TLSと更新は維持するが、将来のDTLS／QUICアプリは別構成になる。SRPとTLS-PSKも別 |
| `no-comp`、`no-zlib no-zlib-dynamic` | 採用候補 | TLS／証明書圧縮やOpenSSLのzlib loadを不要にする。現在は`zlib-dynamic`なので実引数の置換が必要。kmod等のzlibまで消してよいとはしない |
| `no-psk` | EAP method確定まで保留 | TLS-PSKを必要とする認証と、TLS 1.3 resumptionを別に試験する。WPA passphrase認証との名前の一致で決めない |
| `no-cms no-cmp no-ocsp no-ct no-http no-ts no-rfc3779` | 機能別に要測定 | CMP等は削減候補だが、CMSは将来の更新、OCSP等は証明書検証の設計に関係する。一括採用しない |
| `no-ml-kem no-ml-dsa no-slh-dsa` | 利用者の量子耐性方針待ち | 3.5のPQCを失う。Groupsからhybridを外す案と同じ判断として扱い、容量削減だけで自動採用しない |
| `no-module no-dso` | 要測定 | **`no-module`だけではlegacyは消えず、libcryptoへbuilt-inになる**。`providers/build.info`で確認。外部provider／PKCS#11の計画も変わる |
| `no-shared` | 初期案では却下 | 現行の動的consumerとBuildroot全体のlink方式に関わる。libcryptoだけ静的化して総rootfsが縮むとは限らない |
| `enable-ktls` | 今回は不採用 | 現在は無効。TLS bulk I/O利用者も測定もなく、kernel側のKconfig・cipher・RX/TX対応が別途必要。CPUにAES命令を追加する機能ではない |
| `no-asm`、`+crypto`の強制、`OPENSSL_armcap`の正のbit強制 | 却下 | 既存AArch64 asm／runtime dispatchを残す。存在しない命令を実行させない |
| `-Os`／`-O2`／`-O3`、LTO | `-Os`維持、他は要測定 | 現行はサイズ優先。`-O2`の実機性能と容量を比較し、`-O3`やLTOを無条件に速いとしない |

`no-aes`、`no-rsa`、`no-sha256`、`no-sha512`はこの3.5.9の公開disablable一覧にない。古いブログの削減flagをそのまま追加しない。SHA-256は将来のTLS等にも残し、Ed25519内部のSHA-512も失わない。

### 値を取るoption、alias、環境変数

| 入力面 | 既定・採否 |
|---|---|
| `--prefix`、`--openssldir`、`--libdir`、`--cross-compile-prefix` | 前二者はrecipeの`/usr`、`/etc/ssl`を維持。libdirとcross prefixはtoolchain／layoutの既存解決を維持。削減用に変更しない |
| `--with-rand-seed`の`os/getrandom/devrandom/egd/rdcpu/none/jitter` | OS乱数を維持。`none`、EGD、jitter追加は採らない。ARMv8.0の本機でCPU乱数命令を仮定しない |
| `--with-zlib-include/lib`、`--with-brotli-include/lib`、`--with-zstd-include/lib`、`--with-jitter-include/lib` | 非使用backendの探索pathを追加しない。圧縮を削るならConfigure機能と依存を整合させる |
| `--debug`、`--release`、`--strict-warnings`、`--fips-key` | releaseと既存CFLAGSを維持。debug／strict warningsは検証専用の別出力。FIPS keyを製品署名鍵と混同しない |
| `--config`、`--banner`、`--w`、`--help`、`--api` | 独自platform設定や表示変更はしない。helpは調査用。API削減は上表の別実験 |
| `enable-crypto-mdebug-backtrace`、`no-hw-padlock`、`no-hw`、`no-ripemd`、`no-ui`、`386` | 前者はdeprecatedの無効果指定。PadLock／hwは旧ENGINE系、ripemd／uiはalias。x86用386は本機に不適用。重複指定を増やさない |
| `AR/ARFLAGS/AS/ASFLAGS/CC/CFLAGS/CXX/CXXFLAGS/CPP/CPPFLAGS/CPPDEFINES/CPPINCLUDES/HASHBANGPERL/LD/LDFLAGS/LDLIBS/RANLIB/RC/RCFLAGS/RM` | INSTALLのcompile入力。Buildrootのtarget値を継承し、host値や`-march=native`を混ぜない |
| `BUILDFILE/CROSS_COMPILE/KERNEL_BITS/NM/OPENSSL_LOCAL_CONFIG_DIR/PERL/WINDRES` | platform・build設定。生成物名や探索先を削減用に変えない。環境からの意図しない持込みも記録する |

INSTALLのmacro表記はprotocol／algorithm tokenへ展開した。内部`crmf`、廃止された`ssl2/buf-freelists/heartbeats`は独立した採用候補から除く。compiler固有の`-D/-I/-L/-l/-Wl`等はGCCの全optionをこの表へ展開せず、[toolchain調査](buildroot-toolchain.md)へ分ける。

上流最新版の公式配布表は4.1.0、3.5 LTSの最新公開版は3.5.9だった。今回取得した4.1.0 Configureは154 tokenで、3.5.9から追加20・削除14。ENGINE／SSL3系の削除や、新しいDTLS 1.3・ECH・KDF類を3.5へ読み替えない。CSVのlatest欄はtokenとcascade前の既定値だけを比較し、API／ABIや全既定動作の互換を認定しない。3.6との詳しい差は既存の系列比較へ分ける。

## vendorを変更しない受け渡し

公開Kconfigで表現できる削減は外部defconfigで明示し、正規化後の`.config`と実`perlargv`を比較する。`no-legacy`、`no-deprecated`等を渡す`LIBOPENSSL_CONF_OPTS`は固定recipeに読取箇所がなく、単に追加しても効かない。

固定Makefileは`BR2_PACKAGE_OVERRIDE_FILE`を組込みrecipeより前に読む。追加flagが必要なら、既存の外部override fileに`override define LIBOPENSSL_CONFIGURE_CMDS`を定義し、固定recipeのtarget command全体を保った上で末尾へ明示flagを加える方式を候補とする。通常の`define`では後のrecipeに上書きされる。作業はtarget用に限定し、`HOST_LIBOPENSSL_CONFIGURE_CMDS`は変えない。

これはsource順序とGNU makeの優先順位からの設計案で、今回そのoverrideを実装・buildしたわけではない。最初にMakeの展開値と実Configure引数で検証する。`CFLAGS`、threads、shared、toolchain引数、prefix、hash/patch/依存・install処理を欠落させず、固定の`enable-camellia`や`zlib-dynamic`との競合も解消する。recipe更新時に差分を再監査する負担を負う。遅いexternal.mkで版だけを変更したり、arch文字列へflagを埋め込んだり、`-DOPENSSL_NO_*`で生成headerとの整合を迂回したりしない。

## 実行時設定とARM最適化

[openssl.cnfとARMの検討](openssl-minimal-runtime.md)に設定案、providerの制限、BCM2837の一次資料と実機での確認を分ける。いずれも未適用・未測定である。

## 実験と承認待ち

[実験計画と採取記録](../../experiments/2026-11-12-openssl-minimal-plan.md)へ段階、固定条件、数値基準、負の対照をまとめた。次に必要な判断は古いEAPとの互換を残すか、CMS更新方式を予定するか、PQCを残すか、容量と速度の優先度をどうするかである。機能削減と3.5.10への更新を同時に比較しない。

## 一次資料

- [OpenSSL 3.5.9 INSTALL](https://github.com/openssl/openssl/blob/openssl-3.5.9/INSTALL.md)、[Configure](https://github.com/openssl/openssl/blob/openssl-3.5.9/Configure)、[provider build](https://github.com/openssl/openssl/blob/openssl-3.5.9/providers/build.info)、[EdDSA build](https://github.com/openssl/openssl/blob/openssl-3.5.9/providers/implementations/signature/build.info)、[armcap](https://github.com/openssl/openssl/blob/openssl-3.5.9/crypto/armcap.c)。
- [config(5)](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man5/config.pod)、[SSL_CONF_cmd](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man3/SSL_CONF_cmd.pod)、[security level](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man3/SSL_CTX_set_security_level.pod)、[legacy provider](https://github.com/openssl/openssl/blob/openssl-3.5.9/doc/man7/OSSL_PROVIDER-legacy.pod)。
- 固定Buildrootの[recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libopenssl/libopenssl.mk)、[Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libopenssl/Config.in)、[include順序](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/Makefile#L545-L550)、[wpa_supplicant](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/wpa_supplicant/wpa_supplicant.mk)、[kmod](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/kmod/kmod.mk)。
- [公式配布表](https://openssl-library.org/source/)、[4.1.0 Configure](https://github.com/openssl/openssl/blob/openssl-4.1.0/Configure)、[4.1.0 INSTALL](https://github.com/openssl/openssl/blob/openssl-4.1.0/INSTALL.md)。最新tokenの追加・削除は版変更の推奨ではない。
