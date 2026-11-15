# 2026-11-15 利用者判断とeventの対応

[監査本文](session-audit-2026-11-15.md) / [証拠の所在](session-evidence-2026-11-15.md) / [残件](session-followup-2026-11-15.md)

event IDは元sessionのIDです。原文と当時の履行評価はS0 archiveの`audit/analysis-2026-11-15.md`へ保存し、ここでは現在の判断・未完了を区別します。表の「記録済み」は製品実装済みではありません。03914と5917の全31利用者/Automationメッセージと構造化回答を対象にしています。

## 5917の設計・測定判断

| event ID | 判断・要求と現在の状態 |
|---|---|
| `event-01a1dbb100837dc5988b5bb885d2304b` | 先行sessionを参考に時間のかかる実測を実施。E1〜E4、B1〜B3の条件とrawを保存。全測定の完了ではない |
| `event-01a1dce0c0fc7997a39f418f10bf02ab` | 区切りで中断し計画・メモ・taskを残す。rootはSquashFS＋zstd＋dm-verity(crc32c)＋FEC、破損時A/B復帰。dataはLUKS＋btrfs、metadata/dataともDUP、xxhash64。SquashFS/zstd/verity/LUKS/btrfs全option測定。設計・代表測定は保存、製品migrationと全option実測は未完了 |
| `event-01a1dce67b4a71c5b3a2b0d42e1cd89f` | btrfsはzstd透過圧縮、zram/zswapも全option測定。設計と固定版の分類を保存。新data構成・B6実測は未完了 |
| `event-01a1dcfe88267a38b7b3e5461625ff50` | 良いタイミングで中断前作業を再開してよい。E34を完走・保存。全後続taskの実装承認へ広げない |
| `event-01a1dd013f107688954612be5777df50` | btrfs移行後にext4を無効化し軽量化。条件付き既決定。既存card移行・S02/grow置換より先にEXT4/e2fsprogsを削らない |
| `event-01a1dd0bb2bd7fa491403c263fe5be9c` | crc32cが難しい場合はsha256へfallback、NEONを深く調査しresearchへ。crc32c優先を維持し、fallback候補と記録。実機速度で選定済みではない |
| `event-01a1dd0e09e57f98912d07e4d48e55cb` | 調査対象は`sha256_block_neon`。調査を保存、無出典速度をS3で訂正。NEONとARM crypto extension、QEMUと実機を区別 |
| `event-01a1dd3f15477202a8430a9151ebb6be` | 配布はCI/CDなので圧縮時間を選定理由にしない。cipherはCamellia/ChaChaを含む安全性・実機演算性能で後日選定し、当面は既定。`aes-xts-plain64`暫定維持。PBKDF、data cipher、鍵長、安全性を別評価とする |
| `event-01a1dd4070f870f1b808b3dcc22bf1a4` | AES・Camellia・ChaCha等、全cipherを実機bench。計画化のみ。実装可能性・型・鍵長・AF_ALG/moduleを列挙し、実行不能理由も保存する。ARMにAES-NIを仮定せず、QEMU順位を実機の代理にしない |
| `event-01a1dd413bca7c8a8b430e422e4f0ea3` | B1でultraを付けたか確認。mksquashfsの`-Xcompression-level 22`とzstd CLIの`--ultra -22`を区別して記録 |
| `event-01a1dd43c47278a5b75dea399dbc0d9c` | 実機未着のため実機テスト計画として整理。計画保存、実機測定なし。機材到着を推測で完了扱いしない |
| `event-01a1dd52adc87213af6b17d529bd5d77` | hash algorithmも全数実機計測。未実施。用途・利用可能性・安全性と速度を分け、`/proc/crypto`だけを網羅表にしない |
| `event-01a1dd68496e79c382417a2d2b177ee5` | l19/l22のQEMU RAM・展開速度を比較し、本当に展開側に悪影響がなければ22。各5回のB2を保存。ただしkernel/計装差・RAM samplingの制限があり、悪影響なしの証明ではない。**l22は条件付きで保持** |

設計の本文は[rootfs](../storage/rootfs-squashfs-verity-fec-design.md)・[data](../storage/data-luks-btrfs-design.md)・[zstd](../storage/zstd-usage-and-options.md)・[網羅表](../storage/storage-option-coverage.md)です。DUPは同一device内の2copyで独立deviceのRAID1C2ではなく、xxhash64は非暗号学的です。LUKSのvolume keyと解錠鍵、`luksChangeKey`によるkeyslot変更を区別し、FAT上の平文keyfileを既定採用しません。

## 03914の判断と最終slot表示

