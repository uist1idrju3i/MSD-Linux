# 保守監視と署名CLI分類の検証

## 目的・事前条件

基準commitは `7a0d52b2f20889ac23dd6a8fa585a44c3a373866`。Buildrootの版・init・鍵・Brotliを変えず、OpenSSLの上流通常保守期限の見落としと、署名CLI試験のCI分類を改善する。R01/R02の原則承認は台帳へ反映するが、製品実装完了にはしない。

判定は、固定OCI内の回帰5回が全てexit 0、期限当日と翌日の境界・取得失敗・不正入力・Issue条件が期待どおり、署名CLIが常時host試験に含まれ、docsのみと署名試験のみで製品buildを要求せず、製品source・build workflow・判定不能で要求することとする。試験呼出し削除・分類特例削除の改変を検出する。反復は静的A/Aであり、性能比較ではない。

## 実行と結果

開発OCIは `sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、x86_64/Linux 6.8.0-1061-aws、Python 3.13.5、OpenSSL 3.5.7。署名binaryのSHA-256は `acc10176d038aeb7b2a77d9ec972ac2985857a7191f7aecb7c54ef0e2c7e9549`。これは製品のtarget/host-libopenssl 3.6.5ではない。VM側toolchainは使用しない。

[入力hash・実版・取得時刻・一次資料hash](2026-11-03-maintenance-followup.json)、[suite全15行](2026-11-03-maintenance-followup.csv)、[署名コマンド全300行](2026-11-03-maintenance-followup-signing.csv)を保存した。全列を読み、期待値と実exitの一致を確認した。

| 対象 | 反復と結果 | 境界 |
|---|---|---|
| pins回帰 | 5回ともexit 0 | 既存の資格情報保護・全major比較を維持。期限当日/翌日、形式異常、期限欠測/重複/矛盾、recipe/配布/方針の取得失敗とIssue条件を確認 |
| build scope | 6 test methodを各5回、全て成功 | 文書と署名試験、製品source、未知path、新しい署名試験ファイル、PR/push三点差分、manual/schedule、SHA/fetch/diff異常をfixtureで確認 |
| 分類の改変対照 | 5種類を各5回検出 | 呼出し削除・job依存追加・署名試験例外削除・全test除外・build workflow例外削除 |
| 署名CLI | 各suiteで5試験鍵、計25鍵・300 commandのexit一致 | 改変と別鍵の拒否を含む。秘密鍵は試行後に削除され、ログや保存CSVに含めない |
| 公式資料 | 各1回取得成功、固定recipeは3.6.5、配布表は4.1.0/4.0.3/3.5.9 | 時点観測であり性能測定ではない。5回同じ候補を取得しても保守の保証にはならない |

A/Aは同じ入力・OCIの5回反復。suite exitの最小・中央値・最大は全て0で、速度の統計には転用しない。build-scopeのstdout hashが異なるのはunittestの実行時間表示を含むためで、全行のstatusは成功した。pinsログの `Buildroot point release: upstream check unavailable` は意図した負のfixtureであり、公式取得障害の観測ではない。

予備実行では新しいGit stubが空文字を整数へ変換し、6 method中の7 assertionが失敗した。実workflowではなくfixtureの不具合だった。実行終了を待ってstubを修正し、5回反復した。正式採取前の予備実行のstdout hashは未採取で、成功回として数えない。最初の正式5回も成功したが、親reportへのOpenSSL行の接続確認を追加した後、別の出力先で改めて5回実行した。このCSVは後者だけであり、前者と失敗を混ぜない。

actionlint、ShellCheck、zizmor、Python構文、固定値整合の検査も開発OCI内で実行した。文書検査とPRのCIは別の確認であり、後者の結果は実runに戻って判断する。

## 再実行とログ

既存出力先を上書きしない。新しい空の出力名で次を実行する。

```sh
docker/msd-dev python3 docs/experiments/2026-11-03-maintenance-followup.py \
  --output-dir output/maintenance-followup-new --collect-sources
docker/msd-dev actionlint .github/workflows/*.yml
docker/msd-dev python3 .github/scripts/shellcheck-tracked.py
docker/msd-dev zizmor --offline --format=github .github/workflows/
```

runnerは各suiteのstdout/stderr、署名commandごとのログ、一次資料本文とhashを出力先へ残す。今回の最終出力名は `output/maintenance-followup-v2`。大きなログはcommitしない。CSVの各hashからログを照合し、再取得で一次資料が変わったら別試行として扱う。QEMU・実機・新OpenSSL版のbuild/runtime・脆弱性非該当・全依存監視の完成を証明した記録ではない。
