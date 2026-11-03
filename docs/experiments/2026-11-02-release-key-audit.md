# Release設定とEd25519鍵の手順の確認

[実験一覧](README.md) / [Releaseの調査](../research/release-client/release-security.md) / [管理者の手順](../RELEASE-SIGNING.md)

## 目的と事前の基準

管理者向けの鍵生成・公開鍵導出・署名検証のCLI手順が成立するか、製品用ではない試験鍵で確認します。GitHubの設定変更や本番Secretの登録は行いません。

- 基準commit: `b9bea56b703c54d2cd0782481d2de7a73e13294b`。この記録に加えた [runner](../../tests/release-signing-key/run.py) で実行しました。製品の署名処理は変更していません。
- 仮説: raw Ed25519の署名を対応する公開鍵で検証でき、改変と別鍵を拒否できる。公開鍵のDER fingerprintは別実装のSHA-256とも一致する。
- 事前基準: 5回の独立した試験鍵で、生成・導出・鍵確認・公開鍵表示・DER変換・fingerprint・署名・正常検証が終了値0、改変・別鍵での検証が終了値1。署名長は64 bytes、公開鍵の表示にED25519があり、fingerprintはPythonのhashlibと一致する。
- 正常署名を正の対照、改変と別鍵を負の対照にします。全条件で成功する検査器では合格しません。
- host: Ubuntu 22.04.5 LTS、x86_64、Linux 6.8.0-1061-aws、glibc 2.35。OpenSSL 3.0.2を実際のバイナリーで実行しました。固定製品imageのOpenSSLを試した結果ではありません。
- OpenSSLバイナリーSHA-256: `a55e3085b6a1df8887722f6cee7fc32c861d11d5fb584a63837d32d29602c65b`。GitHub CLIは `2.78.0-4-g4fdaf6b25` です。
- build、QEMU、性能測定は行いません。warm/cold比較、中央値・最小・最大の性能値は対象外です。

## 再実行

リポジトリのrootから、親が存在する新しい出力先を指定します。例の `output-release-key-audit` が既にあればrunnerは停止します。実行ごとに別の出力先を使ってください。

```sh
python3 tests/release-signing-key/run.py --output-dir output-release-key-audit
```

runnerは秘密鍵を一時ディレクトリ内に生成し、試験後に破棄します。本番鍵は入力できません。公開鍵の表示、終了値、metadataとhashを残し、秘密鍵の値は保存・表示しません。手順の検査であり、秘密鍵の安全な消去や暗号実装の監査を証明するものではありません。

各回のコマンド、期待終了値、実際の終了値、出力bytesとSHA-256は [CSV](2026-11-02-release-key-audit.csv) にあります。乱数で新しい鍵を作るため、公開鍵・fingerprintの出力hashは再実行時に変わります。終了状態と検査条件が再現の対象です。

## 結果

5回それぞれ12コマンド、計60行が事前基準と一致しました。各回の改変・別鍵の計10検証は、期待どおり終了値1です。CSV全列と出力logを読み、正常検証と拒否を区別しました。秘密鍵は製品用ではなく、実行後の一時ディレクトリも残していません。

公開資料と閲覧可能な設定APIは [出典台帳](../research/release-client/release-security-sources.json) に記録しました。19取得試行のうち17件が取得でき、Secrets一覧とworkflow既定権限の2件はHTTP 403です。19応答のbytesとSHA-256を照合しました。公式文書の関連節を読んだ範囲であり、全文・license・全設定の監査ではありません。

GitHub CLIの `secret set`、`release verify`、`release verify-asset` のhelpで構文を確認しました。Secretを投入せずに公開済みの `v0.0.0` を検証すると、`gh release verify v0.0.0 --repo uist1idrju3i/MSD-Linux` は終了値1で `no attestations for tag` でした。APIでも `immutable=false` であり、署名済みReleaseの成功例とはしません。この照合は1回です。

出力先を同じ名前で再実行した拒否試験も1回行い、既存CSVとlogを上書きせず終了値1で停止しました。GitHubの管理設定を変更する試験、本番Secret登録、公開署名job、初回SD imageの署名、端末の自己更新、実機での鍵移行は実施していません。

確認時のrunner SHA-256は `ad906c171f19bf0ecab17beec78c323567b62174dca9904a8409b092f64ffdfb`、CSVは `12ff6923a8b0bc4e9bc71284c55420c1bc6dd82c8e3342452980344a78ee7e1e` です。既存Releaseの検証logは `604f5ca7ee0dd6f23502b3543fad53a809653f3333ea7f92d9945f7646a25459`、既存出力先の拒否logは `784c69f5a396e4a4915dddbfc29d5f5a8fc0d8c91652ce202034296a45291dbd` でした。これらは当時のlogを識別するhashであり、公開済みの本番署名を示すものではありません。

## 予備確認と失敗の扱い

本番記録の前に、fingerprint照合をまだ含めない55コマンドの予備確認を2回行いました。いずれもCLI手順の確認に成功しましたが、上記60行の試行へ合算せず、性能や暗号の強度の根拠にはしません。

文書への一括patchで既存本文の誤字を誤認し、最後のcontext照合が失敗しました。実ファイルを再読すると元の本文に誤字はなく、先に適用された他の変更をgit diffで確認しました。製品や鍵の試験失敗ではありません。検査・文書の修正があれば別の試行として残します。

yomiyasuの初回は `--reader` に未定義の値を渡し、8文書とも終了値2でした。許可された `informed` へ直して再実行しました。数値・hash、未実装の説明、否定、操作する管理者、追加した用途別の案内を原文と照合しました。手順を示す文末や索引のリスト比率は、その役割を保つため残しています。runとverifyは検査の実施記録であり、正しさの自動認定ではありません。

リンク・JIS文字・サイズ・skills・siteの静的検査は終了値0でした。既存のJIS警告9件と文書サイズの警告は残ります。新しい3本文は各20,000 bytes未満です。[回帰試験と固定環境lintの終了値](2026-11-02-release-key-checks.csv) は9コマンドとも0でした。これらは各1回で、同じ入力に対する構造・終了値を確認する検査です。新しい署名jobや製品imageを検証した結果にはしません。

## 結論と限界

hostの試験鍵で、生成・導出・raw署名・検証と2種類の拒否を確認できました。GitHub Environmentの実際の承認強制、秘密鍵なしのbuild、独立した署名job、imageの署名形式、公開鍵の配備と失効、実機でのA/B更新は未検証です。Secret登録手順の構文確認を、登録や利用の成功と読み替えません。
