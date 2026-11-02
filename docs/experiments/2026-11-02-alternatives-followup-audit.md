# 代替候補の追加調査と出典の静的照合

- 状態: 資料の反復照合と既存host回帰を完了。代替構成は未実行
- 基準commit: `8c6513a74370c3609f821518563f44bd75d64a9e`
- 関連: [比較の入口](../research/alternatives/README.md)、[出典台帳](../research/alternatives/sources.json)

## 目的・条件と事前の基準

周辺機能、PTXdist・Nix・Debian、XML・FFI・gettext・Python構築部品の比較で残った未確認項目を、公式資料と固定Buildrootの設定から補います。代替をbuild・実行した試験ではありません。

資料の取得と予備的なhash照合は本記録より前に行いました。以下は正式な反復検査の前に固定した基準です。取得前から計画していた試験と読み替えません。

1. 先行台帳547件を変更せず、追加分の全取得成功bytes・SHA-256・判明したGit blob IDが一致し、不一致0件。
2. 取得失敗はURLと理由を残し、成功件数に混ぜない。新しいAPI・公式入口で取得できても旧URLの失敗を消さない。
3. 固定した同一入力のA/Aを5回行い、件数・終了値が一致する。改変bytes・誤ったexpected hash・欠落の3負対照を毎回拒否する。
4. リンク・文字・サイズ・skill・siteと各回帰検査、既存更新のhost試験、固定OCIのactionlint・ShellCheck、offline zizmorが終了値0。警告は別に読む。
5. 日本語はyomiyasuのlint/run/verifyと本文の差分で確認する。新規本文は20,000 B未満とし、資料・現行・提案・未試験の意味を混ぜない。

hostはLinux 6.8.0-1061-aws x86_64/glibc 2.35、Python 3.12.13、Git 2.34.1です。固定開発OCIのimage IDは`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、そこで使ったShellCheckは0.11.0、actionlintはv1.7.12、Pythonは3.13.5です。offline zizmorは1.31.1、yomiyasuは2.4.0です。これは新しいOCIを構築・公開した証拠ではありません。

image・kernel・QEMUを新規buildする試験ではなく、Buildrootの`O=`、ccacheのwarm/cold、候補の性能比較は対象外です。元captureと台帳は固定し、負対照だけをmemory内で変えます。

## 再実行

追加分には`phase=followup`とcaptureの`file`を保存します。台帳から既存の汎用照合runner向けの入力を生成します。`AUDIT_INPUT`は未使用の出力先、`CAPTURES`は各fileに対応する原bytesを保存したdirectoryです。

```sh
python3 - "$AUDIT_INPUT" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path('docs/research/alternatives/sources.json').read_text())
rows = []
for entry in data['sources']:
    if entry.get('phase') != 'followup':
        continue
    row = dict(entry)
    row['status'] = 'failed' if entry['status'] == 'retrieval-failed' else 'retrieved'
    if 'blob_sha' in row:
        row['git_blob_sha'] = row['blob_sha']
    rows.append(row)
with Path(sys.argv[1]).open('x') as stream:
    json.dump({'sources': rows}, stream, indent=2)
PY
for repeat in 1 2 3 4 5; do
    python3 docs/experiments/release-client-audit.py \
        --ledger "$AUDIT_INPUT" --captures "$CAPTURES" --negative-tests || exit 1
done
```

raw URLを再取得する場合、Gitの固定refと、時刻により変わるRelease API・PyPI・manualを区別します。JSONを再整形せず応答bytesを保存します。後日に内容が変わっていた場合は新しい取得時刻と台帳を作り、当日のhashに合わせて資料を変更しません。原bytesがなければ当日の全文を再取得できたと認定しません。

提出前の検査は[先行の自己更新調査](2026-11-02-release-client-audit.md#再実行の手順)と同じcommand群を使います。既存runnerの再利用であり、新しい更新clientや検証protocolは追加しません。実行scriptを動作中に変更せず、再試行は別run IDと生ログにします。

## 結果と未確認事項

出典は先行547件を変更せず、225件を追加して772件になりました。追加分はHTTP取得190件と固定Buildrootからの20件、取得失敗15件です。取得成功210件のbytes・SHA-256と、Git blob IDのある88件が一致しました。5回とも`retrieved=210 recorded_failures=15 git_blobs=88 errors=0`で、stdoutは161 B・同じSHA-256、3種の負対照は毎回拒否しました。速度や統計的同等性は測定していません。

TLSのhostname不一致、古い公式URL、GitHubのRelease API、SDLの存在しないpath等の失敗は残しました。証明書検証を無効にして取得したり、Release APIの404をtag不在・EOLへ読み替えたりしていません。取得可能な公式download、master資料、tag一覧、APIの別経路で補った内容は各本文へ記載しました。

既存の更新host試験20件、5種のchecker回帰、actionlint、ShellCheck、offline zizmorは終了値0でした。リンクの初回は、台帳に記録したSDL repository内の原文path2件を古い文書参照とみなして失敗しました。原文を変えず理由付き例外を追加した後は成功し、失敗行はCSVへ残しています。JISの既存警告9件と文書サイズの既存警告はerrorに混ぜず、新規3比較本文はいずれも20,000 B未満です。

日本語はyomiyasuで本文と改稿差分、最終稿のhashを確認しました。資料にない語の候補、表・専門語・文末の反復は、版・許諾・未確認・否定の意味を変えないよう本文と資料で読み比べました。検査の記録は意味の正しさの自動認定ではありません。

終了値・stdoutのbytesとSHA-256、commandを[同名CSV](2026-11-02-alternatives-followup-audit.csv)へ保存しました。失敗行も保持し、各列と生ログを照合しました。原bytesとstdoutは永続領域に保管しますが、第三者の全文や巨大なAPI応答は転載しません。可変URLではhashだけで当日の全文を再生成できない限界があります。

取得できたことは、全文精読、全licenseの閉包、全option、ABI互換性、support保証、実機動作の認定ではありません。取得失敗の理由と、補った内容・残る条件は各比較本文へ残します。

公開版と開発HEAD、mirrorと主repository、manualの古い記載と固定binaryの既定値を区別します。候補のbuild・boot・性能、全deviceの実機動作、権限制御の強制・拒否試験は本リポジトリでは試していません。
