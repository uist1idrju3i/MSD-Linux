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

前回の QMP `query-blockstats` は QEMU 6.2.0 の SD model の読み書き byte counter を計上せず、`rd_bytes` と `wr_bytes` の両方が0だったため、書き込み量の指標として無効だった。今回は mkfs 時に `-E lazy_itable_init=0,lazy_journal_init=0` を指定し、`/data` の mount と online grow の後に `mount -o remount,noinit_itable /data` を実行した。QEMU では remount が受理された。各 run は `sync` 後に field 7 を読み、10秒待って再読する validity gate を通し、idle delta が0のときだけ workload を開始した。20回すべて idle delta は0で、idle delta を各表行に記録した【実測】。workload 開始直前と最終 `sync` 後に field 7（sectors written）を読み、delta bytes を `(after - before) × 512` で算出した。これは guest 側の block-layer 書き込み量であり、カード内部の FTL 書き込みや NAND への物理書き込み量は含まない【実測】。raw counter と serial log は `/home/ubuntu/work/sweep/data-s3/measure-gated/{V0,V1,V2,V3}/run*/attempt1/serial.log` に保存した。

V1 と V2 は、step c の開始後 1〜10 秒の無作為な時点で QEMU を `SIGKILL` し、同じ SD image で再起動して検証した。V1 は20回中20回、V2 も20回中20回で、mount 後の `fsck.ext4 -n` は clean、100 file はすべて旧内容か新内容のいずれか 200 B を保持した。失敗はなかった【実測】。各試行の `firstboot.log` と `reboot.log` は `/home/ubuntu/work/sweep/data-s3/powercut/{V1,V2}/run{1,2,...,20}/` にある。

前回の3回測定では V1 の field 7 の開始値に大きなばらつきがあり、背景の ext4 lazy inode-table initialization が混入した可能性を再検証した。追加の V1 観測では noinit workaround を使わず、mount 時の field 7 が16、60秒後が17,016で、差は17,000 sectors（8,704,000 bytes）だった【実測】。この区間は `/data` mount から `msd-data-grow` の online resize を含む最初の60秒間であり、lazy-init thread 単独の書き込み量ではない。

新しい測定では V1 の中央値は7,618,560 bytes だった。V2 も7,618,560 bytesで、V1 に対する削減は0%であり、20%以上の条件を満たさなかった。V2 の電断試験は20回中20回成功したが、書き込み量の条件を満たさないため `inline_data` は採用しない。V3 も7,618,560 bytesで削減は0%となり、10%以上の条件を満たさないため `lazytime` も採用しない。採用規則に従い、4 KiB と `data=ordered` の V1 を維持する【実測】。V1 の初回60秒観測のログは `/home/ubuntu/work/sweep/data-s3/measure-gated/lazyinit-V1/serial.log` にある。

| FS | 電断・回復モデル | small files・書き込み量 | fsck、RAM、tool size、成熟度 | MSD/Linux での位置づけ |
|---|---|---|---|---|
| ext4 | Journal。data mode、barrier、fsync と clean shutdown に依存する。 | block slack と metadata overhead は workload 次第。write volume は測定対象。 | `e2fsck` あり。時間・kernel/RAM/tool size は未測定。広く使われる成熟度は【推測】。 | `/data` の第一候補。書き込み期間と mount/recovery を実測【候補】。 |
| F2FS | Log-structured。checkpoint と roll-forward recovery を使う。 | 小ファイル性能、GC/write amplification は media と workload 次第【推測】。 | `fsck.f2fs` あり。時間・RAM/tool size は未測定。組込み実績を対象機で確認【推測】。 | ext4 と同一 corpus で比較する候補。既定採用はしない。 |
| btrfs | CoW tree/transaction。 | CoW、metadata、snapshot は書き込み量と容量に影響し得る【推測】。 | `btrfs check` 等あり。所要時間・tool/kernel/RAM cost は未測定。 | 高機能 reference。SD の単一 `/data` では複雑性と性能を測る。 |

