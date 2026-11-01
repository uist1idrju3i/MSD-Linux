# セキュリティ強化項目の調査（2026-11-01）

ユーザーから提示された強化項目を、MSD/Linux（Buildroot + BusyBox、systemd・deb 系なし、ターゲットは BCM2837 / 512 MiB RAM / microSD 起動 / RO SquashFS + A/B 更新）へ適用する観点で調査した。各項目について、現行構成との照合、適用可否、推奨、検証方法を示す。なお現在この機器には**ネットワーク設定自体が未導入**（`udhcpc` は busybox に入っているが interfaces・resolv.conf 系の設定がなく、起動時に net を上げる init もない）ため、ネットワーク前提の項目は「ネットワーク導入時の設計」として整理する。

【一次】現行構成の一次情報は `configs/msd_cardputerzero_defconfig`、`board/cardputerzero/linux.fragment`、`board/cardputerzero/busybox.fragment`、`board/cardputerzero/rootfs-overlay/etc/fstab`、`cmdline_rootfs_{a,b}.txt`、およびビルド済み `output/build/{linux-custom,busybox-1.38.0}/.config` に基づく。

## 1. ファイアウォールをデフォルト有効（最小権限）

**結論: 採用（ネットワーク導入時に nftables でデフォルト drop）。**

- カーネル側は `CONFIG_NF_TABLES=m`・`CONFIG_NF_TABLES_INET=y` ほか多数の netfilter モジュールが defconfig 由来で既に入っており、足りないのは**ユーザーランドの `nft` だけ**。Buildroot は `BR2_PACKAGE_NFTABLES` を持つ。
- 現在 listen しているサービスはない（inetd/dropbear なし）が、将来 Wi-Fi 導入後にサービスを足すたび個別判断するより、既定 drop + outbound accept のベースを先に作るほうが最小権限に合う。
- BusyBox 環境のため `iptables` 系ではなく `nftables`（`nft` バイナリ + 静的ルールファイルを init で `nft -f`）が最も小さい構成。`BR2_PACKAGE_IPTABLES` も可能だが二重実装を避けるため nft 一本がよい。
- 推奨ルール素案: `table inet filter { chain input { policy drop; ct state established,related accept; iif lo accept; icmpv6 type nd-* accept } chain forward { policy drop } chain output { policy accept } }`。機器固有の例外（NTP/DoT・更新用 HTTPS・将来の SSH）は穴を最小化して追記する設計にする。
- 検証: QEMU 上で `nft list ruleset`・外向き ping/wget・（listen を足した場合）拒否を確認。起動時間・RAM は実験で計測（nft テーブル投入は 1 回きりで数十 ms 見込み）。【推測】

## 2. `GRUB_CMDLINE_LINUX_DEFAULT` 最適設定

本機は GRUB を使わず、`board/cardputerzero/cmdline_rootfs_{a,b}.txt` が同じ役割。現行は `root=... rootwait ro rootfstype=squashfs console=tty1 console=serial0,115200 quiet` のみ。

**推奨する追加パラメータ（cmdline でしか効かないもの）:**

| パラメータ | ねらい | 根拠・注意 |
|---|---|---|
| `mitigations=auto` | CPU 緩和策の明示 | A53 は Spectre 系の対象になり得る。カーネル既存値は `CONFIG_UNMAP_KERNEL_AT_EL0=y`（KPTI）と `CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY=y` で既定 ON。`auto` 明示で意図を固定し、無効化事故を防ぐ。【一次: カーネル .config】 |
| `init_on_alloc=1` / `init_on_free=1` | 未初期化メモリの悪用緩和 | security-hardening.md tier B に既挙。CPU 帯域コストあり、A53 での実測が前提。【推測】 |
| `lockdown=confidentiality` | kernel ロックダウン | `SECURITY_LOCKDOWN_LSM` の有効化が前提（tier B 未採用）。firmware 書き込み系や kexec 系と相性が悪い場合があるため要実測。 |
| `slab_merge=off` 相当（`slab_nomerge`） | heap 噴射攻撃の緩和 | KSPP 系の推奨だが RAM 使用量が増える。512 MiB 機器では tier B 評価。 |
| `lsm=` の明示 | LSM 順序の固定 | カーネル側は `CONFIG_DEFAULT_SECURITY_APPARMOR=y`、`CONFIG_LSM` は全 LSM 名を列挙した既定文字列。AppArmor 以外の LSM は未コンパイルのため実害はないが、`lsm=landlock,lockdown,yama,apparmor,bpf` のように実在するものだけを明示する整理は検討余地あり。 |
| `modules_disabled=1` | ロード封じ | **不採用**。署名強制済みだが、USB/Wi-Fi/Bluetooth の hotplug autoload を永久に殺す。既存結論と同じ。 |

