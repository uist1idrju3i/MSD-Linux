# S4参考: fs-compare-v2第4段Aの軽量smoke

## 目的と事前条件

利用者が承認した第4段Aをv2内に実装した。通常測定と旧版を変えず、851 probeの経路確認を短いworkloadで実行する。正式な性能・durability測定ではない。実機のSD書込み、FTL、電断、LCDは対象外とする。

fresh buildと、serial断片分離後の代表21件の経路確認は成功した。A/Aと負対照2件も含む。全smokeは初期10/851件が成功し、backgroundで継続中。全coverageは未完了である。初回のboot診断と明示sampleの停止を含む失敗試行も保持した。[CSV](2026-11-19-s04-fs-compare-v2-stage4.csv)と[実装と保存仕様](../../board/cardputerzero/tools/bench/fs-compare-v2/README.md)を参照。

## 固定条件と判定基準

- freshな`OUTPUT_DIR=output-fscmp-v2`を既存の`fs-compare-build.sh`で構築する。製品defconfig・overlay・旧workload・dm-verity/FECは変更しない。download cacheは再利用する。build treeはcold、ccacheの事前状態は不明として記録し、速度比較には使わない。
- `smoke-profile.json`のW1=2 file、W2=2更新、W3=51 record、W4=64 KiB、T4=3秒、quiesce=3連続sample、T7=256 MiBを使う。T5は84352 logical byte。通常profileの値はhostで別途照合する。
- 20 baseの16経路、130 variantの標準経路を保つ。851 probe／1021 phaseが要求され、限定除外だけを認める。各1回なのは機能経路の確認であり、5回反復の性能比較に代用しない。
- QMP終了・回収、全logの最終scan、profile hash、全phase、T2/T3のcutとverify、非画像archiveの全参照読戻し、cleanup完了が必要。未知errorや未完了を成功にしない。
- 代表診断はE1の全replay・cut・T4 control・T5/T7、各filesystem系統のmountとI2/T6。E1/mountのA/Aを2回、T1-negativeとnegative-finalを負対照にする。negative-finalのloss検出は既存driverの必須条件を維持する。
- SD imageと再pack rootfsはhash・sizeのみ保存する。失敗画像も保存しない。log・manifest・source・生成config・展開rootfsは共有objectと参照manifestで保存し、欠損・改変・ENOSPC時にはcleanupしない。

## 再実行

repo rootで次を順に実行する。各stageは既存directoryを上書きせず停止する。最初にhost試験・文書検査を通し、codeをcommit・pushしてからbuildする。

```sh
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py build --runs-dir /work/fscmp-v2-stage4
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py representative --runs-dir /work/fscmp-v2-stage4
OUTPUT_DIR="$PWD/output-fscmp-v2" docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py smoke --runs-dir /work/fscmp-v2-stage4
```

`stage4.py`はcommit、実QEMUのversion・hash、Buildroot commit、OS、command、時刻、df、終了状態を保存する。build後は生成済みconfig、kernel・DTB・rootfs・SD・workloadのhash、compiler情報も保存する。代表診断はcoverage証明にはならず、全smokeの成功前に本測定を開始しない。再開では`preflight.py gate PLAN DIRECTORY --smoke-only`へ同じplan・環境を渡す。

## 結果と限界

実装中のhost試験は初回1件失敗した。workloadのhost fixtureにroot directoryがなく、実guestには存在するmountpointを再現できていなかった。fixtureを修正し、通常full／t1-reducedとsmokeのfile数・byte数、rename、fsync境界を照合した。これは製品やQEMUの失敗ではない。

codeは`9fd57cb3d489065e5bd8e25a3ef422c0182dc828`をcommit・pushしてからbuildした。v2の最終host試験は56件成功。host aggregateの11 suiteも成功した。ShellCheck、JIS、links、doc-sizeの検査を実行した。これらはQEMUの全経路成功を示さない。

### fresh build

