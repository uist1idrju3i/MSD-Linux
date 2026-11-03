# firewall・DNS・時刻同期の調査履歴

[強化項目の案内へ戻る](README.md) / [現在の接続管理比較](../../alternatives/network.md) / [通信開始前の制限](../network.md)

以下は元の1・7〜9節です。ネットワーク未導入という前提での候補・手順であり、nftables rule、DNS、DoT、NTSが製品で稼働しているという意味ではありません。unboundのみが実用的という旧評価は採用の結論にせず、現在の比較と導入条件を読みます。署名の数学的検証、TLS、metadataの期限の要件は別です。

## 1. ファイアウォールをデフォルト有効（最小権限）

**結論: 採用（ネットワーク導入時に nftables でデフォルト drop）。**

- 固定CIの最終kernel設定には`CONFIG_NF_TABLES=m`・`CONFIG_NF_TABLES_INET=y`等があります。必要module・hook、nft userland、IPv4/IPv6のruleset、起動順・hotplug・失敗時の制御と正負の試験が必要で、userlandを追加するだけでは強制されません。Buildrootには`BR2_PACKAGE_NFTABLES`があります。
- inetd/dropbear等の構成選択と、実行中の全listenerの有無は別です。socket一覧の実行時監査は今回していません。不要な受信・転送を既定拒否する一方、output acceptは外向き通信を制限しないので、侵害済みserviceの対策は別に設計します。
- 二重のpolicy管理を避けるためnftables一系統を第一候補とします。最小sizeや保守費用の優位は本リポジトリでは試していません。
- 旧素案はloopback・確立済み通信・IPv6 NDを中心とする不完全な例でした。実行用rulesetとはせず、DHCP、RA/ND、必要なICMP/ICMPv6、出力・転送、複数interfaceとatomic replacementを[通信設計](../network.md)で個別に定義します。
- 検証: QEMU 上で `nft list ruleset`・外向き ping/wget・（listen を足した場合）拒否を確認。起動時間・RAM は実験で計測（nft テーブル投入は 1 回きりで数十 ms 見込み）。【推測】

## 7. DNS: Quad9（9.9.9.9）を使う

**結論: Quad9 採用（DNS フィルタ付きリゾルバとして）。実装はローカルスタブリゾルバ経由を推奨。**

- BusyBox の `udhcpc` + `resolv.conf` だけでも Quad9 を指定できるが、DoT（次項）を実現するにはローカルのスタブリゾルバが必要になる。素の nss だけで DoT を話せる仕組みはこの系にはない。
- Quad9 のエンドポイント: `9.9.9.9` / `149.112.112.112`（IPv4）、`2620:fe::fe` 系（IPv6）、DoT は `dns.quad9.net:853`、DoH は `https://dns.quad9.net/dns-query`。【一次: Quad9 公式ドキュメント一般情報、要 URL 検証】
- 実装候補（小さい順）。
  - `unbound`（`vendor/buildroot/package/unbound` あり、`BR2_PACKAGE_UNBOUND`）: DoT フォワード可、設定が多いが堅い。**唯一実用的な候補**。
  - `stubby`/`getdns`: Buildroot package 一覧に存在しないため対象外。
  - `knot-resolver`/`dnsmasq`: dnsmasq は DoT を話せない（上流は平文 UDP のみ）、DoT 目的では不適。
- resolv.conf は `nameserver 127.0.0.1` に固定し、上流はスタブリゾルバが DoT で Quad9 に投げる形がセキュアバイデフォルトに合う。

## 8. DNS over TLS を有効にしたい

**結論: DoT 導入。Quad9:853 へのフォワードをローカルリゾルバに持たせる構成を推奨。**

- 前提: `BR2_PACKAGE_CA_CERTIFICATES` が**現在未設定**で、TLS 検証に必要な CA bundle がない。DoT の採用と合わせて CA 証明書を必須依存にする。
- 候補の実現度確認: `unbound` は `forward-zone { name: "."; forward-tls-upstream: yes; forward-addr: 9.9.9.9@853#dns.quad9.net; }` で実現できる。`stubby` は存在すればこれ一本で済む。Buildroot に `BR2_PACKAGE_STUBBY` があるかは要確認（ない場合 unbound が無難）。
- 平文fallbackを禁止することが要件です。旧記述の`do-udp: no`だけで平文上流通信全体が止まるという保証は撤回します。upstream TLS強制、fallback、UDP/TCP両方、DNS初期化を設定とpacketで確認して採否を決めます。
- 検証: QEMU で `kdig` 相当の問い合わせ結果、パケット解析で 853/TLS のみ確認。

## 9. 時刻合わせ: `time.cloudflare.com`、NTS 要検討

**結論: chrony + NTS を第一候補にする。busybox `ntpd` は現在未コンパイルで、NTS 対応もない。**

- 現行 busybox config には `CONFIG_NTPD` がない（`ntpd` アプレット未導入）。
- NTS（Network Time Security、RFC 8915）対応実装は `chrony`（4.0 以降）と `ntpsec`。Buildroot は `BR2_PACKAGE_CHRONY`・`BR2_PACKAGE_NTPSEC` を持つ。**chrony は NTS クライアントをサポート**し、サーバ設定に `server time.cloudflare.com nts` と書ける（Cloudflare は NTS を提供）。【一次: chrony 4.x ドキュメントの NTS 節、要 URL 検証】
- 信頼する時刻はTLSの証明書期限、metadata期限、log、更新運用の判断に必要です。raw Ed25519署名の数学的検証自体は壁時計に依存しません。NTSを含む初期時刻・RTC・offline時の扱いは[通信設計](../network.md)で別に設計します。
- コスト: chrony 常駐で数百 KB〜1 MB 級 RAM、起動後の初期同期待ちは `chronyc waitsync` か makestep で扱う。【推測】
- 代替: busybox `ntpd` を有効化する最小案は NTS なしの平文 NTP（UDP 123）になり、時刻ソースの真正性が弱いため推奨しない。
