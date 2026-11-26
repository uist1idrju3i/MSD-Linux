# S4参考: fs-compare-v2第4段Aの軽量smoke

## 目的と事前条件

利用者が承認した第4段Aをv2内に実装した。通常測定と旧版を変えず、851 probeの経路確認を短いworkloadで実行する。正式な性能・durability測定ではない。実機のSD書込み、FTL、電断、LCDは対象外とする。

以前の代表21件の経路確認は成功したが、全851件smokeは未完了。[試行07のhost中断と08のT7誤判定](2026-11-26-s04-fs-compare-v2-t7-btrfs.md)に続き、最新の[試行09はE1のgrow完了行を誤分類](2026-11-26-s04-fs-compare-v2-grow-marker.md)して先行診断で停止した。09の代表21件と851件は未開始。保存logの写しは限定修正で再判定がokになったが、元の失敗試行は保持し、main runも未開始。[CSV](2026-11-19-s04-fs-compare-v2-stage4.csv)と[実装と保存仕様](../../board/cardputerzero/tools/bench/fs-compare-v2/README.md)を参照。

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

修正は別worktreeで行った。当時実行中だった全smokeは`098c7f5dda8c7e884fa94deec5bbb0f1eb76af24`のsourceを使い続け、元のworktreeに差分がないことを確認した。smokeの51件という上限は変わらず、この全smokeのprobeへ修正を適用しなかった。その後の停止は次節に記録する。

### 全smokeのnegative-final停止と判定修正

再診断04後の全smokeは20件を完了し、21件目の`E2/T1-negative-final`で
`t1_negative_final_checker_validation_failed`となって停止した。
driverの末尾も`smoke failed: E2/T1-negative-final; main run not started`である。
E2はext4の`data=journal`で、最終replayではmountとfsckが成功し、
W1の2 fileがともに残って`manifest=yes`だった。
従来の「中間13点のうち9点では欠損した」という値は、対応する試行とlogを
特定できていないため未確認とする。`T1-negative-final`のreplayは最終点だけを
検査するので、この値を21件目の観測値として扱わない。
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
`T1_MANIFEST_FAIL`の診断には`context=recovery`または
`context=negative_control`を付け、自然な不一致と意図的なhash改変を区別する。
どちらもreplay区間内ではhostの想定内診断として保存する。

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

## b242681での再試行01〜03: いずれも停止

判定修正後の`b242681202aa74ecaa04abb7874c904bc55b2b16`にsourceを固定し、
fresh build、既定の代表21件、単独の`E2/T1-negative-final`診断、
全851件の順で実行する計画で再試行した。各試行は別の出力先を使った。
3試行とも途中で失敗し、単独E2診断と全851件は未実施である。
下表の成功件数は代表21件のうち実行できた件数だけを示す。
旧20件や異なる試行の成功を引き継いでいない。

| 試行 | build | 代表診断 | 停止理由 |
|---|---|---|---|
| 01 | 0.813036秒で失敗 | 0成功、21未実施 | worktreeのsubmoduleの相対Git参照がDocker内で解決できず、Buildrootのcommit取得で停止。compileと容量gateより前 |
| 02 | 3567.344184秒で成功 | 0成功、1失敗、20未実施 | standalone cloneへ変更したが、既存の開発imageはQEMU 11.1.2。規則が要求する11.1.3と不一致で、既知boot診断17件をfatalと判定 |
| 03 | 1442.812923秒で成功 | 2成功、1失敗、18未実施 | imageを再構築し11.1.3へ一致。E1/smokeのA/Aは成功したが、E1/T1の区間markerとkernel printkが連結して停止 |

試行03のimage IDは
`sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65`。
QEMU binaryのSHA-256は
`8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73`で、
実binaryの版出力と`boot-diagnostics.json`はともに11.1.3だった。
stage4はDocker image IDを記録しないため、外側の実行記録に保存した。
stage4のQEMUの版とhashは再構築imageと一致している。

### 証拠の保存状況

