# S4: 試行09のE1 grow完了行の誤判定

[実験索引](README.md) / [第4段A](2026-11-19-s04-fs-compare-v2-stage4.md) / [CSV](2026-11-26-s04-fs-compare-v2-grow-marker.csv)

## 目的・条件・採否

試行09は2026-11-26 13:25 JST、E1のnegative-final先行診断で停止した。
原因は試験器の誤判定で、guestのgrow失敗やhost中断ではない。
正常な完了行の表記だけを修正し、既存の限定条件を保つ。
元のclone・runは参照せず、許可された2つのarchiveを読み取り専用で別directoryへ複写した。
以後の展開・再判定・保存は写しだけで行い、原本の失敗結果は変更しない。

採否は、現行の英語行と旧い日英併記の行を全文一致で受け付け、完了行の欠損、grow行なし、
本当のgrow失敗、非zero終了を拒否すること。QEMU環境、起動中、直前のpartition 4/7 grow行、
phase、終了marker、log hashの条件は緩めない。
保存したE1の同じ6入力を旧・新の判定器へ各1回渡し、新だけが`ok`になることを確認する。
性能測定ではないので5回反復は行わず、QEMUも再実行しない。

| 項目 | 値 |
|---|---|
| 試行09と修正branchの起点 | `e478fde1c2dc5bbe459154418e9c79deef5ad8bb` |
| 元の構築 | fresh build成功。今回の再判定ではbuild tree・ccacheを使わない |
| QEMU | 11.1.3、raspi3b、1G、icount off |
| QEMU binary SHA-256 | `8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73`（`qemu-run.log:4`） |
| kernel / target GCC | 6.18.64-v8 / 14.3.0（`qemu-run.log:9`） |
| 元の構築設定・入力hash | `run/early-e1-negative-final/environment.json`とattempt内の`evidence/environment.json` |
| host | 元調査のapt・dpkg・Docker・disk記録を再読。OS版は保存資料では未確認 |
| 元の診断 | E1 / T1-negative-final、386.91414464398986秒、child_status=1 |
| 今回変えるもの | supervisorの完了行の許容集合だけ。入力6 fileはbyte一致 |

## 原因と根拠

以下の行番号は、保存した`run/early-e1-negative-final/probe-E1-T1-negative-final/`内の原logを指す。
`qemu-run.log`のSHA-256は`9d9f48d3ee4204a87f629c0fd324aee43d98a53ad404d3d7b76a5a1a112e3b09`。

```text
315 msd-data-grow: extending partition 4 to the end of /dev/mmcblk0
316 Re-reading the partition table failed.: Device or resource busy
317 msd-data-grow: extending partition 7 to the end of /dev/mmcblk0
318 Re-reading the partition table failed.: Device or resource busy
326 [  149.787368] EXT4-fs (mmcblk0p7): resized filesystem to 1925120
327 The filesystem on /dev/mmcblk0p7 is now 1925120 (4k) blocks long.
329 msd-data: setup synchronized
```

旧判定器は完了行を`msd-data: setup synchronized / 初期設定の同期が完了しました。`だけに限定していた。
現行の[S02msd-data](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)は英語行だけを出す。
保存済みharnessと固定commitの判定器・規則が一致することは元調査で照合済みである。
`investigation/analysis-09/classifier-gates.json`では316・318行とも、
`boot=true`、`grow_pending=true`、`grow_complete=false`だった。
つまり、既知のgrow再読込警告のpatternと環境条件は成立し、完了行の条件だけが外れた。
`errors.txt:16–17`はこの2行を`run/diagnostic/fatal`と記録している。

別の原因を切り分ける対照として、元調査では写しの完了行だけを旧表記へ置換するとfatalが2から0になった。
完了行を消すと2、本当のguest errorを足すと1である。
今回も行を削除せず、同じ入力を修正後の判定器へ渡してfatalが0になることを確認した。

### guestと終了状態

`qemu-run.log:311–314`ではfsckのclean表示後に`/data`をrw mountし、319–327行でresizeを完了した。
428–430行のmanifest不一致は、negative controlの期待範囲内である。

```text
434 msd.fscmp: T1_NEGATIVE_FINAL_CHECK stack_open=not_applicable mount=yes fsck=0 manifest=no loss_points=1 negative_control=yes
438 msd.fscmp: T1_NEGATIVE_CONTROL loss_detected=yes
439 msd.fscmp: finished
```

436–437行の`mount_fail=0`、`fsck_fail=0`、`loss_points=1`は意図した損失検出を示す。
`FSYNC_LOST`行はなく、CSVの`fsync_lost`も空欄。T3ではないため0に読み替えない。
`phase-run.json`は`returncode=0`、`qmp_quit=true`、`reaped=true`、`marker=true`、
`fallback=[]`、`error=null`で、保存されたlog hashも一致した。

