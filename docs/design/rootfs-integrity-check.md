# 任意のrootfs完全性検査commandの設計

[rootfs設計](../research/storage/rootfs-squashfs-verity-fec-design.md) / [書き込みの台帳](write-policy.md) / [AGENTS.md §10](../../AGENTS.md)

## 現在の決定と対象

2026-11-16の設計です。command名は仮に`msd-verity-check`とし、**未実装**です。起動時・idle時・cronから自動実行せず、利用者が対象slotと検査範囲を選び、表示を確認した時だけ開始します。検査は読取り専用で、修復・slot切替・再起動を自動実行しません。製品の既定verity modeの選定はPhase Cでの比較と利用者判断待ちです。B3の実験段階Cを指すものではありません。

`veritysetup verify`の終了0、repairable、RSのsyndromeゼロを合格根拠にしません。根拠は[rootfs設計§2.5](../research/storage/rootfs-squashfs-verity-fec-design.md#25-完全性の証拠にするもの2026-11-16の設計方針)、[2.7.5のhost誤訂正](../experiments/2026-11-15-dm-verity-fec-host-dry.md)、[独立復号の再検査](../experiments/2026-11-15-dm-verity-fec-host-dry-resume.md)、[PR #260の上流研究](../research/storage/dm-verity-fec-upstream-2026-11.md)です。

許容する経路は、FEC後にもhash検証するkernel dm-verityを介した全mapped data読取り、または全dataからの独立したhash tree再計算と信頼するroot hashの比較です。前者は全範囲でEIO・破損eventがないこと、後者は再計算したroot hashの一致を要求します。FEC候補はhash検証後だけ回復と数え、host実験ではclean参照との全bytes一致を要求します。検査結果は当該範囲・時点だけの証拠で、悪意ある改ざんへのcrc32cの保証やSD全体の診断ではありません。

## 書き込まない範囲と中断

- SDのboot FAT、A/B slot、`/data`を含む全partitionへ書き込みません。検査対象はblock deviceをread-onlyで開き、mount・remount、fsck、parity再生成、discard、root hashの更新はしません。FECの訂正はRAM内の読取り結果に対するもので、SDへの修復ではありません。
- log・cache・lock・中間値は検証したtmpfsの`/run`か`/tmp`だけに置きます。永続領域を指すTMPDIRやsymlinkへのfallback、log export、shell history、core dump等の間接保存も許可しません。RAM不足なら失敗扱いで中止し、SDへ退避しません。swapのSD writebackも使いません。
- 診断はkernel logを消去せず読み、保存先はRAMに限定します。`sync`や全systemのcache dropを呼んでSDへのflushを誘発する設計にはしません。
- 読取りを停止してもcommandがSDを変更することはなく、Ctrl-Cで中断可能と表示します。ただしkernel内のI/O完了待ちには時間がかかり、panic/restartが発火した後はcommandから取り消せません。強制電源断がsystem全体として安全だとは表示しません。
- 中断・短いread・I/O error・観測欠損を成功にしません。中断時に部分結果を「clean」とせず、対象範囲・到達bytesを示して未完了とします。切替・書直しは別の利用者操作と確認・progressを必要とし、このcommandから呼びません。

既存OSのwriterが検査中にも動く可能性と、検査自身の書込み禁止は別です。[台帳](write-policy.md)の既存未対応は残し、検査の設計だけでsystem全体のSD writeゼロとはしません。

## 開始前と進捗

1. 対象slot、稼働rootか他slotか、data block数・block size・hash/salt・tree位置と信頼するroot hashの出所を表示します。認証された更新manifest等との結び付けは未実装で、確立できなければ開始しません。対象自身の未認証headerを信頼起点にしません。
2. 更新処理とRAM上のlockで排他し、検査中の対象・table・root hashの変更を禁止します。排他や安定性を確保できなければ未完了です。raw slotを検査のためにfilesystemとしてmountしません。
3. kernel経路ではignore_corruption等の検証回避を拒否し、`check_at_most_once`付きmapperを再検査の証拠に使いません。cacheの既検証bytesだけで完走しないよう、専用read-only mapper・検証されるI/O経路の設計と回帰試験が必要です。具体的なcache回避方式は未確定で、確認できるまで全読取り検査を有効にしません。
4. 開始時のstatusとkernel logのcursorを採取し、対象deviceに対応付けて観測します。kernel logの欠落・overflow、status取得失敗、対象の変更は完全性未確認です。read終了0だけで成功にせず、全data bytesを読んだことと、EIO・破損eventがないことを照合します。eventがあるのにread成功した場合も合格にはせず、訂正不能と断定せずに観測内容を示します。
5. 2秒以上かかり得るため、開始前に処理・対象・中断条件を表示し、実行中は検査済bytes/総bytes・割合・経過時間を更新します。分母はpartition容量やSquashFSのfile数ではなくmapperの全data範囲です。停止待ちも表示し、成功時だけ100%完了と判定します。

独立再計算の経路はtreeをstream処理するかRAMへ置き、SDに新treeを保存しません。既存treeの自己検査を再計算の代わりにしません。この方法でdataのroot hashが一致しても、保存済みtree全体や未使用parityが健全とは限らず、検査方式と範囲を結果に併記します。

## modeとの関係（Phase Cの判断待ち）

| 検査対象のmode | 全読取りで起こり得ること | commandの設計上の扱い |
|---|---|---|
| panic_on_corruption | 破損slotを読み、corruption処理が発火するとpanicします。FEC再入で訂正完了前にpanicする条件もあります | 通常の結果画面やCtrl-C復帰を約束しません。Phase C決定前はこのmodeでの検査を有効にしません |
| restart_on_corruption | corruption処理が再起動を要求します。次のslotやloop回避は別設計です | 自動切り戻し成功と扱わず、Phase C決定前は有効にしません |
| EIO（panic/restart指定なし） | 訂正不能ならreadにEIOが返る候補経路です。ただし稼働rootの別readが失敗すればsystem動作に影響します | 他slotの専用read-only検査mapperを候補としますが、採用は未決定です。稼働mapperのmodeを暗黙に変更しません |

`panic_on_error`/`restart_on_error`等の実tableも開始前に確認します。危険なmodeや不明なmodeを黙ってEIOへ置き換えず、開始を拒否します。別EIO mapperを作っても稼働root側のpanicを防げるとは限りません。[段階B/C](../experiments/2026-11-16-dm-verity-fec-followup-summary.md)の限定QEMU結果を製品のmode選定済みと読み替えません。

## 結果の分類と英日表示案

LCDとconsoleの両方へ英日併記する案です。CLIの終了code番号は実装時に定義しますが、全範囲の合格以外を成功codeにしません。下表は製品画面用の文言案で、実装・描画確認はしていません。

| 状態 | EN / JA表示案 |
|---|---|
| 開始前 | `Check slot {slot}: read-only. Ctrl-C cancels; do not power off.` / `slot {slot}を読取り専用で検査します。Ctrl-Cで中断できます。電源は切らないでください。` |
| 進捗 | `Checking {done}/{total} bytes ({percent}%), elapsed {seconds}s. Ctrl-C to cancel.` / `検査中 {done}/{total} byte（{percent}%）、経過{seconds}秒。Ctrl-Cで中断できます。` |
| modeで開始不可 | `Check not started: verity mode may panic or restart. Mode policy is pending.` / `検査未開始：verity modeによりpanic・再起動の恐れがあります。mode方針は未決定です。` |
| clean（検査範囲の照合完了、訂正counter差分0を取得） | `Verified; no FEC correction recorded in this check.` / `照合完了。この検査でFEC訂正の記録はありません。` |
| FEC訂正あり、全範囲hash検証成功 | `Verified after FEC; corrected-block counter increased by {n}. SD was not repaired.` / `FEC後の照合完了。訂正block counterは{n}増加しました。SDは修復していません。` |
| 照合完了、訂正数は取得不能 | `Verified; FEC correction count unavailable.` / `照合完了。FEC訂正数は取得できません。` |
| 訂正不能（最終EIO、または独立hash検証不一致） | `Verification failed; data could not be verified. Try the other A/B slot or rewrite this slot from a trusted update bundle.` / `検証失敗。dataを検証できません。別のA/B slotからの起動、または信頼する更新bundleでの当該slot書直しを検討してください。` |
| 破損eventあり、read成功だけでは合格にできない | `Corruption event observed; integrity not established.` / `破損eventを観測しました。完全性は確認できません。` |
| 中断・観測欠損・準備失敗 | `Check incomplete: {reason}. Integrity not established.` / `検査未完了：{reason}。完全性は確認できません。` |
| 中断待ち | `Cancelling; waiting for read I/O. Do not power off.` / `中断処理中。read I/Oの完了を待っています。電源は切らないでください。` |

kernel 6.18.59のstatusにFEC訂正数はありません。`V`等のstatusやerror不在から0件を推定せず、正常完走でも「訂正数取得不能」を表示します。v6.19以降の`fec_corrected_blocks`は実際のkernelの対応と意味を確認してから使い、対象mapperの開始前後の差分だけを表示します。非対応、counter減少、mapper交換や他readとの帰属不明なら数を出しません。counter値は固有の破損block数やSD寿命の推定ではなく、全範囲hash検証失敗を正値で打ち消すこともできません。版の根拠は[上流研究のstatus追加](../research/storage/dm-verity-fec-upstream-2026-11.md)です。CLIのrepairable表示や研究用RS traceから製品の訂正数を作りません。

「訂正不能」画面の推奨は別操作への案内だけです。他slotも未検査なら健全と断言せず、失敗slotを健全slotから信頼するbundleで書き直す手順・確認・progressは更新設計側で扱います。検査自体はboot flagや永続health記録も変更しません。

## 推論・未確認と実装前の検証

hash検証に基づく読取り専用検査なら、修復を伴わず判断材料を得られるという設計上の推論です。信頼するroot hashの配布、mapper/cache方式、error mode、update排他、counter・log観測、停止待ちのUI、console fontでの日本語とLCD表示は未実装・未確認です。独立再計算backendの製品搭載も未決定です。

実装前に正常・FEC回復・訂正不能・空/短い対象・不正params・信頼根拠欠如・中断・RAM不足・log欠損・counter非対応をfixture化し、英日文言の欠落や失敗後の成功表示を拒否します。cacheが検査を省いた負対照、panic/restart/EIOの対照、QEMUの時刻付きblock write計測を別途事前登録します。writeが出ないこと、全範囲の検証、表示・中断を個別に確認するまでは実装完了としません。

今回の変更は設計文書だけで、新しいQEMU実行・実機検証はありません。SD実I/O、FTL、LCD、firmware tryboot、電断、A/B復旧は未確認です。RS研究限定・監査完了まで製品出荷禁止・03914台帳同期保留を維持します。