read-only が通常状態なら、filesystem 選択の主要な差は主に mount、fsck/recovery、および `/data` を `rw` にする短い窓の書き込み性能に現れる、という仮説を測る【推測】。`e2fsprogs`、`f2fs-tools`、`btrfs-progs` の rootfs/tool size と、fsck・mount の時間はこの repository では未測定であり、数値は提示しない。

## Linux 6.18 系 microSD 候補の比較

以下の性能・RAM・tool size の定性的比較は、kernel documentation の機能記述と形式上の特徴からの【推測】である。比較用 image、同じ SD card、同じ workload で測っていない値を既知の数値として扱わない。fsck の時間、tool size、kernel size は候補間で共通の測定条件がなく、すべて未測定とする。Linux 6.18 系の基準で、bcachefs は上流 kernel 本体から外れたため、別途導入しない限り対象 kernel に含まれない【一次: K12】。

| FS | 用途 | 電断時機構 | fsck の有無・時間 | 小ファイル効率 | write amplification | RAM / kernel size cost | tool size | 成熟度 | rootfs / `/data` / boot 適合性 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| SquashFS | 圧縮 read-only image | runtime write なし | 修復 fsck 不要。image 検査は build 時。 | 圧縮・fragment が小ファイル容量を抑える可能性【推測】 | runtime はなし。build image の block/fragment 設定を測る。 | decoder/config が kernel に加わる。cache RAM は workload 次第。 | runtime tool 不要。`mksquashfs`/`unsquashfs` は未測定。 | 高【推測】 | rootfs に適合。`/data` 不適、boot は firmware format 依存。 | **候補**。現行 rootfs。 |
| EROFS | 圧縮 read-only image | runtime write なし | repair fsck 不要。image validation は別途。 | compression/chunk 方式次第【推測】 | runtime はなし。 | decoder/config と page cache cost を測る。 | `erofs-utils` 未測定。 | 上流採用済みだが target test 不足【推測】 | rootfs reference。`/data` 不適、boot image format は別途。 | **reference**。SquashFS 比較対象。 |
| cramfs | 小型 read-only image | runtime write なし | fsck 不要。 | 制約ある format と compression に依存【推測】 | runtime はなし。 | kernel driver cost 未測定。 | image tools 未測定。 | 現代の組込み rootfs の第一選択とはしない【推測】 | rootfs reference。`/data` 不適。 | **reference**。既存 SquashFS/EROFS に優位を示す根拠なし。 |
| romfs | 小型 read-only/ROM image | runtime write なし | fsck 不要。 | header/alignment overhead が小さな file に影響【推測】。kernel docs は空 file minimum overhead 32 bytes と記載。 | runtime はなし。 | 小型用途を意図するが現 kernel build cost 未測定。 | image tool size 未測定。 | 用途が狭い【推測】 | rootfs/boot reference。SD `/data` 不適。 | **reference**。小型 ROM 用途と現在の rootfs 要件が異なる。 |
| ext2 | 汎用 writable block FS | journal なし。clean unmount 失敗時に全体 consistency check が必要になり得る【推測】。 | `e2fsck` あり。時間は未測定。 | block/inode overhead は format 条件次第。 | journal 不要だが電断後の全体修復コストを考慮【推測】。 | kernel/RAM cost 未測定。 | e2fsprogs 未測定。 | 成熟【推測】 | `/data` reference。boot は通常 FAT。 | **reference**。journal recovery を重視する用途では ext4 と比較。 |
| ext3 | 旧 ext3 on-disk format | metadata journaling。data mode と同期条件を確認。 | ext4 driver と `e2fsck` で扱う。時間は未測定。 | ext4 と同様、format/workload 依存。 | journal write を含む【推測】。 | 6.18 に独立した `EXT3_FS` はなく、ext4 driver の共用 cost。 | e2fsprogs 未測定。 | 成熟だが旧世代との位置づけ【推測】 | `/data` reference。boot は通常 FAT。 | **reference**。ext3 format 互換の確認用。 |
| ext4 | 汎用 writable block FS | journal と replay。 | `e2fsck` あり。時間未測定。`ro` mount でも replay し得る。 | block size、inline_data、directory metadata の影響を測る。 | journal、metadata、writeback 条件に依存【推測】。 | kernel/RAM cost 未測定。 | e2fsprogs 未測定。 | 成熟【推測】 | `/data` に適合。 | **候補**。現行実装の比較基準。 |
| F2FS | flash/block writable FS | log-structured、checkpoint、roll-forward recovery。 | `fsck.f2fs` あり。時間未測定。 | 小ファイル性能と GC 影響を計測【推測】。 | GC/metadata amplification が media/workload 依存【推測】。 | GC/cache RAM、kernel cost 未測定。 | f2fs-tools 未測定。 | upstream と利用実績はあるが target maturity は別途評価【推測】。 | `/data` candidate。boot/rootfs は read-only image を優先。 | **候補**。ext4 と電断・fsck・書き込みを比較。 |
| btrfs | CoW writable FS | CoW transaction、metadata tree。 | `btrfs check` 等あり。処理時間未測定。 | CoW/metadata overhead が小ファイルに影響し得る【推測】。 | CoW、metadata、snapshot 次第【推測】。 | kernel/RAM cost と tool size 未測定。 | btrfs-progs 未測定。 | 成熟した機能群だが運用複雑性を評価【推測】。 | `/data` reference。rootfs/boot の本用途には過剰な可能性。 | **reference**。比較ベースライン。 |
| XFS | 大容量向け journaled FS | Write-ahead log と metadata transaction。 | `xfs_repair` あり。時間未測定。 | directory/inode 条件と workload 次第【推測】。 | log/metadata overhead を含む【推測】。 | kernel/RAM cost 未測定。 | xfsprogs 未測定。 | 成熟【推測】 | 大容量 `/data` の reference。boot は不適。 | **reference**。小容量 SD で採用根拠が乏しい。 |
| NILFS2 | log-structured writable FS | log と checkpoint。 | kernel docs は通常の `fsck` 不在を記載。時間の共通測定なし。 | 小ファイル効率未測定。 | log/checkpoint に依存【推測】。 | kernel/RAM cost 未測定。 | nilfs-utils 未測定。 | 専門的用途【推測】 | `/data` reference、rootfs/boot 不適。 | **reference**。fsck/運用 tooling を先に確認。 |
| bcachefs | CoW writable FS | CoW/transaction を持つ設計。 | 本体から分離後の tool/support 状況は構成依存。時間未測定。 | 未測定。 | 未測定。 | 6.18 上流本体には不在。外部 module/tool cost 未測定。 | 未測定。 | version/upstream status 変化中【一次: K12】。 | 既定 kernel では rootfs/`/data`/boot に利用不可。 | **除外**。6.18 上流 kernel から外れている。 |
| exFAT | removable media 用 writable FS | kernel docs は replay journal を規定しない。更新途中の整合性を含めて電断試験する【推測】。 | `fsck.exfat` あり。時間未測定。 | cluster size と directory entries で小ファイル効率を測る。 | cluster allocation/metadata 条件次第【推測】。 | kernel/RAM cost 未測定。 | exfatprogs 未測定。 | removable media interoperability は高い【推測】。 | 外部データ媒体に適合。root `/data` と boot の POSIX 要件には不向き。 | **reference**。Windows 互換媒体用。 |
| vfat/FAT32 | firmware boot partition、交換媒体 | journal/CoW なしとして試験計画を立てる【推測】。 | `fsck.fat` あり。時間未測定。 | cluster size と小さな directory entry に依存。 | allocation table/metadata 更新を伴う【推測】。 | kernel/RAM cost 未測定。 | dosfstools 未測定。 | boot media として広く使われる【推測】。 | boot selector/p1 として適合。Unix `/data` は不適。 | **候補**。boot partition 用。 |
| JFFS2 | raw MTD flash writable FS | eraseblock を直接管理する log-structured FS。 | MTD 固有 recovery/tool。一般 fsck と時間は未測定。 | 圧縮と scan time が影響【推測】。 | wear leveling は raw flash を前提。 | MTD/scan RAM と kernel cost 未測定。 | mtd-utils 未測定。 | raw flash 用【一次】。 | managed-FTL SD には不適。 | **除外**。MTD device がない。 |
| UBIFS | UBI/MTD raw NAND writable FS | UBI と journal/log の回復設計。 | UBI/UBIFS mount recovery。汎用 fsck と所要時間は未測定。 | flash geometry と index/cache に依存【推測】。 | UBI wear leveling/eraseblock を前提。 | UBI/UBIFS RAM と kernel cost 未測定。 | mtd-utils 未測定。 | raw NAND 用の成熟候補【推測】。 | managed-FTL SD には不適。 | **除外**。MTD/UBI が隠れた SD FTL に置き換わらない。 |
| tmpfs | 一時的な RAM-backed FS | 電源断で内容消失。 | fsck 不要。回復時間なし。 | RAM/virtual memory と inode limit に依存。 | 通常は SD へ書かない。ただし swap があると退避し得る【一次: K13】。 | contents 使用量だけ RAM を消費し、上限設定が必要。 | runtime tool 不要。 | kernel 標準【推測】。 | `/run`、`/tmp`、設計後の `/var` に適合。persistent `/data` 不適。 | **候補**。上限と swap 方針を決める。 |
| ramfs | 制限の弱い RAM-backed FS | 電源断で内容消失。 | fsck 不要。 | 小規模な固定用途。 | persistent media write なし。 | 上限なしに増加し得て memory pressure/OOM risk がある。 | runtime tool 不要。 | kernel 内の基本機能【推測】。 | `/data` 不適。unbounded `/var` に使わない。 | **除外**。tmpfs の上限管理を優先。 |

