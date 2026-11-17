# /data grow後のidle残量の帰属

- 状態: 測定完了。88 sectorを全て分類、修正は未実施
- 日付: 2026-11-17
- 担当: Devin
- 関連: [同期初期化の測定](2026-11-17-data-sync-itable.md)、[書き込み台帳](../design/write-policy.md)

## 目的と仮説

同期初期化後の最初の120秒idleに残った88 sectorを、guestのjbd2統計・ext4 lifetime値とblock offsetで帰属します。仮説はgrow・mkdirで汚れたmetadataの遅延writebackです。superblockの定期更新、atime、userspace等も検査し、到達経路を確かめない原因は断定しません。製品コードを変更せず、修正候補は記述にとどめます。

## 採否の基準（測定前）

同一入力を5回測定し、各回のidle1全sectorをoffsetの領域分類とguest counterの差分で説明できた場合に限り帰属を確定します。説明できないsectorを残余として表示します。RAM対照はp7 0、disk正対照は2,048 sector以上を要件とします。idle2も120秒観測します。速度の優劣は判定しません。

## 条件と手順

基準はmainの`72c51cc31e73832e76cb8c9574e2e9c06c6bcf02`です。前回の`output-data-sync-itable/input-after`とwarm treeの`output-openssl-lts`を使い、再buildしません。製品のmount/grow関連sourceが基準と一致すること、binary hashが前回と一致することを照合します。製品imageにはhookを入れず、serial経由でRAMへ転送します。

固定kernelは`CONFIG_FTRACE`無効です。代わりにQEMUの`blk_co_pwritev`でoffsetを取り、guestの`/proc/fs/jbd2/mmcblk0p7-8/info`、ext4 lifetime/session値、p7 statを観測します。元runnerのRAM/disk対照を保持し、idleでは1秒ごとのcounter読取りだけを加えます。

| 項目 | 値 |
|---|---|
| ホスト / container | Linux 7.0.0-43-generic x86_64 / Debian 13 |
| 開発image ID | `47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d` |
| QEMU | 11.1.2、raspi3ap、512 MiB、icountなし。binary hashはserialの`run-qemu: sha256` |
| guest kernel | 6.18.59-v8、source `b3495ea401d709af0701a85babcba5e3d788a602` |
| Buildroot / GCC | 2026.08.1 / Bootlin GCC 14.3.0で前回buildしたimage。今回はcompilerを使用しない |
| debugfs / dumpe2fs | 既存treeのe2fsprogs 1.47.4 |
| 構築状態 | warm treeを再利用。再build・reconfigureなし。ccache未使用 |
| SD / p7 | 未拡張SDをrunごとにcopyして1 GiBへ。p7開始1,376,256 sector、grow後720,896 sector、block 4 KiB |
| 主測定 | trace-r2〜r6を逐次実行、各120秒sleepを2窓 |
| 対照 | grown-r1を1回。pilot終了imageをcopyして再起動し、grow・mkdir済みの状態を観測。性能比較には使わない |
| 固定条件 | 製品rootfs、kernel、DTB、元SD、mount option、serial転送、RAM/disk対照 |

基準から製品sourceを変えていません。mainと旧基準`f132f3c`の製品差分はS02とfstabの2ファイルだけで、image内のS02・fstab・msd-data-growを現行sourceと`cmp`しました。表示versionは前回buildの`f132f3c-dirty`のままです。mainから再buildしたimageとは呼びません。

| 入力 | SHA-256 |
|---|---|
| Image | `c651cfd86fcb08943a863ecbc31f6fa0f2f6fea0f7c7bcd25fc8e3cdd327c261` |
| rootfs | `b6d0c1dab4f94631771580f6f1f5e6d8b16449ab3f12afc0e1c4637a4e4b9ab2` |
| 元SD | `55b2b3e01af1a37bf6e40f8213ac782ebdd0c9fca6c32b8ae472f88a8f03e541` |
| Buildroot .config | `7ba1421598d13671f0087b4ef80caa103509585a32a9cbf1ae131036393621bf` |
| kernel .config | `6b8b92ae3168a28faa9bf8570881244a8c1bbb28ae3a6c2da543690c993381cf` |

