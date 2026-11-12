# 起動後idleのpartition別書き込みとtimezone

- 状態: QEMUで測定。idleの0 sector基準は未達
- 日付: 2026-11-12
- 担当: Devin
- 関連: [書き込みの台帳](../design/write-policy.md)、[timezoneの採用範囲](../research/component-options/timezone.md)

## 目的と仮説

現行製品の永続書き込み先を棚卸しし、起動後に利用者が操作しない区間の書き込みを測ります。
log・cache・一時fileは既にRAMに置かれています。timezoneの変更だけではidleの書き込みは変わらないと予想します。
起動の書き込み、idle、測定器を確かめるための操作を分けます。

## 採否の基準（計測前）

- idleの各120秒区間で、disk全体とp1〜p7の書き込みsector差分が0。正の値は隠さず台帳の未対応として扱います。
- 同一boot内の連続5区間を測り、中央値・最小・最大を記録します。独立した5回のbootではありません。
- RAMへの1 MiB書き込みとloggerは、disk sectorを増やさないこと。
- `/data` への1 MiB書き込みでは、disk全体とp7が少なくとも2048 sector増えること。これを満たさない試行は、idleが0でも有効と扱いません。
- 更新後は、timezoneがJST、offsetが+0900。製品build、A/B slotのQEMU boot、`tests/msd-update/run.sh`が成功すること。
- 圧縮rootfsとzoneinfoの実byte数を記録します。容量と速度の優位性の判定には使いません。

## 条件と手順

基準は `d7d9d622eae2f5f78dc0b891203f3641f334123b`、Buildrootは `8b238854d909c9cce32ef9671d968b03e323b55d`。
`O=output-openssl-lts` のwarm treeを両側で使い、基準をdefconfigから再設定して通常の `make` を行います。
既存imagesとconfigは `output-write-inventory/preexisting-images` と `preexisting.config` に保存してから再構築しました。
通常のmakeで両側のtarget-finalizeとimage生成を行い、個別のreconfigureはしていません。既存の実験scriptは編集していません。
host OSはUbuntu 26.04.1 LTS、開発OCI内はDebian 13です。実際のQEMUは11.1.2、cross GCCは14.3.0、kernelは6.18.59-v8です。
OCI digestは `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`、genimageが使ったmke2fsは1.47.4です。
ccacheは両側で有効です。区間ごとのhit統計は採り忘れ、終了時の累積だけを保存しました。速度比較はしていません。

計測器は [host runner](../../board/cardputerzero/tools/bench/write-inventory/run.py) と [guest probe](../../board/cardputerzero/tools/bench/write-inventory/guest.sh) です。
製品rootfsは変更せず、login後にprobeだけを `/run` へ送ります。作業用SD imageを2のべき乗へ広げる挙動は既存QEMU harnessと同じです。
shellへのlogin・probeの準備後、読み取りとsleepだけで5区間を測ります。controlは全idle区間の後に実行します。
終了はhostからQEMUを停止し、shutdown時のseed保存やunmountは測定に混ぜません。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-openssl-lts --run-dir output-write-inventory/before-01 \
  --variant before --seconds 120 --windows 5
```

run directoryは上書きしません。入力hashとcommitは `metadata.json`、QEMU版・binary hashは `serial.log` の `run-qemu:` 行に残します。
raw CSVは `run_id,variant,repeat,metric,value,unit,valid,note` 形式で、`note` にphase、uptime、元のstat全fieldを保存します。
sectorは512 bytesです。p4はextended partitionなので、p4を加えた合計とdisk全体を同じ量として足し合わせません。

## 保存した値と入力

- [raw CSV](2026-11-12-write-inventory.csv): disk全体・p1〜p7の全stat、失敗試行、容量。`value`は累積counterで、差分ではありません。差分は同じdevice・repeatの `idle-after` から `idle-before` を引きます。
- [入力・tool・logのhashと容量明細](2026-11-12-write-inventory.json): 各runの入力hash、QEMUのprovenance行、生成initの一覧とhash、`/var`のsymlink、rootfsの比較。
- 大きなserial・build log・SD写しはcommitしていません。下記commandで生成でき、logのSHA-256は上のJSONにあります。要約だけでなくserialの全stat・process・mountも読みました。

sectorの単位は512 bytesです。全partitionを足してからdisk全体を足す集計はしません。
計測器のcontrolはidleへの影響を避けるため末尾です。beforeは事後に有効性を確認し、その完了後にafterを始めました。

### 再生成

両側のimageは書き換えず、runnerがrun directoryへ複製したSDだけを変更します。
基準の版を別のworktreeで上記commitから構築するか、変更前にimagesを保存します。
変更後は同じwarm treeでdefconfigとmakeを再実行します。

```sh
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-openssl-lts msd_cardputerzero_defconfig && make -C output-openssl-lts -j8'
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-openssl-lts --run-dir output-write-inventory/after-01 \
  --variant after --seconds 120 --windows 5
docker/msd-dev env OUTPUT_DIR=/work/output-openssl-lts \
  QEMU_LOG_DIR=/work/output-write-inventory/boot-a board/cardputerzero/qemu/test-boot.sh
docker/msd-dev env OUTPUT_DIR=/work/output-openssl-lts \
  QEMU_LOG_DIR=/work/output-write-inventory/boot-b board/cardputerzero/qemu/test-ab.sh
