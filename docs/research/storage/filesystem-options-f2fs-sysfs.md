# F2FS sysfs optionと未操作時のwrite

[保存領域へ戻る](README.md) / [filesystem option調査](filesystem-options.md) / [F2FS formatとmount](filesystem-options-f2fs.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版はLinux 6.18.59の[`Documentation/ABI/testing/sysfs-fs-f2fs`](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/ABI/testing/sysfs-fs-f2fs)、最新版はmainline v7.4-rc1の同じ[ABI文書](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/ABI/testing/sysfs-fs-f2fs)です。sysfs attributeはmount中のruntime stateで、mount optionや永続設定と異なります。製品kernelでF2FSが有効か、値の変更後にCardputerZeroでどのwriteが発生するかは未確認です。

長時間のGC/recoveryはuser-initiatedでprogressを表示する。`gc_*`、discard、checkpoint/flush attributeをtimerで変更したり、idle writerを有効にしたりしない。read-only statisticsは診断値で、persistent storageへ記録する場合は圧縮RAMに置く。

## GC・discard・checkpoint・IPU

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `gc_idle` / `gc_mode` | idle GC policyとmodeを選ぶ | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | idle中GCによる未操作writeを避けたい要件と、空きsegment不足によるforeground latencyを実SDで計測して選ぶ。 |
| `gc_min_sleep_time` / `gc_max_sleep_time` / `gc_no_gc_sleep_time` / `gc_urgent_sleep_time` | GC threadとurgent GCのsleep間隔 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 値ごとのbackground write開始時刻、host write byte数、foreground pauseをblock traceで測り、無操作時間のwriteを許容できる値にする。 |
| `gc_urgent` / `gc_idle_interval` | urgent GCとidle判定時間 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | urgent modeは空き回復のためwriteを集中させる。boot後の未操作write量とfree-segment不足を測り、必要時のみ一時的に有効化する。 |
| `gc_boost_gc_greedy` / `gc_boost_gc_multiple` / `gc_valid_thresh_ratio` | GC選択・aggressive threshold | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | GCによる移動writeを増やす可能性がある。fill levelと長期random-write後の移動byte数、空きsegment、foreground latencyを測り改善する場合に調整する。 |
| `gc_pin_file_thresh` / `gc_segment_mode` / `max_victim_search` | pinned file閾値、segment mode、victim search範囲 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | GC対象と走査負荷を変えるため、pinned file数、victim search時間、移動block数を記録して効果がある場合だけ設定する。 |
| `gc_boost_zoned_gc_percent` / `gc_no_zoned_gc_percent` | zoned GCの利用率閾値 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | CardputerZeroのSDはhost-managed zoned deviceとして扱っていない。 |
| `discard_granularity` / `discard_idle_interval` | discard粒度、idle discardの開始間隔 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 未操作時間にdiscard commandを送る可能性があるため、command時刻・所要時間・error・後続write latencyを記録する。 |
| `discard_io_aware` / `discard_io_aware_gran` | I/O負荷を考慮したdiscard制御 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | foreground write中のdiscardを抑えられるか、SDのdiscard処理と遅延を同じworkloadで比較する。 |
| `discard_urgent_util` | urgent discard開始utilization | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | thresholdごとの未操作discard、空きblock回復、foreground latencyを測る。writeをユーザー操作時に限定する方針と競合する可能性がある。 |
| `max_discard_issue_time` / `mid_discard_issue_time` / `min_discard_issue_time` | 空き領域に応じたdiscard thread待ち時間 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | background discardの実行回数と時間帯、SD busy timeを記録し、未操作時のcommand発行を許容するか決める。 |
| `max_discard_request` / `max_ordered_discard` / `max_small_discards` | discard request数、ordered範囲、小discard量 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 最大値が増やすcommand数・I/O時間と、discard完了までの時間を計測してから調整する。 |
| `umount_discard_timeout` | unmount中にdiscardする時間上限 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 停止操作時の遅延とdiscard量を実測し、shutdown時間の制約がある場合に上限を変える。 |
| `ipu_policy` / `min_ipu_util` | in-place updateのpolicyとutilization条件 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 上書きwriteとout-of-place更新のhost write量、GC移動量、電断後のfsck結果を比べ、書込み増加の少ない方を選ぶ。 |
| `min_fsync_blocks` | fsync時のIPU条件となるdirty block数 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | fsync write数、latency、直後の電断後のdata状態を測り、fsync durabilityを保ったまま不要なsmall-writeを減らせるか確認する。 |
| `min_seq_blocks` / `min_hot_blocks` / `min_ssr_sections` | sequential/hot-data/SSR開始閾値 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | filesystem fill level、sequential write、SSR移動量を記録し、GCのbackground writeや空きspace消費が改善する場合だけ調整する。 |
| `cp_interval` | checkpoint間隔 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 定期checkpointは未操作時もmetadata writeを起こし得る。interval別のblock trace、dirty state量、強制電断後のrecovery時間を測り、write頻度と回復窓を比較する。 |
| `ckpt_thread_ioprio` | checkpoint merge daemonのI/O優先度 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | background checkpoint writeが利用者操作のlatencyへ与える影響をtraceし、priority変更が遅延を下げる場合だけ調整する。 |
| `migration_granularity` / `migration_window_granularity` | GC data migration単位とwindow | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | migration write burst、RAM、GC pauseを長期write試験で計測し、defaultより改善する場合だけ変更する。 |
| `atgc_enabled` / `atgc_candidate_count` / `atgc_candidate_ratio` / `atgc_age_threshold` / `atgc_age_weight` / `last_age_weight` | age-threshold GC有効化、候補数/比率/age/weight | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | age policyはGC timing・移動write・free-space分布を変える。代表的な`/data` workloadを長期実行し、短命/長命dataの移動量が減る場合だけ有効化する。 |
| `hot_data_age_threshold` / `warm_data_age_threshold` | hot/warm dataのage threshold | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | 実際の更新周期とGC移動量を記録し、age分離がSD write byte数を減らす場合だけ設定する。 |
| `min_ipu_util` / `min_fsync_blocks` / `min_hot_blocks` | IPU・fsync・hot data thresholds | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 重複項目は上記個別rowで扱う。 |

## 統計・fault injection・zoned device

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `stat/cp_status` / `stat/issued_discard` / `stat/queued_discard` / `stat/sb_status` / `stat/undiscard_blks` | checkpoint/discard/superblock状態のread-only統計 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | の表示項目。read-onlyであることを実機で確認し、write traceと併せて未操作時I/Oの原因診断に使う。統計値のresetや取得でdataを変更しない。 |
| `cp_background_calls` / `cp_foreground_calls` / `gc_background_calls` / `gc_foreground_calls` / `gc_reclaimed_segments` / `gc_remaining_trials` | checkpoint・GC呼出し、回収segment数 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | のread-only統計。起動直後と無操作時間後のcounter差を記録し、定期的なbackground writeが発生したかを確認する。 |
| `lifetime_write_kbytes` / `mounted_time_sec` / `avg_vblocks` / `dirty_segments` / `free_segments` / `ovp_segments` / `unusable` / `unusable_blocks_per_sec` | lifetime write、mount時間、segment・unusable block統計 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | のread-only統計。未操作期間のcounter差はwrite発生の手掛かりだが、partition外のSD controller内部write量を表すとは限らない。 |
| `committed_atomic_block` / `current_atomic_write` / `peak_atomic_write` / `revoked_atomic_block` / `current_reserved_blocks` / `reserved_blocks` / `reserved_segments` / `pending_discard` / `moved_blocks_background` / `moved_blocks_foreground` | atomic write、reservation、pending discard、移動blockの状態 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | の状態・counter。値の増減とblock traceを対照し、background処理のwrite量を分けて記録する。 |
| `dirty_nats_ratio` / `reclaim_segments` | dirty NAT ratioと回収segment数 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | のstate/counter。値の推移をGC/checkpoint write traceと照合し、無操作中のmetadata writeやfree-space回復が起きているか診断する。 |
| `inject_rate` / `inject_type` / `inject_timeout_type` / `fault_rate` / `fault_type` | fault種類、rate、timeoutを設定 | 未確認（資料でdefault未整理） | 可。`inject_timeout_type`は最新版のみ | 最新版で追加; 版上げで使える候補 | 除外 | 故障注入専用で通常の`/data`運用では使わない。最新版のみの`inject_timeout_type`は、版上げ時の試験候補としてのみ扱う。 |
| `allocate_section_hint` / `allocate_section_policy` / `blkzone_alloc_policy` / `carve_out` / `max_open_zones` / `pinned_area_max_secno` / `reserved_pin_section` / `gc_boost_zoned_gc_percent` / `gc_no_zoned_gc_percent` | zoned section allocation、open-zone上限、pinned area、zoned GC | 未確認（資料でdefault未整理） | 可。`max_open_zones` / `pinned_area_max_secno` / GC閾値は最新版のみ | 最新版で追加; 版上げで使える候補 | 除外 | zoned block device専用のgeometry/policyで、製品のSD cardには適用しない。最新版のみの項目は版上げ候補とするが、SDで有効化しない。 |

## その他のread-only状態とruntime tuning

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `main_blkaddr` / `features` / `feature_list` / `encoding` / `encoding_flags` | filesystem layout・feature・filename encodingを表示 | 未確認（資料でdefault未整理） | 可 | 同 | 除外 | format時に作ったfilesystemとの照合だけに使う。`encoding`設定はF2FS本体のfilename semanticsを変えるため導入しない。 |
| `iostat_enable` / `iostat_period_ms` | F2FS I/O統計を有効化し報告周期を指定 | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | ログを圧縮RAMへ出す場合でもCPU/RAM負荷があるため、計測時だけ有効化し、未操作時間のblock writeが増えないことをtraceする。 |
| `adjust_lock_priority` / `critical_task_priority` / `lock_duration_priority` | lock・critical taskのpriorityを調整 | 未確認（資料でdefault未整理） | 最新版のみ | 最新版で追加; 版上げで使える候補 | 実験で比べる | priority変更でGC/checkpoint threadが利用者操作を妨げるかを実機latencyとscheduler traceで比較する。 |
| `cache_wb_dirty_threshold` / `cache_wb_interval` / `cache_wb_total_threshold` | cache writeback thresholdとinterval | 未確認（資料でdefault未整理） | 最新版のみ | 最新版で追加; 版上げで使える候補 | 実験で比べる | writeback時刻と量を変えるため、未操作時のSD write trace、dirty RAM量、電断後の復旧窓を測ってから使う。 |
| `defrag_blocks` | defrag対象block量を指定 | 未確認（資料でdefault未整理） | 最新版のみ | 最新版で追加; 版上げで使える候補 | 実験で比べる | defragmentationはdata relocation writeを起こし得る。fragmentation、追加write byte数、read latencyが測定上改善する場合だけ明示的なmaintenanceで試す。 |
| `max_atc_write_bio_entry_cnt` / `max_atc_write_bio_size` / `max_lock_elapsed_time` | atomic write bio limit、lock elapsed time上限 | 未確認（資料でdefault未整理） | 最新版のみ | 最新版で追加; 版上げで使える候補 | 実験で比べる | 値ごとのRAM、bio merge、lock hold、write latencyを測り、SD write量または利用者応答に改善がある場合だけ調整する。 |
| `cache_wb_interval` / `cp_interval` / `idle_interval` / `gc_idle_interval` | writeback、checkpoint、system idle、GC interval | 未確認（資料でdefault未整理） | 可 | 最新版で追加; 版上げで使える候補 | 既定のまま | 各intervalが未操作時のwrite開始時刻へ与える影響をblock traceで記録し、ユーザー起点でないwriteを許せる時間窓を決めてから変更する。 |
| `bggc_io_aware` / `data_io_flag` / `node_io_flag` / `effective_lookup_mode` / `dir_level` / `extension_list` | background GCのI/O awareness、allocation flags、lookup・directory・extension設定 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | `/data`のdirectory構造、extension別更新頻度、GC pause、CPU使用量を測り、現行mount policyより効果がある場合だけ設定する。 |
| `compress_percent` / `compress_watermark` / `compr_new_inode` / `compr_saved_block` / `compr_written_block` | compression thresholdと圧縮inode/byte counter | 未確認（資料でdefault未整理） | 可 | 同 | 実験で比べる | RAM cacheだけでなく圧縮後のSD write byte、CPU時間、file内容別の保存量を測り、write削減がCPU負荷に見合う場合だけ有効化する。 |
| `max_fragment_chunk` / `max_fragment_hole` / `max_io_bytes` / `max_read_extent_count` / `max_roll_forward_node_blocks` | fragmentation, I/O batch, read extent, roll-forwardの上限 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | allocation shape、最大I/O、fsck/recovery時間とRAMを測り、既定値が実測上の制約になる場合だけ変更する。 |
| `ra_nid_pages` / `ram_thresh` / `readdir_ra` / `seq_file_ra_mul` | NID/directory/sequential readaheadとRAM threshold | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | compressed-RAM log/cacheを含むRAM予算、cold lookup latency、read byte数を比べ、SD readとRAMの両方が改善する場合だけ調整する。 |
| `reserved_pin_section` / `reserved_blocks` / `reserved_segments` / `carve_out` / `current_reserved_blocks` | reserve/pinned areaのblock・segment管理 | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | 予約領域は利用可能容量を減らすため、`msd-data-grow`後のfree space、GC結果、復旧時のreserve需要を計測する。 |
| `max_discard_issue_time` / `min_discard_issue_time` / `mid_discard_issue_time` / `umount_discard_timeout` | discard thread delay/timeout | 未確認（資料でdefault未整理） | 可 | 同 | 既定のまま | discard controlは上表で説明。未操作時writeを避けるpolicyでは、定期discardをいつ実行するかを先に決める。 |

固定版・最新版で共通のsysfs名は、実際に製品kernelが公開するとは限りません。最新版だけのattributeはこの表で「版上げで使える候補」とし、6.18.59で使えるとは扱いません。sysfs writeability、値の範囲、background activityの実機挙動は未確認です。
