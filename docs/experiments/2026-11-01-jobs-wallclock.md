# kernel-variant-sweep `--jobs` の壁時計効果測定

## 目的

PR #145 の `--jobs N`（ワーカー並列化）が同一候補セットで実際にどれだけ時間を縮めるかを測る。

## 条件

- 環境: Devin VM・docker/msd-dev・既存 Buildroot output・kernel 6.18.58
- 候補: `output/jobs-candidates.txt` の 4 件 — ARM64_LSE_ATOMICS=n・ARM64_PAN=n・ARM64_RAS_EXTN=n・NUMA_EMU=n（PASS 2・TARGET_MISMATCH 2）
- 手順: コンテナ内で `kernel-variant-sweep.sh --no-qemu --jobs N --candidates jobs-candidates.txt`、壁時計は `SECONDS`

## 生の値

| run | jobs | wall-clock | 備考 |
|---|---:|---:|---|
| 1 | 1 | **10421 s**（約2.9h） | 実 build 2 件を直列 + mismatch 2 件 |
| 2 | 2 | 1452 s（約24分） | run 1 の ccache が温い → 比較不可 |
| 3 | 2 | 0 s | 両 worker が即死（下の失敗試行を参照） |

## 解釈

run 2 は条件が違うため run 1 と比較できない。run 1 は候補ごとに autoconf.h が変わりほぼフルコンパイル、run 2 はほぼ全オブジェクトが ccache ヒットで ~24 分に縮んだ。

build 1 件あたりの cold 時間は ~85 分程度と見られるので、cold の jobs2 は合計 ~85–95 分（2 台が別々の build を並行）と見込める。run 1 の build 部分 ~174 分に対して約 2 倍、つまりコンパイル律速では worker 数にほぼ比例する。

## 失敗した試行（重要 — この PR で修正）

clean な計測のため `build/linux-custom` を消して `--jobs 2` を実行 → 0 秒で全滅。全 worker が `cp: cannot stat linux-custom` で死んだ。driver は base tree を clone するのに、存在確認せず worker を spawn していた。

修正: driver ブロックの先頭で `linux-custom/.config` と `arch/arm64/boot/Image` の存在を preflight し、無ければ spawn 前に exit 2。検証済み（`EXIT=2`）。

## 測定の限界

公正な A/B は「同一 baseline tree + 冷えた ccache」が前提だが、`--jobs>1` は tree の存在が必須（clone するため）で、1 run での完全クリーン計測はできない。baseline build を作ってから各 arm ごとに ccache をクリアする方法は arm ごとに数時間かかるため、実測値と制約をそのまま記録する判断をした。

## 結論

- `--jobs 2` は実使用で機能し、build 律速の作業では概ね 2 倍速と見込める（冷えた A/B ではなく build 時間からの推定）
- ツールの欠陥を発見・修正: `--jobs>1` で linux-custom 不在時は spawn 前に分かりやすく止まるようになった
