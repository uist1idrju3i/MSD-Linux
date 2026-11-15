# 2026-11-15 引継ぎ残件と実施順序

[監査本文](session-audit-2026-11-15.md) / [判断](session-decisions-2026-11-15.md) / [証拠](session-evidence-2026-11-15.md)

## 順序と承認の境界

元分析§4の残件を保存・訂正の実施後へ更新します。これは引継ぎ時点の未完了と依存関係の記録であり、新しい製品実装計画の承認ではありません。03914の構造化回答では、Phase S後は**A（認可・境界・通信）をB（storage製品化）より先**としました。B4〜B7は測定の順であり、表の番号を製品Bの先行承認にはしません。

`pending-work.csv`・`roadmap.md`のR16/R24/R28/R36/R37同期は保留のままです。状態や範囲を推測して行更新せず、再開には利用者の明示判断を得ます。実機未着のためPhase Hは未開始です。

| 順 | 元task | 更新後の現在地・次の完了条件 |
|---:|---|---|
| 0 | 未保全text・添付の救済 | S0で87候補＋FEC/build driver等を保存・push済み。18添付版中10版は完全復元不能。原本export待ちであり、保存済み注記を原本としない |
| 1 | PR #245〜#248の再検査・修正 | S1〜S4でcode・文書・fixtureを訂正、通常push済み。#248はfresh mainを通常merge。草案とGitHub本文は別で、最終review finding・全CIの現在状態は別照会が必要。NVD鮮度失敗は黙って迂回しない |
| 2 | B3追補 | 判定器修正済み、旧35 bootを保持。**修正後のsuite未実行**。F3 eio/restart、下位hash、parity/SB、sha256・FEC roots違いを次回版で検査。restart完了と製品A/B復帰を別に判定 |
| 3 | B4 cipher/hash | 未着手。AF_ALG/module・型・鍵長・全候補/実行不能理由を棚卸しし、PBKDF/data cipher/hash用途と安全性を区別。QEMUの機能/時間と実機絶対値を分離。AES・Camellia・ChaCha等全cipher、全hashの実機計画を保持。cipherは当面既定 |
| 4 | B5 btrfs | 旧fs-compareの観測はあるが、新基準LUKS＋data/metadata DUP＋xxhash64＋zstdのmatrixは未実施。T4/T5・破損回復・format/grow・idle writerと§10を確認。旧B2 idle 0を新構成の適合としない |
| 5 | B6 zram/zswap | 未着手。固定6.18.59の有効option分類は訂正済み。swap実有効を前提に圧縮/CPU/RAM/後段SD writeを測る。E2のswap無効mを比較基準へ流用しない |
| 6 | B7統合boot | 未着手。kernel/input/計装を固定し、verity/FEC/LUKSありなしを各5回。変更範囲・hash・機能と性能有効性を保存。QEMUの相対順位を実機へ一般化しない |
| 7 | Phase C設計 | FEC配置、LUKS鍵lifecycle、既定slot/trial別rollback、product-decisions/write-policy・R36等の判断が残る。既決定を維持し、台帳同期は保留。実装前に利用者判断を再提示 |
| 8 | 製品migration | まだ測定基盤段階。genimage/post-image/cmdline、署名bundle配置、msd-update/health、data init/grow/復旧、既存card移行と進捗表示・中断可否を設計・test。Phase Aを先行し、実装承認後に進める |
| 9 | ext4撤去 | btrfs移行後の条件付き既決定。S02/msd-data-growと旧card移行を先に置換し、その後EXT4/e2fsprogs依存・復旧手段を検査して削る。現時点では未実施 |
| 10 | 03914 slot表示 | 2026-11-15にS98msd-readyへ実装。[書込み・画面方針](../../design/write-policy.md#ramに置いているもの)に限定的な英語のみの判断を反映。host fixtureとQEMUの条件・結果は[検証記録](../../experiments/2026-11-15-boot-slot-banner.md)を参照。LCD/firmwareは実機待ち |
| 11 | 03914 Phase A | 調査・計画まで。R03境界とframework比較の結果を再提示し、承認後に実装。原本3件未取得のためR01〜R44全文監査表は再現未完了。以下の順序を保持 |

## 製品rollbackと鍵の未決設計

panicやrestartだけで別slotへ自動的に移るとは限りません。panic timeout/watchdog、既定slotとtrial slot、S99health後の破損、両slot破損、永続flagの書込み時機を決め、成功・失敗・電断を試験します。破損検出＋切戻しの範囲を守り、crc32cを暗号学的tamper resistanceへ読み替えません。

LUKSは解錠鍵の配置、初回生成、変更・紛失・再暗号化・復旧、header backupの保護と削除を決めます。FAT平文keyfileは未採用です。書込みを伴うformat・grow・scrub・回復・更新は、利用者操作か理由付き例外、2秒超progress、中断可否、RAM logを[製品I/O規則](../../../AGENTS.md)に沿って設計します。台帳の「未対応」を小容量・収束だけで適合へ変えません。

## Phase Aの順序と利用者判断

03914の`event-01a1dd85c87374139b483dda4244c085`の提案順を保持します。実装承認はまだありません。

1. R03境界・`/etc` allowlist。RAUC/SWUpdate比較を早期並行し、自作writerを維持するかの入力を得る。
2. R02 user/認可/初回設定/復旧。root consoleの制限と復旧不能の回避を併せて決める。
3. R04権限分離。検証・展開・書込み・downloadの契約と失敗境界を決める。
4. R07 fail-closed firewall。その後R05/R06 Wi-Fi・IP・信頼時刻を実装する。
5. A6 manifest契約、A8 metadata、A9 client。RTC未信頼時のexpiryとoffline/復旧を含める。

allowlistの内容、consoleを封じる方法、RAUC/SWUpdate採否、TUF採否・expiry、Ruby/mruby等の対話toolの工程位置、egress制限の厳しさは利用者判断待ちです。RAUC上流PR #1599の現在状態とSWUpdate raw Ed25519は改めて一次資料・実buildで検査します。計画全体はS→A→B→H→R→Mであり、実機を必要としないAの境界設計と、到着待ちHを混同しません。

## 消してはいけない旧残件

P085 simple-quota（古いbtrfs-progsの制約）、P087 T6 mixed非対応、SSH client・RAUC・OpenSSLの実build等はE34完了で消えません。初期計画の対象外を完了へ移しません。RS portの出典・license監査も残り、監査前の製品formatter出荷はしません。

実機の全cipher/hash、firmware tryboot、SD/電断、LCD・keyboard・I2Cは未実施です。l19/l22の同条件再測定、random read p95、実機RAM/CPUの評価も残ります。新しい測定を始める際は旧rawと旧期待を保ち、case・入力・binary・計装hash・失敗attempt・完了markerを実験文書とdata枝へ対応付けます。
