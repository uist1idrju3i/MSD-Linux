# fs-compare v2の監視と判定

旧版の正式実験に使ったscriptを残し、driver・matrix・guest・build入口・設定定義をこのdirectoryへ分離しました。workloadのC sourceもv2へ分離し、通常profileを維持したままsmoke専用profileを追加しました。dm-verity/FECと共通QEMU起動検査器は変更しません。

## 現在の範囲

step 1の監視・判定、step 2の全経路smoke、step 3の容量検査とarchiveに加え、承認済みのstep 4Aとしてsmokeの負荷と画像保存を軽量化しました。**正式測定にはまだ使いません。** build・QEMUの実施状況は[第4段の記録](../../../../../docs/experiments/2026-11-19-s04-fs-compare-v2-stage4.md)へ追記します。実機は未確認です。

- build: `fs-compare-build.sh`。既定出力は`output-fscmp-v2`です。旧版のBuildroot fragmentを使うtreeは拒否します。
- 単発: `QEMU_LOG_DIR=/永続的な絶対path fs-compare.sh E1 smoke run-id`。既存のrun directoryは上書きしません。
- matrix: `fs-compare-matrix.sh --runs-dir /永続的な絶対path plan.tsv`。旧版と混ぜず、v2で作ったmatrix directoryだけ再開します。

## 容量とlog上限

`storage.py`はimage作成前にoutput・一時領域・archive先をfilesystemごとに調べ、同じdeviceの見積りを合算します。`capacity.json`に内訳、空き容量、必要量、並列数、plan行数、最大attempt数、未実行smoke数を保存します。展開rootfsは`unsquashfs -lln`のfile size合計とentryごとの64 KiBから見積もります。

- output: 同時実行数に対する8 GiB image、展開・再pack用のrootfs 2個分、中間file 1 GiBに、全attemptのlogと保持するtextの上限を加えます。
- 一時領域: 同時実行数に対する8 GiBと展開rootfsを確保します。launcherがimageをcopyしない場合も差し引きません。
- archive: 全attemptのimage・rootfs・中間file・logの合計に10%と16 MiBを加えます。sparse、reflink、gzipによる節約は前提にしません。

各filesystemの必要量は`max(見積り × 1.2, 5 GiB)`です。planの各反復行に最大attempt数を掛け、新規smokeを足します。証明を再利用できるsmokeは新規分に数えません。matrixの`--max-attempts N`は既定2で、retryは最大N−1回です。実行前と各job・probeの投入前に再検査し、検証済みarchiveとcleanupが終わったattemptだけを予約から引きます。同時に進行中のjobは予約を保持します。ほかのprocessによる消費も空き容量へ反映され、不足時には新しいjobを開始しません。logを削除して空きを作ることはありません。

`FSCMP_LOG_LIMIT_BYTES`はattempt内の`.log`・`.jsonl`・`errors.txt`と外側のlauncher logの合計上限で、既定256 MiBです。入力rootfs内の既存logは監視対象から外します。実行中は0.2秒ごと、回収後は再走査の前後に確認します。上限を超えた場合は失敗にしてraw logを保存し、truncateしません。poll間の超過分も保存します。空き領域の消費をOSのquotaのように禁止する機構ではありません。

## archiveとcleanup

単発・matrix・smoke・除外probeとも、子とQEMUを回収し、外側のlauncher logをrun内へcopyしてから最終scanを行います。source・launcher・workloadの写し、生成済みconfig、環境、command、plan、判定、raw logを保存します。通常測定は使い捨てimageと展開rootfsを含むattempt全体をarchiveします。smokeだけは後述の共有保存方式を使います。

archive先は既定でruns rootの`archives/`です。`FSCMP_ARCHIVE_DIR`で別の永続filesystemの絶対pathを指定できます。既知の揮発pathである`/tmp`、`/var/tmp`、`/run`、`/dev/shm`は拒否します。それ以外のpathが実際に永続することは利用者が確認してください。一時領域だけは`TMPDIR`を使います。

処理順は回収、最終scan、manifest、`.tar.gz.partial`作成、全memberとmanifestの読み戻し検証、確定名へのrename、directoryのfsync、完了記録、cleanupです。manifestには相対path・種類・SHA-256・byte数・mtime_nsを記録し、symlink・hardlink・空fileも保存します。mtime_nsはPAX headerにも保持します。manifest自身のhashはrunの`.storage.json`へ保存し、その完了記録自身はarchiveへ入れません。

