# 一覧の検証記録

## 対象と判定

2026-11-02 UTC、基準commit `1395e9d142a0970fc68e57818e51af02e2d99f2f` 上の文書追加を検査した。依存の差し替え、ビルド設定、署名・更新処理は変更していない。実機試験と製品imageの再ビルドは今回の検査対象ではない。

| 検査 | 結果 |
|---|---|
| 実artifactのSBOMとshow-infoを既存 `validate_components()` へ渡す | 一致。入力のhashは[source-record.json](source-record.json)に記録 |
| JSONの構造・件数・参照先・CSVとの対応 | 下記の照合が全て成功 |
| 日本語・文字範囲 | yomiyasu lintと元資料の読み比べ、JIS X 0213検査を実施。全体の文字範囲エラー0件。既存9 warningは引用例・フォント名 |
| 文書サイズ | エラー0件。今回の新規Markdownは全て20,000 byte未満。既存文書のサイズwarningは残る |
| 相対リンクとanchor | 1,497 link、72 anchor、エラー0件 |
| SBOM補正の回帰試験 | 11テスト成功。引数の欠落・不正値を拒否する試験も含む |
| links、doc-size、JIS検査器の回帰試験 | 全て成功。意図した不正入力のerror出力は試験の成功条件 |
| whitespace・conflict marker・公開範囲 | 検査対象の差分に問題なし。VMのパス、raw scan、image tar、秘密鍵は含めていない |

Pythonはホスト3.12.13、固定開発用OCI内3.13.5。通常の検査器と回帰試験は `docker/msd-dev` で実行した。JSON/CSVの件数照合と日本語lintはホストのPythonで実行した。これは一回の構造検査であり、性能の差を主張しない。

## 再照合できる条件

リポジトリのrootで次を実行すると、公開した一覧同士の構造と件数を再照合できる。これはupstreamへの再問い合わせや元資料の正しさまで保証する試験ではない。

```sh
python3 - <<'PY'
import collections
import csv
import json
from pathlib import Path

root = Path('docs/research/dependencies')
read = lambda name: json.loads((root / name).read_text())
components = read('buildroot-packages.json')
graph = read('buildroot-dependencies.json')
apt = read('development-apt.json')['packages']
actions = read('actions-recursive.json')
npm = read('actions-npm-latest.json')
assert len(components) == len({row['id'] for row in components}) == 67
assert collections.Counter(row['scope'] for row in components) == {
    'host': 49, 'target': 18,
}
assert len(graph) == 68
assert sum(len(row.get('dependsOn', [])) for row in graph) == 267
refs = {row['ref'] for row in graph}
assert all(ref in refs for row in graph for ref in row.get('dependsOn', []))
assert len(apt) == 231
assert collections.Counter(row['status'] for row in apt) == {
    'same': 228, 'newer-distro-package': 3,
}
assert len(actions) == 11 and len(npm) == 859
assert all(row['status'] == 'read' for row in npm)
assert sum(len(row['source_versions']) for row in npm) == 1574
for name, count in [('buildroot-packages.csv', 67), ('development-apt.csv', 231)]:
    with (root / name).open() as stream:
        assert len(list(csv.DictReader(stream))) == count
print('inventory cross-check: PASS')
PY
```

公開範囲はJSONを構文解析したうえで各URL・hash・文字列を点検した。credentialそのものを正規表現で探してlogへ出す方法は使っていない。raw npm registry応答、取得途中のZIP、Trivy原本、archive本体は一覧の外に保管し、ここには公開可能な項目だけを残した。

[依存関係の一覧へ戻る](README.md)
