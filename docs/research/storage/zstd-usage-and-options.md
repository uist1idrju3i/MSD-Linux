# zstd の使用箇所と全 option 測定計画

- 種類: 調査（一次資料照合 + 測定計画）
- 作成日: 2026-11-15
- 利用者の方針（2026-11-15）: 「zstdはzramかzswapでも使っているので、そちらも全オプションを測定してください。」
- 関連: [rootfs-squashfs-verity-fec-design](rootfs-squashfs-verity-fec-design.md)、[data-luks-btrfs-design](data-luks-btrfs-design.md)

## 1. zstd が使われる箇所

| 箇所 | レイヤ | 版・設定 | kernel symbol |
|---|---|---|---|
| SquashFS rootfs | fs 圧縮 | squashfs-tools 4.7.5 `-comp zstd` | `CONFIG_SQUASHFS_ZSTD=y` |
| zram（swap） | block dev comp | `CONFIG_ZRAM=y`、def comp=zstd、multi_comp=y | `CONFIG_ZRAM_BACKEND_ZSTD` |
| zswap（swap cache） | frontswap | `CONFIG_ZSWAP=y`、既定 compressor=lzo | `CONFIG_ZSWAP_COMPRESSOR_DEFAULT_*` |
| btrfs /data | fs 透過圧縮 | `compress=zstd[:level]` | `CONFIG_CRYPTO_ZSTD` + `BTRFS` |

zstd 自体は 1.5.7 固定（`vendor/buildroot/package/zstd/zstd.mk`）。kernel 側は `crypto/zstd.c` + lib/zstd で、squashfs/btrfs/zram/zswap すべて kernel 内 decompress/compress 実装を使う。

## 2. zstd の option 全量（一次資料: zstd 1.5.7 `zstd --help` + `zstd.h`）

### 2.1 CLI / lib 共通パラメータ

| 項目 | 範囲 | 測定対象か |
|---|---|---|
| `-<level>` / `--fast[=<n>]` | 1-19、fast は負数 (-1 〜 -7 常用) | SquashFS `-Xcompression-level` 経由で level 1-22 測定（19-22 は ultra、window 制約注意） |
| `-T<n>` threads | 圧縮時のみ | mksquashfs `-processors` と合わせ |
| `--long[=<wlog>]` | window 拡大 | squashfs 内で個別指定不可（mksquashfs が wlog を level から算出）。zram/zswap では level 固定パラメータなので対象外 |
| `--ultra -22` | level 22 | squashfs EXTREME_COMP で既に使用中 |
| `--patch-from` | delta | 対象外（update 用ではない） |
| `-D dict` | 辞書 | squashfs では `-Xdict` 非対応。zram/btrfs も dict 非対応。対象外 |
| `--no-check`/`--check` | xxhash64 frame check | squashfs では frame check なし（csum は verity 側）。zram も frame check なし |
| `--format={zstd,magicless}` | frame 形式 | kernel 組み込みは raw stream/one-shot のため CLI の format は関係しない。squashfs は独自 block 圧縮 |
| `advancedCompressionParameter` (lib) | wlog/clog/hlog/slog/slog2/tlen/window_log/strategy/minMatch/targetLength 等 | kernel API から直接指定できない箇所が多い。btrfs/zram は level 相当のみ |

### 2.2 kernel 側 zstd パラメータ

- kernel の `crypto/zstd` は one-shot API で、compress 時に level を受け取る呼び出し先が限られる。
- zram: `comp_algorithm` に `zstd` または `zstd <algo> <level>` 指定可（kernel 5.4+ の multi_comp: `comp_algorithm` に `algo:wlog:level` 形式、kernel 6.x では `zstd <level>` など backend params）。既定は level 3 相当。
- zswap: `zswap.compressor` kernel 引数または `/sys/module/zswap/parameters/compressor`（lzo/lz4/842/deflate/zstd の crypto alg 名）。zswap の zstd は `zstd` alg 名で、crypto API の one-shot level は kernel 内部 default。
- btrfs: mount `compress=zstd:N` で N=1-15 を btrfs が crypto/zstd の level に渡す。
- SquashFS: `-Xcompression-level` が mksquashfs 側で userspace libzstd 呼び出しの level。kernel 側は展開のみ。

## 3. zram/zswap の option（一次資料: kernel `Documentation/admin-guide/blockdev/zram.rst` + `zswap.rst`）

### 3.1 zram