buildは3491.520939秒、終了状態は成功。Buildrootは`75f325ad84251ee9d903467f84d3683e3bcf3fd5`、kernelは`6.18.59-v8`、GCCは実binaryの出力で`14.3.0`だった。GCCの版文字列には外部toolchainの`Buildroot 2021.11-18033-g83947c7bb6`が含まれ、今回のBuildroot本体commitとは区別する。

実行環境は`msd-dev:local`、image IDは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。QEMUは11.1.2。使用binaryのSHA-256は次のとおり。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  /usr/local/bin/qemu-system-aarch64
```

| 入力・生成物 | SHA-256 |
|---|---|
| Image | `405e21365c7b971661af9b78c3db7adcca2434eb680ed10c59a9a3c2348180e8` |
| bcm2710-rpi-3-b.dtb | `a1bf19944b3c6cd1c8839de25a9a69f1f53a1ad1dd49993f394bd64a78022a2f` |
| rootfs.squashfs | `45f6e6ea9ef7c44f3d66010671a9912f8f99cd5853c6a6201d831e2daa29bcba` |
| sdcard.img | `8ffe3083b02a0e92458b82f499251bfd61afb19fbdbdec5481d42107caf1bd3b` |
| fs-compare-workload | `194b227a899c6ba4429931345258f5b7ba752c10b3ffcb408ce4fd46e0d5302a` |
| replay-log | `e02779a201b41bf34897c3bc72daafa7e0b13dfc148bb91400599471ffae2750` |

config再代入、configureの未対応option、jobserver、compiler等のwarningがあった。BusyBoxは存在しない`ASH_SLEEP`、cryptsetupはOPAL用kernel headers不足も警告した。開発用更新署名keyの生成は測定用buildの動作であり、key本体は証拠archiveへ含めていない。これらを製品の全機能成功やheader更新の根拠にしない。warningの行と生成済みconfigは下記archiveに保存した。

### 最初の代表診断と停止理由

E1/smokeの診断command全体は308.422911秒、probe本体は305.528080秒だった。guestは`environment_ok kernel=6.18.59-v8`、正しいprofile hash、`smoke=mounted`、`finished`を出した。`phase-run.json`は`returncode=0`、`qmp_quit=true`、`reaped=true`、`marker=true`、`fallback=[]`、`error=null`だった。panic、Oops、BUG、guestの`msd.fscmp: error=`は検出されなかった。

一方、変更していない`supervisor.py::aggregate_errors()`は次のようなboot診断を含む24行をfatalとした。`result-before-archive.json`では`driver_status=0`だが`fatal_errors=24`、`status=fail:final_judge`。driverが失敗を返し、archive前の再scanではその終了状態も加わって25件になった。

```text
efi: UEFI not found.
brcmvirt-gpio soc:firmware:virtgpio: Failed to set gpiovirtbuf, trying to get err:0
Re-reading the partition table failed.: Device or resource busy
```

GPIO・UART・rdinit・partition table等も含み、24行全てを無害と確認したわけではない。既存判定器はmainと同一で、今回の変更による差分はない。起動完了だけを理由に診断を無視せず、未知errorを拒否する条件を維持した。次は各行の発生元と対象外hardwareとの関係を確かめ、限定した扱いをreviewしてから新run IDで代表診断を再実行する必要がある。

非画像archiveは2241 entryの全参照読戻しに成功し、tar内は参照manifestだけだった。保持された共有objectとarchiveは48,922,624 byte、cleanup後のprobe directoryは966,656 byteだった。これはhost上の割当量で、実SDの物理write量ではない。SD imageの8,589,934,592 byteと再pack rootfsの24,133,632 byteは本体を保存せず、hash・sizeをmanifestへ残した。

build後の空きは247,146,934,272 byte。最終確認は`df -h`で231Gだった。成功probeを10件得られていないため、全件の更新所要時間は推定しない。A/A、負対照、残りの代表診断と全経路の結果を成功へ振り替えない。QEMUのblock統計や短いidle窓から実SDの耐久性・無書込みを断定しない。

### 判定器修正後の再診断条件

初回24行の[分類と固定source](../../board/cardputerzero/tools/bench/fs-compare-v2/boot-diagnostics.md)を追加した。19行は固定machine・版・boot区間・phase・文面を限定して既知診断として記録する。camera regulatorの3行と、内部分岐の未確定な補助UARTの2行はfatalのまま残す。v2のDTB写しだけで測定に使わないcamera regulatorと補助UARTを無効にし、製品DTB・共通launcher・kernel configは変更しない。元の失敗はそのまま保持する。

初回logそのもの、文面の近似、誤ったphase・版・machine、boot後の再出現、EIO・ENOSPC等でhost回帰を行う。再診断には既存出力を上書きしない新しいrun directoryを使い、同じbuild生成物を再利用する。probeの開始前とcleanup後の空きbyte差も収集する。共有filesystemの差分なので、他processの消費を分離した値ではない。

### 初回の保存済み証拠

[証拠archive](2026-11-19-s04-fs-compare-v2-stage4-evidence.tar.gz)は207,033 byte、SHA-256は`2e58c75e8656242d02cd3f2020ab69f4168d327ee3dd6e63125782162a88159a`。37 memberのsize・hashを`SHA256.json`で読戻し照合した。build条件・生成済みconfig・版と入力hash、probeのserial・host log・phase・最終判定・画像省略manifestを収録した。archive内の絶対pathは実行時のraw値である。

7,469,895 byteの全build logと共有object本体はコミットしていない。build logのSHA-256は`1585bef2c665b952e4062b455ffb997b26d8d362adf297cdb345c0c8ad297d1d`。再生成には上記のcode commitとfresh出力先でbuild・代表診断を実行する。失敗試行を成功として再利用しない。

### A/A成功とT1の再停止

harness commit `74bc9e3b40260632bb602c7fd35d1f39bba3e163`で、同じbuild生成物を再利用した。kernel・DTB本体・rootfs・workloadの再buildはなく、各probeでguest hookを写しへ入れる。最初の起動依頼は相対run directoryを拒否され、QEMU開始前に終了した。この失敗も保存した。次は次のcommandで実行した。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py representative +  --runs-dir /work/fscmp-v2-stage4-bootfix-02
```

