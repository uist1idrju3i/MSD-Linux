# openssl.cnfのC1採用とARM最適化

[OpenSSL最小化の調査](openssl-minimal.md) / [component option索引](README.md)。一次資料の一覧は親文書を参照する。

2026-11-13の[製品方針](../../design/product-decisions.md)ではlegacy EAP／TLS-PSK互換を維持せず、速度優先でasmを残す。CMSは標準更新frameworkの比較・移行まで維持し、CLIは`msd-update`存続中だけ維持する。移行後に`no-apps`を再検討する。同日DEFAULT groupsとML-KEMの維持を決定したため、C1でもclassical groupsへ固定しない。[PQCの決定](openssl-pqc-groups.md)と[容量・VM／QEMU実験](../../experiments/2026-11-13-pqc-groups.md)を参照する。C1の適用処理は実装したが、ARM最適化と実機の互換性・速度・boot時間は未測定である。

## openssl.cnfの採用設定

変更前の上流example configは`openssl_conf`、`config_diagnostics=1`、provider sectionがあり、defaultの`activate`はcommentだった。TLSの`system_default`やMinProtocolは未設定。既存の初期化・診断・CA/CSR節を保持し、post-buildでC1だけを追加する。legacy.soがrootfsに存在することは、自動load済みという証拠ではない。

2026-11-23に利用者がC1を選び、C2のAEAD限定を不採用とした。下記は採用設定の抜粋で、上流file全体をoverlayで置換しない。MinProtocolはTLS 1.2、最大版は固定しない。CipherStringはTLS 1.2以下、CiphersuitesはTLS 1.3で別に効く。SECLEVEL=2は対称暗号bit数の指定ではなく、鍵長・署名・DH等のsecurity callback方針である。

```ini
openssl_conf = openssl_init
config_diagnostics = 1

[openssl_init]
providers = provider_sect
ssl_conf = msd_tls

[provider_sect]
default = default_sect

[default_sect]
activate = 1

[msd_tls]
system_default = msd_tls_defaults

[msd_tls_defaults]
MinProtocol = TLSv1.2
CipherString = DEFAULT:@SECLEVEL=2
```

TLS 1.2のCBCを一括排除しないC1であり、AEADだけにするC2とは区別する。TLS-PSKを使うEAP methodを維持しない方針は別で、C1による機能削除とは扱わない。Groupsは指定せずDEFAULTとML-KEMを維持し、TLS 1.3のCiphersuitesも固定しない。実機の互換性は未確認である。

SignatureAlgorithmsとClientSignatureAlgorithmsは初期案では固定しない。ClientSignatureAlgorithmsはTLS 1.2/1.3のclient証明書認証用で、serverのCertificateRequestとclientの証明書署名選択に関わる。固定する場合はEd25519、ECDSA、RSA-PSSとchain署名の要件を試験し、古い相手へのSHA-1緩和をdefaultへ混ぜない。SECLEVELの閾値を下げて試験を通す変更は別の利用者判断とする。

default providerは明示activateし、legacyを記載しない。ただしapplicationやCLIの明示loadまで阻止する設定ではない。legacy機能自体をなくすにはbuild時の`no-legacy`を使う。FIPS認証は要件にないためFIPS providerを追加せず、検証済みmoduleを用意しない`default_properties=fips=yes`も設定しない。FIPS有効化だけで製品全体の適合を主張しない。

SSL_CONFの`system_default`はSSL_CTX作成時の既定で、applicationが設定を無視・変更する場合がある。`OPENSSL_CONF`、`OPENSSL_MODULES`、provider property等の影響も別に調べる。rootfsのconfigはroot所有の読取専用fileとし、秘密鍵や永続的な乱数seedを書かない。sampleのCA/database/serial関連sectionを削る案は、機器がCA発行をしない条件で試す。TLS設定は`pkeyutl`のraw署名検証方針を直接指定するものではないが、configの構文誤りは初期化を失敗させ得る。

## 設定だけのQEMU実験結果

2026-11-18の[C0/C1/C2比較記録](../../experiments/2026-11-18-openssl-cnf.md)に条件・CSV・生logを保存した。各条件3回とC0のA/A反復によるQEMU限定の機能確認で、その時点では製品へ適用しなかった。

C0もTLS 1.0/1.1を既に拒否しており、C1による新たな拒否効果は観測していない。TLS 1.2/1.3は全条件で成功し、TLS 1.2 CBCの対照はC0/C1が受理、C2だけが拒否した。Ed25519更新署名の正常受理・不正拒否、Argon2id/PBKDF2のLUKS2 format/open、署名付きmodule loadは全条件で成功した。module署名の検証主体はkernelである。

cryptsetupはdefault/legacyを自らloadし、CLIのprovider一覧はdefaultだけだった。CA/CSR節は維持した。その後C1を採用し、[hostでの外部接続](../../experiments/2026-11-23-openssl-c1.md)も確認した。製品のCA配布と初期時刻、実機の互換性・速度・boot時間は未確認。製品build・A/B起動はCIへ残す。

## ARM専用最適化の判断

`linux-aarch64`は`Configurations/10-main.conf`で`asm_arch=aarch64`を選ぶ。asmを維持する方針は決定済みで、wrapperの`-mcpu=cortex-a53`と既存のruntime dispatchを残す。単なるgeneric C buildから新たにARM化する状況ではない。実機速度のためにrootfsが大きくなることを許容するが、bootへの影響が小さいという見込みはOpenSSL削減実験で測定する。

**Cortex-A53という名前だけではAES/SHA/PMULL命令は保証されない。** Arm TRMのoptional extensionという説明は[既存調査](../tuning/fastboot-and-cpu-tuning.md#cm0のcpu機能と確認度)にもある。今回、メーカー一次回答として[PhilE（Raspberry Pi Engineer）のBCM2837B0説明](https://forums.raspberrypi.com/viewtopic.php?t=263234)を取得した。3B+のFeaturesはCRC32を含むがSHA/AESを含まないとの報告で、ソフトウェアoptionで暗号命令を有効にできるという根拠にはならない。

この一次観測は3B+であり、CM0／Zero 2の個体採取ではない。BCM2837系で暗号拡張を前提にしない判断を支持するが、本機の全revisionを測定済みとはしない。CM0の実機で64-bit kernelの`/proc/cpuinfo`、`AT_HWCAP`のAES/PMULL/SHA1/SHA2、SoC/revisionを採取する。CRC32の存在は暗号拡張の証拠ではない。

3.5.9の`crypto/armcap.c`はLinux/glibcのgetauxval経路を持ち、AArch64ではAT_HWCAPの機能bitからdispatchする。**`-march=armv8-a+crypto`や正の`OPENSSL_armcap` bitの強制はしない。** 手動bitで存在しない命令へ進ませればSIGILLになり得る。`no-asm`も最適化の逆方向なので採らない。

QEMUのCPU機能は実機のシリコン証拠ではない。QEMUで`openssl speed`の値を出してもA53の性能比較には使えない。実機では同じ電源、温度、governor、周波数、throttling状態で5回以上測り、更新署名検証と実TLS workloadを優先する。
