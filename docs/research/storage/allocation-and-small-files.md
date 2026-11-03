# 割当単位・ext4作成条件・小さいファイル

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

formatterの条件、割当単位と小さいファイルの測定を続けて読めるように保持しました。現在の新規data imageは[genimage.cfg](../../../board/cardputerzero/genimage.cfg)の`-b 4096`で作成します。既存カードの割当単位を変更した結果ではありません。

以下の測定は記録にある入力tree・ツール・ホスト条件に限られます。rootfsや実microSDでの同じ効果を確認したことにはしません。配置と用語・共通資料の一覧は[フラッシュ境界](layout-and-flash.md)を参照します。

## ext4 の `/data`

### ブロックサイズと作成条件

CI artifact の 64 MiB `/data` ext4 は `dumpe2fs` の `Block size: 1024` から 1,024 B と確認しました。CI build log には `mke2fs -t ext4 ... -L 'data' ... 65536k` とあり、`mke2fs 1.47.4 (6-Mar-2025)` と記録されています。呼び出しに `-b`、`-T` はありません。【実測】[CI run 39204900529](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529)

CI log は Buildroot host tool の `output/host/sbin/mke2fs` と `output/host/etc/mke2fs.conf` の install を記録します。Buildroot の `vendor/buildroot/Makefile:487` にある `BR_PATH` は `$(HOST_DIR)/bin:$(HOST_DIR)/sbin:$(PATH)` という検索順です。genimage の呼び出しも `mke2fs 1.47.4` と記録されるため、`data.ext4` を作った実行ファイルは Buildroot host の `output/host/sbin/mke2fs` と判断できます。genimage 設定に `mke2fs-conf` の指定はありません。e2fsprogs 1.47.4 の `misc/mke2fs.c:1311` は既定 path を `ROOT_SYSCONFDIR "/mke2fs.conf"` とし、CI log の host tool configure/install path は `output/host/etc` です。`MKE2FS_CONFIG` 環境変数による override は CI log で記録されていないため、実ファイルの open 自体は未観測ですが、既定 path から Buildroot host の `output/host/etc/mke2fs.conf` が選ばれたと判断できます。【一次】【推測】[CI run 39204900529](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529)／[Buildroot Makefile](https://github.com/buildroot/buildroot/blob/2026.08/Makefile#L487)／[e2fsprogs v1.47.4 `mke2fs.c`](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.c)／[genimage v20 `image-ext2.c`](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c)

Buildroot host `output/host/etc/mke2fs.conf` は `[defaults] blocksize = 4096` と、`[fs_types] small` の `blocksize = 1024`、`inode_ratio = 4096` を持ちます。e2fsprogs 1.47.4 の `misc/mke2fs.c:1489-1493` は `fs_blocks_count < 512 * meg` の場合に `small` を選ぶ実装です。64 MiB image はこの条件に該当し、明示的な `-b` もないため、`small` の 1 KiB block size が適用されます。workflow の裸の `mke2fs -V` は `mke2fs 1.47.2 (1-Jan-2025)` を表示しますが、これは genimage が使った Buildroot host binary のバージョンとは異なります。【一次】【実測】[e2fsprogs v1.47.4 `mke2fs.c`](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.c)／[e2fsprogs v1.47.4 `mke2fs.conf`](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in)／[CI run 39204900529](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529)

`genimage.cfg` の `extraargs = "-b 4096"` と `S02msd-data` の fallback formatter は新規 filesystem の block size を 4 KiB に固定します。genimage v20 の source は `cfg_getstr(image->imagesec, "extraargs")` で項目を読み、`mke2fs` に渡す実装です。既存デバイスの 1 KiB filesystem は再作成も移行もせず、新しい mount option で使い続けます。【一次】[genimage v20 `image-ext2.c`](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c#L67-L95)／[genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[実行時 formatter](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)

S3 変更後の mount option は `noatime,nodev,nosuid,data=ordered,errors=remount-ro` です。従来の `data=journal` は旧 filesystem で mount option に指定していた値です。【一次】[fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)

ext4 の `data=journal` はファイルデータをジャーナルへ記録してから本体へ反映し、遅延割り当てと `O_DIRECT` を無効にします。現行の ext4 文書はこのモードを非推奨とし、2028 年 1 月の削除予定を記載しています。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=ordered` はファイルデータをメタデータのジャーナル確定より先に本体へ書きます。既定のコミット間隔は 5 秒で、`commit=` は間隔を変えますが、短くしても個々のアプリケーションの書込みが永続化された保証にはなりません。アプリケーション側の `fsync`、一時ファイルからの rename、ディレクトリーの `fsync` を含む更新手順を確認します。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

ext4 は既定で write barrier を有効にします。電断時の順序保証を弱める `nobarrier` は性能改善策として採用しません。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=journal` はファイルデータをジャーナルと最終配置の両方へ書くため、追加書込みや遅延割り当て無効化が生じる可能性があります。これは SD の摩耗を測定した結果ではありません。現行の `S02msd-data` と `fstab` は `/data` に `data=ordered` を指定しています。アプリケーションの同期・rename 手順と実機での電断回復は未確認です。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)／[S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)／[fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab)

`mke2fs -E stride` は RAID の chunk／stripe geometry 向けに文書化されており、一般的な microSD の AU や消去単位を指定する設定としては使いません。【一次】[mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html)

SquashFS／EROFS の圧縮ブロックサイズと rootfs の比較は、既存の[ユーザー空間・セキュリティ調査](../userspace/README.md)にも記載しています。

## 割り当て単位（クラスタ・ブロック）と小さいファイル

論理セクターはカードがホストへ提示する読み書き単位で、現行イメージのパーティション表は 512 byte セクターで構成されています。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) ファイルシステムの割り当て単位は別です。FAT／exFAT はクラスタ、ext4 はブロック単位で空き領域を割り当てます。カードの論理セクターが 512 byte であることだけでは、NAND のページ、消去単位、内部書込み粒度は分かりません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認

