# mksquashfs 圧縮 matrix の速報データ（単発）

- 取得日: 2026-11-15
- 目的: docs/experiments/2026-11-15-storage-options-prereg.md の B1 の host 側速報値の生データ。
- source tree: fs-compare 作業 checkout の build target（46MB）。
- 注意: 単発測定・未反復の速報。正式な記録は docs/experiments/ の記録（反復後）と併せて参照のこと。
- host の algif_skcipher 非搭載のため cryptsetup-benchmark.txt は PBKDF のみ。cipher throughput は QEMU guest で測定予定。
