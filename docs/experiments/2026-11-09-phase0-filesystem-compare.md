# Phase 0 filesystem comparison: T1 replay and instrument checks

- 状態: 完了（記載した条件でQEMU runを実施。実機検証ではない）
- 日付: 2026-11-08 - 2026-11-09
- 担当: Devin
- 関連: [filesystem比較の予備実験](2026-10-30-s4-fs-compare.md)
- 生の値: [phase-0結果CSV](2026-11-09-phase0-filesystem-compare.csv)

## 目的と仮説

「/dataは頻繁には書き換えないのでパフォーマンスを犠牲にしても良い」という前提を、ファイルシステム、暗号化、integrity stackの構成ごとに、耐久性、ユーザー起因でない書き込み、電源断時の損失・破損検出、書き込み量、メモリ、処理時間で検証するためのphase-0計測器を作り、QEMU上で制御条件とT1 replayを確認する。QEMU結果を実SDの特性へ一般化しない。

## 採否の基準

- T1-finalは選択されたfinal pointでmount、fsck、manifest、stack openの検査が通り、すべてのacknowledged fileが存在してhash一致すること。
- T1 mode=allは各flush/FUA pointを検査し、setupとworkloadの失敗を分ける。負の対照では意図した損失を検出する。
- 計測器の正負の対照が意図したread結果・書き込み数を記録する。失敗・中断runは成功runと混ぜない。
- 各構成は指定回数の測定値をそのまま報告する。1 runの比較から一般的な性能差や統計的同等性を主張しない。

## 条件

| 項目 | 値 |
|---|---|
| 基準commitと変更 | `8f659bf`をreview対象の基準とし、`6afb1cf`でincremental replay、dm-snapshot、T1 reduced workload、T2-T7計測とsummaryを導入。`1d3a7d4`でsetup-done markによるphase分類とpoint単位のerror出力、34列summaryを追加。`3c8fbc8`でstacked 20構成のreplay、fscrypt、F2FS dry-run fsck、snapshot overflowとsignal分類を追加。`83864e8`で非同期markの有界待機とF1 manifest境界を修正。 |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-43-generic、x86_64、6 core、30 GB RAM |
| Buildroot / GCC / kernel / QEMU | Buildroot 2026.08.1、GCC 14.3.0、Linux `6.18.59-v8`、QEMU emulator 11.1.2 |
| その他の実行ツール | mke2fs 1.47.4、btrfs-progs 6.10、f2fs-tools 1.16.0。QEMU binary SHA-256 `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`。 |
| T1固定条件 | 256 MiB test device、1 GiB sparse log-writes file、64 MiB snapshot COW。reduced workloadはW1=50 files、W2=25 updates、W3=250 appends (50件ごとにfsync)、W4=8 MiB。F1は`fsync_mode=posix`。 |
| 出力先 | 既存`output-fscmp`を再利用。`*-reconfigure`なし。各runは別run directoryとSD imageを使用。run ID、input hash、QEMU logは測定出力先に保存し、CSVにはhashを記録する。 |
| 反復 | 各T1-final、T1 mode=all、instrument checkは原則1 run。並列比較も1組のみ。性能の統計的結論には使わない。 |
| replay-log / workload | replay-log source commit `7b70d8a6863c5de30933d42a7672d35d01d2dc6c`、SHA-256 `e02779a201b41bf34897c3bc72daafa7e0b13dfc148bb91400599471ffae2750`。workload binary SHA-256 `5926b57671c9813808d41b4577bb968460ee1a5246da714f309917a3c7c8d08e`。 |

各段階のBuildroot logとSHA-256は以下のとおり。4段階とも`CONFIG_DM_SNAPSHOT=y`を確認した。

