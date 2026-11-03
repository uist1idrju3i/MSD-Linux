# 更新frameworkと暗号libraryのbuild option

[代替比較](README.md) / [更新framework](updates.md) / [暗号・TLS](crypto.md) / [ネットワーク](network.md) / [署名](signing.md) / [RESEARCH](../../../RESEARCH.md)

## 前提

2026-11-03に、MSD/Linuxの`origin/main` `94915bfef27f0d50ae0f4c6e24ffa98daf68a12e`と、固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`を基準に設定を調べました。`origin/main`の値は文書化ブランチ作成時の`git rev-parse origin/main`で確認しました。暗号libraryはOpenSSLを採用する方針（2026-11-03 利用者決定）、差分更新は必須でnetwork依存可。調べた構成のbuild、QEMU、実機での起動や暗号性能の測定は本リポジトリでは試していません。

## OpenSSLの保守期限と現行版

OpenSSLの公開する保守期限は次のとおりです。

| 系列 | 保守期限 |
|---|---|
| 3.6 | 2026-11-01（2026-11-03時点で期限切れ） |
| 3.5 LTS | 2030-04-08 |
| 4.0 | 2027-05-14 |

固定Buildrootと、2026-11-03時点のBuildroot masterは、どちらもOpenSSL 3.6.5です。3.6.5と3.5.9は2026-09-29に公開されました。現行製品では`msd-update`が署名検証にOpenSSL CLIを使います。

## RAUCとOpenSSLの組み合わせ

RAUC v1.15.2はOpenSSL 4.0でbuildできないという報告が[Issue #1913](https://github.com/rauc/rauc/issues/1913)にあります。[Issue #1914](https://github.com/rauc/rauc/issues/1914)が修正候補として参照されていますが、mergeされたかは未確認です。RAUC masterはv1.15.2より426 commit先です。

OpenSSL 4.0ではengineが削除されました。一方、固定BuildrootのRAUC packageは`BR2_PACKAGE_LIBOPENSSL_ENGINES`を選び、`pkcs11_engine`の上流既定値もtrueです。providerへの対応を求める[Issue #1779](https://github.com/rauc/rauc/issues/1779)はopenです。このため、固定BuildrootのRAUCとOpenSSL 4.0はそのままでは組み合わせられません。

| RAUCのoption（v1.15.2） | 上流の既定値 | 固定Buildrootで選べる設定 |
|---|---|---|
| `service`（D-Bus） | true | `RAUC_DBUS` |
| `network`（libcurl） | true | `RAUC_NETWORK` |
| `streaming`（libnl、NBD） | true | `RAUC_STREAMING` |
| `json` | enabled | `RAUC_JSON` |
| `gpt` | auto | `RAUC_GPT` |
| `create`（bundle作成・変更command） | true | 選択肢なし。targetにも入る |
| `pkcs11_engine` | true | 選択肢なし。OpenSSL enginesを選ぶ |
| `composefs` | disabled | 選択肢なし |
| `tests` | true | Buildrootはtargetで`-Dtests=false` |

`create=false`と`pkcs11_engine=false`をBuildrootのpackage設定から選ぶ方法はありません。Buildroot側のpackage定義は`vendor/buildroot/package/rauc/Config.in`と`vendor/buildroot/package/rauc/rauc.mk`です。

## SWUpdate 2026.05.1の設定

SWUpdateは上流のKconfigを`BR2_PACKAGE_SWUPDATE_CONFIG`で指定します。Buildrootの設定で直接選べる機能は限られます。

| 項目 | 確認した設定・制約 |
|---|---|
| Buildrootの設定 | USB（systemdが必要）、webserver（既定で有効）、websiteのinstallを選べる |
| 常に入る依存 | `json-c`、`libconfig`、`libubootenv`をselectする |
| 自動検出される依存 | targetにOpenSSL、curl、zlib、zstd、Lua等があると、`HAVE_*`が有効になり依存に入る。最終binaryの依存は未確認 |
| 暗号実装 | OpenSSL（既定で有効）、wolfSSL、mbedTLS、gpgme、PKCS#11 |
| 署名形式 | RSA PKCS#1.5、RSA-PSS、CMS/PKCS#7、GPG。Ed25519はない |
| 暗号化 | 対称鍵のAES-CBC。`sw-description`の非対称暗号化はOpenSSL CMSのみ |
| bootloader | none（環境変数をRAMに保存）、EFI Boot Guard、U-Boot、GRUB、Cboot。tryboot対応の実装はない |
| handler | raw、rawfile、archive、shellscript、diskpart、delta、rdiff、Lua、UBI等 |
| 通信機能 | webserver（mongoose）、suricatta（hawkBit）、download（curl）、Dockerを含む |
| license | Buildrootの記載ではGPL-2.0を主とする複数license |

Buildrootのpackage定義と既定configは`vendor/buildroot/package/swupdate/Config.in`、`vendor/buildroot/package/swupdate/swupdate.mk`、`vendor/buildroot/package/swupdate/swupdate.config`です。上流の設定・署名・bootloader・deltaの説明は下記の資料を参照してください。

## 将来packageと暗号library

| 用途 | package | 固定Buildrootで使う暗号library |
|---|---|---|
| SSH client/server | OpenSSH | OpenSSLが必須。`--with-ssl-engine`も使う |
| 軽量SSH | Dropbear | 同梱のlibtomcryptを使い、OpenSSLは使わない |
| SSH library | libssh、libssh2 | OpenSSL、mbedTLS、libgcryptから選ぶ |
| HTTPS取得 | libcurl 8.23.0 | OpenSSL、GnuTLS、mbedTLS、wolfSSLから1つを選ぶ |
| Wi-Fi | wpa_supplicant 2.12 | WPA3とmeshではlibopensslが必須。DESとMD4もselectする |
| Wi-Fiの別案 | iwd 3.12 | ELLとkernelの暗号APIを使い、OpenSSLは使わない |
| Pythonのssl | python3 | libopensslが必須。BLAKE2をselectする |
| text browser | links、lynx、w3m | linksはOpenSSLのみ、lynxはOpenSSLかGnuTLS |
| GUI browser | netsurf、WebKitGTK、WPE WebKit | netsurfはcurl経由でlibopensslが必須。WebKitはlibsoup3経由でGnuTLSとlibgcryptが必須 |
| git | git 2.54.0 | OpenSSLは任意 |
| kernel module | kmod | targetにOpenSSLがあれば自動で使う |

WPA3、OpenSSH、Pythonのsslのどれかを使えばtargetにもOpenSSLが入ります。OpenSSLを外す構成は将来の用途も含めると現実的ではありません。mbedTLS等も追加すると暗号libraryが複数になり、CVE監視と更新の対象が増えます。OpenSSLの任意機能は各packageからselectされるため、現在の既定値を外しても、後から追加するpackageが必要な機能を戻すことがあります。

## iwdの暗号と実行時依存

iwdはOpenSSLを使わず、ELLとkernel暗号APIを利用します。実行時依存はD-Busと、`iwctl`のreadlineです。Buildrootのkernel fixupはDES、MD5、SHA1等の必要なkernel暗号設定を有効にします。WPA3（SAE）とEAPの処理はiwd自身とELLのTLSが担います。

iwdを選ぶ場合はD-Busの常駐が増え、userspaceからkernel暗号APIを使うため、攻撃面がkernel側へ移ります。TLSがOpenSSLではなくELLの実装になるため、OpenSSLより監査実績が少ないという推測があります。

## OpenSSLのbuild設定とhardening

現行defconfigで明示しているのは`BR2_PACKAGE_LIBOPENSSL_BIN=y`です。Buildrootの`package/openssl/Config.in`では複数の任意機能が既定で`y`になっています。最終`.config`は未確認のため、次の一覧はConfig.inの既定値からの推測です。

- SSL3、weak SSL ciphers
- MD2、MD4、RC2、RC4、DES、IDEA、SEED、Blowfish、CAST、Whirlpool
- PSK、QUIC、CMP、comp、dynamic engine

Ed25519の署名検証に必要な`ENABLE_ECX`は残す必要があります。`msd-update`がOpenSSL CLIを使う間は`BIN`も必要です。旧算法やTLS機能を外す場合、別packageがその機能をselectしてbuild時に戻すことがあります。

現行のdefconfigは`BR2_cortex_a53=y`、`BR2_OPTIMIZE_S=y`、`BR2_ENABLE_LTO=y`、`BR2_FORTIFY_SOURCE_3=y`です。OpenSSLのCFLAGSは`TARGET_CFLAGS`を引き継ぎます。target archは`linux-aarch64`でassemblerを使います。上流は`no-asm`を本番用とはしていません。Buildrootは`no-afalgeng`と`no-rc5`を常に指定し、`no-unit-test`、`no-crypto-mdebug`、`no-autoerrinit`は`LIBOPENSSL_UNSECURE`を選ばない場合に追加します。

Buildroot recipeでは`no-deprecated`、`no-legacy`、`no-srp`、`no-gost`、`no-dtls`、`no-tls1`、`enable-ktls`等を指定できません。rootfs-overlayの`openssl.cnf`ではlegacy providerを読み込まない、`MinProtocol = TLSv1.2`、`CipherString = DEFAULT:@SECLEVEL=2`以上を設定できます。package設定の変更なしで適用できる実行時設定です。

BCM2837（CM0）にAES・SHAの暗号拡張命令があるかは、メーカーの一次仕様で未確認です。命令がない場合はAESがNEONのbit-sliced実装になり、ChaCha20-Poly1305の方が速いという推測があります。実機での確認は未実施です。確認には`/proc/cpuinfo`のFeaturesと`openssl speed -evp`（`aes-128-gcm`、`chacha20-poly1305`、`sha256`、`ed25519`、`x25519`、`ML-KEM`）を使います。QEMUの値を実機CPU性能の根拠にはできません。

固定Buildrootの主なpackage資料は、`vendor/buildroot/package/openssl/Config.in`、`vendor/buildroot/package/openssl/openssl.mk`、`vendor/buildroot/package/mbedtls/Config.in`、`vendor/buildroot/package/mbedtls/mbedtls.mk`、`vendor/buildroot/package/iwd/Config.in`、`vendor/buildroot/package/iwd/iwd.mk`、`vendor/buildroot/package/wpa_supplicant/Config.in`、`vendor/buildroot/package/libcurl/Config.in`、`vendor/buildroot/package/python3/Config.in`です。

## `/data`の任意の暗号化

| 方式 | Buildroot | 鍵 | 注意点 |
|---|---|---|---|
| dm-cryptとLUKS2（cryptsetup 2.8.7） | `BR2_PACKAGE_CRYPTSETUP`。lvm2、util-linux、json-c、libargon2をselectする。暗号backendにOpenSSLを選べる | passphraseからArgon2idで鍵を導く | file system全体を暗号化する。initramfsか早い段階でpassphraseを入力する仕組みが必要。起動時間とRAMが増える |
| ext4のfscrypt（`fscryptctl`、e2fsprogsの`e4crypt`） | `BR2_PACKAGE_FSCRYPTCTL` | passphraseから導いた鍵をkernelのkeyringに入れる | directoryごとに暗号化する。file名の長さなどmetadataの一部は守られない。後から有効にしやすい |

### 共通の前提

- CardputerZeroには鍵を安全に保管するhardware（secure element、TPM）がありません。そのため、起動のたびにkeyboardでpassphraseを入力する方式を前提にします。
- passphraseをmicroSDに保存すると、暗号化の意味がなくなります。
- CM0にAES命令がない場合はAdiantum（`CONFIG_CRYPTO_ADIANTUM`）が速い可能性があります（推測）。実機の`cryptsetup benchmark`でAES-XTSと比べます。
- 暗号化の有効化・無効化、passphraseの変更と紛失時の`/data`初期化、電源断への耐性を、R05の実験条件に沿ってPoCで確かめる必要があります。

固定Buildrootのpackage資料は`vendor/buildroot/package/cryptsetup/Config.in`、`cryptsetup.mk`、`vendor/buildroot/package/fscryptctl/Config.in`、`fscryptctl.mk`です。

## 上流資料

- [OpenSSL Release Strategy](https://openssl-library.org/policies/releasestrat/)
- [OpenSSL 4.0.0 NEWS](https://raw.githubusercontent.com/openssl/openssl/openssl-4.0.0/NEWS.md)
- [RAUC v1.15.2 advanced.rst](https://raw.githubusercontent.com/rauc/rauc/v1.15.2/docs/advanced.rst)
- [SWUpdate 2026.05.1 Kconfig](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/Kconfig)、[crypto/Kconfig](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/crypto/Kconfig)、[bootloader/Kconfig](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/bootloader/Kconfig)、[handlers/Kconfig](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/handlers/Kconfig)
- [SWUpdate 2026.05.1 signed_images.rst](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/doc/source/signed_images.rst)、[bootloader_interface.rst](https://raw.githubusercontent.com/sbabic/swupdate/2026.05.1/doc/source/bootloader_interface.rst)
- [mbedTLS BRANCHES.md](https://raw.githubusercontent.com/Mbed-TLS/mbedtls/development/BRANCHES.md)
- 固定Buildrootのpackage定義は本文中の`vendor/buildroot/package/`以下の各pathを参照してください。
