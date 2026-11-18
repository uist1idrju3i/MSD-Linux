# fs-compare v2の監視と判定

旧版の正式実験に使ったscriptを残し、driver・matrix・guest・build入口・設定定義をこのdirectoryへ分離しました。workloadのC sourceだけは一つ上の旧版と共有し、入力hashへ含めます。dm-verity/FECと共通QEMU起動検査器は変更しません。

## 現在の範囲

step 1の監視・判定に加え、step 2の経路定義、環境検査、全経路smoke、自動除外、新しいplan生成を実装しています。容量見積りとcleanup前の自動archiveはまだありません。**正式測定にはまだ使いません。** QEMU・実機での試行は行っておらず、この変更の実験記録はありません。

- build: `fs-compare-build.sh`。既定出力は`output-fscmp-v2`です。旧版のBuildroot fragmentを使うtreeは拒否します。
- 単発: `QEMU_LOG_DIR=/永続的な絶対path fs-compare.sh E1 smoke run-id`。既存のrun directoryは上書きしません。
- matrix: `fs-compare-matrix.sh --runs-dir /永続的な絶対path plan.tsv`。旧版と混ぜず、v2で作ったmatrix directoryだけ再開します。

これらの入口は本書と同じdirectoryにあります。`run-qemu.sh`は既存のものを使い、exec後のQEMUをPython supervisorが直接waitします。`FS_COMPARE_V2_DRIVER`はhost試験で偽driverを渡す入口で、環境検査とsmokeを迂回します。通常は指定しません。`FSCMP_PREFLIGHT_WORKER`、`FSCMP_SMOKE`、`FSCMP_EXPECT_KERNEL`は内部呼出し専用です。利用者が設定してはいけません。

## 環境検査とsmoke

`preflight.py`が単発とmatrixの通常入口から呼ばれます。test imageの展開・加工より前にhost toolの実体・version・hash、kernel・DTB・rootfs・SD image・workload・replay-logのhashを確認します。Buildrootの`.config`と、build配下のLinux・BusyBoxの生成済み`.config`を保存します。fragmentだけでは代用せず、必要なkernel機能は組込みの`=y`を要求します。欠損、version取得失敗、設定不足、異なるkernel/DTBへの環境変数による差替えは停止します。

承認済みの環境へ固定する場合は、単発・matrixとも`--expect-environment FILE`で保存済み`environment.json`を渡します。tool versionを含む現在の環境が一致しなければ、smokeやimage作成の前に停止します。指定しない初回は環境を収集し、そのhashに対してsmokeを実行します。

guestの情報は起動しないと確認できません。診断用imageを作った後、各smokeのvolume作成前に`fs-compare-probe`を実行します。実kernel releaseを生成物のreleaseと照合し、filesystem、dm target、mkfs/fsck・暗号化toolのversionを記録します。module未導入などで実際に機能を利用できなければ失敗します。本測定用imageは、この検査を含む全smokeが終わるまで作りません。

`paths.tsv`は引数検査・新plan生成・smoke生成に共通の経路定義です。全20 baseについて全経路を通します。T1の各replay方式・negative方式・sampleの自動選択と明示選択、T2/T3のcutとverify、T4のcontrol、T5/T6/T7を含みます。明示sampleはそのrunで生成した最初の有効なentryを選びます。全variantではTSVに指定された標準のT3・T4-sync・T5と、対象ならT6に加えてmount-only smokeを通します。それ以外の組合せが入力planにあれば、その組合せも追加します。

smokeも同じguest dispatchと最終判定器を使い、反復は1回です。現段階ではworkloadを短縮せず、T1の全point再生やT7の4 GiB処理も残しています。このため全経路の確認には多くの時間と領域が必要です。mountできただけではcoverage済みにせず、未実行・途中失敗・verify未完了なら本測定を開始しません。smokeの結果は測定用matrix-summaryに混ぜません。

単発の記録はruns rootの`.preflight/`、matrixは`<matrix-id>.preflight/`へ保存します。

