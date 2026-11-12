# 第2段のファイルシステム設定比較

- 状態: 完了（QEMU）
- 日付: 2026-11-11 - 2026-11-12
- 担当: Devin
- 関連: [実験一覧](README.md)、[第1段のT2再実行](2026-11-11-phase1-t2-rerun.md)、[PR #219](https://github.com/uist1idrju3i/MSD-Linux/pull/219)、[PR #220](https://github.com/uist1idrju3i/MSD-Linux/pull/220)

## 目的と仮説

ファイルシステム設定の差が、電源断後の回復、破損検出、書き込み量、実行時間にどう現れるかをQEMUで記録する。結果から製品設定の採否は決めない。
仮説は、設定差が書き込み量や回復結果に影響する可能性があること。採否の仮説は置かない。

## 採否の基準（結果を見る前に書く）

この実験では採用閾値を設定しない。T3は5回、T4-sync、T5、T6は各1回実行する。smokeで固定toolが拒否したoptionは変更せず、対象variantを計画から除く。計測値は実機の耐久性や電源断耐性の判定に使わない。

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | T4、main、main-r2は `e99402bf52c998171a14e83eeb9ccda217503828`、stackfixは `c1eff38ae53c18ce80366cc00114c6776b385475` |
| stackfix | PR #220のstack reopen修正。PR #220は実験後にmainへmergeされた |
| 環境 | `docker/msd-dev`、QEMU |
| 並列度 | T4-syncは `-j 8`、T3/T5/T6は `-j 4` |
| 反復 | T3は5回。T4-sync、T5、T6は各1回 |
| 対象 | 第2段のファイルシステム設定variant。P012、P085、P101、P133は固定toolが拒否したため除外 |
| 最終行データ | [phase2-option-variants.csv](2026-11-12-phase2-option-variants.csv) |
| QEMU | `QEMU emulator version 11.1.2`（各runの `qemu.log` の `run-qemu: version=` の行） |
| kernel | `6.18.59-v8`、GCC 14.3.0、GNU ld 2.43.1（serial logの `Linux version` の行） |
| guestのtool | mke2fs 1.47.4、mkfs.f2fs 1.16.0、btrfs-progs v6.10、cryptsetup 2.8.7、integritysetup 2.8.7、dmsetup library 1.02.205（guest logの `tool_version` の行） |
| variant定義 | [`fs-compare-phase2-variants.tsv`](../../board/cardputerzero/tools/bench/fs-compare-phase2-variants.tsv)（130行）。結果の表のIDの内容はこの表で確かめる |

kernel image、rootfs、SD imageなどの入力のSHA-256は、各runの `inputs.sha256` に記録し、data branchに保存した。host OSのversionは記録していない。

## 計画

| 計画 | 行数 | SHA-256 |
|---|---:|---|
| `phase2-generated-unfiltered.tsv` | 921 | `9a7eaee0294fc1485c08bff2d2277bc932df0c41af9941cfd5f1b5bd1c272277` |
| `phase2-t4-plan.tsv` | 126 | `6d9309dab7b8c449a9784584412750e4c85d37207c2d655fdb6261a37a660458` |
| `phase2-main-plan.tsv` | 767 | `ce836bc728bd63a66133eb331e9a6bd691821d7e20789240b445503248e376c2` |
| `phase2-main-plan-no-P007-T5.tsv` | 766 | `ead240b676fa14ea793cb119eeb8e16e99490ccc32afcdb91a465fb0d480cc4a` |
| `phase2-main-r2-plan.tsv` | 231 | `928cd9ff774d5b1fba7624bc22b1daf34dfcb87174aff02219f003a022ae424c` |
| `phase2-stackfix-rerun-plan.tsv` | 81 | `87f68bd729f4ec54ae2c78e930f0080c3ca13f85f0728f3a752d0b8cbfa48721` |
| `phase2-smoke-r2` | 132 | `5c05151b6a7d6d42d548d08047ef53cb945bf17381d0bc12d4ba223ef0152675` |
| `phase2-smoke-r3` | 1 | `b559384a9d2e98c82dc1cc0defc98fa5c1e05d0b0aa0416580afe0766861e5d5` |
| `phase2-pilot` | 22 | `4751c72318564ea703ecc30ccbab2841b42adc2a021b04de690fa82cd53b08c0` |
| `phase2-j8-check` | 8 | `e478342151f8fcdcf4c059e1420371256916d73a5c35e0300e93db3d2b6d5b4c` |

`phase2-main-plan-no-P007-T5.tsv`はP007/T5だけを除き、P007/T3は残した。`phase2-main-r2-plan.tsv`はmainの成功済み行を除き、P047/T3、P087/T6、P103/T6を外した。P110/T3は再現性確認のため残した。stackfix計画は、baseとopen commandが異なるvariantのT3/T6である。

## 手順

`fs-compare-matrix.sh --generate-phase2`で計画を作成し、除外対象を反映したplanを各matrix driverへ渡した。実行には `docker/msd-dev` とcontainer内の出力先を使い、host load、RAM、diskを60秒間隔で記録した。disk guardは25 GiBに設定し、停止条件には達しなかった。T4-syncを終えてからT3/T5/T6を実行した。
各matrixの先頭行がQEMUに到達したことを確認してから続行した。

```sh
docker/msd-dev board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  --matrix-id phase2-t4 -j 8 --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase2-t4/plan.tsv"
docker/msd-dev board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  --matrix-id phase2-main -j 4 --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase2-main/plan.tsv"
docker/msd-dev board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  --matrix-id phase2-main-r2 -j 4 --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase2-main-r2/plan.tsv"
docker/msd-dev board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  --matrix-id phase2-stackfix -j 4 --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase2-stackfix/plan.tsv"
```

## 計測器の検証

T4の `-j 8` 確認は8 variantで行った。pilotの `-j 4` にも含まれる7 variantでは、quiesce sectorsとidle write数が一致した。quiesce I/O数はP135で63/68となった。P155は `-j 8` のみで、j4比較はない。

| Variant | wall秒 j8/j4 | quiesce秒 j8/j4 | quiesce write I/O j8/j4 | quiesce sector j8/j4 | idle I/O j8/j4 | idle sector j8/j4 |
|---|---:|---:|---:|---:|---:|---:|
| P010 | 1149/1069 | 89/89 | 8/8 | 32800/32800 | 0/0 | 0/0 |
| P055 | 1037/1014 | 35/40 | 0/0 | 0/0 | 0/0 | 0/0 |
| P082 | 1113/1102 | 37/42 | 11/11 | 272/272 | 0/0 | 0/0 |
| P113 | 1486/1392 | 172/161 | 53/53 | 32384/32384 | 1/1 | 0/0 |
| P135 | 1278/1233 | 151/145 | 63/68 | 30784/30784 | 0/0 | 0/0 |
| P150 | 1151/1120 | 107/93 | 8/8 | 32800/32800 | 0/0 | 0/0 |
| P160 | 1148/1210 | 101/96 | 8/8 | 32800/32800 | 0/0 | 0/0 |

P155はj8のみで、wall 1118秒、quiesce 98秒、quiesce中6 I/O・32800 sectors、idle writeは0だった。

## 結果

### Matrixの実行結果

| Matrix | 開始 - 終了（UTC） | 成功・失敗 |
|---|---|---|
| `phase2-t4` | 2026-11-11 04:39:46 - 09:49:04 | 125/126行成功。P007/T4-syncが2 attemptともquiesce timeout |
| `phase2-main` | 09:54:28 - 16:58:58 | 528成功、6 `fail:exit_1`、2 `guest_exit_status=1`、4 SIGTERM。532/766行で監視停止 |
| `phase2-main-r2` | 17:08:06 - 21:58:41 | 220/231行成功、11行失敗 |
| `phase2-stackfix` | 22:06:28 - 23:53:03 | 81/81成功 |

時刻は2026-11-11。T4、main、main-r2は `e99402b`、stackfixは `c1eff38` で実行した。

`phase2-smoke-r2`は計画132行、139回の試行で125件が `ok`、14件が失敗試行だった。P153は修正後のr3で成功し、この時点では124/130 variantが成功した。E1/F1 smokeは両方成功した。r4の最初の起動は4回ともQEMU到達前に `exit_127` となり、`mksquashfs.orig` がcontainer内で見つからなかった。container内のpathを直したretryではP110/P118が2/2成功し、最終結果は126/130 variantが成功した。pilotは22/22成功、`phase2-j8-check`は8/8成功だった。

### T3

最終データは125 variant、625 run。全runで `recovered=ok`、`fsync_lost=0` だった。P047は実データ損失が5/5回起きたため、最終比較から除いた。

| 対象 | run | 回復成功 | fsync済みデータ損失 |
|---|---:|---:|---:|
| 有効variant | 625 | 625 | 0 |
| P047 `checkpoint=disable` | 5 | — | 5 |

P047ではT3のfile全体が消失した。QEMU logは `msd.fscmp: T3_DISK last_seq=0 open_errno=2` を記録した。F2FSのmount optionはkernel文書 `Documentation/filesystems/f2fs.rst` の `checkpoint=disable` を参照。

### T4-sync

quiesce中の書き込み（`quiesce_*`）とidle中の書き込み（`write_*`）は別の列である。最終125 variantのうち12でidle writeが非zeroだった。

| Variant | Config | idle write I/O | sector | 最後のwrite（秒） |
|---|---|---:|---:|---:|
| P044 | F1 | 203 | 6720 | 264 |
| P070 | F3 | 13 | 5736 | 218 |
| P071 | F3 | 13 | 5736 | 236 |
| P072 | F3 | 13 | 5736 | 240 |
| P073 | F3 | 13 | 5736 | 224 |
| P097 | B2 | 17 | 592 | 48 |
| P113 | I1 | 1 | 0 | 5 |
| P120 | I2 | 1 | 0 | 5 |
| P121 | I2 | 6 | 24 | 25 |
| P122 | I2 | 7 | 32 | 7 |
| P140 | L3 | 1 | 88 | 7 |
| P141 | L3 | 1 | 88 | 5 |

F3のP070-P073はbase F3と同じ13 I/O、5736 sectorsだった。P140/P141もbase L3と同じ1 I/O、88 sectorsだった。

### T5

各variantは1回だけ実行した。次表はwrite sectorsがphase1のbase平均から10%以上離れたvariantである。反復数が異なるため、比率は参考値であり同等性を示さない。

| Variant | sectors | phase1 base mean | 比率 |
|---|---:|---:|---:|
| P006 | 79112 | 96176 | 0.823 |
| P020 | 109376 | 96176 | 1.137 |
| P023 | 142048 | 96176 | 1.477 |
| P024 | 109368 | 96176 | 1.137 |
| P044 | 85496 | 74528 | 1.147 |
| P072 | 24752 | 37064 | 0.668 |
| P074 | 86312 | 37064 | 2.329 |
| P080 | 181112 | 227096 | 0.798 |
| P086 | 168792 | 227096 | 0.743 |
| P087 | 169720 | 227096 | 0.747 |
| P089 | 90680 | 227096 | 0.399 |
| P090 | 99624 | 227096 | 0.439 |
| P091 | 90616 | 227096 | 0.399 |
| P104 | 92712 | 227096 | 0.408 |
| P110 | 285368 | 359376 | 0.794 |
| P112 | 545328 | 359376 | 1.517 |
| P113 | 106376 | 359376 | 0.296 |
| P136 | 126912 | 96168 | 1.32 |

T5はverify-phaseでstackをreopenしないため、stack reopen修正の対象ではない。

### T6

| Variant | Config | 結果 | scrub corrected |
|---|---|---|---:|
| P032 | F1 | wrong | — |
| P073 | F3 | wrong | — |
| P080 | B2 | ok | 1 |
| P082 | B2 | ok | 1 |
| P083 | B2 | ok | 1 |
| P084 | B2 | ok | 1 |
| P110 | I1 | eio | — |
| P111 | I1 | eio | — |
| P140 | L3 | eio | — |

測定した9 variantの結果classはbaseと同じだった。P087はunmeasured、P103はraw copyが異なるためscrubで検出できず、最終比較に含めていない。

## 捨てた試行と経緯

| 対象 | 理由・状態 |
|---|---|
| P012 | `EXT4-fs (loop0): can't mount with journal_async_commit in data=ordered mode` |
| P085 | `mkfs.btrfs: unrecognized option '--enable-simple-quota'` |
| P101 | `BTRFS error (device loop0): cannot disable free-space-tree` |
| P133 | `cryptsetup: Option --iv-large-sectors is not allowed with luksFormat action.` |
| P110/P118の初期smoke | format/openのoption不一致で失敗した。TSVを修正し、r4 retryで2/2成功した。後述のstack reopen bugとは別である |
| P007/T4・T5 | `-O mmp` により `kmmpd` が約5秒間隔でMMP blockを書き換え、quiesceできないため再試行しなかった |
| P087/T6 | `--mixed` はT6 harnessの制約で測定できない |
| P103/T6 | checksumなしではscrubが破損を検出できない |
| stack reopen | PR #220以前はverify-phase/T6のopenがvariant optionを無視した。P110、P113、P115-P122、P134-P139のT3/T6を無効とし、stackfixで再測定した。T4/T5はreopenしないため対象外 |

main-r2の11失敗行はP110/T3が5行、P110/T6が1行、P118/T3が5行で、いずれもstack reopen bugによるものだった。

最初のmain監視は `fail:exit_1` を共通原因として数え、P047/T3の5行と別原因のP110/T3を合わせて停止した。P047のhost logは `Could not derive T3 loss metrics from run logs`、P110のkernel logは `device-mapper: integrity: Error on tag mismatch when replaying journal: -84` だった。同じ実エラーが5行を超えた停止ではなかった。r2では実際のerror lineで数えた。初期のDocker `exit_127` はcontainer内output pathの誤りであり、variantの失敗ではない。

## 結論

QEMU内で、記載したvariantとworkloadの結果を得た。採用判断はしない。QEMUのloop imageはSD card FTL、実際の電源断、物理copyの独立性を再現しないため、これらの結果は実機のデータ保全性や耐久性を保証しない。

## 未確認の点

実SD cardでの電源断、FTLのwrite amplification、別個体へのphysical copyの独立性は未確認である。実機での再測定が必要。

## ログの保存先

全phase2のtext evidenceは `data/fs-compare-experiments` branchに保存した。archive commitは `586d7e4`。`SHA256SUMS`、各groupの `.files.sha256` と再展開後のhashを照合した。最終行データは本記録に添付したCSVである。
