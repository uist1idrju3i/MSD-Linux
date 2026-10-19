# ストレージとフラッシュ境界

## 結論

現行の CI イメージは MBR で、p1～p7 の開始位置がすべて 4 KiB 境界からずれています。genimage v20 の `align = 4M` を使った実測では、拡張パーティションと論理パーティションを含む全開始位置が 4 MiB 境界にそろい、イメージは約 16 MiB 大きくなりました。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)／[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)

現時点では、`align = 4M` を別変更として実機評価へ進める案を推奨します。これは測定した候補のうち全開始位置がそろう設定であり、SD の速度、寿命、電断耐性が向上することを示すものではありません。実カードで比較してから採否を決めます。【推測】[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[実機測定計画](measurement-and-planning.md)

パーティションの整列と FAT のデータ領域の整列は別です。現行 boot-a の FAT データ領域はパーティション開始から 292 セクター（149,504 byte）後にあります。パーティション開始を 4 MiB にそろえても、この相対オフセットは変わりません。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)／[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)

## 用語と可視範囲

| 用語 | 本書での意味 | ホストから確認できる範囲 |
|---|---|---|
| 論理セクター | このイメージでパーティション表が使う 512 byte 単位。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) | `sfdisk` で開始セクターを読めます。 |
| ファイルシステムブロック | ext4 などが割り当てに使う単位。現行 CI artifact の `data.ext4` は `dumpe2fs` で 1,024 byte ブロックと確認しました。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) | ファイルシステム作成時の値は `dumpe2fs` などで読めます。 |
| ページ | カード内部の NAND やコントローラーが扱う書込み単位を指す一般語です。カード固有の実際のページ寸法は今回確認できていません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 | 通常のブロックデバイスから実ページを直接観測できるとは限りません。 |
| RU（Recording Unit） | SD 仕様上の記録単位。現行仕様の定義や AU との整列要件は取得できていません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 | 公開された Linux 属性から RU を直接確認できるとは限りません。 |
| AU（Allocation Unit） | SD Status にカードが報告する割当単位。Linux 6.18 系は AU_SIZE をデコードしますが、これは RU の定義や最適な書込み境界を確定するものではありません。【一次】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L53-L58) | カードが値を報告し、ドライバーが公開する場合に限り確認できます。 |
| 消去ブロック | カードが内部消去に使う単位。カード内部の FTL に隠れるため、ホスト側の論理セクター境界と同一とは限りません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 | `erase_size` などはカードが公開する値であり、NAND 内部の実装全体を示すとは限りません。 |
| FTL | 論理ブロックとフラッシュ媒体の物理配置を仲介するカード内部の変換層です。カード固有の動作や電断時の保証は今回確認できていません。【未確認】[電源・更新方式の調査](power-and-updates.md) | 通常のホストから内部マッピングを直接確認できません。 |

## 現行イメージの開始位置

下表は CI run 39178538327 の `sdcard.img` で測った開始セクターです。4 KiB は 8 セクター、4 MiB は 8,192 セクターに相当します。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

| エントリー | 開始セクター | 4 KiB 境界からの残り（セクター） | 4 MiB 境界からの残り（セクター） |
|---|---:|---:|---:|
| p1 | 1 | 1 | 1 |
| p2 | 32,769 | 1 | 1 |
| p3 | 163,841 | 1 | 1 |
| p4（拡張） | 294,913 | 1 | 1 |
| p5（論理） | 294,914 | 2 | 2 |
| p6（論理） | 819,203 | 3 | 3 |
| p7（論理） | 1,343,492 | 4 | 4 |

## genimage の整列とレイアウト比較

genimage v20 は `hdimage` の `align` を既定のパーティション整列として使い、自動配置の開始位置を指定境界まで切り上げます。明示 `offset` は自動整列と異なる扱いになるため、明示位置を使う場合は個別に整合性を確認します。【一次】[genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst)

