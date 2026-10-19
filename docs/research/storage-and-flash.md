# ストレージとフラッシュ境界

## 結論

現行の CI イメージは MBR で、p1～p7 の開始位置がすべて 4 KiB 境界からずれています。genimage v20 の `align = 4M` を使った実測では、拡張パーティションと論理パーティションを含む全開始位置が 4 MiB 境界にそろい、イメージは約 16 MiB 大きくなりました。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)／[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)

現時点では、`align = 4M` を別変更として実機評価へ進める案を推奨します。これは測定した候補のうち全開始位置がそろう設定であり、SD の速度、寿命、電断耐性が向上することを示すものではありません。実カードで比較してから採否を決めます。【推測】[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[実機測定計画](measurement-and-planning.md)

パーティションの整列と FAT のデータ領域の整列は別です。現行 boot-a の FAT データ領域はパーティション開始から 292 セクター（149,504 byte）後にあります。パーティション開始を 4 MiB にそろえても、この相対オフセットは変わりません。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)／[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)

## 用語と可視範囲

| 用語 | 本書での意味 | ホストから確認できる範囲 |
|---|---|---|
| 論理セクター | このイメージでパーティション表が使う 512 byte 単位。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) | `sfdisk` で開始セクターを読めます。 |
| ファイルシステムブロック | ext4 などが割り当てに使う単位。現行 `data.ext4` は 1,024 byte ブロックです。【実測】[Buildroot のイメージ構成](../../board/cardputerzero/genimage.cfg) | ファイルシステム作成時の値は `dumpe2fs` などで読めます。 |
| ページ | カード内部の NAND やコントローラーが扱う書込み単位を指す一般語です。カード固有の実際のページ寸法は今回確認できていません。【未確認】[SD Association の仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1) | 通常のブロックデバイスから実ページを直接観測できるとは限りません。 |
| RU（Recording Unit） | SD 仕様上の記録単位。現行仕様の定義や AU との整列要件は取得できていません。【未確認】[SD Association の仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1) | 公開された Linux 属性から RU を直接確認できるとは限りません。 |
| AU（Allocation Unit） | SD Status にカードが報告する割当単位。Linux 6.18 系は AU_SIZE をデコードしますが、これは RU の定義や最適な書込み境界を確定するものではありません。【一次】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L53-L58) | カードが値を報告し、ドライバーが公開する場合に限り確認できます。 |
| 消去ブロック | カードが内部消去に使う単位。カード内部の FTL に隠れるため、ホスト側の論理セクター境界と同一とは限りません。【未確認】[SD Association の仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1) | `erase_size` などはカードが公開する値であり、NAND 内部の実装全体を示すとは限りません。 |
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

FAT のクラスタ数や予約セクターを変更すれば整列する、といった推奨は、確認した仕様資料で裏付けられていません。現時点では根拠を確認できる修正方法を採用せず、SDA のファイルシステム仕様または formatter の文書を確認し、再フォーマット後の BPB を測る項目として残します。【未確認】[SD Association の仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1)

## ext4 の `/data`

現行イメージでは `/data` に `data=journal` を指定します。【一次】[現行 fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab)