| 診断 | command全体、秒 | probe本体、秒 | filesystem使用量差、byte | 結果 |
|---|---:|---:|---:|---|
| E1/smoke A | 276.84786771399376 | 273.9513031630049 | 50,216,960 | 成功 |
| E1/smoke A再試行 | 270.1614557080029 | 267.2806370199978 | 1,454,080 | 成功 |
| E1/T1 | 506.01140718499664 | 503.1206269719987 | 1,748,992 | 失敗 |

空き容量の差は共有filesystem全体の値で、各probe単独の割当量ではない。A/Aは機能確認2回であり、性能の同等性を示さない。

T1のlogは`W3 records=51`に対し`T1_W3_EXPECTED cycle=0 max_record=50 bytes=6400`だった。最後のfsync markerが50なので、T1だけが51番目のtailを全体の上限超過として拒否した。prefix hashは一致していたが、この時点ではtail内容の検査に達していない。後続修正では`W3_FULL_RECORDS`を渡し、smokeは51、通常は従来と同じ1000を上限とする。同期済みprefixとtailの各recordの内容検査は維持する。

同じbootでpartition 7拡張と再読込み診断の間に、timestamp付きのLED診断が割り込んでいた。後続修正では、間にkernel行があっても「次のuserspace行」である場合に限り照合する。kernel行自身の判定は変更せず、他のuserspace行を挟んだ場合も拒否する。

host試験は、初回logの全24診断で19 expected・5 fatalを照合して60件成功した。tail修正後は、50または51の正常record、空file、部分record、改変tail、52 recordの上限超過、通常1000 record、行の割込みを加えて62件成功した。host aggregateも全11 suiteが成功した。次の代表診断は既存出力を上書きせず、別run directoryで行う。

