# kernel・mount・sysctlの強化案の履歴

[強化項目の案内へ戻る](README.md) / [処理ごとの権限](../privileges.md)

以下は元の2〜6・10・13節です。GRUBを使わないCM0の起動経路、kernel設定とruntime policy、mount option、sysctlを分けます。ACPIを使うARMシステムもあるため、CM0の構成からARM全般を断定しません。irqbalanceの効果と費用は本機の実測ではありません。

## BusyBoxのsysctl読込み

固定[Buildrootのbusybox.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/busybox/busybox.mk)が指定する[BusyBox 1.38.0の原文archive](https://www.busybox.net/downloads/busybox-1.38.0.tar.bz2)を読みました。archiveのSHA-256は`34f9ea6ff8636f2c9241153b9114eefa9e65674a45318ae1ef95bb5f31c53bb2`です。`procps/sysctl.c`のusage（33行）とmain（317〜333行）は、引数なしの`-p`で`/etc/sysctl.conf`、引数ありでは指定した各ファイルを開きます。`sysctl.d`を自動列挙する処理ではありません。

後段の「`/etc/sysctl.conf` か `sysctl.d`」という案内はこの点を訂正します。明示的にファイルを渡す処理、directoryの選別・順序、起動時の呼出しを別に設計する必要があります。これは固定sourceの確認であり、製品に新しいsysctl設定を入れた、または起動時の反映を実機で確かめたという意味ではありません。

## 2. `GRUB_CMDLINE_LINUX_DEFAULT` 最適設定

本機は GRUB を使わず、`board/cardputerzero/cmdline_rootfs_{a,b}.txt` が同じ役割。現行は `root=... rootwait ro rootfstype=squashfs console=tty1 console=serial0,115200 quiet` のみ。

**推奨する追加パラメータ（cmdline でしか効かないもの）:**

| パラメータ | ねらい | 根拠・注意 |
|---|---|---|
| `mitigations=auto` | CPU 緩和策の明示 | A53 は Spectre 系の対象になり得る。カーネル既存値は `CONFIG_UNMAP_KERNEL_AT_EL0=y`（KPTI）と `CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY=y` で既定 ON。`auto` 明示で意図を固定し、無効化事故を防ぐ。【一次: カーネル .config】 |
| `init_on_alloc=1` / `init_on_free=1` | 未初期化メモリの悪用緩和 | security-hardening.md tier B に既挙。CPU 帯域コストあり、A53 での実測が前提。【推測】 |
| `lockdown=confidentiality` | kernel ロックダウン | `SECURITY_LOCKDOWN_LSM` の有効化が前提（tier B 未採用）。firmware 書き込み系や kexec 系と相性が悪い場合があるため要実測。 |
| `slab_merge=off` 相当（`slab_nomerge`） | heap 噴射攻撃の緩和 | KSPP 系の推奨だが RAM 使用量が増える。512 MiB 機器では tier B 評価。 |
| `lsm=` の明示 | LSM順序の固定 | CONFIG_LSMの文字列、compileした機能、実行時の有効一覧は別です。AppArmor以外が全て未compileという旧説明は誤りで、YamaとLandlockも設定されています。lockdown等も名前だけで利用可能とせず、最終設定・起動引数・runtimeを照合して決めます。 |
| `modules_disabled=1` | ロード封じ | **不採用**。署名強制済みだが、USB/Wi-Fi/Bluetooth の hotplug autoload を永久に殺す。既存結論と同じ。 |

`quiet` 維持、`loglevel` は現行どおり。

## 3. AppArmor / SELinux を有効にしたい

**結論: 固定kernelのAppArmorを再利用する案を第一候補とし、policyと運用費用を評価する。製品での強制は未実装。**

- 固定CIの最終設定には`CONFIG_SECURITY_APPARMOR=y`・`CONFIG_DEFAULT_SECURITY_APPARMOR=y`があります。profileの読込み、attachment・exec遷移、enforce状態、必須policy失敗時の起動停止、拒否試験が必要です。kernel設定やparserの存在だけでは保護済みにしません。
- 上流の利用可能なprofileを先に調べ、必要なら対象serviceのprofileを作ります。complainは試験用の観測であり、製品のenforceを代替しません。root updaterをprofileで囲むだけで解析・認可・writerの分離が完成するわけでもありません。
- SELinuxは固定CI kernelでは無効です。policy・Buildroot/BusyBox連携・保守費用を比較対象とし、恒久的に劣る方式と断定しません。major LSMの無条件な併用を前提にしません。
- YamaとLandlockのkernel設定はありますが、Landlockは対象processによるruleset適用が必要です。上流の制限、ABI確認、拒否試験とYamaの既存証拠を[原則とLinux機構](../principles.md)で分けて扱います。

## 4. acpid / irqbalance は不要か

- **acpid: 不要。** ACPI 自体が ARM 組み込みでは使われず、本機の電源断対策は watchdog + powerfail-notify + UPS 連携で既に設計済み。`acpid` パッケージも未導入。
- **irqbalance: 不要。** 4 コアの小さい SoC で IRQ 分散の恩恵は小さく、デーモン常駐の RAM・起動時間コストのほうが大きい。必要なら静的な `smp_affinity` 書き込みで足りる。【推測】

## 5. `txqueuelen` チューニングは不要か

- **原則不要。** 100 Mbps 級リンク・小トラフィックではデフォルト 1000 で十分。bufferbloat 対策として下げる実験は価値あるが、現状ネットワーク未導入のため保留。ネットワーク導入時に tc/qdisc と合わせて評価する（`tc` は busybox にはなく `iproute2` 必要）。

## 6. I/O スケジューラ チューニングは不要か

- **要検証（実験価値あり）。** microSD に対して mq-deadline / kyber / bfq / none を比較する実験が可能。ただし 6.18 系では mq が主体で `elevator=` の選択肢は限られる。まず現行値を `/sys/block/mmcblk0/queue/scheduler` で確認してから、ブート時間・更新書き込み時間を基準に選ぶ。`docs/research/cpu-irq-and-sysctl.md` のスケジューラ節と既存ブート時間データを参照し、差分が小さいなら既定維持。

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