| 案 | p1～p7 の開始セクター | 現行比のイメージ増分 | BCM2837 ファームウェア互換性リスク | 費用・課題 |
|---|---|---:|---|---|
| 現行（整列なし） | 1 / 32,769 / 163,841 / 294,913 / 294,914 / 819,203 / 1,343,492 | 基準 | 現行動作以外は評価対象外 | 変更なし。ただし開始位置が 4 KiB 境界にそろわない。【実測】 |
| `align = 1M` | 2,048 / 34,816 / 165,888 / 296,960 / 299,008 / 825,344 / 1,351,680 | 約 +4 MiB | 起動可否は実機未確認。配置変更だけで互換性を保証できない。【未確認】 | 約 4 MiB の容量増。p5/p6 は 4 MiB 境界にそろわない。【実測】 |
| `align = 4M` | 8,192 / 40,960 / 172,032 / 303,104 / 311,296 / 843,776 / 1,376,256 | 約 +16 MiB | 起動可否は実機未確認。配置変更だけで互換性を保証できない。【未確認】 | 約 16 MiB の容量増。全開始位置が 4 MiB 境界にそろう。【実測】 |
| GPT | このイメージでの測定なし | 未測定 | BCM2837 の起動互換性は未確認で、採用可能とは判断しない。【未確認】 | パーティション表と起動互換性の再設計・実機検証が必要。 |
| MBR のプライマリだけで再設計 | このイメージでの測定なし | 未測定 | MBR のエントリー制限を含む起動互換性は未確認。【未確認】 | 現行 7 エントリーをそのままプライマリ化できないため、領域統合など構成変更が必要。 |

`align = 4M` は測定した候補の中で全エントリーの開始位置が 4 MiB 境界にそろう設定です。「最適」と証明されたわけではありません。実機では、同じカード・カーネル・ファイルシステム・ワークロードを使い、起動、連続／小ブロック I/O、電断後の整合性を比較します。【推測】[実機測定計画](measurement-and-planning.md)

## FAT データ領域

現行 boot-a の FAT は 512 byte セクター、4 セクター／クラスタ、4 セクターの予約領域、各 128 セクターの FAT が 2 面、32 セクターのルートディレクトリーです。データ領域はパーティション先頭から 292 セクター（149,504 byte）後に始まります。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

現行 p2 の開始セクター 32,769 にこの相対オフセットを足すと、データ領域は 16,927,232 byte から始まり、4 MiB 境界から 150,016 byte ずれます。パーティション開始位置だけを整列しても、FAT BPB 内の予約領域・FAT 面・ディレクトリーの合計は変わらないため、データ領域の相対位置は直りません。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

FAT のクラスタ数や予約セクターを変更すれば整列する、といった推奨は、確認した仕様資料で裏付けられていません。現時点では根拠を確認できる修正方法を採用せず、SDA のファイルシステム仕様または formatter の文書を確認し、再フォーマット後の BPB を測る項目として残します。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認

## ext4 の `/data`

### ブロックサイズと作成条件

CI artifact の 64 MiB の `/data` ext4 は、`dumpe2fs` の `Block size: 1024` から 1,024 B と確認しました。これは生成後のファイルシステムを測った値であり、`genimage.cfg` の記述から読み取った値ではありません。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

