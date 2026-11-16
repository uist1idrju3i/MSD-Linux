# B3追試B〜Fの総括

[実験索引](README.md) / [事前登録・実行前amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [研究への反映](../research/storage/storage-integrity-corrections.md)

## 終了状態と期待一致数

2026-11-16 UTC、B〜Fの43条件・正式215 trialを終了しました。正式195件が既登録の期待と一致し、20件は反証です。期待を実測後に変更していません。smoke・clean事前確認は別の43件で39一致。**試した条件のQEMU結果であり、全条件合格・製品採用・実機検証ではありません。**

| 段階 | 条件数 | smoke/clean事前確認 | 正式期待一致 | 主な結果 |
|---|---:|---:|---:|---|
| [B](2026-11-15-dm-verity-fec-stage-b.md) | 10 | 8/10 | 40/50 | EIO通常/RAMの訂正read成功は読取り-EIO期待への反証 |
| [C](2026-11-16-dm-verity-fec-stage-c.md) | 10 | 8/10 | 40/50 | lower-head/tailは正常read期待に反してguard後panic |
| [D](2026-11-16-dm-verity-fec-stage-d.md) | 18 | 18/18 | 90/90 | hash2種×roots 2/8/16、clean/data/超過の期待と一致 |
| [E](2026-11-16-dm-verity-fec-stage-e.md) | 4 | 4/4 | 20/20 | 9/24 blockの集中はpanic、分散は訂正read成功 |
| [F](2026-11-16-dm-verity-fec-stage-f.md) | 1 | 1/1 | 5/5 | guest-resetと2回目bannerをhost停止前に観測 |
| 計 | 43 | 39/43 | 195/215 | 258 trial中234期待一致 |

集計元は各結果文書と同名のCSVです。`phase=formal`を正式として数え、`functional_pass=True`を期待一致とします。Bの事前確認10件はCSVの`clean-smoke`2件と`smoke`8件の合計で、他段階は`smoke`だけです。初期失敗・host検査・Fの0 boot launch失敗はこの258件に混ぜていません。Fのtrialは2回目bannerまでで、完全起動を2回確認した意味ではありません。

[Aの35回](2026-11-15-dm-verity-fec-stage-a.md)は当時のv3期待35/35一致として別保存しています。readall独立marker/loginが未観測で、B以降とはpack hashも異なるため、上表へ合算して厳密なclean成功数を増やしません。当初の48条件/240 bootという計画は履歴として残し、Bの実行前amendmentによる2条件追加と区別します。

## 観測から言えること

- **BのF3**：同じbio IDでFEC内hash lookupの再入→level1 guardの-EIO→panic/restartを観測しました。EIO通常/RAMでは各5/5で訂正後read成功となり、既存EIO期待を反証しました。RAMの明示readでも同経路なのでroot mount前だけの説明には反します。guard無効化対照はなく、全構成の因果へ一般化しません。
- **C-lower-headとlower-tail**：各正式5/5、smokeを含め各6/6でpanic。事前期待は正常readのままです。data両端・parity＋対応dataの訂正成功と区別し、parity単独・superblock・非保護領域のread成功を修復やintegrityの証明にはしません。
- **D**：roots2超過ではcrc32c/SHA-256とも各正式5/5でRS正値→復号候補のhash不一致→位置あり再試行も拒否→panicを観測しました。guardは0回で、B/Cのguard経路とは別です。kernel候補bytesはdumpしておらず、hostの誤訂正候補との全bytes一致は未確認です。
- **E**：集中の正式10件は位置ありRSが8を返してもhash不一致で拒否され、分散の正式10件はRS訂正成功とreadall完了→ready→loginを観測しました。総block数だけでなくcodeごとの負荷を区別する必要があります。全patternの保証ではありません。
- **FのF6観測**：正式5/5で破損→restart→guest由来QMP RESET→2回目banner。hostからreset命令を送っておらず、SIGTERMは証拠観測後です。`-no-reboot`下の自然終了、2回目の完全起動、別slot復旧とは別の判定です。

RS能力超過の誤訂正は想定される挙動であり、syndromeゼロ・veritysetup終了0・repairable表示は元bytesへの回復を保証しません。[host再検査](2026-11-15-dm-verity-fec-host-dry-resume.md)の回復判定は独立decoder出力とclean参照の全bytes一致だけです。host観測とD/Eの特定入力におけるkernelのFEC後hash再検査を区別し、全誤訂正の拒否・crc32cの暗号学的保証・製品安全性へ広げません。

## 失敗・逸脱・欠損を残した場所

| 記録 | 当時の停止・不足 | その後の扱い |
|---|---|---|
| [最初のB clean smoke](2026-11-15-dm-verity-fec-stage-b-smoke.md) | readall marker欠落。initcall_debugを継承しなかった未記載逸脱も検出 | 承認後のamendmentを先にcommitし、明示的shell/helperと新packで再実行。旧raw不変 |
| [B再開smoke](2026-11-15-dm-verity-fec-stage-b-resume-smoke.md) | 通常read成功、RAM cleanはloader探索失敗でpanic | lib64 aliasと依存閉包検査を追加。正式B前の通常/RAM clean成功とは別保存 |
| [host一括検査の停止](2026-11-15-dm-verity-fec-host-dry.md) | DのCLI終了0を拒否するgateで停止。原runのD中間境界rawは未保存 | 承認後にCLIと回復判定を分離し、新runで中間値を即時保存。原runの欠損が埋まったとはしない |
| [C結果](2026-11-16-dm-verity-fec-stage-c.md) | lower hash両端の正常read期待を反証 | 不一致12件（smoke2＋正式10）を保存し、成功へ分類変更しない |
| [E結果](2026-11-16-dm-verity-fec-stage-e.md) | 監視再接続 | 稼働中container/process/script/入力は変更も再起動もせず継続採取 |
| [F結果](2026-11-16-dm-verity-fec-stage-f.md) | rootless DockerのUID指定違いで出力作成がPermissionError、0 boot | mappingを確認してhost所有者へ写るUIDに合わせた。失敗stderr/wallをarchiveへ収録。条件・期待・scriptは不変 |

watchdog driverは事前amendmentどおりrestart系で有効、panic/EIO系は無効です。したがってmodeだけの因果比較ではありません。Bの新helper・packはAとは異なるhashで、B内の3 modeは同じbytesを使いました。boottime valid、marker判定、全module load、正常製品bootを混同しません。既知のmodule署名拒否はrawに残っています。

## 保存と再照合

各結果文書からCSVとevidence archiveを参照できます。archiveにはserial/QMP/判定、case設定・入力hash・注入位置、固定source・collector・driver log・wallを収録しました。入力本体は共通packとsuffixを含むhost記録を併せて参照します。bootごとのPopen argv/env全体の独立snapshotとkernel候補bytesは未保存です。

| 段階 | archive SHA-256 |
|---|---|
| C | `6501a5846f40978157f125391849f47e972241591218eba5e3a25756dae5e244` |
| D | `5ba4d7d0e0d84c1636e0e504a0070d85d0ea04f23358f7ea8d2ecf90382077c3` |
| E | `fe5e85f7327fd34b9fc1497c59d1614a7e19c474cf51cc1f828c337af52bc8d6` |
| F | `0e4fb7eca1866542491b82da8c6a66b718c719a2391a99eb711834087b3aa70f` |

C/Dは先行commit `452a741`（文書強調修正`c795b67`）/`6577a1b`、Eは`4125a0e`、Fと本総括は本記録のcommitに保存します。raw・CSV・期待表を上書きせず、既存data branchや履歴の結果も変更していません。[利用者の設定確認](../research/verification/session-decisions-2026-11-15.md)には2026-11-16 09:24 JSTの`~ALL`・bypass list・Web Analytics回答も保存済みです。

## wallと36時間上限

| 段階 | smoke driver秒 | 正式driver秒 | 正式boot wall合計秒 |
|---|---:|---:|---:|
| C | 2375.707 | 11540.900 | 11511.65046835682 |
| D | 4175.688 | 20734.782 | 20680.84396872096 |
| E | 980.684 | 4799.697 | 4787.875741162046 |
| F | 231.619 | 1158.255 | 1154.854771015991 |

driverは入力検査・copy等を含み、boot wall合計とは別です。Fの最初の0 boot launchは別途0.575秒。Bの正式driverは11445.745秒でした。値はhost上の所要時間で、実機性能の比較ではありません。

累積時計は初回事前登録の2026-11-15 12:17:52 UTCから、失敗・host調査・待機も含めます。E終了時は約23時間2分、F終了時は約23時間34分で、保存・検査にさらに1時間を予約しても約24時間34分です。deadline 2026-11-17 00:17:52 UTC、36時間上限の延長は不要でした。追加bootの予定はありません。

実機のSD実I/O・LCD・firmware tryboot・電断・A/B復旧は未確認です。RSは研究限定で、provenance監査完了まで製品出荷禁止、03914台帳同期保留を維持します。QEMUの反復結果、法的な出荷判断、実機適合はそれぞれ別です。