`quiet` 維持、`loglevel` は現行どおり。

## 3. AppArmor / SELinux を有効にしたい

**結論: AppArmor を採用方向で進める。SELinux は本機では非推奨。**

- カーネルは既に `CONFIG_SECURITY_APPARMOR=y`・`CONFIG_DEFAULT_SECURITY_APPARMOR=y` で**カーネル側は有効済み**。足りないのはユーザーランド: `apparmor_parser`（Buildroot `BR2_PACKAGE_APPARMOR`）とプロファイル、`aa-status` 確認系。
- BusyBox 環境ではサービス個別のプロファイルを自作する形になる。まずは complain モードで観測 → 実効プロファイルにする段階運用が現実的。主要対象は `msd-update`、ネットワーク系、init 系。
- SELinux は kernel config もユーザーランドも入っておらず、refpolicy の持ち込み・BusyBox 連携のコストが大きい。小さい組み込みで AppArmor と SELinux を併用する実益はなく、**SELinux は不採用**を推奨。
- Landlock（`CONFIG_SECURITY_LANDLOCK=y` 済）と Yama（`SECURITY_YAMA=y` 済）は既に有効。将来アプリ側から Landlock を使う設計余地はある。

## 4. acpid / irqbalance は不要か

- **acpid: 不要。** ACPI 自体が ARM 組み込みでは使われず、本機の電源断対策は watchdog + powerfail-notify + UPS 連携で既に設計済み。`acpid` パッケージも未導入。
- **irqbalance: 不要。** 4 コアの小さい SoC で IRQ 分散の恩恵は小さく、デーモン常駐の RAM・起動時間コストのほうが大きい。必要なら静的な `smp_affinity` 書き込みで足りる。【推測】

## 5. `txqueuelen` チューニングは不要か

- **原則不要。** 100 Mbps 級リンク・小トラフィックではデフォルト 1000 で十分。bufferbloat 対策として下げる実験は価値あるが、現状ネットワーク未導入のため保留。ネットワーク導入時に tc/qdisc と合わせて評価する（`tc` は busybox にはなく `iproute2` 必要）。

## 6. I/O スケジューラ チューニングは不要か

- **要検証（実験価値あり）。** microSD に対して mq-deadline / kyber / bfq / none を比較する実験が可能。ただし 6.18 系では mq が主体で `elevator=` の選択肢は限られる。まず現行値を `/sys/block/mmcblk0/queue/scheduler` で確認してから、ブート時間・更新書き込み時間を基準に選ぶ。`docs/research/cpu-irq-and-sysctl.md` のスケジューラ節と既存ブート時間データを参照し、差分が小さいなら既定維持。

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
- フォールバック: DoT が失敗しても平文 UDP へ落ちないよう `do-udp: no` にする（平文化しないことが要件）。
- 検証: QEMU で `kdig` 相当の問い合わせ結果、パケット解析で 853/TLS のみ確認。

## 9. 時刻合わせ: `time.cloudflare.com`、NTS 要検討

**結論: chrony + NTS を第一候補にする。busybox `ntpd` は現在未コンパイルで、NTS 対応もない。**

