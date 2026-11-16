# storage実験B1〜B3・E34の訂正とformatter監査

## E34の反復・因果・規則適合

[E34](../../experiments/2026-11-15-fs-compare-matrix.md)のT5は18 variant中17で差を反復し、P136の増加は非再現でした。idleはf2fs F3/P044に遅いwrite、I2/L3に最大88 sectorの追い書きを観測。B2/P097の各3回0も、新LUKS+btrfs設計の§10適合ではありません。174成功runを42群へ集計し、4中断attempt・harness差分・集計器をdata枝へ追補保存しました。

## B1〜B3とformatter

2026-11-15。過去のraw・CSVを改変せず、誤った説明と次回の計測器を訂正します。03914の台帳同期保留は維持し、全option測定や製品移行の完了とはしません。

| 対象 | 旧説明 | 訂正と記録 |
|---|---|---|
| [B1](../../experiments/2026-11-15-mksquashfs-matrix.md) | l19/l22はbytes完全一致・同じimage、buildが短い19を採用 | 同じsizeだけ。1Mのhashは相違。build時間を製品選定理由にせず、利用者の条件付き22を保持 |
| [B2](../../experiments/2026-11-15-squashfs-boot-read-bench.md) | kernel差は影響なし、RAM差は誤差、22に悪影響なし | kernel約135 KB差、途中のbegin/mem計装追加、0.5秒RAM samplingを交絡・限界として残す。誤差の校正・random read p95・実機性能は未測定 |
| [B3](../../experiments/2026-11-15-dm-verity-fec-corruption.md) | 同じRS再計算でformatter欠陥を否定、下位hashも修復可能 | 自己整合だけで独立検証ではない。再入依存は有力な説明に限定し、eio/restart対照・下位hashを未実施へ |
| B3 | 1 bit、F2は9 block、F6はrestart成功 | 保存記録は1 byte反転・24 block。新生成器を24 blockのbyte全反転へ合わせる。旧sourceの9 block/bit注入との差を明記。F6はhost SIGTERMでrestart完了未確認 |
| [NEON調査](arm64-neon-crypto.md) | 桁違い、1 byte/cycle、2〜3倍、100〜200 MB/s、常にNEON | 出典・実測がない速度を撤回。固定sourceのcap/config/`may_use_simd()` gateと、QEMU観測・実機未確認を分離。crc32c判断は維持 |
| product-decisions | 全option実測は未着手 | B1〜B3の限定条件は既測定だが全option・B4〜B7は未完了 |

## formatterの修正範囲

`--salt-random N` が固定salt指定扱いになり乱数読込みを飛ばす欠陥を修正しました。過去の固定saltのB3がこの欠陥を踏んだという証拠はありません。hexの全桁、数値の空文字・末尾・overflow、画像とparamsのI/O完了を検査し、自己検査はCRC32CとSHA-256両方を比較します。

host回帰は `docker/msd-dev tests/dm-verity-format/run.sh`。固定salt、乱数長と複数試行での変化、独立したPython SHA-256 readback、invalid/empty入力、短いimage、read/write/fsync/close/params失敗を含みます。fault注入はhost testだけです。既存のveritysetup比較に加え、readbackの対象をtool生成imageへ変更しました。kernel/実機の読み出し保証ではありません。

今回のhost結果は入力系6 test・harness 3 testがOK、SHA-256のroot/hash area/FEC parityがveritysetupと一致し、tool生成imageのverifyも成功しました。QEMU suiteは再実行していません。再現可能な検査本体は `tests/dm-verity-format/` に保存しています。

RS部分はPhil Karn由来libfecのportとのcommentがあります。正確な移植元revision・copyright通知・変更・license条件の監査は未解決です。違反とは断定せず、監査が済むまで製品formatterとして出荷しません。hash/FECの一致と法的な出荷可否を混同しません。

2026-11-15追記：利用者は監査と並行する研究限定利用を承認しました。[初期監査](rs-formatter-provenance-2026-11-15.md)に固定上流比較を、[B3追試](../../experiments/2026-11-15-dm-verity-fec-followup-prereg.md)に次回の条件を保存しました。監査未完了・製品出荷禁止は変わりません。

同日の[v3計測器smoke](../../experiments/2026-11-15-dm-verity-fec-stage-a-smoke.md)では、同じF3破損がpanic modeではFEC内のhash検査でpanic、両flagなしでは1 error訂正後にreadyとなりました。各1回の対照で、再入guard自体は未計装です。F6は既存wrapperのwatchdog driver無効化を外した対照で自然終了とQMP RESET・2回目bannerを観測しました。旧F6を成功へ変更せず、実機A/B復帰とも扱いません。

[amendment後のstage A](../../experiments/2026-11-15-dm-verity-fec-stage-a.md)は7条件各5回でv3期待35/35一致でした。F3のFEC内hash検査からのpanicと、F6のdriver有効時の自然終了0をそれぞれ5/5観測しました。反復性とguard自体の因果は別で、後者は未計装です。通常起動のreadall独立marker/loginとmodule署名は残件のため、原計画の全検証や製品boot成功とは扱いません。

