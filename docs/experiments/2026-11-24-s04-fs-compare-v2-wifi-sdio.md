# S4: 試行06のWi-Fi SDIO診断と別出力での再判定

[実験索引](README.md) / [第4段A](2026-11-19-s04-fs-compare-v2-stage4.md) / [CSV](2026-11-24-s04-fs-compare-v2-wifi-sdio.csv)

## 目的・条件・採否

試行06の代表E1/T3を落とした判定を調べ、既知のQEMU診断だけを許容する。元の失敗結果、log、archiveは変更しない。採否の条件は、固定環境で完全一致するwifi-sdio行をphase内1回だけ許容し、重複・未知環境・別device・その他のerrorを拒否すること。一般のboot許容区間は最初の`msd.fscmp:`で閉じる条件を維持する。

固定log 1組に対して旧・新の判定器を各1回実行する。同じ入力で結果が決まる判定器の比較なので、5回の時間測定は行わない。buildとQEMUは再実行せず、性能・durabilityの新しい値にはしない。

- 元の固定commit: `5bb55e96cb7d9dac1d9143518e1bbf7e8929ab64`。
- 修正commit: `4a7931b321a0ff2813cd0151bf8336f87f90778d`。
- QEMU: 11.1.3、raspi3b、1G、icount off。binary SHA-256: `8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73`。
- kernel: 6.18.64-v8、source `a40f735325391b1705161b07f36ed45e1bf04521`。GCC 14.3.0、binutils 2.43.1。元試行はfresh build。再判定はbuild出力を使わない。
- 再判定host: Linux 7.0.0-44-generic x86_64、Python 3.14.4。host回帰は固定の`docker/msd-dev`で実行。

## 元の失敗と原因

fresh buildとE1・E2・F1のnegative-final先行診断は成功。代表21件は1〜9件目成功、10件目E1/T3で停止し、11〜21件目、851件smoke、main runは未開始。pipeline PID 3401324は終了済み。

保存DTBのaliasは`mmc0=/soc/mmc@7e202000`、`mmc1=/soc/mmcnr@7e300000`。後者は有効かつnon-removableのWi-Fi SDIO hostである。QEMUは1個のSD cardをGPIO mux経由でSDHOSTへ接続し、Wi-Fi deviceは作らない。guestではimageが`mmc0`・`mmcblk0`として列挙されている。

固定kernelの`drivers/mmc/core/core.c:2265〜2349`は非同期workでSDIO・SD・MMCを試し、non-removableなのにbusが登録されなければ対象行を出す。userspace開始との同期はない。`bcm2835-mmc.c`のcommand timerによるtimeout行も先行している。各commandやhost schedulingが時刻差へ与えた寄与は未追跡である。

既知診断の規則は#283の`8eab8b6`で追加されたが、許容区間を最初の`msd.fscmp:`で閉じていた。#287 `82c7284`、#288 `c59321b`、#301 `5bb55e9`の全てで今回の行はfatalになった。#288のserial分離修正はこの終了条件を変えていない。終了条件だけをメモリ上で外す反証確認ではfatalが1から0になった。

**原因は判定器の誤分類**。verifyの317行目のSMOKE_PROFILEで区間が閉じ、375行目が一般の`failed`規則へ落ちた。run側の同じ行は`known_boot=wifi-sdio`で許容されていた。guestの記録は次のとおり。

```text
msd.fscmp: recovery_fsck=0
msd.fscmp: recovery_mount=ok
msd.fscmp: T3_DISK last_seq=10 monotonic_ns=177823795600
msd.fscmp: T3_FSYNC_LOST count=0
```

元の`result-before-archive.json`はdriver_status=0、fatal_errors=1。最終判定の終了値1を受けたarchive時の再走査が、`driver exit status=1`を追加した。driverとguestが別々に異常終了したという意味ではない。

## 出現数・出現位置

`qemu-run.log`と`qemu-verify.log`を対象に、同一内容のコピーをSHA-256で除外した。206種類全てに1行ずつあり、最初のmarkerより後だったものは今回のverifyだけだった。206種類の原logとhash、別名一覧をtext証拠に保存した。

| 対象 | phase log | 診断行 | markerより後 |
|---|---:|---:|---:|
| 比較可能な履歴全体 | 206 | 206 | 1 |
| 試行05・先行診断 | 2 | 2 | 0 |
| 試行05・代表 | 23 | 23 | 0 |
| 試行05・smoke | 95 | 95 | 0 |
| 試行06・先行診断 | 3 | 3 | 0 |
| 試行06・代表 | 12 | 12 | 1 |

T2・T3はrunとverifyの2 phaseを持つためprobe数とlog数は一致しない。各行の集団は互いに重なるため合算しない。元archiveでも05のsmokeは95/95行、06は15/15行と確認した。

| E1/T3 verify | kernel時刻（秒） | 診断行 | 最初のmarker行 | 元結果 |
|---|---:|---:|---:|---|
| bootfix-04・代表 | 6.348661 | 299 | 326 | ok |
| bootfix-04・smoke | 16.917942 | 321 | 327 | ok |
| 試行05・代表 | 16.384711 | 312 | 318 | ok |
| 試行05・smoke | 15.760728 | 312 | 318 | ok |
| 試行06・代表 | 26.439258 | 375 | 317 | fail:final_judge |

