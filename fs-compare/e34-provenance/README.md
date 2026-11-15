# E34の再集計・実行入力の追補

2026-11-15の監査時に保存しました。元の `../e34-matrix.tar.zst` とCSVは変更しません。archiveの全1,073 memberを既存manifestと照合し、178 attempt（ok 174・signal 15中断4）、入力manifest 178本を確認しました。

| 記録 | 内容と限界 |
|---|---|
| `plan.tsv`、`matrix-summary.csv` | 既存archiveの同名memberをbyteのまま複写。成功174=120 T5（base 6+variant 18を各5回）+54 T4-sync（18構成を各3回）。集計CSVは42群 |
| `interrupted-attempts.csv` | matrix-summaryから4中断attemptを抽出。成功の統計に混ぜず、元logは既存archiveに保持 |
| `harness/`、`harness-manifest.csv` | 現存harnessの写し。10入力は178本のruntime manifestに記録されたhashと全件一致。matrix driver自体はruntime hash未収録のため、現在のsnapshotと区別 |
| `harness.patch`、`base-commit.txt` | b9c57dabf6de17c6cdff5e77293cde8ccd3cf17dからguestとvariant定義へのdirty差分。無関係のB3変更は含めない。runtime hashと一致した写しに対する差分で、当時のindex状態そのものの証明ではない |
| `aggregation-event.txt` | 元セッションのevent-01a1ddc765977c31adfef0cc5ef79174から集計commandを復元した原文。絶対pathも原文として保存し、再現手順の参照先にはしない |
| `aggregate.py` | 今回の可搬な監査用集計器。重複・不足・不正値を拒否。元集計器と同じ13指標をmedian/min/maxへ集約し、既存42群CSVと全fieldを照合する。新規測定ではない |
| `SHA256SUMS` | 本directoryのfile別hash。自己参照とPython cacheを除く |

```sh
python3 test-aggregate.py
python3 aggregate.py plan.tsv matrix-summary.csv --check-csv EXPERIMENTS/2026-11-15-fs-compare-matrix.csv
```

元aggregateは42群の重複を除いて集計しています。初期の一時CSVにはplanの各行に同じ群の集計値を繰り返した174行版もありましたが、研究枝の正式CSVは42行です。旧rawの入力image本文が全て遠隔保存されたという意味ではなく、runtimeに記録されたhashと現存harnessの照合です。実機試験、因果の確定、製品の書き込み規則への適合を示すものではありません。
