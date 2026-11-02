# 通信開始前のfirewallとservice制限

[入口](README.md) / [権限表](privileges.md) / [接続管理の代替](../alternatives/network.md) / [検証](verification.md)

## 何を防ぐ設計か

Wi-Fiのdriver・firmwareが存在しても、認証・IP・DNS・時刻・HTTPSとpolicyが稼働した証拠にはなりません。現行は接続管理とnftables userland・ruleset、AppArmor profile等を製品へ統合していません。この文書は導入前の設計条件です。

| 入力・故障 | 影響 | 必要な境界 |
|---|---|---|
| 近隣無線、Ethernet、USB NIC、偽DHCP/DNS応答 | driver/parserへの非信頼入力、route・DNS設定の変更 | driver更新、不要protocolの無効化、特権分離、interfaceと入力の検査。IP firewallだけでは無線管理frameや全L2処理を守れない |
| 意図しないlistener・AP・Bluetooth discoverable | 受信攻撃面の増加 | 未使用serviceと自動公開を既定で無効化。IPv4/IPv6両方の入力・転送policy |
| 侵害されたdownloader | data流出、boot領域の破壊 | 専用UID、限定した書込み先と通信、署名された更新認可と特権writerの分離 |
| policy読込み失敗、daemon crash/restart、hotplug | 無制限で通信を始める時間帯 | 必須policyの読込み成功をservice開始の前提にする。失敗時は対象通信を開始せず、他の安全なオフライン操作と復旧経路を保つ |
| 古い時刻・切断・敵対的配信元 | TLS・metadata期限の判定失敗、古い更新・停止攻撃 | CA/hostname/期限、信頼する時刻、metadataの署名・期限・hash/length。失敗時に検証を無効にしない |

Wi-Fi認証の安全な算法はIC・firmware・driver・supplicant・接続先の全てに依存します。WPA3対応の上流説明だけで本機のWPA3接続を保証せず、必要な認証方式と無効にする旧方式・AP/P2P/WPS等を最終設定と実機交渉で確認します。

## firewallの初期要件

提案はnftables一系統でIPv4/IPv6を扱い、**不要な受信と転送を既定拒否**するものです。実行可能な完成rulesetをこの段階で配布していません。[上流のworkstation例](https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_workstation)は入力の基本例であり、製品のDHCP・時刻・DNS・出力制限・USBや無線の全要件を満たす証拠ではありません。

- loopbackと確立済み通信だけで足りるとはしません。DHCPv4/v6、ARP、IPv6のRA/ND、ICMP/ICMPv6の到達不能・Packet Too Big等について、使う機能に必要な方向・interface・範囲を設計します。IPv6を使わないなら、その無効化と漏れがないことも試験します。
- output acceptは入力側防御の最初の比較案ですが、侵害済みprocessの外向き通信を制限しません。専用serviceのUID・LSM・socket制限等を重ね、DNS・時刻・更新等の必要通信と、通常アプリのネットワーク要件を区別します。
- nftablesのIP/port許可だけでGitHubのdomainやReleaseの真正性を認証できません。CDNの可変IP、redirect、DNS、TLSの名前検証とsigned metadataを別々に扱います。TLS検証を省略してIP固定を安全性の代替にしません。
- hotplug後のinterface名にも適用されるpolicy、同時に動くwired/wireless、USB gadget、bridge・転送の有無を試験します。未確認のinterfaceを無制限な例外へ落としません。
- 反映は[nft -fによる一つのtransaction](https://wiki.nftables.org/wiki-nftables/index.php/Atomic_rule_replacement)を基本にし、flushしてから別commandで再設定する空白時間を作りません。syntax check、module・hookの準備、load、実効ruleset確認、負のpacket試験を区別します。syntaxが正しいだけでは稼働の証明になりません。

## 起動と復旧の順序

1. dataを必要な所有者・modeで準備し、正本のpolicyと秘密の設定を識別します。通常userがroot用policyを上書き・隠蔽できる場所から読みません。
2. firewallに必要なkernel機能・moduleとAppArmor等のpolicyを準備します。kernel autoconfigurationや既存initが、先にIP通信を始める経路も調べます。
3. firewallをatomicに読み込み、必須のLSM/profileを確認します。失敗なら対象serviceを起動しません。後からreloadする場合も、失敗時は直前の有効な制限を保ちます。
4. 各daemonの上流の起動契約に合わせ、必要なFD・初期権限を取得し、専用user・capability・syscall・file制限へ移行します。policyを読んだroot起動scriptと、実際に隔離されたdaemonを区別します。
5. link、無線認証、IP、DNS、時刻、HTTPSの状態を別々に記録します。supplicantがL2認証を開始する時点とIP通信開始を区別し、firewallで全無線入力を遮断したとは書きません。
6. crash、restart、suspend、link変更、hotplug、A/B再起動後も同じ条件を満たします。policyを外して通信を続けるfallbackは作りません。

AppArmorを使う案は、固定CI kernelにある機能を再利用できる候補です。ただしprofile attachment、exec遷移、interpreter、可変etc、device ioctl、子process、policy更新を含む費用を見積もります。SELinuxを恒久的に劣る候補と扱うのではなく、固定構成との差と既存policy・保守体制で比較します。AppArmorとLandlock等を重ねる場合も、各層の拒否試験が必要です。

## DNS・時刻・更新の認可

DNSの暗号化と悪性domainのfilter、DNSSEC、TLSでのserver認証、署名metadataは別の保証です。単一の公開resolverを使うだけで安全性が完成したとはしません。DoT等を採る場合は平文fallbackを禁止する設定を上流文書で確認し、packetで検証します。特定の`do-udp`設定だけを、全ての平文上流通信を止める根拠にしません。

TLSとmetadata期限には時刻の問題があり、NTSにも初期TLS接続時の扱いがあります。RTC、前回の信頼時刻、初回設定、極端な過去・未来、切断時の挙動を設計し、証明書検証無効化を常用の回避策にしません。raw Ed25519署名の数学的検証自体に壁時計が必要なわけではなく、TLS・期限・運用判断と分けます。

GitHub Releasesは更新候補を見つける入口です。取得したAPI応答・asset名・tag・download URLだけで更新を許可せず、信頼するsigned metadataが機種と対象bytesのhash/length等を認証する設計にします。[TUF/Uptane等の比較](../alternatives/update-metadata.md)と、[特権writer](privileges.md)へつなげます。CA、取得上限、redirect先、期限・巻戻し・鍵更新・再試行・中断を含む実装と試験は未実施です。

## 認証情報とオフライン利用

接続profile、PSK、API資格情報、時刻・更新状態を全serviceで共有しません。root専用や専用userのmodeを定め、process引数・環境・log・diagnostic出力へ秘密を出さない手順を設けます。公開Releaseを読むだけなら、端末へGitHubのwrite tokenや署名秘密鍵を配りません。

製品の必須security policyが稼働することと、インターネットに到達できることは別です。A/Bのhealthへ外部server到達を無条件に必須化すると、正しいimageもオフラインで確定できなくなります。ローカルで確認できるpolicy・serviceの状態と、外部接続の劣化表示・再試行を分けて設計します。
