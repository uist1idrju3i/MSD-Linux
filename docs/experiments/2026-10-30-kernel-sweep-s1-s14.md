# S1・S14 本番: カーネル config 総当たりスイープ（80 候補）

- 日付: 2026-10-29〜2026-10-30
- 実施環境: 開発用コンテナ（msd-dev:local）、QEMU 11.1.2、icount `shift=0,sleep=off`
- ツール: `board/cardputerzero/tools/kernel-variant-sweep.sh`（#117 の修正版: 失敗試行のログ保存・既定 image パス修正）
- 対象ツリー: `output/`（linux-custom、6.18.58-v8、PREEMPT_RT 前の fragment）
- 生データ: `output/kernel-sweep.csv`（gitignore 対象、添付せず本記録に要約）

## 方法

RESEARCH の S1（不要 config の削減）・S14（アーキテクチャ機能の見直し）の候補 80 件について、1 候補ずつ `linux.fragment` を変更 → `linux-rebuild` → gzip サイズ差分を計測 → QEMU で `MSD/Linux ready` 到達まで起動確認、を繰り返した。所要約 21 時間。

status の意味:

- `PASS`: QEMU で ready 到達
- `QEMU_FAILED`: ビルドは成功したが QEMU の起動検証が失敗（タイムアウトや ready 未到達など。詳細は `output/sweep-logs/` 各候補のログ）
- `TARGET_MISMATCH`: その時点の .config にシンボルが存在せず試行不可
- `KEEP_CHANGED`: 候補値が既に設定値と一致し変更不要

## 集計

| status | 件数 |
|---|---:|
| PASS | 61 |
| QEMU_FAILED | 12 |
| TARGET_MISMATCH | 5 |
| KEEP_CHANGED | 1 |

## PASS で効果が大きかった候補（kernel8.img.gz の差分）

| シンボル | 値 | gz 差分 [B] | 備考 |
|---|---|---:|---|
| ARM64_USE_LSE_ATOMICS | n | -155,337 | Cortex-A53 は ARMv8.0 で LSE 非搭載。生成コード上も不要 |
| EROFS_FS | n | -39,751 | ルート FS は SquashFS 維持が確定（#126）。EROFS 不要 |
| ARCH_BRCMSTB | n | -32,939 | BCM2837（BCM2710）のみ対象で BRCMSTB SoC 不要 |
| ARM64_HW_AFDBM | n | -5,040 | A53 にハードウェア AF/DBM なし |
| ARM64_BRBE | n | -3,579 | A53 に BRBE なし |
| ARM64_POE | n | -2,973 | A53 に POE なし |
| ARM64_TLB_RANGE | n | -2,281 | TLB range invalidate は A53 非対応 |
| NUMA_EMU | n | -2,130 | エミュレーション用途のみ |

PASS 全 61 件の gz 差分の合計は約 -250 KiB。大半は誤差範囲の微小差だが、上表の SoC/CPU 機能系は「CM0 では使われない機能」なので副作用リスクが小さい。

## QEMU_FAILED で注視すべき候補

| シンボル | 値 | gz 差分 [B] | qemu_ready_vtime | 考察 |
|---|---|---:|---:|---|
| CC_OPTIMIZE_FOR_SIZE | y | -1,504,298 | 3.69 | カーネル自体の -Os。gz で -1.5 MB と最大級だが起動失敗。FUNCTION_ALIGNMENT と collateral が出ており要調査 |
| FTRACE | n | -1,294,262 | 2.03 | 既に製品採用済み（#135）。sweep 環境では QEMU_FAILED 判定だったが、製品構成では ready 到達を確認済み |
| NUMA | n | -62,620 | 3.17 | シングルノード構成で NUMA 無効化は有望だが起動失敗。別途調査 |
| CPU_IDLE / HOTPLUG_CPU / NODES_SHIFT | n/1 | -13 〜 -15 K | - | いずれも起動失敗。CPU 周りの前提が絡む |
| ARM64_SVE / SME / MTE / GCS / ERRATUM_4193714 | n | -2.3 〜 -19 K | - | A53 非対応機能だがいずれも起動失敗。原因は sweep の個別ログ参照 |
| FTRACE_SYSCALLS | n | -56,708 | 3.33 | FTRACE=n とセットで効果が出る類。起動失敗は sweep 環境側の要因の可能性 |

## TARGET_MISMATCH / KEEP_CHANGED

- TARGET_MISMATCH（.config にシンボルなし）: ARM64_LSE_ATOMICS（=USE_LSE_ATOMICS の別名）、ARM64_PAN、PROBE_EVENTS、KPROBES、KALLSYMS_ALL —— 依存条件で見えないか既に目的値。追加の作業不要
- KEEP_CHANGED: ARM64_PTR_AUTH=n（既に目的値）

## 結論と採用候補

- 既に採用済み: FTRACE=n（#135）
- 本実験で新たに採用を提案するセット（全て PASS、CM0/BCM2837 で使用されない機能の OFF）:
  `CONFIG_ARM64_USE_LSE_ATOMICS=n`、`CONFIG_EROFS_FS=n`、`CONFIG_ARCH_BRCMSTB=n`、`CONFIG_ARM64_HW_AFDBM=n`、`CONFIG_ARM64_BRBE=n`、`CONFIG_ARM64_POE=n`、`CONFIG_ARM64_TLB_RANGE=n`、`CONFIG_NUMA_EMU=n`
  合計で gz 約 -244 KiB。QEMU 回帰で再確認のうえ linux.fragment へ追加する。
- 追加調査が必要なもの: `CC_OPTIMIZE_FOR_SIZE=y`（-1.5 MB と最大だが起動失敗）、`NUMA=n`、`ARM64_SVE/SME/MTE/GCS` 系（いずれも起動失敗の理由を sweep ログで特定してから再試行）
- 効果なし・採用不可: 残りの PASS 候補（差分 ±2 KiB 未満）は積み上げても効果が出ないため見送り

## 再現

1. `docker run -d -v $PWD:/work -w /work msd-dev:local board/cardputerzero/tools/kernel-variant-sweep.sh <候補リスト>`
2. 結果は `output/kernel-sweep.csv`、各試行のログは `output/sweep-logs/<symbol>.log`