大きなクラスタやブロックは、割り当て情報の数や管理処理を減らし、連続した大きな読み書きで効率が上がる可能性があります。一方、小さいファイルほど末尾の未使用領域が増えます。SD カード内の書込み増幅や速度が必ず改善するとは言えず、効果はカード、負荷、ファイルシステム、実装に依存するため【推測】です。LWN が紹介した microSD 1 枚の測定では小さい書込みが遅く、整列した大きめの書込みが速い例がありますが、これはカード固有の二次情報であり、全カードの性質ではありません。【二次】[LWN flashbench 記事](https://lwn.net/Articles/428584/)

### 既定値と機能のバージョン

| 項目 | 版・既定値 | 確認した内容 |
|---|---|---|
| e2fsprogs | 1.47.4（2026-03-06） | `[defaults]` は `blocksize=4096`、`inode_size=256`、`inode_ratio=16384`。`small` は 3–512 MiB、`floppy` は 3 MiB 未満という upstream maintainer の説明があり、両方の `blocksize` は 1024。`inode_size` はプロファイル内に指定がないため 256 を継承し、`inode_ratio` は `small=4096`、`floppy=8192`。この範囲は `mke2fs.conf` の定義ではなく upstream の説明です。【一次】[v1.47.4 の設定](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in)／[upstream issue #74](https://github.com/tytso/e2fsprogs/issues/74) |
| e2fsprogs の ext4 | 1.47.4 | `ext4` プロファイルの既定 feature に `orphan_file`、`metadata_csum_seed`、`64bit` などを含みます。`small` の blocksize／ratio は v1.46.5 と v1.47.4 の upstream 設定で同じであり、新版での変更は確認できませんでした。【一次】[v1.47.4 設定](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in)／[v1.46.5 設定](https://github.com/tytso/e2fsprogs/blob/v1.46.5/misc/mke2fs.conf.in) |
| Buildroot の e2fsprogs | 2026.08／1.47.4 | package は 1.47.4 を指定します。CI log は genimage が実行した `mke2fs` を 1.47.4 と記録し、host tool と config の install 先をそれぞれ `output/host/sbin/mke2fs`、`output/host/etc/mke2fs.conf` と記録しています。workflow の裸の `mke2fs -V` は system binary 1.47.2 です。genimage v20 は `PATH` から `mke2fs` を解決し、Buildroot は host の `bin` と `sbin` を前置します。【一次】【実測】[Buildroot 2026.08 package](https://github.com/buildroot/buildroot/blob/2026.08/package/e2fsprogs/e2fsprogs.mk)／[genimage v20 `image-ext2.c`](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c)／[CI run 39204900529](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529) |
| ext4 の blocksize | docs.kernel.org 現行ページ（2026-10-19 取得。kernel tag はページ上で未確認） | 1 KiB–64 KiB を使え、一般的には 4 KiB です。blocksize がカーネルの page size より大きい構成では mount 上の制約が生じます。【一次】【未確認】[ext4 documentation](https://docs.kernel.org/filesystems/ext4/) |
| ext4 `inline_data` | e2fsprogs 1.43 以降 | ext4 の inode 内に短いファイル内容を持てます。文書は `i_block` 内の 60 byte と、256-byte inode で条件により約 160 byte まで保持できる例を示します。xattr と同じ inode 空間を使うため上限は条件に依存します。e2fsprogs 1.43 の release notes は inline data support を追加機能として記録し、ローカル e2fsck 1.46.5 で本測定 image の検査も通りました。【一次】【実測】[ext4 inline data](https://docs.kernel.org/filesystems/ext4/inline.html)／[e2fsprogs v1.43 release notes](https://github.com/tytso/e2fsprogs/blob/v1.43/RELEASE-NOTES) |
| dosfstools | 4.2（2021-01-31） | `mkfs.fat` は既定でファイルシステムの大きさに応じて FAT 型・クラスタ数を選びます。FAT32 の初期クラスタ選択は 260 MiB 以下 512 byte、8 GiB 以下 4 KiB、16 GiB 以下 8 KiB、32 GiB 以下 16 KiB、64 GiB 以下 32 KiB、それより大きい場合 64 KiB です。FAT12／16 は 2 KiB から始め、クラスタ数上限に合わせて調整します。【一次】[v4.2 `mkfs.fat.c`](https://github.com/dosfstools/dosfstools/blob/v4.2/src/mkfs.fat.c)／[v4.2 NEWS](https://github.com/dosfstools/dosfstools/blob/v4.2/NEWS) |
| genimage の vfat | v20 | vfat handler は設定された `mkdosfs` を呼び、`extraargs` を渡します。`-s` は sectors-per-cluster、`-S` は logical-sector size、`-a` は既定のクラスタ境界整列を無効にし、`--offset` は image 内の開始 sector を指定します。`mkfs.fat` は通常、小さすぎる filesystem を除き、FAT 等の内部構造を cluster 境界に整列します。パーティション開始位置と内部のデータ領域整列は別です。【一次】[genimage v20 `image-vfat.c`](https://github.com/pengutronix/genimage/blob/v20/image-vfat.c)／[dosfstools 4.2 man page](https://man.cgr.dev/os/dosfstools/4.2-r46/man8/mkfs.fat.8.md) |
| Microsoft exFAT specification | 現行公開仕様ページ | 最大 32 MiB の cluster を定義しますが、formatter の既定 cluster-size 表は見つかりませんでした。【一次】【未確認】[Microsoft exFAT specification](https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification) |
| SD Association | 公開 FAQ／Formatter 説明 | 公開案内は容量に応じた FAT／exFAT の選択と、内部 flash 境界を考慮した partition／FAT／cluster heap の整列に触れます。一般的な AU 値や全カード共通の境界寸法は確認できていません。Part 1 仕様 PDF は HTTP 403 のため、内容を根拠にしていません。【一次】【未確認】[Formatter FAQ](https://www.sdcard.org/downloads/formatter/faq/)／[Formatter の解説](https://www.sdcard.org/press/thoughtleadership/the-sd-memory-card-formatterhow-this-handy-tool-solves-your-memory-card-formatting-needs/) |
| exfatprogs | 1.4.3（2026-08-14） | `mkfs.exfat` の既定 cluster は 7 MiB 未満 512 byte、256 MiB 以下 4 KiB、32 GiB 以下 32 KiB、それを超える場合 128 KiB。`--boundary-align` は FAT と cluster heap の境界整列を設定し、既定値は 1 MiB です。【一次】[v1.4.3 release](https://github.com/exfatprogs/exfatprogs/releases/tag/1.4.3)／[v1.4.3 `libexfat.c`](https://github.com/exfatprogs/exfatprogs/blob/1.4.3/lib/libexfat.c)／[`mkfs.exfat(8)`](https://github.com/exfatprogs/exfatprogs/blob/1.4.3/man/mkfs.exfat.8.in) |
| SquashFS tools | 4.7.5（2026-03-01） | `-b` は 4 KiB–1 MiB。fragment はファイル末尾をまとめ、`-no-fragments` は無効化、`-always-use-fragments` は小さいファイルの fragment 化を強制します。圧縮 block が大きい場合、random read 時に余分な圧縮データを読む可能性があります。【一次】【推測】[4.7.5 release](https://github.com/plougher/squashfs-tools/releases/tag/4.7.5)／[SquashFS tools documentation](https://github.com/plougher/squashfs-tools/blob/4.7.5/README.md) |
| EROFS tools | 1.9.4（2026-08-19） | tail packing、fragment、`ztailpacking`、重複排除を扱います。mkfs の `-b` 既定値は page size で、4 KiB page のシステムでは 4 KiB が標準候補です。大きな圧縮単位と random read の交換条件は本リポジトリでは試していません。【一次】【推測】[v1.9.4 ChangeLog](https://github.com/erofs/erofs-utils/blob/v1.9.4/ChangeLog)／[EROFS mkfs docs](https://erofs.docs.kernel.org/en/latest/mkfs.html) |
| F2FS | docs.kernel.org 現行ページ（2026-10-19 取得。kernel tag はページ上で未確認） | inline data と inline directory entry を使い、小さい file／directory 情報を inode に収めます。filesystem block は 4 KiB です。【一次】【未確認】[F2FS documentation](https://docs.kernel.org/filesystems/f2fs.html) |

### 小さいファイルのローカル測定

同一の決定的な 10,000 file × 100 byte（合計 1,000,000 byte）の tree を使いました。payload はファイルごとに異なる乱数列で、入力一覧と hash は当時のローカル計測 log に保存しましたが、リポジトリには含めていません。測定 host は mke2fs／e2fsck 1.46.5、mksquashfs 4.5 です。

| image | blocksize | inode size／数 | 使用 blocks | filesystem 内の使用量 | 補足 |
|---|---:|---:|---:|---:|---|
| ext4 明示 1 KiB | 1 KiB | 256 B／16,384 | 19,716 of 65,536 | 19.25 MiB | 1 KiB 比較用に追加測定 |
| ext4 default | 4 KiB | 256 B／16,384 | 12,115 of 16,384 | 47.31 MiB | ローカル host default |
| ext4 `-b 4096` | 4 KiB | 256 B／16,384 | 12,115 of 16,384 | 47.31 MiB | default と同じ |
| ext4 `-b 4096 -O inline_data` | 4 KiB | 256 B／16,384 | 2,113 of 16,384 | 8.25 MiB | sample file の `Blockcount: 0`、inline data 100 byte |

ext4 の使用量には 10,000 個の inode と directory、journal、bitmap 等の filesystem metadata も含まれます。したがって使用量差をそのままデータだけの slack とみなすことはできません。測定結果はこの入力 tree とローカル e2fsprogs のものです。【実測】dumpe2fs logs は `dumpe2fs-{1k,default,4k,4k-inline}-distinct.txt`、sample は `debugfs-inline-sample.txt`、e2fsck log は `e2fsck-4k-inline-distinct.txt` です。いずれもリポジトリ外です。

同じ tree の SquashFS は default flags で 1,110,016 byte、`-no-fragments` で 1,122,304 byte でした。fragment 有効時の差は 12,288 byte ですが、これは mksquashfs 4.5 と一つの入力 tree の測定に限られます。【実測】log `squashfs-sizes-distinct.txt` はリポジトリ外です。本リポジトリの rootfs で同じ節約が得られるか、実機の random read が変わるかは本リポジトリでは試していません。【未確認】

### 用途ごとの判断

- **SquashFS rootfs:** 小さい file の末尾を fragment にまとめる機能は有用な候補です。blocksize と fragment の設定は実際の rootfs image size、起動時の読み込み、CPU 使用量を測って選びます。他の project の比較結果は本リポジトリでは試していません。
- **FAT boot:** genimage の partition alignment と `mkfs.fat` 内部の data-area alignment は別々に記録します。`mkfs.fat` の既定 alignment は維持し、cluster を大きくする変更はカード別の測定なしに採用しません。
- **ext4 `/data`:** 4 KiB block は 4 KiB page と合わせる候補です。`inline_data` は多くの小さい file を持つ場合の追加候補ですが、対象 kernel／e2fsck の互換性と fsck 時間を確認します。`bigalloc` は cluster 全体が小さい file／directory の最小割り当て単位になるため、small-file workload への採用根拠はありません。
- **exFAT／SDXC:** exFAT の cluster はカード容量や formatter で変わり、Microsoft の仕様ページから推奨既定値を確定できません。SD Association の公開 formatter 案内を参考にしつつ、特定 AU への整列要件は【未確認】として実カードで確認します。

### 実機での比較手順

1. 同じカードで 1 KiB／4 KiB ext4 と `inline_data`、必要なら既定／指定 cluster の FAT／exFAT を作り、formatter のバージョン、mount option、block／cluster size、partition と FAT data-area の offset を記録します。
2. 同一の file tree で作成・読込み・更新・削除を反復し、使用量、fsck 時間、連続 I/O、4 KiB random I/O、同期書込みの throughput と latency を測ります。
3. カード型番・容量・使用量・温度・電源条件を記録し、カードを替えて再測定します。`blockdev`／sysfs の論理・物理・最適 I/O サイズはカードが公開する値として記録し、内部 NAND の値とは扱いません。
4. 速度差だけで結論づけず、rootfs 起動時の I/O と `/data` の代表 workload、e2fsck、電断後の整合性を別々に確認します。SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認のため、仕様上の AU 整列を前提にしません。【推測】【未確認】[実機測定計画](../verification/hardware-measurements.md)