[追加証拠archive](2026-11-19-s04-fs-compare-v2-boot-evidence.tar.gz)は111,058 byte、SHA-256は`6a0cd4227294af2f4de17c1eaa88703c153fc8a982c17f28de4c35dd9428c458`。77 fileのsize・hashを読戻し照合した。起動依頼の失敗、A/A、T1失敗のserial・host log、各phaseのDTB、環境・保存状態、host検査を収録した。画像と共有object本体は含めず、元の非画像archiveと共有objectは測定出力に保持している。raw log・metadata内の絶対pathは実行時の値である。

### 再診断03: tail成功と1行内の割込み

code commit `a3c3a5a9561f5303052dfdf6afedf164a21404ca`を保存・pushした後、同じbuild生成物で実行した。前の出力は上書きしていない。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py representative +  --runs-dir /work/fscmp-v2-stage4-bootfix-03
```

| 診断 | command全体、秒 | 結果 |
|---|---:|---|
| E1/smoke A | 294.15094499599945 | 成功 |
| E1/smoke A再試行 | 277.21236964999116 | 成功 |
| E1/T1 | 485.8173672630073 | 成功 |
| E1/T1-final | 369.9134132129984 | 成功 |
| E1/T1-sample | 398.12064521999855 | 成功 |
| E1/T1-sample-selected | 329.6439274690056 | 失敗 |

T1 allでは`T1_W3_EXPECTED cycle=0 max_record=51 bytes=6528`となり、最終dm-snapshotの`expected_files=5 actual_files=5 mount=yes fsck=0 manifest=yes`を確認した。tail上限の修正はこの経路で機能した。probe本体の時間とfilesystem使用量差はCSVに残した。

明示sampleではguestが`finished`まで進み、phaseは`returncode=0 qmp_quit=true reaped=true fallback=[] error=null marker=true`、`summary.pending.csv`も`status=ok`だった。しかしboot logの316–317行は次の形だった。

```text
Re-reading the partition table failed.[   16.000491] mmc1: Timeout waiting for hardware interrupt.
: Device or resource busy
```

直前はpartition 7の拡張で、userspace診断の途中へkernelの断片が入った。kernel行は固定sourceの[SDHCI timeout log](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/mmc/host/sdhci.c#L3287)に一致するが、QEMU側のtimeoutの原因は今回未切分けである。

`aggregate_errors()`は物理行の先頭timestampだけを除いて完全一致を調べるため、316行を既知の再読込み診断と認めなかった。archive前のfatalはこの1件で、driver終了状態は0だった。最終rescanではdriver終了状態1が加わりfatalは2件となった。guest側のreplay失敗やQEMU回収失敗を原因とする候補は、これらの結果と一致しない。

kernel/userspaceが1行内で混ざる場合の判定は未解決であり、両者をまとめて無害と扱う変更はしていない。代表診断は21件中5成功・1失敗・残り15件未実施で終了した。負対照2件にも達していない。全smokeの開始条件を満たさないため、851件のbackground run、最初の10件の実測、実測に基づく所要時間の更新は未実施である。

[再診断03の証拠archive](2026-11-19-s04-fs-compare-v2-bootfix03-evidence.tar.gz)は210,107 byte、SHA-256は`9b5e52fd2475636dcfa238505da69e2f5f69dcc9d26e5ace1a64a520f9dcc4fc`。137 fileのsize・hashを読戻し照合した。6件の結果、serial log、`errors.jsonl`、phase・環境・保存状態、生成DTB、runnerの終了を収録した。画像と共有object本体は含めていない。

### boot期間だけのserial断片分離

承認後、kernel timestampで断片を分け、保留したuserspaceの断片へ次のuserspace行を連結する処理を追加した。両方の断片を既存の判定規則へ別々に通す。boot期間外・host logは従来どおりで、raw logは変更しない。combined lineのallowlistは追加していない。

再診断03の実logを新しい判定器へ通すとfatalは0件となり、log本体のSHA-256が不変であることを照合した。これは過去の失敗を成功へ書き換える再実行ではなく、判定器のhost検査である。過去の結果JSONとCSVは失敗のまま保持した。単独の`mmc1: Timeout waiting for hardware interrupt.`は既存規則のfatalに一致しないため、smoke DTBの無効化対象を増やしていない。

host aggregateは全11 suite成功、v2は64 test成功。実際の316–317行、空入力、未完の断片、boot終了、scope違い、errno違い、未同期setup、独立した未知error・panic・Oops・BUG・EIO・ENOSPCを検査した。新しい代表診断の結果は次の試行として残す。

### 再診断04と全smokeの開始

codeは`b77348dbe37af68b1e5dafdab383b5ab70cb5859`、run directoryは`fscmp-v2-stage4-bootfix-04`。既存のbuild生成物を再利用し、過去のrunを上書きしていない。代表21件はdriverと判定器が全て成功し、全体は7309.030秒だった。A/Aは301.253秒と280.175秒、T1-negativeはloss 10件、negative-finalはloss 1件を検出した。

T2/T3はcut後に別QEMUでreopenし、両方で`recovery_fsck=0`、`recovery_mount=ok`、`recovery_finished`を確認した。T2はW3のprefix hash不一致で`manifest_ok=no`、T3は`T3_FSYNC_LOST count=0`だった。経路の成功を、回復データの全件一致やdurabilityの成功と読み替えない。I2/T6は破損注入、stack reopen、readcheckとfsckまで到達し、`raw_changed=yes`、`T6_READCHECK exit=3`、`T6_FSCK result=0`だった。dm-integrityなのでscrub metricsは`not_applicable`。Btrfsのscrub経路を成功した扱いにはしない。

代表全件の成功を確認してから、同じcodeとbuildで次を直列実行した。PIDはhost上の`1145717`。実行中のスクリプトは変更していない。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/fs-compare-v2/stage4.py smoke --runs-dir /work/fscmp-v2-stage4-bootfix-04
```

