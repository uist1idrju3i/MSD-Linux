# 2026-11-15 二セッションの調査・判断・引継ぎ監査

[検証の入口](README.md) / [判断とevent対応](session-decisions-2026-11-15.md) / [証拠と復元限界](session-evidence-2026-11-15.md) / [残件と順序](session-followup-2026-11-15.md)

## 結論と範囲

対象は03914（実装状況の確認と今後の計画）と5917（実測・実験）です。会話、event一覧と詳細、添付metadata、現存artifact、PR #245〜#248を照合しました。対象ID・件数・保存commitは[証拠文書](session-evidence-2026-11-15.md)に固定します。S0〜S4の保存・訂正を反映した監査であり、元sessionの計画書を製品実装の完了記録へ読み替えません。

E34は174成功runと4中断attemptを保存済みです。B3は35 bootの記録を保存していますが、F3の5回は旧期待のreadyに反してpanicしました。F6のhost SIGTERMはrestart完了の証拠ではなく、製品A/B復帰は未確認です。QEMUの結果から実機のLCD、firmware tryboot、SD、電断、安全性を判定しません。

利用者の現在の判断は[判断表](session-decisions-2026-11-15.md)へ集約しました。crc32c、条件付きl22、LUKS cipherの暫定既定、btrfs移行後のext4撤去、最終slot表示を保持します。03914の`pending-work.csv`・`roadmap.md`同期保留は解除しません。この監査への収録は、保留された行更新や製品実装の承認ではありません。

## 03914から残す境界・更新・時刻の調査

出典は03914の`event-01a1dd85c87374139b483dda4244c085`、2026-11-15 04:44 UTCの調査回答です。以下は**当時のagent報告**です。今回、現行code全体、上流の最新状態、実機の到達可能性を独立再検証していません。「確認済み」という当時の語を、そのまま現在の検証済み状態にはしません。

| 当時の報告 | 引継ぐ問題と未確認範囲 |
|---|---|
| `/data/etc` overlayは`init.d`を含む任意の`/etc` fileを覆える | `/data`を書ける主体が次回起動でroot権限を得る危険。allowlistと書込み主体の境界をR03で設計する。現行設定での攻撃到達性・実証は未検証であり、侵害発生の報告ではない |
| `msd-update`の単一processが検証・展開・書込みを兼ね、download経路なし | R04の権限集中と分離境界。検証済み入力をwriterへ渡す契約、失敗時の復旧を設計する。今回の分離実装はない |
| user tableなし、root無password console | 初回設定・認可・復旧手段と一緒にR02で判断する。consoleを無条件に封じて復旧経路を失う変更はしない。現行imageの再採取は未実施 |
| nftables・wpa_supplicant・dhcpcd未導入。NF_TABLES=m、SECCOMP/AppArmor/Landlock=y | 設定symbolの存在はfirewallや分離の稼働確認ではない。R07 fail-closed、R05/R06 Wi-Fi/IPの実装・負試験が必要。今回、packageや通信状態は再検証していない |
| RX8130CEは電池保持なし想定で起動時刻未確定 | 信頼時刻前のmetadata expiry、初回起動、rollback、offline復旧の共通前提。物理回路・実機時刻は未検証。RTCの存在だけで期限判定の信頼性を得たとはしない |
| RAUC custom backendの4 APIを確認、RPi firmware backend PR #1599は未merge | 当時の比較入力。上流PRの現在のmerge状態・製品への適合は今回未照会。[更新方式比較](../alternatives/updates.md)と実buildで再確認する |
| SWUpdate raw Ed25519は未確認、handlerの自由度あり | 未対応と断定しない。署名形式・検証backend・handlerの権限・bundle契約を一次資料と負試験で確認してから選定する |

R01〜R44の行ごとの全文監査表は添付原本が取得できず、完全再現できません。上の報告だけから44行の架空の完了表を作りません。Phase Aの順序と判断待ちは[残件文書](session-followup-2026-11-15.md)へ分けました。

## S1〜S4で訂正したPR

commitは修正の所在を示します。PRの現在のmerge状態、botの未解決finding数、全CI合格を証明する欄ではありません。通常mergeで先行修正を後続へ取り込み、S5の基点は#248の`49c7dc48f9499a82378c2aac5ebabfec74bb591c`です。

