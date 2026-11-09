# 第1段の全構成対応パイロット

- 状態: 完了（QEMU、6構成の実行可能性確認）
- 日付: 2026-11-09
- 担当: Devin
- 関連: 第0段の実験記録

## 目的と仮説

20構成に対する第1段の全テストを実行できることを、6構成、6テスト、各1回の36 runで確かめる。特に、4 GiBのT7セットアップ、LUKSとdm-integrityを含むT6の破損位置、fscryptのワークロードrootを検証する。これは実行可否のパイロットであり、性能の結論には使わない。

## 採否の基準（結果を見る前に書く）

- 36のplan entryすべてで最終attemptのsummary statusが`ok`である。自動再試行を含む全attemptはCSVに残し、失敗attemptを成功値へ混ぜない。
- T6はL1=`wrong`、L3=`eio`、I2=`eio`となる。E5、F3、B5は結果を記録するが、事前に期待値を定めない。
- T7の各runに`mkfs_seconds`、`mount_seconds`、`fsck_seconds`、`setup_seconds`があり、メモリ値も正の数である。時間は0以上、4 GiBセットアップが120分以内に完了する。
- 条件を満たさない場合は失敗runを残し、結果を見て採否基準を変えない。

## 条件

| 項目 | 値 |
|---|---|
| 基準のcommit | `0686c699b3dd4c93a4d086eba88545a82285c623`。実行時のHEADは同commitで、guest/host scriptの変更を含むdirty tree |
| ホスト | 6 cores / 30 GB RAM |
| QEMU | 11.1.2。既存`output-fscmp`と`msd-dev`環境を再利用 |
| Buildroot / GCC / カーネル | Buildroot 2026.08.1、GCC 14.3.0、Linux `6.18.59-v8` |
| guest内ツール | cryptsetup / integritysetup 2.8.7、dmsetup library 1.02.205 / driver 4.50.0、btrfs-progs 6.10、mke2fs 1.47.4、f2fs-tools 1.16.0 |
| 変える条件 | E5、F3、B5、L1、L3、I2。各構成でT2、T3、T4-sync、T5、T6、T7を各1回 |
| 変えない条件 | 構成定義、テストの既定workload、matrix driver、QEMU環境 |
| 並列度とtimeout | `-j 4`。T2/T3の開始・回復markerは各900秒、T4-sync/T4-nosyncは3600秒、T7は7200秒 |
| 繰り返し | 各条件1回。実行可能性の確認のためで、性能の統計的比較には使わない |
| 入力とバイナリ | `output-fscmp`のBuildroot成果物を再利用した。`fs-compare.sh`がrunごとにbase rootfsを展開し、作業ツリーのguest scriptを配置して実験用rootfsを作るため、Buildrootの再ビルドは不要 |
| 初回と失敗の扱い | 全runを保存する。失敗は再試行・修正の有無とともに記録し、成功runと混ぜて成功扱いしない |

## 手順

```sh
OUTPUT_DIR=<Buildroot output directory>
QEMU_LOG_DIR=<persistent runs directory>
docker/msd-dev board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  -j 4 --matrix-id phase1-pilot --runs-dir "$QEMU_LOG_DIR" \
  "$QEMU_LOG_DIR/phase1-pilot-plan.tsv"
```

計画は6構成×6テスト、repetition 1の36行とする。driverは`host-load.txt`へ60秒ごとに`uptime`と`free -m`を記録する。

## 計測器と経路の検証

既存の第0段記録にある計測器検証を参照する。今回のパイロットでは、各T6の`T6_EXPECTED`、`T6_PLAINTEXT_CHANGE`、`T6_CORRUPTION_TARGET`、`T6_READCHECK`と、各T7のstep timerを確認した。

T6のext4/F2FSのblock位置は`filefrag -b4096`のblock番号に4096を掛けて求める。F2FSにも同じ直接map分岐を追加した。LUKS構成では`cryptsetup luksDump`のpayload offsetをraw位置へ加える。dm-integrity構成は`integritysetup dump`のtag size、sector size、data size、journal sections、interleave、flagsからsuperblock/journalとtag areaを計算した。カーネル文書は`Documentation/admin-guide/device-mapper/dm-integrity.rst`のjournalとdata/tag記述、target引数の`interleave_sectors`、journalのflush説明（同文書5-13、41-50、105-117、129-130行）に基づく。

```text
area = logical_sector / interleave_sectors
area_offset = logical_sector % interleave_sectors
raw_sector = base_sector + initial_sectors
           + area * (interleave_sectors + metadata_run_sectors)
           + metadata_run_sectors + area_offset
```

L3では`base_sector`にLUKS payload offsetを置く。B5ではBtrfs DUPの各physical offsetを復号済みmapper上で比較し、その後にpayload offset 16,777,216 bytesを加えてraw位置とする。B5のpilot logはmapper offsets `105906176:173015040`、raw offsets `122683392:189792256`、`plaintext_copies=match`を記録した。暗号化後のraw DUP copy同士は比較しない。E5/F3/B5/L1では破損後にplaintextが変化し、L3/I2ではintegrity検査で読み出し不能となった。全6構成でraw targetの変更を確認し、`T6_CORRUPTION_TARGET=verified`だった。

