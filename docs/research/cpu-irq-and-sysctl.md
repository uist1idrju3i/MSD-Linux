# CPU・割り込み・sysctl の調整余地

## 調査範囲

確認基準日は 2026 年 10 月 19 日です。対象カーネルは本リポジトリが指定する Raspberry Pi Linux commit `234188315037848e5b07d65b85d38edc64095caa`、Buildroot は gitlink commit `d6061d653d7fb215c2409c59e4bfad1b9d677215`、M5 ドライバーは gitlink commit `75518549a2640486f5d13ea72ca4935b198d7c20` です。Raspberry Pi の設定資料は documentation commit `ddea98e98dafe9419feb4fd82710c2fbdef7dc44` を読みました。

調べた問いは次の 3 つです。

1. RP3A0（BCM2837）の 4 コアを使い切れているか。irqbalance は効くか。
2. あえて 1 コアだけを動かし、電力と熱の余裕を 1 コアに集めると速くなるか。
3. VPS 向けの運用記事（sysctl、I/O スケジューラー、SSH 強化など）のうち、MSD/Linux に当てはまるものはどれか。

ソースと公式資料を読んだ結果です。CM0 実機と QEMU のどちらでも測っていません。効果の見込みは【推測】と記します。

## 割り込みの分散と irqbalance

| 確認したこと | 内容 | 確認度 |
|---|---|---|
| 担当コアを指定できるか | 周辺機器の割り込みを扱う `armctrl_chip`（`irq-bcm2835.c`）と、その上位の `bcm2836_arm_irqchip_gpu`（`irq-bcm2836.c`）は `irq_set_affinity` を持ちません。そのため `/proc/irq/*/smp_affinity` を書き換えても担当コアは変わらず、irqbalance は何もできません。 | 【一次】 |
| カーネルがすでに分散しているか | SMP 構成では `armctrl_chip` の `.irq_ack` が `bcm2836_arm_irqchip_spin_gpu_irq()` を呼びます。この関数は `LOCAL_GPU_ROUTING` を書き換え、周辺機器の割り込みの送り先を、動作中の次のコアへ順に回します。4 コアへの分散は、irqbalance なしで行われています。 | 【一次】 |
| 結論 | irqbalance を入れても分散は変わらず、常駐プロセスが 1 つ増えるだけなので採用しません。割り込みが多い処理（Wi-Fi など）で 1 コアに偏る問題が実機で見つかった場合は、RPS/XPS などソフトウェア側の分散を別に検討します。 | 【推測】 |

## コア数・周波数・熱

