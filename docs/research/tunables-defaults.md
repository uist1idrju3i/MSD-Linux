# 調整項目の全一覧（QEMU で取得した既定値）

この文書は [2026-10-19-tunables-dump](../experiments/2026-10-19-tunables-dump.md) の生の値から `board/cardputerzero/tools/bench/tuning/make-tables.py` で作った一覧です。手で編集せず、再生成してください。項目ごとの意味と判断は [CPU・割り込み・sysctl の調整余地](cpu-irq-and-sysctl.md) にまとめました。

- 対象：main の commit `ed42686237581a286b30c132991a58d950267221` の CI 成果物（`msd-cardputerzero-build`）。カーネルは 6.18.57-v8 です。
- 環境：QEMU 6.2.0 の `-M raspi3b`（RAM 1 GiB）で A スロットから起動しました。「`mem=512M`」の列は、cmdline に `mem=512M` を足して起動した値です。CM0 実機の RAM は 512 MB からファームウェアの取り分を引いた量なので、実機の値はさらに小さくなる可能性があります。
- 値は通常の起動（`S02sysctl` を含むすべての init スクリプト）が終わった後のものです。rootfs に `/etc/sysctl.d/` の設定はないため、sysctl の値はカーネルの既定値です。
- QEMU の値は実機の値ではありません。特に、メモリー量で決まる値、ブロックデバイス（QEMU の SD）の値、cpufreq（QEMU ではドライバーが probe に失敗します）、温度は実機と異なります。
- 実行時に変わる値（`random/uuid`、`file-nr`、`dentry-state` など）も、取得した時点の値をそのまま載せています。
- 書き込み専用の項目（`vm/drop_caches`、`vm/compact_memory`、`net/ipv4/route/flush`）は、値の欄が読み出しのエラーです。イメージに `stat` がないため、権限は取得していません。
- IPv6 はモジュール（`CONFIG_IPV6=m`）で、この起動では読み込まれていないため、`net/ipv6` の項目はありません。

## sysctl（`/proc/sys`）

詳しくは [tunables-sysctl.md](tunables-sysctl.md) を参照してください。

## ブロックデバイス `mmcblk0`（queue、iosched、bdi）

65 項目です。

