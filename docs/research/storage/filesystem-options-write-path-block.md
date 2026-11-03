# block layerのqueueとscheduler設定

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 範囲と出典

固定Linux 6.18.59とmainline 7.4-rc1の`Documentation/ABI/stable/sysfs-block`、deadline・BFQ・Kyber scheduler文書、およびscheduler/WBTのKconfigを対象にします。ABIにあるqueue以外の属性も含めています。製品の最終kernel `.config`は生成していないためschedulerの組み込み状態は未確認です。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
|---|---|---|---|---|---|---|
| `scheduler` `MQ_IOSCHED_DEADLINE` `MQ_IOSCHED_KYBER` `IOSCHED_BFQ` | block I/O scheduler選択とscheduler build option | kernel/config/driver依存 | sourceにあり。最終`.config`未確認 | `async_depth`等を追加 | 実験で比べる | SD queueでread/write latencyとflush orderingを測る。fragmentだけでbuilt-inを断定しない。 |
| `read_expire` `write_expire` `fifo_batch` `writes_starved` `front_merges` | deadline schedulerのread/write期限とdispatch batching | scheduler既定値 | 可 | 同 | 実験で比べる | journal、fsync、長いwriteの待ち時間をuser-requested workloadで測る。 |
| `slice_idle` `slice_idle_us` `low_latency` `max_budget` `strict_guarantees` `timeout_sync` `async_depth` `read_lat_nsec` `write_lat_nsec` `zoned_qd1_writes` `back_seek_max` `back_seek_penalty` `fifo_expire_async` `fifo_expire_sync` | BFQ/Kyber/deadline等のqueue budget、latency、seekとasync dispatch | scheduler/driver依存 | 可 | `async_depth`,`zoned_qd1_writes`等は最新版差分 | 実験で比べる | SDでのscheduler latencyとidle期間の追加write有無を同時に記録する。 |
| `BLK_WBT` `BLK_WBT_MQ` `wbt_lat_usec` | writeback throttlingのbuild optionとlatency target | kernel/config/queue依存 | sourceにあり。最終`.config`未確認 | 同 | 実験で比べる | dirty writebackがforeground readを妨げる条件を測る。WBTの有効化だけでno-idle-writeを保証しない。 |
| `write_cache` `stable_writes` `fua` `discard_zeroes_data` | cache flush、stable write、FUA、discardのdevice特性 | device driverが報告 | 可 | 同 | 実験で比べる | `write_cache`の報告が正しいこと、flush/FUAが暗号化・filesystem層を通過することをdevice traceと電断試験で確認する。 |
| `discard_granularity` `discard_max_bytes` `discard_max_hw_bytes` `max_discard_segments` `discard_alignment` `alignment_offset` | discard範囲・alignment | device依存 | 可 | 同 | 実験で比べる | discardはfree-spaceを漏らし、idle中のSD commandにもなり得る。発行時機、量、回収効果を測定する。 |
| `logical_block_size` `physical_block_size` `hw_sector_size` `minimum_io_size` `optimal_io_size` `max_hw_sectors_kb` `max_sectors_kb` `max_segment_size` `max_segments` `nr_requests` `chunk_sectors` `dma_alignment` `max_write_streams` `write_stream_granularity` `max_integrity_segments` | block size、request上限、streamとintegrity segment特性 | device/host driver依存 | 可 | 同 | 既定のまま | controller/cardの報告を尊重し、値を固定してalignmentやdurabilityを壊さない。 |
| `add_random` `dax` `io_poll` `io_poll_delay` `io_timeout` `iostats` `iostats_passthrough` `nomerges` `rq_affinity` `read_ahead_kb` `rotational` `inflight` `stat` `virt_boundary_mask` | queue性能、統計、pollingとdevice property | driver/kernel依存 | 可 | 同 | 既定のまま | 計測・scheduler制御・device特性であり、write durabilityを直接保証しない。統計採取中もlogはRAMに置く。 |
| `hw_wrapped_keys` `max_dun_bits` `num_keyslots` `raw_keys` | block inline encryption capability | hardware/driver依存 | 可 | 同 | 既定のまま | 暗号化はdm-crypt方針を既定とし、SD hostのinline crypto対応は実機で未確認。 |
| `max_active_zones` `max_open_zones` `nr_zones` `zone_append_max_bytes` `zone_write_granularity` `zoned` `write_zeroes_max_bytes` `write_zeroes_unmap_max_bytes` `write_zeroes_unmap_max_hw_bytes` `write_same_max_bytes` | zoned device、zero/write-same capability | device/driver依存 | 可 | 同 | 既定のまま | 対象SDのzoned capabilityは未確認。必要性を実機調査せずにzone commandを発行しない。 |
| `BLK_WBT` `BLK_WBT_MQ` `MQ_IOSCHED_DEADLINE` `MQ_IOSCHED_KYBER` `IOSCHED_BFQ` | kernel Kconfigでscheduler/throttling機能を選ぶ | 未確認 | 最終`.config`未確認 | 同 | 既定のまま | `linux.fragment`は完全解決後の`.config`ではない。最終config生成時に設定と依存関係を確かめる。 |

`queue/write_cache`はSDの実際のvolatile cache有無を示すものとは限らず、kernel driverの報告値です。安全性は電源断を含む実機試験で確認します。

## 出典

- [固定版 sysfs-block ABI](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/ABI/stable/sysfs-block)
- [固定版 deadline](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/block/deadline-iosched.rst)、[BFQ](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/block/bfq-iosched.rst)、[Kyber](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/block/kyber-iosched.rst)
- [Linux v7.4-rc1 block ABI](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/ABI/stable/sysfs-block?h=v7.4-rc1)、[block scheduler docs](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/block?h=v7.4-rc1)
