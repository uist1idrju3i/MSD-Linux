# dm-verity(crc32c)+FEC の破損注入試験（B3）

2026-11-15。root=SquashFS+dm-verity(crc32c)+FEC 方針（[設計調査](../research/storage/rootfs-squashfs-verity-fec-design.md)）に対し、破損を注入した sdcard image で QEMU 起動を反復し、検出・訂正・停止の挙動を確認した。

## 条件

- kernel: `devin/1794708015-kernel-config-integrity` の `output-integrity` ビルド（`DM_VERITY=y`、`DM_VERITY_FEC=y`、`DM_CRYPT=y`、`BTRFS_FS=y`、`CRYPTO_CRC32C=y`、`CRYPTO_ZSTD=y`）。起動 log に `device-mapper: verity: crc32c using "crc32c-lib"` を確認
- hash tree + FEC: `board/cardputerzero/tools/dm-verity/verityfmt`（自前実装）が生成。crc32c は `veritysetup format` が userspace で拒否するため同 tool を使用。`data_blocks=5832`、`hash_start_block=5833`、`hash_area_blocks=7`、salt 32 byte。FEC は `fec_roots=8`（RS(255,247)）・`fec_blocks=5839`・`fec_start=5840`・interleave `rounds=24`（cryptsetup `VERITY_FEC_process` と kernel `dm-verity-fec.c` の `fec_interleave` と同じ配置）
- error mode: `panic_on_corruption`（F6 のみ `restart_on_corruption`）
- 実行: `docker/msd-dev bash board/cardputerzero/tools/bench/dm-verity-fec/run-all.sh /work/output-fscmp /work/output-b3/cases /work/output-b3/results-b3 4 480`（各 case 5 boot・timeout 480s・`--expected` で起動結果を照合）
- case 生成: `board/cardputerzero/tools/bench/dm-verity-fec/make-case.sh`（rootfs.img への byte 反転を注入）
- QEMU raspi3ap + icount（TCG）。QEMU での結果であり実機の挙動確認ではない

## case と結果

| case | 注入内容 | FEC | error mode | 期待 | 結果（5 boot） | 判定 |
|---|---|---|---|---|---|---|
| F0-A2 | なし（clean） | あり | panic | ready | 5/5 ready | 期待通り |
| F1-A2 | data block 2916 の 1 byte 反転（offset 11944059） | あり | panic | ready（FEC で訂正して起動） | 5/5 で `FEC 49152: corrected 1 errors` の後 ready | 期待通り。**FEC が data block の 1 bit 破損を訂正して起動** |
| F2-A2 | data 領域 24 block に各 1 byte 反転（分散、rsn=247・rounds=24 の interleave 全域） | あり | panic | verity-error | 5/5 で `corrected 8 errors` の後 `failed to correct (8 erasures)` → `Kernel panic: dm-verity device corrupted` | 期待通り。訂正能力超過で検出・panic |
| F3-A2 | **最上位 hash block 5833 の 1 byte 反転**（offset 23891985、top level の digest index 4 内） | あり | panic | ready（FEC で訂正して起動） | 5/5 で `metadata block 5833 is corrupted` → `Kernel panic` | **期待と不一致。訂正されず panic**（後述） |
| F4-A2 | cmdline の root_hash 改ざん（`2a3f426f` → `2a3f4260`。image 無改変） | あり | panic | verity-error | 5/5 で `metadata block 5833 is corrupted` → panic | 期待通り。root_hash 不一致を検出 |
| F5-A2 | data block の 1 byte 反転（F1 と同じ offset） | **なし**（fec_roots=0） | panic | verity-error | 5/5 で `data block ... is corrupted` → panic | 期待通り。FEC 無しでは 1 bit でも panic |
| F6-A2 | F2 と同じ 24 block 分散反転 | あり | **restart_on_corruption** | verity-error | 5/5 で `corrected 8 errors` → `data block 0 is corrupted` → restart（QEMU は no-reboot で終了） | 期待通り。panic の代わりに restart を選択 |

## F3 の分析: 最上位 hash block の破損は FEC で救えない

F3 は「FEC が修復できる程度の破損で起動継続（ready）」を期待した case だが、5/5 全て panic した。切り分けの結果:

- **formatter（verityfmt）のバグではない**。F0-A2 の rootfs.img について、全 24 round × 4096 byte 列の RS(255,247) parity を同じ符号化器で再計算して保存 parity と照合したところ **全 98,304 列が一致**（hash 領域を含む covered=5839 block 全体）
- kernel の動作で説明できる。`verity_verify_io` で hash block 5833 の verify が root_hash と不整合 → `verity_fec_decode(METADATA, 5833)` → `fec_decode_rsb` が RS 入力 block を読む際、data block 入力は `verity_hash_for_block` で検証される → その検証は（壊れた）最上位 block 5833 の digest に依存 → `fio->level` の再入ガードで nested decode が `-EIO` → `verity_handle_err` → `panic_on_corruption` で panic。stack trace も `verity_fec_decode → fec_decode_rsb → verity_hash_for_block → verity_verify_level → verity_handle_err` の順で一致する
- つまり FEC の parity は hash 領域を正しくカバーしているが、**最上位 hash block を含む検証経路上の破損は `panic_on_corruption` 下では訂復前に panic する**。kernel の `panic_on_corruption` と FEC の入力検証の組み合わせによる制約であり、`error_mode=eio`/`restart` なら nested verify が -EIO を返して decode が完了する可能性がある（未検証）
- 製品要件への影響: 破損検出自体は成立しており、panic → tryboot → A/B 切り戻しの経路で要件は満たせる。FEC が役に立つのは data block（F1 で実証）と検証経路の上位に無い下位 hash block の破損で、**最上位 hash block の破損は A/B 切り戻しで救う**設計とする

## F5/F6 が示す対照

- F5（FEC 無し）: F1 と同じ 1 byte 反転でも panic。FEC の有無で「1 bit 破損を透過修復して起動継続するか、panic するか」が分かれた
- F6（restart_on_corruption）: panic の代わりに `data block 0 is corrupted` の後 restart。QEMU（no-reboot）ではそこで終了。実機では restart → firmware の tryboot 機構に繋がる想定（QEMU では tryboot 自体は検証対象外）

## 生データと再現

- `output-b3/results-b3/<case>/boot*/` に serial log・result.txt、`<case>.csv` に各 run の wall 秒・exit_status・log SHA-256。data branch `data/fs-compare-experiments` の `fs-compare/b3-dm-verity-fec.tar.zst` に同梱
- オフライン parity 検査: session 上の check 用 C tool（verityfmt と同一の RS 符号化）で rootfs.img の全列を再計算・照合

## 失敗した試行・注意点

- F3 の期待値 `ready` は kernel 実動作と合わず 5/5 で panic — case 設計の期待値が実際の kernel 挙動を反映していなかった（記録として残す。`run-all.sh` の期待値表は「実測は panic」と分かるよう後続で修正する）
- 各 run の csv は `valid=0` — `msd.boottime=1` 由来の dmesg dump 行が serial に無いため parse 不可。検出・ready は serial timestamp と marker で個別に確認した
- QEMU/TCG での挙動。実機での検出・panic・restart・tryboot 連携は `docs/research/verification/hardware-measurements.md` の実機計測計画に含める

## 未確認

- `error_mode=eio`/`restart` での最上位 hash block 破損の訂復可否（追加 case で検証可能）
- restart_on_corruption の実機での tryboot 連携
- 破損が FEC parity 領域・superblock 領域に入った場合の挙動（別 case で要検証）
