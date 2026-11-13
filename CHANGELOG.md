# 変更履歴

この文書は[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形式を参考にし、リリースごとの利用者向け変更を記録します。

## [Unreleased]

### 追加

- CardputerZero向けBuildroot構成、A/B更新手順、QEMUを含む検証手順を整備しました。
- 調査・測定記録を主題別に整理し、再現条件と未確認範囲を追跡できるようにしました。
- 起動時の `/etc/issue` と `os-release` に、版、commit時刻（JST）、commit IDを記録します。
- 初回起動からRAM約50%のzram swapを使います。console開始後にbackgroundで有効化し、zstdを優先します。永続storageへのwritebackは使いません。
- legal-infoへ固定Buildroot sourceとBootlinのlicense原文を補足します。SHA-256を検査し、原警告と未収集のsource・patch等を明記します。完全な対応sourceや配布許諾の確認を意味しません。

### 変更

- 製品の既定timezoneをAsia/Tokyoにし、tzdataのasiaを収録します。log・cache・一時fileのRAM配置を棚卸しし、QEMUの起動直後に残る永続書き込みと判断待ちを台帳に記録しました。
- Buildrootを現行のbuild基盤とし、Yoctoへの移行を見送りました。
- CIの文書検査と開発用imageの構築・検査を改善しました。

### セキュリティ

- seedrngの起動・停止時の永続seed保存と`/data/seedrng`の作成をやめ、kernelのhwrngを維持します。既存SDの古いseedを消去する変更ではなく、乱数の品質と実機の起動時保証は未確認です。

- Cloudflare PagesにCSP・機能制限・埋め込み拒否を指定し、previewの検索登録を抑止します。外部資源の例外は承認済みのWeb Analyticsだけです。
- 開発用imageの定期検査をamd64とarm64に広げ、両方の結果を一つのIssueへ集約します。公開はmainだけに限定し、buildの読取専用jobからpush・attestationを分離しました。
- 定期監視のIssueを全ページから探し、競合による重複を防ぎます。取得・走査の失敗や未照合を検出なしと区別し、Issueとsummaryに未確認と表示してjobを失敗させます。
- Buildrootの無視指定による`in_triage`は、影響あり・解消・scan失敗と別の未評価欄に記録し、状態間の移動も差分で通知します。
- 本番更新の公開鍵だけを使うbuildと、Environmentで保護された独立署名jobを追加しました。署名対象は従来のmanifestで、SD image全体の署名や鍵失効機能は含みません。
- 開発用imageのDebian snapshotを更新し、apt・libapt-pkg7.0とzlib1g・zlib1g-devのsecurity修正版を取り込みます。
- 開発用Docker imageをTrivyで検査するgateを追加しました。
- 製品SBOMについて、PRで新たに増えた修正可能なCRITICAL CVEを失敗させるgateを追加しました。
- 製品SBOMを2時間ごとにNVDと照合し、差分をIssueで通知する監視を追加しました。

## [0.0.0] - 2026-11-02

開発用pre-releaseです。実機での起動は未確認で、immutableではありません。
