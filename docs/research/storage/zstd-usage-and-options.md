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
| zswap（swap cache） | swap cache | `CONFIG_ZSWAP=y`、既定compressorはbuild config依存 | `CONFIG_ZSWAP_COMPRESSOR_DEFAULT_*` |
| btrfs /data | fs 透過圧縮 | `compress=zstd[:level]` | `CONFIG_BTRFS_FS`がlib/zstdを選択 |

userspace zstdは1.5.7固定（`vendor/buildroot/package/zstd/zstd.mk`）。kernel側は固定kernelが内包するlib/zstdで、userspace libraryとは別です。SquashFSは展開だけ、btrfsとzramのbackendはそれぞれのwrapperを使います。zswapはcrypto API経由です。

## 2. zstdの代表optionと適用先

これは要約です。CLI・libraryのtokenごとの分類、source hash、抽出入力は[全optionの分類表](storage-option-coverage.md)へ分けました。CLIの存在だけで各consumerが同じ設定を受け取れるとはしません。

### 2.1 CLI / lib 共通パラメータ

| 項目 | 範囲 | 測定対象か |
|---|---|---|
| `-<level>` / `--fast[=<n>]` | CLI通常1-19、20-22は `--ultra` が必要。19には不要 | mksquashfsは `-Xcompression-level 22` を直接libzstdへ渡し、`--ultra` は使わない。B1は正level6点のみ既測定、負levelは未測定 |
| `-T<n>` threads | 圧縮時のみ | mksquashfs `-processors` と合わせ |
| `--long[=<wlog>]` | window 拡大 | squashfs 内で個別指定不可（mksquashfs が wlog を level から算出）。zram/zswap では level 固定パラメータなので対象外 |
| `--ultra -22` | CLIの上限解除とlevel指定 | mksquashfsの `EXTREME_COMP` とCLIのflagを混同しない |
| `--patch-from` | delta | 対象外（update 用ではない） |
| `-D dict` | CLI辞書 | SquashFS/btrfsには同じ引数を渡せない。固定kernelのzramは `algorithm_params` の `dict=` に対応し、未測定 |
| `--no-check`/`--check` | xxhash64 frame check | squashfs では frame check なし（csum は verity 側）。zram も frame check なし |
| `--format=FORMAT` | CLI出力形式（zstd/gzip/xz/lzma/lz4、build依存） | libraryのmagicless指定と同じCLI構文にはしない。SquashFSは独自block格納 |
| libraryの `ZSTD_c_*` / `ZSTD_d_*` | `windowLog` / `chainLog` / `hashLog` / `searchLog` / `minMatch` / `targetLength` / `strategy` 等 | 正確なtokenは分類CSVへ。各consumerが全parameterを公開するわけではない。zramはlevelに加えてdictも別属性で設定 |

### 2.2 kernel 側 zstd パラメータ

- kernel の `crypto/zstd` は one-shot API で、compress 時に level を受け取る呼び出し先が限られる。
- zram: `comp_algorithm` はalgorithm名の選択です。levelと辞書は別属性 `algorithm_params` に `algo=zstd level=8` や `algo=zstd level=8 dict=/etc/dictionary` と書き、device初期化前に設定します。旧説明の `zstd:1` / `zstd <level>` を `comp_algorithm` に渡す案を撤回します。source上の文法確認であり、実imageでの全backend起動成功は未確認です。
- zswap: `zswap.compressor` kernel 引数または `/sys/module/zswap/parameters/compressor`（lzo/lz4/842/deflate/zstd の crypto alg 名）。zswap の zstd は `zstd` alg 名で、crypto API の one-shot level は kernel 内部 default。
- btrfs: mount `compress=zstd:N` はbtrfsのlib/zstd wrapperへの設定です。crypto/zstdのmodule parameterではありません。
- SquashFS: `-Xcompression-level` が mksquashfs 側で userspace libzstd 呼び出しの level。kernel 側は展開のみ。

## 3. zram/zswap の option（一次資料: kernel `Documentation/admin-guide/blockdev/zram.rst` + `zswap.rst`）

### 3.1 zram

