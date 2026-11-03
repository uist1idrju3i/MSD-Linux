# 導入・A/B更新手順の静的照合とホスト回帰検査

[実験一覧](README.md) / [調査結果](../research/release-client/install-update-status.md) / [導入](../INSTALL.md) / [更新](../UPDATE.md)

## 目的と事前基準

commit `0c781e3755aa7a4f52b2f299632e398cf3bd8e8c` を基準に、READMEへ全SD imageの導入と既存A/B更新の手順を追加します。製品コード、依存の版、鍵、manifestの形式、ログイン設定は変更しません。

事前の合格条件は、操作手順が生成物・起動処理と一致し、以下の既存回帰試験と文書検査が終了値0であることです。警告は内容を読み、残っているものを明記します。これは決定的な回帰試験の再実行なので各1回とし、性能の結論に使いません。署名の拒否、archiveの異常、誤ったslotや更新番号、パーティションの異常を既存試験の負の対照として扱います。

## 条件とコマンド

- ホスト試験は開発用OCIの `docker/msd-dev` 内で行います。実行したローカルimageのIDは `sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77` でした。生成imageや実カードへ書かず、既存試験の一時ファイル・模擬DT・mock rebootを使います。
- `tests/msd-update/run.sh` と `tests/msd-data-grow/run.sh` を実行します。後者は一時ディスクimageと別のext4ファイルを使い、実機のkernelへの通知は省く試験です。
- 文書のlink、JIS、サイズ、skills、siteの検査、および4種の文書検査の回帰試験を実行します。
- workflow用のactionlint、追跡するshellのShellCheck、offline zizmorを実行します。
- コマンド、終了値、出力のbytesとSHA-256は [CSV](2026-11-02-install-update-audit.csv) へ記録します。zizmorの実行パスはHOME変数に一般化しています。生ログはコミットせず、同じコマンドで再生成します。試験の一時パスやI/O表示、対象文書の追加でログのbytes・hashが変わることがあるため、hash一致だけを合格条件にしません。

## 結果

固定OCIで更新処理の20件とデータ拡張の4件が合格しました。更新試験は署名・hash・番号の異常を拒否し、同じ番号の許可、両slotへの書き込み、mock rebootの引数も確認します。データ拡張は一時MBR imageとext4ファイルに対する試験で、実カードへのオンライン拡張の確認ではありません。

最初の14コマンド中、文書リンク検査だけが終了値1でした。新しい導入手順の権限設計へのanchor名が誤っていたためで、実在する見出しへ直したあとの文書検査5コマンドは全て終了値0でした。最初のほかの13コマンドも終了値0でした。この失敗をCSVから削除しません。

JISの既存警告9件は、文字検査skillの例と中国語入力方式の名前でした。文書サイズの既存警告25件は、既存の実験一覧と長い調査・実験の記録です。今回の追加だけで全文書の再編を完了したとはしません。新しい操作・調査・確認記録は20,000 bytes未満に分け、全文書の整理は別の作業として続けます。各検査の回帰試験にある意図したerror出力も、全体の終了値と分けて読みました。

OCIの実行出力はPython 3.13.5、OpenSSL 3.5.7、util-linux 2.41.5、e2fsprogs 1.47.2、actionlint 1.7.12、ShellCheck 0.11.0でした。`resize2fs -V` は未対応の引数として拒否され、版は同じ出力の先頭に表示されました。製品側のOpenSSL等の版とは区別します。

公式サイトのHTTP 403と、代わりに読んだ公式GitHub sourceは [取得記録](../research/release-client/install-update-sources.json) に残しています。ログとCSVは出力の全列・bytes・hashを照合し、失敗と成功を混ぜて集計しません。

## 確認できないこと

Imagerでの書き込みと読み戻し、CardputerZero実機の起動・ログイン・tryboot・電源断・自動復帰、新しい製品imageの構築・QEMU確認、本番Release・Secret登録は行っていません。既存実験のQEMU結果を今回の新しい実機試験として数えません。
