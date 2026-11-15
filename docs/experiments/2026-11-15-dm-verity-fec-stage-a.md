# B3 stage Aの35 boot結果

[実験索引](README.md) / [事前登録とamendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [計測器smoke](2026-11-15-dm-verity-fec-stage-a-smoke.md)

## 結論と範囲

2026-11-15 UTCにF0〜F6を各5回、計35 boot実行しました。**最終v3判定は35/35で期待一致**です。入力不一致・clean失敗・timeout・中断はなく、期待を実測に合わせて変えていません。

これはamendment付きのstage Aのmarker反復です。readall独立完了markerとloginは取得しておらず、原計画の通常起動確認をすべて満たしたという意味ではありません。ready到達caseのmodule署名拒否も残ります。製品boot、原因の完全解明、実機復帰、stage B以降の合格とは区別します。

F3のpanicは5/5でFEC内のhash検証経路に現れ、F1は5/5で1 error訂正後にreadyでした。F6はwatchdog driver有効・`-no-reboot`の設定で5/5自然終了0となり、host停止を成功の根拠にしていません。

## 実行前承認と固定条件

基点はfresh main `e575f033fbfab6cfaf4402a0f8b8b9fb2d53fc05`。実行前amendmentは[commit 7be60e5](https://github.com/uist1idrju3i/MSD-Linux/commit/7be60e5411c07489e74e6ad411d1d19cea619fcd)として先にcommit・pushしました。実行cloneのHEADもこのSHAです。

利用者は2026-11-15 22:36 JSTの承認とその後の訂正で、事前期待の維持、restart系のwatchdog有効化、F5の当初pack方式維持を決めました。chat提案の「EIO期待panic」は誤記であり、AのF3=`verity-panic`、BのEIO対照=`verity-eio`です。訂正成功は仮説の反証として保存する意図をamendmentへ記録しました。今回はEIO対照を実行していません。

| 項目 | 条件 |
|---|---|
| 実行器 | 最終v3の`run-v3.py`。SHA-256 `cb2e21aec3d5234f6b8bb8eccc384a9f85749addc11527a7c00adf8862de0084` |
| 場所 | standalone cloneのDocker内。linked worktree内の実行ではない |
| 開発image | `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。稼働containerのimage IDも照合 |
| host | Linux 7.0.0-43-generic。開始時空き167 GiB、RAM available 27 GiB |
| QEMU | 11.1.2、raspi3ap、512M、icount shift=0、`-no-reboot` |
| QEMU binary | SHA-256 `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410` |
| kernel | 再利用T0の6.18.59-v8。SHA-256 `45d52f6e148cebaee66ecbc9735c6260ec23ca8c9ad0b00032cf04d20f1420e8`。bannerのaarch64 GCCは14.3.0 |
| build/cache | 再build・reconfigureなし。既存のwarm入力を再利用。ccacheは今回使用せず、cold性能比較ではない |
| verity/FEC | 4K、crc32c、固定salt、roots8（F5は0）。SHA-256対照と既知消失復号は同じ入力hashのsmoke結果を参照し、今回は再実行せず |
| watchdog | F6だけ有効、F0〜F5は既存wrapperのinitcall blacklistで無効。これは事前登録からの明示した逸脱 |
| 回数・上限 | 各5回、boot0〜4。`--runs 5 --timeout 600 --restart-watchdog on`、逐次 |

host cc 14.2.0-19とveritysetup 2.7.5の実versionもmetadataへ保存しましたが、今回はformatterやkernelをcompileしていません。

## 入力照合と停止規則

開始前に7 caseすべての`inputs.json`をsmoke archive内の保存値と比較し、各manifestが指す全fileのSHA-256を照合しました。入力はread-only mountです。実行器も各case開始時にhashを再照合します。生成時のp5読戻し・注入位置・独立復号の記録は、今回同一hashと確認した入力に対応します。

まずF0だけ5回実行し、5/5のv3 ready判定とserial hashを確認してからF1〜F6を開始しました。clean失敗なら後続を開始せず、入力不一致なら実行器の例外で停止する手順です。実行中のscriptは編集していません。停止規則のclean合否には指定された最終v3のready判定を適用しており、loginの独立確認とはしません。

| case | 注入・期待 | 結果 |
|---|---|---|
| F0 | clean、ready | 5/5 ready |
| F1 | data 1 byte、ready | 5/5 `FEC 49152: corrected 1 errors`とready |
| F2 | 同じFEC columnのdata 24 byte/24 block、verity-panic | 5/5 verity panic |
| F3 | top hash 1 byte、verity-panic | 5/5 metadata block 5833由来のverity panic |
| F4 | root hash引数の改ざん、verity-panic | 5/5 verity panic。imageへのbyte注入ではない |
| F5 | FECなし、当初の別pack方式とdata 1 byte、verity-panic | 5/5 verity panic |
| F6 | F2と同一image、restart-request | 5/5 corruption→restart marker→自然終了0 |

F2/F6のrootfsとSD imageはそれぞれ同一hashです。ただしmodeとwatchdog条件が違うため、mode単独の因果比較ではありません。今回のF2は実差分24 byteを確認しており、旧記載9 blockを実測後に修正したものではありません。9/24 block対照は段階Eに残します。F5のpack条件を揃える追加対照は承認どおりstage Bへ送ります。

## 生のwall値

単位は秒。丸め前の35値・判定・停止理由は[CSV](2026-11-15-dm-verity-fec-stage-a.csv)にあります。boot0も除外せず別columnで示します。

| case | boot0 | boot1 | boot2 | boot3 | boot4 |
|---|---:|---:|---:|---:|---:|
| F0-A3 | 238.218 | 246.009 | 236.220 | 239.268 | 245.227 |
| F1-A3 | 249.502 | 240.726 | 247.903 | 242.098 | 232.616 |
| F2-A3 | 217.353 | 218.116 | 218.567 | 224.712 | 219.996 |
| F3-A3 | 229.494 | 234.384 | 234.633 | 215.456 | 218.514 |
| F4-A3 | 216.654 | 220.614 | 219.794 | 212.595 | 231.097 |
| F5-A3 | 221.508 | 225.801 | 227.476 | 230.784 | 220.894 |
| F6-A3 | 231.829 | 228.583 | 229.841 | 224.015 | 238.971 |

| case | 最小 | 中央値（全5回） | 最大 | 中央値（boot1〜4） |
|---|---:|---:|---:|---:|
| F0-A3 | 236.220 | 239.268 | 246.009 | 242.247 |
| F1-A3 | 232.616 | 242.098 | 249.502 | 241.412 |
| F2-A3 | 217.353 | 218.567 | 224.712 | 219.281 |
| F3-A3 | 215.456 | 229.494 | 234.633 | 226.449 |
| F4-A3 | 212.595 | 219.794 | 231.097 | 220.204 |
| F5-A3 | 220.894 | 225.801 | 230.784 | 226.639 |
| F6-A3 | 224.015 | 229.841 | 238.971 | 229.212 |

wallはimage複製後から観測・cleanupまでです。ready/panicの30回は観測後にhostが終了させ、F6の5回だけ自然終了です。boottimeのvalidや正常製品bootの時間とは区別します。単発smokeとの差を性能退行・同等性の証明には使いません。

## F3/F6の仮説判定

F3の注入はoffset 23,891,985、物理block 5833、byte 17、tree level 1、digest index 4です。FEC論理block 5832、column [0,17]、symbol 243で、0x5e→0xa1の1 byte反転でした。

| 仮説・観測 | 今回の証拠・反証を試みた点 | 評価・確度 |
|---|---|---|
| F3の注入位置や入力が違う | 保存manifestと全file hashを照合、全5回で同じmetadata block 5833を報告 | 今回の位置不一致説は支持しない。高 |
| FEC全体が無効・単純な容量超過 | 同じ設定のF1は5/5実訂正。F3の同一hash入力はsmokeの既知消失decoderでcleanへ復元 | FEC全面無効や容量だけの説明は弱い。kernelの未知error同定までは保証せず、中 |
| FEC内のhash検査がpanicへ到達 | 5/5のstackに`verity_fec_decode → fec_decode_rsb → verity_hash_for_block → verity_verify_level → verity_handle_err` | 到達経路は高。panic policyが回復を先に止める因果説明は中 |
| 再入guardが直接の原因 | `fio->level`のtraceなし。smokeのEIO単発は訂正readyだが、今回のAでは再試験していない | guardの直接因果は未確認 |
| initのreadallがF3 panicを起こす | F3の全5回はroot mount完了・`Run /sbin/init`より前にpanic | 今回のF3はinit readall起因ではない。高。RAM initramfs経路は未試験 |
| F6のhost SIGTERMをrestart成功と誤認 | 5/5でrestart markerと自然終了0、停止前status=0、host停止=false。driver登録行あり | このQEMU設定でのrestart要求・自然終了は高。driver内部全関数は未trace |
| F6がresetして別slotへ復旧 | 今回は`-no-reboot`でbannerは1個、QMP RESETなし | 未検証。smokeのreset単発とも別slot復旧とは扱わない |

panic経路の到達、反復性、policy/guardの因果を分けました。旧B3の5/5を今回と同一binaryの反復として合算しません。

## 警告・欠損と未確認

- 正式試行の失敗・欠損・中断は0件です。以前のsmokeの失敗対照3件とEIO期待不一致は別記録のまま保持し、35件へ混ぜません。待機toolの接続が切れた間もcontainerは継続し、実験の再起動・やり直しはしていません。
- readyの10回すべてにddの22+1 records in/outがありました。ただし`verity-readall-complete`もloginもserialで観測していません。v3はready到達で観測を終えます。原計画の独立完了marker・login確認は残件です。
- readyの10回すべてにmodule署名拒否（`Key was rejected by service`5行/bootなど）があります。再利用kernel/rootfsの全module loadや正常製品bootに合格したとはしません。鍵・moduleの組合せ確認を残します。
- kernel再入guardの計装、RAM initramfs、EIO再反復、下位hash/superblock/parity/roots/hash境界は未実施。後続段階の自動開始・採用判断はしません。
- 実機LCD・firmware tryboot・SD電気的I/O・電断・A/B復旧・§10適合は未確認。RSの由来監査と製品組込み/出荷禁止、03914の台帳同期保留を維持します。

## 時間・diskと36時間上限

metadata開始は2026-11-15 **13:56:11 UTC**、最終結果保存は**16:10:49 UTC**。経過wallは**8,078.074秒（2時間14分38秒）**、35 bootのwall合計は8,029.467秒でした。差48.607秒には入力照合・clean gate・起動間の処理が含まれます。

準備済み入力を再利用したAの実測であり、36時間上限の約6.23%です。上限には近づかず、延長判断も不要でした。48条件全体の完了時間を保証する値ではありません。終了後空きは166 GiBで、元imageと証拠は削除していません。

## 証拠と再実行

[evidence.tar.gz](2026-11-15-dm-verity-fec-stage-a/evidence.tar.gz)は120,685 byte、SHA-256は`df278b3d4d93027382c6bfbb83b0425a406000c6cefc7e9eab3356f9735036ec`です。内部181 memberをhash照合しました。全35回のserial/QMP/functional JSON、CSV、両groupのharness/settings、全caseの位置・入力hash・cmdline、実行source、環境・clean gate・終了metadata・console logを含みます。集計は重複・不足・非有限値を拒否し、全serial hashとCSVを照合しました。

入力image本体は大きいためGitに含めず、既存の永続保管入力とhashで管理します。公開archiveだけから同一binaryを取得できるとはしません。入力を新規生成した場合はhashを照合し、一致しないものを今回の再生と呼ばないでください。

standalone cloneでamendment SHAをcheckoutし、`CASES`に保存hashと一致する7 case、`BUILD_OUTPUT`に既存出力、`IMAGE`に固定開発imageを指定します。以下の第2groupは第1groupの全5回成功を確認した場合だけ実行します。両出力先が既存なら使い回しません。

```sh
docker run --rm --user 0:0 -v "$PWD:/work" -v "$CASES:/inputs:ro" \
  -v "$BUILD_OUTPUT:/work/output-integrity" -w /work "$IMAGE" \
  python3 board/cardputerzero/tools/bench/dm-verity-fec/run-v3.py run /inputs stage-a-clean \
  --runs 5 --timeout 600 --restart-watchdog on --case F0-A3
# functional.json全5件の期待一致・serial hashを確認後だけ続行
docker run --rm --user 0:0 -v "$PWD:/work" -v "$CASES:/inputs:ro" \
  -v "$BUILD_OUTPUT:/work/output-integrity" -w /work "$IMAGE" \
  python3 board/cardputerzero/tools/bench/dm-verity-fec/run-v3.py run /inputs stage-a-injected \
  --runs 5 --timeout 600 --restart-watchdog on \
  --case F1-A3 --case F2-A3 --case F3-A3 --case F4-A3 --case F5-A3 --case F6-A3
```

rootless Dockerでの実行例です。計測器sourceはsmoke時と同一で、今回scriptは変更していません。host fixture・ShellCheckの以前の合格と、今回の35 bootの判定を分けて参照してください。
