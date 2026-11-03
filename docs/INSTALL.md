# microSDへの導入

[文書案内](README.md) / [READMEの概要](../README.md#microsdへのインストール) / [A/B更新](UPDATE.md)

## 適用範囲と必要なもの

MSD/Linuxは開発中です。これは全SD imageをPCから書く手順であり、CardputerZero実機で成功を確認したインストーラーではありません。QEMUでA/B両rootfsを起動しても、GPU firmwareの起動選択、LCD、キーボード、SDの電源断耐性を確認したことにはなりません。

PC、microSDリーダー、内容を消してよいmicroSD、別媒体へのバックアップ、安定した電源が必要です。標準版とLite版の共通imageを作る設計ですが、両モデルの実機動作は未確認です。カードには展開済み `sdcard.img` 全体が収まる容量が必要です。圧縮ファイルのサイズで選ばないでください。

再導入はp1〜p7を含む領域へ上書きし、設定・更新状態・`/data` のデータを失います。通常の更新には [A/B更新](UPDATE.md) を使います。

## 1. imageを用意する

### 自分で構築する場合

[構築手順](BUILD.md) の固定した開発環境で、確認するcommitから生成した `output/images/sdcard.img` を使います。秘密鍵をbuild全体へ渡すことを安全な本番手順とはしていません。鍵の分離と署名jobは [署名鍵の設定](RELEASE-SIGNING.md) にある未実装部分です。

### CI成果物を使う場合

1. 本リポジトリの [Actions](https://github.com/uist1idrju3i/MSD-Linux/actions) から、対象commitを明示したBuildrootの実行を開きます。失敗した実行、別commit、第三者のforkの成果物を混同しません。
2. Buildroot build、image layoutとQEMU検査の結果・ログを読みます。artifactはbuild成功を条件に保存するため、artifactがあるだけで後続検査の成功を証明できません。文書変更でbuildがskipされたPRには新しいimageはありません。
3. `msd-cardputerzero-build` をダウンロードし、ZIPの中の `sdcard.img.xz` を展開して `sdcard.img` にします。ほかのDTB・kernel・SBOM・legal-infoは全SD imageの代わりにはなりません。

既存の `v0.0.0` はprereleaseで、確認した時点ではimmutableではなく、Release attestationも取得できませんでした。本番の署名済み配布としては案内しません。HTTPS、GitHubのasset digestや同じ配布場所にあるchecksumだけを、独立した発行者署名の代わりにはしません。SD image全体の署名・初回の信頼鍵の配布は未実装です。詳細は [Releaseの調査](research/release-client/release-security.md) を参照してください。

## 2. PCでカード全体へ書く

以下は [Raspberry Pi公式のImager手順](https://github.com/raspberrypi/documentation/blob/daf1ca791713d5f1346556122a2b6942bcc7b1d7/documentation/asciidoc/computers/getting-started/install.adoc) にある、ローカルのimageを選ぶ操作に基づきます。ImagerでのMSD/Linuxの書き込みと実カードの読み戻しは、本リポジトリでは試していません。

1. [公式配布元](https://www.raspberrypi.com/software/) からPCに合うRaspberry Pi Imagerを用意します。バックアップを確認してから、書き込み対象以外の外付けストレージを外します。
2. ImagerでOSを選ぶ画面へ進み、**Use Custom** から展開済みの `sdcard.img` を選びます。モデルの選択だけでCardputerZero向けのimageが取得・検証されるわけではありません。
3. StorageでmicroSDを選びます。容量と製品名を確かめ、**Exclude system drives** は有効のままにします。対象を識別できなければ書き込みを止めてください。
4. OSのカスタマイズが表示されてもスキップします。MSD/LinuxはRaspberry Pi OSの初回設定処理を呼ばないため、Imagerで指定したユーザー、Wi-Fi、SSH、Connectが使えるとは扱いません。
5. 消去の確認では、選んだimageとカードをもう一度照合します。書き込みと検証が完了するまでカードを抜きません。検証を省略して起動成功としないでください。
6. 完了後、PCでカードを安全に取り外します。Windows等がLinux領域のフォーマットを求めてもキャンセルします。別途FATで初期化したり、imageファイルをカード上へ単にコピーしたりする手順ではありません。

`dd` の誤った出力先はPCのディスクを破壊します。そのため、未確定のデバイス名へそのまま実行できる書き込みコマンドは掲載しません。

## 3. 初回起動を確認する

CardputerZeroの電源を切ってからmicroSDを挿入し、安定した電源で起動します。LCD・内蔵キーボードを含む起動と操作は実機での確認が残っています。[権限調査の設定照合](research/security/README.md#照合した範囲と限界)では、現行Buildrootの展開設定はrootログイン有効・初期パスワード空・console gettyありでした。これは設定値であり、実機でのログイン確認ではありません。無認証の開発consoleを本番の認可手段として扱わず、不特定の人やネットワークにさらさないでください。製品の利用者・管理者認可を分ける方針は未確定です。

管理用consoleで操作できた場合、READMEの確認コマンドと [実機確認](VERIFY.md) に沿い、slot、鍵の由来、更新番号、rootfs、`/data`、入力・表示を記録します。`msd-update status` がDTの情報を読めない場合、`MSD_UPDATE_DT_DIR` 等の試験用環境変数で見かけの成功にしてはいけません。

p7はimage内で64 MiBです。起動時に `S02msd-data` が `msd-data-grow` を呼び、拡張パーティションp4とp7をディスク末尾まで拡張し、`resize2fs` を実行する実装があります。失敗時はエラーを記録し、`/data` のマウントを維持します。`df -h /data` と起動ログで結果を確認します。実装の存在と、全カードでの拡張成功は別です。実機確認なしに手動でパーティションを削除・再作成しないでください。

起動できない場合は、使ったcommit・artifact・hash、モデル、カード、電源、表示・consoleのログを保存します。カード全体への再書き込みで調べる場合も、先に既存データを別媒体へ保全します。ネットワーク経由の自動復旧を前提にしません。