DTBとQEMUのhashは前回と同じで、各runのmetadata・serialにも保存しました。旧treeのsort入力やdevelopment signing keyも継承しますが、今回はbuildしていません。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-data-sync-itable/input-after \
  --run-dir output-data-idle-residual/runs/trace-r2 \
  --variant trace --seconds 120 --windows 2 --trace-writes \
  --guest-script board/cardputerzero/tools/bench/write-inventory/residual-guest.sh
```

同じcommandでrun名をr3〜r6へ変えて反復しました。出力先は存在すれば停止します。grown対照は元inputの`.config`・kernel・rootfs・DTBを`input-grown`へcopyし、SDだけをtrace-r1の終了imageへ置き換えます。`--output output-data-idle-residual/input-grown --run-dir output-data-idle-residual/runs/grown-r1 --variant grown --windows 1`で実行しました。対照にはpilotの正対照fileとjournal recoveryも含みます。

## 計測器と分類の検証

全7 runでRAM対照はp7 0、disk正対照は2,112 sector（grownだけ2,120）でした。各runでQEMU traceのp7全sector数がguestの最終累積値と一致します。boot・idle境界のin-flight I/Oは0です。これを条件に累積sector順でidle1を切り出し、offsetをp7内のblock番号へ換算しました。traceには時刻がないため、書き込み時刻はguestのpollから得た観測上限です。

反応がない壊れた計測器を0件と扱わないよう、集計器は空・切断trace、累積値不一致、非整列I/O、partition境界越えを拒否します。既存test suiteに正常・空idle・異常入力とCLI検査を加えました。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/residual-report.py \
  output-data-idle-residual/runs/trace-r{1,2,3,4,5,6} \
  output-data-idle-residual/runs/grown-r1 \
  --start-sectors 1376256 --size-sectors 720896 \
  --exclude-from-primary trace-r1 \
  --csv docs/experiments/2026-11-17-data-idle-residual.csv
```

既存CSVは上書きしません。再集計時は別の`--csv`を指定します。[CSV](2026-11-17-data-idle-residual.csv)には全device・phaseの生counterと、block別のidle1 sector数を収録しました。pilotの`valid=no`は主集計からの除外を表します。元のraw.csvは改変せずarchiveに残しました。

## 結果

単位は512 byte sectorです。主測定の中央値（最小–最大）はboot 16,848（16,848–16,848）、idle1 88（88–88）、idle2 0（0–0）です。窓の実長はsnapshotの処理を含み120.83秒（120.68–120.92）でした。

| run | boot | idle1 | idle2 | idle1開始uptime | 増加を初観測したuptime |
|---|---|---|---|---|---|
| trace-r2 | 16,848 | 88 | 0 | 31.57 | 51.91 |
| trace-r3 | 16,848 | 88 | 0 | 30.54 | 51.86 |
| trace-r4 | 16,848 | 88 | 0 | 32.48 | 52.87 |
| trace-r5 | 16,848 | 88 | 0 | 32.35 | 52.79 |
| trace-r6 | 16,848 | 88 | 0 | 32.72 | 53.33 |
| grown-r1（対照） | 416 | 0 | 未測定 | 24.79 | 増加なし |
| trace-r1（pilot、除外） | 16,848 | 88 | 0 | 32.71 | 53.27 |

初観測時刻の中央値は52.79秒（51.86–53.33）。poll間隔は約1秒で、正確な発行時刻や所要時間ではありません。

### 88 sectorの内訳

5回とも同じ11 blockで、各blockに8 sectorを書き込みました。`dumpe2fs`の配置、`debugfs icheck/ncheck/stat`、journalのdescriptorを照合した結果です。

| 帰属 | p7内block | sector | 証拠 |
|---|---|---|---|
| directory | 10、2097、2098 | 24 | inode 2=`/`、13=`/etc`、16385=`/msd-update` |
| bitmap | 9、25、32779 | 24 | group 0のblock/inode bitmapとgroup 1のinode bitmap |
| inode table | 41、32781 | 16 | group 0とgroup 1。root・新規directoryのinodeを含む |
| primary/backup superblock | 0、32768 | 16 | `dumpe2fs`のprimaryとgroup 1 backup |
| group descriptor | 1 | 8 | group descriptor table |
| journal領域、その他・未分類 | なし | 0 | journal inode 8のextentとは重ならない。11 blockで88 sector全量 |