| 対象・修正commit | 主な訂正と残る限界 |
|---|---|
| [#245](https://github.com/uist1idrju3i/MSD-Linux/pull/245)・`7c6c13dca28fb55e941b0cf9a142588185df47e2` | E1の上書きguard、完了marker・全phase・hash・欠損/重複検査、fixtureを追加。nolazyは別mkfsでinode数も違い、独立した寄与量の測定ではない。8320は旧120秒区間、16952はboot＋idle合計。E2のm側swap無効を機能非等価と明記。旧rawは保持 |
| [#246](https://github.com/uist1idrju3i/MSD-Linux/pull/246)・`1d9986c99cf9eef7594198519fa30fbe2d3da540` | [option対応表](../storage/storage-option-coverage.md)で固定24入力・1344 tokenを分類。未実施1303、既測定10、対象外26、実行不能5。4K/8K消失理由は保存資料で確認不能。CLI ultraとmksquashfs、6.18.59 zswapとzram algorithm_params、DUP/RAID1C2、非暗号学的xxhash、keyslot/volume key、FAT keyfile、panicとslot選択を区別 |
| [#247](https://github.com/uist1idrju3i/MSD-Linux/pull/247)・`26db4812c496c4fc2d09417da6e5b5fd0f48b90b` | formatter、B2/B3判定器・上書き拒否・l22・次回期待v2を修正。B1はsize一致だけ、B2はkernel約135 KB差・計装差・0.5秒RAM sampling・random read p95未測定。B3は1-byte flip、原因は有力な説明に限定。NEONの無出典速度を除去。詳細は[storage訂正](../storage/storage-integrity-corrections.md) |
| [#248](https://github.com/uist1idrju3i/MSD-Linux/pull/248)・`1fadc3b3a8fbb8ca2748fc8a6f032a917b5bf139` | [E34](../../experiments/2026-11-15-fs-compare-matrix.md)は17/18 variantで差を反復、P136増加は非再現。120 T5＋54 T4-sync＝174成功、別に中断4、42群。F3/P044の遅いwriteとI2/L3最大88 sectorを記録。B2/P097 idle 0も新LUKS+btrfs DUP/xxhash/zstdの§10適合ではない |

### verityfmtの欠陥と判定器

`--salt-random N`はoption処理で`salt_given=1`にした後、`if (!salt_given)`に置いた乱数読込みを飛ばすため、CLIから未初期化saltを使う経路がありました。**code上の到達可能な欠陥**ですが、固定saltを使った旧B3がこの経路を通った証拠はありません。

S3で乱数読込み、strict hex、数値の空・末尾・overflow、I/O・fsync/close・params書込み失敗、SHA-256自己検査を修正し、tool生成imageのveritysetup readbackとhost負試験を追加しました。RS portの出典・license監査は未解決で、違反とは断定しません。監査完了まで製品formatterとして出荷しません。

B3の機能判定をboottimeから分離し、cause・期待mode・終了状態・ready＋corruptionの矛盾を検査します。generic panicだけをverity成功にせず、F6はrestart markerまたは新boot bannerを必要とします。旧CSV・期待表は書換えず、次回版へ分けました。修正後のQEMU suiteは未再実行です。

## CIとreviewの扱い

S0の保存logでPR #245（job `132612266632`）、#246（`132665946330`）、#248（`132720177521`）に次を確認しました。

```text
cve-monitor: NVD feed commit is older than 24 hours
##[error]Process completed with exit code 1.
```

これはrequired checkを実際に落としたfeed鮮度エラーです。保存した分析ではmainの同失敗とも照合していますが、現在のmain/feedを再照会した結果ではありません。製品codeに新しいCVEが見つかったこととも、CVEが存在しないこととも区別します。Automationが無視を求めても、gateを黙って迂回せず、鮮度回復または運用判断を利用者へ提示します。PR修正commitや一部checkのgreenだけで全CI合格としません。

公開reviewの修正件数、native review comment stream、Devin Review内部のfindingは別です。S0で取得できた公開情報だけから未解決findingゼロとは保証しません。PR本文と最終文書の同期には草案を作成しましたが、S4ではGitHub本文を更新していません。

## 進め方の改善

| 問題 | 次回の手順 |
|---|---|
| 入力生成・完走・機能・性能・製品化を一つの「完了」にした | 計画、実装、入力hash、完走、機能判定、性能有効性、raw保存、research、CI、実機を別statusにする |
| idleとquiesceの列を取り違え、最終文書だけ訂正した | 列の意味をschema化し、集計fixtureと独立読取りを先に行う。PR本文・索引・比較表を同じroundで更新する |
| 途中の期待・計装・kernel変更を同条件と扱った | 事前登録を版別に保持し、新期待・新run ID・dirty patchと変更時点を保存する。実行中のscriptや出力先を編集・移動しない |
| generic panic・SIGTERM・swap無効を見落とした | 正常、空、欠損、重複、途中終了、矛盾marker、無関係panic、同条件A/Aをfixture化し、負の対照を先に通す |
| 同じRS codeでの再計算を独立検証と扱った | 別実装/upstream比較・kernel負試験を分離する。保存後のhash一致も過去測定時の同一性の証明とはしない |
| 抽出本文なしの添付を復元済みと数えた | attachment ID・期待hash・復元方法・限界をmanifestへ。今回10版が完全復元不能であることを保持する |
| 並列build/QEMUのwall値や不確かなETAを性能判断へ使った | 固定入力・並列度・計装を記録。ETAは直近bootと残数から幅で示す。終了済みB3の旧PID監視を再開しない |
| reminderと利用者の停止判断、既決定が混在した | 発生順のeventを残し、後続の明示判断を優先。途中案やuser-actionsの再承認要求で既決定を消さない |
| 製品I/O・stackの境界が曖昧だった | 製品移行は2秒超progress・中断可否・RAM log・永続write例外を設計。slot英語例外を一般化しない。通常mergeで両側の索引を保持し、base変更・PR mergeは利用者が行う |

本監査は文書と証拠の対応を残す作業です。新しいbuild、QEMU、実機試験、製品設定変更は行っていません。次の実装承認と完了条件は[残件と順序](session-followup-2026-11-15.md)で判断します。
