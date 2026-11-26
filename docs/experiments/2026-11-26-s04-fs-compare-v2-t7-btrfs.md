# S4: 試行07のhost中断と試行08のT7誤判定

[実験索引](README.md) / [第4段A](2026-11-19-s04-fs-compare-v2-stage4.md) / [CSV](2026-11-26-s04-fs-compare-v2-t7-btrfs.csv)

## 目的・条件・採否

試行07と08の失敗を区別し、試行08で正常なBtrfs診断を拒否した判定器を直す。
元の失敗結果、log、archive、実行用cloneは変更しない。
採否は、T7のrun phaseでbtrfsの正常出力が全文一致する場合だけ許容し、
本当のerror、正常行との混在、marker欠損、非zero終了、log hash不一致を拒否すること。
`no error`を含む行全般の許容には広げない。

元log 1組に旧・新の判定器を各1回適用する。同じ入力の機能確認なので、
時間測定の5回反復は行わない。buildとQEMUを再実行せず、実機性能や電断耐性の値にはしない。

- 元試行のcommit: `ab0eec727c0dce6b6dd6d49c42de4721237d0646`。
- 修正branchの起点: `4343c134a6eae7b3858d6d99e1d143e9e9d0cb09`。
- 試行08はfresh build、共有ccacheなし。QEMU 11.1.3、raspi3b、1G、icount off。
- 再判定は保存済みtextだけを使い、build treeとimageを使用しない。
- 再判定hostはLinux 7.0.0-44-generic x86_64、Python 3.14.4。
- B1は暗号化なしのBtrfs、metadata DUP、data SINGLE、crc32c。
  LUKS2+BtrfsのB5とは区別する。

## 試行07: B1/T6のhost中断

smokeは174件成功後、175件目のB1/T6で停止した。driver statusは143。
EXIT cleanupがabortを要求し、supervisorがQEMUへSIGTERMを送った。
finished markerはなく、guestのT6判定へ到達していない。分類はhost側の中断であり、
製品やfilesystemの異常を示したものではない。

2026-11-25 08:34 JSTの中断付近でapt更新があったが、元のSIGTERM送信元と
更新からsignalへの因果関係は未確認。実際のDocker endpointはrootlessで、
dockerdとcontainerdは11月22日起動のままだった。system側の再起動処理だけを根拠に、
実際のdaemonが再起動したとは扱わない。権限の必要なsystem logも確認できなかった。

同じsource、binary、config、QEMUを使い、別runでB1/T6だけを再実行した結果は成功。
child statusは0、probeは307.950472秒、host全体は311.405499秒だった。
これは機能の再確認であり、CM0の性能値ではない。元の175/851失敗は変更していない。
共有filesystem上で保全も同時実行したため、空き容量の差をrun単体の容量とは扱わない。

## 試行08: B1/T7の誤判定

同じcommitの新しいfresh buildで、先行診断と代表を経てsmokeを実行した。
1から175件目まで成功し、B1/T6も成功。176件目のB1/T7で停止した。
main runは開始していない。

T7はimageを確保してdirect I/Oのloopへ接続し、setup、format、mount、
MemAvailable採取、umount、readonly fsck、必要な暗号stackのclose、loop切断を行う。
通常は4 GiB、smokeは256 MiB。Btrfsの検査は`btrfs check --readonly`である。
実装は`board/cardputerzero/tools/bench/fs-compare-v2/fs-compare-guest`の
`run_t7()`と`run_timed_step()`を参照。

保存した`probe-B1-T7/qemu-run.log`の生の行を示す。

```text
428: msd.fscmp: TIMER command=btrfs elapsed_ns=962362768 status=0
439: msd.fscmp: T7_STEP command=btrfs found 147456 bytes used, no error found
448: msd.fscmp: T7_FINISHED filesystem=btrfs bytes=268435456
449: msd.fscmp: finished
```

`errors.txt:18`は439行目を`[run/diagnostic/fatal]`とした。
`supervisor.py`の`aggregate_errors()`が`no error found`中の`error`に一致するためである。
bytes usedが非zeroであることを失敗条件にしているわけではない。
元logの441行目はtreeが147456 bytes、445行目はfile dataが0だった。

初回の`result-before-archive.json`はdriver_status=0、fatal_errors=1。
phaseはreturncode=0、mode=normal、qmp_quit=true、fallback=[]、error=null、marker=trueで、
`summary.pending.csv`もokだった。最終のdriver_status=1とfatal_errors=2は、
誤判定による終了値1を保存時の再走査が追加したもの。別々の異常2件とは扱わない。
`host.log:0`という診断も集計器の生成行で、SIGTERMの証拠ではない。

分類は**試験器の欠陥**。guestの検査失敗やhost側の中断ではない。
元logを同じ関数へ渡すとfatal 1、問題の正常行だけを除いた写しではfatal 0だった。
使用量を0とした正常行でも旧判定器はfatalにするため、非zero使用量が原因という仮説は棄却した。

