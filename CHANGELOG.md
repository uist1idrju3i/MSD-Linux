# 変更履歴

この文書は[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形式を参考にし、リリースごとの利用者向け変更を記録します。

## [Unreleased]

### 追加

- CardputerZero向けBuildroot構成、A/B更新手順、QEMUを含む検証手順を整備しました。
- 調査・測定記録を主題別に整理し、再現条件と未確認範囲を追跡できるようにしました。

### 変更

- Buildrootを現行のbuild基盤とし、Yoctoへの移行を見送りました。
- CIの文書検査と開発用imageの構築・検査を改善しました。

### セキュリティ

- 開発用Docker imageをTrivyで検査するgateを追加しました。
- 製品SBOMについて、PRで新たに増えた修正可能なCRITICAL CVEを失敗させるgateを追加しました。
- 製品SBOMを2時間ごとにNVDと照合し、差分をIssueで通知する監視を追加しました。

## [0.0.0] - 2026-11-02

開発用pre-releaseです。実機での起動は未確認で、immutableではありません。
