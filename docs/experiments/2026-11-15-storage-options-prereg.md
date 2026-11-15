# 事前登録: storage option 全測定（rootfs verity/FEC・/data LUKS+btrfs・zram/zswap）

- 種類: 実験の事前登録（experiment-record 準拠）
- 作成日: 2026-11-15
- 背景: 利用者方針（2026-11-15）により root=SquashFS+zstd+dm-verity(crc32c)+FEC+A/B 切り戻し、data=LUKS+btrfs dup+xxhash64+zstd 透過圧縮とし、SquashFS/zstd/dm-verity/LUKS/btrfs の全 option を測定する。設計根拠は [rootfs完全性設計](../research/storage/rootfs-squashfs-verity-fec-design.md)、[data LUKS+btrfs設計](../research/storage/data-luks-btrfs-design.md)、[zstd使用箇所とoption](../research/storage/zstd-usage-and-options.md)。
- 本 doc は実行前の登録。各実験は完了後に別の `YYYY-MM-DD-<short>.md` + `.csv` へ記録する。

## 固定版（実験の全 run で固定）

| 部品 | 版 |
|---|---|
| kernel | rpi-6.18.59（`b3495ea401d709af0701a85babcba5e3d788a602`）+ `linux.fragment` |
| Buildroot | 2026.08.1-27-g8b238854d90 |
| squashfs-tools | 4.7.5 |
| zstd | 1.5.7 |
| cryptsetup | 2.8.7（dev image は 2.7.5。計測は target 内 2.8.7 で行う） |
| btrfs-progs | 6.10 |
| e2fsprogs | 1.47.4 |
| QEMU | raspi3ap / raspi3b 既存 harness |

## 実験一覧と採否基準

### B1. SquashFS 圧縮 matrix（host 側、先行速報済み）

- 目的: `-comp zstd` での block size×level の圧縮率・build 時間を網羅し、rootfs の既定値を決める。
- 条件: source=既存 build の target tree。`-b {4K,8K,16K,32K,64K,128K,256K,512K,1M}` × `-Xcompression-level {1,3,9,15,19,22}`。codec 比較に `xz -Xbcj arm`、`lz4`、`gzip`（128K・既定 level）を各1点。
- 採否基準: image サイズと QEMU での mount・起動時間の兼ね合い。現行 `-b 128K -Xcompression-level 22` との差が 5% 以内なら block 拡大を検討。
- 反復: build は3回、QEMU read は5回、median/min/max を記録。
- 状態: **単発速報済み**（xz=22.21MB・zstd 1M l19/22=22.37MB・zstd 128K default=23.90MB・lz4=30.84MB）。生データ（matrix.csv・script・driver.log・SHA256SUMS）は orphan branch `data/fs-compare-experiments` の commit `328bece4cd9f724aaafa83e5cc350c632762dc20` の `storage-options/mksquashfs-quick-scan/` に保存済み。正式記録は反復後。

### B2. SquashFS 展開・read 性能（QEMU）

- 目的: block size×level が decompress 時間と read 遅延に与える差。kernel decompressor が level 22（wlog 27 相当 window）を扱えるかの検証を兼ねる。
- 条件: B1 の代表点（128K/l15・128K/l22・512K/l19・1M/l19）で rootfs を作り、boot 時間（既存 icount 手法 T0〜T5）と `/usr` 以下ランダム read（固定 seed）を測る。
- 採否基準: T0 起動成功が前提。boot 時間増加が no-verity ベースライン比 +10% 以内、read p95 が既定比 +20% 以内なら採用候補。
- 反復: 各構成5回。

### B3. dm-verity + FEC（crc32c formatter・破損注入・error mode）

- 目的: hash=crc32c での tree 生成・起動・破損検出・FEC 訂正・error mode→tryboot 切り戻しを検証。
- 前提: veritysetup は crc32c を拒否するため、hash tree+FEC 生成は自前 formatter（`board/cardputerzero/tools/` に新規、超過用語なしの小 tool）を先に実装してから測定。
- 条件: hash {sha256(比較基準), crc32c}、4K block、error mode {restart_on_corruption, panic_on_corruption}、FEC {なし, fec_roots 2/8/16}。破損注入: ①data 1 block ビット化け ②連続 region 化け（FEC 訂正限界確認）③hash tree 自身の化け。
- 採否基準: ①は FEC 範囲内なら訂正して起動継続、②③は検出して error mode 通りの動作、切り戻しは tryboot で別スロット起動を serial log で確認。
- 反復: 各破損 case 5回。

### B4. /data LUKS cipher throughput（QEMU guest 内）

