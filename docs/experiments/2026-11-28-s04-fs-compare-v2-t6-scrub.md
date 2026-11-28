# S4参考: T6のBtrfs scrub判定と試行10・11

## 目的と範囲

[第4段A](2026-11-19-s04-fs-compare-v2-stage4.md)の試行10のimage消失と、11のB2/T6誤判定を記録する。
保存logを変えず、修復済みのchecksum診断だけを許容する。全851件の成功や性能改善とは扱わない。
事前の合格条件は同じ6入力・初回driver終了値0で旧判定器のfatal 1件を再現し、
修正後だけstatus=ok、fatal 0件になること。不正な修復証拠や別configを許容しないことも条件とした。
各判定器を1回実行した機能確認であり、反復測定の中央値・最小・最大は出さない。
[生の値](2026-11-28-s04-fs-compare-v2-t6-scrub.csv)はpipeline、probe、再判定を分け、重複加算しない。

## 固定条件

| 項目 | 値・確認範囲 |
|---|---|
| 試行10 source | `9abf1683e32820334e18a898f2a8b351ba259322` |
| 試行11 source | `2087ab7a105dc8949b07ac2b51f0de09bd1d9738` |
| 今回の独立cloneの起点 | `origin/main`の`2907e159e6173e2479f4785e6db49bcdf9d12309` |
| 試行11の開発image | `msd-dev:fscmp-a11`、保存値`sha256:f31cdb6ee5180c308818d5cc73f6c6674a2e4b4834f158dd77db51364b89a3ce` |
| 今回のhost試験image | `msd-dev:work-fscmp-fix`、`sha256:54109435d97055b0f1414d6262b32359797ee0c45c5fee924bef1f6b8530cdce` |
| 原logのQEMU | 11.1.3、raspi3b、1 GiB、icount=off |
| 原logのkernel・compiler | Linux `6.18.64-v8`、GCC `14.3.0`。compilerの自己申告は`Buildroot 2021.11-18033-g83947c7bb6` |
| 今回の再判定host | Linux `7.0.0-44-generic`、Python `3.14.4` |

試行11のplanはfresh出力からのbuild、download cache再利用を指定していた。ccacheの実状態は不明。
今回target build、reconfigure、QEMU再実行はしていない。保存logの再判定にはBuildroot出力を使わない。
試行11のimageは起動も再buildもせず、tag・IDは保存metadataから読んだ。共有tagにも触れていない。

起動logに記録されたQEMU binaryのSHA-256は
`82248f8b0b31dcdc63d59c3f21b1f57a74e3f57346c582d740d33c0e8edcef04`、
kernelは`afee1572c6c59cba891dd487d0ef8b529b8b0e459d1cc64d2555e58e856c372c`。
今回はbinaryを再hashしたのではなく、原logの値を保存した。

## 試行10: image消失でsmoke未開始

fresh build、E1/E2/F1 negative-final、代表21件は終了値0。
buildは3731.3450310230255秒、代表21件は7568.663738965988秒だった。
smokeは0.11519312858581543秒、Docker終了値125で停止した。probeは始まっていない。

```text
docker: Error response from daemon: No such image: sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65
```

根拠は`pipeline/failure-10.json`、`pipeline/smoke-10.log`、
元の`attempt-10-image-loss-investigation.tar.gz`のDocker・build調査記録である。
imageが起動時に存在しなかったことと、誰がどの操作で消したかは分ける。後者は確定していない。
この失敗はguestや判定器の失敗ではない。試行11は専用tagと固定IDを各段で検査し、不在時に自動再buildしない方式へ変えた。

## 試行11: scrub修復後の診断をfatalと誤分類

buildは3488.1633608341217秒、E1/E2/F1と代表21件も終了値0。
代表21件は7361.1178250312805秒だった。
smokeは65696.03935909271秒で停止し、191/851件完了、190成功・1失敗・除外0。
失敗probeはB2/T6、所要311.347秒だった。smokeとprobeの時間は包含関係にある。

原logの該当行は次のとおり。B2はBtrfs DUP構成で、T6はcorruption注入後にscrubで修復する試験である。

