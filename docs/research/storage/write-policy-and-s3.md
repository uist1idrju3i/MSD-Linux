# 書き込み経路・read-only policy案・S3

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

コードの書き込み経路、未実装のpolicy案、S3の条件と結果を分けて読んでください。現在は`/data`を通常運用中もread-onlyに保つ書き込み窓を実装していません。[現在のコードと限界](README.md#現在の実装とまだ確かめていないこと)と[権限の設計](../security/README.md)を先に確認します。

2026-11-13に[seed非保存と初回起動からのzram swap](../../experiments/2026-11-13-seedrng-zram.md)を実装しました。以下のseed保存を含む書き込み窓の案と保存経路の表は当時の調査として残し、現在の実装とは区別します。seed init・設定・directory作成は削除し、hwrngをbuilt-inで明示しました。品質や実機の保証とは別です。`/data`の具体的なrw・journal・commit値は未決定で、既存実験の適用範囲と[追加計画](../../design/write-policy.md#dataのmount方針を決めるための資料と追加計画)を台帳にまとめています。

生成`.config`の未取得などは、以下の調査を行った時点の確認範囲です。後の生成物を調べた範囲は[BSPの確認記録](../../experiments/2026-11-02-hardware-artifact-audit.md)へ分けています。K/P系列のURL・逐語抜粋・適用範囲は[共通出典](filesystem-sources.md)、候補比較は[filesystem候補](filesystem-candidates.md)、S17は[故障注入の計画](fault-injection-s17.md)です。

現行のmount・初期化・overlay・healthと、置換時に一緒に変える契約は[保存領域と実行時検証の比較](../alternatives/filesystems.md)にまとめています。以下の設計案や過去の資料を、現行実装や本機の実測に読み替えません。

2026-11-12のrootfs・init・生成configの棚卸しと判断待ちは[書き込みの台帳](../../design/write-policy.md)、起動後idleのpartition別counterは[今回の実験](../../experiments/2026-11-12-write-inventory.md)に記録します。通常imageのgenimageはinode tableとjournalをlazy初期化しませんが、起動時のonline resizeや空partitionのfallback formatは別の経路です。

この文書は、CardputerZero の現在の書き込み経路をコードで確認し、`/etc`・`/data` の read-only 化、ファイルシステム選択、障害試験を提案する。提案や未測定の性能評価は【推測】、コードや取得済み一次資料で確認した事項は【一次】、未確認事項は【未確認】と記す。ファイルシステム比較の範囲は Linux 6.18 系で microSD 用途に関係する、依頼指定の候補である。

## 現在のマウントと書き込み先

| 対象 | `origin/main` の状態 | 根拠 |
|---|---|---|
| `/` | SquashFS を `ro` でマウントする。 | `board/cardputerzero/rootfs-overlay/etc/fstab:5` |
| `/tmp`、`/run`、`/dev/shm` | fstab が tmpfs としてマウントする。 | `board/cardputerzero/rootfs-overlay/etc/fstab:3,6-7` |
| `/data` | ext4。新規 image と空領域の初期化は 4 KiB block。既存の 1 KiB filesystem は移行せずそのまま使う。mount option は `noauto,noatime,nodev,nosuid,data=ordered,errors=remount-ro`。`S02msd-data` が `fsck.ext4 -p`、mount、成長処理、状態 directory 作成を行う。 | `board/cardputerzero/genimage.cfg`、`board/cardputerzero/rootfs-overlay/etc/fstab:8`、`board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data` |
| `/etc` | `S03msd-etc-overlay` が `/data/etc:/etc` を lower、`/run/etc-overlay` を upper/work とする overlay を作り、merged view を `/etc` に bind mount する。 | `board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay:3-11` |
| seedrng | `SEEDRNG_ARGS="--seed-dir=/data/seedrng"`。seedrng の永続 seed は `/data` 配下に置かれる。 | `board/cardputerzero/rootfs-overlay/etc/default/seedrng:1`、`board/cardputerzero/post-build.sh:69-82` |
| update 状態と鍵 | updater の状態は `/data/msd-update`、公開鍵・key-origin・最低更新番号は `/usr/share/msd-update/` から読む。この場所は `/etc` overlay の対象外。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-update`、`board/cardputerzero/post-build.sh` |
| A/B payload と selector | rootfs は p5/p6、boot payload は p2/p3 の inactive raw partition に書く。状態記録は `/data/msd-update`、`autoboot.txt` の切替は p1 上で行う。A/B payload を `/data` に保存する方式ではない。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-update:56,170-179,220-231` |
| data partition grow | partition table の p4/p7 を調整し、`resize2fs` で p7 の ext4 を拡張する。 | `board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow:25,116-134` |
| hwinfo・ready marker | hwinfo cache は `/run/msd/hardware`、ready marker は `/run/msd-ready`。これらの書き込み先は揮発領域である。 | `board/cardputerzero/rootfs-overlay/etc/init.d/S97msd-hwinfo:3-9`、`board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready:3` |
| `/var` とログ | `/var` 自体の mount はない。skeleton では `/var/cache`、`/var/log`、`/var/spool`、`/var/tmp` が `/tmp` への symlink、`/var/lock`、`/var/run` が `/run` への symlink、`/var/lib/misc` が `/tmp` への symlink。2026-11-12の生成rootfsとQEMUではsyslogd・klogdが起動し、syslogdの既定log先はRAM上の `/var/log/messages`。 | fstab、Buildroot `system/skeleton/var`、生成S01syslogd・S02klogd、[台帳](../../design/write-policy.md) |
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

前回の QMP `query-blockstats` は QEMU 6.2.0 の SD model の読み書き byte counter を計上せず、`rd_bytes` と `wr_bytes` の両方が0だったため、書き込み量の指標として無効だった。今回は mkfs 時に `-E lazy_itable_init=0,lazy_journal_init=0` を指定し、`/data` の mount と online grow の後に `mount -o remount,noinit_itable /data` を実行した。QEMU では remount が受理された。各 run は `sync` 後に field 7 を読み、10秒待って再読する validity gate を通し、idle delta が0のときだけ workload を開始した。V0〜V5の30回すべて idle delta は0で、idle delta を各表行に記録した【実測】。workload 開始直前と最終 `sync` 後に field 7（sectors written）を読み、delta bytes を `(after - before) × 512` で算出した。これは guest 側の block-layer 書き込み量であり、カード内部の FTL 書き込みや NAND への物理書き込み量は含まない【実測】。raw counter は[同名の S3 実験記録](../../experiments/2026-10-19-s03-data-ext4-writes.md)の CSV に保存した。

V1 と V2 は、step c の開始後 1〜10 秒の無作為な時点で QEMU を `SIGKILL` し、同じ SD image で再起動して検証した。V1 は20回中20回、V2 も20回中20回で、mount 後の `fsck.ext4 -n` は clean、100 file はすべて旧内容か新内容のいずれか 200 B を保持した。失敗はなかった【実測】。試行ごとの delay と status は[電断 CSV](../../experiments/2026-10-19-s03-data-ext4-powercut.csv)に保存した。

前回の3回測定では V1 の field 7 の開始値に大きなばらつきがあり、背景の ext4 lazy inode-table initialization が混入した可能性を再検証した。追加の V1 観測では noinit workaround を使わず、mount 時の field 7 が16、60秒後が17,016で、差は17,000 sectors（8,704,000 bytes）だった【実測】。この区間は `/data` mount から `msd-data-grow` の online resize を含む最初の60秒間であり、lazy-init thread 単独の書き込み量ではない。

新しい測定では V1 の中央値は7,618,560 bytes だった。V2 も7,618,560 bytesで、V1 に対する削減は0%であり、20%以上の条件を満たさなかった。V2 の電断試験は20回中20回成功したが、書き込み量の条件を満たさないため `inline_data` は採用しない。V3 も7,618,560 bytesで削減は0%となり、10%以上の条件を満たさないため `lazytime` も採用しない。採用規則に従い、4 KiB と `data=ordered` の V1 を維持する【実測】。初回60秒観測の詳細は[実験記録](../../experiments/2026-10-19-s03-data-ext4-writes.md)に記録した。

追加した2×2では、`data=ordered` は `data=journal` より1 KiB時に12.1%、4 KiB時に14.0%少ない一方、4 KiBは同じ journal mode の1 KiBに対して3.43倍、ordered modeでは3.36倍の guest 書き込み量となり、この workload では block size の差が大きかった【実測】。V0の既存測定には `nodev,nosuid` がなく、V1/V4/V5にはあるが、これらの security mount option はこの通常ファイル workload の書き込みを変えない。

実カードでは、ATP の industrial microSD 資料が “4KB page management” と記載し、Cactus Technologies の資料は “NAND flash is programmed in pages” としたうえで、ページ寸法を “either 2KB or 4KB” と説明している【一次】([ATP microSD](https://www.melchionielectronics.com/media/f8/73/b0/1759225388/atp_microsd_card.pdf?ts=1760740424), [Cactus Technologies](https://www.cactus-tech.com/wp-content/uploads/2019/03/CTWP005-WriteAbort-v3.pdf))。カードによっては4 KiB以上の内部ページに対して1 KiBの書き込みが内部で増幅される可能性があるが、製品固有の FTL とページ寸法は guest から確認できないため、対象 SD card での実機確認が必要である【推測】。

| FS | 電断・回復モデル | small files・書き込み量 | fsck、RAM、tool size、成熟度 | MSD/Linux での位置づけ |
|---|---|---|---|---|
| ext4 | Journal。data mode、barrier、fsync と clean shutdown に依存する。 | block slack と metadata overhead は workload 次第。write volume は測定対象。 | `e2fsck` あり。時間・kernel/RAM/tool size は未測定。広く使われる成熟度は【推測】。 | `/data` の第一候補。書き込み期間と mount/recovery を実測【候補】。 |
| F2FS | Log-structured。checkpoint と roll-forward recovery を使う。 | 小ファイル性能、GC/write amplification は media と workload 次第【推測】。 | `fsck.f2fs` あり。時間・RAM/tool size は未測定。組込み実績を対象機で確認【推測】。 | ext4 と同一 corpus で比較する候補。既定採用はしない。 |
| btrfs | CoW tree/transaction。 | CoW、metadata、snapshot は書き込み量と容量に影響し得る【推測】。 | `btrfs check` 等あり。所要時間・tool/kernel/RAM cost は未測定。 | 高機能 reference。SD の単一 `/data` では複雑性と性能を測る。 |

read-only が通常状態なら、filesystem 選択の主要な差は主に mount、fsck/recovery、および `/data` を `rw` にする短い窓の書き込み性能に現れる、という仮説を測る【推測】。`e2fsprogs`、`f2fs-tools`、`btrfs-progs` の rootfs/tool size と、fsck・mount の時間はこの repository では未測定であり、数値は提示しない。

## ファイルシステムの候補と既存システムの例

Linux 6.18 系で microSD に使える候補の比較と、既存システムの設計例は、[ファイルシステムの候補と設計例](filesystem-candidates.md) に分けました。