- 目的: **kernel crypto API が提供する全 cipher**（ゲストの /proc/crypto で列挙: aes/camellia/chacha/sm4/twofish/serpent/aria/xchacha12・20-adiantum 等、利用者指示 2026-11-15）の read/write throughput。同じ枠組みで **全ハッシュアルゴリズム**（crc32c/sha1/sha256/sha512/sha3/blake2b/2s/xxhash64/wp512/streebog/md5 等）の throughput も測る。verity hash_alg と btrfs csum 選定の根拠。sector-size {512,4096}、integrity 有無の差も比較。
- 背景: host コンテナでは algif_skcipher が無く `cryptsetup benchmark` の cipher 計測ができないため QEMU guest 内で `cryptsetup benchmark` / dd ベースで測る。QEMU TCG は cycle 相当ではないため絶対性能は[実機計測](../research/verification/hardware-measurements.md)（cipher・hash 全数）で確定し、ここでは相対比較と機能確認を行う。
- 採否基準: CardputerZero（BCM2837B0 ARMv8、AES-NI 無し想定）で adiantum 系が AES 系を上回るかどうか。adiantum 系の sequential write throughput が AES 系の 1.2 倍を超える場合のみ adiantum 採用を検討し、1.2 倍未満なら AES 系（aes-xts-plain64）でよいとする。最終決定はセキュリティビット数（key size 込み）と実機 throughput の両方。
- 反復: 各 cipher・hash 5回。

### B5. btrfs mkfs/mount option（QEMU guest + fs-compare 連携）

- 目的: `mkfs.btrfs --csum xxhash -m dup -d dup` を基準に csum {crc32c,xxhash,sha256,blake2b}、nodesize {4K,16K,32K}、mount `compress=zstd:{1,3,9}`/compress-force/commit={30,5,0}/ssd, nossd/autodefrag/space_cache/thread_pool/flushoncommit/max_inline を測る。
- 方法: 既存 fs-compare harness（`fs-compare-configs.tsv`）に variant を追加して T4-sync・T5・write inventory を測る。E3/E4 matrix 完了後に同じ機構で。
- 採否基準: idle 書き込みが規則（§10: 操作なし・progress なしで書き込みなし）を満たす構成であること。数値基準として、T4-sync/T5 の idle window で quiesce 後の書き込みが 0 sector であること、write inventory の総 sector 数が ext4 base 比 +15% 以内であること。
- 反復: 各 variant 5回。

### B6. zram/zswap（QEMU guest）

- 目的: zram `comp_algorithm` {lz4, lzo, zstd 既定/1/9}、zswap `compressor` {lzo,lz4,zstd}、`zpool` {zbud,z3fold,zsmalloc}、`max_pool_percent` {10,20,40} の圧縮率・swap 速度・CPU 時間。
- 方法: メモリ圧 workload（fs-compare-workload.c にメモリプレッシャー版追加）で swap out→in。`mm_stat`/`io_stat` で圧縮率取得。
- 採否基準: 圧縮率（orig_data_size/mem_used_total）と swap in/out の所要時間が現行 zstd 既定から ±10% 以内の差なら現行構成を維持する。lz4 は比較点で、圧縮率が zstd 既定比 -15% を超えて落ちるなら不採用とする。
- 反復: 各構成5回。

### B7. 起動時間の統合影響

- 目的: verity あり/なし、FEC あり/なし、LUKS unlock あり/なしでの boot 時間差（T0〜T5）。
- 反復: 各構成5回。

## 共通の記録方法

- 各実験の生の値・失敗した試行は `docs/experiments/<date>-<short>.md` + 同名 `.csv` に、ログが大きい場合は data 枝（`data/fs-compare-experiments`）に SHA-256 つきで保存。
- QEMU の結果は実機（LCD/keyboard/I2C/firmware tryboot/電源断）の確認と分けて書く。
- 実行中 script は編集しない。出力を消す前に untracked な証拠を保存。

## 既知の阻害要因

1. **dev image の tool 不足**: `mkfs.btrfs`、zstd CLI が無い。btrfs-progs は Buildroot に package があるので target image へ `BR2_PACKAGE_BTRFS_PROGS` 追加で対応する案。
2. **crc32c formatter 不在**: B3 の前提。`board/cardputerzero/tools/` に自前実装（hash tree + RS(255,N) parity を userspace で生成）。
3. **kernel config 未適用**: `DM_VERITY=y`、`DM_VERITY_FEC`、`DM_CRYPT=y`、`CRYPTO_CRC32C=y`、`BTRFS_FS=y`、`CRYPTO_ZSTD=y` が fragment 未記述。実装 PR が測定の前提。
4. **E34 matrix 中断中**: 87/174。B5 の fs-compare 連携は同じ harness を使うため、E34 再開完了後に順次。
