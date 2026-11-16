# B3 stage Bのclean smoke停止記録

[実験索引](README.md) / [事前登録・実行前amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [stage A](2026-11-15-dm-verity-fec-stage-a.md)

## 状態と結論

2026-11-15 UTC。**Bの最初のclean smokeがreadall完了marker欠落で不合格となり、停止しました。** 後続9条件のsmoke、Bの正式5反復、C〜Fは開始していません。判定・期待を緩めず、修正・再試行も行っていません。

ddの22+1 records in/outとready/loginは観測しましたが、必要な`verity-readall-complete`がありません。これは600秒timeoutではなく、236.06956884099054秒で`unexpected-terminal`となった試行です。上限の600秒と実測wallを混同しません。

最有力原因は、BusyBox initがinittabの複合コマンドに`exec`を付け、ddでshellを置き換えるため末尾のechoが実行されないことです。実入力と実BusyBox binaryの逆assemblyで、その経路を照合しました。execveの動的traceは取っていません。

## 実行前の固定と環境

branchはstage A結果`0dcdf3cdd478189f43c286de88290f51c64cdde9`に積みました。

| 項目 | 条件 |
|---|---|
| 実行前amendment | [5925006](https://github.com/uist1idrju3i/MSD-Linux/commit/5925006)。smoke前にcommit・push |
| 計測器 | [084fc44](https://github.com/uist1idrju3i/MSD-Linux/commit/084fc44ed08f8e0d394d5484ed3376b3121e93b2)。RAM読取り、厳密な完了判定、FEC再入trace |
| library配置の補足 | [6788346](https://github.com/uist1idrju3i/MSD-Linux/commit/678834692b465db20a9b020169d0b80b689e75cf)。このcommitのstandalone cloneで生成・実行 |
| 場所 | standalone Docker clone。linked worktree内ではbuild・QEMUを実行せず |
| image | `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`で固定 |
| QEMU | 11.1.2、SHA-256 `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410` |
| machine | raspi3ap、512M、icount shift=0、no-reboot。cleanはwatchdog無効 |
| kernel | 6.18.59-v8-b3trace。SHA-256 `bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69` |
| kernel source | [Raspberry Pi b3495ea](https://github.com/raspberrypi/linux/commit/b3495ea401d709af0701a85babcba5e3d788a602)に対応する既存treeの写し。FECの観測点とIDだけを追加 |
| compiler | 実際のcross ccはaarch64-linux-gcc.br_real、14.3.0（bannerのBuildrootは2021.11-18033-g83947c7bb6） |
| cache/build | 既存warm build treeをコピーして直接make。再configureなし、ccache不使用。多数のobjectを再compileしており、cold/warm性能比較ではない |
| rootfs | AのF0と同じSquashFS bytes・crc32c・roots8・salt・panic。新kernelとログ観測条件だけを変更 |
| 観測 | `ignore_loglevel loglevel=8`。readall完了→ready→loginを要求 |
| 回数・停止 | 各1 smokeを予定。clean失敗なら後続を開始しない。正式は各5回を予定したが0回 |

研究専用の`trace-kernel.py`はFEC enter/guard/phase、RS column・neras・戻り値、hash参照、bio ID、modeを記録します。kernel patch・変更前後のsource hash・config・build logを保存しました。cleanではFEC呼出しを誘発せず、guard hitは0でした。**これはguard仮説の反証ではなく、破損caseへ進んでいないためです。**

## 入力と予定条件

生成前にAのF0のmanifest、formatter binary/sourceを照合しました。全10 caseについてSD p5読戻し、注入差分、既知消失decoderによる検査を行い、生成後の全manifestを独立に再照合しました。実行器も開始時に照合し、caseはread-only mountです。入力不一致はありません。

F5の同一pack対照はAの承認でBへ送った2条件です。実行前amendmentで追加を記録し、元の8条件と合わせて10条件/50正式bootとしました。roots0の再生成でF0とdata bytes・root hashが同じことをhost側で照合していますが、QEMUでは未確認です。

| 条件 | 固定した期待 | 今回 |
|---|---|---|
| B-clean-normal | readall完了・ready・login | **1回不合格** |
| B-clean-ram | 対象1 block→全dataの読取り成功 | 未実行 |
| B-F3-panic-normal/ram | verity-panic | 両方未実行 |
| B-F3-restart-normal/ram | restart-request・自然終了0 | 両方未実行 |
| B-F3-eio-normal/ram | 読取り-EIO。訂正成功は反証 | 両方未実行 |
| B-nofec-clean | 同一packの通常起動成功 | 未実行 |
| B-nofec-data | 同一pack・roots0・data1 byteでverity-panic | 未実行 |

RAM用initramfsは生成しましたが一度もbootしていません。Cの下位hash/header/parity/境界、Dのhash/roots matrixと容量境界、Eの9/24 block集中・分散、Fのreset継続の今回の拡張・正式反復も未実施です。

## 生の結果と停止

[CSV](2026-11-15-dm-verity-fec-stage-b-smoke.csv)は失敗1行を残しています。単発失敗なので中央値を性能比較に使いません。

| case/repeat | wall秒 | readall marker | ready/login | 判定・停止 |
|---|---:|---|---|---|
| B-clean-normal/0 | 236.06956884099054 | なし | 両方あり | 不合格・unexpected-terminal |

判定時点のQEMU statusは未終了、観測後host停止=trueです。最終process status 0だけを自然終了成功と数えていません。

```text
22+1 records in
22+1 records out
...
[    2.697575] MSD/Linux ready
...
msd login:
```

kernelのversion suffixに対応するmodule directoryがrootfsにない警告も出ました。Aの署名拒否と同じ警告だとはせず、今回のmodule path不一致として保存しています。通常製品boot・全module loadの検証には使えません。

停止後の差分確認で、cmdline再構築時にAの`initcall_debug`を継承していなかったことも見つかりました。これは実行前amendmentに列挙していないログ条件の逸脱です。事後の追記を事前承認とは扱わず、今回を厳密に事前登録どおりの比較とはしません。次の実行前amendmentで復元を明示する必要があります。

## marker欠落の切り分け

起動したrootfs imageから抽出したinittabには、次の行がありました。Aの既知のmarker欠落を直した入力ではありません。

```text
::sysinit:/bin/dd if=/dev/dm-0 of=/dev/null bs=1048576 && /bin/echo verity-readall-complete > /dev/kmsg
```

1. 実imageから抽出したBusyBoxのSHA-256は`bca3db4b4267666e0f5fd78b89326bbc34b8e8cdb779a62f3ffb49d083b14637`で、分析対象binaryと一致しました。`/sbin/init`と`/bin/sh`はBusyBoxへのlinkです。
2. 同versionのcached sourceでは`init/init.c:1182`のSYSINIT dispatch、`:603`のrun、`:551`のinit_execを経て、`:443-451`で特殊文字を含むcommandを`/bin/sh -c "exec ..."`へ変換します。
3. cached buildのBusyBox binaryは入力とhashが違うため、同じsource buildだとは仮定しませんでした。**実binary自体**の0x97294はstrpbrk、0x972b4はformat `exec %s`（0xb9450）を使うsprintf、0x972d8以降は`/bin/sh`・`-c`・生成文字列のargv設定、0x97300はexecvpです。判別文字列0xb9439には`=`と`&`が含まれます。逆assemblyとstring値を証拠へ保存しました。
4. その結果は`exec /bin/dd ... && /bin/echo ...`です。ddのexecが成功するとshellは置き換わり、echoへ戻りません。hostのPOSIX shellでexec付き/なしの対照を実行し、前者だけ末尾のprintfが実行されないことを確認しました。ARM ashのexecve動的traceは未取得です。

反証も試みました。実imageの行に既に明示的なshell wrapperがある可能性を抽出で調べましたが、上記のとおりありません。ログlevelだけの問題については、serialに`printk: debug: ignoring loglevel setting.`があり、ignore_loglevelが実際に有効でした。観測終了が早すぎるという説明も、readallより後のready/loginまで採取した事実とは合いません。

このためexecによるecho省略を強く支持します。ただし、ddの22+1 recordsだけを独立完了markerへ読み替えて合格させず、F3やF6の追加仮説判定には進んでいません。

## 予算の再見積りと再開待ち

amendmentで固定した保守的時計は2026-11-15 12:17:52 UTC開始、deadlineは2026-11-17 00:17:52 UTCです。記録時点の経過は約5時間で、Aの2時間14分38秒と準備・CI待ちも含みます。開始時空き166 GiB、生成後161 GiBです。

新入力でsmokeをやり直すと仮定した残数は、正式215 bootとsmoke43 bootです。240秒/bootの仮置きで17.2時間、準備4時間を加えると累積約26時間の見込みです。36時間には現時点で近づいていませんが、RAM経路などは未測定で、この見積りは保証ではありません。全件600秒timeoutを消化すると超過するため、その実行は認めていません。再開時に時計と資源を再確認します。

**提案する次の一手は、研究専用readall scriptを明示的なshell経由で実行する入力へ修正し、initcall_debugの復元も含む日付付きamendment後にBのclean smokeから再開することです。** rootfsを再packするためAとは別hashになります。B内の3 modeは同じ新しいbytesで比較し、期待は変えません。現在は承認待ちで、helper修正・再pack・再試行をしていません。

## 証拠と検査

[evidence.tar.gz](2026-11-15-dm-verity-fec-stage-b-smoke/evidence.tar.gz)は249,990 byte、SHA-256は`1cdc71246614298fe3cc83b46d6715b5cd0fa98f031cf62cb6ab623baf3d8359`です。69 fileをhash照合し、別にMANIFEST.jsonを含みます。失敗serial/QMP/判定JSON、全10入力のhash・位置・独立検査・設定、実行source、kernel patch/config/build log、host検査、実inittab、BusyBox source/license・実binaryの逆assembly・POSIX対照を保存しました。大きなimage/initramfs/kernel本体は永続保管し、公開archiveにはhashを収録しています。

host fixtureと既存format検査、standalone Dockerのtracked ShellCheckは実行前に終了値0でした。新規fixtureは正常・空・不正・矛盾・順序・上書き拒否・hash不一致・CPIO内library配置を検査します。研究用kernelのmakeも終了値0です。最終文書ではlinks/JIS/doc-sizeとyomiyasuを確認します。

再現入口は[followup.py](../../board/cardputerzero/tools/bench/dm-verity-fec/followup.py)の`prepare-b`と`run`です。生成済みcaseをread-onlyの`/cases`へ、standalone cloneを`/work`へmountし、固定image内で以下を実行しました。実行source・引数は証拠にもあります。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py +  run /cases output-b3-smoke-b --runs 1 --timeout 600
```

旧raw/CSV/期待は未変更です。RSの研究限定・製品出荷禁止、03914台帳同期保留を維持します。LCD・firmware tryboot・実機・電断・A/B復旧は未確認です。
