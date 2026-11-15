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

## 次回harness

B3の旧 `run-all.sh` とF3のready期待は歴史的事前登録として保持します。次回は [v2](../../../board/cardputerzero/tools/bench/dm-verity-fec/run-all-v2.sh) と別の期待表を使います。機能合否はboottimeのvalidと分離し、verity固有のcause・期待mode・終了状態・矛盾markerを照合します。generic panicやhost SIGTERMだけでは成功にしません。F6にはrestart markerまたは新boot bannerが必要です。

B2は既存caseの黙示再利用を廃止し、l22を含む8 caseを一括生成します。旧計測値の補完や過去の再現済みという主張はしません。今回QEMU suiteを再実行せず、host fixtureで計測器の正常・空・誤検知・上書き拒否を検査します。