この3試行のtext証拠はorphan branch `data/fs-compare-experiments`の
commit `e3d073d42822535330ec08d3dc112e5abd859d67`に保存した。
配置は`fs-compare/stage4-rerun-b242681-01-03.tar.zst`、
memberごとのhashは同名の`.files.sha256`、選別・除外・加工の記録は
同名の`.selection.json`である。
[保管branchの案内](https://github.com/uist1idrju3i/MSD-Linux/blob/e3d073d42822535330ec08d3dc112e5abd859d67/README.md)にも対象を記した。
既存の古い証拠archiveには追加していない。
保管した証拠の識別名は次のとおり。要約と
[CSV](2026-11-19-s04-fs-compare-v2-stage4.csv)には生の秒数を残す。

- 01: `attempt-01-failure.md`、`build.log`、`build-host-result.json`、
  `failed-rerun-b242681-01`。旧worktreeは証拠を保存した後に削除した。
- 02: `attempt-02-diagnosis.json`、`build-02-host-result.json`、
  `representative-02.log`、`rerun-b242681-02`。
  `rerun-02-copy-manifest.json`で1595 fileのsize・hashを照合した。
- 03: `attempt-03-diagnosis.json`、`image-inspect-03.json`、
  `qemu-verify-03.json`、`build-03-host-result.json`、
  `representative-03.log`、`rerun-b242681-03`。
  `rerun-03-copy-manifest.json`で1795 fileのsize・hashを照合した。

archiveはlog、結果JSON、manifest、診断JSON、実行scriptなどの
text 682 fileを含む。image・binaryなど2736 fileは含めず、
除外したpath・size・hashを`.selection.json`に残した。
試行02のbuild log 1 fileは署名付きdownload URLのqueryだけを保管用の写しで伏せた。
その変更前後のhashも同JSONに残し、元logと他のmemberは変更していない。
旧copy manifestは元の保存物全体のhash、`.files.sha256`は今回公開した
memberのhashであり、対象が異なる。push後にremoteからcommitを取得し、
archiveと全682 memberのhashを照合した。

### data branchからの取得と読取り専用の再分類

リポジトリの最上位で次を実行する。`zstd`、`tar`、`sha256sum`が必要である。
`evidence-b242681-01-03`は新しい保存先とし、既存の証拠を上書きしない。
data branchをmergeしたり、実行中のcloneを変更したりする必要はない。

```sh
git fetch origin data/fs-compare-experiments
data_sha=e3d073d42822535330ec08d3dc112e5abd859d67
mkdir evidence-b242681-01-03
git archive "$data_sha" fs-compare/stage4-rerun-b242681-01-03.tar.zst \
  fs-compare/stage4-rerun-b242681-01-03.files.sha256 \
  fs-compare/stage4-rerun-b242681-01-03.selection.json fs-compare/SHA256SUMS |
  tar -xf - -C evidence-b242681-01-03
cd evidence-b242681-01-03
grep '  stage4-rerun-b242681-01-03\.' fs-compare/SHA256SUMS |
  (cd fs-compare && sha256sum -c -)
zstd -dc fs-compare/stage4-rerun-b242681-01-03.tar.zst | tar -xf -
sha256sum -c fs-compare/stage4-rerun-b242681-01-03.files.sha256
cd ..
```

次の再分類では、修正commitの判定器と規則を新しい証拠directoryへ取り出す。
原log・結果JSONへ書き込まずに実行し、fatal 0件と前後のhash一致を要求する。
失敗した試行を成功へ書き換える操作ではない。

```sh
judge_sha=1dc14a323f4387503a04691838431b741bf97e9f
bench=board/cardputerzero/tools/bench/fs-compare-v2
git show "$judge_sha:$bench/supervisor.py" > evidence-b242681-01-03/supervisor.py
git show "$judge_sha:$bench/boot-diagnostics.json" > evidence-b242681-01-03/boot-diagnostics.json
python3 - <<'PY'
import hashlib
import importlib.util
from pathlib import Path

root = Path("evidence-b242681-01-03")
spec = importlib.util.spec_from_file_location("supervisor", root / "supervisor.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)
log = root / "rerun-b242681-03/representative/03-E1-T1/probe-E1-T1/qemu-run.log"
before = hashlib.sha256(log.read_bytes()).hexdigest()
records = judge.aggregate_errors([("run", log)], "T1")
fatal = sum(not row["expected"] for row in records)
assert before == hashlib.sha256(log.read_bytes()).hexdigest()
assert before == "1ae02dbeda610a19d3dcd56a30f20cd746ca9d0dfa2a1724bfcd9b20340a2430"
print(f"records={len(records)} fatal={fatal} SHA-256 unchanged")
assert fatal == 0
PY
```

試行03の`representative/03-E1-T1/probe-E1-T1/qemu-run.log`の
SHA-256は`1ae02dbeda610a19d3dcd56a30f20cd746ca9d0dfa2a1724bfcd9b20340a2430`。
500行目と505行目は次のとおり。

```text
msd.fscmp: expected_errors_begin kind=T1_replay[  276.732017] EXT4-fs (dm-1): recovery complete
msd.fscmp: expected_errors_end kind=T1_replay
```

旧host判定器は開始kindを`T1_replay[`と読み、開始・終了をともに
不正な区間として記録した。QEMU logのfatalは2件で、
driver終了状態によるhost側のfatalを含めると3件だった。

修正では[既存のserial断片分離](../../board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py)を
この開始・終了markerにも適用する。markerを先に処理し、同じ行のtimestamp付き
kernel断片を独立に判定する。未知のkind、区間外の診断、kernel panicは
引き続き拒否する。[host回帰テスト](../../tests/fs-compare-v2/run.py)に
上記の実測行と、連結した終了marker、T6、未知kind、誤ったphase、
閉じていない区間、kernel fatalの検査を加えた。

修正した判定器で試行03の元QEMU logを読み取り専用で再集計すると、
診断は61件、fatalは0件だった。読取り前後のSHA-256は上記と一致し、
原log、元の判定結果、凍結した実験sourceは変更していない。

guestの`console()`は既に末尾改行付きの`printf`を使っている。
先頭改行を加えてもmarkerの後ろへのprintk割り込みは防げない。
storageへの`sync`もserialの排他にはならないため、guestは変更しない。
この修正はhost判定器の検査であり、失敗した試行03を成功へ変更せず、
QEMUや実機の電源断の再実行とも扱わない。

## 1dc14a3での再試行04: 負対照の未設定変数で停止

sourceを`1dc14a323f4387503a04691838431b741bf97e9f`に固定した新しい
standalone cloneで再試行した。Docker関連fileは`b242681`と同一だったため、
試行03と同じimage IDを再利用した。実binaryのQEMU 11.1.3とhashも一致した。
fresh出力は`output-fscmp-v2-04`、runs directoryは`rerun-1dc14a3-04`である。

buildは3499.8475962750017秒で成功した。代表21件は7成功・1失敗・13未実施で停止した。
成功した経路はE1/smokeのA/A、T1、T1-final、T1-sample、
T1-sample-selected、T1-negativeである。試行03が停止したE1/T1は成功したが、
8件目のE1/T1-negative-finalが次のguestエラーで終了した。

```text
/usr/libexec/fs-compare-guest: line 1117: point_entry: parameter not set
msd.fscmp: error=guest_exit status=2
```

今回は開始markerとkernel printkは別行だった。
`T1_NEGATIVE_FINAL_CHECK`の成功行と`finished`は出ていない。
単独E2診断と全851件smokeは開始しなかった。失敗した試行を成功へ変更せず、
凍結sourceと原logは変更していない。元の保存物2153 fileは
`rerun-04-copy-manifest.json`でsize・hashを照合した。
各probeの秒数と終了状態は[CSV](2026-11-19-s04-fs-compare-v2-stage4.csv)へ追記した。

### 原因と負対照経路の監査

#287で追加した負対照は`check_t1_manifest()`を使うが、その診断に必要な
`point_entry`を渡していなかった。回復経路は
`result="$(check_manifest_at_point ...)"`で実行するため、
その関数内で設定した`point_entry`は親shellへ残らない。
後続の負対照がhash不一致を記録しようとすると、`set -u`により停止する。
修正では負対照関数の第2引数へ最終点の`entry`を渡し、
そのsubshell内で`point_entry`に設定する。回復経路と同じentryを診断へ記録する。

負対照の他の変数も確認した。`RUN_PATH`、`REPLAY_WORKLOAD_ROOT`、`tab`は
guestの共通初期化、`mount_ok`は呼出し元が設定する。
`expected_file`、`manifest_strict_hash`、`manifest_context`は負対照内で設定し、
marker関連の各値はmanifestの各行を`read`して取得する。
`ack_count`、`manifest_ok`、`manifest_hash_mismatch`、`actual`もchecker内で設定する。
strict hashを指定する負対照では、回復時だけ使うW2の先行更新照合と
W3のtail検査へ入らない。これらに回復経路だけの代入への依存は見つからなかった。
負対照はsubshellなのでcontextとstrict指定は回復経路へ残らない。

旧hostテストも`sh -eu`だったが、`check_manifest_at_point`を
command substitutionにせず直接実行し、`point_entry`を親shellへ残していた。
回帰テストをguestと同じ呼出し方に直し、負対照直前で同変数が未設定であること、
回復・負対照の診断がともに最終点のentryを記録することを検査した。
修正前は1テスト内の5ケースが`point_entry: parameter not set`で失敗し、
修正後は全67テストが成功した。正常・欠損・空集合・各workload・
checkerの検出失敗の既存ケースもこの呼出し方で検査している。

### 試行04の証拠と取得

orphan branch `data/fs-compare-experiments`のcommit
`f2062dd2d978911704c9b49a41e70ed6abc0be2a`に、
`fs-compare/stage4-rerun-1dc14a3-04.tar.zst`を保存した。
928個のtext証拠を原本のまま収録し、image・binaryなど1380 fileは除外した。
memberのhashは同名の`.files.sha256`、除外したpath・size・hashは
同名の`.selection.json`にある。push後にremoteから取得し、
archiveと全928 memberのhashを照合した。

取得には前節と同じく`zstd`、`tar`、`sha256sum`を使う。
新しい保存先で次を実行する。data branchをmergeする必要はない。

```sh
git fetch origin data/fs-compare-experiments
data_sha=f2062dd2d978911704c9b49a41e70ed6abc0be2a
mkdir evidence-1dc14a3-04
git archive "$data_sha" fs-compare/stage4-rerun-1dc14a3-04.tar.zst \
  fs-compare/stage4-rerun-1dc14a3-04.files.sha256 \
  fs-compare/stage4-rerun-1dc14a3-04.selection.json fs-compare/SHA256SUMS |
  tar -xf - -C evidence-1dc14a3-04
cd evidence-1dc14a3-04
grep '  stage4-rerun-1dc14a3-04\.' fs-compare/SHA256SUMS |
  (cd fs-compare && sha256sum -c -)
zstd -dc fs-compare/stage4-rerun-1dc14a3-04.tar.zst | tar -xf -
sha256sum -c fs-compare/stage4-rerun-1dc14a3-04.files.sha256
```

主な一次資料は`build-04-host-result.json`、`representative-04.log`、
`attempt-04-diagnosis.json`と、`rerun-1dc14a3-04/representative/results.csv`、
その下の`08-E1-T1-negative-final/probe-E1-T1-negative-final/qemu-run.log`である。
再試行05は修正後の新しいheadに固定し、fresh build後に単独の
E1・E2/T1-negative-finalを先に診断する計画とする。
両方と既定の代表21件が成功した場合だけ、新しい全851件smokeを開始する。

## 試行05の全smoke停止

実行commitは`12b5c744bb62714284e038ca67f57cb0cface785`。`smoke-coverage.json`は重複なしの85件を収録し、84件が成功、最後の`F1/T1-negative-final`が失敗した。1〜83件に加え、84件目の`F1/T1-final`も成功している。停止した経路は1始まりで85件目、配列indexでは84に当たる。全851件の完了とは扱わない。

guestは次を出して終了値1で停止した。

```text
msd.fscmp: T1_NEGATIVE_FINAL_CHECK stack_open=not_applicable mount=yes fsck=0 manifest=no loss_points=1 negative_control=t1_negative_control_no_present_file
msd.fscmp: error=t1_negative_control_no_present_file
```

`W1/file-000.dat`と`W1/file-001.dat`はともにack=0、fsync省略で、復旧点1048では両方が`reason=missing`だった。mountとfsckは成功している。旧判定器は残存fileだけから改変対照を作るため、対象が0件になった。fsyncしていないfileの消失を、同期済みdataの破損とは扱わない。この試行自体は失敗・中断として残す。

host driver PID `1871398`は終了済み。hostの結果は終了値1、30111.008838891983秒で、guest側QEMUのPID `129987`は`phase-run.json`で`reaped=true`。main runは未開始である。

保全原本は`smoke-05-final/rerun-12b5c74-05-smoke.tar`、SHA-256は`49f6bdbca8f604bc12d1402609e1c9f0732379c2129b9bda791ae3e70cdf594c`。textの写しはorphan branch `data/fs-compare-experiments`のcommit `03b03956647fbc4eb5a8ae07ad914ff5e65811fd`、`fs-compare/stage4-negative-sentinel-01.tar.zst`に保存した。写しのSHA-256は`2129bcac5b560635833015ac8869e3dd4b34a6e654695f232b037eedc7abd6d0`。取得・照合方法と修正後の結果は[sentinel診断記録](2026-11-23-s04-fs-compare-v2-negative-sentinel.md)を参照。このdata branchはmergeも削除もしない。

## 試行06の代表停止

代表10件目E1/T3で停止。既知のWi-Fi用mmc1診断がmarker後に出てfatalになった。206/206 phaseに同じ診断がある。一般のboot区間は維持し、固定環境のwifi-sdioだけをphase内1回に限って許容する。

| verify | 診断行 | 最初のmarker行 |
|---|---:|---:|
| 05代表 | 312 | 318 |
| 05 smoke | 312 | 318 |
| 06代表 | 375 | 317 |

原本`fscmp-v2-stage4-attempt-06-5bb55e9/rerun-5bb55e9-06-failed.tar`のSHA-256は`12a787c8e19965f28b90bde5b90d06c36c65e96c0c5a91bc472ba20202d964d1`。[調査・別出力の再判定・証拠の取得](2026-11-24-s04-fs-compare-v2-wifi-sdio.md)を参照。元結果は変更しない。