`mke2fs.conf(5)` の `small` 使用型は `blocksize = 1024` を設定し、`mke2fs(8)` は `-b` を省略した場合のブロックサイズをファイルシステムの大きさと用途から決めると説明しています。現行 `genimage.cfg` は `use-mke2fs = "true"` と `size = 64M` を指定するだけで、使用型やブロックサイズを明示しません。したがって 1 KiB は小さいファイルシステム向けの mke2fs 設定と整合しますが、CI で実際に選ばれた設定ファイル・使用型までは記録されておらず、選択理由の特定は未確認です。【一次】【未確認】[mke2fs.conf(5)](https://man7.org/linux/man-pages/man5/mke2fs.conf.5.html)／[mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html)／[genimage.cfg](../../board/cardputerzero/genimage.cfg)

genimage v20 の `image-ext2.c` は `usage-type` が設定された場合だけ `-T` を加え、`extraargs` は `mke2fs` の呼出しへ渡します。現行 `genimage.cfg` に `usage-type` はありません。今回の host 1.46.5 で genimage と同じ主要引数を使った空の 64 MiB filesystem は 4 KiB block となり、`-T small` を付けてもローカル設定では 4 KiB でした（結果は `dumpe2fs-genimage-empty.txt` と `dumpe2fs-small-profile-control.txt`）。したがって upstream `small` profile だけでは CI の 1 KiB を説明できません。CI host の `mke2fs` 版、設定ファイル、実際の command line が未記録のため、原因は【未確認】です。【一次】【実測】【未確認】[genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[genimage v20 `image-ext2.c`](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c)／[genimage.cfg](../../board/cardputerzero/genimage.cfg)

1 KiB block は 4 KiB page より小さいため、`genimage` の ext4 `extraargs` に `-b 4096` を渡し、実行時の `S02msd-data` の `mkfs.ext4` にも `-b 4096` を指定する案があります。genimage v20 は `extraargs` を `mke2fs` に渡すため、両方を合わせれば image 作成時と初回起動時の blocksize を明示できます。page 境界との整合が改善する利点は【推測】で、起動時間、`fsck` 時間、容量、書込み量の差は本リポジトリでは試していません。【一次】【推測】[genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html)／[実行時 formatter](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)

現行イメージでは `/data` に `data=journal` を指定します。【一次】[現行 fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab)

ext4 の `data=journal` はファイルデータをジャーナルへ記録してから本体へ反映し、遅延割り当てと `O_DIRECT` を無効にします。現行の ext4 文書はこのモードを非推奨とし、2028 年 1 月の削除予定を記載しています。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=ordered` はファイルデータをメタデータのジャーナル確定より先に本体へ書きます。既定のコミット間隔は 5 秒で、`commit=` は間隔を変えますが、短くしても個々のアプリケーションの書込みが永続化された保証にはなりません。アプリケーション側の `fsync`、一時ファイルからの rename、ディレクトリーの `fsync` を含む更新手順を確認します。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

ext4 は既定で write barrier を有効にします。電断時の順序保証を弱める `nobarrier` は性能改善策として採用しません。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=journal` はファイルデータをジャーナルと最終配置の両方へ書くため、追加書込みや遅延割り当て無効化が生じる可能性があります。これは SD の摩耗を測定した結果ではありません。`data=ordered` を移行候補にする場合は、アプリケーションの同期・rename 手順と電断回復を確認します。【推測】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)／[電源・更新方式の調査](power-and-updates.md)

`mke2fs -E stride` は RAID の chunk／stripe geometry 向けに文書化されており、一般的な microSD の AU や消去単位を指定する設定としては使いません。【一次】[mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html)

SquashFS／EROFS の圧縮ブロックサイズと rootfs の比較は、既存の[ユーザー空間・セキュリティ調査](userspace-and-security.md)にも記載しています。

## 割り当て単位（クラスタ・ブロック）と小さいファイル

論理セクターはカードがホストへ提示する読み書き単位で、現行イメージのパーティション表は 512 byte セクターで構成されています。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) ファイルシステムの割り当て単位は別です。FAT／exFAT はクラスタ、ext4 はブロック単位で空き領域を割り当てます。カードの論理セクターが 512 byte であることだけでは、NAND のページ、消去単位、内部書込み粒度は分かりません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認