| sysfs/module option | 内容 | 測定対象 |
|---|---|---|
| `/sys/block/zram*/disksize` | 仮想 disk サイズ | 値差は容量設計、測定対象は既定値との差 |
| `comp_algorithm` | `lz4`, `lzo`, `zstd`（multi_comp で列挙可能）、`zstd <level>` 等 backend params 付き | **全 algorithm × 主 level 比較** |
| `writeback` | idle/incompressible page の backing dev への退避 | **`CONFIG_ZRAM_WRITEBACK` 未設定で使用不可**。SD write 規則とも衝突するため不採用方向 |
| `mem_limit` | メモリ上限。sysfs `/sys/block/zram0/mem_limit`（WO）。module param は `num_devices` のみで kernel 引数では設定できない | 測定対象 |
| `idle` | page の idle 時刻設定。`ZRAM_WRITEBACK` 未設定でも利用可（`CONFIG_ZRAM_MULTI_COMP` の recompress で参照される） | 測定対象 |
| `recompress` | idle/incompressible な page の現行 algorithm での再圧縮（`CONFIG_ZRAM_MULTI_COMP` で公開） | 測定対象（algorithm 切替後の効果確認） |
| `reset`, `mm_stat`, `io_stat` | 統計 | 計測手段 |
| module param `num_devices` | 既定 1 | 対象外 |
| kernel `CONFIG_ZRAM_WRITEBACK` / `ZRAM_MEMORY_TRACKING` | config | WRITEBACK 未設定 / TRACKING=y |

### 3.2 zswap

| kernel 引数/param | 内容 | 測定対象 |
|---|---|---|
| `zswap.enabled` | 0/1 | 既定 0（`ZSWAP_DEFAULT_ON` 未設定） |
| `zswap.compressor` | lzo/lz4/842/deflate/zstd | **全 compressor 比較** |
| `zswap.zpool` | zbud/z3fold/zsmalloc | 全比較 |
| `zswap.max_pool_percent` | 既定 20 | 測定対象 |
| `zswap.accept_threshold_percent` | 既定 90 | 測定対象 |
| `zswap.exclusive_loads` | 0/1 | 測定対象 |
| `zswap.shrinker_enabled` | 0/1 | 既定 off |
| `zswap.non_same_filled_pages_enabled` | 0/1 | 既定 on |
| `zswap.same_filled_pages_enabled` | 0/1 | 既定 on |

## 4. 測定計画（experiment-record 準拠）

各測定は実行前に experiment-record 準拠の事前登録（目的・採否基準・反復回数5回以上・固定版）を `docs/experiments/` に作ってから行う。測定は 2 面:

**A. squashfs/zstd 側（host + QEMU boot/read 時間）**

- `-comp zstd -b {4K,8K,16K,32K,64K,128K,256K,512K,1M}` × `-Xcompression-level {1,3,9,15,19,22}` のサイズ・生成時間。
- QEMU で mount 時間・`/usr/bin` 以下ランダム read・boot 完了までの icount。
- 比較基準として `-comp xz -Xbcj arm`、`-comp lz4`、`-comp gzip` を数点だけ。

**B. zram/zswap 側（QEMU 内 workload）**

- zram: `comp_algorithm` {lz4, lzo, zstd(level 既定), zstd level 1, zstd level 9} で、mem_limit/disksize 固定下での圧縮率・swap in/out 速度・CPU 時間。workload は既存 fs-compare-workload.c に zram 用メモリプレッシャー版を追加する形。
- zswap: `compressor` {lzo, lz4, zstd}、zpool {zbud, z3fold, zsmalloc}、`max_pool_percent` {10,20,40}、frontswap 経由の swap 挙動。
- 共通 workload: メモリ圧を掛けて swap out → swap in。速度と圧縮率、後続の fs 書き込みがないこと（write-policy §10 の idle write 観点でもチェック）。

**C. btrfs zstd 側**

- `data-luks-btrfs-design.md` §4 の compress= 系と合わせて測定（重複しない）。

## 5. 未解決

1. **kernel zstd の level 上限**: squashfs `-Xcompression-level 22` は展開側で window が大きくなる。kernel decompressor の max window を超えないか要検証（SquashFS は既定で level 22 の wlog まで許容するはずだが実機メモリ制約で測定）。
2. **zram backend params 形式の kernel 6.18 での正確な文法**: `comp_algorithm` に `zstd:1` のような指定が通るか QEMU で確かめる。
3. **zswap と zram の併存**: 両方有効化したときの優先順位（zswap は frontswap、zram は独立 block dev）。製品では片方のみ使うか、併存させるかを利用者確認。
