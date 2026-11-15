# B3 stage A計測器のsmoke

- 日付: 2026-11-15
- 状態: 計測器の構築確認。正式なstage A反復試験ではない
- 基準: 事前登録commit `6451189ed58b0d9fd2395cc52456c7da3a4f6ddf`と今回のharness差分
- 関連: [事前登録](2026-11-15-dm-verity-fec-followup-prereg.md)、[旧B3](2026-11-15-dm-verity-fec-corruption.md)、[RS監査](../research/storage/rs-formatter-provenance-2026-11-15.md)

## 目的と範囲

F3の注入位置・FEC列・既知消失の復号可否と、panic/restart/EIOの違いを記録する計測器を追加しました。F6は`-no-reboot`の自然終了と、reset許可時のQMP RESET・2回目kernel bannerを分離します。期待はsmoke前にv3表へ固定しました。

利用者承認はRS formatterの研究限定利用です。由来監査と製品出荷禁止は継続します。旧raw/CSV/v1/v2期待は変更していません。今回の一回試験から反復性・性能採否・原因確定・実機復帰は判断しません。

v3はAの7条件にF3 restart/EIO対照とF6 resetを加えた10条件です。RAM initramfsからの読取り、計装kernelによる`fio->level`追跡、C〜Eの追加注入は対象外です。F3の再入仮説はこのsmokeだけでは確定しません。

## 計測器と独立検査

- [v3期待表](../../board/cardputerzero/tools/bench/dm-verity-fec/expectations-v3.tsv)と[runner](../../board/cardputerzero/tools/bench/dm-verity-fec/run-v3.py)を追加。`--runs 1`は本当に1 boot、正式反復は`--runs 5`です。case/results先の既存directory・symlinkを拒否し、実行前に入力hashを照合します。
- 旧generatorを新しいseed先だけで実行し、F0からcaseを派生。F5は旧generator通り別にpackするため、F0とbyte同一とはしません。F5のdata破損は自身のclean byteを復元して位置を検査します。
- `location.json`に全変更byteのoffset、before/after、物理block、hash level、level内digest index、FEC論理block・column（round/byte lane）・symbolを保存。p5を読み戻してrootfs.imgと比較します。F4はimageへの注入ではなくroot hashの改ざんと記録します。
- [数学的な既知消失decoder](../../board/cardputerzero/tools/bench/dm-verity-fec/stage_a.py)はGF(256)/0x11d上のsyndrome計算と連立一次方程式による復元です。verityfmtのencoderやKarnの復号sourceは呼びません。全注入columnと全roundの先頭/末尾byteを検査します。**全column検査、未知error位置の同定、kernelと同じ復号過程の再現ではありません**。消失位置は注入差分から与えます。
- [SHA-256対照](../../board/cardputerzero/tools/bench/dm-verity-fec/check-codec.py)はveritysetupでcleanをverifyし、1 byte破損をFECなしで拒否、`--fec-device`付きで実際に復号してverifyします。crc32cはveritysetupが扱えず、上記の既知消失検査を使います。veritysetupのRSもKarn系なので、別系統の由来証明とは呼びません。
- 24 symbolの集中破損は8 rootsの既知消失容量を超える負の対照です。「常に8 errorsまで訂正可能」とは解釈しません。

## 終了の判定

readyとcorruptionの併記、generic panicだけ、timeout、host SIGTERMだけは成功にしません。panicはverity由来が必要です。EIOはverity corruptionとI/O errorが必要で、後段のgeneric mount panicをverity-panic成功へ読み替えません。

restart-requestはcorruption・restart marker・QEMU自然終了0のすべてが必要です。reset試験は同じmarkerに加え、restart markerの後に受け取ったQMP RESETと2回目の`Linux version`が必要です。起動時RESETだけでは合格しません。reset先は同じ破損imageであり、A/B選択ではありません。

restart系だけは`QEMU_WATCHDOG=1`でbcm2835のrestart handlerを有効にします。既存QEMU wrapperの既定はこのdriverをinitcall blacklistへ入れます。`--restart-watchdog off`はその失敗経路を再現する対照です。mode間でwatchdog条件も変わるため、restartとの比較をmode単独の因果証明とはしません。panicとEIO対照はともにwatchdog無効で比較しています。