| 確認したこと | 内容 | 確認度 |
|---|---|---|
| 周波数はコアごとか | DT の `__overrides__` は `arm_freq` を cpu0〜cpu3 の `clock-frequency` に同じ値で渡します。cpufreq は `raspberrypi-cpufreq` がファームウェアのクロックから上限と下限を求め、`cpufreq-dt` に渡します。周波数は 4 コアで 1 系統です。1 コアだけを速くする仕組みはありません。 | 【一次】 |
| 上限 | 公式資料の既定値表では、Pi Zero 2 W（CM0 と同じ RP3A0）は `arm_freq` が 1000 MHz、`arm_freq_min` が 600 MHz です。CM0 の値は資料の表にありません。 | 【一次】（Zero 2 W）、【未確認】（CM0） |
| `arm_boost=1` の効果 | 公式資料は「ボードとファームウェアが対応する最高周波数に上げる」と説明します。既定値表で `arm_boost` によって値が変わるのは Pi 4B R1.4（1500 → 1800 MHz）だけです。CM0 で値が変わるかは分かりません。`board/cardputerzero/config.txt` のコメント「Enable the Raspberry Pi 3 CPU boost mode」は、資料の説明と一致しません。 | 【一次】（資料）、【未確認】（CM0 の実効値） |
| 使わないコアを止められるか | `bcm2837.dtsi` の 4 コアは `enable-method = "spin-table"` です。arm64 の `smp_spin_table_ops` には `cpu_init`、`cpu_prepare`、`cpu_boot` しかなく、`cpu_disable` と `cpu_die` がありません。実行中に `/sys/devices/system/cpu/cpuN/online` へ 0 を書いてコアを止めることはできません。 | 【一次】 |
| `maxcpus=1` | 起動オプションで 3 コアを起こさず、ファームウェアの待機ループに残すことはできます。待機中のコアがどれだけ電力を使うかは資料がなく、OS が使っていないコアは普段から待機命令で止まっているため、節電効果は小さいと見ています。 | 【推測】 |
| 熱による減速 | 公式資料によると、80〜85°C で Arm コアが、85°C を超えると Arm コアと GPU が減速します。`temp_soft_limit` は 3A+/3B+ 専用です。電圧が 4.63 V（±5%）を下回った場合も減速します。 | 【一次】 |
| 1 コアに集める効果 | 周波数の上限は上がらないので、短い処理は 4 コアのほうが速いはずです。効果がありうるのは、長い高負荷で 4 コアだと 80°C に達して減速し、1 コアなら達しない場合だけです。筐体内の温度上昇を測るまで判断できません。 | 【推測】 |
| 現在の制御方針 | 基底の `bcm2711_defconfig` は `CPU_FREQ_DEFAULT_GOV_ONDEMAND=y` で、`schedutil`、`conservative`、`powersave`、`userspace` の各 governor も組み込みます。`linux.fragment` はこれを変えていません。`CPU_IDLE=y` ですが、`bcm2837.dtsi` に `idle-states` はありません。 | 【一次】 |
| ユーザー空間のビルド | `BR2_cortex_a53=y` で、最適化は Buildroot の既定 `BR2_OPTIMIZE_2`（`-O2`）です。 | 【一次】 |

### 実機で比べる候補

どれも実機でしか測れません。QEMU では温度、電力、実際の周波数、ファームウェアによる減速を再現できません。

| 候補 | 測る値 |
|---|---|
| `ondemand`（現状）、`schedutil`、`performance`、起動中だけ `performance` にして起動後に戻す案 | 起動時間、`scaling_cur_freq` と `vcgencmd measure_clock arm` の差、温度、消費電流 |
| `maxcpus=1` と 4 コア | 長時間の負荷での処理量、温度の推移、`get_throttled` の減速ビット |
| `arm_boost=1` の有無 | `vcgencmd get_config arm_freq` と実クロック |
| `/proc/interrupts` の各コアの数 | 割り込みが本当に 4 コアへ回っているか |

## VPS 運用記事との照合

照合した記事は「さくらのAI Engine(基盤モデル無償プラン)×さくらのVPSで、HermesAgentを無人運用してみる」（Qiita、2026-07-24 投稿）です。記事の対象は RAM 2 GB の x86 VPS で、SSH で入る常時接続のサーバーです。MSD/Linux は RAM 512 MB の端末で、SSH を実装せず、rootfs は読み取り専用の SquashFS、init は BusyBox です。

### sysctl を置く場所

Buildroot の BusyBox パッケージは、`CONFIG_BB_SYSCTL=y` で procps-ng を選んでいない場合に `S02sysctl` をインストールします。`S02sysctl` は `/etc/sysctl.d/` などの `*.conf` を読みます。本リポジトリの defconfig はこの条件に当てはまります。CI の成果物の rootfs に `/etc/init.d/S02sysctl` があり、QEMU の起動ログに `Running sysctl: OK` が出ることを確かめました。rootfs に `/etc/sysctl.d/` の設定はありません。rootfs-overlay に drop-in を置けば、起動時に反映されます。【一次】【QEMU】

### `kernel.sysrq = 0` は電源断対策を止める

記事は `kernel.sysrq = 0` で SysRq を全部止めます。MSD/Linux でこれを使うと、電源断対策が動かなくなります。

