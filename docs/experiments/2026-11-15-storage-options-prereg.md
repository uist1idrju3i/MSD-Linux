# 事前登録: storage option 全測定（rootfs verity/FEC・/data LUKS+btrfs・zram/zswap）

- 種類: 実験の事前登録（experiment-record 準拠）
- 作成日: 2026-11-15
- 背景: 利用者方針（2026-11-15）により root=SquashFS+zstd+dm-verity(crc32c)+FEC+A/B 切り戻し、data=LUKS+btrfs dup+xxhash64+zstd 透過圧縮とし、SquashFS/zstd/dm-verity/LUKS/btrfs の全 option を測定する。設計根拠は [rootfs完全性設計](../research/storage/rootfs-squashfs-verity-fec-design.md)、[data LUKS+btrfs設計](../research/storage/data-luks-btrfs-design.md)、[zstd使用箇所とoption](../research/storage/zstd-usage-and-options.md)。
- 本 doc は実行前の登録。各実験は完了後に別の `YYYY-MM-DD-<short>.md` + `.csv` へ記録する。

監査による追記: 以下の初回条件・数値閾値・raw保存参照を保持したまま、固定版で存在しないoptionと誤った説明を訂正しました。[全token分類と未実施範囲](../research/storage/storage-option-coverage.md)を併読してください。全optionの測定は未完了です。03914の台帳同期保留は解除せず、製品設定も変更しません。

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

追記: 保存scriptの実行ループは16K〜1Mで、4K/8Kがありません。除外理由・失敗logは保存資料から確認できず、未実施の計画逸脱として残します。小blockが実行不能だったとはしません。後続の46構成×3回も元の54点全部の代わりではありません。

### B2. SquashFS 展開・read 性能（QEMU）

- 目的: block size×levelがdecompress時間とread遅延に与える差。旧登録の「level 22はwlog 27相当」という一般CLIの説明をSquashFSへ直結させず、独立blockの実際の展開時間・RAM・起動可否を測る。
- 条件: B1 の代表点（128K/l15・128K/l22・512K/l19・1M/l19）で rootfs を作り、boot 時間（既存 icount 手法 T0〜T5）と `/usr` 以下ランダム read（固定 seed）を測る。
- 採否基準: T0 起動成功が前提。boot 時間増加が no-verity ベースライン比 +10% 以内、read p95 が既定比 +20% 以内なら採用候補。
- 反復: 各構成5回。

### B3. dm-verity + FEC（crc32c formatter・破損注入・error mode）

- 目的: hash=crc32c での tree生成・起動・破損検出・FEC訂正・error modeを検証。別slot復帰はfirmware・永続flagを含む別の完了条件で、restart/panicの検出だけでは成立しない。
- 前提: veritysetup は crc32c を拒否するため、hash tree+FEC 生成は自前 formatter（`board/cardputerzero/tools/` に新規、超過用語なしの小 tool）を先に実装してから測定。
- 条件: hash {sha256(比較基準), crc32c}、4K block、error mode {restart_on_corruption, panic_on_corruption}、FEC {なし, fec_roots 2/8/16}。破損注入: ①data 1 block ビット化け ②連続 region 化け（FEC 訂正限界確認）③hash tree 自身の化け。
- 採否基準: ①は FEC 範囲内なら訂正して起動継続、②③は検出して error mode 通りの動作、切り戻しは tryboot で別スロット起動を serial log で確認。
- 反復: 各破損 case 5回。

### B4. /data LUKS cipher throughput（QEMU guest 内）

- 目的: 利用者要求の全cipher（AES/Camellia/ChaCha/SM4/Twofish/Serpent/ARIA/Adiantum等）と全hashを対象にする。sector-size {512,4096}、integrity有無、data cipher throughput、PBKDF時間/RAMを別々に測定する。hashはPBKDF2・verity・btrfs checksum・独立throughputの用途を分ける。
- 背景: hostではalgif_skcipher不足を観測。QEMUは機能確認・計測器検証用で、絶対速度も相対順位もARM実機の代理にしない。ARMのAES拡張・NEON実装を確認し、x86のAES-NIと混同しない。`/proc/crypto` は登録済み実装だけなので、固定Kconfig・module一覧・明示load結果・benchmarkが受理する組合せと照合し、不在/未load/不適用を区別する。
- 採否基準: 元の「adiantum sequential writeがAESの1.2倍超なら検討」という数値を保持するが、適用先は同条件の実機測定。LUKS cipherは利用者指定どおり当面aes-xts-plain64を維持。key sizeとsecurity strengthは別（XTSの2本分合計長を安全性bit数にしない）。最終判断は安全性要件と実機性能の両方で行い、QEMU順位で変更しない。
- 反復: 各cipher・hash 5回。全候補の入力・非対応理由・失敗logとbinary/config hashを保存する。

### B5. btrfs mkfs/mount option（QEMU guest + fs-compare 連携）

- 目的: `mkfs.btrfs --csum xxhash -m dup -d dup` を基準に csum {crc32c,xxhash,sha256,blake2b}、nodesize {4K,16K,32K}、mount `compress=zstd:{1,3,9}`/compress-force/commit={30,5,0}/ssd, nossd/autodefrag/space_cache/thread_pool/flushoncommit/max_inline を測る。
- 方法: 既存 fs-compare harness（`fs-compare-configs.tsv`）に variant を追加して T4-sync・T5・write inventory を測る。E3/E4 matrix 完了後に同じ機構で。
- 採否基準: idle 書き込みが規則（§10: 操作なし・progress なしで書き込みなし）を満たす構成であること。数値基準として、T4-sync/T5 の idle window で quiesce 後の書き込みが 0 sector であること、write inventory の総 sector 数が ext4 base 比 +15% 以内であること。
- 反復: 各 variant 5回。

### B6. zram/zswap（QEMU guest）

- 目的: zramは `comp_algorithm` で名前、`algorithm_params` でzstdの既定/1/9を設定。zswapは実装可能なcompressor、`max_pool_percent` {10,20,40}等の5 parameterを比較。旧計画のzpool {zbud,z3fold,zsmalloc}切替は6.18.59に公開parameterがなく実行不能として分離する。
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