### host事象・他のT7・履歴

QEMU logの最終mtimeは2026-11-26 04:54:09.496 JST、初回判定のmtimeは04:54:10.633、
launcherの終了は04:55:31.509、終了値1。mtimeは保存時刻であり、guest内のwall clockではない。
04:25:31から05:25:31までのapt historyとdpkg logには更新記録がなく、
最も近いapt更新は06:04:48から49のlibsqlite3更新だった。
rootless Docker unitは11月22日起動、NRestarts=0で、daemonのprocess開始時刻も同時期。
読めるjournalの04:55:31のscope終了・shim cleanupは初回判定より後である。
他userとsystem全体のjournal、dmesg、apt term.log、syslog、kern.logは権限不足で未確認。
host全体の異常不在は断定しないが、今回の失敗は正常終了後の誤判定だけで説明・再現できる。

試行08のE1からE5、F1からF5のT7は全件成功。B2以降はB1/T7での停止により未実行。
保存済み試行05のsmokeは85件目F1/T1-negative-final、07は175件目B1/T6で止まっており、
B1/T7に未到達だった。手元のstage4結果と保存済みcoverage等を調べ、summary.csvを568件読んだ範囲では
B1/T7は今回の1件だけ。削除済み・未取得の実行まで不存在とするものではない。

## 修正と別出力での再判定

`aggregate_errors()`に、testがT7、phaseがrunで、次の正規表現に全文一致する行だけを
expectedとする条件を加えた。許容行も原文と行番号をerrors.jsonlに残す。

```text
msd\.fscmp: T7_STEP command=btrfs found [0-9]+ bytes used, no error found
```

guest error、kernel fatal、QEMU errorの分類は優先する。終了状態、回収、marker、log hash、
pending summaryの検査は変更していない。verify、host、T6、別command、別prefix、末尾error追記は許容しない。
既存の`tests/fs-compare-v2/run.py`に回帰を追加した。
このsuiteは既に`.github/scripts/run-host-tests.py`の`SUITES`に登録されており、
同runnerの`run()`を経由して実行した。runner自体への変更は不要だった。
結果は74テスト成功。実際の正常行と使用量0、別の使用量を受理し、
本当のBtrfs error、正常行との混在、guest error、marker欠損、非zeroのphase・driver status、
log hash不一致、空logを拒否した。別test、phase、command、prefixと末尾追記の拒否も検査した。

原本archiveのSHA-256を照合し、初回判定のdriver_status=0を旧・新の両方に与えた。
archive後の1を再入力すると、誤判定自身が生んだ終了値を引き継いでしまう。
host.log、launcher.log、supervisor-run.log、qemu-run.log、phase-run.json、summary.pending.csvの
6入力をbyte一致で別directoryへ複写した。旧判定器もarchive内の保存済みharnessを使った。

```text
baseline status=fail:final_judge driver_status=0 fatal_errors=1
candidate status=ok driver_status=0 fatal_errors=0
Original archive unchanged; six inputs byte-identical; no smoke clone access; no QEMU rerun
```

元phase logのSHA-256は`21872c6820a0b893520ea42a512069c6ca483681bd944be3965ad32abb7363a8`。
再判定に使った修正後supervisorのSHA-256は
`a9ebfa868a96c3ec082aa85c1a955c45205def7ad0dbf5ad58ab090168f97d2f`。
原本archiveのhashは再判定後も一致した。これはhost判定器の再検査で、試行08自体の成功への変更ではない。

## 保存物と限界

下表は非画像のtext証拠。SHA-256を記録し、別directoryへ展開してmemberを照合した。
image本体は含めず、path・size・hashだけを記録した。保存済みarchiveはこの修正branchには含めない。
一次資料は各archiveのhost結果、phase結果、qemu log、coverage、manifest、調査JSONである。

| 試行 | archive名 | SHA-256 |
|---|---|---|
| 07 原本text | `attempt-07-smoke-failed-text-only.tar.gz` | `f731ca3c62aba8483216aa02de428efada983428a5098cc20ac11909abc99352` |
| 07 単独再実行・host調査 | `attempt-07-b1-t6-diagnostic-and-host-facts.tar.gz` | `878c7b305b17243c7655a381dd07b221fdd516f4505ff675de92cc94fd3bdc25` |
| 08 原本text | `attempt-08-smoke-failed-text-only.tar.gz` | `8738e97de0fe5104c36beba3e4049eec29bb5da21535f730197d17cc6eb7e75a` |
| 08 判定器・host調査 | `attempt-08-b1-t7-investigation-and-host-facts.tar.gz` | `823e8f1e80c458a21dd8d64cbe02f98383d6f5f0500aa99cf25b0e00ce8b8d74` |