大きなクラスタやブロックは、割り当て情報の数や管理処理を減らし、連続した大きな読み書きで効率が上がる可能性があります。一方、小さいファイルほど末尾の未使用領域が増えます。SD カード内の書込み増幅や速度が必ず改善するとは言えず、効果はカード、負荷、ファイルシステム、実装に依存するため【推測】です。LWN が紹介した microSD 1 枚の測定では小さい書込みが遅く、整列した大きめの書込みが速い例がありますが、これはカード固有の二次情報であり、全カードの性質ではありません。【二次】[LWN flashbench 記事](https://lwn.net/Articles/428584/)

### 既定値と機能の版

| 項目 | 版・既定値 | 確認した内容 |
|---|---|---|
| e2fsprogs | 1.47.4（2026-03-06） | `[defaults]` は `blocksize=4096`、`inode_size=256`、`inode_ratio=16384`。`small` は 3–512 MiB、`floppy` は 3 MiB 未満という upstream maintainer の説明があり、両方の `blocksize` は 1024。`inode_size` はプロファイル内に指定がないため 256 を継承し、`inode_ratio` は `small=4096`、`floppy=8192`。この範囲は `mke2fs.conf` の定義ではなく upstream の説明です。【一次】[v1.47.4 の設定](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in)／[upstream issue #74](https://github.com/tytso/e2fsprogs/issues/74) |
| e2fsprogs の ext4 | 1.47.4 | `ext4` プロファイルの既定 feature に `orphan_file`、`metadata_csum_seed`、`64bit` などを含みます。`small` の blocksize／ratio は v1.46.5 と v1.47.4 の upstream 設定で同じであり、新版での変更は確認できませんでした。【一次】[v1.47.4 設定](https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in)／[v1.46.5 設定](https://github.com/tytso/e2fsprogs/blob/v1.46.5/misc/mke2fs.conf.in) |
| Buildroot の e2fsprogs | 2026.08 | package file は 1.47.4 を指定します。genimage v20 自体は `mke2fs` の版を固定せず、`PATH` から解決した実行ファイルを呼びます。今回のローカル測定ホストは e2fsprogs 1.46.5、CI artifact を生成した host `mke2fs` の版と設定ファイルは【未確認】です。【一次】[Buildroot 2026.08 package](https://github.com/buildroot/buildroot/blob/2026.08/package/e2fsprogs/e2fsprogs.mk)／[genimage v20 `image-ext2.c`](https://github.com/pengutronix/genimage/blob/v20/image-ext2.c) |
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

同一の決定的な 10,000 file × 100 byte（合計 1,000,000 byte）の tree を使いました。payload はファイルごとに異なる乱数列で、入力一覧と hash は `/home/ubuntu/work/research/measure/alloc/inputs/manifest-distinct.txt` と `sha256-distinct.txt` に保存しています。測定 host は mke2fs／e2fsck 1.46.5、mksquashfs 4.5 です。

| image | blocksize | inode size／数 | 使用 blocks | filesystem 内の使用量 | 補足 |
|---|---:|---:|---:|---:|---|
| ext4 明示 1 KiB | 1 KiB | 256 B／16,384 | 19,716 of 65,536 | 19.25 MiB | 1 KiB 比較用に追加測定 |
| ext4 default | 4 KiB | 256 B／16,384 | 12,115 of 16,384 | 47.31 MiB | ローカル host default |
| ext4 `-b 4096` | 4 KiB | 256 B／16,384 | 12,115 of 16,384 | 47.31 MiB | default と同じ |
| ext4 `-b 4096 -O inline_data` | 4 KiB | 256 B／16,384 | 2,113 of 16,384 | 8.25 MiB | sample file の `Blockcount: 0`、inline data 100 byte |

ext4 の使用量には 10,000 個の inode と directory、journal、bitmap 等の filesystem metadata も含まれます。したがって使用量差をそのままデータだけの slack とみなすことはできません。測定結果はこの入力 tree とローカル e2fsprogs のものです。【実測】dumpe2fs logs: `/home/ubuntu/work/research/measure/alloc/logs/dumpe2fs-{1k,default,4k,4k-inline}-distinct.txt`、sample: `debugfs-inline-sample.txt`、e2fsck: `e2fsck-4k-inline-distinct.txt`

同じ tree の SquashFS は default flags で 1,110,016 byte、`-no-fragments` で 1,122,304 byte でした。fragment 有効時の差は 12,288 byte ですが、これは mksquashfs 4.5 と一つの入力 tree の測定に限られます。【実測】log: `/home/ubuntu/work/research/measure/alloc/logs/squashfs-sizes-distinct.txt` 本リポジトリの rootfs で同じ節約が得られるか、実機の random read が変わるかは本リポジトリでは試していません。【未確認】

### 用途ごとの判断

- **SquashFS rootfs:** 小さい file の末尾を fragment にまとめる機能は有用な候補です。blocksize と fragment の設定は実際の rootfs image size、起動時の読み込み、CPU 使用量を測って選びます。他の project の比較結果は本リポジトリでは試していません。
- **FAT boot:** genimage の partition alignment と `mkfs.fat` 内部の data-area alignment は別々に記録します。`mkfs.fat` の既定 alignment は維持し、cluster を大きくする変更はカード別の測定なしに採用しません。
- **ext4 `/data`:** 4 KiB block は 4 KiB page と合わせる候補です。`inline_data` は多くの小さい file を持つ場合の追加候補ですが、対象 kernel／e2fsck の互換性と fsck 時間を確認します。`bigalloc` は cluster 全体が小さい file／directory の最小割り当て単位になるため、small-file workload への採用根拠はありません。
- **exFAT／SDXC:** exFAT の cluster はカード容量や formatter で変わり、Microsoft の仕様ページから推奨既定値を確定できません。SD Association の公開 formatter 案内を参考にしつつ、特定 AU への整列要件は【未確認】として実カードで確認します。

### 実機での比較手順

1. 同じカードで 1 KiB／4 KiB ext4 と `inline_data`、必要なら既定／指定 cluster の FAT／exFAT を作り、formatter の版、mount option、block／cluster size、partition と FAT data-area の offset を記録します。
2. 同一の file tree で作成・読込み・更新・削除を反復し、使用量、fsck 時間、連続 I/O、4 KiB random I/O、同期書込みの throughput と latency を測ります。
3. カード型番・容量・使用量・温度・電源条件を記録し、カードを替えて再測定します。`blockdev`／sysfs の論理・物理・最適 I/O サイズはカードが公開する値として記録し、内部 NAND の値とは扱いません。
4. 速度差だけで結論づけず、rootfs 起動時の I/O と `/data` の代表 workload、e2fsck、電断後の整合性を別々に確認します。SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認のため、仕様上の AU 整列を前提にしません。【推測】【未確認】[実機測定計画](measurement-and-planning.md)

## discard、fstrim、SD バス

Linux 6.18 系の SD コアは、カードが SD 5.1 以降で discard 機能を報告した場合に限って discard を選択します。カードが全て同じ機能を持つとは限らないため、`fstrim` の可否と効果は対象カード・ホストで確認します。【一次】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L291-L313)

SD Speed Class は規格条件下の最低連続アクセス性能であり、4 KiB ランダム IOPS の指標ではありません。Application Performance Class は 4 KiB コマンドの IOPS を数え、A2 の性能には A2 カードと A2 対応ホストの両方が必要です。【一次】[SD Association Speed Class](https://www.sdcard.org/developers/sd-standard-overview/speed-class/)／[Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/)

CM0 の正確な microSD ホスト接続、最大クロック、UHS 電圧切替、カードとファームウェアの組合せは今回確定していません。カードの A1/A2 表記だけでホストが同等の性能を出すとは判断せず、実機のカーネルログとカード属性を記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)

## 実機での測定手順

1. 同一の CM0、カード、ファームウェア、カーネル、ファイルシステム、電源条件で現行配置と `align = 4M` を比較します。最初にパーティション開始位置、FAT BPB、ext4 の作成条件を記録します。【推測】[実機測定計画](measurement-and-planning.md)
2. 起動時に `/sys/class/mmc_host/` と `/sys/bus/mmc/devices/` を列挙し、カード識別情報と読み取り可能な `erase_size`、`preferred_erase_size`、`ssr` 等を保存します。実際に存在する sysfs 属性だけを記録し、欠落値を推定で補いません。【一次】[Linux SD コアの sysfs 属性](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797)
3. `/sys/class/block/mmcblk*/queue/` の `logical_block_size`、`physical_block_size`、`minimum_io_size`、`optimal_io_size`、`alignment_offset`、`discard_granularity` など、実機で公開される属性を保存します。値の意味とドライバー実装が一致するかを確認し、存在しない属性は記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)
4. 連続読み書き、小ブロックのランダム読み書き、起動時間、温度・電圧をそれぞれ測定し、同じ条件で複数回実行します。flashbench は候補の調査手段ですが、このカード／ホストでの測定手順と妥当性は未確認です。【未確認】
5. SDA が公開する AU／RU 定義と formatter の手順を確認できるまでは、カードが報告した値から FAT の最適配置を推測しません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認
6. 1 KiB と 4 KiB の ext4 作成条件をそろえ、`fsck.ext4 -p` の時間、ファイルシステム容量、代表的な `/data` 書込み、電断後の整合性を比較します。【推測】[実行時 formatter](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)／[実機測定計画](measurement-and-planning.md)

## 電源断試験との関係

パーティション整列やファイルシステムのジャーナリングだけでは、カード内部 FTL の電断時の挙動を保証できません。試験では更新中・アイドル時の電断、起動不能数、ファイルシステム検査結果、A/B 復帰結果を記録します。QEMU は Linux の起動・パーティション認識・ファイルシステム回帰に使えますが、実カードの電源遮断や FTL の代替にはなりません。【推測】[電源・更新方式の調査](power-and-updates.md)／[実機測定計画](measurement-and-planning.md)

## 未確認事項

| 項目 | 次に必要な確認 |
|---|---|
| RU／AU の規範的定義、FAT の推奨境界、formatter の整列挙動 | SDA の仕様書または正規 formatter 文書を確認し、再フォーマット後の BPB と照合する。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 |
| CM0 のホストコントローラー、クロック、UHS 切替 | 対象基板のデバイスツリー、カーネルログ、実カードで確認する。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c) |
| `preferred_erase_size` 等の対象カード値と A1/A2 の実効性能 | 実機 sysfs と read-only のカード診断、同一条件の workload で測る。【未確認】[Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/) |
| `data=ordered` への変更がアプリケーションの更新要件を満たすか | `fsync`／rename と繰り返し電断を含む更新試験を行う。【未確認】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html) |
| 4 MiB 整列が実カードの速度・寿命・電断耐性に与える影響 | 現行配置との実機比較が必要。測定前に効果を断定しない。【未確認】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) |

