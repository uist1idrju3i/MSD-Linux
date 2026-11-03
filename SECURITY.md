# セキュリティポリシー

## 脆弱性の報告

MSD/Linux の脆弱性は、公開の Issue、Pull Request、Discussion には書かず、GitHub の [private vulnerability reporting](https://github.com/uist1idrju3i/MSD-Linux/security/advisories/new) で報告してください。報告は、修正するか公開するかを決めるまで非公開で扱います。

報告には、次の情報を含めてください。

- 対象の commit、tag、または Release asset
- 再現手順と、確かめた環境（QEMU か実機か）
- 想定される影響

返信と修正の期限は約束しません。

## 対象

| 対象 | 扱い |
|---|---|
| `main` ブランチ | 対象です |
| 最新の pre-release | 対象です。現在の pre-release は開発版で、開発用の鍵で署名しています。実機での起動は未確認です |
| 古い pre-release | 修正版は出しません。最新の pre-release または `main` で再現するかを確かめてください |
| `vendor/` 以下の上流のコード | 上流の窓口へ報告してください。MSD/Linux の設定や組み込み方が原因の場合は、こちらで受け付けます |

## 現在の監視

MSD/Linux は未リリースです。製品向けの署名済み image はまだありません。

- 製品の SBOM を 2 時間ごとに NVD のデータと照合し、結果を Issue「製品SBOMの脆弱性監視」で公開しています。
- Pull Request では、変更によって新たに増えた、修正版のある CRITICAL の CVE を失敗にします。
- 開発用 Docker image は Trivy で検査し、`dev-image gate` で結果を返します。

仕組みは [CI の構成](docs/CI.md#ワークフロー)、理由と再確認期限を付けた例外の一覧は [.github/cve-exceptions.tsv](.github/cve-exceptions.tsv) を参照してください。
