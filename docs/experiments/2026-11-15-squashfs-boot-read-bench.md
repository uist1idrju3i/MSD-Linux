# SquashFS option 別の boot・read 時間測定（B2）

2026-11-15。[mksquashfs matrix](2026-11-15-mksquashfs-matrix.md)（B1、圧縮率と生成時間）の上位 option について、QEMU で実際に起動して展開側のコスト（読み出し時間・起動時間・メモリ）を測った記録です。zstd level 19 / 22 の展開側への影響確認も目的です。

## 目的

- codec（zstd/gzip/lz4/xz）と block size（128K/512K/1M）が起動時の全 file 読み出し（squashfs の展開経路）と ready までの時間に与える影響を比較する
- zstd `-b 1M` で level 19 と 22 の展開速度・メモリ使用量を比較する（B1 で image サイズは同一サイズだったため、展開側に差がなければ 22 を採用する判断材料）

## 条件

- case 生成: `board/cardputerzero/tools/bench/squashfs-opts/make-case.sh`、実行: `board/cardputerzero/tools/bench/dm-verity/run-boots.sh`（`ROOT_DEVICE_OVERRIDE=/dev/mmcblk0p5`、verity なしの素の squashfs を p5 から起動）
- 各 variant 5 boot（repeat 0〜4）。QEMU 11.1.2 `raspi3ap`、memory 512M、`icount=shift=0`（guest 時刻 = printk timestamp）
- guest 側の計測: `msd-readall` が `/dev/kmsg` に `squashfs-readall-begin`・`squashfs-readall-mem`（0.5 秒ごとの `MemAvailable` 最小値と `drop_caches` 後の値）・`squashfs-readall-complete` を書き込む。`squashfs-readall-complete` の timestamp を「全 file 展開完了時刻」として使う
- なお `begin`/`mem` marker は測定の途中で追加したため、新しい計装を含むのは `S-z1m-l19`・`S-z1m-l22` の 2 case だけ。他 6 variant は `complete` timestamp と ready 時刻のみ
- imageサイズはB1 matrixの値。kernelはS-z128-def・S-z128-l19・S-z512k-l19と他variantでImage sizeが約135 KB異なります。生成時期によるbuild差があり、ready時間への影響を除外できません。

## 結果

生の値は [2026-11-15-squashfs-boot-read-bench.csv](2026-11-15-squashfs-boot-read-bench.csv)。raw log は data branch `data/fs-compare-experiments` の `session-2026-11-15/evidence/b2-squashfs-boot-read.tar.zst`。

| variant | codec/block/level | image bytes | readall 完了 med (s) | ready med (s) |
|---|---|---|---|---|
| S-lz4-128 | lz4 128K | 30,842,880 | 2.108 | 3.144 |
| S-z128-def | zstd 128K default | 23,896,064 | 2.594 | 3.658 |
| S-z128-l19 | zstd 128K l19 | 23,691,264 | 2.621 | 3.693 |
| S-gzip128 | gzip 128K | 25,108,480 | 2.874 | 3.914 |
| S-z512k-l19 | zstd 512K l19 | 22,970,368 | 3.483 | 4.546 |
| S-z1m-l19 | zstd 1M l19 | 22,372,352 | 4.669 | 5.996 |
| S-z1m-l22 | zstd 1M l22 | 22,372,352 | 4.659 | 6.013 |
| S-xz128-bcja | xz 128K + bcj=arm | 22,155,264 | 6.065 | 7.106 |

### zstd level 19 vs 22（`-b 1M`、5 boot）

| 指標 | l19 median (range) | l22 median (range) |
|---|---|---|
| readall 所要時間（begin→complete） | 2.987 s（2.979–2.990） | 2.988 s（2.978–3.001） |
| readall 完了時刻 | 4.669 s | 4.659 s |
| boot→ready | 5.996 s（5.985–6.007） | 6.013 s（5.960–6.019） |
| readall 中の MemAvailable 最小 | 351,336 kB | 354,424 kB |
| drop_caches 後の MemAvailable | 358,508 kB | 367,028 kB |

l22のreadall所要時間の中央値差は+0.001 sでした。誤差幅を校正していないので統計的同等性とはしません。RAMは0.5秒間隔のMemAvailableサンプルであり、瞬間peakやdecompressor単独のworkspace量は測っていません。block独立圧縮という性質だけで、l22の展開側に悪影響がないとは結論できません。利用者の条件付きl22判断に対する限定的なQEMU資料です。

## 結論

- この条件ではlz4のreadall完了時刻が最小でimageは最大（30.8 MB）。xz(+bcj)の完了時刻は6.1 s、zstd 128Kの約2.3倍でした。時刻差にはreadall開始以前の起動処理も入り、全variantでbegin計装が揃っていません。
- zstdの128K→512K→1Mで完了時刻は2.6→3.5→4.7 sでしたが、kernel差もあるためblock sizeだけの因果効果・実機順位とはしません。
- 製品既定を本測定だけで変更しません。l22は展開側の悪影響がないという利用者条件を保持し、同一kernel・計装と実機で追加確認します。

## 未確認

- QEMU/TCGの絶対速度も相対順位も実機の代理にはしません。[実機計画](../research/verification/hardware-measurements.md)で別途確認します。
- kernel約135 KB差と途中のbegin/mem計装追加があり、影響なしとはしません。新runnerは全caseを同じ入力kernelと現行計装で新規生成しますが、その再測定は今回未実施です。
- 実機 SD の I/O 帯域では lz4 の大きい image の読み出しコストが変わる可能性がある（QEMU の raw image 読み出しは host page cache 依存）
- 登録したrandom read p95は未測定です。実施したのは全fileの順次catと起動時刻の観測で、ランダムI/Oの代用ではありません。

## 次回の一括再現（今回未実行）

V0とT0を揃えたbase入力に対し、次の一命令で8 case（1M/l19・l22を含む）を生成し各5 bootします。出力先は存在しないpathを指定し、旧case・CSVは再利用しません。各caseのvariant-infoにkernel/image hashを保存します。

```sh
docker/msd-dev bash board/cardputerzero/tools/bench/squashfs-opts/run-all.sh /work/output-fscmp /work/output-b3/cases /work/output-b2-next/cases /work/output-b2-next/results 4 180
```
