# 変更履歴

この文書は[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形式を参考にし、リリースごとの利用者向け変更を記録します。

## [Unreleased]

### 追加

- CardputerZero向けBuildroot構成、A/B更新手順、QEMUを含む検証手順を整備しました。
- 調査・測定記録を主題別に整理し、再現条件と未確認範囲を追跡できるようにしました。
- 起動時の `/etc/issue` と `os-release` に、版、commit時刻（JST）、commit IDを記録します。

### 変更

- Buildrootを現行のbuild基盤とし、Yoctoへの移行を見送りました。
- CIの文書検査と開発用imageの構築・検査を改善しました。

### セキュリティ

- 定期監視のIssueを全ページから探し、競合による重複を防ぎます。取得・走査の失敗や未照合を検出なしと区別し、Issueとsummaryに未確認と表示してjobを失敗させます。
- 開発用imageのDebian snapshotを更新し、apt・libapt-pkg7.0とzlib1g・zlib1g-devのsecurity修正版を取り込みます。
- 開発用Docker imageをTrivyで検査するgateを追加しました。
- 製品SBOMについて、PRで新たに増えた修正可能なCRITICAL CVEを失敗させるgateを追加しました。
- 製品SBOMを2時間ごとにNVDと照合し、差分をIssueで通知する監視を追加しました。

## [0.0.0] - 2026-11-02

開発用pre-releaseです。実機での起動は未確認で、immutableではありません。