初回の`result-before-archive.json`は`driver_status=0`、`fatal_errors=2`、`fail:final_judge`。
その失敗をdriverが1で返し、保存時の再集計が`host.log:0`へ`driver exit status=1`を加えたため、
最終の`result.json`はfatal 3件になった。独立したhost障害ではない。
親の`diagnostic.json`は`ok=false`、`child_status=1`で、`pipeline/e1-09.log`には
`diagnostic failed; no coverage certificate issued`が残る。
代表21件と851件smokeは始まっておらず、元試行にcoverage証明はない。

## host確認と過去事例

対象時間帯は11月26日12:40–13:25 JST。以下は新しいhost測定ではなく、保存済み調査記録の再確認である。

| 記録 | 確認結果・限界 |
|---|---|
| apt / dpkg | 対象時間帯は0件。直近の更新は06:04:48–06:04:58 |
| rootless Docker | 11月22日22:42から起動、`NRestarts=0`。対象時間帯のdaemon再起動記録なし |
| Docker journal | 13:18・13:20にnetwork namespaceの権限警告あり。containerの終了処理は13:25:08 |
| 当時のdisk | `diagnostic.json`の空きは前124,553,359,360、後124,315,615,232 bytes |
| 調査時のdisk | 22:07 JST採取、空き107,571,814,400 bytes、inode使用40%。連続監視値ではない |
| kernel記録 | `dmesg: read kernel buffer failed: Operation not permitted`。kernel/system journal全体も権限で確認できない |

元調査が保存したmtimeは、QEMU logが13:23:29.446、phase正常終了記録が13:23:29.802、
初回final judgeが13:23:30.128。container終了処理より先に判定が失敗している。
mtimeはguest各行のhost時刻ではない。host全体が無異常とは断定しないが、停止原因は判定器だけで再現する。

| 試行 | 今回との違い |
|---|---|
| [06](2026-11-24-s04-fs-compare-v2-wifi-sdio.md) | Wi-Fi SDIOの誤分類。09のSDIO行は`errors.txt:15`でexpected |
| [07](2026-11-26-s04-fs-compare-v2-t7-btrfs.md) | B1/T6のhost SIGTERM。09はQMP quitで正常終了 |
| [08](2026-11-26-s04-fs-compare-v2-t7-btrfs.md) | B1/T7の`no error found`の誤分類。09はT1起動時の完了行不整合 |
| 09 | 同じ試験器の誤判定という分類だが、直接原因は新しいgrow markerの不一致 |

## 修正・回帰試験・再判定

[supervisor.py](../../board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py)は、現行の英語行と旧い日英併記の行だけを明示的に許容する。
既存のQEMU環境・run/verify phase・起動中・直前のpartition 4/7 grow行・完了行存在の条件は変更しない。
製品shellと単独実行するPython判定器の間に実行時の依存を増やさず、
[host試験](../../tests/fs-compare-v2/run.py)で現行markerとS02の出力命令の一致を検査する。

host試験には両表記の正常例、欠損・類似行・growなし・誤partition・間にuserspace処理・
grow失敗・終了marker欠損・非zeroのphase/driver終了・hash不一致・環境違い・起動後・空logの拒否を加えた。
保存したE1の実logはgzip fixtureとしてbyteを変えずに収録し、修正後のfinal judgeへ渡す。
固定開発imageで78試験が成功した。新fixtureの初回試験はCRLFをLF前提で検索して失敗したため、
原logを変えず、存在確認だけを`splitlines()`へ直した。host直接実行でのC workloadのコンパイル失敗は、固定開発imageで解消した。

6入力は`host.log`、`launcher.log`、`supervisor-run.log`、`qemu-run.log`、`phase-run.json`、`summary.pending.csv`。
初回の`driver_status=0`を旧・新双方へ渡した。元の失敗結果と集計済みCSVは入力へ移さない。

| 判定器 | status | driver_status | fatal_errors |
|---|---|---:|---:|
| 保存済み旧harness | fail:final_judge | 0 | 2 |
| 修正後 | ok | 0 | 0 |

## archiveの保存先と取得

元のgzip archiveのSHA-256は次のとおり。いずれも変更せず、写しのhashを照合して使った。

| archive | SHA-256 |
|---|---|
| `attempt-09-e1-negative-final-text-only.tar.gz` | `c1ed683aafeea867ebbf003b3eba2e5a4a79195df12909342eeb5df0c55690cd` |
| `attempt-09-e1-investigation-and-host-facts.tar.gz` | `90933411e639840a1fc67d7e0c984fc52e954a6372c3a7b881aa5d076d92a63a` |

