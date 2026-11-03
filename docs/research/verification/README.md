# 検証・測定・未確認事項

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

知りたい内容から本文へ進みます。現行設定、過去の結果、未実施の案を分け、文書・CI・QEMUの検査だけで実機対応済みとはしません。

[今回の配置と原記録の照合](../../experiments/2026-11-02-verification-document-layout.md)には、本文の保存・改変対照・未確認の範囲を記録しています。

| 知りたいこと | 本文 |
|---|---|
| 現在の未確認事項と次の確認 | [主題別の一覧](open-questions.md) |
| 未実施・判断待ち・延期・将来計画の順序 | [残件台帳と要求の対応](../roadmap.md) |
| init移行の計測条件と拒否・復旧試験 | [比較計画](../../experiments/2026-11-03-init-comparison-plan.md) |
| S1–S17の実験・状態・不足 | [試験台帳](experiment-catalog.md) |
| S番号以外のQEMU/生成物の記録 | [確認できる範囲](qemu-coverage.md) |
| UART・通信・ログの条件 | [観測方法](observability.md) |
| 実機で測る指標と機能 | [実機測定](hardware-measurements.md)、[カメラの実行手順](../../VERIFY.md) |
| シミュレーター・代理機の役割 | [基盤比較](platforms.md) |
| 過去の順序と分類 | [計画履歴](planning-history.md) |
| 当初の設計案と未決事項 | [設計履歴](design-history.md) |

利用者の操作は[導入](../../INSTALL.md)・[更新](../../UPDATE.md)、構築は[BUILD](../../BUILD.md)、数値・失敗・再実行は[実験一覧](../../experiments/README.md)へ分けます。

## 証拠の境界

host試験は合成ファイル・stubを使った範囲、製品buildは固定設定からの生成、QEMUは記録したモデル・binary・入力、実機は個体・回路rev・カード・給電条件で判定します。
同じS番号でも、過去の合格を現在のrevisionの合格へ引き継ぎません。設定があること、手順を書いたこと、負の試験が通ることも区別します。
統合・訂正で除いた原記述は[記録CSV](research-records.csv)に保持し、CSV自体を現在の状態表にはしません。