| パス | 値（1 GiB） | 値（`mem=512M`） |
|---|---|---|
| `/sys/block/mmcblk0/bdi/max_bytes` | `180961280` | `89714688` |
| `/sys/block/mmcblk0/bdi/max_ratio` | `100` | 同じ |
| `/sys/block/mmcblk0/bdi/max_ratio_fine` | `1000000` | 同じ |
| `/sys/block/mmcblk0/bdi/min_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/bdi/min_ratio` | `0` | 同じ |
| `/sys/block/mmcblk0/bdi/min_ratio_fine` | `0` | 同じ |
| `/sys/block/mmcblk0/bdi/read_ahead_kb` | `128` | 同じ |
| `/sys/block/mmcblk0/bdi/stable_pages_required` | `0` | 同じ |
| `/sys/block/mmcblk0/bdi/strict_limit` | `0` | 同じ |
| `/sys/block/mmcblk0/bdi/uevent` | （空） | 同じ |
| `/sys/block/mmcblk0/queue/add_random` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/atomic_write_boundary_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/atomic_write_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/atomic_write_unit_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/atomic_write_unit_min_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/chunk_sectors` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/dax` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/discard_granularity` | `4194304` | 同じ |
| `/sys/block/mmcblk0/queue/discard_max_bytes` | `4194304` | 同じ |
| `/sys/block/mmcblk0/queue/discard_max_hw_bytes` | `4194304` | 同じ |
| `/sys/block/mmcblk0/queue/discard_zeroes_data` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/dma_alignment` | `511` | 同じ |
| `/sys/block/mmcblk0/queue/fua` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/hw_sector_size` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/io_poll` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/io_poll_delay` | `-1` | 同じ |
| `/sys/block/mmcblk0/queue/io_timeout` | `60000` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/async_depth` | `128` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/fifo_batch` | `16` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/front_merges` | `1` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/prio_aging_expire` | `10000` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/read_expire` | `500` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/write_expire` | `5000` | 同じ |
| `/sys/block/mmcblk0/queue/iosched/writes_starved` | `2` | 同じ |
| `/sys/block/mmcblk0/queue/iostats` | `1` | 同じ |
| `/sys/block/mmcblk0/queue/iostats_passthrough` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/logical_block_size` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/max_discard_segments` | `1` | 同じ |
| `/sys/block/mmcblk0/queue/max_hw_sectors_kb` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/max_integrity_segments` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/max_sectors_kb` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/max_segment_size` | `524288` | 同じ |
| `/sys/block/mmcblk0/queue/max_segments` | `128` | 同じ |
| `/sys/block/mmcblk0/queue/max_write_streams` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/minimum_io_size` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/nomerges` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/nr_requests` | `128` | 同じ |
| `/sys/block/mmcblk0/queue/nr_zones` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/optimal_io_size` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/physical_block_size` | `512` | 同じ |
| `/sys/block/mmcblk0/queue/read_ahead_kb` | `128` | 同じ |
| `/sys/block/mmcblk0/queue/rotational` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/rq_affinity` | `1` | 同じ |
| `/sys/block/mmcblk0/queue/scheduler` | `none [mq-deadline] kyber bfq` | 同じ |
| `/sys/block/mmcblk0/queue/stable_writes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/virt_boundary_mask` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/write_cache` | `write through` | 同じ |
| `/sys/block/mmcblk0/queue/write_same_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/write_stream_granularity` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/write_zeroes_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/write_zeroes_unmap_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/write_zeroes_unmap_max_hw_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/zone_append_max_bytes` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/zone_write_granularity` | `0` | 同じ |
| `/sys/block/mmcblk0/queue/zoned` | `none` | 同じ |

## CPU（cpuidle、脆弱性対策の状態）

27 項目です。

| パス | 値（1 GiB） | 値（`mem=512M`） |
|---|---|---|
| `/sys/devices/system/cpu/cpuidle/available_governors` | `menu` | 同じ |
| `/sys/devices/system/cpu/cpuidle/current_driver` | `none` | 同じ |
| `/sys/devices/system/cpu/cpuidle/current_governor` | `menu` | 同じ |
| `/sys/devices/system/cpu/cpuidle/current_governor_ro` | `menu` | 同じ |
| `/sys/devices/system/cpu/online` | `0-3` | 同じ |
| `/sys/devices/system/cpu/possible` | `0-3` | 同じ |
| `/sys/devices/system/cpu/smt/active` | `0` | 同じ |
| `/sys/devices/system/cpu/smt/control` | `-1` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/gather_data_sampling` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/ghostwrite` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/indirect_target_selection` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/itlb_multihit` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/l1tf` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/mds` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/meltdown` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/mmio_stale_data` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/old_microcode` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/reg_file_data_sampling` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/retbleed` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/spec_rstack_overflow` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/spec_store_bypass` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/spectre_v1` | `Mitigation: __user pointer sanitization` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/spectre_v2` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/srbds` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/tsa` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/tsx_async_abort` | `Not affected` | 同じ |
| `/sys/devices/system/cpu/vulnerabilities/vmscape` | `Not affected` | 同じ |

## sysfs（mm、power、thermal）

25 項目です。

| パス | 値（1 GiB） | 値（`mem=512M`） |
|---|---|---|
| `/sys/class/thermal/thermal_zone0/available_policies` | `step_wise` | 同じ |
| `/sys/class/thermal/thermal_zone0/integral_cutoff` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/k_d` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/k_i` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/k_po` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/k_pu` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/mode` | `enabled` | 同じ |
| `/sys/class/thermal/thermal_zone0/offset` | `412000` | 同じ |
| `/sys/class/thermal/thermal_zone0/policy` | `step_wise` | 同じ |
| `/sys/class/thermal/thermal_zone0/slope` | `-538` | 同じ |
| `/sys/class/thermal/thermal_zone0/sustainable_power` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/temp` | `25178` | 同じ |
| `/sys/class/thermal/thermal_zone0/trip_point_0_hyst` | `0` | 同じ |
| `/sys/class/thermal/thermal_zone0/trip_point_0_temp` | `110000` | 同じ |
| `/sys/class/thermal/thermal_zone0/trip_point_0_type` | `critical` | 同じ |
| `/sys/class/thermal/thermal_zone0/type` | `cpu-thermal` | 同じ |
| `/sys/class/thermal/thermal_zone0/uevent` | （空） | 同じ |
| `/sys/kernel/mm/lru_gen/enabled` | `0x0001` | 同じ |
| `/sys/kernel/mm/lru_gen/min_ttl_ms` | `0` | 同じ |
| `/sys/kernel/mm/mempolicy/weighted_interleave/__auto_type` | `true` | 同じ |
| `/sys/kernel/mm/mempolicy/weighted_interleave/node0` | `1` | 同じ |
| `/sys/kernel/mm/numa/demotion_enabled` | `false` | 同じ |
| `/sys/kernel/mm/swap/vma_ra_enabled` | `true` | 同じ |
| `/sys/power/pm_freeze_timeout` | `20000` | 同じ |
| `/sys/power/state` | （空） | 同じ |

## モジュールパラメーター（`/sys/module/*/parameters`）

詳しくは [tunables-module-params.md](tunables-module-params.md) を参照してください。
