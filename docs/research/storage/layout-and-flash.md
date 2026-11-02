# イメージの配置とフラッシュ境界

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

以下は配置・整列を調べたときの本文です。「現行（整列なし）」と開始セクター32,769は、表が引用するCI imageの値として保持しています。現在の`align = 4M`とは時点を分けます。[現在の配置と限界](README.md#現在の実装とまだ確かめていないこと)を先に確認してください。

割当単位は[ext4と小さいファイル](allocation-and-small-files.md)、カードで測る条件は[媒体と測定](media-measurements.md)に分けました。末尾の出典表は、分割前の配置・割当・媒体の調査で使った資料です。各本文中のURLと併せて参照します。

## 結論

#19 より前の CI イメージは MBR で、p1～p7 の開始位置がすべて 4 KiB 境界からずれていました。genimage v20 の `align = 4M` を使った実測では、拡張パーティションと論理パーティションを含む全開始位置が 4 MiB 境界にそろい、イメージは約 16 MiB 大きくなりました。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)／[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)

現時点では、`align = 4M` を別変更として実機評価へ進める案を推奨します。これは測定した候補のうち全開始位置がそろう設定であり、SD の速度、寿命、電断耐性が向上することを示すものではありません。実カードで比較してから採否を決めます。【推測】その後 #19 で `align = 4M` を `genimage.cfg` に入れ、`check-image-layout.sh` が CI で全開始位置の 8192 sector 境界を検査しています。実カードでの比較は未実施です。[genimage v20 の仕様](https://github.com/pengutronix/genimage/blob/v20/README.rst)／[実機測定計画](../verification/hardware-measurements.md)

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
| FTL | 論理ブロックとフラッシュ媒体の物理配置を仲介するカード内部の変換層です。カード固有の動作や電断時の保証は今回確認できていません。【未確認】[電源・更新方式の調査](README.md) | 通常のホストから内部マッピングを直接確認できません。 |

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

`align = 4M` は測定した候補の中で全エントリーの開始位置が 4 MiB 境界にそろう設定です。「最適」と証明されたわけではありません。実機では、同じカード・カーネル・ファイルシステム・ワークロードを使い、起動、連続／小ブロック I/O、電断後の整合性を比較します。【推測】[実機測定計画](../verification/hardware-measurements.md)

## FAT データ領域

現行 boot-a の FAT は 512 byte セクター、4 セクター／クラスタ、4 セクターの予約領域、各 128 セクターの FAT が 2 面、32 セクターのルートディレクトリーです。データ領域はパーティション先頭から 292 セクター（149,504 byte）後に始まります。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

現行 p2 の開始セクター 32,769 にこの相対オフセットを足すと、データ領域は 16,927,232 byte から始まり、4 MiB 境界から 150,016 byte ずれます。パーティション開始位置だけを整列しても、FAT BPB 内の予約領域・FAT 面・ディレクトリーの合計は変わらないため、データ領域の相対位置は直りません。【実測】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327)

FAT のクラスタ数や予約セクターを変更すれば整列する、といった推奨は、確認した仕様資料で裏付けられていません。現時点では根拠を確認できる修正方法を採用せず、SDA のファイルシステム仕様または formatter の文書を確認し、再フォーマット後の BPB を測る項目として残します。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認

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