| 段階 | 保存先 | build.log SHA-256 |
|---|---|---|
| `6afb1cf` | `runs/phase0-review-build-after-T6-stat-1794153360/build.log` | `0074279d68c75e11ee724723dedf5ba5798ca42807e3a9091ba41d940b8bcb58` |
| `1d3a7d4` | `runs/phase0-review-build-setup-mark-retry-1794161154/build.log` | `2243eb1a66057a7ba4693525c39fe04abb2c104fc312718eeb7f02e4b0664d6c` |
| `3c8fbc8` | `runs/phase0-review-build-t1-stack-retry-1794163525/build.log` | `e5d5752d00e66d929b33e2cde2fd4a94f37296283bb18a8df4d5a75084ec6c45` |
| `83864e8` | `runs/phase0-review-build-t1-markers-1794170986/build.log` | `e6203f819e5e40c7d43a774baff35af7e5e6cea40e7ba0da8b4dea91ac8cef9d` |

## 計測器の検証

- 1 MiBのO_DIRECT controlはloop0で2048 sectors、backing partition `mmcblk0p7`で2072 sectorsを計数した。QEMU logは`phase0-control-T4-odirect-E1-1794133284`の354-357行。
- T4 idle E1ではmkfs後のquiesceに92秒かかり、quiesce中のloop0書き込みは8 I/O / 32,800 sectors。その後の60秒・61 sampleは0 I/O / 0 sectors。`phase0-review-T4-idle-control-E1-final-1794152324`のsummaryとQEMU log 368、559行。quiesceのlazy-init書き込みはidle baselineへ混ぜない。
- T6の検出対照: E1は意図した破損データを`wrong`と判定、B1は`eio`、B2はscrubが`corrected=1 uncorrectable=0`を記録し、両raw copyが原本と一致した。B2はscrub前後で修復を確認し、後続readcheckの修復と混同しない。
- T3 E1はconsoleの最終seq 28に対してdisk seq 20、loss 8 records / 8.234秒、`fsync_lost=0`。run `phase0-review-T3-E1-1794153622`のsummaryとQEMU log 401、753行。
- T1 negative control E1は1 loss pointを検出し、`T1_NEGATIVE_CONTROL loss_detected=yes`。`phase0-review-T1-negative-E1-1794153826`のsummaryとQEMU log 430行。これはcounter順序修正前のrunで、同log 428行の`T1_NEGATIVE_FINAL_CHECK`は`loss_points=0`を表示する。summaryと後続`T1_SUMMARY`は1である。

## T1のsetup phaseとreplay

T1は最終pointだけを見る`T1-final`と、全flush/FUA pointを見る`mode=all`を区別した。`T1-final`のsetup point数0は、選択したfinal pointがworkload phaseだったという意味で、candidate setup point全体の検査ではない。

par4b B2 run `phase0-par4b-T1-all-B2-1794166818`ではsetup-done entry 1296。以前mount/fsckに失敗したentry `1026, 1047, 1049, 1075, 1077, 1103, 1105, 1171, 1173, 1207, 1209, 1243, 1245, 1287, 1289, 1291`は、今回の全point logで`phase=setup`だった。16件すべてsetup mount/fsck失敗、workload phaseのmount/fsck失敗は0。最初の失敗はentry 1026のmount `Invalid argument`、fsckは`superblock magic doesn't match`が2行。詳細はrunの`qemu.log`に保持した。

### 見つかったharness bugと修正

1. **L3 setup markの非同期記録。** pinned kernel sourceの`drivers/md/dm-log-writes.c`で、`log_mark()`はmarkをqueueしてworkerを起こすが、記録完了を待たずに戻る。flush/FUA経路もpending log entryの書き込み完了を待たない。serial run `phase0-review-T1-final-L3-1794162416`とpar4b run `phase0-par4b-T1-all-L3-1794166818`はともに`t1_setup_done_mark_not_found`で失敗した。failed logではlog full/write failureの明示的kernel errorは見つからず、raw log scanのspanは1 GiBの16.4%と25.2%。古いfailed runはdm statusを記録していないため、当時の`logging_disabled` flagは未確認。

   `83864e8`で、dm statusのentry count進行と`replay-log --find --end-mark setup-done`を同時に待つ900秒上限のpollを追加した。新たな同時実行runではL3-Aが213秒、L3-Bが219秒待ってmarkを検出し、final checkも成功した。各runのstatus high-waterは336,048,128 / 342,449,152 bytesで、1 GiBの約31% / 32%。ログが小さすぎる証拠はなく、容量は増やしていない。上記の失敗runと成功runはすべて下のwall tableとCSVに残す。

