# 読み取り専用データ領域とファイルシステム比較

この文書は、CardputerZero の現在の書き込み経路をコードで確認し、`/etc`・`/data` の read-only 化、ファイルシステム選択、障害試験を提案する。提案や未測定の性能評価は【推測】、コードや取得済み一次資料で確認した事項は【一次】、未確認事項は【未確認】と記す。ファイルシステム比較の範囲は Linux 6.18 系で microSD 用途に関係する、依頼指定の候補である。

## 現在のマウントと書き込み先

| 対象 | `origin/main` の状態 | 根拠 |
|---|---|---|
| `/` | SquashFS を `ro` でマウントする。 | `board/cardputerzero/rootfs-overlay/etc/fstab:5` |
| `/tmp`、`/run`、`/dev/shm` | fstab が tmpfs としてマウントする。 | `board/cardputerzero/rootfs-overlay/etc/fstab:3,6-7` |
| `/data` | ext4。新規 image と空領域の初期化は 4 KiB block。既存の 1 KiB filesystem は移行せずそのまま使う。mount option は `noauto,noatime,nodev,nosuid,data=ordered,errors=remount-ro`。`S02msd-data` が `fsck.ext4 -p`、mount、成長処理、状態 directory 作成を行う。 | `board/cardputerzero/genimage.cfg`、`board/cardputerzero/rootfs-overlay/etc/fstab:8`、`board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data` |
| `/etc` | `S03msd-etc-overlay` が `/data/etc:/etc` を lower、`/run/etc-overlay` を upper/work とする overlay を作り、merged view を `/etc` に bind mount する。 | `board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay:3-11` |
| seedrng | `SEEDRNG_ARGS="--seed-dir=/data/seedrng"`。seedrng の永続 seed は `/data` 配下に置かれる。 | `board/cardputerzero/rootfs-overlay/etc/default/seedrng:1`、`board/cardputerzero/post-build.sh:69-82` |
| update 状態と鍵 | updater の状態は `/data/msd-update`、公開鍵の読み取り元は `/etc/msd-update/update-key.pem`。ビルド時に公開鍵と key-origin を rootfs の `/etc` に生成する。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-update:8,10,168-178`、`board/cardputerzero/post-build.sh:182-185` |
| A/B payload と selector | rootfs は p5/p6、boot payload は p2/p3 の inactive raw partition に書く。状態記録は `/data/msd-update`、`autoboot.txt` の切替は p1 上で行う。A/B payload を `/data` に保存する方式ではない。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-update:56,170-179,220-231` |
| data partition grow | partition table の p4/p7 を調整し、`resize2fs` で p7 の ext4 を拡張する。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow:25,116-134` |
| hwinfo・ready marker | hwinfo cache は `/run/msd/hardware`、ready marker は `/run/msd-ready`。これらの書き込み先は揮発領域である。 | `board/cardputerzero/rootfs-overlay/etc/init.d/S97msd-hwinfo:3-9`、`board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready:3` |
| `/var` とログ | `/var` 自体の mount はない。skeleton では `/var/cache`、`/var/log`、`/var/spool`、`/var/tmp` が `/tmp` への symlink、`/var/lock`、`/var/run` が `/run` への symlink、`/var/lib/misc` が `/tmp` への symlink。対象 runtime scripts に syslog daemon の `/var/log` 書き込み設定も見つからなかった。 | fstab、Buildroot `system/skeleton/var`、`board/cardputerzero/post-build.sh:5` |
| RTC | `RESEARCH.md:40` は I2C1 上の RX8130CE を記録する。対象 init scripts に時刻を `/data` または `/etc` へ保存する処理は見つからなかった。RTC 初期化と実機時刻取得の経路は未確認。 | `RESEARCH.md:40`、上記 init scripts の調査 |
| BCM2835 RNG | kernel の BCM2835 RNG driver は存在する【一次】が、`linux.fragment` に `CONFIG_HW_RANDOM_BCM2835` の明示設定はない。生成済み Linux `.config` を取得できていないため、有効状態は【未確認】。seedrng の `/data/seedrng` 保存を RNG hardware による代替とみなさない。 | `board/cardputerzero/linux.fragment`、生成 `.config` 未取得、[K1] |

`/data/etc` が lowerdir の先頭にあるため、そこにある既存ファイルが A/B 更新後の image 側 `/etc` の同名既定値を隠し続ける可能性がある【推測】。overlay の lower/upper の意味は [K2] に示す。現在の update metadata、seedrng seed、partition resize は `/data` への書き込み経路であり、read-only 化するなら対象ごとに書き込み窓を設計する必要がある。

## 提案する read-only policy

以下は未実装の提案である【推測】。

1. `/data` は通常 `ro` とし、設定の永続化、seedrng seed 更新、update journal/state 更新、data partition resize の各処理だけ、排他的な maintenance window で `rw` にする。更新処理は一時ファイル作成、`fsync`、atomic rename の順を守り、全 writer が終了した後に `sync` と `ro` remount を行う。現行 updater は `/data` が writable mount 済みであることを前提にしており、remount 制御は実装されていない。
2. `/etc` は通常時 read-only とし、設定変更時だけ maintenance window で writable にして、永続設定を `/data` に同期した後に再び read-only にする。現行の `/run` upper は writable overlay なので、現在の揮発設定を継続するなら `/etc` を完全 read-only にする設計とは異なる。揮発設定を許す範囲を定めるか、maintenance mode に限定する必要がある。永続設定を変更するときは `/data` の保護された書き込み窓を使う。image の既定値を更新した際に古い `/data/etc` が残る問題には、設定 schema/version migration、既定値の overlay を止めて明示的な設定だけ保存する方法、または対象設定を個別に管理する方法を比較する。
3. 通常ログは tmpfs に置き、再起動後に必要な crash record は pstore/ramoops 等の別経路を検討する。開発 image だけで `/data` への詳細ログを許す案もある。現状 `/var` は tmpfs ではないので、採用前に fstab/service 設定と実際のログ writer を追加・検証する。
4. `/data` の起動時には ext4 の `fsck.ext4 -p` と journal recovery を許す。ext4 の `ro` mount は未 clean 状態で journal replay を行い、partition に書き込む可能性がある。`ro,noload` は journal replay を止める一方、直前の unclean shutdown による不整合を残し得るため、通常運用の既定値にせず、厳密な無書き込み検査に限る。回復に必要な書き込みを許可する maintenance state と、検査後の `ro` 運用を分離する【一次: K3】。

### OverlayFS の3案

| 案 | upper/lower と書き込み | 電断・更新上の論点 |
|---|---|---|
| 現行 `/etc`-only overlay | lower=`/data/etc:/etc`、upper/work=`/run/etc-overlay`。upper は tmpfs、設定 overlay write は揮発。 | `/data/etc` が stale lower になり、A/B 更新後の新しい `/etc` defaults を隠す可能性【推測】。 |
| full-root overlay | lower は read-only SquashFS、upper/work は tmpfs または別の writable FS。全 root の変更が upper に入る。 | tmpfs upper は電断で消える。persistent upper は電断回復と旧 rootfs の whiteout/opaque metadata の移行を要検討【推測】。 |
| `/data` bind mount/symlink | mutable path だけを `/data` に直接向ける。OverlayFS whiteout は不要。 | persistent writes は明示的になり、schema migration と同一 filesystem 上の atomic rename/fsync を設計する。A/B rootfs 更新後の stale config は別途解決が必要【推測】。 |

OverlayFS upper は trusted/user xattr と有効な `d_type` を必要とする。lower の削除は whiteout、directory の masking は opaque metadata に記録されるため、full-root upper を persistent にする場合は upper filesystem と overlay metadata の recovery が必要になる【一次: K2】。rename は同じ filesystem 内の namespace 操作であり、cross-filesystem move を同じ atomic operation と仮定しない。電断後の durability には対象ファイルと親 directory の同期を検証する【一次: K18-K19】。

### mount option と ext4/F2FS/btrfs の比較方針

| 項目 | 現状・候補 | 調査上の扱い |
|---|---|---|
| `noatime` | S3 で維持し、`/data` mount option に含めた。 | アクセス時刻更新を避ける。 |
| `lazytime` | inode の atime/mtime/ctime を memory 上で更新し、disk 更新を遅らせる。 | S3 の5回測定では V3 の中央値が V1 と同じで、10%削減条件を満たさず採用しない【一次: K4】【実測】。 |
| `nodev,nosuid` | S3 で `/data` mount に採用した。 | `/data` は device node や setuid executable の実行場所にしない。 |
| `data=ordered` | S3 の新規 image と mount option で採用。既存 filesystem も同じ mode で mount する。 | 小ファイル workload、書き込み量、復旧挙動を測る。 |
| 4 KiB block | S3 で新規 filesystem に採用。 | 既存 1 KiB filesystem は再フォーマットしない。small-file corpus、image size、fsck/mount 時間を比較する。 |
| `inline_data` | ext4 feature。mount option ではなく、format 時に feature を有効化して作る。 | S3 の V2 は電断試験を20回中20回通過した。5回測定の書き込み中央値は V1 と同じで、20%削減条件を満たさず採用しない【実測】。 |
| F2FS `fsync_mode` | `posix` が既定、`strict` はより強い同期挙動、`nobarrier` 等も文書化される。 | checkpoint、fsync 頻度、power-cut replay と fsck/mount 時間を測る【一次: K5】。 |

### S3 の測定結果と採用判断

QEMU の `msd.s3bench=1` hook で、100 個の 200 B file を作り、各 file を一時 file へ書いて置き換える workload を実行した。各 variant は別 image から起動し、5 回測定した【実測】。

| Variant | Filesystem / mount option | field 7 before→after sectors（run 1 / 2 / 3 / 4 / 5） | delta bytes（run 1 / 2 / 3 / 4 / 5、中央値） | idle delta sectors（run 1 / 2 / 3 / 4 / 5） | `df` used KiB（run 1 / 2 / 3 / 4 / 5、中央値） |
|---|---|---|---|---|---|
| V0 | 1 KiB / `data=journal` | `2,864→8,220 / 2,864→7,904 / 2,864→8,064 / 2,864→7,668 / 2,864→7,634` | `2,742,272 / 2,580,480 / 2,662,400 / 2,459,648 / 2,442,240`（2,580,480） | `0 / 0 / 0 / 0 / 0` | `153 / 153 / 153 / 153 / 153`（153） |
| V1 | 4 KiB / `data=ordered` | `664→15,544 / 664→15,544 / 664→15,544 / 664→15,544 / 664→15,544` | `7,618,560 / 7,618,560 / 7,618,560 / 7,618,560 / 7,618,560`（7,618,560） | `0 / 0 / 0 / 0 / 0` | `572 / 572 / 572 / 572 / 572`（572） |
| V2 | 4 KiB / `data=ordered` + `inline_data` | `560→15,440 / 560→15,440 / 560→15,440 / 560→15,440 / 560→15,440` | `7,618,560 / 7,618,560 / 7,618,560 / 7,618,560 / 7,618,560`（7,618,560） | `0 / 0 / 0 / 0 / 0` | `552 / 552 / 552 / 552 / 552`（552） |
| V3 | 4 KiB / `data=ordered` + `lazytime` | `664→15,544 / 664→15,544 / 664→15,544 / 664→15,544 / 664→15,544` | `7,618,560 / 7,618,560 / 7,618,560 / 7,618,560 / 7,618,560`（7,618,560） | `0 / 0 / 0 / 0 / 0` | `572 / 572 / 572 / 572 / 572`（572） |
| V4 | 1 KiB / `data=ordered` | `2,850→7,282 / 2,850→7,190 / 2,850→7,150 / 2,850→7,526 / 2,850→7,398` | `2,269,184 / 2,222,080 / 2,201,600 / 2,394,112 / 2,328,576`（2,269,184） | `0 / 0 / 0 / 0 / 0` | `153 / 153 / 153 / 153 / 153`（153） |
| V5 | 4 KiB / `data=journal` | `672→17,968`（5回） | `8,855,552`（5回、中央値8,855,552） | `0 / 0 / 0 / 0 / 0` | `572 / 572 / 572 / 572 / 572`（572） |

前回の QMP `query-blockstats` は QEMU 6.2.0 の SD model の読み書き byte counter を計上せず、`rd_bytes` と `wr_bytes` の両方が0だったため、書き込み量の指標として無効だった。今回は mkfs 時に `-E lazy_itable_init=0,lazy_journal_init=0` を指定し、`/data` の mount と online grow の後に `mount -o remount,noinit_itable /data` を実行した。QEMU では remount が受理された。各 run は `sync` 後に field 7 を読み、10秒待って再読する validity gate を通し、idle delta が0のときだけ workload を開始した。V0〜V5の30回すべて idle delta は0で、idle delta を各表行に記録した【実測】。workload 開始直前と最終 `sync` 後に field 7（sectors written）を読み、delta bytes を `(after - before) × 512` で算出した。これは guest 側の block-layer 書き込み量であり、カード内部の FTL 書き込みや NAND への物理書き込み量は含まない【実測】。raw counter は[同名の S3 実験記録](../experiments/2026-10-19-s03-data-ext4-writes.md)の CSV に保存した。

V1 と V2 は、step c の開始後 1〜10 秒の無作為な時点で QEMU を `SIGKILL` し、同じ SD image で再起動して検証した。V1 は20回中20回、V2 も20回中20回で、mount 後の `fsck.ext4 -n` は clean、100 file はすべて旧内容か新内容のいずれか 200 B を保持した。失敗はなかった【実測】。試行ごとの delay と status は[電断 CSV](../experiments/2026-10-19-s03-data-ext4-powercut.csv)に保存した。

前回の3回測定では V1 の field 7 の開始値に大きなばらつきがあり、背景の ext4 lazy inode-table initialization が混入した可能性を再検証した。追加の V1 観測では noinit workaround を使わず、mount 時の field 7 が16、60秒後が17,016で、差は17,000 sectors（8,704,000 bytes）だった【実測】。この区間は `/data` mount から `msd-data-grow` の online resize を含む最初の60秒間であり、lazy-init thread 単独の書き込み量ではない。

新しい測定では V1 の中央値は7,618,560 bytes だった。V2 も7,618,560 bytesで、V1 に対する削減は0%であり、20%以上の条件を満たさなかった。V2 の電断試験は20回中20回成功したが、書き込み量の条件を満たさないため `inline_data` は採用しない。V3 も7,618,560 bytesで削減は0%となり、10%以上の条件を満たさないため `lazytime` も採用しない。採用規則に従い、4 KiB と `data=ordered` の V1 を維持する【実測】。初回60秒観測の詳細は[実験記録](../experiments/2026-10-19-s03-data-ext4-writes.md)に記録した。

追加した2×2では、`data=ordered` は `data=journal` より1 KiB時に12.1%、4 KiB時に14.0%少ない一方、4 KiBは同じ journal mode の1 KiBに対して3.43倍、ordered modeでは3.36倍の guest 書き込み量となり、この workload では block size の差が大きかった【実測】。V0の既存測定には `nodev,nosuid` がなく、V1/V4/V5にはあるが、これらの security mount option はこの通常ファイル workload の書き込みを変えない。

実カードでは、ATP の industrial microSD 資料が “4KB page management” と記載し、Cactus Technologies の資料は “NAND flash is programmed in pages” としたうえで、ページ寸法を “either 2KB or 4KB” と説明している【一次】([ATP microSD](https://www.melchionielectronics.com/media/f8/73/b0/1759225388/atp_microsd_card.pdf?ts=1760740424), [Cactus Technologies](https://www.cactus-tech.com/wp-content/uploads/2019/03/CTWP005-WriteAbort-v3.pdf))。カードによっては4 KiB以上の内部ページに対して1 KiBの書き込みが内部で増幅される可能性があるが、製品固有の FTL とページ寸法は guest から確認できないため、対象 SD card での実機確認が必要である【推測】。

| FS | 電断・回復モデル | small files・書き込み量 | fsck、RAM、tool size、成熟度 | MSD/Linux での位置づけ |
|---|---|---|---|---|
| ext4 | Journal。data mode、barrier、fsync と clean shutdown に依存する。 | block slack と metadata overhead は workload 次第。write volume は測定対象。 | `e2fsck` あり。時間・kernel/RAM/tool size は未測定。広く使われる成熟度は【推測】。 | `/data` の第一候補。書き込み期間と mount/recovery を実測【候補】。 |
| F2FS | Log-structured。checkpoint と roll-forward recovery を使う。 | 小ファイル性能、GC/write amplification は media と workload 次第【推測】。 | `fsck.f2fs` あり。時間・RAM/tool size は未測定。組込み実績を対象機で確認【推測】。 | ext4 と同一 corpus で比較する候補。既定採用はしない。 |
| btrfs | CoW tree/transaction。 | CoW、metadata、snapshot は書き込み量と容量に影響し得る【推測】。 | `btrfs check` 等あり。所要時間・tool/kernel/RAM cost は未測定。 | 高機能 reference。SD の単一 `/data` では複雑性と性能を測る。 |

read-only が通常状態なら、filesystem 選択の主要な差は主に mount、fsck/recovery、および `/data` を `rw` にする短い窓の書き込み性能に現れる、という仮説を測る【推測】。`e2fsprogs`、`f2fs-tools`、`btrfs-progs` の rootfs/tool size と、fsck・mount の時間はこの repository では未測定であり、数値は提示しない。

## ファイルシステムの候補と既存システムの例

Linux 6.18 系で microSD に使える候補の比較と、既存システムの設計例は、[ファイルシステムの候補と設計例](fs-candidates.md) に分けました。

## S17: ストレージの障害・速度の模擬

これは試験計画であり、まだ実行していない。`dm-log-writes` は block write と flush の順序を log に記録し、`replay-log` で任意の位置まで再生できる。filesystem の各 write/flush point で image を作り、mount/fsck とデータ invariants を検査する方法を試す。xfstests は `replay-log` を使う `dmlogwrites` helper を含む。CrashMonkey/Ace は bounded workload を生成し、crash point ごとの recovered state を検査する別系統の framework であり、同一ツールとみなさない【一次: S17-1〜S17-3】。

| 手法 | 何を模擬・検証するか | root / sudo | MSD/Linux での使い分けと限界 |
|---|---|---|---|
| dm-log-writes + `replay-log` | 実際の block write/flush 列を保存し、flush/FUA/mark までの prefix を再生。fsck/checker を各再生点で行う。 | Device Mapper table と block device を作る権限が必要。QEMU guest 内の仮想 block device だけを使うなら guest root が必要だが、host root は不要。host の実 block device を直接 map する場合は host root が必要。 | filesystem crash consistency の exhaustive/bounded replay に適する。実 microSD controller/FTL の power loss timing は再現しない。 |
| dm-flakey | 一定間隔で read/write error、drop write、corrupt I/O 等を発生させる。 | Guest 内では guest root、host block device では host root。 | I/O failure handling や remount/fsck を試す。実カードの障害頻度を表すものではない。 |
| dm-delay | read/write/flush に独立の固定 delay を入れる。 | Guest 内では guest root、host block device では host root。 | latency 感度の試験。SD の分布、queueing、内部 FTL garbage collection は再現しない。 |
| QEMU `blkdebug` | QEMU block request の指定 event/state/sector に error を注入する。 | QEMU process が user-owned image を開ければ host root 不要。guest root も故障した block path を検査する場合だけ必要。 | update の I/O error path を試す。実 card failure mode と同じとは限らない。 |
| QEMU block throttle | `bps`/`iops` で virtio/block request throughput を制限する。 | Host root 不要。 | SD の上限速度に寄せた比較を行う。固定上限だけで card latency、command busy time、FTL を再現しない。 |
| QEMU `cache=unsafe` + 強制終了 | QEMU が flush request を尊重しない cache mode とし、VM/QEMU を止めて flush ordering に依存する code path を探す。 | QEMU process を user として実行できれば host root 不要。guest root は通常試験操作で必要。 | QEMU unsafe mode は「flush を無視する」故障注入。`kill -9` は host power cut ではなく、host kernel/page cache が残るため物理 SD の電断と同一視しない。 |
| QEMU `raspi3b` SD | BCM SD host と QEMU の SD card block backend を通した機能試験【一次: S17-6】。 | QEMU の通常起動に host root 不要。 | QEMU SD model は controller/card protocol の一部を模擬するが、SD FTL、カード固有 latency、実 timing を表さない【推測】。source code は command を「never really delay」すると記す。 |
| FEMU / MQSim / FlashSim | SSD/NAND FTL model・NVMe queue・flash behavior の研究用比較。 | tool/config により異なる。導入・実行条件は別途確認する。 | 参考モデルのみ。SD card の vendor-specific controller/FTL と同等ではなく、結果をカード性能に転用しない。 |

dm target は Linux device-mapper の privileged block mapping を使うため、root 権限が要る。QEMU `blkdebug`、throttle、cache mode は user-owned disk image を QEMU process が開く構成であれば host root は不要である。Guest の filesystem mount、fsck、dmsetup は guest 内 root を必要とする。host の実 device を触る試験を追加する場合は host root と破壊可能な専用媒体が必要であり、本計画では実施しない【一次: S17-1〜S17-6】。

S17 の dm-log-writes、xfstests、CrashMonkey/Ace は目的と仕組みが異なる。xfstests の `dmlogwrites` helper は replay utility で mark までを再生し、fsck/check を実行する。CrashMonkey は独自の bio logging/disk snapshot kernel modules と auto-checker を用い、Ace は有限の範囲で operation sequence を exhaustively 生成する。CrashMonkey を `dm-log-writes` の wrapper として説明しない【一次: S17-2、S17-3】。

## 出典、抜粋、信頼度

外部 URL は参照時に取得したものを記録する。抜粋は claim と直接関係する短い原文であり、定性的な性能評価や MSD/Linux への適用は【推測】として区別した。

| ID | URL | 短い逐語抜粋 | 信頼度・適用範囲 |
|---|---|---|---|
| K1 | [BCM2835 RNG driver](https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/drivers/char/hw_random/bcm2835-rng.c) | “devm_hwrng_register(dev, &priv->rng)” | 【一次】driver の存在。実効 config は未確認。 |
| K2 | [Linux 6.18 OverlayFS documentation](https://docs.kernel.org/6.18/filesystems/overlayfs.html) | “The upper filesystem must support the creation of trusted.* and/or user.* extended attributes”; removed files use “whiteouts and opaque directories” | 【一次】Linux 6.18 upper filesystem requirements and deletion metadata. |
| K3 | [Linux 6.18 ext4 administration](https://docs.kernel.org/6.18/admin-guide/ext4.html) | “if the filesystem is mounted read-only, and the journal needs to be replayed, the filesystem will be mounted read-write for the duration of the replay” | 【一次】Linux 6.18 `ro` mount と journal recovery。 |
| K4 | [`mount(2)`](https://man7.org/linux/man-pages/man2/mount.2.html) | “lazytime” updates timestamps in memory and writes them later | 【一次】mount behavior。 |
| K5 | [Linux 6.18 F2FS documentation](https://docs.kernel.org/6.18/filesystems/f2fs.html) | “In ‘posix’ mode, which is default, fsync will follow POSIX semantics” | 【一次】Linux 6.18 F2FS fsync policy。 |
| K6 | [Linux 6.18 SquashFS documentation](https://docs.kernel.org/6.18/filesystems/squashfs.html) | “Squashfs is a compressed read-only filesystem for Linux.” | 【一次】read-only compressed image。 |
| K7 | [Linux 6.18 EROFS documentation](https://docs.kernel.org/6.18/filesystems/erofs.html) | “EROFS is a read-only filesystem” | 【一次】filesystem role。 |
| K8 | [Linux 6.18 cramfs documentation](https://docs.kernel.org/6.18/filesystems/cramfs.html) | “You can’t write to a cramfs” | 【一次】write restriction. |
| K9 | [Linux 6.18 romfs documentation](https://docs.kernel.org/6.18/filesystems/romfs.html) | “This is a quite dumb, read only filesystem” | 【一次】intended use. |
| K10 | [Linux 6.18 ext2 documentation](https://docs.kernel.org/6.18/filesystems/ext2.html) | “Smaller blocks mean less wasted space per file” | 【一次】block-size tradeoff. |
| K11 | [rpi-6.18.y `fs/ext4/Kconfig`](https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/fs/ext4/Kconfig), [`fs/Kconfig`](https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/fs/Kconfig) | “The ext4 filesystem supports mounting an ext3 filesystem”; `fs/Kconfig` sources `fs/ext4/Kconfig` but not `fs/ext3/Kconfig` | 【一次】6.18 source confirms ext3 format support through ext4 and no separate ext3 Kconfig. |
| K12 | [Linux 6.18 Btrfs documentation](https://docs.kernel.org/6.18/filesystems/btrfs.html), [upstream bcachefs removal commit](https://github.com/torvalds/linux/commit/f2c61db29f277b9c80de92102fc532cc247495cd), [bcachefs project](https://bcachefs.org/) | “Btrfs is a copy on write filesystem”; “As of 6.18, bcachefs is no longer being distributed with the kernel” | 【一次】Btrfs behavior and bcachefs upstream status. |
| K13 | [Linux 6.18 tmpfs documentation](https://docs.kernel.org/6.18/filesystems/tmpfs.html), [Linux 6.18 ramfs documentation](https://docs.kernel.org/6.18/filesystems/ramfs-rootfs-initramfs.html) | “Everything in tmpfs is temporary” | 【一次】volatile in-memory storage. |
| K14 | [Linux 6.18 UBIFS documentation](https://docs.kernel.org/6.18/filesystems/ubifs.html), [Linux 6.18 JFFS2 documentation](https://docs.kernel.org/6.18/filesystems/jffs2.html), [Linux 6.18 MTD/UBI/UBIFS overview](https://docs.kernel.org/6.18/filesystems/ubifs-authentication.html) | “MTD (Memory Technology Devices) subsystem provides a uniform interface to access raw flash devices”; “UBIFS is a filesystem for raw flash which operates on top of UBI” | 【一次】raw flash model. Managed-FTL SD mismatch is an engineering inference. |
| K15 | [Linux 6.18 XFS logging design](https://docs.kernel.org/6.18/filesystems/xfs/xfs-delayed-logging-design.html) | “XFS uses Write Ahead Logging for ensuring changes to the filesystem metadata are atomic and recoverable.” | 【一次】XFS journal/recovery model. |
| K16 | [Linux 6.18 exFAT documentation](https://docs.kernel.org/6.18/filesystems/exfat.html), [exfatprogs v1.4.3 `fsck.exfat`](https://github.com/exfatprogs/exfatprogs/blob/v1.4.3/manpages/fsck.exfat.8), [Linux 6.18 VFAT documentation](https://docs.kernel.org/6.18/filesystems/vfat.html) | “exfatprogs project provides userspace utilities for creating, checking, repairing” | 【一次】Linux driver and exfatprogs fsck tool availability. |
| K17 | [Linux 6.18 NILFS2 documentation](https://docs.kernel.org/6.18/filesystems/nilfs2.html) | “NILFS2 supports continuous snapshotting” | 【一次】log/checkpoint features; fsck support status as documented there. |
| K18 | [`rename(2)`](https://man7.org/linux/man-pages/man2/rename.2.html) | “If newpath already exists, it will be atomically replaced” | 【一次】rename の namespace atomicity。 |
| K19 | [`fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html) | “an explicit fsync() on a file descriptor for the directory is also needed” | 【一次】directory entry durability after file creation/rename. |
| P1 | [Android filesystem support](https://source.android.com/docs/core/architecture/android-kernel-file-system-support) | “Not all file systems are suitable for use on Android devices.” | 【一次】Android production support depends on OTA and privacy requirements. |
| P2 | [Android User Data Checkpoint](https://source.android.com/docs/core/ota/user-data-checkpoint) | “For the F2FS file system, UDC adds the checkpoint functionality” | 【一次】userdata rollback/checkpoint behavior. |
| P12 | [Android dm-verity](https://source.android.com/docs/security/features/verifiedboot/dm-verity) | “Android 4.4 and higher supports Verified Boot through the optional device-mapper-verity (dm-verity) kernel feature” | 【一次】integrity verification of system block devices. |
| P13 | [Android A/B system updates](https://source.android.com/docs/core/ota/ab) | “ensure a workable booting system remains on the disk during an over-the-air (OTA) update” | 【一次】legacy A/B update behavior; the page notes Virtual A/B replaced it in Android 10. |
| P14 | [Android Virtual A/B overview](https://source.android.com/docs/core/ota/virtual_ab) | “Virtual A/B is Android's main update mechanism.” | 【一次】snapshot-based update and merge model. |
| P3 | [ChromeOS disk format](https://chromium.googlesource.com/chromiumos/docs/+/HEAD/disk_format.md), [ChromeOS autoupdate](https://www.chromium.org/chromium-os/chromiumos-design-docs/automatic-updates/) | “stateful partition” | 【一次】root/stateful partition and update layout; log placement is not generalized here. |
| P4 | [Raspberry Pi read-only overlay guide](https://www.raspberrypi.com/documentation/computers/configuration.html#overlay-file-system) | “The Overlay File System makes the root filesystem read-only” | 【一次】raspi-config option; behavior depends on configured overlay. |
| P5 | [Yocto read-only root filesystem](https://docs.yoctoproject.org/dev-manual/read-only-rootfs.html) | “any attempt by a package to write to the root filesystem will result in an error” | 【一次】read-only-rootfs integration constraint. |
| P6 | [Buildroot rootfs customization](https://buildroot.org/downloads/manual/manual.html#customize-rootfs) | “There are two ways to customize the target filesystem” | 【一次】overlay and post-build mechanisms. |
| P7 | [RAUC reference](https://rauc.readthedocs.io/en/latest/reference.html) | “The data directory is located on a non-redundant filesystem” | 【一次】persistent update state. |
| P8 | [Mender rootfs/updates overview](https://docs.mender.io/overview/introduction) | “Mender uses A/B partitioning” | 【一次】rootfs update model; logs not specified. |
| P9 | [SWUpdate documentation](https://sbabic.github.io/swupdate/) | “SWUpdate is a software update for embedded systems” | 【一次】framework scope; data layout is product-specific. |
| P10 | [OSTree deployment documentation](https://ostreedev.github.io/ostree/deployment/) | “/var is shared between deployments” | 【一次】shared state across deployments. |
| P11 | [OpenWrt filesystem guide](https://oldwiki.archive.openwrt.org/doc/techref/filesystems) | “one read-only and the other writable”; “`/var` is a symlink to [tmpfs]” | 【二次・旧版】archived OpenWrt guide; not a claim about every current target. |
| S17-1 | [Linux 6.18 dm-log-writes documentation](https://docs.kernel.org/6.18/admin-guide/device-mapper/log-writes.html) | “replay the log until it sees a FUA request, run the fsck command” | 【一次】write log replay and repeated checks. |
| S17-2 | [xfstests dm-log-writes helper](https://github.com/torvalds/linux/blob/2b414a95/drivers/md/dm-log-writes.c) and [xfstests replay fix](https://github.com/chandanr/xfstests/commit/1475bdd1f7b6cd434a6e1f8439b2a8a21111942a) | “replay the log to check for fs consistency at all times”; “replay the log until the given mark” | 【一次】kernel target and xfstests replay integration. |
| S17-3 | [CrashMonkey](https://github.com/utsaslab/crashmonkey/blob/master/docs/CrashMonkey.md), [Ace](https://github.com/utsaslab/crashmonkey/blob/master/docs/Ace.md) | “exhaustively generates workloads within the defined bounds” | 【一次】bounded crash consistency testing; distinct from `dm-log-writes`. |
| S17-4 | [Linux 6.18 dm-flakey](https://docs.kernel.org/6.18/admin-guide/device-mapper/dm-flakey.html), [Linux 6.18 dm-delay](https://docs.kernel.org/6.18/admin-guide/device-mapper/delay.html) | “simulating failing devices”; “delays reads and/or writes and/or flushes” | 【一次】device mapper fault/delay controls. |
| S17-5 | [QEMU 11.1.2 blkdebug](https://qemu.readthedocs.io/en/v11.1.2/devel/testing/blkdebug.html), [QEMU 11.1.2 block throttling](https://raw.githubusercontent.com/qemu/qemu/v11.1.2/docs/throttle.txt), [QEMU 11.1.2 block cache modes](https://qemu.readthedocs.io/en/v11.1.2/system/qemu-block-drivers.html) | “rule-based error injection engine”; “bytes per second and operations per second”; cache `unsafe` ignores flushes | 【一次】QEMU 11.1.2 block backend behavior; no physical power-loss equivalence. |
| S17-6 | [QEMU 11.1.2 raspi SD host model](https://raw.githubusercontent.com/qemu/qemu/v11.1.2/hw/sd/bcm2835_sdhost.c), [QEMU 11.1.2 Raspberry Pi machine model](https://raw.githubusercontent.com/qemu/qemu/v11.1.2/hw/arm/raspi.c) | “We never really delay commands”; the machine “Create[s] and plug[s] in the SD cards” | 【一次】emulated controller/card connection and timing limitation. |
| S17-7 | [FEMU paper](https://www.usenix.org/system/files/conference/fast18/fast18-li.pdf), [MQSim paper](https://www.usenix.org/system/files/conference/fast18/fast18-tavakkol.pdf), [FlashSim paper](https://discos.sogang.ac.kr/file/2009/intl_conf/SIMUL_2009_YKim.pdf) | “software (QEMU-based) flash emulator”; “SSD simulators”; “simulator aimed at ... SSDs” | 【一次】research models for SSD/NAND; applicability to vendor-specific microSD FTL is limited【推測】. |
