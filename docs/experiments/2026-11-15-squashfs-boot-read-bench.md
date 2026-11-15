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
- image サイズは B1 matrix の値。kernel は S-z128-def・S-z128-l19・S-z512k-l19 と他 variant で Image size が約 135 KB 異なる（生成時期の違いによる build 差。ready 時間の大小比較には影響しないと判断）

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

level 19 と 22 で展開時間・メモリの差は測定誤差の範囲（l22 の readall 所要時間の中央値差は +0.001 s）。SquashFS は block 独立圧縮のため、level 22 でも展開側の window は実質 block size + kernel workspace 程度に収まり、実測でも悪影響は確認できなかった。**展開側に悪影響がないため zstd level 22 を採用できる**。

## 結論

- **codec・block size は展開速度に支配的な影響**がある。lz4 が最速だが image は最大（30.8 MB）。zstd 128K は gzip より速く小さい。xz(+bcj) は最小サイズだが readall が 6.1 s と zstd 128K の約 2.3 倍、ready で +3.4 s
- **zstd の block size を上げると展開が遅くなる**（128K→512K→1M で readall が 2.6→3.5→4.7 s）。圧縮率は 1M が最小だが、boot/read の遅さを考えると 128K〜512K が実用的
- 現行の採用候補: `zstd -b 128K -Xcompression-level 19`（サイズと速度のバランス）。level は 19→22 でも展開側の差なし

## 未確認

- QEMU/TCG のゲスト時刻での比較。codec 間の順位は傾向として使えるが、絶対値と実機での差は実機計測で確かめる（`docs/research/verification/hardware-measurements.md`）
- `S-z128-def`・`S-z128-l19`・`S-z512k-l19` と他 variant で kernel Image が約 135 KB 違う（case 生成時期の差）。ready 時刻の codec 間差（最小で約 0.5 s）に対して影響は小さいと判断したが、厳密な同一条件ではない
- 実機 SD の I/O 帯域では lz4 の大きい image の読み出しコストが変わる可能性がある（QEMU の raw image 読み出しは host page cache 依存）