T2/T3はworkload markerを初回bootで待ち、回復bootでは`recovery_finished`を完了markerとして扱う。B5の回復bootにもLUKS stackをopenする。T4/T5のblock統計はmapper device nodeのmajor/minorから`/sys/dev/block/<major>:<minor>`のcanonical名を引く。最初の修正版ではguestの`stat` appletが使えず、mapper nodeの取得で失敗したため、BusyBox `ls -l`のblock major/minorを読む方法に変更した。I2のT4-syncは1500秒host timeoutでは最後のidle markerまで達しなかったので、T4 timeoutを3600秒へ延長した。T4-syncのI2最終runはwall 1636秒で完了し、`write_ios=7`、`write_sectors=32`、`last_write_s=4`だった。T4-nosyncのruntime pilotは実施していない。

## 結果

最初の`phase1-pilot`は36 plan rows、60 attemptsで、24 plan entriesが最終失敗した。修正後の`phase1-pilot-final`は36 plan rows、44 attemptsで、T4/T5のmapper aliasに起因する8 entriesが2回ずつ失敗した。`phase1-pilot-retest`では該当8 entriesを再実行し、7件が成功した。I2 T4-syncは1500秒timeoutで2回失敗し、timeoutを3600秒へ変更した`phase1-pilot-i2-t4-final`で成功した。各matrixのattemptは全てraw CSVに残した。最後に採用した36 plan entriesは全て`status=ok`である。

修正後の実行系列は2026-11-09 00:25:16 UTCから03:26:54 UTCまでで、経過wall timeは10,898秒（3時間1分38秒）。内訳は`phase1-pilot-final` 5,336秒、`phase1-pilot-retest` 3,854秒、I2 T4-sync最終確認1,636秒。60秒間隔で記録した1分load averageの最大値は5.87である。初回診断matrixは7,688秒、最大load 6.29だった。

最初の診断run（2026-11-08 22:10:15 UTC）から最終run完了（2026-11-09 03:26:54 UTC）までの総経過は18,999秒（5時間16分39秒）、matrix driver実行中のwall time合計は18,514秒である。全attempt中のhost-load最大値は6.29。

| 構成 | T6 `read_result` | `T6_EXPECTED` | `T7 mkfs_seconds` | `mount_seconds` | `fsck_seconds` | `setup_seconds` |
|---|---|---|---:|---:|---:|---:|
| E5 | wrong | not_defined | 2.826 | 1.947 | 2.665 | 0.106 |
| F3 | wrong | not_defined | 8.564 | 0.406 | 10.870 | 0.000 |
| B5 | ok | not_defined | 4.971 | 0.372 | 0.546 | 19.238 |
| L1 | wrong | wrong | 49.002 | 1.827 | 2.616 | 13.691 |
| L3 | eio | eio | 85.479 | 5.748 | 3.713 | 2802.011 |
| I2 | eio | eio | 44.415 | 3.009 | 4.210 | 2621.914 |

L1/L3/I2のT6 resultは事前期待と一致し、読み出しが原本のSHA-256のままなのにtarget plaintextが変化しない場合の`T6_corruption_not_applied`判定は発生しなかった。E5/F3/B5は期待結果を定義せず、実測値を記録した。T7は全構成でsetup chain、mount、fsck、stack closeまで完了し、setupは120分以内だった。

T2/T3、T4-sync、T5、T6、T7の36個の最終plan entryは成功した。T2/T3の回復marker、T4/T5のwrite statistics、T6の破損結果、T7のtimer summaryを確認した。全attemptを含む生CSVは[2026-11-09-phase1-pilot.csv](2026-11-09-phase1-pilot.csv)（114 attempts、38 columns）に保存した。各runのsummaryとQEMU logは下記matrix run directoryに保持する。

## 失敗attemptと経緯

- `phase1-pilot`: 24 plan entriesが最終失敗。T7のtimer capture、recovery marker、stack open、F2FS mapping、B5 DUP比較、marker timeoutの不具合を示した初回診断結果で、削除していない。
- `phase1-pilot-final`: 8 entries（B5/L1/L3/I2のT4-syncとT5）が2回ずつ`block_device_number_missing_path=/dev/mapper/...`で失敗した。guest `stat` appletに依存しないmajor/minor lookupへ変更した。
- `phase1-pilot-retest`: 7 entriesは成功。I2 T4-syncはホスト側timeout 1500秒でwall 1505-1506秒の`exit_1`となり、最後の`T4_SAMPLE`はelapsed 513/572秒で`T4_RESULT`を出していなかった。timeoutを3600秒に変更後、最終runはelapsed 600秒のsampleと`T4_RESULT`を記録して成功した。
- 初期の直接起動smoke 3件は、container内でhost絶対パスを`OUTPUT_DIR`に指定したため`Required file not found`でQEMU起動前に終了した。run directoryは保持し、pilot attempt CSVからは除外した。以降は`docker/msd-dev`の環境変数mappingと既存`output-fscmp`を使った。

## 結論

6構成のpilotではphase-1の対象テストが完走し、修正後の最終plan entryは36/36成功した。これは実行可能性の確認であり、性能の比較結論には使わない。phase-1の620-row matrixは実行していない。

## 未確認の点

このQEMU試験はSDカードのFTL、書き込みcache、実機の物理的な電源断を再現しない。

## ログ

全run directoryは`runs/phase1-pilot/`、`runs/phase1-pilot-final/`、`runs/phase1-pilot-retest/`、`runs/phase1-pilot-i2-t4-final/`とその子runとして保持する。60秒ごとのホスト負荷記録と各`matrix-summary.csv`も保持する。再現時は既存の`phase1-pilot-plan.tsv`を使い、変更後は新しいmatrix IDを指定する。