観測後にhostが止めるcaseは、停止前のserialと終了状態で判定し、観測時のUTF-8換算byte数・停止理由・最終process statusを分けます。serial原文にはその後のsignal行も残します。F6の自然終了にはこの扱いを使いません。

## 固定条件と再現

standalone cloneをrootless Dockerへmountして生成・起動しました。既存T0のkernel 6.18.59とV0のDTB/入力SquashFSを再利用し、F0/F5のrootfsとformatterは新規生成です。build/cacheはwarmで、kernelの再buildはしていません。rawにはbinary hashと入力hashを残します。

QEMU 11.1.2、GCC 14.2.0-19、veritysetup 2.7.5。開発image IDは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。raspi3ap/512M、icount shift=0、4K、crc32c、固定salt、roots8（F5は0）、通常mount後のreadallです。

上記GCCはformatterのhost compilerです。再利用kernelのbannerはaarch64 GCC 14.3.0を示しており、今回のcompilerでkernelをbuildしたという意味ではありません。

以下はrootless Docker用です。`BUILD_OUTPUT`はhost toolsを含む既存build出力、`BASE`はV0/T0を持つ入力、`IMAGE`は上記開発imageを指定します。rootful Dockerでは実行者のUID/GIDを指定してください。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/dm-verity-fec/check-codec.py codec-control
docker run --rm --user 0:0 -v "$PWD:/work" \
  -v "$BUILD_OUTPUT:/work/output-integrity" -v "$BASE:/inputs:ro" -w /work "$IMAGE" \
  python3 board/cardputerzero/tools/bench/dm-verity-fec/run-v3.py prepare output-integrity /inputs cases-v3
docker/msd-dev python3 board/cardputerzero/tools/bench/dm-verity-fec/run-v3.py \
  run cases-v3 smoke-v3 --runs 1 --timeout 600