- `powerfail_suo.c` は GPIO6 の割り込みを受けると `handle_sysrq('u')`（緊急の読み取り専用 remount）を呼びます。【一次】
- `handle_sysrq()` は、まず `sysrq_on()` で `kernel.sysrq` が 0 でないことを確かめ、次に `__handle_sysrq(key, true)` の中の `sysrq_on_mask()` で、remount のビットが立っているかを確かめます。値が 0 だと remount は実行されません。【一次】
- 基底の defconfig は `MAGIC_SYSRQ_DEFAULT_ENABLE=0x1f6` で、remount のビット `SYSRQ_ENABLE_REMOUNT`（0x20）を含みます。QEMU で起動したイメージでも `kernel.sysrq` は 502（`0x1f6`）でした。現在は remount が動きます。【一次】【QEMU】
- 絞る場合は `kernel.sysrq = 32` が候補です。remount だけを残し、キーボードからの他の SysRq を止めます。root が `/proc/sysrq-trigger` に書く経路は `__handle_sysrq(c, false)` なので、値に関係なく動きます。【一次】（ソース）、【推測】（採用の判断）

### 項目ごとの判断

| 記事の項目 | MSD/Linux での判断 | 理由 |
|---|---|---|
| `kptr_restrict = 2`、`dmesg_restrict = 1`、`yama.ptrace_scope = 1` | 候補 | 低コストで、[セキュリティ・ハードニング](security-hardening.md)の A 段の sysctl と重なります。Yama は `CONFIG_LSM` で有効です。 |
| `unprivileged_bpf_disabled = 1`、`io_uring_disabled = 2`、`kexec_load_disabled = 1` | 候補（S1 と合わせて判断） | 現在は `BPF_UNPRIV_DEFAULT_OFF=y`（実行時の値は 2）です。BPF と io_uring を Kconfig で外す案は S1 の削減候補と重なるので、外すか sysctl で止めるかを一緒に決めます。基底の defconfig に kexec の設定は見つかっていません。 |
| `kernel.sysrq = 0` | 不採用 | 上記のとおり電源断時の remount が止まります。絞るなら 32 です。 |
| `kernel.panic = 60`、`panic_on_oops = 1` | 候補 | 無人で動く端末に合います。tryboot の試し起動中に panic すると、再起動で元のスロットに戻るので、A/B 更新の失敗検知にも使えます。秒数は watchdog（`S01msd-watchdog` の `-T 15`）と合わせて決めます。現在の cmdline に `panic=` はありません。 |
| `rp_filter`、redirect と source route の拒否、`icmp_echo_ignore_broadcasts` など | 候補 | Wi-Fi や USB ネットワークのクライアントとして使う場合に効きます。値を書くだけで済みます。 |
| 既定値と同じ値も明示して固定する方針 | 候補 | カーネルの更新で既定値が変わっても設定が変わらないようにする考え方で、固定版の更新確認と同じ発想です。 |
| BBR + fq、TCP バッファー 8 MB、backlog 系、keepalive | 不採用 | サーバー向けの値で、512 MB の端末には大きすぎます。基底の defconfig では `TCP_CONG_BBR=m`、`NET_SCH_FQ=m` です。 |
| zswap | 不採用 | SD 上の swap が前提で、電源断への耐性と書き込み寿命に反します。使うなら zram にします（[電源断耐性・A/B 更新](power-and-updates.md)）。 |
| I/O スケジューラーを `none` にする | 実機で測る | 記事の対象は SSD 上の virtio-blk です。カーネルは単一キューのデバイスに `mq-deadline` を選びます（`elevator.c`）。SD 上の rootfs はほぼ読むだけなので、差は小さいと見ています。【推測】SquashFS の読み込みには `read_ahead_kb` のほうが効く可能性があります。【推測】 |
| `noatime`、`compress=zstd:1`（Btrfs） | 対応済み・対象外 | `/data` はすでに `noatime` で、rootfs は SquashFS です。Btrfs は使いません。 |
| SSH 強化（tcp_wrappers、鍵認証のみ、ed25519 のホスト鍵、待受アドレスの限定、レート制限） | 対象外 | SSH を実装しない方針です（[ユーザー空間・SSH/VPN 調査](userspace-and-security.md)）。将来、開発用イメージに SSH を入れる場合の確認項目として残します。 |
| unattended-upgrades とサービスの自動再起動 | 対象外 | 更新は `msd-update` による A/B 方式です。 |
| ufw、DNS over TLS、chrony | 対象外（今は） | 待ち受けるサービスがなく、ネットワーク機能を起動時に使っていません。Wi-Fi を使う段階で改めて検討します。 |
| Falco、Suricata | 不採用 | 512 MB の端末には重すぎます。 |
| Lynis | 候補 | QEMU 上で生成イメージを監査する用途に使えます。kernel-hardening-checker の結果と合わせて読みます。 |