- `environment.json`: host環境と入力hash。
- `attempt-*/`: 各probeのraw log・process証拠・判定。再試行でも消しません。
- `smoke-coverage.json`: config・経路・phaseごとの成否、終了値、証拠hash、除外の理由。
- `effective-plan.tsv`: 非対応の構成を除いたplan。
- `excluded-options.json`: 正確な診断行とprobeへの参照。

再利用するのは、harness・launcher・設定・tool・入力image・planのhashと起動環境が一致し、必要な経路とphaseが全てそろい、保存した証拠のhashも一致する場合だけです。入力planの反復番号や単発のpoint指定が変わった場合も再確認します。

自動除外は過去に記録したP012・P085・P101・P133の正確な非対応診断だけに限定します。未知のerror、timeout、ENOSPC、EIO、異常なprocess証拠が併存すれば除外せず停止します。T1/T6の期待したnegative診断はerror一覧へ残し、除外の根拠にしません。全件除外は`nothing to run`として非zeroで終了し、成功にしません。

## planと反復

新しい`fs-compare-matrix.sh --generate-plan`は標準のbase試験とvariant試験を既定3回ずつ生成します。`--repetitions N`で変更できます。`preflight.py generate --profile phase1|phase2 --repetitions N`でも部分planを生成できます。測定対象の試験も`paths.tsv`に定義し、診断用smokeやnegative controlを新planへ自動的に混ぜません。必要な場合は3列TSVで指定します。

既存の`--generate-phase1`と`--generate-phase2`は以前の反復profileを明示的に選ぶ入口として残します。既存の3列TSVの第3列は反復番号です。入力を再展開・書換えせず、retryは同じ反復番号の別attemptとして扱います。

## 成功条件

完了markerだけでは成功にしません。QMPのcapabilities交渉とquitが成功し、QEMUを回収して終了値0を確認し、全logに予期しないerrorがなく、driverも終了0の時だけ成功です。TERM/KILL fallback、SIGKILL、非zero、status不明、証拠欠損は失敗です。QMP socketは短い一時pathに置き、停止要求・回収結果はrun directoryへ残します。

T2/T3の最初のphaseだけは例外です。開始markerを確認し、cut意図を保存した後のSIGKILLを予定cutとして扱います。verify phaseのrecovery markerとQMP正常終了は別に必要です。予定外signalやrecovery marker後の異常終了は失敗です。

`summary.pending.csv`は中間値です。回収後に全logを再走査し、`summary.csv`をatomic置換してから、最後に`result.json`をatomic置換します。後者が最終判定の確定印です。matrixはschema・run識別・summary hash・phase結果も検査し、子processが非zeroならsummaryがokでも失敗です。子の終了値も保存し、再開で成功に変わることを防ぎます。これはhostの突然の電源断まで保証するものではありません。

## errorの保存

`host.log`にはdriverの準備・image加工のstdout/stderr、`qemu-run.log`と`qemu-verify.log`には各phaseのQEMU/guest出力を残します。`qemu.log`は回収後の結合logです。`phase-*.json`にはQMP、fallback、終了値、回収の有無、log hashを保存します。

`errors.jsonl`と`errors.txt`にはfile・行番号・phase・分類・原文・expectedの区別を保存します。process statusも記録します。guestのerror、kernel panic/Oops、QEMUのfatal、未知のerrorは成功markerより後でも失敗です。T1 replayとT6 corruptionのguestが明示した区間だけ、列挙したfilesystem診断・測定markerをexpectedとして残します。kernel panic、guestの失敗、SDのI/O errorは除外しません。区間が閉じない時も失敗です。未知の診断は保守的に失敗するため、後続のsmokeで分類の妥当性を確認する必要があります。

## host試験

repo rootで`python3 tests/fs-compare-v2/run.py`を実行します。偽process・QMP peer・tool・小さいlogを使い、QEMUやnetworkは使いません。registry、plan、生成済みconfig、host/guest probe、限定的な除外、coverageとhashによる再利用も検査します。`run-host-tests.py`にも登録しています。実QEMUとの結合、全workloadの経路、再現性、性能、LCD表示は未確認です。