成功・失敗・中断・除外のいずれもarchive対象です。cleanupするのは使い捨てimageとbuild内の非log payloadだけで、`.log`・`.jsonl`・`.txt`は元pathにも残します。失敗・破損・ENOSPC・sourceの変化があればcleanupしません。失敗した`.partial`も自動削除しません。QEMUの回収を確認できない時は、archiveとcleanupを止めてsourceを残します。SIGKILLやhost障害で回収処理まで失われた場合に、自動で完了できるとは保証しません。

再開時はarchiveとmanifestを検証し、未完了の記録を成功にしません。元のpayloadを未検証のまま消すこともありません。障害を直した後は`python3 storage.py finish /runの絶対path TEST 子の終了値`で同じattemptのarchiveを再試行できます。既存の完了archiveも読み戻してからcleanupを再開し、失敗したsourceが変わっていれば停止します。

これらの入口は本書と同じdirectoryにあります。`run-qemu.sh`は既存のものを使い、exec後のQEMUをPython supervisorが直接waitします。`FS_COMPARE_V2_DRIVER`はhost試験で偽driverを渡す入口で、環境検査とsmokeを迂回します。通常は指定しません。`FSCMP_PREFLIGHT_WORKER`、`FSCMP_SMOKE`、`FSCMP_EXPECT_KERNEL`は内部呼出し専用です。利用者が設定してはいけません。

## 環境検査とsmoke

`preflight.py`が単発とmatrixの通常入口から呼ばれます。test imageの展開・加工より前にhost toolの実体・version・hash、kernel・DTB・rootfs・SD image・workload・replay-logのhashを確認します。Buildrootの`.config`と、build配下のLinux・BusyBoxの生成済み`.config`を保存します。fragmentだけでは代用せず、必要なkernel機能は組込みの`=y`を要求します。欠損、version取得失敗、設定不足、異なるkernel/DTBへの環境変数による差替えは停止します。

承認済みの環境へ固定する場合は、単発・matrixとも`--expect-environment FILE`で保存済み`environment.json`を渡します。tool versionを含む現在の環境が一致しなければ、smokeやimage作成の前に停止します。指定しない初回は環境を収集し、そのhashに対してsmokeを実行します。

guestの情報は起動しないと確認できません。診断用imageを作った後、各smokeのvolume作成前に`fs-compare-probe`を実行します。実kernel releaseを生成物のreleaseと照合し、filesystem、dm target、mkfs/fsck・暗号化toolのversionを記録します。module未導入などで実際に機能を利用できなければ失敗します。本測定用imageは、この検査を含む全smokeが終わるまで作りません。

`paths.tsv`は引数検査・新plan生成・smoke生成に共通の経路定義です。全20 baseについて全経路を通します。T1の各replay方式・negative方式・sampleの自動選択と明示選択、T2/T3のcutとverify、T4のcontrol、T5/T6/T7を含みます。明示sampleはそのrunで生成した最初の有効なentryを選びます。全variantではTSVに指定された標準のT3・T4-sync・T5と、対象ならT6に加えてmount-only smokeを通します。それ以外の組合せが入力planにあれば、その組合せも追加します。

smokeも同じguest dispatchと最終判定器を使い、反復は1回です。T1のall・final・sampleを統合せず、allは短縮workloadが生成した候補を全て再生します。mountできただけではcoverage済みにせず、未実行・途中失敗・verify未完了なら本測定を開始しません。smokeの結果は測定用matrix-summaryに混ぜません。

## 第4段Aの軽量smoke

`smoke-profile.json`をbuild時のC headerとguest設定へ変換します。profile・保存方式・sourceを環境hashへ含め、guestの両phaseでprofile hashを照合します。入口への`FSCMP_SMOKE`指定は拒否し、内部probeの後は通常設定へ戻します。通常測定の値と画像archiveは維持します。

| 経路 | smoke専用の値・確認 |
|---|---|
| W1–W4 | 2 file、2更新、51 record、64 KiB。50 recordのfsync境界と未同期tail、renameとdirectory fsyncを維持 |
| T1 | all・final・negative・sample自動／明示を区別。生成された全候補をallで再生 |
| T2/T3 | W4の書込み・fsync完了、またはT3のfsync ACKを待ってからcut。同じ画像を別QEMUでreopenしてverify |
| T4 | 各3秒、1秒間隔。quiesceは3回連続安定。O_DIRECT controlは変更なし |
| T5 | 実効logical bytesをprofileから算出。既定84352 byte |
| T6 | 既知data、破損注入、stack reopen、readcheck・scrub・fsckを省略しない |
| T7 | 256 MiB。timed setup、mount、umount、fsck、暗号stack closeを維持 |

