# MSD/Linux の文書案内

現行のビルド基盤は Buildroot です。文書は、操作・実装の説明、調査、実験の証拠を分けて読みます。調査中の案は製品への採用を意味しません。

## 使う人

| 目的 | 入口 | 本文の扱い |
|---|---|---|
| microSDへの導入・再導入 | [INSTALL.md](INSTALL.md) | PCから全SD imageを書く開発用手順。実機未確認とデータ消去を明記 |
| 更新・署名・A/B | [UPDATE.md](UPDATE.md) | 現在の更新処理と、実機で確認する点 |
| 脆弱性の報告と監視 | [SECURITY.md](../SECURITY.md) | 報告方法、対象範囲、現在の監視 |

## 作る人

| 目的 | 入口 | 本文の扱い |
|---|---|---|
| 構築・成果物・QEMU 起動 | [BUILD.md](BUILD.md) | 現在の実装と実行手順 |
| 実機での確認 | [VERIFY.md](VERIFY.md) | 実機試験の手順。収録済みなのはカメラで、他の試験が済んだという意味ではない |
| Releaseと署名鍵の管理 | [RELEASE-SIGNING.md](RELEASE-SIGNING.md) | 管理者の設定手順。Secret登録と、未実装の署名jobを区別する |
| CI・開発用イメージ・品質検査 | [CI.md](CI.md) | workflow の構成と成果物 |

## 調べる人

| 目的 | 入口 | 本文の扱い |
|---|---|---|
| 設計方針・主題別の調査 | [RESEARCH.md](../RESEARCH.md) | 決定済みの方針、候補、未確認事項への案内 |
| 測定条件・生データ・失敗した試行 | [実験一覧](experiments/README.md) | 当時の commit と入力に対する証拠。新しい版の合格を保証しない |
| Yocto 移行を見送った経緯 | [検討記録](research/yocto-migration/README.md) | 中止した計画と現在の決定を分けて保存 |
| Yocto 検討の Buildroot への還元 | [還元の評価](research/yocto-migration/buildroot-lessons.md) | 取り込む検査・監査と、製品設定を変えない候補の区別 |
| ロゴの意匠・利用 | [ロゴ](logo/README.md) | 意匠、生成手順、ライセンス |
| 文書の役割・重複・分割の判断 | [文書の配置](research/document-map.md) | 更新する本文の置き場と、長い文書を保持した理由 |

測定の設計と記録を探すときは[検証・測定の入口](research/verification/README.md)から、未確認事項、S1–S17、観測方法、実機測定、計画履歴へ進みます。

保存領域は[現在の配置と調査の入口](research/storage/README.md)から、FAT/ext4の割当、writerと未実装のpolicy、FS候補、電源断、A/Bの設計履歴へ進みます。過去の比較・測定と、現在実行する導入・更新の操作を分けています。

ユーザー空間は[init・libcの案内](research/userspace/README.md)から、現在の候補比較と過去のdevice依存・測定条件へ進みます。セキュリティは[具体的な権限設計](research/security/README.md)、[物理アクセスの脅威モデル](research/security/threat-model.md)、[過去の強化項目](research/security/history/README.md)を分けています。

作業規則は [AGENTS.md](../AGENTS.md)、手順は [.agents/skills/](../.agents/skills/) にあります。公開サイト用のファイルは `public_html/` に置き、文書の原本はここに置きます。