試行08の原本textは10,047 fileと元manifest 176件、展開照合は10,231 regular file。
元textのhash・mtimeも一致した。image記録359件のうち352件は試験器が削除済みのimageについての
元manifestの値であり、今回の再hashではない。現存する参照build image 7件は再hashした。
その他binary 203件は本体を除外してmetadataを記録。調査tarの49 memberも展開して照合した。

### 保存先と取得方法

試行05・06と同じorphan branch `data/fs-compare-experiments`にtextの写しを保存した。
固定commitは`b898e1a83cd4b6c4a6f0028a1b347cb4e0672fbf`。data branchはmergeも削除もしない。
各試行の原本textに、その試行の調査tarの内容を`investigation/`以下として加えた。
元の4つのgzip archiveは変更せず、そのhashを同名`.selection.json`にも記録した。
展開済みbuild rootfsのfirmware設定を除外し、原本と同じbyteのtextだけを再packした。
除外fileのpath・size・hash・理由も同JSONに残す。image本体は含まない。

| data branch内の保存先 | bytes | SHA-256 | 照合したmember数 | 除外数 |
|---|---:|---|---:|---:|
| `fs-compare/stage4-attempt-07-text-01.tar.zst` | 3478327 | `c4e289af8581413dee3bbad1d1bb3bcde3cb4a3e6a0ddcd1d0a0268fa7fba184` | 14323 | 800 |
| `fs-compare/stage4-attempt-08-text-01.tar.zst` | 1489533 | `d3380db640ba5e68d58f7d37d789e4f0f7cffcb910781696c624a91af2994cce` | 9576 | 704 |

前例と同じ通常のGit blobで、LFSは使わない。圧縮後は各50 MiB未満である。
memberごとのhashは`.files.sha256`、archiveとsidecarのhashは`fs-compare/SHA256SUMS`、
収録した本repo sourceのGPL-2.0原文は`fs-compare/stage4-attempt-07-08.licenses.txt`に付す。
以下は修正後checkoutのrootで実行する。出力先が既にあれば停止する。

```sh
set -eu
git fetch origin data/fs-compare-experiments
data_sha=b898e1a83cd4b6c4a6f0028a1b347cb4e0672fbf
mkdir evidence-t7
git archive -o evidence-t7/data.tar "$data_sha" \
  fs-compare/stage4-attempt-07-text-01.tar.zst \
  fs-compare/stage4-attempt-07-text-01.files.sha256 \
  fs-compare/stage4-attempt-07-text-01.selection.json \
  fs-compare/stage4-attempt-08-text-01.tar.zst \
  fs-compare/stage4-attempt-08-text-01.files.sha256 \
  fs-compare/stage4-attempt-08-text-01.selection.json \
  fs-compare/stage4-attempt-07-08.licenses.txt fs-compare/SHA256SUMS
tar -xf evidence-t7/data.tar -C evidence-t7
grep '  stage4-attempt-0' evidence-t7/fs-compare/SHA256SUMS > evidence-t7/checksums
(cd evidence-t7/fs-compare && sha256sum -c ../checksums)
for attempt in 07 08; do
  mkdir "evidence-t7/unpacked-$attempt"
  zstd -dc "evidence-t7/fs-compare/stage4-attempt-$attempt-text-01.tar.zst" > "evidence-t7/attempt-$attempt.tar"
  tar -xf "evidence-t7/attempt-$attempt.tar" -C "evidence-t7/unpacked-$attempt"
  (cd "evidence-t7/unpacked-$attempt" && sha256sum -c "../fs-compare/stage4-attempt-$attempt-text-01.files.sha256")
done
```

### 再判定の手順

上の取得・照合を終えてから、修正後checkoutのrootで次を実行する。
既存の出力先は上書きしない。元archiveから入力だけを取り出し、既存の失敗結果は移さない。
終了値0は初回の`result-before-archive.json`に記録されたdriver_statusである。

```sh
archive=evidence-t7/fs-compare/stage4-attempt-08-text-01.tar.zst
printf 'd3380db640ba5e68d58f7d37d789e4f0f7cffcb910781696c624a91af2994cce  %s\n' "$archive" | sha256sum -c -
mkdir rejudge-t7
out=rejudge-t7/probe-B1-T7
mkdir "$out"
prefix=run/attempt-1795577395970912517/probe-B1-T7
tar --zstd -xf "$archive" -C "$out" --strip-components=3 \
  "$prefix/host.log" "$prefix/launcher.log" "$prefix/supervisor-run.log" \
  "$prefix/qemu-run.log" "$prefix/phase-run.json" "$prefix/summary.pending.csv"
python3 board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py finalize "$out" T7 0
cat "$out/result.json"
```

元の07・08は失敗のまま保持する。今回の修正後のQEMU単独再実行、全851件smoke、main run、
実機のSD・FTL・電断・LCD・keyboardは未実施。
次は新しいrunでB1/T7を確認してから他のBtrfs構成と全smokeへ進む。