```

## 失敗試行と制限

初回の直接Docker実行はrootless環境にhost UIDを渡したため、出力directoryの作成でPermissionErrorとなりました。開発wrapperのrootless設定に合わせて解決しました。次の生成はrootfs-tree内のdangling symlinkを追跡してcopyに失敗。treeを配布caseから除外し、symlinkを保存する方式に修正して新directoryで生成しました。

その後の初回smokeはcloneへの最終sourceの転送漏れを見つけて中断しました。部分serialを保持し、最終版とhash一致する写しで別directoryへ再実行しています。中断試行を成功数・時間見積りへ混ぜません。

watchdog無効のrestart対照では、`reboot: Restarting system`の後に`Reboot failed -- System halted`となりました。600秒timeout後にhostが停止したものをrestart成功へ数えません。同じkernel・破損imageでdriverを有効にした対照では、driver登録のserial行と自然終了、さらにreset許可時のQMP RESET・2回目bannerを取得しました。wrapperのdriver無効化がこの環境のrestartを止めることを対照で確かめました。実機の再起動・復旧を検証した結果ではありません。

非restart条件は修正前snapshotで、restart 3条件はdriver設定と記録だけを変えた最終runnerでsmokeしました。両sourceと差分、各試行のharness hashを保存します。実行中の写しは変更せず、restart対照は別standalone cloneで行いました。

## smokeの結果

各条件は1 bootだけです。構築・判定経路の確認が目的であり、5回の正式反復ではありません。期待との相違は事後に期待を変えずに残しました。

[全13試行のCSV](2026-11-15-dm-verity-fec-stage-a-smoke.csv)には、watchdog無効の失敗対照3件も含めています。以下は最終条件10件の表で、期待一致9・不一致1です。全13件では一致9・不一致4となり、別に初回の中断試行があります。

| 条件 | 期待 | 観測・合否 | wall秒 |
|---|---|---|---:|
| F0 | ready | ready・合格 | 249.54 |
| F1 | ready | ready・合格 | 246.21 |
| F2 | verity-panic | verity panic・合格 | 216.30 |
| F3 panic | verity-panic | verity panic・合格 | 216.04 |
| F4 | verity-panic | verity panic・合格 | 225.75 |
| F5 | verity-panic | verity panic・合格 | 229.50 |
| F6 no-reboot、driver有効 | restart-request | host停止なし・自然終了0・合格 | 189.30 |
| F3 restart、driver有効 | restart-request | host停止なし・自然終了0・合格 | 195.61 |
| F3 EIO、driver無効 | verity-eio | **期待不一致**。FECで1 error訂正後にready | 186.62 |
| F6 reset、driver有効 | restart-reset | guest-resetのQMP RESETと2回目banner・合格 | 184.87 |

F3は物理block 5833のoffset 23,891,985、top level 1のdigest index 4、FEC論理block 5832・column [0,17]・symbol 243でした。0x5eから0xa1への1 byte反転で、既知消失decoderはclean codewordへ復元しました。

panic版の実stackには`verity_fec_decode → fec_decode_rsb → verity_hash_for_block → verity_verify_level → verity_handle_err`があり、FEC内のhash検査からpanicへ入る経路を実際に通っています。EIO版は同じ破損で`FEC 0: corrected 1 errors`の後にroot mount・readall・readyへ到達しました。容量超過だけでF3を説明する仮説に反する観測であり、panic policyが回復を先に止める説明を支持します。ただし各1回で、`fio->level` guardへの到達・正確な再入回数は未計装です。

readallはinittabの挿入数1とddの22+1 records in/outを確認しました。一方、serialには`verity-readall-complete`の文字列はなく、独立した完了markerによる確認とはしません。またready到達caseに`Key was rejected by service`などmodule署名拒否があります。再利用したkernel/rootfsの全module loadや正常製品bootの合格は主張せず、正式反復前に鍵・moduleの組合せを確認する残件とします。

F3 EIOの「corruptionとreadyが併記されたら成功にしない」判定は意図どおり働きました。この期待不一致はharnessの例外や試験の欠損ではありません。新たな成功分類・期待への変更は別の判断とし、今回のv3表を実測に合わせて変えません。

## 次回の時間とdisk

wallはimage複製後から観測・cleanupまでで、入力hash検査・準備を含みません。後半のrestart対照は旧対照と並列に走ったため、純粋な性能比較には使いません。

smokeの単発wallを単純に5倍すると、Aの7条件・35 bootは2.18時間、v3全10条件・50 bootは2.97時間です。準備・hash検査・変動を足し、それぞれ3〜4時間、4〜5時間を仮予算にします。各bootの上限600秒をすべて使う場合は、35 bootで5.83時間、50 bootで8.33時間に準備分を加えます。runnerは期待不一致でも反復を続け、入力hashの不一致では止まります。事前登録どおり、clean条件が失敗したら後段を始めません。timeoutや再実行があるため、この時間だけで完了を保証しません。全48条件の旧見積りをこのsmokeだけで短縮もしません。

生成済みseedと10 caseは実割当8.6 GiB、実行中imageは約0.74 GiBを使いました。逐次実行なら入力・log・一時imageに12〜16 GiBを予約する見積りです。失敗生成物・以前の証拠を消さず、開始前100 GiB空きの条件は維持します。

正式反復前にはF3 EIOの期待不一致、F5の別pack条件、mode対照のwatchdog条件を判断する必要があります。今回、正式なstage Aは開始していません。

## 証拠と検査

[raw証拠archive](2026-11-15-dm-verity-fec-stage-a-smoke/evidence.tar.gz)にserial/QMP/functional JSON、全caseのlocation/input hash、生成・host検査log、入力hash、両runner snapshotと差分を保存しました。内部186 memberをhash照合済みです。archiveは104,143 byte、SHA-256は`303d2f03ccdab0fdf8070e1e081324a09c714dcae25c68f265d2e1e6547ea0f9`です。

rootless UIDの初回PermissionErrorはtool出力だけで、独立raw logは未保存です。copy失敗のtracebackは保存しましたが、失敗時sourceの完全snapshotはありません。生成image本体は大きいためarchiveに含めず、hash・生成手順と永続保管した生成物で追跡します。

host回帰は入力6件・旧judge3件・新judge/locator/decoder4件、計13件を実行しました。veritysetup対照の終了値はclean=0、破損/FECなし=2、破損/FECあり=0でした。standalone Dockerのtracked ShellCheckは終了値0・出力なしです。これらの合格をsmokeの期待不一致や実機未確認と混同しません。

正式なstage A、full 48条件、追加kernel計装、実機LCD/firmware tryboot/SD電気的I/O/電断/A/B復旧は未実施です。03914の台帳同期保留も継続します。