## QEMU で取得した既定値

[2026-10-19-tunables-dump](../experiments/2026-10-19-tunables-dump.md) で、CI の成果物を QEMU（`raspi3b`）で起動し、通常の起動が終わった後の値を取得しました。sysctl 606 項目、ブロックデバイス 1,385 項目、モジュールパラメーター 395 項目などの全一覧は [調整項目の全一覧](tunables-defaults.md) にあります。QEMU の値は実機の値ではありません。

### sysctl の主な値

rootfs に sysctl の設定はないので、すべてカーネルの既定値です。記事の値と違うものを中心に挙げます。

| 項目 | 現在の値 | 記事の値 | MSD/Linux での判断 |
|---|---|---|---|
| `kernel.sysrq` | 502（`0x1f6`） | 0 | 0 は不可。絞るなら 32 |
| `kernel.panic` / `kernel.panic_on_oops` | 0 / 0 | 60 / 1 | 候補。watchdog と合わせて秒数を決める |
| `kernel.hung_task_timeout_secs` / `kernel.hung_task_panic` | 120 / 0 | なし | panic の方針と合わせて検討 |
| `kernel.kptr_restrict` / `kernel.dmesg_restrict` | 0 / 0 | 2 / 1 | 候補 |
| `kernel.yama.ptrace_scope` | 1 | 1 | 同じ。明示して固定する候補 |
| `kernel.unprivileged_bpf_disabled` | 2 | 1 | 2 は「無効だが root が 0 に戻せる」。1 は戻せない |
| `kernel.io_uring_disabled` | 0 | 2 | 候補 |
| `kernel.kexec_load_disabled` | 項目なし | 1 | kexec がカーネルにないため不要 |
| `kernel.perf_event_paranoid` | 2 | なし | 現状維持 |
| `kernel.randomize_va_space` | 2 | なし | 現状維持 |
| `kernel.printk` | `7 4 1 7` | なし | QEMU の cmdline の値。実機は `quiet` があるので異なる【未確認】 |
| `fs.protected_symlinks` / `protected_hardlinks` / `protected_fifos` / `protected_regular` | 0 / 0 / 0 / 0 | なし | 候補（1、1、1、2）。カーネルの既定は 0 で、一般のディストリビューションでは init が設定します。BusyBox の init は設定しません |
| `fs.suid_dumpable` / `kernel.core_pattern` | 0 / `core` | なし | 現状維持 |
| `dev.tty.ldisc_autoload` | 1 | なし | 候補（0） |
| `net.core.bpf_jit_harden` | 0 | なし | 候補（2）。BPF を Kconfig で外すなら不要 |
| `vm.swappiness` | 60 | 60 | swap がないので効果なし。zram を入れるときに決める |
| `vm.dirty_ratio` / `vm.dirty_background_ratio` | 20 / 10 | なし | `/data` の書き込みと電源断の観点で、実機で測る |
| `vm.dirty_expire_centisecs` / `vm.dirty_writeback_centisecs` | 3000 / 500 | なし | 同上 |
| `vm.page-cluster` | 3 | なし | zram を入れるなら 0 が候補 |
| `vm.min_free_kbytes` | 3,869（`mem=512M` で 2,791） | なし | 実機の RAM で決まる |
| `vm.overcommit_memory` / `vm.panic_on_oom` | 0 / 0 | なし | 現状維持 |
| `net.ipv4.conf.all.rp_filter` | 0 | 1 | 候補 |
| `net.ipv4.conf.all.accept_redirects` / `secure_redirects` / `send_redirects` | 1 / 1 / 1 | 0 / 0 / 0 | 候補 |
| `net.ipv4.conf.all.accept_source_route` | 0 | 0 | 同じ |
| `net.ipv4.conf.all.log_martians` | 0 | なし | 現状維持（ログが SD に増えるため） |
| `net.ipv4.tcp_syncookies` | 1 | 1 | 同じ |
| `net.ipv4.icmp_echo_ignore_broadcasts` / `icmp_ignore_bogus_error_responses` | 1 / 1 | 1 / 1 | 同じ |
| `net.ipv4.tcp_congestion_control` / `net.core.default_qdisc` | `cubic` / `pfifo_fast` | `bbr` / `fq` | 現状維持 |
| `net.core.rmem_max` / `wmem_max` | 4,194,304 / 4,194,304 | 8,388,608 / 8,388,608 | 現状維持 |
| `net.ipv4.tcp_max_syn_backlog` / `net.core.somaxconn` | 128 / 4,096 | 1,024 / 4,096 | 待ち受けがないので現状維持 |
| `net.ipv6.*` | 項目なし | 0 など | IPv6 はモジュール（`CONFIG_IPV6=m`）で、読み込まれていない |