| event ID | 判断・要求と現在の状態 |
|---|---|
| `event-01a1dd5576897b348d0e0b8399479960` | 全体計画に対する深い実装監査と今後の計画。調査回答を保存したがR01〜R44添付全文は復元不能で、全行の再照合は未達 |
| `event-01a1dd82721577179ee06003de5d5f1a` | 構造化回答4件: 実機は未着、Phase S後はA（認可・境界・通信）を先行、verity/FECは破損検出＋tryboot切戻し限定、台帳同期は保留。いずれも維持。tamper resistanceや信頼の起点の実現としない |
| `event-01a1dd82c9d97ca690b03c8d32510f4d` | 今は深い調査と計画まで、commit/push不要。03914では尊重。今回のS0〜S5保存・訂正は後続の別指示によるもので、当時の指示違反と混同しない |
| `event-01a1ddc984c77eefbbca4062dea5401c` | slotをバナー前の青/緑丸で示す可否。検討済み、後続判断で置換され現在の仕様ではない |
| `event-01a1ddcd386f78b1a878ce6fe380e34f` | 無色の(A)/(B)、trialは小文字案。後続の英語別行に置換。途中案を実装しない |
| `event-01a1ddcf43b37975a211a25b2c4fc540` | readyにcommit hashが出るかを確認。readyと別のversion表示を区別。表示例は実採取logではない |
| `event-01a1ddd08cf2715db2d77c9510a294a9` | 起動時表示を全行提示。再構成例を提示したもので、QEMU/実機の採取証拠とはしない |
| `event-01a1ddd65fa87c0a8e97aaa5c861d212` | serialとLCDの両方、issueへは付けない。文言をBoot from slot形式へ変更 |
| `event-01a1ddd85a907e499ff40b3506001719` | A案を採用し、今回はLCDも英語のみを許可。最終仕様として保存、実装は未着手 |

最終仕様は`S98msd-ready`で`MSD/Linux ready`の**直前の別行**に`Boot from slot A`またはB、試行中は`Boot from slot A (try)`またはBを出します。serialとLCD `/dev/tty1`の両方へ、tty1がなければskip。未知は`Boot from slot ?`、`/etc/issue`は変更しません。

判定はDT nodeとtrybootを読む`msd-update status`を再利用し、失敗時に`/proc/cmdline`の`root=/dev/mmcblk0p5`（A）/p6（B）へfallbackします。将来のdm rootではこのfallbackだけで判定できないためDT経路との整合が必要です。英語だけの許可はこのslot表示に限り、製品全体の英日併記規則を解除しません。正常A/B、trial、不正/欠落、未知、status error、tty1なしの試験と実機LCD確認が残ります。

## RS formatterの研究限定利用（2026-11-15追記）

本sessionで利用者は、provenance監査を並行して続けながらRS formatterを**研究限定で利用する**ことを承認しました。製品への組込み・出荷は監査完了まで禁止のままです。[B3追試の事前登録](../../experiments/2026-11-15-dm-verity-fec-followup-prereg.md)と[固定上流sourceの初期監査](../storage/rs-formatter-provenance-2026-11-15.md)へ記録しました。監査完了・license違反・追試成功の判断ではなく、03914の台帳同期保留も解除しません。この追記の判断元は本sessionの利用者指示で、過去sessionのevent IDは付けません。

## 進捗・停止・Automation

2026-11-15のP2追記：上記は判断保存時点の状態です。slot表示をS98msd-readyへ実装し、[host fixtureとQEMU A/B](../../experiments/2026-11-15-boot-slot-banner.md)で検査しました。実機LCD/firmware trybootは未確認のままです。今回の限定的な実装承認で、03914の台帳同期保留は解除しません。

以下の要求は製品の採否を変える決定ではありませんが、引継ぎから落とさないようeventを対応付けます。

| event ID | 要求・履行と限界 |
|---|---|
| `event-01a1dc91961e73ed8ace4898ffcc9d0e` | E3/E4の概要・ETAを質問。進捗回答済み。ETAは性能の測定値ではない |
| `event-01a1dc93851c79a3b442d038664dd751` | fs-compareの対象を質問。対象を回答。代表構成を全optionとしない |
| `event-01a1dd2f83837278bce1e9290140532d` | 進捗・定期監視を確認。状態を回答。旧PID監視の再開指示ではない |
| `event-01a1dd429a08773aab70b0a1ddd76f04` | task管理、完了/実行中/残時間/計画を要求。報告済み。残件は別文書へ保持 |
| `event-01a1dda9d38b7c0c86488a0b226c802a` | 進捗質問。回答済み |
| `event-01a1ddc51e057638a7e537192a6de45b` | 進捗質問。E34/B2保存とB3開始を報告。B3成功の確約ではない |
| `event-01a1ddf25359751c9812c43f724ed30c` | continue。B3継続 |
| `event-01a1de3f66497960a8c3f5b6d19a9313` | taskとETAを要求。B3と残件を報告 |
| `event-01a1de486aa87285a8f34588f319a416` | 区切りで終了し、忘れたtaskと改善を振返る。B3とraw保存後終了。B4以降の完了ではない |
| `event-01a1de581ba07f20a181f845512622ff` | AutomationはB3保存・review/CI・B4以降を要求し、NVD失敗の無視も指示。B3保存済み、B4未着手。host SIGTERMをrestart成功にしない。利用者の終了判断を優先し、required checkの失敗を隠さない |

既決定をuser-actionsの再承認依頼で未決定へ戻さず、実機未着をQEMUで代替完了にしません。実装の順序・承認待ち・測定の完了条件は[引継ぎ残件](session-followup-2026-11-15.md)を参照します。