```text
431 msd.fscmp: mounted config=B2 base_config=B2 variant_id=none test=T6
437 msd.fscmp: expected_errors_begin kind=T6_corruption
450 msd.fscmp: T6_SCRUB WARNING: errors detected during scrubbing, 1 corrected
458 msd.fscmp: T6_SCRUB Error summary:    csum=1
481 msd.fscmp: T6_SCRUB_RESULT corrected=1 uncorrectable=0
501 msd.fscmp: T6_SCRUB_METRICS corrected=1 uncorrectable=0 repaired=yes
503 msd.fscmp: expected_errors_end kind=T6_corruption
```

旧判定器の`aggregate_errors()`は458行の`Error`をrun/diagnostic/fatalにした。
同じcontextのkernel `scrub: fixed up error`、`corrupt 1`は既存規則でexpectedだった。
phase結果は`returncode=0`、`qmp_quit=true`、`reaped=true`、`marker=true`、
`fallback=[]`、`error=null`。phaseが記録したlog hashも原logと一致した。
初回`result-before-archive.json`はdriver_status=0、fatal 1件。
その失敗をdriverが1で返した後の`result.json`は、process診断も加えてfatal 2件である。
これは独立したguest障害が二つあったという意味ではない。

## 限定修正と回帰試験

[supervisor.py](../../board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py)で、
次の条件をすべて満たす`Error summary: csum=N`だけをexpectedにする。

- test=T6、run phase、`qemu-run.log`だけ。
- mounted行のconfigとbase_configが一致したB1またはB2だけ。
- 完結した同じ`T6_corruption` context内で、summary、RESULT、METRICSがこの順にある。
- RESULTとMETRICSは各1行で、correctedが同じ正整数、uncorrectable=0、repaired=yes。
- summaryの種類はcsumだけ。read、super、verify等との混在、前後の別診断は許容しない。

修復証拠を別contextや別logから借りない。一般的なerror検出、boot allowlist、guestは変えない。
[host試験](../../tests/fs-compare-v2/run.py)にはB1/B2の成功、RESULT/METRICS欠損、
uncorrectable、修復なし、値不整合、別種類、混在、他config、他test/phase/log、
context欠損・未完了・別実行を加えた。guest error、終了marker欠損、非zero終了、hash改変も引き続き拒否する。
保存した実logをbyteのままgzip fixtureに追加し、既存fixtureは変更していない。

固定imageで84試験が成功した。最初のhost試験は修正中の括弧の不整合でSyntaxErrorとなり、
修正後に全件実行した。その失敗logも証拠に残した。
保存logのSHA-256は`b13187e14df44093288f6b9762360a9ebd764b06beda84676aeef486342c59a8`。

### 同じ入力による再判定

元archiveの6入力は`host.log`、`launcher.log`、`supervisor-run.log`、
`qemu-run.log`、`phase-run.json`、`summary.pending.csv`。元の失敗結果は入力へ移さない。
[T7の限定修正](2026-11-26-s04-fs-compare-v2-t7-btrfs.md)と
[grow marker修正](2026-11-26-s04-fs-compare-v2-grow-marker.md)と同じ方法で、初回driver_status=0を双方へ渡した。

| 判定器 | status | driver_status | fatal_errors | CLI終了値 |
|---|---|---:|---:|---:|
| archive内の旧harness | fail:final_judge | 0 | 1 | 1 |
| 修正後 | ok | 0 | 0 | 0 |

旧判定器のSHA-256は`0cb094a1f4727d865f868cc006ae2799a060295ee06ec6bc1d24d1b82a00e7e4`、
修正後は`c632fd2d2d36edff587396cb9fc7195f08c69f2f4581618992010982ab59c349`。
元の試行10・11は失敗のまま保持する。全851件のcoverage、main runの開始を認める結果ではない。

## text証拠の保存先と取得

試行05〜09と同じorphan branch `data/fs-compare-experiments`の固定commit
`25b2726a3625b2d62083813d8c29a67c78c12388`へ保存した。mergeも削除もしない。
通常のGit blobを使い、各archiveは50 MiB未満。全smoke treeではなく、失敗probeとpipelineの選択したtextの写しである。

