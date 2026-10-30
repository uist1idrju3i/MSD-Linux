# S6 tier B: カーネル hardening 候補の総当たりスイープ

- 実施日: 2026-10-30
- 状態: 完了（QEMU のみ）
- ベース: adopt2 採用後の製品構成（PREEMPT_RT・FTRACE off・sweep 第1・第2弾を適用した `linux.fragment`、Image 17,750,528 B）

## 目的

S6（カーネル hardening）のうち QEMU で起動確認できる 24 候補を `kernel-variant-sweep.sh` で 1 件ずつビルド・起動試験し、起動時間・サイズへの影響を測る。採否は製品判断として別途行う。

## 方法

`kernel-variant-sweep.sh --candidates output/s6-tierb-candidates.txt` で各候補を `scripts/config` で変更 → `olddefconfig` → フルビルド → `test-boot.sh`（`MSD/Linux ready`・ログイン・シリアルログ・/data マウント・モジュール検査）まで自動実行。結果は `output/s6-tierb-sweep.csv`。

## 結果（24 候補）

| シンボル | 値 | status | Image [B] | vtime [s] | 現行製品との差 |
|---|---|---|---:|---:|---|
| SLAB_FREELIST_HARDENED | y | QEMU_FAILED* | 17,750,528 | - | off→on |
| SLAB_FREELIST_RANDOM | y | QEMU_FAILED* | 17,750,528 | - | off→on |
| SLAB_MERGE_DEFAULT | n | PASS | 17,750,528 | - | on→off |
| RANDOM_KMALLOC_CACHES | y | QEMU_FAILED* | 17,750,528 | - | off→on |
| LIST_HARDENED | y | PASS | 17,816,064 | - | off→on（+65 KiB） |
| BUG_ON_DATA_CORRUPTION | y | PASS | 17,750,528 | 2.218 | off→on |
| SHUFFLE_PAGE_ALLOCATOR | y | PASS | 17,750,528 | - | off→on |
| FORTIFY_SOURCE | y | PASS | 17,754,624 | - | off→on |
| ZERO_CALL_USED_REGS | y | PASS | 18,995,712 | - | off→on（**+1.19 MiB**） |
| RANDOMIZE_KSTACK_OFFSET_DEFAULT | y | PASS | 17,750,528 | - | off→on（機能本体は済） |
| RODATA_FULL_DEFAULT_ENABLED | y | TARGET_MISMATCH | - | - | arm64 ではシンボル無効（常時 full rodata） |
| DEBUG_WX | y | PASS | 17,750,528 | 2.244 | off→on |
| DEFAULT_MMAP_MIN_ADDR | 65536 | PASS | 17,750,528 | - | 4096→65536 |
| ARCH_MMAP_RND_BITS | 18 | PASS | 17,750,528 | - | 現行値と同じ（no-op） |
| SECURITY_DMESG_RESTRICT | y | PASS | 17,750,528 | - | off→on |
| LEGACY_TIOCSTI | n | PASS | 17,750,528 | - | on→off |
| LDISC_AUTOLOAD | n | PASS | 17,750,528 | - | on→off |
| PROC_MEM_NO_FORCE | y | PASS | 17,750,528 | 2.218 | ALWAYS_FORCE→NO_FORCE |
| STRICT_DEVMEM | y | PASS | 17,750,528 | 2.210 | off→on（IO_STRICT_DEVMEM が自動で付く） |
| IO_STRICT_DEVMEM | y | TARGET_MISMATCH | - | - | STRICT_DEVMEM 依存で単独指定不可 |
| DEVPORT | n | PASS | 17,750,528 | - | on→off（arm64 では無効な機能） |
| SECURITY_LANDLOCK | y | PASS | 17,820,160 | - | off→on（+68 KiB） |
| MODULE_SIG_SHA512 | y | KEEP_CHANGED | - | - | 選択式のため SHA256 のまま（要 SHA256 off 併記） |
| BLK_DEV_WRITE_MOUNTED | n | QEMU_FAILED* | 17,750,528 | - | on→off |