ext4 の `data=journal` はファイルデータをジャーナルへ記録してから本体へ反映し、遅延割り当てと `O_DIRECT` を無効にします。現行の ext4 文書はこのモードを非推奨とし、2028 年 1 月の削除予定を記載しています。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=ordered` はファイルデータをメタデータのジャーナル確定より先に本体へ書きます。既定のコミット間隔は 5 秒で、`commit=` は間隔を変えますが、短くしても個々のアプリケーションの書込みが永続化された保証にはなりません。アプリケーション側の `fsync`、一時ファイルからの rename、ディレクトリーの `fsync` を含む更新手順を確認します。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

ext4 は既定で write barrier を有効にします。電断時の順序保証を弱める `nobarrier` は性能改善策として採用しません。【一次】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)

`data=journal` はファイルデータをジャーナルと最終配置の両方へ書くため、追加書込みや遅延割り当て無効化が生じる可能性があります。これは SD の摩耗を測定した結果ではありません。`data=ordered` を移行候補にする場合は、アプリケーションの同期・rename 手順と電断回復を確認します。【推測】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html)／[電源・更新方式の調査](power-and-updates.md)

`mke2fs -E stride` は RAID の chunk／stripe geometry 向けに文書化されており、一般的な microSD の AU や消去単位を指定する設定としては使いません。【一次】[mke2fs(8)](https://man7.org/linux/man-pages/man8/mke2fs.8.html)

SquashFS／EROFS の圧縮ブロックサイズと rootfs の比較は、既存の[電源・更新方式の調査](power-and-updates.md)に記載しています。ここでは重複を避け、ストレージ配置と書込み境界に絞ります。

## discard、fstrim、SD バス

Linux 6.18 系の SD コアは、カードが SD 5.1 以降で discard 機能を報告した場合に限って discard を選択します。カードが全て同じ機能を持つとは限らないため、`fstrim` の可否と効果は対象カード・ホストで確認します。【一次】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L291-L313)

SD Speed Class は規格条件下の最低連続アクセス性能であり、4 KiB ランダム IOPS の指標ではありません。Application Performance Class は 4 KiB コマンドの IOPS を数え、A2 の性能には A2 カードと A2 対応ホストの両方が必要です。【一次】[SD Association Speed Class](https://www.sdcard.org/developers/sd-standard-overview/speed-class/)／[Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/)

CM0 の正確な microSD ホスト接続、最大クロック、UHS 電圧切替、カードとファームウェアの組合せは今回確定していません。カードの A1/A2 表記だけでホストが同等の性能を出すとは判断せず、実機のカーネルログとカード属性を記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)

## 実機での測定手順

1. 同一の CM0、カード、ファームウェア、カーネル、ファイルシステム、電源条件で現行配置と `align = 4M` を比較します。最初にパーティション開始位置、FAT BPB、ext4 の作成条件を記録します。【推測】[実機測定計画](measurement-and-planning.md)
2. 起動時に `/sys/class/mmc_host/` と `/sys/bus/mmc/devices/` を列挙し、カード識別情報と読み取り可能な `erase_size`、`preferred_erase_size`、`ssr` 等を保存します。実際に存在する sysfs 属性だけを記録し、欠落値を推定で補いません。【一次】[Linux SD コアの sysfs 属性](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797)
3. `/sys/class/block/mmcblk*/queue/` の `logical_block_size`、`physical_block_size`、`minimum_io_size`、`optimal_io_size`、`alignment_offset`、`discard_granularity` など、実機で公開される属性を保存します。値の意味とドライバー実装が一致するかを確認し、存在しない属性は記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)
4. 連続読み書き、小ブロックのランダム読み書き、起動時間、温度・電圧をそれぞれ測定し、同じ条件で複数回実行します。flashbench は候補の調査手段ですが、このカード／ホストでの測定手順と妥当性は未確認です。【未確認】
5. SDA が公開する AU／RU 定義と formatter の手順を確認できるまでは、カードが報告した値から FAT の最適配置を推測しません。【未確認】[SD Association の仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1)

## 電源断試験との関係

パーティション整列やファイルシステムのジャーナリングだけでは、カード内部 FTL の電断時の挙動を保証できません。試験では更新中・アイドル時の電断、起動不能数、ファイルシステム検査結果、A/B 復帰結果を記録します。QEMU は Linux の起動・パーティション認識・ファイルシステム回帰に使えますが、実カードの電源遮断や FTL の代替にはなりません。【推測】[電源・更新方式の調査](power-and-updates.md)／[実機測定計画](measurement-and-planning.md)

## 未確認事項

| 項目 | 次に必要な確認 |
|---|---|
| RU／AU の規範的定義、FAT の推奨境界、formatter の整列挙動 | SDA の仕様書または正規 formatter 文書を確認し、再フォーマット後の BPB と照合する。【未確認】[SDA 仕様書](https://www.sdcard.org/downloads/pls/pdf/?p=Part1_Physical_Layer_Simplified_Specification_Ver9.10.jpg&f=Part1PhysicalLayerSimplifiedSpecificationVer9.10Fin_20231201.pdf&e=EN_SS9_1) |
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