| sysfs/module option | 内容 | 測定対象 |
|---|---|---|
| `/sys/block/zram*/disksize` | 仮想 disk サイズ | 値差は容量設計、測定対象は既定値との差 |
| `comp_algorithm` / `algorithm_params` | 前者で名前を選択、後者に `algo=` / `priority=` / `level=` / `dict=` | 全algorithm × 主level比較は未実施。列挙表示とbuild config・module load・backendの可用性は別に照合 |
| `writeback` | idle/incompressible page の backing dev への退避 | **`CONFIG_ZRAM_WRITEBACK` 未設定で使用不可**。SD write 規則とも衝突するため不採用方向 |
| `mem_limit` | メモリ上限。sysfs `/sys/block/zram0/mem_limit`（WO）。module param は `num_devices` のみで kernel 引数では設定できない | 測定対象 |
| `idle` | page の idle 時刻設定。`ZRAM_WRITEBACK` 未設定でも利用可（`CONFIG_ZRAM_MULTI_COMP` の recompress で参照される） | 測定対象 |
| `recomp_algorithm` / `recompress` | secondary algorithmとpriorityを登録して再圧縮（`CONFIG_ZRAM_MULTI_COMP`が必要） | 未測定。primary algorithmを切り替えるだけの機能とはしない |
| `reset` | deviceの初期化状態をリセットする書込み操作 | 統計ではない。測定前後の制御 |
| `mm_stat`, `io_stat` | 統計 | 計測手段 |
| module param `num_devices` | 既定 1 | 対象外 |
| kernel `CONFIG_ZRAM_WRITEBACK` / `ZRAM_MEMORY_TRACKING` | config | WRITEBACKは現行fragmentで無効。TRACKINGはbuild依存で、別imageの状態を混同しない |

### 3.2 zswap

| kernel 引数/param | 内容 | 測定対象 |
|---|---|---|
| `zswap.enabled` | 0/1 | 既定 0（`ZSWAP_DEFAULT_ON` 未設定） |
| `zswap.compressor` | crypto APIのcompressor名、build/load依存 | 全compressor比較は未実施。候補一覧と実際に受理される名前を照合する |
| `zswap.zpool` | 固定6.18.59の公開parameterに存在しない | 実行不能。現行sourceはzsmallocを直接使うためzbud/z3fold総当たり案を撤回 |
| `zswap.max_pool_percent` | 既定 20 | 測定対象 |
| `zswap.accept_threshold_percent` | 既定 90 | 測定対象 |
| `zswap.exclusive_loads` | 固定版にparameterなし | 実行不能。旧版の候補を現行計画から分離 |
| `zswap.shrinker_enabled` | 0/1 | 既定は `CONFIG_ZSWAP_SHRINKER_DEFAULT_ON` 次第。全比較は未測定 |
| `zswap.non_same_filled_pages_enabled` | 固定版にparameterなし | 実行不能。現行の測定対象ではない |
| `zswap.same_filled_pages_enabled` | 固定版にparameterなし | 実行不能。現行の測定対象ではない |

固定source `mm/zswap.c` の公開parameterは `enabled` / `compressor` / `max_pool_percent` / `accept_threshold_percent` / `shrinker_enabled` の5件です。既定compressorは `CONFIG_ZSWAP_COMPRESSOR_DEFAULT` 次第であり、常にlzoとはしません。source・Buildroot optionの全tokenは分類表に収録しました。

## 4. 測定計画（experiment-record 準拠）

各測定は実行前に experiment-record 準拠の事前登録（目的・採否基準・反復回数5回以上・固定版）を `docs/experiments/` に作ってから行う。測定は 2 面:

**A. squashfs/zstd 側（host + QEMU boot/read 時間）**

- `-comp zstd -b {4K,8K,16K,32K,64K,128K,256K,512K,1M}` × `-Xcompression-level {1,3,9,15,19,22}` のサイズ・生成時間。
- QEMU で mount 時間・`/usr/bin` 以下ランダム read・boot 完了までの icount。
- 比較基準として `-comp xz -Xbcj arm`、`-comp lz4`、`-comp gzip` を数点だけ。

**B. zram/zswap 側（QEMU 内 workload）**

- zram: algorithm名を選び、zstdのlevelは `algorithm_params` で既定/1/9を設定。mem_limit/disksize固定下で圧縮率・swap in/out速度・CPU時間を測る計画。backendを列挙しbuild configとmodule loadを照合します。
- zswap: 実行可能な `compressor`、`max_pool_percent` {10,20,40}、`accept_threshold_percent`、`shrinker_enabled` を比較。zpool切替は現行では実行不能。swap backing deviceを明記し、zram併用による二重圧縮と区別します。
- 共通 workload: メモリ圧を掛けて swap out → swap in。速度と圧縮率、後続の fs 書き込みがないこと（write-policy §10 の idle write 観点でもチェック）。

**C. btrfs zstd 側**

- `data-luks-btrfs-design.md` §4 の compress= 系と合わせて測定（重複しない）。

## 5. 未解決

1. **l19/l22**: 利用者の「本当に展開側に悪影響がないのであれば22」という条件を保持します。SquashFSはblock独立圧縮で、CLIの一般的なwindowと同一視しません。後続B2の限定的なQEMU結果を実機RAM・性能の保証にはしません。
2. **zram backend params**: 文法は固定sourceで上記のとおり確認。利用可能backend・level/dictの適用結果・失敗時動作はguestで別途測定します。
3. **zswap と zram の併存**: 両方有効化したときの優先順位（zswap は frontswap、zram は独立 block dev）。製品では片方のみ使うか、併存させるかを利用者確認。
