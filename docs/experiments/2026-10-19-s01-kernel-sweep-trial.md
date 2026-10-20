# S1 カーネル設定スイープ試行

- 状態: 完了（ツールのみ。本番構成の採否は未実施）
- 日付: 2026-10-19
- 担当: Devin
- 関連: PR #25、[S1–S17 検証計画](../research/simulation-plan.md#シミュレーション検証計画s1s17)

## 目的と仮説

`kernel-variant-sweep.sh` で候補設定の Image サイズと gzip サイズを測る。サイズ改善だけでは採用せず、QEMU を実行した候補は起動結果も採否に使う。

## 採否の基準（結果を見る前に書く）

QEMU を実行していない候補はツール試行としてのみ記録し、本番構成には採用しない。QEMU が失敗した候補はサイズ差だけで評価しない。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `e1c1efb299f6b1c6eb353295ff453e62ea3b041e` |
| ホスト | Ubuntu 22.04 |
| QEMU | 6.2.0 |
| Buildroot / GCC / カーネル | 2026.08 / 14.3.0 / 6.18.57-v8 |
| 出力先と状態 | `OUTPUT_DIR=<Buildroot の O= ディレクトリ>`。再利用したローカル output |
| 変える条件 | `CONFIG_SQUASHFS_LZ4=n`、`CONFIG_NUMA=n` |
| 変えない条件 | 各候補で元の `.config` に戻し、スクリプトの keep-list 検査を実行 |
| 繰り返し | 各候補 1 回。中央値は算出しない |

## 手順

`--no-qemu` はスクリプトの `NO_QEMU` を有効にし、QEMU 測定欄を空のままにする。NUMA 行は QEMU を実行したが失敗した。

```sh
REPO=<リポジトリのルート>
OUTPUT_DIR=<Buildroot の O= ディレクトリ>
LOG_DIR=<ローカルログの保存先>
SWEEP_CSV="$LOG_DIR/s01-kernel-sweep.csv" \
OUTPUT_DIR="$OUTPUT_DIR" \
"$REPO/board/cardputerzero/tools/kernel-variant-sweep.sh" --no-qemu
```

## 計測器の検証

スクリプトは候補ごとに `.config` と `Image` を退避・復元し、QEMU 実行時は保存した serial log から ready 時刻を抽出する。QEMU を実行しなかった `SQUASHFS_LZ4=n` は起動試験の結果ではない。NUMA 行の `~166` は ready 行に時刻がなかったため、awk が直前の printk 時刻を近似値として出したものだった。

## 結果

生データは同名 CSV に全列そのまま保存した。

| 候補 | 状態 | Image bytes | gzip bytes | gzip 差 | QEMU ready 欄 |
|---|---|---:|---:|---:|---|
| `SQUASHFS_LZ4=n` | PASS（QEMU 未実行） | 26,249,728 | 10,494,603 | −439 B | 空欄 |
| `NUMA=n` | QEMU_FAILED | 26,188,288 | 10,430,258 | −64,784 B | `~166`（直前の printk 時刻） |

## 捨てた試行と経緯

NUMA=n は QEMU_FAILED であり、結果を判定しない。QEMU log はスクリプトの一時ディレクトリに置かれ、後から失われたため、ログを保持する条件で再試験が必要である。PR #25 の以前の報告では −64,784 B のサイズ差を記載した一方、QEMU_FAILED を併記していなかった。

## 結論

S1 はツール試行のみで、本番設定の採否は未決である。`SQUASHFS_LZ4=n` の差はこの測定の gzip サイズ差であり、QEMU 動作や実機性能の根拠ではない。NUMA=n は再試験まで未判定とする。

## 未確認の点

NUMA=n の QEMU 起動失敗の原因と、保持したログで再実行した場合の結果は未確認である。実機での効果も測定していない。

## ログ

大きな QEMU log は保存されていない。生の CSV は本リポジトリ内の同名ファイルにある。
