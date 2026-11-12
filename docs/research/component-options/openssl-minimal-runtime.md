# openssl.cnfとARM最適化（未適用の草案）

[OpenSSL最小化の調査](openssl-minimal.md) / [component option索引](README.md)。一次資料の一覧は親文書を参照する。

## openssl.cnf案

現在は上流example configで、`openssl_conf`、`config_diagnostics=1`、provider sectionはあるが、defaultの`activate`はcomment。TLSの`system_default`やMinProtocolは設定していない。legacy.soがrootfsに存在することは、自動load済みという証拠ではない。

下記は**modern TLS／EAP-TLSに限定する場合の候補**。まだrootfs-overlayへ置かない。MinProtocolはTLS 1.2、最大版は固定しない。CipherStringはTLS 1.2以下、CiphersuitesはTLS 1.3で別に効く。SECLEVEL=2は対称暗号bit数の指定ではなく、鍵長・署名・DH等のsecurity callback方針である。

```ini
openssl_conf = openssl_init
config_diagnostics = 1

[openssl_init]
providers = providers
ssl_conf = ssl_settings

[providers]
default = default_provider

[default_provider]
activate = 1

[ssl_settings]
system_default = tls_policy

[tls_policy]
MinProtocol = TLSv1.2
CipherString = ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!eNULL:!PSK:@SECLEVEL=2
Ciphersuites = TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384
Groups = X25519:P-256:P-384
```

TLS 1.2のCBC／static RSA key exchange等を除く案であり、互換性は未確認。TLS-PSKを使うEAP methodにはそのまま適用しない。TLS 1.3のPSKやresumptionをCipherStringの`!PSK`で一括禁止できるとも扱わない。Groupsの固定は3.5既定のPQC hybridも外す判断なので、PQCを保つならこの行を採用せず、実際のbuildに存在するgroupを選ぶ。

SignatureAlgorithmsとClientSignatureAlgorithmsは初期案では固定しない。ClientSignatureAlgorithmsはTLS 1.2/1.3のclient証明書認証用で、serverのCertificateRequestとclientの証明書署名選択に関わる。固定する場合はEd25519、ECDSA、RSA-PSSとchain署名の要件を試験し、古い相手へのSHA-1緩和をdefaultへ混ぜない。SECLEVELの閾値を下げて試験を通す変更は別の利用者判断とする。

default providerは明示activateし、legacyを記載しない。ただしapplicationやCLIの明示loadまで阻止する設定ではない。legacy機能自体をなくすにはbuild時の`no-legacy`を使う。FIPS認証は要件にないためFIPS providerを追加せず、検証済みmoduleを用意しない`default_properties=fips=yes`も設定しない。FIPS有効化だけで製品全体の適合を主張しない。

SSL_CONFの`system_default`はSSL_CTX作成時の既定で、applicationが設定を無視・変更する場合がある。`OPENSSL_CONF`、`OPENSSL_MODULES`、provider property等の影響も別に調べる。rootfsのconfigはroot所有の読取専用fileとし、秘密鍵や永続的な乱数seedを書かない。sampleのCA/database/serial関連sectionを削る案は、機器がCA発行をしない条件で試す。TLS設定は`pkeyutl`のraw署名検証方針を直接指定するものではないが、configの構文誤りは初期化を失敗させ得る。

## ARM専用最適化の判断

`linux-aarch64`は`Configurations/10-main.conf`で`asm_arch=aarch64`を選ぶ。asmを削除せず、wrapperの`-mcpu=cortex-a53`と既存のruntime dispatchを維持するのが初期案であり、単なるgeneric C buildから新たにARM化する状況ではない。

**Cortex-A53という名前だけではAES/SHA/PMULL命令は保証されない。** Arm TRMのoptional extensionという説明は[既存調査](../tuning/fastboot-and-cpu-tuning.md#cm0のcpu機能と確認度)にもある。今回、メーカー一次回答として[PhilE（Raspberry Pi Engineer）のBCM2837B0説明](https://forums.raspberrypi.com/viewtopic.php?t=263234)を取得した。3B+のFeaturesはCRC32を含むがSHA/AESを含まないとの報告で、ソフトウェアoptionで暗号命令を有効にできるという根拠にはならない。

この一次観測は3B+であり、CM0／Zero 2の個体採取ではない。BCM2837系で暗号拡張を前提にしない判断を支持するが、本機の全revisionを測定済みとはしない。CM0の実機で64-bit kernelの`/proc/cpuinfo`、`AT_HWCAP`のAES/PMULL/SHA1/SHA2、SoC/revisionを採取する。CRC32の存在は暗号拡張の証拠ではない。

3.5.9の`crypto/armcap.c`はLinux/glibcのgetauxval経路を持ち、AArch64ではAT_HWCAPの機能bitからdispatchする。**`-march=armv8-a+crypto`や正の`OPENSSL_armcap` bitの強制はしない。** 手動bitで存在しない命令へ進ませればSIGILLになり得る。`no-asm`も最適化の逆方向なので採らない。

QEMUのCPU機能は実機のシリコン証拠ではない。QEMUで`openssl speed`の値を出してもA53の性能比較には使えない。実機では同じ電源、温度、governor、周波数、throttling状態で5回以上測り、更新署名検証と実TLS workloadを優先する。
