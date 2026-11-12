# sysctlの既定値（IPv4以外のnetwork）

[調整項目の全一覧](tunables-defaults.md)から分割したQEMU取得値です。測定条件、生成元、実機との差、読み出しエラーの扱いは親の一覧を参照してください。製品の設定や採否を示すものではありません。

69 項目です。

| パス | 値（1 GiB） | 値（`mem=512M`） |
|---|---|---|
| `/proc/sys/net/core/bpf_jit_enable` | `1` | 同じ |
| `/proc/sys/net/core/bpf_jit_harden` | `0` | 同じ |
| `/proc/sys/net/core/bpf_jit_kallsyms` | `1` | 同じ |
| `/proc/sys/net/core/bpf_jit_limit` | `133676662784` | 同じ |
| `/proc/sys/net/core/busy_poll` | `0` | 同じ |
| `/proc/sys/net/core/busy_read` | `0` | 同じ |
| `/proc/sys/net/core/default_qdisc` | `pfifo_fast` | 同じ |
| `/proc/sys/net/core/dev_weight` | `64` | 同じ |
| `/proc/sys/net/core/dev_weight_rx_bias` | `1` | 同じ |
| `/proc/sys/net/core/dev_weight_tx_bias` | `1` | 同じ |
| `/proc/sys/net/core/devconf_inherit_init_net` | `0` | 同じ |
| `/proc/sys/net/core/fb_tunnels_only_for_init_net` | `0` | 同じ |
| `/proc/sys/net/core/flow_limit_cpu_bitmap` | `0` | 同じ |
| `/proc/sys/net/core/flow_limit_table_len` | `4096` | 同じ |
| `/proc/sys/net/core/gro_normal_batch` | `8` | 同じ |
| `/proc/sys/net/core/high_order_alloc_disable` | `0` | 同じ |
| `/proc/sys/net/core/max_skb_frags` | `17` | 同じ |
| `/proc/sys/net/core/mem_pcpu_rsv` | `256` | 同じ |
| `/proc/sys/net/core/message_burst` | `10` | 同じ |
| `/proc/sys/net/core/message_cost` | `5` | 同じ |
| `/proc/sys/net/core/netdev_budget` | `300` | 同じ |
| `/proc/sys/net/core/netdev_budget_usecs` | `8000` | 同じ |
| `/proc/sys/net/core/netdev_max_backlog` | `1000` | 同じ |
| `/proc/sys/net/core/netdev_rss_key` | `00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00` | 同じ |
| `/proc/sys/net/core/netdev_tstamp_prequeue` | `1` | 同じ |
| `/proc/sys/net/core/netdev_unregister_timeout_secs` | `10` | 同じ |
| `/proc/sys/net/core/optmem_max` | `131072` | 同じ |
| `/proc/sys/net/core/rmem_default` | `212992` | 同じ |
| `/proc/sys/net/core/rmem_max` | `4194304` | 同じ |
| `/proc/sys/net/core/rps_default_mask` | `0` | 同じ |
| `/proc/sys/net/core/rps_sock_flow_entries` | `0` | 同じ |
| `/proc/sys/net/core/skb_defer_max` | `64` | 同じ |
| `/proc/sys/net/core/somaxconn` | `4096` | 同じ |
| `/proc/sys/net/core/tstamp_allow_data` | `1` | 同じ |
| `/proc/sys/net/core/txrehash` | `1` | 同じ |
| `/proc/sys/net/core/warnings` | `0` | 同じ |
| `/proc/sys/net/core/wmem_default` | `212992` | 同じ |
| `/proc/sys/net/core/wmem_max` | `4194304` | 同じ |
| `/proc/sys/net/core/xfrm_acq_expires` | `30` | 同じ |
| `/proc/sys/net/core/xfrm_aevent_etime` | `10` | 同じ |
| `/proc/sys/net/core/xfrm_aevent_rseqth` | `2` | 同じ |
| `/proc/sys/net/core/xfrm_larval_drop` | `1` | 同じ |
| `/proc/sys/net/mptcp/add_addr_timeout` | `120` | 同じ |
| `/proc/sys/net/mptcp/allow_join_initial_addr_port` | `1` | 同じ |
| `/proc/sys/net/mptcp/available_path_managers` | `kernel userspace` | 同じ |
| `/proc/sys/net/mptcp/available_schedulers` | `default` | 同じ |
| `/proc/sys/net/mptcp/blackhole_timeout` | `3600` | 同じ |
| `/proc/sys/net/mptcp/checksum_enabled` | `0` | 同じ |
| `/proc/sys/net/mptcp/close_timeout` | `60` | 同じ |
| `/proc/sys/net/mptcp/enabled` | `1` | 同じ |
| `/proc/sys/net/mptcp/path_manager` | `kernel` | 同じ |
| `/proc/sys/net/mptcp/pm_type` | `0` | 同じ |
| `/proc/sys/net/mptcp/scheduler` | `default` | 同じ |
| `/proc/sys/net/mptcp/stale_loss_cnt` | `4` | 同じ |
| `/proc/sys/net/mptcp/syn_retrans_before_tcp_fallback` | `2` | 同じ |
| `/proc/sys/net/netfilter/nf_hooks_lwtunnel` | `0` | 同じ |
| `/proc/sys/net/netfilter/nf_log/0` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/1` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/10` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/2` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/3` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/4` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/5` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/6` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/7` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/8` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log/9` | `NONE` | 同じ |
| `/proc/sys/net/netfilter/nf_log_all_netns` | `0` | 同じ |
| `/proc/sys/net/unix/max_dgram_qlen` | `10` | 同じ |
