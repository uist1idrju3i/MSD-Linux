# Wi-Fi・接続管理・通信防御の比較と実装計画

[代替比較](README.md) / [TLS](crypto.md) / [更新metadata](update-metadata.md) / [RESEARCH](../../../RESEARCH.md)

## 現在どこまで使えるか

**Wi-Fiを利用可能とはまだ言えません。** 2026-11-02にMSD/Linuxの`551eee4`と固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`を調べました。無線driver・firmwareの選択と、認証・IP設定・DNS・安全な通信開始は別です。この文書は比較と未実装機能の計画であり、製品設定を変えていません。候補のbuild・実行、実機の無線接続・firewall・権限制限は本リポジトリでは試していません。

| 層 | 確認できたもの | 足りない確認・実装 |
|---|---|---|
| IC・接続・firmware | [公式OS・BSP比較](../official-software.md)、[部品と配線](../hardware-wiring-audit.md)、[defconfig](../../../configs/msd_cardputerzero_defconfig)のBRCMFMAC SDIO firmware選択 | 実機のprobe、正しいfirmware/NVRAM、規制地域、rfkill、scan、接続。上流supplicantのWPA3対応を無線ICの対応証明にしない |
| kernel | [固定CI生成物の記録](../../experiments/2026-11-02-hardware-artifact-audit.md)と同じSHA-256の最終`.config`を追加読取り。BRCMFMAC/CFG80211/MAC80211はmodule | signed moduleのload、実機interfaceの出現。QEMUの仮想Ethernetで代用しない |
| 認証・接続管理 | 現行defconfigにwpa_supplicant、iwd、ConnMan、NetworkManagerの選択なし | 認証方式、接続先選択、資格情報保存、再接続、Wi-FiとEthernetの優先度 |
| IP・DNS | [固定BusyBox既定config](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/busybox/busybox.config)にはUDHCPCとip appletがある | 最終BusyBox設定・imageの実物、起動時の呼出し、DHCP hook、IPv6、resolv.conf。appletの存在だけで接続設定済みにはしない |
| HTTPS・更新取得 | OpenSSL CLIは選択済み。libcurl・CA bundleは現行defconfigに選択なし | downloader、信頼するCA、名前・期限検証、取得上限、時刻、[metadataの認証](update-metadata.md)。OpenSSLの存在だけでwgetのHTTPS対応や検証を保証しない |
| packet filtering・隔離 | 同CIの最終kernel設定ではNETFILTER=y、NF_TABLES=m、SECCOMP/SECURITY_APPARMOR/SECURITY_LANDLOCK=y | nftables userland・policy、起動順、profile/filterの読込み、対象processへの適用と拒否試験。kernel optionと強制中のpolicyは別 |

最終kernel設定のSHA-256は、既存の[入力JSON](../../experiments/2026-11-02-hardware-artifact-audit.json)にある`74d625a1c9dad65fd2999abd0b0a572874a39b32dbd1d685edcb3153ea8a0739`と照合しました。これは当該CI生成物の静的確認であり、今回のbranchでの新規build・実機起動ではありません。現行のreadyとA/B healthはWi-Fi接続成功を判定していません。更新をcommitするためにインターネット必須とする設計も、オフライン利用・復旧を妨げるので別途判断します。

## 接続管理を同じ役割ごとに比べる

### Wi-Fi認証とinterfaceの管理

| 候補 | 役割と再評価 | 固定Buildrootでの条件・費用 | 今回の提案 |
|---|---|---|---|
| [wpa_supplicant](https://w1.fi/wpa_supplicant/) | 認証、scan、再接続等。IP/DNS全体のmanagerと同一視しない | 固定recipeは2.12。nl80211にlibnl。D-Busはoptionalで、CLI/control socketでも構成可能。WPA3、EAP、AP/P2P、WPS、WEP等を個別に確認する | D-Busなしのstation構成を先に試す。必要な認証方式を残し、旧方式や不要server機能の削減を測る |
| [iwd](https://www.kernel.org/pub/linux/network/wireless/) | 認証に加え、内蔵DHCPでIP設定も可能。systemd必須として除外しない | 固定recipeと取得indexの最大releaseは3.12。ELLと実行時D-Bus。iwctlにはreadlineを使うrecipeで、clientのGPL-3.0+も別に考える。SysV init対応 | 独立した比較候補。内蔵IP設定と外部DHCPの二重起動を避け、DNSの管理方法も決める |
| [ConnMan](https://git.kernel.org/pub/scm/network/connman/connman.git/plain/README) | embedded向けの接続・service管理。認証だけのdaemonより広い責務 | 固定recipeはGLib・D-Bus、Wi-Fiにwpa_supplicantとそのD-Bus。firewallはiptablesが既定だがnftablesも選べる。musl不可はこのBuildrootの条件で、全上流へ一般化しない | wired/wireless切替・VPN等の統合費用を含めて比較。WISPr、Bluetooth、telephony等の不要機能を切る |
| [NetworkManager](https://networkmanager.dev/docs/) | 接続profile・route・DNSやCLIを統合。GUIは選択理由にも除外理由にもしない | 固定recipeにudev、GLib、D-Bus等が必要。現行mdevからの変更を伴う。nmcli、nmtui、modem等は選択式 | profile管理の利便性とdevice管理変更・RAM・policy費用を測る。最小構成と同じ依存量とは扱わない |
| [systemd-networkd](https://www.freedesktop.org/software/systemd/man/latest/systemd-networkd.html) | link/IP設定を管理する。Wi-Fi認証は別担当 | systemd構成を採る場合の候補。resolvedも別serviceで、PID 1の[比較](init.md)と合わせる | networkのためだけの無条件導入はしない。systemdを試す構成では比較対象へ戻す |
| BusyBox ifupdown / [ifupdown-ng](https://github.com/ifupdown-ng/ifupdown-ng/tree/60777d0f33453335761e8ab94359e6b31a4c8c1a) | interfaceの立上げとhookの順序。認証やDHCPを自動で代替するものではない | ifupdown-ngには依存関係に基づく順序制御。glibcでのlibbsd要件もREADMEにある。hookがrootで入力を処理する経路を調べる | 単純な固定構成の比較候補。ただし自作shellの監視・再試行・入力検査を保守費用へ算入する |

iwd 3.12の`src/iwd.config.rst`では`EnableNetworkConfiguration=false`が既定で、IP設定を有効にしても`NameResolvingService=none`ではDNS情報を無視します。上流の既定は`systemd`、固定Buildrootのrecipeはopenresolv/resolvedがないと`none`を設定します。「DHCP内蔵だからDNSまで使える」「systemdなしでは使えない」のどちらにも単純化しません。IPv6設定は同資料では既定有効です。

wpa_supplicant 2.12のupstream defconfigにはWPS・P2P等があり、TKIPを除く`CONFIG_NO_TKIP`は既定でコメントされています。さらに固定Buildrootのwpa_supplicant選択は、libopenssl利用時にDES/MD4も選びます。iwdのkernel fixupにもDES/MD5/SHA1等があります。新しい実装やstation modeという名前だけで、旧算法がbuild・使用されないとは主張しません。最終設定、生成binary、接続時の交渉結果を別々に検査します。

### DHCPとDNS

| 候補 | 利点・役割 | 費用・試験条件 |
|---|---|---|
| BusyBox udhcpc | 既存multi-call binaryのDHCPv4 appletを使える候補 | 実際のapplet選択とhookを調べる。受信したhostname/domain/DNS/routeをshellへ無検査で渡さない。DHCPv6、RA、複数interface、lease保持は個別に確認 |
| [dhcpcd](https://github.com/NetworkConfiguration/dhcpcd/tree/93df2b254caf9639f9ffb66e0fe2b584eeba6220) | DHCPv4/v6、IPv4LL等。固定recipeの10.2.4はprivilege separationが既定有効で、専用userも作る | privileged helperとparserのprocess分離、AArch64 seccomp、chroot、IPC、lease・DUIDの保存を確認。10.5.2のlatest Release応答と固定10.2.4は別に記録し、ここでは更新しない |
| iwd内蔵IP設定 | Wi-Fi構成でdaemon間の重複を減らす候補 | Ethernetの管理、DNS連携、IPv6と再接続、複数linkのroute選択が残る。dhcpcd等と同じinterfaceを二重管理しない |
| [openresolv](https://github.com/NetworkConfiguration/openresolv/tree/9b3691b545af83fb1ccffb2291dd4151dae6551e) + libc resolver | 複数interfaceが渡すDNS情報からresolv.confを管理する。DNS server自体ではない | `/run`の可変状態とread-only rootを接続し、切断時の古いDNS・search domainを消す。hook・権限・VPNの名前解決漏れを確認 |
| [systemd-resolved](https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html) | stub/cache、linkごとの名前解決等を持つ別service | systemd構成・libcとの接続・DNSSEC/暗号化・時刻・例外設定を一緒に評価。必要のないLLMNR/mDNS等は既定で開かない案を比較 |
| [dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html) | DNS forwarding/cache、DHCP/RA等のserver用途 | 端末がDHCP clientとして接続するだけなら自動追加しない。AP・共有機能を設計する時に、bind先・待受・最小権限とともに再検討 |

固定dhcpcd 10.2.4の[`src/privsep-linux.c`](https://github.com/NetworkConfiguration/dhcpcd/blob/93df2b254caf9639f9ffb66e0fe2b584eeba6220/src/privsep-linux.c)で、AArch64のarch照合、許可syscall、`PR_SET_NO_NEW_PRIVS`とseccomp filterの設定を確認しました。一方で`DISABLE_SECCOMP`経路もあります。設定名だけで保護中とせず、実行processのUID/GID、capability、`NoNewPrivs`、`Seccomp`と、禁止操作が失敗することを調べます。自作のroot DHCP hookと比較する際は、binaryの大きさだけでなく、この分離を維持する費用も数えます。

## HTTPS取得と時刻を接続後の別機能にする

更新取得には、認証済みmetadataのhash/length、download上限、許可するURL、途中fileの扱いが必要です。TLSは[暗号libraryの比較](crypto.md)、更新認可は[TUFの比較](update-metadata.md)で扱います。

- BusyBox wget、GNU Wget、curl/libcurl、更新frameworkの内蔵downloaderを比較します。固定BusyBox既定configのwgetは有効でも、HTTPS/OpenSSL機能は無効です。製品の最終config・binaryで再確認するまでHTTPS clientとして数えません。
- [curlの証明書説明](https://curl.se/docs/sslcerts.html)に従い、信頼するCAとhostname・期限検証を有効にします。`--insecure`、証明書確認の無効化、TLS失敗時のHTTP fallbackは採りません。curlの[固定Buildroot設定](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libcurl/Config.in)はTLSなしも選択でき、追加protocol・proxy・cookiesも既定有効なので、採用時は削減と必要な背反を調べます。
- HTTPSだけを許すprotocol/redirect制限、最大redirect・応答長・展開量・時間・再試行を設定します。TLS認証と署名検証を両方維持します。HTTP errorを成功としないこと、proxy環境変数・任意URL・別scheme・redirect先へ秘密を漏らさないことも負の試験へ含めます。GitHubのasset CDNを固定IPだけで許可する案は、配信先変更との衝突を評価してから決めます。
- DHCPが示すDNS、route、時刻は未認証入力として扱います。[chronyのNTS設定](https://chrony-project.org/doc/4.8/chrony.conf.html)も比較しますが、RTC初期値、CA検証、時刻同期、metadata expiryの依存関係を解決した証拠にはしません。時刻が不明なら更新認可を止め、オフラインの既存slotを起動できる復旧方法を設計します。TLS/expiry検証を無効にして循環を回避しません。

## 通信を有効化する前の防御

### packet filterとprocess隔離を分ける

| 方式 | 防ぐ対象と条件 | 比較で残す費用・限界 |
|---|---|---|
| [nftables](https://www.nftables.org/projects/nftables/index.html) | IPv4/IPv6を含むpacket policyの第一実験候補。固定recipeはlibmnl/libnftnl、任意JSONにjansson | kernel moduleと実際に使うexpression、signed load、読込み失敗、atomic変更を試す。JSON/対話編集/Python等は必要なものだけ。選択だけでdefault denyにはならない |
| iptables | 必要な既存hookとの相互運用候補 | nft backendとlegacy backendを区別する。二重policy、IPv4だけの制限、更新順の複雑化を比べる。名前だけでnftablesより安全・危険と順位づけない |
| eBPF/XDP | 別の処理位置や高負荷処理の用途候補 | 端末の基本firewallと自動的に同じ機能ではない。loader、権限、program更新、verifier、観測・復旧費用が増える。本機での必要性・効果は未測定 |
| AppArmor | processごとのfile・capability・network等のpolicy | kernelの有効化だけでは不十分。parser/profile、attach、enforce、更新とrollback時のpolicy互換性が必要。受信portのpacket policyや署名検証の代用にしない |
| Landlock・seccomp・capabilities・namespaces | helperのfile、syscall、権限・資源の範囲を絞る候補 | policyを実行processへ適用する実装が必要。Landlockのnetwork制御は任意のpacket firewallではない。外部daemonと自作helperの適用可能範囲を分け、詳細は[セキュリティ検討](../security/threat-model.md)で再評価する |

起動時はfilterを用意してからlinkを上げ、DHCP・認証・一般processの通信を開始する順序を設計します。policyの構文不正、必要moduleの欠落、読込み失敗では通信開始を止めます。単にinit script名を早めるだけでなく、hotplug、daemonのautostart、IPv6 link-local、再起動・再接続でも順序を確認します。

通常の端末用途では、不要な受信・forwarding・SSH等の待受を既定で開かない案を基準にします。IPv4だけを拒否してIPv6を通す状態を避け、DHCP、IPv6 RA/ND、ICMP/PMTU、DNS、時刻、確立済み通信の必要条件を列挙します。厳格な送信先制限には、共有IP/CDN、DNS変更、bootstrap・proxy・オフライン復旧の費用も含めます。実機未試験の万能ルールをREADMEへ貼りません。

資格情報はimage・Release・command line・debug logへ埋めず、明示的に登録した接続先だけへ使う案です。WEP、WPA1/TKIP、open networkへの自動fallback、WPS・AP・P2Pの不用意な有効化は避けます。WPA3/PMFの実機対応とAP相互運用を先に確かめ、WPA2-CCMP等との選択は機能・安全性の実測を踏まえて判断します。MAC randomizationもdriver制約、再接続、DHCP/DUID・監視との関係を測り、匿名性を保証する表現は使いません。

## 実装順と完了条件

以下は未実装機能の計画です。daemonの選定・製品設定・鍵や資格情報の導入は、この比較だけで実施していません。

| 順 | 成果物 | 完了条件 |
|---|---|---|
| 1 | device/firmware/regulatoryの実機記録 | 固定image・module・firmware hash、probe、interface、rfkill、countryと合法なchannelを保存。未確認の無線IC機能を対応済みと言わない |
| 2 | 最小station構成の比較 | wpa_supplicant + dhcpcd(privsep)を第一候補、udhcpc構成とiwd内蔵IP + openresolvを対照に、依存・license・最終option・size/RAM・CPU・起動を測る。採用決定ではない |
| 3 | local登録・保存・復旧手順 | SSID/鍵のlocal入力、所有者・0600等のmode、secret非表示、削除・再設定・電源断・A/B rollbackを確認。永続化は必要pathに限定し、`/data/etc`全体のoverlayでtrust anchorやpolicyを隠さない設計を評価 |
| 4 | 起動順・firewall・権限制限 | 通信前のpolicy強制、profile/filterのattach、非root parserと限定helper、誤設定でもoffline起動・local復旧が可能。既定で不必要な待受なし |
| 5 | IP/DNS/時刻と再接続 | IPv4/v6、lease renew、RA、切断、Ethernet併用、DNSの優先度と消去、RTC不正・時刻同期失敗を確認。daemon二重管理・root hookの入力注入を拒否 |
| 6 | HTTPSと更新取得の独立試験 | 不正CA/hostname/期限、HTTP fallback、悪いredirect、巨大・中断応答、metadata rollback/expiry、間違うboardを拒否。download processはactive slotやselectorへ書けない |
| 7 | 統合試験と公開手順 | 同一の最終revision・binaryで5回以上反復。QEMU/host network namespaceのpacket・負の試験と、実機SD/Wi-Fi/AP・電断試験を分け、基準・失敗・raw結果を保存。オフラインの通常利用とA/B復旧も壊さない |

これらが済むまで「Wi-Fi利用可能」「firewall保護済み」「AppArmorで制限済み」とは記載しません。networkの有効化とGitHub Releasesからの自己更新は別の完了条件です。

## 根拠の保存範囲

URL・固定ref・bytes/hash・失敗試行は[sources.json](sources.json)に保存します。wpa_supplicant 2.12とiwd 3.12の配布tarは、固定Buildrootの`.hash`とSHA-256が一致しました。配布物の照合は、署名の検証・本機互換性・実行確認の代わりではありません。upstream defconfigとBuildrootによる編集後の設定も区別します。

iwd wikiの取得は失敗し、配布tar内のREADME・`src/iwd.config.rst`・`doc/main.conf`で該当設定を確認しました。取得した開発masterのmain.confは固定3.12の証拠に混ぜません。ifupdown-ngのlatest Release API失敗は、保守終了やrelease不存在を意味しません。chronyのsecurityページも取得失敗として残し、文書の取得成功をsecurity監査完了とは扱いません。OpenBSDの設計思想からLinuxのruntime policyへ具体化する検討、全周辺機能・開発CIの代替比較は引き続き残っています。

### 今回実施した検査

出典93件を追加し、取得済みraw bytes・長さ・SHA-256と、記録されたGit blob IDを照合しました。配布tarからの4 memberも元archiveと照合し、既存312件のsource recordが不変であることを検査しています。取得失敗3件を成功へ書き換えていません。

リンク、JIS文字集合、文書サイズ、スキル、サイトの検査と各回帰試験、既存`tests/msd-update/run.sh`のhost試験が通りました。固定開発コンテナーのShellCheck・actionlintとoffline zizmorも通っています。yomiyasuの候補は本文・出典・差分と読み比べて判断しました。既存のサイズ・JIS警告は残ります。これらは文書と既存処理の検査であり、上表のnetwork構成、代替downloader、新規policyの試験ではありません。