`mem=512M` で起動すると、メモリー量から計算される 24 項目が小さくなりました（`fs.file-max` 86,624 → 41,792、`kernel.threads-max` 7,007 → 3,500、`net.ipv4.tcp_mem` の 3 値がほぼ半分など）。実機ではファームウェアの取り分を引いた RAM で決まるので、実機で取り直します。

### I/O スケジューラーとブロックデバイス

| 項目 | `mmcblk0` の値（QEMU） | 備考 |
|---|---|---|
| `queue/scheduler` | `none [mq-deadline] kyber bfq` | 4 方式が組み込み済み（`MQ_IOSCHED_DEADLINE`、`MQ_IOSCHED_KYBER`、`IOSCHED_BFQ` がすべて `=y`）。単一キューなので `mq-deadline` |
| `queue/iosched/*`（mq-deadline） | `read_expire` 500、`write_expire` 5000、`fifo_batch` 16、`writes_starved` 2、`front_merges` 1、`async_depth` 128、`prio_aging_expire` 10000 | |
| `queue/read_ahead_kb`、`bdi/read_ahead_kb` | 128 | SquashFS の読み込みで比べる候補 |
| `queue/nr_requests` | 128 | |
| `queue/max_sectors_kb` / `max_hw_sectors_kb` | 512 / 512 | |
| `queue/rotational` | 0 | 記事が明示している値。SD では既に 0 |
| `queue/add_random` | 0 | |
| `queue/rq_affinity` | 1 | |
| `queue/nomerges` | 0 | |
| `queue/write_cache` | `write through` | QEMU の SD の値。実機のカードでは確かめていない |
| `queue/discard_granularity` / `discard_max_bytes` | 4,194,304 / 4,194,304 | QEMU の SD の値 |
| `queue/io_timeout` | 60,000 | |
| `queue/iostats` | 1 | 0 にすると統計の負荷が減るが、測定に使うので現状維持 |

ブロックデバイスは `mmcblk0` のほかに `loop0`〜`loop7`（`max_loop` 8）と `ram0`〜`ram15`（`brd` の `rd_nr` 16、`rd_size` 4096）がありました。MSD/Linux の用途で `ram*` は使っていません【推測】。

SD 上の rootfs はほぼ読むだけなので、スケジューラーの差は小さいと見ています【推測】。比べるなら、起動時間と `/data` への書き込み中の読み込み遅延を、`mq-deadline`、`none`、`bfq` と `read_ahead_kb`（128、256、512）の組み合わせで実機で測ります。

## その他のチューニング要素

