# 2026-11-15 二セッションの証拠と復元限界

[監査本文](session-audit-2026-11-15.md) / [判断](session-decisions-2026-11-15.md) / [残件](session-followup-2026-11-15.md)

## 対象と読めた範囲

| session | 対象ID | event照合 |
|---|---|---|
| 03914・実装状況の確認と今後の計画 | `03914d06ecff4447a74024c8c9c5eabc` | details/listとも1189、unique 1189、不足0・余分0 |
| 5917・実測・実験 | `5917cbf6493a4629beebffd56807a507` | details/listとも12810、unique 12810、不足0・余分0 |

これはevent IDの収録検査です。`output_trunc`の省略部分や`contents_key`が指す本文まで読めた証明ではありません。全31利用者/Automationメッセージの原文、別の構造化回答4件、shell command・非0終了・file編集metadata・PR/CI記録を抽出しました。raw events-details dumpをそのまま公開してはいません。

S0の分析は**訂正前の監査時点**の記録です。「未修正」「保存が必要」等の現在地は[本監査](session-audit-2026-11-15.md)で更新し、旧分析そのものは変更しません。

## 固定された保存先

data枝は`data/fs-compare-experiments`です。主枝へmergeする製品sourceではありません。固定commitのURLとmanifestを根拠とし、作業環境だけにあるpathを根拠にしません。

| 記録 | 保存先・照合範囲 |
|---|---|
| S0救済・分析 | [5bc9844のsessions-2026-11-15](https://github.com/uist1idrju3i/MSD-Linux/tree/5bc9844af3b39212252ed6361ff7c5e66f8bc110/sessions-2026-11-15)。`evidence.tar.gz`、`manifest.json`、`evidence.files.sha256`、`SHA256SUMS` |
| S0 archiveの中身 | 146 file、展開後16,272,608 bytes。未保全text候補87件、check_fec/build driver、抽出command・失敗command・file event、PR/CI、復元添付と限界注記、分析。`audit/analysis-2026-11-15.md`と`attachments/manifest.csv`が対応の入口 |
| E34本体 | [e9d4d14時点のfs-compare](https://github.com/uist1idrju3i/MSD-Linux/tree/e9d4d1431bb3fafb91a8c3c449ad99be6d6992ed/fs-compare)内の`e34-matrix.tar.zst`。1073 memberを既存manifestへ照合、178 attempt中174成功・中断4、178本の`inputs.sha256`を確認 |
| E34追補 | [e9d4d14のe34-provenance](https://github.com/uist1idrju3i/MSD-Linux/tree/e9d4d1431bb3fafb91a8c3c449ad99be6d6992ed/fs-compare/e34-provenance)。plan、dirty patch、10 harness input写し、driver snapshot、元集計event、集計器・fixture、中断一覧、manifest計21 file |
| B1/B2/B3・E1/E2等の実験 | [実験索引](../../experiments/README.md)から各実験の固定data URL/hashへ進む。B3は最終35 serial logを独立再読し、archive内とbyte一致を確認。B3機能成功・製品rollbackの証明とは別 |

SHA-256は次のとおりです。保存後の一致は、hash未収録の過去入力や未保存binaryの同一性まで保証しません。

```text
S0 evidence.tar.gz
def757086e5b64289892662ce7d786ac8debb1323a94fe98dfef4f0c9625c513
E34 e34-matrix.tar.zst
3369f24a65454966d6ea2ad59360221740d39d4f74d82e02ecfcd588790b4530
E34 e34-provenance/SHA256SUMS
d067f83a7a333b9267b05c04cf8b1ce938741f322947065f5c32f7353afd2df2
E34 plan.tsv
ad6272601ea036db8300362e728365954c23a59ea264d15b79c087a0a88d0949
```

S0は指定されたcredential patternを検査し、対象archiveで検出0、redact 0行でした。raw events-details dump、image、巨大binary、秘密鍵本文は含めていません。pattern検査は秘密情報が一切存在しないという一般的保証ではありません。E34の10 harness inputは全記録hashと一致しましたが、matrix driver自体は当時のruntime hashがないため、現在のsnapshotとして保存しています。

## 完全復元できなかった添付

S0の`attachments/manifest.csv`は18添付版を記録しています。**期待hashに一致する復元は8版、本文なしは10版**です。分析要約の「03914の3原本と5917初期memo2版」だけでは不足していました。全manifestを再照合すると、5917の復元不能memoは**7版**です。原文がない版には復元限界と会話抜粋だけを保存し、完全復元とは数えません。

| session・file | 復元不能attachment ID |
|---|---|
| 03914 `msd-linux-plan-2026-11-15.md` | `f6c4be80-12ae-42b7-a8da-61aa6f1e15bb` |
| 03914 `msd-linux-phase-a-plan-2026-11-15.md` | `8c7fc1b4-9cdf-4f0b-be67-fcae4b6d182b` |
| 03914 `msd-boot-slot-display-memo-2026-11-15.md` | `1ea71a54-a87b-4724-9c36-f2404ddc1509` |
| 5917 `memo-2026-11-15-interruption-and-new-task.md` | `6bc7c15d-6372-4320-8942-5cb61e37edf8` |
| 同memoの別版 | `e15e82ef-4917-4cbe-b730-1cdd91e637be` |
| 同memoの別版 | `0038c2b8-1c70-40e2-a13a-f17c040db552` |
| 同memoの別版 | `05ad25a8-d0d2-4874-b59f-8afc78bd0a6b` |
| 同memoの別版 | `ee3391ed-4743-48b6-b74a-f912a1389600` |
| 同memoの別版 | `221d4cd1-80a1-4088-9401-88e2de0477da` |
| 同memoの別版 | `f3e84d6f-2192-43db-b538-1474a762cd46` |

5917の計画・user-actions・最終memoと現存原本prefixに一致した旧memoは、manifestに期待hashと復元方法があります。添付URLが存在するだけで本文を取得済みとはしません。完全な原本のexportが得られるまで、R01〜R44やPhase A全文の再構成は未完了です。

## 保存監査の限界

今回の87 text候補はこの二セッションで抽出した対象です。さらに古い全実験履歴・失われたbinaryまで完全保全したという主張ではありません。runtime入力のhash、現在残る写しのhash、添付期待hash、archive自身のhashを混同しません。

S0・E34追補はremote保存済みで、旧raw/CSVと失敗attemptを残しています。研究への反映先は[監査本文](session-audit-2026-11-15.md)・[判断](session-decisions-2026-11-15.md)・[残件](session-followup-2026-11-15.md)です。新実測がなくても、次回は実施条件・全失敗・完了marker・性能の有効性・保存hashを実験単位で照合してから完了を報告します。