- 現行 busybox config には `CONFIG_NTPD` がない（`ntpd` アプレット未導入）。
- NTS（Network Time Security、RFC 8915）対応実装は `chrony`（4.0 以降）と `ntpsec`。Buildroot は `BR2_PACKAGE_CHRONY`・`BR2_PACKAGE_NTPSEC` を持つ。**chrony は NTS クライアントをサポート**し、サーバ設定に `server time.cloudflare.com nts` と書ける（Cloudflare は NTS を提供）。【一次: chrony 4.x ドキュメントの NTS 節、要 URL 検証】
- 時刻がずれていると署名検証・TLS の時刻評価・ログ証拠が崩れるため、この機器では NTP/NTS は「あれば」ではなく設計上の要ピース。
- コスト: chrony 常駐で数百 KB〜1 MB 級 RAM、起動後の初期同期待ちは `chronyc waitsync` か makestep で扱う。【推測】
- 代替: busybox `ntpd` を有効化する最小案は NTS なしの平文 NTP（UDP 123）になり、時刻ソースの真正性が弱いため推奨しない。

## 10. noatime・マウントオプションは最適か

現行 fstab の評価。

| マウント | 現行 | 評価 | 提案 |
|---|---|---|---|
| `/`（squashfs p5） | `ro` | OK。`noatime` は RO では不要だが明示は可 | 変更不要（必要なら `ro,noatime`） |
| `/data`（ext4 p7） | `noauto,noatime,nodev,nosuid,data=ordered,errors=remount-ro` | noatime 済み。`noexec` は未検証事項として記録済み（security-hardening.md、QEMU 実験あり） | `noexec` は用途確認後に採否（現状判断保留） |
| `/tmp` | `tmpfs mode=1777,nosuid,nodev` | `noexec` がない | `noexec` 追加を推奨（実害確認が先） |
| `/run` | `tmpfs mode=0755,nosuid,nodev` | 同上 | `noexec` 追加を検討（init 系が置くもの次第） |
| `/dev/shm` | `tmpfs mode=1777` | `nosuid,nodev,noexec` なし | `nosuid,nodev,noexec` 追加を推奨 |
| `/etc` overlay | tmpfs upper の overlay（S03msd-etc-overlay） | overlay 自体に `noatime,nodev,nosuid,noexec` が付いているか要確認 | マウント引数を確認して同水準に揃える |
| `proc` / `sysfs` / `devpts` | 既定 | `hidepid=` 未指定 | `hidepid=2` 等は機器用途に合わせて検討（本機は他ユーザープロセスを見せたい場面が少ないので方向性としてはあり） |

`data=ordered` 維持（journal=data より性能と integrity のバランスがよい）。【一次: fstab】【推測】

## 11. 導入しないが調査だけ残す項目

### Falco（eBPF ランタイム検知）

- Buildroot には `BR2_PACKAGE_FALCOSECURITY_LIBS`（Falco 本体ではなく検知ライブラリ群）が存在する。依存は grpc、abseil-cpp、protobuf、lua 5.1、tbb（要 glibc、本ツールチェーンは glibc なのでビルド要件は満たせる）と重い。eBPF syscall 監視は kernel BTF・libbpf・膨大なユーザーランドが要り、本機は 512 MiB / BusyBox で常駐させる実用的選択ではない。**調査のみ・非採用**。
- kernel 側は `CONFIG_BPF_SYSCALL=y`、`CONFIG_CGROUP_BPF=y` があるが `CONFIG_DEBUG_INFO_BTF` が確認できておらず、BTF 不在なら CO-RE 系の Falco driver は動かない。
- 同等の目的で将来使える軽量手段: `kernel.dmesg_restrict` 等の観測制限、audit（`CONFIG_AUDIT`）の限定的導入。

### Suricata（IDS/IPS）

- Buildroot に `BR2_PACKAGE_SURICATA` は存在する（要 rust host、jansson、libhtp、libpcap、libyaml、pcre2）。ただしネットワーク未導入・常駐重い・ルール更新運用が要る。組み込み最小構成では過剰。**調査のみ・非採用**。必要になった場合は nftables の ct/ログ + ホスト側分析のほうが適合する。

### debsums（ファイル整合性）

- deb 系がないため対象外。同等目的は dm-verity（tier B、QEMU 検証済み）で rootfs 側を担保し、`/data` 側は `msd-update` の署名・read-back 設計を流用する方向が合う。**対象外**。