bootfix-04はQEMU 11.1.2／kernel 6.18.59-v8、05と06は11.1.3／6.18.64-v8。成功例でも同じ診断が出ており、今回の初出ではない。

広域調査は25,304の候補logとSHA重複除外後466種類のarchiveを検索した。serial log内容5,365種類中4,737種類に計6,298行があったが、結合logとphase原本が重なるため独立した起動回数にはしない。ZIPとして読めなかった`output-dev-image-snapshot/pr229-arm64.zip`と`handoff/pr209/q.zip`、削除済み・未取得のCI logは未確認である。

## 修正と別出力での再判定

`supervisor.py`は固定のQEMU・kernel・raspi3b・model・SMOKE profileとphase専用log名を確認する。timestampを外して完全一致する`mmc1`行だけをphase全体で1回許容する。2回目はfatalとし、runとverifyは別に数える。一般の既知診断は従来どおりmarker前だけに限る。既知環境ではmarker後もserial断片を分離し、混在した別errorを独立して判定する。許容した原文・行番号・理由・出典をerrors.jsonlに残す。

原本の`result-before-archive.json`にあるdriver_status=0を旧・新の両方に使った。archive後の1を使うと判定器自身が発生させた終了値まで再入力することになる。原本から入力10 fileをそれぞれ別の新規directoryへbyte一致で複写し、旧・新のfinalizeを実行した。

```text
baseline status=fail:final_judge driver_status=0 fatal_errors=1
candidate status=ok driver_status=0 fatal_errors=0
Original 15 input/result files unchanged; run/verify log hashes identical; no QEMU rerun
```

これは判定器のhost再検査であり、試行06は失敗のまま残す。QEMUの再起動、新しい代表21件、全851件、main run、実機のSDIO・電断・表示は未実施。

回帰試験は70件成功。marker前、SMOKE_PROFILE後、environment_ok後、未知のQEMU・kernel・machine・model、SMOKE欠損、mmc0・mmc2・別error・末尾追記、host log、同一phase内の重複、run/verify別集計、同じ物理行の混在と重複、断片化した別error、一般診断の区間終了を検査した。空logの既存試験も維持する。

## 証拠の取得と再現

原本archiveの識別pathは`fscmp-v2-stage4-attempt-06-5bb55e9/rerun-5bb55e9-06-failed.tar`、SHA-256は`12a787c8e19965f28b90bde5b90d06c36c65e96c0c5a91bc472ba20202d964d1`。

textの写しはorphan branch `data/fs-compare-experiments`の`fs-compare/stage4-wifi-sdio-late-01.tar.zst`に保存した。data branchはmergeも削除もしない。SHA-256は`30a4b298456c3e33ede77ad94ab03970e673f8f6b09c4d5c0a11bc5e0857220f`。1472 memberのbyte・hashを原本と照合した。image、build tree、共有poolは除外し、追加で除外した非UTF-8等の候補2661 fileは`selection.json`に記録した。kernelの未改変sourceのライセンスは同名`.licenses.txt`に付す。

push後にremoteから取得し、archive・member manifest・ライセンスの3 hashと全1472 memberのhashを再照合した。取得した入力とscriptでも旧fatal 1、新0を再現した。

新しい保存先で次を実行する。data branchをmergeする必要はない。

```sh
git fetch origin data/fs-compare-experiments
data_sha=f425e593d528a80bd50f8e7118facdb577f3fbc8
mkdir evidence-wifi-sdio
git archive "$data_sha" fs-compare/stage4-wifi-sdio-late-01.tar.zst \
  fs-compare/stage4-wifi-sdio-late-01.files.sha256 \
  fs-compare/stage4-wifi-sdio-late-01.licenses.txt fs-compare/SHA256SUMS |
  tar -xf - -C evidence-wifi-sdio
cd evidence-wifi-sdio
grep '  stage4-wifi-sdio-late-01\.' fs-compare/SHA256SUMS |
  (cd fs-compare && sha256sum -c -)
mkdir unpacked
zstd -dc fs-compare/stage4-wifi-sdio-late-01.tar.zst | tar -xf - -C unpacked
(cd unpacked && sha256sum -c ../fs-compare/stage4-wifi-sdio-late-01.files.sha256)
```

再判定scriptは`unpacked/maintenance/rejudge.py`、入力は`unpacked/attempt-06/run/representative/10-E1-T3/probe-E1-T3`。旧・新それぞれのcheckoutを用意し、新しい出力先を指定する。

```sh
python3 unpacked/maintenance/rejudge.py "$NEW_CHECKOUT" "$OLD_CHECKOUT" \
  unpacked/attempt-06/run/representative/10-E1-T3/probe-E1-T3 replay-new
```

旧は`5bb55e9`、新は`4a7931b`に固定する。`maintenance/rejudge/comparison.json`に入力hash・原結果・両判定を、`maintenance/tests.log`にhost試験出力を、`history/inventory.json`に206 logの照合根拠を収録した。