取得した値と Kconfig から、sysctl と I/O スケジューラー以外の要素を洗い出しました。どれも未実施で、効果は実機で測っていません。

| 分類 | 現状（QEMU で確認した値または Kconfig） | 検討の余地 | 検証 |
|---|---|---|---|
| CPU 周波数 | `cpufreq/parameters/default_governor` は `ondemand`。QEMU では `raspberrypi-cpufreq` の probe が失敗し、policy がない | `schedutil`、`performance`、起動中だけ `performance` | 実機のみ |
| CPU idle | `cpuidle/current_driver` は `none`、governor は `menu`。DT に `idle-states` がない | 待機時は WFI だけと見ています【推測】 | 実機で電流 |
| タイマー・プリエンプション | `CONFIG_HZ=250`、`NO_HZ_IDLE=y`、`PREEMPT=y` | `HZ=100` や `PREEMPT_VOLUNTARY` は起動時間と応答性の比較が必要 | QEMU：命令数 / 実機：時間 |
| workqueue | `workqueue/parameters/power_efficient` は `N` | `workqueue.power_efficient=1`（cmdline）で、待機中のコアを起こしにくくする | 実機で電流 |
| メモリー管理 | `lru_gen/enabled` は `0x0001`（MGLRU 有効）、swap なし、zswap は組み込みで `enabled=N`（compressor `lzo`） | zram を使うなら zswap は無効のまま。MGLRU の `min_ttl_ms` は 0 | QEMU・実機 |
| pstore / ramoops | `PSTORE_RAM=y` だが `ramoops/parameters/mem_size` は 0 で、領域がない | DT か cmdline で ramoops の領域を予約すると、panic の記録を再起動後に読める | QEMU：一部 / 実機 |
| watchdog | `watchdog/parameters/handle_boot_enabled` は `Y`、`open_timeout` 0 | `S01msd-watchdog`（`-T 15`）と panic の秒数を合わせる | 実機 |
| 温度 | thermal zone は `step_wise`、`trip_point_0` は 110°C（critical）。値は QEMU の DT と模擬値 | ファームウェアの減速（80〜85°C）とは別の仕組み。実機で両方を記録 | 実機のみ |
| USB | `usbcore/parameters/autosuspend` は 2 秒、`dwc_otg` の FIQ は有効 | 電力と USB 機器の応答の比較 | 実機 |
| カーネルの機能 | `bcm2711_defconfig` 由来で、CM0 にない機能が組み込みのまま：NVMe、PCIe（`PCIE_BRCMSTB`）、RP1、MACB、KVM、Android binder、NFS、`brd`、DRM、xHCI | S1（カーネルの削減）で外す候補。起動時間と RAM が減る可能性 | QEMU：サイズ・起動 / 実機：全周辺 |
| Kconfig の参照 | `IKCONFIG=m`（`/proc/config.gz` は `configs.ko` を読み込んだときだけ） | 実機での確認用に、`=y` にするか、ビルドの `.config` を成果物に含める（CI の成果物に `.config` が入っていなかった） | CI |
| ulimit | `core file size` 0、`max locked memory` 8,192 kB、`pending signals` 3,503 | 現状維持 | - |
| コンソール | 実機の cmdline に `quiet`、`console=tty1 console=serial0,115200` | `loglevel=` と printk の遅延が起動時間に与える影響（既存の PREEMPT / printk 比較と同じ） | QEMU・実機 |

## 出典