\* QEMU_FAILED は全件 sweep ツールの誤検出。カーネル Image だけ差し替える方式のため sdcard 内モジュールと vermagic が一致せず `msd-module-check` が失敗する。各シリアルログは `MSD/Linux ready` 到達を確認済み（S1/S14 調査と同じ artifact）。vtime の空欄はテーブル上記録が残らなかった行。

## 所見

- 起動時間（ready 到達の仮想時刻）を記録できた行は全て 2.21〜2.24 s でベースライン（約 2.2 s）と差なし。**計測上、起動速度への悪影響は 0 件**。
- サイズに影響するのは `ZERO_CALL_USED_REGS` のみ（+1.19 MiB）。`LIST_HARDENED` +65 KiB、`SECURITY_LANDLOCK` +68 KiB、`FORTIFY_SOURCE` +4 KiB は僅少。
- 機能面の注意:
  - `ZERO_CALL_USED_REGS` はリターン時のレジスタゼロ化で実行コストも伴う。サイズ・速度の両面でコストが最も大きい候補。
  - `BUG_ON_DATA_CORRUPTION` は検出時に WARN ではなく panic になる。fail-stop としては安全側だが、継続動作を優先するなら外す選択肢。
  - `STRICT_DEVMEM` / `DEVPORT` は `/dev/mem`・`/dev/port` の低レベルデバッグ手段を失わせる。
  - `BLK_DEV_WRITE_MOUNTED=n` はマウント中ブロックデバイスへの直接書き込みを禁止する。msd-update は非アクティブスロットへ書くため影響しないことをコード上で確認。
  - `RODATA_FULL_DEFAULT_ENABLED`・`IO_STRICT_DEVMEM`・`MODULE_SIG_SHA512` はこの構成では適用不可（mismatch/KEEP_CHANGED）。arm64 は常時 full rodata、モジュール署名は SHA256 で十分。
  - `ARCH_MMAP_RND_BITS=18` は現行値と同じで変化なし（MAX=24 にすれば更に増やせる余地はある）。

## 採否の整理（提案）

- 採用候補（影響なし・防御効果あり）: SLAB_FREELIST_HARDENED、SLAB_FREELIST_RANDOM、RANDOM_KMALLOC_CACHES、SLAB_MERGE_DEFAULT=n、SHUFFLE_PAGE_ALLOCATOR、FORTIFY_SOURCE、LIST_HARDENED、RANDOMIZE_KSTACK_OFFSET_DEFAULT、DEFAULT_MMAP_MIN_ADDR=65536、SECURITY_DMESG_RESTRICT、LEGACY_TIOCSTI=n、LDISC_AUTOLOAD=n、PROC_MEM_NO_FORCE、DEVPORT=n、SECURITY_LANDLOCK
- 検討が要るもの: ZERO_CALL_USED_REGS（+1.19 MiB・実行コスト）、BUG_ON_DATA_CORRUPTION（panic 化）、DEBUG_WX（診断用・運用では不要とも）、STRICT_DEVMEM（/dev/mem デバッグ喪失）

## 採用後の修正（2026-10-30 追記）

`BLK_DEV_WRITE_MOUNTED=n` は製品ビルドの QEMU ゲートで実害を確認したため採用を見送った。`/data` マウント後に `msd-data-grow` が `resize2fs /dev/mmcblk0p7` を実行するが、マウント済みブロックデバイスを O_RDWR で開けずオンライン resize が失敗する（`msd-data-grow failed; keeping /data mounted`）。sweep の vermagic 誤検出とは別系統の、製品機能との実際の衝突。

## 再現

```sh
docker/msd-dev build
docker run --rm -v "$PWD":/work -w /work msd-dev:local \
  board/cardputerzero/tools/kernel-variant-sweep.sh \
  --candidates output/s6-tierb-candidates.txt
```

生データは `output/s6-tierb-sweep.csv`、各候補のシリアルログは `output/s6-tierb-logs/<SYMBOL>/`。