| 保存先（`fs-compare/`以下） | bytes | SHA-256 | 照合member数 | binary等の除外数 |
|---|---:|---|---:|---:|
| `stage4-attempt-10-text-01.tar.zst` | 270712 | `f5d2f77f48661ed94f72d9f4d1f8e771dde8618e7d86e097c5ae016d23de1e9c` | 993 | 0 |
| `stage4-attempt-11-text-01.tar.zst` | 218136 | `8e7d83a0134a3f4b4cf7044708a91de0275288b7a216fe41bcd203c7985e0510` | 121 | 2 |

`.selection.json`は採用・除外したfileのpath・size・hash・元archiveを、
`.files.sha256`は収録memberのhashを記録する。作成後に全memberを読戻して照合した。
11の`original/probe-B2-T6/`は原本text、`pipeline/`は各段の記録、
`rejudge/`は別出力の旧新再判定、`investigation/`は修正とhost試験の記録。
GPL-2.0原文は`stage4-attempt-10-11.licenses.txt`に付す。imageやDTB本体は保存しない。

元archiveのSHA-256も記録する。原本は書き換えていない。

| 元archive | SHA-256 |
|---|---|
| `attempt-10-smoke-failure-inputs.tar.gz` | `145ab01c2d71202d460d3f8e0b23f6339a607f6bbd2a1f7dc993c206e6ec8637` |
| `attempt-10-image-loss-investigation.tar.gz` | `1aa4b354cdb828c995d3613db3fb1c0c45f110a08fb487144d16f14c5fa605f8` |
| `attempt-11-smoke-failure-B2-T6.tar.gz` | `35e202d794161ae2ad27c060c2bd4477c80caf693aac75c3ceb843563c64833a` |

以下は修正後checkoutのrootで実行する。Python 3.14の`compression.zstd`を使う。
出力先が既にあれば停止する。

```sh
set -eu
git fetch origin data/fs-compare-experiments
data_sha=25b2726a3625b2d62083813d8c29a67c78c12388
mkdir evidence-t6
git archive -o evidence-t6/data.tar "$data_sha" \
  fs-compare/stage4-attempt-10-text-01.tar.zst \
  fs-compare/stage4-attempt-10-text-01.files.sha256 \
  fs-compare/stage4-attempt-10-text-01.selection.json \
  fs-compare/stage4-attempt-11-text-01.tar.zst \
  fs-compare/stage4-attempt-11-text-01.files.sha256 \
  fs-compare/stage4-attempt-11-text-01.selection.json \
  fs-compare/stage4-attempt-10-11.licenses.txt fs-compare/SHA256SUMS
tar -xf evidence-t6/data.tar -C evidence-t6
rg '  stage4-attempt-1[01]' evidence-t6/fs-compare/SHA256SUMS > evidence-t6/checksums
(cd evidence-t6/fs-compare && sha256sum -c ../checksums)
python3 - <<'PY'
from compression import zstd
from pathlib import Path
import tarfile
for attempt in ("10", "11"):
    target = Path(f"evidence-t6/unpacked-{attempt}")
    target.mkdir()
    with zstd.open(f"evidence-t6/fs-compare/stage4-attempt-{attempt}-text-01.tar.zst", "rb") as stream:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            archive.extractall(target, filter="data")
PY
for attempt in 10 11; do
  (cd "evidence-t6/unpacked-$attempt" &&
    sha256sum -c "../fs-compare/stage4-attempt-$attempt-text-01.files.sha256")
done
```

取得・照合後、次で両判定を再現する。oldの終了値1は比較対象の期待値である。

```sh
set -eu
source=evidence-t6/unpacked-11/original/probe-B2-T6
mkdir rejudge-t6
for version in old new; do
  mkdir "rejudge-t6/$version"
  out="rejudge-t6/$version/probe-B2-T6"
  mkdir "$out"
  for file in host.log launcher.log supervisor-run.log qemu-run.log phase-run.json summary.pending.csv; do
    cp "$source/$file" "$out/"
  done
  judge="$source/evidence/harness/supervisor.py"
  if [ "$version" = new ]; then
    judge=board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py
  fi
  status=0
  python3 "$judge" finalize "$out" T6 0 || status=$?
  printf '%s exit=%s\n' "$version" "$status"
  cat "$out/result.json"
done
```

修正後の新しいQEMU試行、全smoke、main run、実SD/FTL、実電源断、LCD・keyboardは未実施。
PR Cの作業状態は保存したままで、この判定器修正には含めない。