| 項目 | URL | 抜粋・該当箇所 | 確認度 |
|---|---|---|---|
| armctrl の ack と routing | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/irqchip/irq-bcm2835.c#L156-L173 | `.irq_ack = armctrl_ack_irq` → `bcm2836_arm_irqchip_spin_gpu_irq()` | 【一次】 |
| GPU 割り込みの送り先の切り替え | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/irqchip/irq-bcm2836.c#L92-L115 | `LOCAL_GPU_ROUTING` を `cpu_active()` の次のコアへ書き換え | 【一次】 |
| spin-table | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2837.dtsi#L49-L99 | `enable-method = "spin-table";` | 【一次】 |
| spin-table の操作 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/kernel/smp_spin_table.c#L122-L127 | `cpu_init`、`cpu_prepare`、`cpu_boot` のみ | 【一次】 |
| `arm_freq` の上書き | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710.dtsi#L18-L23 | `arm_freq = <&cpu0>, "clock-frequency:0", ... <&cpu3>` | 【一次】 |
| cpufreq ドライバー | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/cpufreq/raspberrypi-cpufreq.c#L40-L53 | ファームウェアのクロックから min/max を求め `cpufreq-dt` を登録 | 【一次】 |
| 基底の defconfig | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L64-L73 | `CPU_IDLE=y`、`CPU_FREQ_DEFAULT_GOV_ONDEMAND=y`、`ARM_RASPBERRYPI_CPUFREQ=y` | 【一次】 |
| SysRq の既定マスク | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1780 | `CONFIG_MAGIC_SYSRQ_DEFAULT_ENABLE=0x1f6` | 【一次】 |
| SysRq のマスク判定 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/tty/sysrq.c#L83-L88 | `sysrq_enabled == 1 \|\| (sysrq_enabled & mask)` | 【一次】 |
| remount の有効ビット | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/tty/sysrq.c#L200-L209 | `.enable_mask = SYSRQ_ENABLE_REMOUNT` | 【一次】 |
| `sysrq_on()` と `handle_sysrq()`、trigger | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/tty/sysrq.c#L640-L644<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/tty/sysrq.c#L1212-L1222 | `if (sysrq_on()) __handle_sysrq(key, true);` / `__handle_sysrq(c, false)` | 【一次】 |
| `SYSRQ_ENABLE_REMOUNT` | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/include/linux/sysrq.h#L27 | `0x0020` | 【一次】 |
| 電源断ドライバー | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L92-L93 | `handle_sysrq('u');` | 【一次】 |
| 既定の I/O スケジューラー | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/block/elevator.c#L743-L751 | “For single queue devices, default to using mq-deadline.” | 【一次】 |
| Buildroot の S02sysctl | https://github.com/buildroot/buildroot/blob/d6061d653d7fb215c2409c59e4bfad1b9d677215/package/busybox/busybox.mk#L348-L354<br>https://github.com/buildroot/buildroot/blob/d6061d653d7fb215c2409c59e4bfad1b9d677215/package/busybox/S02sysctl#L26 | procps-ng なしで `CONFIG_BB_SYSCTL=y` なら導入 / `SYSCTL_SOURCES="/etc/sysctl.d/ ..."` | 【一次】 |
| 周波数・減速の公式資料 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/overclocking.adoc | `arm_boost` の説明、既定値表（Pi Zero 2 W は `arm_freq` 1000、`arm_freq_min` 600）、80〜85°C の減速、4.63 V の低電圧 | 【一次】 |
| sysctl の説明（kernel、vm、fs、net） | https://docs.kernel.org/admin-guide/sysctl/index.html | 各項目の意味と既定値の説明 | 【一次】 |
| `fs.protected_*` | https://docs.kernel.org/admin-guide/sysctl/fs.html | `protected_fifos`、`protected_hardlinks`、`protected_regular`、`protected_symlinks` | 【一次】 |
| mq-deadline の調整項目 | https://docs.kernel.org/block/deadline-iosched.html | `read_expire`、`write_expire`、`fifo_batch`、`writes_starved`、`front_merges` | 【一次】 |
| QEMU で取得した値 | [2026-10-19-tunables-dump](../experiments/2026-10-19-tunables-dump.md) | CI 成果物（commit `ed426862`）を QEMU 6.2.0 で起動 | 【QEMU】 |
| VPS 運用記事 | https://qiita.com/uist1idrju3i/items/d45408d02e8c39526f5d | 「4. カーネルチューニング」の sysctl と ioscheduler、「3. SSH強化」、zswap、Btrfs のマウントオプション | 【一次】（記事の記述） |