[Bの最初のclean smoke](../../experiments/2026-11-15-dm-verity-fec-stage-b-smoke.md)はready/loginまで進みましたがreadall完了markerがなく、厳密なclean判定で停止しました。実inittabと実BusyBox binaryの逆assemblyから、initが加えるexecによりdd後のechoが実行されない説明を強く支持します。旧A/v3の結果は当時のmarker判定として保持し、期待や判定を後付けで緩めていません。B正式反復・C〜Fは未実行、研究用helperと再packの承認待ちです。

利用者承認後の[再開smoke](../../experiments/2026-11-15-dm-verity-fec-stage-b-resume-smoke.md)では、明示的shell経由の新helper・新packで通常経路のreadall→ready→loginを観測しました。一方RAM cleanはlibresolv探索失敗でinitが終了し、再停止しました。実CPIOにはlibrary本体がありますが、元treeのlib64 aliasがなく、実loaderの既定探索先と合いません。alias欠落を強く支持し、動的traceと修正後bootは未確認です。RAM読取り・F3 mode比較・正式B・C〜Fは未実行で、次の修正承認を待ちます。

利用者承認後の[host一括検査](../../experiments/2026-11-15-dm-verity-fec-host-dry.md)では、alias保存と実DT_NEEDED閉包を実装し、旧CPIOを同じcheckerで拒否しました。新CPIOはhost検査成功ですが、修正後RAM bootはまだ未確認です。37/43入力の生成時点で、DのSHA-256/roots2・同column 3 block破損にveritysetupがhash失敗を表示しながら終了0を返し、host gateで停止しました。独立RS復号はsyndromeゼロでも元bytesと異なるcodewordとなり、CLI終了0を完全回復の根拠にできません。残りD6入力・B clean再試行・正式B〜Fは未実行で、boot期待は変えていません。共通pack・D新規suffix・initramfs・metadata・rawを上記archiveに保存しました。次はhost回復判定の修正と中間値の即時保存の承認が必要です。

## 正式Bの結果（2026-11-15 UTC）

上の停止・未確認の記述は各記録作成時点の状態です。[正式B](../../experiments/2026-11-15-dm-verity-fec-stage-b.md)はalias修正・host全43入力照合後、両cleanを含む10 smokeと正式50 bootを完了しました。正式は40期待一致、EIO通常/RAMの10件は訂正後read成功で既存のEIO期待に対する反証です。clean失敗・timeoutはなく、旧期待は変更していません。

同じbio IDでFEC内hash lookupの再入、level1 guardの-EIO、その後のpanic/restartを全反復で観測しました。EIOは各243 guard後にRSが1 symbol訂正してread成功となり、容量超過だけの説明を反証します。RAMの明示read後も同じ経路なのでroot mount前だけの説明にも反します。本条件での経路は高確度ですが、guard無効化対照や全hash/rootsの一般化、RS誤訂正のkernel拒否、実機適合は未検証です。C〜Fはまだ未実行です。

## 次回harness

### Cの位置境界追試（2026-11-16）

2026-11-16の[stage C](../../experiments/2026-11-16-dm-verity-fec-stage-c.md)は正式50件中40期待一致でした。lower hash先頭・末尾は各5/5で再入guard後panicとなり、単一byteなら正常読取りという期待に反しました。data両端とparity＋対応dataは各5/5正常読取り。parity単独・superblock・範囲外の正常読取りは、FEC修復や範囲外integrityの証明ではありません。既存期待は変えず、QEMUと実機を区別します。

### 容量超過の誤訂正と製品設計への示唆（2026-11-15承認、host限定）

RS訂正能力を超えた入力が、元とは異なる正しいcodewordへ誤訂正されることは想定される挙動です。syndromeゼロは元bytesへの回復を保証しません。上のhost観測をRSの保証範囲内の不具合やkernelの回復成功とは扱いません。利用者承認により、hostの回復判定は独立decoder出力とclean参照bytesの一致に限定し、誤訂正・拒否を分け、CLI応答は観測値として記録します。

**製品設計への示唆：veritysetupの終了0やrepairable表示をintegrityの証明にしてはいけません。** FECで得た候補をhashで再検査するkernel側の防御が重要です。今回の検証範囲はhostで、kernelのFEC後hash再検査を今回のQEMUや実機で検証したわけではありません。製品適合・安全性の結論へ拡張せず、研究限定と出荷禁止を維持します。

承認後の[host再検査](../../experiments/2026-11-15-dm-verity-fec-host-dry-resume.md)でD18入力を完了し、全43入力を照合しました。独立decoder出力と参照imageの全bytes一致は12件、別codeword2件、拒否4件です。新runの中間値を即時保存し、前runの欠損と区別しました。CLIは観測値のままで、boot期待・研究限定・実機未確認は不変です。

B3の旧 `run-all.sh` とF3のready期待は歴史的事前登録として保持します。次回は [v2](../../../board/cardputerzero/tools/bench/dm-verity-fec/run-all-v2.sh) と別の期待表を使います。機能合否はboottimeのvalidと分離し、verity固有のcause・期待mode・終了状態・矛盾markerを照合します。generic panicやhost SIGTERMだけでは成功にしません。F6にはrestart markerまたは新boot bannerが必要です。

B2は既存caseの黙示再利用を廃止し、l22を含む8 caseを一括生成します。旧計測値の補完や過去の再現済みという主張はしません。今回QEMU suiteを再実行せず、host fixtureで計測器の正常・空・誤検知・上書き拒否を検査します。