### commitではなく、commit済みmetadataのhome-location writeback

全主測定でidle前後のjbd2統計は`2 transactions (1 requested)`のままでした。journal inodeのextentは15–24、26–40、1066–2064で、idle1の書き込み先には一つもありません。`debugfs logdump -a`のtransaction 3には上表の11 blockが全てあり、commit recordも残っています。別のjournal commitがidleで発生した説明とは一致しません。

T3はjournal block 18のdescriptor、19–29のmetadata、30のcommit recordです。物理blockへ換算すると34–40、1066–1071で、**全104 sectorの書き込みがboot counterより前**にあり、その後の上書きはありません。commit record（物理block 1071）も含めてtraceで確認でき、時計の一致を仮定せずにT3のcommit I/Oがidleより前だったと分かります。commit headerのguest CLOCK_REALTIMEは25.916〜27.972秒、新directoryのinode時刻は約22秒です。S02でgrowの後に`mkdir -p`する経路とdirectoryのinode・内容も一致します。CLOCK_REALTIMEとuptimeの厳密な同期は測っていません。

guest lifetimeは8,625から8,669 KiB、sessionは8,420から8,464 KiBへ増えました。差44 KiBは88 sectorと一致します。一方、journal内T3 primary superblockの`s_kbytes_written`は全5回205 KiBです。これは新しい累積値を記録するための独立した定期更新ではなく、以前の値を含むsuperblockのwritebackです。

### 候補を区別した結果

| 候補 | 測定・到達条件 | 判断 |
|---|---|---|
| grow・mkdir後のmetadata writeback | 全11 blockがcommit済みT3のhome-location。新directoryも含む | 今回の88 sectorを全量説明 |
| `commit=5s`の遅延commit | idle中commit回数不変、journal領域I/O 0 | 今回のidle残量はcommit自体ではない |
| lifetime値の定期superblock更新 | T3の値は205 KiBのまま。固定sourceの自動更新条件は1時間かつ16 MiB超 | 独立した残量の原因とは一致しない |
| atime・新しいuserspace更新 | 実mountは`noatime`。idle中の新transactionなし、directory一覧も不変 | 新しいfile更新を示す証拠なし。元のmkdirはuserspace由来 |
| MMP / fast commit | filesystem featureに`mmp`・`fast_commit`なし | この構成では対象外 |
| orphan file | featureは存在するが、専用block 2065–2096へのidle I/Oは0 | 独立したorphan-file I/Oなし。共有superblock内flagの由来までは分離しない |
| lazy inode table zeroing | 書き込み先に新規table全域の連続zeroなし | 88 sectorは初期化残量ではない |

原因が通常のmountだけではないかを確かめる対照も取りました。grow・mkdir済みのgrown-r1はjournal recoveryを含む再起動でもidle1 0でした。1回の対照なので、全ての既存SDやmount条件へ一般化はしません。

固定sourceではjournal commit後のbufferをVMへdirtyとして公開します。既定のdirty expiry 30秒・writeback周期5秒と約52秒の観測は整合します。ただしguest sysctlの実値と発行workerのPIDは取っていません。**home-location writebackの帰属は確認済みですが、どのworker/timerが発行したかは未確認**です。

## 修正候補（未実施）

S02のgrowだけでなく、その後の`mkdir -p`も完了してから、初期設定のprogressを閉じる前にmetadataの同期完了を待つ案です。固定kernelの`sync()`はfilesystemの同期に続いてblock deviceのwritebackも待つため、今回のhome-locationへの書き込みを起動処理内へ寄せる効果が期待できます。journal commitだけを待つ方法は、今回すでにcommit済みなので不十分です。

このBusyBoxは`CONFIG_SYNC=y`、`CONFIG_FEATURE_SYNC_FANCY`無効です。`sync -f /data`をそのまま使えるとは扱いません。全体の`sync`は他filesystemも対象にするため、対象限定の`syncfs()`等との比較が必要です。候補の実装・同期を加えた測定はしていません。総量を減らす案ではなく、所要時間・追加I/O・error処理・実SD・電源断は再検証が必要です。

