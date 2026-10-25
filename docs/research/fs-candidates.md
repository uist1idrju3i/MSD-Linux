# ファイルシステムの候補と設計例

[読み取り専用データ領域とファイルシステム比較](readonly-data-and-fs.md) から分けた節です。【一次: K12】のような出典の ID は、元の文書の[出典、抜粋、信頼度](readonly-data-and-fs.md#出典抜粋信頼度)の表を指します。

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