初期checkpointは10/851 probe成功、除外0件。851 probe／1021 phaseの要求は不変で、通常測定の残り試行数は0。以下は全smokeそのものの初期値で、代表診断とは別である。

| 順序 | E1の経路 | probe秒 | filesystem使用量差byte |
|---:|---|---:|---:|
| 1 | smoke | 280.859 | 50,397,184 |
| 2 | T1 | 504.190 | 1,740,800 |
| 3 | T1-negative | 408.372 | 1,671,168 |
| 4 | T1-final | 381.137 | 9,924,608 |
| 5 | T1-negative-final | 377.060 | 1,548,288 |
| 6 | T1-sample | 402.323 | 1,585,152 |
| 7 | T1-sample-selected | 343.802 | 1,519,616 |
| 8 | T2 | 350.106 | 1,822,720 |
| 9 | T3 | 353.258 | 1,798,144 |
| 10 | T4-sync | 303.488 | 9,883,648 |

平均370.460秒、中央値365.159秒。単純に851倍すると計87.57時間、10件完了後の残りは86.54時間となり、当初の24〜72時間という仮見積りを更新する。先頭10件はE1だけで、構成や経路の比率、再試行、後続の停止を反映していない粗い見積りである。

使用量差の合計は81,891,328 byte。一律外挿は6.97 GB、初回を別扱いにして残り9件の平均を850倍すると3.02 GB。ただし共有filesystemの空き差であり、保存証拠だけの量や実SDの物理write量ではなく、容量保証にも使わない。開始時の容量gateはoutput/archiveで65,184,499,272 byte、tempで10,533,151,122 byteを必要空きの計画値とした。確認時の`df -h /home`は466G中212G使用、230G空き、48%だった。