## 捨てた試行と経緯

trace-r1はpollと`sleep 1`を120回直列に行い、idle1が140.93秒になりました。主測定から除外し、pollをbackgroundにしてforegroundの`sleep 120`を維持したr2〜r6を採りました。r1のcounter・trace・journalは診断用に全て保存しています。pilot hookは終了後に旧版の写しを作り、metadataのSHA-256と一致することを確認しました。

container内の初回tool probeでは`rg`が未導入でした。PATHとPython/QEMUの解決を確認し、検索は既に利用できるhost側で行いました。`sh`内のbrace展開によるhash取得も失敗したため、明示した3 pathで取り直しました。これらは計測runの失敗ではなく、失敗したhash取得の原出力はprovenance.logに保持しています。依存の追加・環境版の変更はありません。

## sourceによる補助確認

いずれも測定kernelの固定commitです。sourceで可能な経路と、実行時に観測した帰属を区別します。

- [jbd2/transaction.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/jbd2/transaction.c): `__jbd2_journal_temp_unlink_buffer()`がcommit後のdirty bufferをVMへ公開。
- [jbd2/commit.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/jbd2/commit.c): checkpoint対象bufferとcommit完了の処理。
- [ext4/super.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/super.c): `ext4_maybe_update_superblock()`、`ext4_update_super()`、`ext4_sync_fs()`。
- [ext4/sysfs.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/ext4/sysfs.c): lifetime/sessionのreadはblock counterの読取り。
- [mm/page-writeback.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/mm/page-writeback.c)、[fs/sync.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/sync.c): 既定値と同期完了の範囲。

## ログの保存と再確認

証拠archiveは同名directoryの`evidence.tar.gz`です。初期計画、全7 runのserial・raw.csv・metadata・trace・journal binary・debugfs・dumpe2fs・partition表、測定hook、入力hash、検証出力を保存しました。archive内manifestで全fileのbyte数とSHA-256を照合します。大きなSD・p7 imageは収録せず、journalの写しは収録しました。元imageの実行時hashはmetadataに残っています。

```sh
mkdir -p output-data-idle-residual/recheck
tar -xzf docs/experiments/2026-11-17-data-idle-residual/evidence.tar.gz -C output-data-idle-residual/recheck
# 以下は元の測定treeでの配置照合。runごとにr2を変更する:
docker/msd-dev sh -c '
  dd if=output-data-idle-residual/runs/trace-r2/sdcard.img \
    of=output-data-idle-residual/trace-r2-p7.img bs=4M skip=168 count=88 status=none
  output-openssl-lts/host/sbin/dumpe2fs output-data-idle-residual/trace-r2-p7.img
  output-openssl-lts/host/sbin/debugfs -R "icheck 0 1 9 10 25 41 2097 2098 32768 32779 32781" \
    output-data-idle-residual/trace-r2-p7.img
  output-openssl-lts/host/sbin/debugfs -R "ncheck 2 13 16385" output-data-idle-residual/trace-r2-p7.img
  output-openssl-lts/host/sbin/debugfs -R "logdump -a" output-data-idle-residual/trace-r2-p7.img
'
```

archiveは727,155 byte、SHA-256は`58ecfb4ea0781cfb77c4bd59f81d4af798211d6df4f2f27e6e5e8ad988f438f8`です。manifest対象83 fileをarchiveから読み直し、byte数・SHA-256の一致を確認しました。journal binaryは全7 run計29,360,128 byteを保存しています。

## 結論と未確認

今回の5回では、残る88 sector全量をgrow・mkdirに伴うcommit済みmetadataの遅延writebackへ帰属しました。採否の基準を満たしましたが、書き込みをなくしたことやAGENTS.mdへの適合を意味しません。製品source・kernel設定は変更していません。

worker PID・実timer設定、growとmkdirが共有するmetadataの操作別按分、修正候補の効果、実SD・FTL・電源断・製品画面は未確認です。QEMUのsector値を実SDの物理書き込み量として扱いません。