2. **F1 manifest境界。** par4b F1は旧checkerでloss pointを2件報告した。focused diagnostic run `phase0-f1-pointdiag-F1-1794170560`ではentry 1048に`W1/file-000.dat`, marker entry 1049、entry 1481に`W3/append.log`, marker entry 1482の`T1_MANIFEST_FAIL`が出た。旧checkerの`manifest_limit=entry+1`がreplay pointより1つ先のmarkerをmanifest期待値へ含めていた。`83864e8`でlimitをentryへ修正。再run `phase0-f1-pointdiag-fixed-F1-1794172438`ではentry 1048が0 files、entry 1481が51 filesでいずれも`mount=yes fsck=0 manifest=yes`、`loss_points=0`。par4b full runでは次のflush point 1053が2 files、1487が52 filesでmanifest pass。よって2つの記録済みlossはchecker境界の誤りである。ただしworkload markerはfile fsyncとmanifest fsyncの後に出すため、markerはfsync完了時刻の上限であり、実際のfsync return瞬間の耐久性はこの測定だけでは確定しない。

## 結果: per-run wall_seconds

status、wall_seconds、T1のpoint結果をまとめる。詳細値とhashは同じ名前のCSVに記録した。`failed attempt`も除外せず載せた。

| run ID | 構成 / test | status | wall_seconds | 主な結果 |
|---|---|---:|---:|---|
| `phase0-review-smoke-E1-1794151739` | E1 smoke | ok | 69 | smoke完了 |
| `phase0-control-T4-odirect-E1-1794133284` | E1 T4 O_DIRECT | ok | 69 | loop0 2048、mmcblk0p7 2072 sectors |
| `phase0-review-T4-idle-control-E1-final-1794152324` | E1 T4 idle | ok | 264 | quiesce 92 s、idle 0 writes |
| `phase0-review-T5-E1-1794152599` | E1 T5 | ok | 295 | 1,247 I/O / 96,288 sectors |
| `phase0-review-T5-B2-1794152901` | B2 T5 | ok | 323 | 3,956 I/O / 225,144 sectors |
| `phase0-T6-E1-extentfix-1794135110` | E1 T6 | completed | 74 | `READCHECK result=wrong` |
| `phase0-review-T6-B1-1794153241` | B1 T6 | failed attempt | 81 | guest missing `stat` applet |
| `phase0-review-T6-B1-retry-1794153422` | B1 T6 | ok | 84 | `READCHECK result=eio` |
| `phase0-review-T6-B2-1794153523` | B2 T6 | ok | 90 | scrub corrected 1, uncorrectable 0 |
| `phase0-review-T3-E1-1794153622` | E1 T3 | ok | 162 | 8 records / 8.234 s |
| `phase0-review-T1-negative-E1-1794153826` | E1 T1 negative | ok | 198 | 1 loss point detected |
| `phase0-review-T1-all-E1-1794154038` | E1 T1 all, serial | ok | 3593 | 220 points, loss 0 |
| `phase0-review-T1-all-B2-1794157660` | B2 T1 all, serial | ok | 2865 | 242 points, loss 0 |
| `phase0-review-T1-final-E1-setupmark-1794161013` | E1 T1-final | failed attempt | 94 | setup mark not found |
| `phase0-review-T1-final-E1-setupmark-retry-1794161212` | E1 T1-final | ok | 335 | setup mark entry 105 |
| `phase0-review-T1-final-F1-1794162416` | F1 T1-final | ok | 163 | 53/53 files, final check pass |
| `phase0-review-T1-final-E5-1794162416` | E5 T1-final | ok | 243 | 53/53 files, final check pass |
| `phase0-review-T1-final-I2-1794162416` | I2 T1-final | ok | 1038 | 53/53 files, final check pass |
| `phase0-review-T1-final-L3-1794162416` | L3 T1-final | failed attempt | 433 | setup mark not found |
| `phase0-review-T1-final-L3-retry-1794163586` | L3 T1-final | ok | 1556 | setup mark 2628, final check pass |
| `phase0-review-T1-final-B5-1794165151` | B5 T1-final | ok | 452 | 53/53 files, final check pass |
| `phase0-review-T1-final-E1-1794165612` | E1 T1-final | ok | 343 | 53/53 files, final check pass |
| `phase0-review-T1-terminated-E1-1794165972` | E1 T1-final SIGTERM | failed attempt | 91 | signal sent to launcher; not the 60 s control |
| `phase0-review-T1-terminated-E1-1794166081` | E1 T1-final SIGTERM | expected failure | 61 | `fail:terminated_signal_15`, no guest `finished` |
| `phase0-par4b-T1-all-E1-1794166818` | E1 T1 all, parallel | ok | 2499 | 222 points, setup 5; setup mount/fsck 3/3 |
| `phase0-par4b-T1-all-B2-1794166818` | B2 T1 all, parallel | ok | 1539 | 240 points, setup 18; setup mount/fsck 16/16 |
| `phase0-par4b-T1-all-F1-1794166818` | F1 T1 all, parallel | ok | 1281 | 138 points; 2 old-boundary loss points |
| `phase0-par4b-T1-all-L3-1794166818` | L3 T1 all, parallel | failed attempt | 493 | setup mark not found; no T1 points |
| `phase0-f1-pointdiag-F1-1794170560` | F1 T1 sample, old boundary | completed with finding | 230 | points 1048/1481 both false loss |
| `phase0-final-T1-final-E1-1794171077` | E1 T1-final | ok | 248 | mark 105; final 53/53 pass |
| `phase0-final-T1-final-B2-1794171077` | B2 T1-final | ok | 233 | mark 1296; final 53/53 pass |
| `phase0-final-T1-final-L3-A-1794171077` | L3 T1-final | ok | 1307 | mark 2642; wait 213 s; final 53/53 pass |
| `phase0-final-T1-final-L3-B-1794171077` | L3 T1-final | ok | 1332 | mark 2643; wait 219 s; final 53/53 pass |
| `phase0-f1-pointdiag-fixed-F1-1794172438` | F1 T1 sample, corrected boundary | ok | 227 | points 1048/1481 pass, loss 0 |

