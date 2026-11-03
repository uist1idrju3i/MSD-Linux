# 未実施項目・将来計画と判断の順序

[RESEARCH](../../RESEARCH.md) / [未確認の問い](verification/open-questions.md) / [実験の現在地](verification/experiment-catalog.md)

## この台帳の範囲

2026-11-03、`1670bdd`を基準にした整理です。**調査が済んだことと、製品実装・実機確認・release準備が済んだことを分けます。** 現行実装、過去の実験、今後の候補は下表の正本へ戻り、過去の「完了」を現在のbinaryへ引き継ぎません。

| 正本 | 内容 |
|---|---|
| [残件台帳CSV](pending-work.csv) | 各項目の状態、根拠、未確認、依存、次の操作、優先度、完了条件、証拠層、判断者、費用・危険・破壊的変更 |
| [要求との対応CSV](roadmap-coverage.csv) | 31主題、原Q/Rの79件、S1–S17、旧計画と今回の追加要求がどの残件へ対応するか |
| [主題別の問い](verification/open-questions.md) | 問いの意味と次に確かめること。原記録は改変しない |
| [S1–S17](verification/experiment-catalog.md)・[QEMUの範囲](verification/qemu-coverage.md) | 過去の試験revision・条件・実機で未確認の境界 |
| [init比較](alternatives/init-detail.md)・[実測計画](../experiments/2026-11-03-init-comparison-plan.md) | 今回追加した深掘りと未実施の試験仕様 |

CSVは案内のための対応づけであり、全機能の正しさの認定ではありません。原資料にない細目や新しい要求が見つかったら、根拠と完了条件を加えます。全チャット・全成果物の最終照合自体もR33の残件です。「全ての約束を既に検査した」とはしません。

## 状態・優先度・依存の読み方

| state | 意味 |
|---|---|
| implemented-hw-unverified | 設定・実装はあるが実機未確認。全機能完成とはしない |
| historical-host-qemu | 過去のhost/QEMU記録あり。現在のrevision、実機、性能の再現は別 |
| static-only | 文書・source・生成物の静的照合。buildや動作確認ではない |
| design-only | 比較・設計・実験計画まで。製品実装や本計測は未実施 |
| not-implemented | 製品側の必要な処理が未実装 |
| approval-pending | 利用者の選択・承認待ち。回答なしで製品仕様を決めない |
| dependency-pending | 前提の設計・実装・機材・証拠待ち |
| deferred | 利用者の指示等により意図的に延期。検出・監視は残す |
| not-selected | 現条件で不採用・対象外。実装待ちとはしない |
| conditional | 再評価条件を満たしたら調査・実験へ戻す |

P0はreleaseや通信・特権操作に先立つ安全・信頼・復旧の条件、P1は製品機能と検証、P2は保守・最適化・将来比較、P3は条件付き候補です。P0の全項目が今すぐ実装できるわけではなく、`depends_on`が満たされる順に進めます。承認待ちで止まるのは該当範囲だけとし、安い静的照合や文書整理を一律に後回しにしません。

`evidence_paths`は確認に戻るrepo内の資料・実験・実装、`pr_urls`は変更の背景です。PRがmerged、CIがgreenでも、その中の未実施機能まで合格にはしません。`ci_scope`は確認の層を示し、特定のCIが通った証明には使いません。結果を閉じる際は実commit・CI run/job URL・binary hashを別の実験記録へ足します。

`depends_on`は残件IDの有向関係です。「全機能を実装し終えてから調べる」ではなく、当該の実装・測定・判断へ必要な前提を表します。完了後も原行は根拠へ接続し、未確認だけを別行へ分けます。単に行を消して残件数を減らしません。

## 先に進めるまとまり

| 順 | 項目 | 先に行う理由と完了の境界 |
|---|---|---|
| 1 | R01/R02の既存の判断待ちを保持、R03の不変policy設計 | 公開SemVerは選択済み。内部番号の契約とlogin方針は未回答。`/etc`上書き境界はinit・鍵・認可の共通前提 |
| 2 | R24/R28/R31の短い追跡・判定・文書作業 | 保守期限・監視漏れ、署名CLIテストの分類、CPU/IRQ/sysctl等の重複整理はrelease後まで待つ必要がない。Brotli更新はR25で延期を維持 |
| 3 | R04/R07/R08とR05/R06 | 特権helper、通信開始前firewall、認証・IP/DNS/時刻、policy拒否を一組にする。driver・firmwareだけでWi-Fi利用可能とは言わない |
| 4 | R19/R20/R30 | init候補の調査から、共通計測器・構成成立・QEMU・実機の順に進む。今回のコミットは調査・計画であり、実測の完了ではない |
| 5 | R10/R11/R09 | 公開鍵・署名job・metadata・時刻と状態を整え、非特権clientと書込helperを分離してRelease自己更新を試す |
| 6 | R12–R18/R42 | 取得した実機でfirmware・全周辺・更新・電断・性能を測る。QEMUの制約を実機合格へ読み替えない |
| 7 | R22/R23/R26/R27/R29 | 実bundle・全license・外部toolchain・OCI stage/arm64・runnerまで監査し、cache/並列化は正しさと総費用で比較 |
| 8 | R32–R35/R44 | 公開導線、約束・成果物・CIの最終監査、OS改善提案、作業方法の振り返りを別々に納品。release判断は必要な機能と例外を明示して行う |

## 確定しないこと・延期・対象外

- 公開versionはSemVerという利用者の方針は確定です。公開tag、pre-release、内部anti-rollback番号と署名manifestの契約・移行、AGENTS/SKILLへの反映はR01で残します。内部番号の分離案を承認済みにしません。
- 通常操作を一般userへ分ける案はR02で判断待ちです。既定root consoleを今回変更しません。復旧・開発用consoleと製品版の認可を一緒に決めます。
- Brotli修正版導入はR25で意図的延期です。検出・追跡Issue・公開ゲートを緩めません。更新の延期を安全だという判定へ変えません。
- initは未採用です。s6・OpenRC等を含む代替にも同じ安全条件を課し、systemdを前提として周辺実装を先に固定しません。
- Yocto移行は現条件で不採用です。還元したBuildroot改善の再確認と、将来の再評価条件は残します。旧計画に移行作業があることを理由に再開しません。
- **libcamera/ISP、dm-verity、RAUC等の置換、PQ暗号、別構築基盤**は条件付きです。依存と実機根拠が揃うまでは採用・対応済みにしません。
- **SSH/VPN、GUI・公式ランチャー、Debian互換、newlibを汎用Linux libcへ置換**は現行の目的外です。周辺MCU等の別用途の比較は否定しません。

## 閉じるときの証拠

各行は、書いた次の操作、全ての完了条件、未確認範囲、要求する証拠層を照合してから閉じます。host stub、source設定、生成物、QEMU、実機を代用しません。5回未満・条件差・失敗・ログ欠落はそのまま残します。Brotli等の延期、現条件で対象外の項目は「実装完了」で閉じません。

この整理の再検査は[文書・台帳の検証記録](../experiments/2026-11-03-init-roadmap-validation.md)へ保存します。機械検査はID・参照・依存cycle・対応漏れを検出するもので、主張の技術的正しさやチャット全文の精読の代替ではありません。
