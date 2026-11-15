# mksquashfs 圧縮 option matrix（B1 正式記録）

事前登録: `docs/experiments/2026-11-15-storage-options-prereg.md` の B1。

## 目的

`mksquashfs -comp zstd` の block size と `-Xcompression-level` の全組み合わせ、および codec 比較点（xz, lz4, gzip）で、生成 image サイズと build 時間を測り、rootfs の既定値を決める根拠にする。

## 条件

- 入力: 固定された rootfs target tree（約 46 MiB、fs-compare 用 build の `target/`）。展開済みの単一 source。
- option: `-b {16K,32K,64K,128K,256K,512K,1M}` × `-Xcompression-level {1,3,9,15,19,22}`（zstd 42 点）、codec 比較 `xz -Xbcj arm`/`lz4`/`gzip`/`zstd 既定`（128K・既定 level 各1点）。共通 `-noappend -all-root -no-xattrs` 相当（script は `-all-root -no-progress`）。
- 反復: 3 回。image サイズは全回同一（決定的）、build 時間のみ min/median/max。
- 版: squashfs-tools 4.7.5（zstd 1.5.7 リンク）。
- script: `board/cardputerzero/tools/` 管理外の一時 script を data 枝に保存（後述）。

## 生の値

- 全 138 run（46 config × 3 回）: `data/fs-compare-experiments` 枝 commit `71e8ad6` の `storage-options/mksquashfs-matrix-repeat/`（`matrix-r1..r3.csv`、`matrix-medians.csv`、script、SHA256SUMS）。
- 単発の先行 run は同枝 commit `328bece4` の `storage-options/mksquashfs-quick-scan/`。
- 集計 csv はこの文書と同名の `.csv`。

## 結果（median、bytes）

| codec / block / level | image bytes | build ms | 128K/l22 比 |
|---|---|---|---|
| xz 128K +bcj arm 既定 | 22,155,264 | 5,246 | -6.5% |
| **zstd 1M l19** | **22,372,352** | 2,827 | **-5.6%** |
| zstd 1M l22 | 22,372,352 | 3,034 | -5.6% |
| zstd 512K l19/l22 | 22,970,368 | 3,253/3,080 | -3.0% |
| zstd 256K l19/l22 | 23,310,336 | 4,872/5,465 | -1.6% |
| zstd 128K l19/l22（現行） | 23,691,264 | 5,768/6,320 | ±0% |
| zstd 128K 既定(l15) | 23,896,064 | 1,446 | +0.9% |
| gzip 128K 既定 | 25,108,480 | 1,286 | +6.0% |
| zstd 任意 block l1 | 26.3-27.0 MB | 120-290 | +11-14% |
| lz4 128K 既定 | 30,842,880 | 113 | +30.2% |

- level 19→22 では全 block size で bytes が完全に一致（飽和）。build 時間は level 22 が長い（128K で 5.8s→6.3s、64K ではばらつき大）。
- build 時間: zstd は level 9 以下なら 0.2-0.6s、level 19-22 で 2.3-6.3s。xz は 5.2s 一定。

## 考察

- xz は最小（22.16 MB）だが kernel xz decompressor の read 遅延が zstd より悪いことが一般的で、差は 1M zstd 対比 -1.0% しかない。rootfs 読み取り面積の方が大きい製品では zstd の方が釣り合う（B2 で read 側を確認）。
- 現行既定 `128K l22` から 512K/1M への拡大で -3.0%/-5.6%。dm-verity は data block 4096B 固定で hash tree は image 全体に掛かるため、squashfs の block size は verity とは独立に選べる。
- level 19 と 22 は同じ image を出すので、build 時間の短い **level 19 が無駄なく有利**（EXTREME_COMP の 22 を選ぶ理由は無かった）。

## 失敗した試行・注意

- host 環境の `cryptsetup benchmark` は algif_skcipher 非対応コンテナで cipher を測れず（B4 へ持ち越し）。
- 失敗 run は無し。mksquashfs は全 138 run 成功。

## 次に必要な測定

- B2: 代表点（128K/l15, 128K/l19, 512K/l19, 1M/l19, xz 128K）の QEMU read・boot 時間。B1 単体では image サイズだけで read 性能を判断しない。