20 baseの16経路と130 variantの標準経路は削らず、要求数は851 probe／1021 phaseです。限定除外が成立した構成だけ後続probeを省略します。短縮smokeは経路確認であり、durability、性能、idle writeの測定結果には使いません。

smokeの`sdcard.img`と再pack済みrootfsはSHA-256と論理byte数だけをmanifestへ残します。失敗時も画像本体を残さないため、後日の画像解析はできません。展開rootfsを含む非画像証拠は`archives/objects/<SHA-256>`へ共有保存し、attemptごとのarchiveに全entryの種類・mode・mtime・link関係・size・hashを記録します。archiveと同階層の`objects/`も保全対象です。

QEMU回収、最終scan、画像hash、非画像保存、全参照読戻し、fsync、完了記録の順を守り、完了後だけcleanupします。欠損・改変・ENOSPC・未回収なら成功にせずsourceを残します。中断後は同一の環境・plan・profileと証拠hashが一致する完了probeだけを再利用し、失敗attemptは残します。

容量検査は通常attemptとsmokeを分けて合算します。smokeのlog上限は8 MiB、各attemptの非共有metadata等に16 MiB、共有証拠に展開rootfsの2倍と1 GiBを予約します。outputとarchiveの両側にlog・metadataを積み、同時image・一時領域と20%余裕も維持します。各投入前に空き容量を再検査し、archiveとcleanupの完了分だけ予約を返します。上記の通常測定の全画像予約をsmokeへは適用しません。

```sh
python3 board/cardputerzero/tools/bench/fs-compare-v2/preflight.py generate --repetitions 1 > plan.tsv
OUTPUT_DIR="$PWD/output-fscmp-v2" python3 board/cardputerzero/tools/bench/fs-compare-v2/preflight.py gate plan.tsv /永続path/preflight --smoke-only
```

`gate --smoke-only`は本測定を起動しません。`diagnose CONFIG PATH DIRECTORY`は代表経路だけを調べ、coverage証明を作りません。`stage4.py`はfresh build、代表経路とA/A・負対照、全smokeの順に実行する記録用入口です。詳細なコマンドは第4段の記録を参照してください。

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

`summary.pending.csv`は中間値です。回収後に全logを再走査し、`summary.csv`と`result.json`をatomic置換します。archive直前にもscanし、最初の判定は`result-before-archive.json`へ残します。通常実行の成功には`.storage.json`のarchive・cleanup完了も必要です。matrixはschema・run識別・summary hash・phase結果も検査し、子processが非zeroならsummaryがokでも失敗です。子の終了値も保存し、再開で成功に変わることを防ぎます。これはhostの突然の電源断まで保証するものではありません。

## errorの保存

`host.log`にはdriverの準備・image加工のstdout/stderr、`qemu-run.log`と`qemu-verify.log`には各phaseのQEMU/guest出力を残します。`qemu.log`は回収後の結合logです。`phase-*.json`にはQMP、fallback、終了値、回収の有無、log hashを保存します。

`errors.jsonl`と`errors.txt`にはfile・行番号・phase・分類・原文・expectedの区別を保存します。process statusも記録します。guestのerror、kernel panic/Oops、QEMUのfatal、未知のerrorは成功markerより後でも失敗です。T1 replayとT6 corruptionのguestが明示した区間だけ、列挙したfilesystem診断・測定markerをexpectedとして残します。kernel panic、guestの失敗、SDのI/O errorは除外しません。区間が閉じない時も失敗です。未知の診断は保守的に失敗するため、後続のsmokeで分類の妥当性を確認する必要があります。

## host試験

repo rootで`python3 tests/fs-compare-v2/run.py`を実行します。偽process・QMP peer・tool・小さいlogを使い、QEMUやnetworkは使いません。registry、plan、生成済みconfig、host/guest probe、限定的な除外、coverageとhashによる再利用も検査します。`run-host-tests.py`にも登録しています。実QEMUとの結合、全workloadの経路、再現性、性能、LCD表示は未確認です。
