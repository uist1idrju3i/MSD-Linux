# CardputerZero自身によるGitHub Releasesからの更新

[RESEARCH](../../../RESEARCH.md) / [現在のA/B操作](../../UPDATE.md) / [Release署名](release-security.md) / [TUFの基礎](../alternatives/update-metadata.md)

## 結論と現在地

GitHub Releasesを配布元にして、CardputerZero自身が新しいOSを取得し、非稼働slotへ導入する構成は設計できます。ただし、現在のMSD/LinuxにRelease取得clientはありません。既存の`msd-update`、Wi-Fi driver・firmware、署名済みbundleがあることを、自己更新が利用可能という意味にはしません。

2026-11-02に、MSD/Linuxの`9fbc7767ccc475d67fba5e7d1d9e9968c12131bd`と[sources.json](sources.json)の固定資料を基準に調べました。この文書群は調査・比較・設計案で、製品設定、更新形式、GitHubの設定・Secretは変更していません。新clientのbuild・実行、network取得、実機のtryboot・電源断復帰は本リポジトリでは試していません。

推奨は、**不変のRelease payload、標準TUFによるmetadata検証、機種・版を認可する処理、狭いA/B writerを分離**する構成です。TUFの独自再実装や、端末への常設PAT配布は先に選びません。公開SemVerと内部番号の対応は承認済みです（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。製品の管理操作認可は確認待ちであり、この調査では決定しません。

## 読む順序

| 文書 | 答える問い |
|---|---|
| [実装の比較](implementations.md) | Python-TUF、go-tuf、tough、rust-tufを何に使い、公開側をどこまで再利用できるか |
| [配信と取得](transport.md) | Releaseと期限付きmetadataをどう公開し、匿名取得・redirect・容量・通信断をどう制限するか |
| [信頼・状態・復旧](trust-and-state.md) | 鍵、時刻、版、権限、A/Bとdataのtransactionをどう分けるか |
| [資料台帳](sources.json) | どのURL・commit・bytes・hashを取得し、何が失敗したか |
| [静的照合の記録](../../experiments/2026-11-02-release-client-audit.md) | 今回何を検査し、実行・実機試験をしていないか |

## 処理を分ける

| 段階 | 入力と責務 | 失敗時に維持するもの |
|---|---|---|
| 発見 | 設定済みのmetadata配布先やRelease APIから未信頼の候補を取得する | 稼働slot、boot selector。`latest`を認可根拠にしない |
| 信頼の更新 | 配備済みrootからTUFのroot・timestamp・snapshot・targetsを検証し、信頼状態を保存する | 旧い応答や期限切れを「更新なし」と成功扱いしない |
| OSの選択 | 認証済みのcatalog/descriptorから機種・channel・schema・版・最低updater版を検査する | metadata版とOS版を混同せず、違う機種や未対応schemaを拒否する |
| 取得 | 認可されたtargetを長さ・hash・時間・容量の上限内で保存し、内容を検証する | 一時fileを更新済みとして扱わない。SDへまだ書かない |
| 導入 | 認可を再確認し、非稼働slotだけへ書き、読み戻す | 単なるpathやdownload成功だけをwriterの認可としない |
| 試行・確定 | tryboot、期限付きhealth、commit、失敗復帰をtransactionとして扱う | 既知の正常slotと互換なdataを保持する |

TUF metadataが正しくても、OSが起動することや、slotと共有dataの整合は保証しません。現在のwriterをそのままネットワーク入力へ接続せず、[最小権限の設計](../security/privileges.md)と合わせて境界を検証します。

## 実施順と完了条件

1. 署名jobの分離、公開鍵だけのbuild、Release payloadの認証を整える。[Release保護の既知の不足](release-security.md)を先に解消する。
2. SemVerと内部番号の対応は承認済みです（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。製品の認可、channel、時刻未確定時の復旧を決める。安全性を上げる案と、利用者が更新できなくなる背反を確認する。
3. host上で小さなTUF repositoryと複数clientを比較する。鍵更新、期限、rollback、長さ、parser差、故障時の永続化を成功系と同じ重さで試す。
4. 現行Buildroot・BootlinでAArch64をbuildし、依存閉包、license、SBOM、image/RSS、起動、拒否試験を記録する。新依存を版・脆弱性監視へ加える。
5. 通信防御を先に有効化し、認証・DHCP・DNS・CA・時刻が揃ってから更新通信を許す。[Wi-Fiと通信の未実装計画](../alternatives/network.md)と統合する。
6. QEMU/hostでstate machine、同時実行、容量不足、途中切断、clock後退、権限拒否を検証する。QEMUで届かないGPU firmware・実SD・電源断は実機で確認する。
7. 実機のtryboot・watchdog・health・鍵移行・長期offlineからの復帰を確認し、その版とbinaryの証拠を残して初めて利用可能とする。

RAUC等のwriterへの移行も[別の比較軸](../alternatives/updates.md)として残します。TUF clientの選択だけでA/B frameworkを決めたり、この設計案の作成を製品実装の完了としたりしません。
