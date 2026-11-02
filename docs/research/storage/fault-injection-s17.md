# S17の故障注入計画と限界

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

以下はS17の当初の試験計画です。冒頭の「まだ実行していない」は、この計画を立てた時点の記述として保持します。後の[エラー注入の試行](../../experiments/2026-10-30-s17-error-injection.md)では、試したSDモデルのblkdebugがゲストへ伝播しなかったことと、dm-flakeyでゲストread errorを確認したことを分けています。

全方式を実行済みにはせず、カードのFTL・実電断は未確認です。現在の試験状態は[台帳](../verification/experiment-catalog.md)、S17系列の根拠は[共通出典](filesystem-sources.md)にあります。

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