## 出典と短い抜粋

| 主張 | URL | 原文の短い抜粋 | 確度 |
|---|---|---|---|
| CI image の現行 partition starts | [CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) | `p1=1, p2=32769, p3=163841, p4=294913, p5=294914, p6=819203, p7=1343492` | 【実測】 |
| genimage v20 が自動 offset を丸めること | [genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst) | “the final offset rounded up to the partition's `align` value” | 【一次】 |
| `align=1M` / `align=4M` 候補の partition starts と image size | [genimage v20 README](https://github.com/pengutronix/genimage/blob/v20/README.rst) | “partition's `align` value” — 数値は v20 に同じ filesystem payload を渡した本調査の実測 | 【実測】 |
| FAT data area が partition 内 292 sectors | [CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) | `Data area starts at byte 149504 (sector 292)` | 【実測】 |
| ext4 `data=journal` の書込み順序と非推奨 | [Linux ext4 documentation](https://docs.kernel.org/admin-guide/ext4.html) | “All data are committed into the journal prior to being written into the main file system.” / “removed in January 2028” | 【一次】 |
| `data=ordered` の書込み順序、barrier の既定 | [Linux ext4 documentation](https://docs.kernel.org/admin-guide/ext4.html) | “All data are forced directly out to the main file system prior to its metadata being committed to the journal.” / “ext4 enables write barriers by default” | 【一次】 |
| SD A2 の IOPS 単位 | [SD Association Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/) | “the number of 4KB read/write commands can be executed per second” | 【一次】 |
| Speed Class は連続 access 性能 | [SD Association Speed Class](https://www.sdcard.org/developers/sd-standard-overview/speed-class/) | “All speed class types assures minimum sequential card access performance” | 【一次】 |
| Linux MMC が `preferred_erase_size` を公開 | [Raspberry Pi Linux SD core](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797) | `MMC_DEV_ATTR(preferred_erase_size` | 【一次】 |
| `mke2fs -E stride` の用途 | [mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html) | “Configure the file system for a RAID array with stride-size file system blocks” | 【一次】 |
| flashbench が timing から内部挙動を推定する手法 | [LWN: flashbench](https://lwn.net/Articles/428584/) | “information ... had to be gathered using reverse engineering based on timing data” | 【二次】 |