tests/msd-update/run.sh
python3 tests/write-inventory/run.py
```

runnerはkernel・DTB・root A・driveの写し・watchdog等を固定します。
beforeとmatureの完了後にhost runnerの環境固定とCSV発行順を整理しました。両runの実際のboot引数・input hashを読み、同じ設定であったことを照合しています。guestの実行処理は両側で同じです。
activeなscriptは変更せず、lint用の注記も測定終了後に加えました。注記以外のguest実行行は同じで、測定時のhashをJSONに残しています。

## 結果

初回bootの最初の120秒でp7に8320 sector（4,259,840 bytes）増え、その後は0でした。これはlog/cacheをRAMへ移した前後差ではありません。RAM配置は変更前から満たしており、変更した製品設定はtimezoneだけです。

| 試行 | p7の120秒ごとの差分（sector） | 中央値 / 最小 / 最大 | disk全体・他partition |
|---|---|---|---|
| before-02 | 8320, 0, 0, 0, 0 | 0 / 0 / 8320 | mmcblk0も同じ。p1〜p6は全て0 |
| after-01 | 8320, 0, 0, 0, 0 | 0 / 0 / 8320 | mmcblk0も同じ。p1〜p6は全て0 |
| mature-01 | 64（1区間のみ） | 反復分布として扱いません | mmcblk0も64。p1〜p6は0 |

before/afterのRAM controlは全deviceで0、disk controlはmmcblk0・p7で2104 sector、他は0でした。matureのdisk controlは2096 sectorです。
最初の区間を除いて「idle書き込みなし」とは結論しません。規則に合わせる追加設計が必要です。

### 容量とtimezone

| 指標 | before | after | 差 |
|---|---:|---:|---:|
| rootfs.squashfs | 20,680,704 bytes | 20,725,760 bytes | +45,056 bytes |
| rootfs.tar | 40,509,440 bytes | 40,919,040 bytes | +409,600 bytes |
| zoneinfoのregular file本文合計 | 0 bytes | 183,198 bytes（121 file） | +183,198 bytes |
| `date '+%Z %z'` | UTC +0000 | JST +0900 | 既定localtimeが変化 |

tarの内容hashを比較すると、追加132 path、削除0 pathでした。既存fileの内容差は `/etc/issue` と `/usr/lib/os-release` のdirty表示です。
zoneinfo本文合計はtarのregular fileだけを足し、symlink・hardlinkの参照先を重ねて足していません。
圧縮rootfsの差には版表示や生成metadataも含み、tzdata単体の圧縮率を示す値ではありません。
kernel Imageは両側18,016,768 bytesで同じhashです。新しいprobeはどちらの製品rootfsにも入っていません。

### 回帰と監査

製品buildとQEMUのA（p5）・B（p6）のready/login、msd-updateのhost suiteは成功しました。
これはfirmwareのtryboot成功やtarget上の全更新操作の試験ではありません。
legal-infoは終了値0で、target/host tzdataとhost-zicのLICENSE hashはOKでした。
既存のBuildroot source未保存、Bootlin license file未定義の2警告は残ります。R23の未解決を、この変更で閉じません。

## 失敗・限界

| 試行・確認 | 結果と扱い |
|---|---|
| `before-01` | heredoc送信後のpromptを `\\n# ` として待ち、改行なしの `# ` を見落としてtimeout。probeの開始前で、有効なcounterはありません。元log・入力hashを保持し、次のrun IDで再試行しました |
| shellcheck初回 | BusyBox ashの `ulimit -c` にSC3045。測定終了後に、このshellで使う拡張であることを注記して再検査しました |
| 拡張済みimageの追試 | 下記の仮説に反して64 sector増えました。growをしなければidleは0になる、とは結論しません |

QEMUのcounterはguestから見たblock書き込みで、SD実機・FTLの書き込み量ではありません。
counterだけではprocess別の寄与を分離できません。`resize2fs` とext4lazyinit workerが到達したことはserialにありますが、8320 sectorの全てがその経路から出た証拠はありません。
追試でも正の値が残るため、growだけでは全量を説明できません。block trace等による帰属、起動時のseed・mkdir・journalとの分離は未実施です。
afterでは別のQEMU boot試験・legal-infoもhost上で並行しており、host負荷は統制していません。guestのidle中には追加操作をしていませんが、時間・性能の比較には使いません。
shutdown、障害回復、実機、power-fail、RTC、NTP、別のSD容量は未測定です。late bootの観測区間が0でも、将来のidle全体が0という証明ではありません。

## 途中結果を受けた追試の計画

基準の最初の120秒区間でp7に8320 sector増え、次の区間は0でした。同じbootにresizeと `ext4lazyinit` があるため、拡張済みimageでの再bootを1回追加します。
最初の試行を消したり、最初の区間を集計から除いたりしません。追試は120秒×1区間で、独立した性能評価には使いません。
元の作業用imageを保存したまま複製し、同じkernel・rootfs・DTBで再bootします。仮説は「再拡張なしなら、この区間の差分は0」です。
これで0になっても、先の8320 sector全量を特定processへ帰属した証拠とは扱いません。

追試の実行commandです。初回のdisk control fileやseedは残るため、同じFS状態のA/Aではありません。
`before-images` と `before.config` は、変更前buildから保存したものです。

```sh
mkdir -p output-write-inventory/mature-input/images
cp --sparse=always output-write-inventory/before-02/sdcard.img output-write-inventory/mature-input/images/sdcard.img
cp output-write-inventory/before.config output-write-inventory/mature-input/.config
ln -s ../../output-openssl-lts/host output-write-inventory/mature-input/host
ln -s ../../before-images/Image ../../before-images/rootfs.squashfs ../../before-images/bcm2710-rpi-cm0.dtb output-write-inventory/mature-input/images/
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-write-inventory/mature-input --run-dir output-write-inventory/mature-01 \
  --variant mature --seconds 120 --windows 1
```