T1 par4b E1/B2 wall timeは過去のserial runを下回ったが、1回ずつでpoint数とcommitも異なる。参考比はE1 `2499/3593=0.6955`、B2 `1539/2865=0.5372`に限る。性能差の一般化には使わない。par4bのE1/B2/F1は`83864e8`のF1 manifest fixより前の結果であり、F1の2 lossは旧境界による誤検出と確認した。

## 結論と未確認の点

B2の16 setup failuresはworkloadではなくsetup phaseにあった。L3 markが最大219秒遅れて見つかったため、短い固定待機では不足し、1 GiB logの容量不足も測定値には現れなかった。F1の2 loss pointはmanifest境界のchecker bugだった。T4、T6、T3、T1 negative controlはそれぞれの正負の計測器確認を通った。

T1 mode=allはE1、B2、F1が完走し、L3はsetup mark未検出で完走しなかった。**L3は有効な完走結果がなく、残る14構成のT1 mode=allは未実施**である。T1-finalのstack対応試験は6構成を対象にしたが、全20構成のT1-finalを網羅した結果でもない。

QEMUのSD imageは実SDのflash translation layer (FTL)、device write cache、物理的な電源断を再現しない。本記録から実SDの書き込み耐久性、性能、wear、電源断後のデータ保持を結論づけない。

## ログとraw data

raw CSVにはrunごとのwall_seconds、結果、summary値、既存のQEMU log/input hashと今回の診断runのhashを保持する。大きなQEMU log、SD image、Buildroot出力は測定出力先に保持し、リポジトリには含めない。各run IDで保存物を識別できる。