raw NAND 用の JFFS2/UBIFS は MTD/eraseblock と UBI の管理モデルに依存する。microSD は controller 内の managed FTL が raw flash の bad block/wear management を隠し、OS には block device として見える。したがって JFFS2/UBIFS を microSD 上で使う案は除外し、電断試験では block device 上の ext4/F2FS 等を対象とする【一次: K14】。

表の filesystem 行と一次資料の対応は、SquashFS=[K6]、EROFS=[K7]、cramfs=[K8]、romfs=[K9]、ext2=[K10]、ext3/ext4=[K11]、ext4 read-only recovery=[K3]、F2FS=[K5]、btrfs/bcachefs=[K12]、XFS=[K15]、NILFS2=[K17]、exFAT/vfat=[K16]、JFFS2/UBIFS=[K14]、tmpfs/ramfs=[K13] である。

## 既存システムの設計例

下表は資料で確認できた rootfs、writable state、update、logs のみを記す。「資料に記載なし」は推測で補っていない。適用案は MSD/Linux 固有の【推測】である。

| 例 | rootfs | writable data | update | logs | MSD/Linux への適用 |
|---|---|---|---|---|---|
| Android | EROFS 等の read-only system image と dm-verity を使う構成がある。 | `/data` は端末ごとの設定で ext4/F2FS 等。F2FS の user data checkpoint と rollback docs がある。 | A/B OTA と Virtual A/B snapshot/merge。 | 今回取得した partition/update docs では log placement の一般則は記載なし。 | immutable system と data の分離、update rollback と `/data` migration を参考にする【一次: P1-P2、P12-P14】。 |
| ChromeOS | rootfs を read-only とし verified boot/verity で検証する設計。 | stateful partition にユーザー・端末状態。 | A/B rootfs update と active slot 切替。 | stateful partition と log handling の関係は資料の対象外。 | root integrity と stateful partition の分離は参考。MSD の selector p1 と raw A/B slot は独自設計のまま扱う【一次: P3】。 |
| Raspberry Pi OS | rootfs は SD 上にあり、raspi-config の Overlay File System option で overlay 化できる。 | OverlayFS の upper は RAM 上の揮発 state。 | overlay を外してから通常の package/image update を行う手順。今回の取得資料では update の完全な手順は記載なし。 | read-only overlay 時に root 側へ書く logs は再起動で失われ得る【推測】。公式資料は任意 temporary files に tmpfs を提案。 | volatile changes を採用する際、更新・保守 mode を明確に分ける【一次: P4】。 |
| Yocto | `read-only-rootfs` image feature は rootfs を read-only とし、root に書こうとする package/service は build 時に解決または外部領域へ移す。 | application-specific writable locations。一般の data partition 仕様は資料に固定されない。 | image/update system に依存。 | product config に依存。 | Buildroot image の read-only 化でも、boot 後に root に書く service を列挙して修正する【一次: P5】。 |
| Buildroot | rootfs overlay と post-build script で rootfs の内容・権限・mount 設定を作る。 | project が fstab/init script で定義する。Buildroot 自体は `/data` policy を決めない。 | product-specific。 | product-specific。 | 現行 `post-build.sh` と overlay を使い、read-only mount と runtime writer の両方を構成管理する【一次: P6】。 |
| RAUC | A/B slot の rootfs image を管理する組み込み update framework。 | `data-directory` は update で上書きされない non-redundant filesystem に置く。 | inactive slot に image を install し、bootloader integration で切替。 | framework の一般ログ保存場所は今回の文書で確認できず。 | `/data/msd-update` のような別 data partition に update state を置く設計を参考にする【一次: P7】。 |
| Mender | A/B rootfs partition を想定する。 | persistent data partition は rootfs update で保持する。 | inactive rootfs 更新、boot/commit で rollback を管理。 | log placement は参照した overview に記載なし。 | raw A/B slots と `/data` の役割を分離する考え方を参考にする【一次: P8】。 |
| SWUpdate | image/partition、file、script 等を project-specific に更新する枠組み。 | data preservation は partition layout、handler、script に依存。 | update strategy は target design で選ぶ。 | 一般配置を特定する資料は未確認。 | 自動的に data を保持すると仮定せず、slot/state transition を明示的に設計する【一次: P9】。 |
| OSTree | versioned deployment を複数保持し、deployment content を read-only として扱う。 | deployment 間で `/var` を共有し、state を分離する。 | 新 deployment を作成し boot entry を切り替え、旧 deployment へ戻せる。 | log の配置は product-specific。`/var` が共有されるため保存先候補にはなる【推測】。 | `/etc` の古い値が新 image を隠す問題を、versioned deployment/config migration として扱う【一次: P10】。 |
| OpenWrt | 旧公式 wiki は embedded flash 上の SquashFS read-only rootfs と writable JFFS2 overlay の組み合わせを説明する。 | NOR/NAND で JFFS2/UBIFS 等。`/tmp` は tmpfs、`/var` は `/tmp` symlink と記載。 | flash layout と target に依存。kernel は separate raw partition の場合もある。 | 同 wiki の構成例では `/var` が tmpfs 由来なので volatile。 | overlay と flash type の依存を参考にするが、MTD 用 filesystem を managed-FTL SD に移植しない【二次・旧版: P11】。 |

共通して参考にできるのは、immutable system image、明示的な persistent state area、inactive image update を別の責務として設計する点である。MSD/Linux では現在すでに SquashFS rootfs、raw A/B payload、p1 selector、`/data` update state が分離している。次の設計課題は `/data` writer の列挙、書き込み窓・同期・recovery の定義、`/data/etc` の古い設定が新 slot の既定値を隠す問題、`/var`/crash log の実際の mount である【推測】。

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
