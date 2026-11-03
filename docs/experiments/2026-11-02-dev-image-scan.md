# 開発用OCIの検出と報告器の確認

- 状態: 完了。報告器の確認であり、Brotliの修正版は未導入。
- 日付: 2026-11-02 UTC
- 担当: Devin
- 関連: [調査と判断](../research/operations/development-image-security.md)、[追跡Issue](https://github.com/uist1idrju3i/MSD-Linux/issues/59)

## 目的と採否の基準

探索的なTrivyの走査は先に1回実施しました。性能を測る試験ではなく、固定OCIのpackageとadvisoryを照合する確認です。そこで見つかったCRITICALの詳細が、従来の本文に表示されない問題を調べました。

報告器のA/A試行では、同じ走査JSONを5回入力します。各回の終了値が0、全件JSONに2184件と公開ゲート対象1件が残ること、本文の最初の項目が`CVE-2026-111497`であること、5回の本文とJSONのhashがそれぞれ一致することを、実行前に採用の条件としました。走査の5回反復や性能比較とは扱いません。

## 条件

| 項目 | 条件 |
|---|---|
| 基準commit | `916a45e80545fb5ecf3546873ce332093b0501f2` |
| 変更するもの | `trivy-gate.py`の本文の並び順と、安全な全件JSONの出力 |
| 固定するもの | 入力JSON、Python、各回のCLI引数。実行中は報告器を編集しない |
| OCI、Trivy、DB | [調査の確認値](../research/operations/development-image-security.md#対象と確認の限界)を参照 |
| ホスト、Python、入力と実行コードのhash | 同名の[JSON](2026-11-02-dev-image-scan.json)に記録 |
| Buildroot、GCC、kernel、QEMU | 構築・起動せず、この試行では使わない |
| 出力 | 各回を別名に保存し、既存の出力には上書きしない。Buildrootの`O=`、ccache、warm/coldは該当しない |

## 手順と負の対照

元の走査の手順は[調査文書](../research/operations/development-image-security.md#再検査の手順)にあります。同じDBを再取得できない場合は件数が変わります。DBの更新日時と元JSONのhashを、同名JSONと比較してください。

報告器は、その走査JSONに対して次のように繰り返します。`out`は走査時に作った出力先です。

```sh
for n in 1 2 3 4 5; do
  test ! -e "$out/findings-$n.json"
  test ! -e "$out/report-$n.md"
  python3 .github/scripts/trivy-gate.py report "$out/trivy.json" \
    --findings-json "$out/findings-$n.json" > "$out/report-$n.md"
  sha256sum "$out/findings-$n.json" "$out/report-$n.md"
done
tests/trivy-gate/run.sh
```

基準commitの報告器も同じ入力で1回動かし、本文にBrotliの識別子がないことを負の対照にします。合成入力による回帰テストでも、120件のLOWの後ろにHIGH/CRITICALを置き、表示の打ち切りと全件JSONを区別します。秘密値を模した文字列が、本文と保存JSONに出ないことも検査します。

## 結果

[CSV](2026-11-02-dev-image-scan.csv)の全6行と、同名JSONへ結果を記録しました。負の対照は終了値0でしたが、Brotliの識別子は本文に出ませんでした。改修後の5回はすべて終了値0で、全件2184件・公開ゲート対象1件を保存し、本文の最初にBrotliを表示しました。本文と全件JSONのhashは5回ともそれぞれ一致し、採用の基準を満たしました。件数は全5回で中央値・最小・最大とも2184件、公開ゲート対象は同じく1件です。失敗・除外した試行はありません。

元の走査では重大度の選び方に関する警告が出ており、BrotliのCRITICALはNVD由来、修正版があるという状態はDebian由来でした。対象での悪用を確認した結果ではありません。

## 未確認と証拠の限界

- この試行ではOCIの依存を更新しません。Brotliの修正版導入や、配布OSへの影響は別の確認です。
- 週次workflowでのartifact作成・Issue更新はローカルの報告器テストでは確認できません。
- 大きなimage tar、元の走査JSON、生ログ、DBはリポジトリへ入れず、hashを同名JSONへ残します。再生成は上記の手順によります。元JSONにはimage設定が含まれるため、無選別に公開しません。
- 旧workflowには元JSONのartifactがありません。参照したCIの全文とIssueの本文は読みましたが、CIの元JSONを取得・照合したわけではありません。
