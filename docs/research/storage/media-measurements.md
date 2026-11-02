# SD媒体の特性と実機測定計画

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

以下はdiscard、SDバスと実カードでの測定案です。計画・チェック項目を保存したことを、CardputerZeroで実行した結果とは扱いません。`align = 4M`の指定だけではFTL・カードのerase/AU・速度改善を確かめたことになりません。

用語と配置・共通資料は[フラッシュ境界](layout-and-flash.md)、電断の資料は[電源遮断](power-loss.md)、試験の現在地は[S1–S17](../verification/experiment-catalog.md)を参照します。

## discard、fstrim、SD バス

Linux 6.18 系の SD コアは、カードが SD 5.1 以降で discard 機能を報告した場合に限って discard を選択します。カードが全て同じ機能を持つとは限らないため、`fstrim` の可否と効果は対象カード・ホストで確認します。【一次】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L291-L313)

SD Speed Class は規格条件下の最低連続アクセス性能であり、4 KiB ランダム IOPS の指標ではありません。Application Performance Class は 4 KiB コマンドの IOPS を数え、A2 の性能には A2 カードと A2 対応ホストの両方が必要です。【一次】[SD Association Speed Class](https://www.sdcard.org/developers/sd-standard-overview/speed-class/)／[Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/)

CM0 の正確な microSD ホスト接続、最大クロック、UHS 電圧切替、カードとファームウェアの組合せは今回確定していません。カードの A1/A2 表記だけでホストが同等の性能を出すとは判断せず、実機のカーネルログとカード属性を記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)

## 実機での測定手順

1. 同一の CM0、カード、ファームウェア、カーネル、ファイルシステム、電源条件で現行配置と `align = 4M` を比較します。最初にパーティション開始位置、FAT BPB、ext4 の作成条件を記録します。【推測】[実機測定計画](../verification/hardware-measurements.md)
2. 起動時に `/sys/class/mmc_host/` と `/sys/bus/mmc/devices/` を列挙し、カード識別情報と読み取り可能な `erase_size`、`preferred_erase_size`、`ssr` 等を保存します。実際に存在する sysfs 属性だけを記録し、欠落値を推定で補いません。【一次】[Linux SD コアの sysfs 属性](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797)
3. `/sys/class/block/mmcblk*/queue/` の `logical_block_size`、`physical_block_size`、`minimum_io_size`、`optimal_io_size`、`alignment_offset`、`discard_granularity` など、実機で公開される属性を保存します。値の意味とドライバー実装が一致するかを確認し、存在しない属性は記録します。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c)
4. 連続読み書き、小ブロックのランダム読み書き、起動時間、温度・電圧をそれぞれ測定し、同じ条件で複数回実行します。flashbench は候補の調査手段ですが、このカード／ホストでの測定手順と妥当性は未確認です。【未確認】
5. SDA が公開する AU／RU 定義と formatter の手順を確認できるまでは、カードが報告した値から FAT の最適配置を推測しません。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認
6. 1 KiB と 4 KiB の ext4 作成条件をそろえ、`fsck.ext4 -p` の時間、ファイルシステム容量、代表的な `/data` 書込み、電断後の整合性を比較します。【推測】[実行時 formatter](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)／[実機測定計画](../verification/hardware-measurements.md)

## 電源断試験との関係

パーティション整列やファイルシステムのジャーナリングだけでは、カード内部 FTL の電断時の挙動を保証できません。試験では更新中・アイドル時の電断、起動不能数、ファイルシステム検査結果、A/B 復帰結果を記録します。QEMU は Linux の起動・パーティション認識・ファイルシステム回帰に使えますが、実カードの電源遮断や FTL の代替にはなりません。【推測】[電源・更新方式の調査](README.md)／[実機測定計画](../verification/hardware-measurements.md)

## 未確認事項

| 項目 | 次に必要な確認 |
|---|---|
| RU／AU の規範的定義、FAT の推奨境界、formatter の整列挙動 | SDA の仕様書または正規 formatter 文書を確認し、再フォーマット後の BPB と照合する。【未確認】SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 |
| CM0 のホストコントローラー、クロック、UHS 切替 | 対象基板のデバイスツリー、カーネルログ、実カードで確認する。【未確認】[Linux SD コア](https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c) |
| `preferred_erase_size` 等の対象カード値と A1/A2 の実効性能 | 実機 sysfs と read-only のカード診断、同一条件の workload で測る。【未確認】[Application Performance Class](https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/) |
| `data=ordered` への変更がアプリケーションの更新要件を満たすか | `fsync`／rename と繰り返し電断を含む更新試験を行う。【未確認】[ext4 文書](https://docs.kernel.org/admin-guide/ext4.html) |
| 4 MiB 整列が実カードの速度・寿命・電断耐性に与える影響 | 現行配置との実機比較が必要。測定前に効果を断定しない。【未確認】[CI run 39178538327](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327) |