試行07・08と同じorphan branch `data/fs-compare-experiments`の固定commit
`f64185d320339b5fca4adf088eb1b148cc664792`にtextを保存した。data branchはmergeも削除もしない。
保存先は`fs-compare/stage4-attempt-09-text-01.tar.zst`、304,817 bytes、SHA-256は
`70aec2eed8de39de5e76b2e852bcd80463eaad67d65a16cfec540d83058d291b`。
通常のGit blobで50 MiB未満。LFSは使わず、image binaryは収録しない。

原本textに調査tarの内容を`investigation/`以下として加えた。
前例と同じく展開済みrootfsのfirmware設定4 fileを除外し、118 memberのbyte一致とhashを照合した。
元archiveのhash、収録・除外fileのpath・size・hash・理由は`.selection.json`に残す。
memberごとのhashは`.files.sha256`、archiveとsidecarのhashは`fs-compare/SHA256SUMS`、
収録した本repo sourceのGPL-2.0原文は`fs-compare/stage4-attempt-09.licenses.txt`に付す。

修正後checkoutのrootで実行する。既存directory、hash不一致、取得失敗があれば停止する。

```sh
set -eu
git fetch origin data/fs-compare-experiments
data_sha=f64185d320339b5fca4adf088eb1b148cc664792
mkdir evidence-grow
git archive -o evidence-grow/data.tar "$data_sha" \
  fs-compare/stage4-attempt-09-text-01.tar.zst \
  fs-compare/stage4-attempt-09-text-01.files.sha256 \
  fs-compare/stage4-attempt-09-text-01.selection.json \
  fs-compare/stage4-attempt-09.licenses.txt fs-compare/SHA256SUMS
tar -xf evidence-grow/data.tar -C evidence-grow
grep '  stage4-attempt-09' evidence-grow/fs-compare/SHA256SUMS > evidence-grow/checksums
(cd evidence-grow/fs-compare && sha256sum -c ../checksums)
mkdir evidence-grow/unpacked
tar --zstd -xf evidence-grow/fs-compare/stage4-attempt-09-text-01.tar.zst -C evidence-grow/unpacked
(cd evidence-grow/unpacked && sha256sum -c ../fs-compare/stage4-attempt-09-text-01.files.sha256)
```

### 再判定の手順

取得・照合後に、同じcheckoutのrootで実行する。新しい出力先へ6入力だけを展開する。
終了値0は初回の`result-before-archive.json`に記録された値で、失敗後のdriver終了値1ではない。
判定器と起動診断の規則は、修正済みの固定commitから同じworktreeへ取り出す。
現在のcheckoutでQEMUやkernelの固定版が更新されても、再判定にはその規則を使わない。
`judge_sha`はPR #307でgrow完了行を修正したcommitで、submoduleの初期化は不要である。

```sh
set -eu
archive=evidence-grow/fs-compare/stage4-attempt-09-text-01.tar.zst
printf '70aec2eed8de39de5e76b2e852bcd80463eaad67d65a16cfec540d83058d291b  %s\n' "$archive" | sha256sum -c -
mkdir rejudge-grow
judge_sha=2c33ebf83a74212fad811ac5e5bb1e042844aca9
git fetch origin "$judge_sha"
git worktree add --detach rejudge-grow/judge "$judge_sha"
out=rejudge-grow/probe-E1-T1-negative-final
mkdir "$out"
prefix=run/early-e1-negative-final/probe-E1-T1-negative-final
tar --zstd -xf "$archive" -C "$out" --strip-components=3 \
  "$prefix/host.log" "$prefix/launcher.log" "$prefix/supervisor-run.log" \
  "$prefix/qemu-run.log" "$prefix/phase-run.json" "$prefix/summary.pending.csv"
python3 rejudge-grow/judge/board/cardputerzero/tools/bench/fs-compare-v2/supervisor.py finalize "$out" T1-negative-final 0
cat "$out/result.json"
```

この手順を新しい出力先で実行し、次の結果を得た（`result.json`の抜粋）。

```json
"status": "ok",
"driver_status": 0,
"fatal_errors": 0
```

## 結論と残件

grow完了行の不整合を直す限定修正を採用する。元試行09は失敗のまま保持する。
今回の成功は保存logの再判定であり、新しいQEMU試行やcoverage証明ではない。
修正後のQEMU先行診断、代表21件、全851件smoke、main runは未実施。
LCD・keyboard、実SDのFTL、物理電断、CM0の実機動作は未確認である。
