# VM writebackとBDIの設定項目

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 範囲と出典

Linux固定版6.18.59とmainline 7.4-rc1の`Documentation/admin-guide/sysctl/vm.rst`に載る全`/proc/sys/vm`項目、および`Documentation/ABI/testing/sysfs-class-bdi`の属性を列挙します。memory管理のみの項目も省かず、writebackと無関係な理由を記します。個別値はkernel config・RAM量・workloadで変わります。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
|---|---|---|---|---|---|---|
| `vm.dirty_background_bytes` `vm.dirty_background_ratio` `vm.dirty_bytes` `vm.dirty_ratio` | background flusher開始量とdirty memory上限 | kernel/RAM依存。bytesとratioは片方 | 可 | 同 | 実験で比べる | writeback開始時刻を左右し、無操作時のSD write規則に直結する。比率とbytesの双方を同じRAM条件で記録する。 |
| `vm.dirty_expire_centisecs` `vm.dirty_writeback_centisecs` `vm.laptop_mode` | dirty data期限とflusher周期、laptop mode | kernel既定 | 可 | 同 | 実験で比べる | 短いtimerは利用者操作後のdirty dataを無操作時間中に書く可能性がある。SD traceで実際の時機を測る。 |
| `vm.dirtytime_expire_seconds` | dirty timestampの期限 | kernel既定 | 可 | 同 | 実験で比べる | lazytimeと組み合わさるmetadata writeを測り、idle writeを起こさない期限を選ぶ。 |
| `vm.admin_reserve_kbytes` `vm.user_reserve_kbytes` `vm.lowmem_reserve_ratio` `vm.min_free_kbytes` `vm.min_slab_ratio` `vm.min_unmapped_ratio` `vm.percpu_pagelist_high_fraction` | reserve、watermark、slab、per-CPU page list | kernel/RAM依存 | 可 | 同 | 既定のまま | VMの安全余裕を維持する項目で、filesystem write policyの代わりに調整しない。 |
| `vm.compact_memory` `vm.compact_unevictable_allowed` `vm.compaction_proactiveness` `vm.defrag_mode` `vm.extfrag_threshold` `vm.watermark_boost_factor` `vm.watermark_scale_factor` | memory compactionとfragmentation制御 | kernel/config依存 | 可 | 同 | 既定のまま | CPU latencyやlarge allocationに関する項目で、SDへのwrite許可条件とは別である。 |
| `vm.drop_caches` `vm.enable_soft_offline` `vm.memory_failure_early_kill` `vm.memory_failure_recovery` `vm.oom_dump_tasks` `vm.oom_kill_allocating_task` `vm.panic_on_oom` `vm.panic_on_unrecoverable_memory_failure` `vm.page_lock_unfairness` `vm.nr_trim_pages` `vm.stat_interval` `vm.stat_refresh` `vm.swappiness` `vm.zone_reclaim_mode` | cache破棄、memory failure、OOM、統計、reclaim | kernel/config依存 | 可 | 同 | 既定のまま | filesystemのdata耐久性を高める項目ではない。cache破棄やOOM動作による副作用を避ける。 |
| `vm.hugetlb_shm_group` `vm.legacy_va_layout` `vm.max_map_count` `vm.mmap_min_addr` `vm.mmap_rnd_bits` `vm.mmap_rnd_compat_bits` `vm.unprivileged_userfaultfd` | mmap、address space、hugetlbのpolicy | kernel/architecture依存 | 可 | 同 | 既定のまま | process memory・security policyであり、SD writebackの対象ではない。 |
| `vm.nr_hugepages` `vm.nr_hugepages_mempolicy` `vm.nr_overcommit_hugepages` `vm.overcommit_kbytes` `vm.overcommit_memory` `vm.overcommit_ratio` `vm.page-cluster` `vm.numa_stat` `vm.numa_zonelist_order` `vm.highmem_is_dirtyable` `vm.mem_profiling` `vm.movable_gigantic_pages` | huge page、overcommit、NUMA等のmemory配置 | kernel/config依存 | 固定版可。最新版のみの項目は最新版のみ | `movable_gigantic_pages`等を含む | 既定のまま | `/data`のwrite時機に直接関係しない。最新版だけの項目はkernel更新後にmemory試験で再確認する。 |
| `bdi/read_ahead_kb` | BDIのread-ahead量 | device/driver依存 | 可 | 同 | 実験で比べる | read-aheadとcache圧力を測る。write抑制の根拠にはせず、read workload中のwritebackをtraceする。 |
| `bdi/min_ratio` `bdi/min_ratio_fine` `bdi/max_ratio` `bdi/max_ratio_fine` `bdi/min_bytes` `bdi/max_bytes` `bdi/strict_limit` `bdi/stable_pages_required` `vm.vfs_cache_pressure` `vm.vfs_cache_pressure_denom` | backing deviceのdirty memory制御とVFS cache reclaim | device/kernel依存 | 可 | 同 | 実験で比べる | BDI単位でwritebackを制御する。SDへの個別上限を設定する場合もidle writeが出ないこととdata durabilityを実測する。VFS cache pressureはwriteback設定と混同しない。 |

memory管理だけの項目も除外せず記載しました。最新版で新規となるsysctlの有効性は最終kernel `.config`で未確認です。

## 出典

- [固定版 vm.rst](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/sysctl/vm.rst)、[sysfs-class-bdi](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/ABI/testing/sysfs-class-bdi)
- [Linux v7.4-rc1 vm.rst](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/admin-guide/sysctl/vm.rst?h=v7.4-rc1)、[sysfs-class-bdi](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/ABI/testing/sysfs-class-bdi?h=v7.4-rc1)
