# RAID6 PQの起動時選択

## 対象と判断

対象は製品のLinux 6.18.59、Raspberry Pi source `b3495ea401d709af0701a85babcba5e3d788a602`。Btrfsは`RAID6_PQ`と`XOR_BLOCKS`をselectする。そのため、filesystemがsingle/DUPでも、built-in libraryの初期化は起動時に行われる。今回の範囲はPQ起動選択のKconfigと、その依存だけであり、kernel全optionの再調査ではない。

利用者が承認した変更は`CONFIG_RAID6_PQ_BENCHMARK=n`だけである。PQ生成・復旧libraryやBtrfsの削除ではない。実験・採否の根拠は[QEMU比較記録](../../experiments/2026-11-19-raid6-pq.md)へ保存する。実機時間と実機で選ばれるalgorithmは未確認である。

| 選択肢 | 効果と背反 | 扱い |
|---|---|---|
| benchmark有効の維持 | 起動時に候補を計測してPQ algorithmを選ぶ。起動時間とhost負荷の影響を受ける | 比較のA |
| benchmarkだけ無効 | 有効性を確認した先頭の候補を選び、gen/xorの速度計測を省く。選ばれる候補が変わり、RAID5/6の性能が最良とは限らない | 利用者が承認したB |
| Btrfs・PQ libraryの削除、別filesystemへの置換 | 現行のBtrfs要件や依存の変更となる | 今回は行わない |
| `initcall_blacklist=raid6_select_algo` | libraryの必要な初期化まで止める。計測だけを省く変更とは異なる | 採用しない |

同じlibraryを使うので、保守元とGPL-2.0のlicenseは変わらない。新しい依存・自前のalgorithm・永続cacheは追加しない。option変更のCVE削減効果や容量・RAMの改善量は測っていない。

## optionの表

既定値は他のconfigからselectされる前の値。固定版の一次資料は[lib/Kconfig](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/lib/Kconfig)、[crypto/Kconfig](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/crypto/Kconfig)、[Btrfs Kconfig](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/btrfs/Kconfig)。最新版側は調査時のmainline `7.4.0-rc3`、commit `4405c18c95d2d0f99f6c581ef0ee8591a1aa6ccd`の[lib/raid/Kconfig](https://github.com/torvalds/linux/blob/4405c18c95d2d0f99f6c581ef0ee8591a1aa6ccd/lib/raid/Kconfig)を比較した。最新版への更新は行わない。

| option | 意味・固定版の既定 | 固定版での利用 | mainline比較 | MSD/Linuxの扱い・理由 |
|---|---|---|---|---|
| `CONFIG_RAID6_PQ` | PQ library。tristate、暗黙n | あり | 維持 | Btrfsのselectでy。支援機能を残す |
| `CONFIG_RAID6_PQ_BENCHMARK` | 起動時のPQ速度計測。RAID6_PQに依存し、既定y | あり | 既定yを維持、定義fileは移動 | n。計測だけを省き、有効性の検査と候補選択は残す |
| `CONFIG_XOR_BLOCKS` | XOR library。tristate、暗黙n | あり | 維持、定義fileは移動 | Btrfsのselectでy。別のXOR較正は変更しない |
| `CONFIG_BTRFS_FS` | Btrfs。tristate、暗黙n | あり | 今回はconsumerとして参照 | 製品fragmentでy。single/DUPを検査する |
| `CONFIG_XOR_BLOCKS_ARCH` | architecture最適化を選ぶ内部option | なし | ARM64などで条件付きy | 固定版にないため設定を追加しない |
| `CONFIG_XOR_KUNIT_TEST` | XORのKUnit test | なし | KUNITとXOR_BLOCKSに依存、既定KUNIT_ALL_TESTS | 同上。今回の起動較正とは別 |
| `CONFIG_XOR_BENCHMARK` | XORのKUnit benchmark | なし | XOR_KUNIT_TESTに依存、KUNIT_ALL_TESTS=mで既定y | 同上。固定版のXOR較正のswitchと混同しない |
| `CONFIG_RAID6_PQ_ARCH` | PQのarchitecture最適化を選ぶ内部option | なし | KERNEL_MODE_NEONなどで条件付きy | 固定版にないため設定を追加しない |
| `CONFIG_RAID6_PQ_KUNIT_TEST` | PQのKUnit test | なし | KUNITとRAID6_PQに依存、既定KUNIT_ALL_TESTS | 同上 |
| `CONFIG_RAID6_PQ_KUNIT_BENCHMARK` | PQのKUnit benchmark | なし | PQ testに依存、KUNIT_ALL_TESTS=mで既定y | 同上。起動選択のbenchmarkとは別 |

機械照合は、固定版`lib/Kconfig`の`RAID6_PQ*`、`crypto/Kconfig`の`XOR_BLOCKS`、consumerの`BTRFS_FS`、比較版`lib/raid/Kconfig`の全config tokenを母集団とする。表と集合で比較する。

## 設定の経路と実行時

[QEMU実験](../../experiments/2026-11-19-raid6-pq.md)ではA/AとABAB各5回が成功した。無効時は全5回で`neonx8`を選び、benchmark throughput行が消えた。Btrfs single/DUPのmount・読戻し・scrubも成功した。起動完了中央値は29.73秒から28.57秒だが、逆転したpairもある。実機の時間・最適algorithmは未確認のまま、起動時の計測だけを省く設定を採用する。

Buildrootはこのswitch専用のoptionを公開していない。[製品defconfig](../../../configs/msd_cardputerzero_defconfig)の`BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES`が[linux.fragment](../../../board/cardputerzero/linux.fragment)を渡すので、vendorを編集せずに無効化できる。fragmentの記述だけでなく、生成したkernel `.config`も照合する。

固定版[raid6_choose_gen](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/lib/raid6/algos.c)は、無効時に最初のvalidな候補で止まり、`skipped pq benchmark and selected`を出す。gen/xorの計測loopを通らないが、PQ生成・復旧の選択自体は残る。選択を切り替える公開のsysctl・環境変数・kernel command lineは、この実装にはない。

[crypto/xor.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/crypto/xor.c)の`calibrate_xor_blocks`は別のinitcallで、このoptionを参照しない。固定版には`CONFIG_XOR_BENCHMARK`もない。PQ計測を省くことを「全てのRAID・XOR計測を止める」とは扱わない。single/DUPのmount・scrub成功もRAID5/6経路の検証ではない。
