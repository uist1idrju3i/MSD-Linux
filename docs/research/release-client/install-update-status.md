# 導入・A/B操作と現行実装の照合

[調査の索引](../../../RESEARCH.md) / [導入手順](../../INSTALL.md) / [更新手順](../../UPDATE.md)

## 確認対象と結論

基準はMSD/Linuxのcommit `0c781e3755aa7a4f52b2f299632e398cf3bd8e8c`です。操作手順を追加するため、imageの生成、CIの保存対象、更新処理、health処理、データ拡張を静的に読みました。新しい製品imageの構築、Imagerでの書き込み、実カードの読み戻し、実機での起動・更新は行っていません。既存のホスト試験の再実行は [確認記録](../../experiments/2026-11-02-install-update-audit.md) に分けています。

| 操作・期待 | 実装から確認したこと | 利用手順で分けること |
|---|---|---|
| 初回導入 | [genimage.cfg](../../../board/cardputerzero/genimage.cfg) がMBRの全SD imageを作る | kernel単体や更新tarの書き込みではない。再導入はp7のデータも消す |
| CIからの入手 | [build.yml](../../../.github/workflows/build.yml) の `msd-cardputerzero-build` はSD image、DTB、kernel、構成、SBOM、legal-infoを保存する | build成功が保存条件であり、artifactの存在だけでQEMU検査の合格とはしない。文書変更だけならbuildを省く |
| 更新tarの入手 | [post-image.sh](../../../board/cardputerzero/post-image.sh) は `msd-update-bundle.tar` を生成するが、上記artifactの保存対象ではない | READMEで「Releaseから更新tarを取得できる」とは案内しない。端末の自動取得も未実装 |
| データ拡張 | [S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data) は [msd-data-grow](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow) を呼ぶ | p4・p7の末尾拡張とext4の拡張は既存実装。失敗してもマウントを維持するため、ログと容量を確認する |
| install | [msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) は4ファイルのbundle、署名、hash、番号、サイズを検査し、非稼働slotへ書いて読み戻す | 失敗後にtryしない。稼働slotは保つが、共有データはA/Bで巻き戻らない。展開先の通常tmpfsにも容量が必要 |
| try | 検証済みslotとp1のselectorが一致するかを検査し、`reboot '0 tryboot'` を呼ぶ | 既存のホスト試験はrebootをmockする。firmwareによる実機切替の確認ではない |
| commit | [S99msd-health](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health) がSquashFS、ext4、ready markerを確認し、自動でcommitする | 利用者の承認や全周辺機能の確認を待たない。手動commitを通常の手順に足さない |
| commit後の表示 | commitはp1と状態ファイルを書き換え、DTのtryboot値は書き換えない | 同じ起動中は `tryboot=1` のまま。`committed` と `partition` の番号一致・保留の消去を確認し、通常再起動後に同じ新slot・`tryboot=0` を確認する |
| 失敗からの復帰 | 未commitなら次の通常起動で旧slotを選ぶ設計 | 起動停止の即時検出、watchdog開始前の停止、電源断、SD故障からの自動復旧を保証しない |
| 版と信頼 | manifestの版は10進整数、署名対象はmanifest | SemVer文字列の対応は未確定。稼働版より小さい番号は拒否するが同じ番号は許可する。SD全体の認証や耐改ざんのanti-rollbackではない |

`msd-update status` はDTにある稼働slotの情報であり、commit完了や全デバイスのhealthを表示するものではありません。試験用の `MSD_UPDATE_*` 環境変数で実機の欠けた情報を補い、確認済みとすることは避けます。

## 外部資料と限界

[Raspberry Pi公式のImager手順](https://github.com/raspberrypi/documentation/blob/daf1ca791713d5f1346556122a2b6942bcc7b1d7/documentation/asciidoc/computers/getting-started/install.adoc) のローカルimageの選択、対象の識別、system driveの除外、書き込みと検証の節を読みました。公式サイトへの取得はHTTP 403で失敗したため、公式GitHubの固定commitの同じ資料を使いました。[取得記録](install-update-sources.json) に両方を残しています。

公式資料のRaspberry Pi OS用カスタマイズやNetwork Installを、MSD/Linuxが利用できる機能とはしません。手順は展開済みの全SD imageをPCから書く形に絞り、PCのディスクを破壊し得る固定の `dd` 出力先は掲載しません。Imagerによる読み戻しは書き込み結果の検査であり、発行者署名の代わりではありません。

本番鍵を別buildへ渡すこと、拒否された署名を回避して鍵を差し替えること、未保護の開発用root consoleを本番運用することは案内しません。初回imageの署名、公開鍵だけを渡すbuild、最小の署名job、鍵移行・復旧、端末のネットワーク・Release取得は [Releaseの調査](release-security.md) と [権限設計](../security/README.md) の未実装項目です。