### Lynis（監査スクリプト）

- POSIX sh ベースで BusyBox でも動く可能性が高い。Buildroot に `BR2_PACKAGE_LYNIS` があり、監査用途で**導入ではなく CI/一時実行として評価可能**。セキュリティ監査の定期実行を設計に組み込むかは別途判断。
- このリポジトリには既に vendor の Lynis 調査や hardening 実験（S6 tier B）があるため、Lynis の指摘は記録として残し、実装上の採否は別途決める整理が合う。

### Zenarmor（次世代ファイアウォール/アプリケーション制御）

- Sunny Valley Networks の商用 NGFW。主な展開先は OPNsense/pfSense CE のプラグイン、または Linux（Ubuntu/Debian/RHEL 系）ゲートウェイ。**Buildroot パッケージなし、プロプライエタリなバイナリ**。
- ハードウェア要件（公式）: 最小でも x86_64 デュアルコア + **1 GB RAM**（インストーラが 1 GB 未満を拒否）、レポート用 Elasticsearch がメモリを大量に消費し、推奨は 8 GB。本機は ARM64（BCM2837）+ 512 MiB のため**アーキテクチャ・RAM 両面で対象外**。【一次: [Zenarmor hardware requirements](https://www.zenarmor.com/docs/introduction/hardware-requirements)】
- 管理面はクラウド（SaaS コンソール）前提で、本機のエアギャップ/最小構成と相性が悪い。
- **効能（もし使えたら何を得るか）**: L3/L4 では識別できない「アプリケーション層」の可視性とポリシー（L7 DPI によるアプリ識別・ブロック）、カテゴリベースの Web フィルタリング、TLS SNI ベースのフィルタ（完全 MITM なしで接続先ドメイン単位の制御）、脅威インテリジェンス、詳細なレポート/可視化。
- **本機での同等獲得方法**: 既知悪性ドメインの遮断は Quad9（本書 7/8 節）で DNS 層カバー済み。SNI ベース制御は必要になれば nftables では難しく、eBPF/透過プロキシを要するため範囲外。レポートは本機の syslog + ホスト側集約で代替する方向。**非採用・調査のみ**。

### ClamAV（シグネチャ型マルウェア検知）

- Buildroot に `BR2_PACKAGE_CLAMAV` あり（要 libstdcpp、rust host、json-c、libcurl、libmspack、libxml2、openssl）。
- 実用面: `clamd`/`clamscan` はシグネチャ DB（main+daily cvd）をメモリに展開して動く設計で、常時 1 GB 級の RAM を要する傾向がある。**512 MiB ではデーモンも単発スキャンも現実的でない**。【推測、実測要】
- **効能**: 既知マルウェアのシグネチャ検知、on-access スキャン（fanotify 経由）、フィッシング/PUA 検出、freshclam による日次シグネチャ更新。
- **本機での整理**: 読み取り専用 rootfs は署名+dm-verity（tier B）で改ざん検知の対象になり、AV スキャンの対象外。唯一書き込める `/data` は `noexec` を決めれば「実行されないデータ置き場」になり、AV による検知の意義は薄い。検査が要るなら**デバイス側ではなく、更新物・持ち込み物を配布側/ホスト側でスキャン**する運用にするほうが、RAM と CPU を使わずに同じ効果が得られる。**非採用・調査のみ**。

### Proofpoint ET Pro / ET Open（IDS ルールセット）

- Emerging Threats（ET）は Proofpoint の IDS ルールセットで、Snort/Suricata 系エンジンに流し込む**ルール供給源**であって製品そのものではない。ET Open（無償コミュニティ版、更新に遅延・件数制限あり）と ET Pro（有償サブスクリプション、フルセット・日次更新）に分かれる。【推測、価格・条項は要検証】
- **効能**: マルウェア C2 通信、エクスプロイト試行、スキャン・ブルートフォース、ポリシー違反系の既知パターンを IDS が検知できるようになる。Quad9 が DNS 層で遮断する悪性ドメインとは別経路（パケット内容・挙動）の防御層になる。
- **本機への適用可否**: 前提の Suricata/Snort エンジン自体が非採用（11 節・RAM と運用負荷）のため、ルール単体の導入意義はない。**非採用・調査のみ**。将来 Suricata を別のホスト/ゲートウェイ側に置く構成になった場合、ルール源として ET Open → ET Pro の順で評価するのが順当。
- ルール更新の運用（`suricata-update`/`pulledpork` による日次取得）も記録しておく。

## 12. systemd の ProtectSystem 等 Sandboxing（調査のみ）

- 本機に systemd はないため `ProtectSystem=`・`PrivateTmp=`・`NoNewPrivileges=` 等の directive は直接対象外。**調査のみ**。
- 概念のマッピング（本機で使える同等物）:
  - `ProtectSystem=strict` → rootfs RO + `/data` 制限マウント（既に近い構造）
  - `NoNewPrivileges` → 実行時の setuid 無効化は `nosuid` マウントと LSM で代替。BusyBox のサービス起動に `prctl(NO_NEW_PRIVS)` 相当を組み込む手段は別途要る（init スクリプト or 小さいラッパ）。
  - `PrivateTmp`/`ProtectHome`/`ProtectKernel*` → mount namespace での隔離が同等概念。BusyBox の `unshare`・`nsenter` アプレット有無を確認し、必要なら util-linux 系を足す。
  - LSM による sandbox 化は AppArmor（カーネル ON 済）のプロファイルとして実装する方向が現実的。

## 13. sysctl の最適化（提示リストの照合）

提示リストを、本機の現状・ハード（512 MiB、100 Mbps 級想定、microSD）と照合する。既存の `docs/research/tunables-sysctl.md` に 606 項目の既定値一覧があり、今回は提示値との差分に絞る。

### 採用方向でよいもの

| 項目 | 提示値 | 本機での判断 |
|---|---|---|
| `net.ipv4.conf.*.rp_filter=1` | strict RP | 採用（単一経路前提で安全） |
| `net.ipv4.tcp_syncookies=1` | 既定と同じ | 明示維持 |
| `icmp_ignore_bogus_error_responses=1` など ICMP 系 | 既定と同じ | 明示維持 |
| `conf.*.accept_redirects/send_redirects/accept_source_route=0` | 既定を 0 で固定 | 採用（明示は害なし） |
| `kernel.sysrq=0` | 全 SysRq 無効 | 採用方向（開発時の診断手段は別途限定可） |
| `kernel.dmesg_restrict=1` | 既定と同じ（`CONFIG_SECURITY_DMESG_RESTRICT=y` 済） | 明示維持 |
| `kernel.kptr_restrict=2` | 1→2 | 採用（既存 `kernel.kptr_restrict` の既定確認のうえ） |
| `kernel.yama.ptrace_scope=1` | 既定と同じ（Yama ON） | 明示維持 |
| `kernel.unprivileged_bpf_disabled=1` | 1 = reboot までロック | 採用（BPF_SYSCALL=ON だが本機用途で必要とは限らない） |
| `kernel.kexec_load_disabled=1` | 0→1 | kernel `CONFIG_KEXEC` が設定されているか要確認。無効なら記述だけでよい |
| `kernel.io_uring_disabled=2` | 全プロセス禁止 | `CONFIG_IO_URING=y` 存在。io_uring を使うパッケージがないなら 2 で固定可、用途次第 |
| `kernel.apparmor_restrict_unprivileged_userns=1` | Ubuntu 由来の既定 | 本機は USER_NS=y。AppArmor の userns 制限を使う設計に合わせて採用（非 Ubuntu でも機能する範囲で） |
| `kernel.panic=60` / `panic_on_oops=1` | panic 後自動再起動 | **要検討**: powerfail/WD 復旧設計と整合するか確認してから。再起動より「止まって記録」が正しい場面もある |
| `vm.swappiness=60` | 既定と同じ | swap/zswap 構成次第。現状 swap なしなら実害なし |
| `net.core.default_qdisc=fq` / `tcp_congestion_control=bbr` | BBR + fq | ネットワーク導入時に検討。カーネルに `CONFIG_TCP_CONG_BBR`・`CONFIG_NET_SCH_FQ` があるか要確認 |
| TCP の各種（`tcp_timestamps` `mtu_probing` `fastopen` `sack` `moderate_rcvbuf` `slow_start_after_idle` `no_metrics_save` `window_scaling` 等） | 概ね既定と同じか小改善 | ネットワーク導入時に一括適用でよい。明示値はそのまま採用候補 |
| `tcp_syn_retries/synack_retries` 短縮・`fin_timeout`・`tw_reuse`・`keepalive_*` | 短めのタイムアウト | 採用候補。機器のネットワーク特性に合わせて実測で調整 |
| `ip_local_port_range=32768 65535` | 上限を 65535 まで拡大 | 採用候補 |
| `net.core.netdev_max_backlog`/`somaxconn`/`tcp_max_syn_backlog`/`tcp_max_tw_buckets` | 既定より大きい値 | 512 MiB 機器では提示値（2 GB 前提）より小さめを選ぶべき。実測してスケール |
| `rmem_max`/`wmem_max`/`tcp_rmem`/`tcp_wmem` | 8 MiB 級 | 512 MiB 機器では大きすぎる可能性。BBR を使うなら別途調整 |

### 注意点

- 提示リストは「2 GB RAM / 100 Mbps / サーバ用途」を前提にした箇所（バッファ・キュー・backlog）があるため、512 MiB の本機にそのまま適用しない。値はスケールしてから入れる。
- sysctl の適用方法は BusyBox では `sysctl -p`（`/etc/sysctl.conf` または `sysctl.d/` 読み込み）で、init 内で適用する形になる（`/etc/sysctl.conf` 新設か `S*` init で適用）。sysctl 適用のタイミングをどこに置くかは実装判断。

## 14. Debian/Ubuntu におけるコンパイルオプション強化の経緯

Debian/Ubuntu が「ディストリビューション全体のデフォルト」を段階的に強化してきた流れは、本機（Buildroot で全体を自前ビルド）にとって「どのフラグが本当に効いたか」の実績表として使える。

### Debian の経緯

- **hardening-wrapper → dpkg-buildflags**: 初期は `hardening-wrapper` で個別有効化していたが、dpkg 1.16.1 系で `dpkg-buildflags` に一本化され、wheezy（Debian 7）のリリースゴールとして既定フラグに **`-Wl,-z,relro`（partial RELRO）、`-fstack-protector`、`-D_FORTIFY_SOURCE`、`-Wformat -Werror=format-security`** が入った。この時点で PIE と `-z now`（bindnow）は既定外で、`DEB_BUILD_MAINT_OPTIONS=hardening=+all` の opt-in。【一次: [Debian HardeningWalkthrough](https://wiki.debian.org/HardeningWalkthrough)、[Hardening](https://wiki.debian.org/Hardening)】
- **stretch（Debian 9）頃**: PIE を既定にする案が持ち上がり、dpkg ではなく **GCC 6 の `--enable-default-pie` configure オプション経由で gcc が既定 PIE を吐く**形にした（`-fPIC` 衝突を gcc 側で自動解決させるため）。bindnow もこの時期に既定化の方向へ。【一次: [debian-devel 2016-05](https://lists.debian.org/debian-devel/2016/05/msg00229.html)】
- 以後: `-fstack-clash-protection`、x86 向け `-fcf-protection`（CET）などは gcc 側の既定/機能有効化として吸収される形が主流。`DEB_BUILD_MAINT_OPTIONS` による feature 単位の切替（`hardening=+pie,-fortify` 等）は現在も有効。

### Ubuntu の経緯

Ubuntu は「ディストリビューションの gcc に既定フラグを埋め込む」方針を早くから採り、歴史的に Debian より先行している点が特徴。

- **Ubuntu 6.10（2006）**: `-fstack-protector` を gcc 既定で有効化（glibc 側の stack check ルーチンへのリンクを gcc パッチで既定化）。【一次: [Ubuntu ToolChain/CompilerFlags](https://wiki.ubuntu.com/ToolChain/CompilerFlags)】
- **Ubuntu 8.10（2008）**: `-D_FORTIFY_SOURCE=2` を既定化。【一次: Ruffell 氏の調査まとめに基づく wiki 記述】
- **Ubuntu 10.10（2010）**: `--param ssp-buffer-size=4` で stack protector の適用対象を拡大。
- **Ubuntu 14.10（2014）**: `-fstack-protector-strong` に切替。
- **Ubuntu 16.10**: PIE を amd64/ppc64el/s390x で既定化（gcc の default-pie 切替）。【一次: [Ubuntu Security documentation - compiler flags](https://documentation.ubuntu.com/security/security-features/process-memory/compiler-flags/)】
- **Ubuntu 17.10**: 全アーキテクチャで PIE を既定化。x86 以外はレジスタ数の影響が小さいため全 arch 化の判断。
- **その後**: `-Wl,-z,now`（bindnow）の既定化、x86 向け `-fcf-protection`（Intel CET）・`-fstack-clash-protection`、`-D_GLIBCXX_ASSERTIONS` 等が 19.10〜24.04 頃にかけて段階導入（個別リリース単位の正確な有効化時期は要検証）。

### 教訓（本機への適用）

- Ubuntu/Debian が得た効果の実績: ASLR の実効化（PIE）、リターンアドレス破壊の検知（SSP strong）、memcpy 系のバッファ境界検査（FORTIFY）、GOT の RO 化（RELRO/bindnow）、format string 脆弱のコンパイル時検出。**これらは互いに別の攻撃経路を閉じる層**で、どれか 1 つではなく重ねる設計。
- 本機の Buildroot 設定は既に **`BR2_PIC_PIE=y`、`BR2_SSP_STRONG=y`、`BR2_RELRO_FULL=y`（bindnow 含む）、`BR2_FORTIFY_SOURCE_3=y`** で、Ubuntu が 10 年以上かけて既定化したセットをほぼ踏襲している。【一次: `output*/.config`】
- 残りの差分候補: `-fstack-clash-protection`（Buildroot に個別オプションはなく、gcc 側 `-fstack-clash-protection` を `BR2_TARGET_OPTIMIZATION` に足す形）、`-fcf-protection` は ARM64 非対象（x86 専用）、`-D_GLIBCXX_ASSERTIONS` は stdc++ を使うパッケージがほぼないため効果薄。
- Debian/Ubuntu の「default-pie を gcc configure で有効化した」経緯は、Buildroot でも `BR2_PIC_PIE` がグローバルに効くため同等とみなせる。
- Ubuntu の hardening は「gcc パッチで既定にし、壊れる個別パッケージだけ例外的に外す」運用で、Buildroot の per-package `*_CONF_OPTS`/`CFLAGS` と同じ発想。

## 15. システムソフトウェアの Rust 化（最新情報）

「C 系の長年のバグの素因であるメモリ安全を、言語レベルで取る」動きが 2025 年に Debian/Ubuntu 系で顕在化した。本機は BusyBox ベースで対象ソフト自体を持たないものが多いが、方向性として記録する。

### 各ソフトの状況（2025-11-01 時点）

| ソフト | 状況 | 本機との関係 |
|---|---|---|
| sudo-rs（Trifecta Tech） | Ubuntu 25.10 で既定の sudo 実装に採用（元の sudo は `sudo.ws` として併存、0.2.8 で `sudoedit`・NOEXEC・AppArmor 切替に対応）。CVE-2021-3156（2011 年から潜伏した sudo のヒープ破壊）を「メモリ安全で防げた類」として採用理由に挙げられている。【一次: [Ubuntu 25.10 release notes](https://documentation.ubuntu.com/release-notes/25.10/)、[Trifecta Tech sudo-rs](https://trifectatech.org/projects/sudo-rs/)】 | 本機に sudo はない（BusyBox の `su` のみ）。対象外 |
| rust-coreutils（uutils coreutils） | Ubuntu 25.10 で既定の coreutils に（0.2.2、GNU 版は併存で切替可能、互換性の差分リストを公開）。base64 が大幅に高速化。【一次: 同上】 | 本機は BusyBox アプレットで coreutils を持たない。Buildroot に uutils のパッケージはない（GNU `coreutils` のみ収録）【一次: `vendor/buildroot/package/`】 |
| ntpd-rs（Trifecta Tech） | Debian パッケージあり（1.9.0）。NTS を早期に実装した実装として知られる。Ubuntu 25.10 は ntpd-rs ではなく Chrony+NTS を既定に採用。【一次: [Debian Rust tracker](https://rustsec.debian.net/pkgs/ntpd-rs.html)、Trifecta Tech】 | Buildroot 未収録（`openntpd`・`chrony`・`ntpsec` のみ）。9 節の NTS 案で Chrony を選んだ現状、別選択肢として名前だけ残す |
| APT（Debian） | 2025-11 に APT メンテナの Julian Klode が「2026-05 以降、APT に Rust の強い依存を入れる」と Debian 開発者リストで表明。.deb/.ar/tar のパーサと HTTP 署名検証が第一候補で、Sequoia（Rust 製 OpenPGP 実装）系を使う方針。【一次: [The New Stack](https://thenewstack.io/debian-mandates-rust-for-apt-reshaping-ubuntu-and-other-linux-distros/)】 | 本機に APT はない。Debian 系を使う将来の派生物で影響が出る可能性だけ記録 |
| zlib-rs / libzstd-rs | Trifecta Tech の data-compression イニシアティブで進行。sudo-rs 0.2.8 が両者対応済み。【一次: Trifecta Tech】 | squashfs/zstd の伸張を行う mksquashfs・カーネルとは別レイヤ。現状関係なし |
| Sequoia（OpenPGP） | APT の署名検証を支える Rust 実装として Debian が採用方向。【一次: 同上】 | 本機の msd-update は Ed25519 直接検証（OpenPGP 非使用） |
| statime（PTP） | Trifecta Tech の時刻同期イニシアティブで進行中。IEEE 1588 PTP の Rust 実装。 | NTP ではなく PTP。時計同期の選択肢に入らない |

### 傾向と本機への示唆

- 採用されているのは「**権限境界・パーサ・プロトコル実装**」（sudo、.deb/HTTP 署名、NTP/NTS）で、攻撃面が外部入力の解釈に集中する領域。本機の外部入力面は msd-update の署名検証とカーネルのプロトコル処理が主。
- 本機はユーザー空間が BusyBox（C）＋カーネルで構成され、置き換えられる個別ソフトがそもそもないため、**Rust 化の恩恵は「依存先の上流が安全になる」形で間接的に入る**。例: ホスト側ビルド環境が Debian 系なら、将来 APT・sudo が Rust 化した恩恵を受ける。
- 仮に将来 userspace を拡充するとき、uutils coreutils・sudo-rs・ntpd-rs は「Buildroot 未収録」のため手組みが要る（外部 toolchain + cargo ビルド）。対費用効果は現状低い。

## 実装の優先順位案

1. **先にやる（低コスト）**: `fstab` の `/tmp`・`/run`・`/dev/shm` への `noexec`/`nosuid`/`nodev` 追加、`/data` `noexec` の採否結論、sysctl ファイルの整備、`mitigations=auto` 等の cmdline 追加。
2. **中**: `nftables`（`BR2_PACKAGE_NFTABLES` + 静的ルール）、`BR2_PACKAGE_CA_CERTIFICATES`、DoT 用 unbound/stubby、chrony + NTS。
3. **後で評価**: AppArmor プロファイル整備（complain 観測 → enforce）、io scheduler 実測、qdisc/BBR、hidepid。
4. **対象外**: acpid、irqbalance、SELinux（本機では AppArmor）、debsums（deb なし）、systemd 系（なし）、Suricata/Falco（調査のみ）。

## 検証方法

- カーネル・sysctl・マウント・nftables は QEMU で回帰確認（起動時間差分は S1/S14 方式で測る）。
- DoT/NTS は実 DNS/時刻サーバへの到達性が要るため QEMU ネットワーク構成での確認が必要。実機での時間確立と TLS 失敗時の挙動も要確認。
- 実験は experiment-record スキルに従い、`docs/experiments/` に記録する。