[再診断04と初期10件の証拠](2026-11-19-s04-fs-compare-v2-run04-evidence.tar.gz)は4,051,114 byte、SHA-256は`ee5e0b19d775895ae0c7914cbfd5006481db7bf133465d38d1cbb85883285f59`。768 member中767 fileのsize・hashを読戻し照合した。環境・入力hash、全21件と初期10件のserial・phase・保存状態・画像省略manifest、coverageの写し、PID・起動条件・外挿式の値を収録した。画像と共有object本体は含めていない。

全851件の完了は未確認。追加の診断例外は足していない。全smoke完了後に、RAID6 benchmarkを含む見落とした最適化候補の棚卸しへ進む。

### PR review後の通常T1上限修正

通常T1は`full`ではなく`t1-reduced`を使うため、W3の上限は1000ではなく250件である。writerと同じprofile選択関数から実効record数を取得し、replayのtail上限へ渡すよう修正した。250件は受理し251件は拒否、smokeは51件を受理し52件を拒否する。fullの1000件も維持する。

修正は別worktreeで行った。実行中の全smokeは`098c7f5dda8c7e884fa94deec5bbb0f1eb76af24`のsourceを使い続け、元のworktreeに差分がないことを確認した。smokeの51件という上限は変わらず、実行中のprobeと後続probeへこの修正を適用していない。

### 全smokeのnegative-final停止と判定修正

再診断04後の全smokeは20件を完了し、21件目の`E2/T1-negative-final`で
`t1_negative_final_checker_validation_failed`となって停止した。
driverの末尾も`smoke failed: E2/T1-negative-final; main run not started`である。
E2はext4の`data=journal`で、最終replayではmountとfsckが成功し、
W1の2 fileがともに残って`manifest=yes`だった。中間13点のうち9点では欠損した。
この停止と値は旧判定器の履歴として保持し、成功へ書き換えない。

原因はguestの最終点のguardが`manifest=no`を要求し、末尾のguardも
`loss_points > 0`を要求していたことにある。fsyncなしの書き込みが残ることは
正当な結果であり、必ず失われるという前提ではcheckerを検証できない。
stage4とpreflightはguestの失敗を受けて停止しており、自然な欠損を要求する
この2つのguardはともにguest内にあった。

修正後も`manifest=yes/no`と`loss_points`は観測値のまま記録する。
負の対照は期待manifestのうち回復filesystemにfileが存在する行を
workloadを問わず別fileへコピーし、期待hashの先頭1桁を
意図的に変更して同じcheckerへ渡す。回復filesystemと元manifestは変更しない。
空の期待集合や全file欠損だけではhash不一致の検出を証明できないため、
少なくとも1件のhash不一致を検出した場合だけ負の対照を成功とする。
負の対照ではW2の先行更新やW3の追記を許容する判定を使わず、
改変hashとの不一致を検出する。期待fileが1件も存在しない場合は
`t1_negative_control_no_present_file`をconsoleへ記録して失敗する。
negative-finalの合格条件はmount成功、fsck成功、この負の対照の成功の3つとする。
自然な欠損の有無は合否に使わない。

host回帰テストでは正常なmanifest、file欠損、空の期待集合、改変hashの検出、
checkerが改変を見逃す場合の不合格、およびmount・fsck失敗を検査する。
これはcheckerの検査であり、QEMUや実機の電源断の再検証ではない。

完了済み20 probeと失敗した21件目の記録は履歴として残す。
修正で環境identityが変わるため、旧20件を引き継がず、新しい出力先で
851 probeを最初から再実行する。今回の修正作業ではbuildもsmokeも開始しない。

初回の修正では負の対照をW1だけから作っていたため、W1が全て失われた場合も
誤って失敗していた。reviewでこの前提を指摘され、上記の存在するfileだけを
使う方式へ修正した。W1欠損時にW2・W3・W4の各fileを使えること、
W1が存在する場合、期待fileが全て欠損した場合の専用理由、
checkerの検出失敗をhost回帰テストへ追加した。
