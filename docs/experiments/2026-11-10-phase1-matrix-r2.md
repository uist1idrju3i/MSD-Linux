# 第1段の全構成比較（phase1-r2）

- 状態: 完了（運用判断によりI2 T1の2回目を停止）
- 日付: 2026-11-09 - 2026-11-10
- 担当: Devin
- 関連: [第0段の実験記録](2026-11-09-phase0-filesystem-compare.md)、[全構成対応パイロット](2026-11-09-phase1-pilot.md)

## 目的と仮説

20構成でT1からT7を実行し、/dataの回復、破損検出、書き込み量、初期化時間を比較する。特定の方式を事前に優位とみなさず、全attemptを保存して測定値から今後の確認項目を選ぶ。QEMUで得た値を実SDカードの寿命や電源断耐性の結論には用いない。

## 採否の基準

本試験は性能上の採用閾値を決める試験ではない。matrix driverは各plan rowを最大2回実行する。事前の中止基準は、同一の構成・testが2回失敗する事例が3構成以上に達すること、またはdisk full、Docker failure、全run失敗などのsystemic errorである。いずれも発生しなかった。

I2 T1の1回目が14,400秒のtimeoutに達した後、他の全rowとF5 T3 rep 4のretryが終わり、I2 T1のretryだけが残った時点で、既知の同一timeoutを約4時間繰り返さないよう運用判断でdriverを停止した。これは事前のabort基準とは別の判断であり、未完了rowとして記録する。

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | `8b5daefb43ebcb980eb84b0455f3336cf74d4014` |
| ホスト | 6 cores / 30 GB RAM。matrix実行中のOS/kernel版はrun metadataに記録されていない |
| QEMU / Buildroot / GCC / kernel | phase1-pilotと同じ`msd-dev`および`output-fscmp`環境。版は同じ環境を使ったpilot記録から採録: QEMU 11.1.2、Buildroot 2026.08.1、GCC 14.3.0、Linux `6.18.59-v8`。このmatrix固有のcontainer digestとbinary SHA-256は記録されていない |
| 入力と出力 | branch `devin/1794125029-fs-compare-harness`。既存Buildroot成果物を再利用し、runごとにhost scriptが作業treeのguest scriptを含むrootfsを準備した。Buildrootの再configure・再buildは行っていない |
| 変更する条件 | 20構成すべて。各構成でT1×1、T2×20、T3×5、T4-sync×1、T4-nosync×1、T5×1、T6×1、T7×1 |
| 固定する条件 | 構成定義、test workload、commit、QEMU環境。実行中のscriptは編集していない |
| 並列度とretry | `-j 4`。各plan rowを自動で最大2 attemptまで実行 |
| 計画 | 620 rows。SHA-256: `5cc893399cb20b51f07ef567d7dd45685b015a0f39a9cb734d21fe1f78503f77` |
| 反復数 | T2は1 invocationにつきhost側の電源断・再起動1回を20回、T3は5回。その他は各1回。統計比較に使うにはT1/T4/T5/T6/T7の反復数が不足する |

T2は1 invocationあたりhost側の電源断・再起動を1回行い、各構成で20 invocationを実施した。guest内の20回反復ではない。再現時は同じplanと、次のdriver呼び出しを使う。

```sh
RUNS_DIR=<永続run保存先>
QEMU_LOG_DIR="$RUNS_DIR" docker/msd-dev \
  board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  -j 4 --matrix-id phase1-r2 --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase1-r2/plan.tsv"
```

実行時はこのdriverをdetachedで起動し、60秒間隔で`uptime`と`free -m`を記録した。T1 checkerの基準は承認済みの`8b5daefb`で統一した。

## 計測器の検証

O_DIRECTのwrite accounting、T4のquiesce/idle、T6の破損検出、T3のmarker、T1のnegative controlは[第0段の実験記録](2026-11-09-phase0-filesystem-compare.md)に記録した。T6のstack mappingとT7の全setup chainは[全構成対応パイロット](2026-11-09-phase1-pilot.md)で確認している。本matrixでは別のA/A試験やnegative-control runを追加していない。

## 結果

開始は2026-11-09 19:33:28 UTC、最終progress記録は2026-11-10 13:45:56 UTCで、開始から最終progressまで65,548秒（18時間12分28秒）。driver停止後、13:46:18 UTCまでに終了と子process不在を確認した。620 plan rowsすべてにsummary rowがあり、622 attemptsを記録した。最終attemptでは619 rowsが`ok`、I2 T1だけがoperator stopで未完了となった。

host-loadの1分平均最大値は10.54、5分平均は9.55、15分平均は9.31。記録数は1,092 samplesだった。

以下のstatus表は各testの最終attemptにおける`成功/失敗`数である。失敗attemptを成功数に混ぜていない。

| 構成 | T1 | T2 | T3 | T4-sync | T4-nosync | T5 | T6 | T7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| E2 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| E3 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| E4 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| E5 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| F1 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| F2 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| F3 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| F4 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| F5 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| B1 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| B2 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| B3 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| B4 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| B5 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| L1 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| L2 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| L3 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| I1 | 1/0 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| I2 | 0/1 | 20/0 | 5/0 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |

構成ごとの値を次表に示す。T1の値は、setupでは`mount_fail/fsck_fail`、workloadでは`mount_fail/fsck_fail/loss_points`の順。T5比率は`write_sectors × 512 / logical_bytes`。T6列は`read_result/scrub_corrected/scrub_uncorrectable/fsck_detection/repaired`、T7列は`mkfs/setup/mount/fsck`秒と`mem_available_kb`である。

| 構成 | T1 setup | T1 workload | T2 recovered /20; manifest_ok /20 | T3 median lost s; max fsync_lost | T4-sync ios/sectors/last s | T4-nosync ios/sectors/last s | T5 sectors/logical bytes; ratio | T6 read/scrub+/scrub-/fsck/repaired | T7 mkfs/setup/mount/fsck s; mem kB |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 3/3 | 0/0/0 | 20/20; 20/20 | 4.176; 0 | 0/0/none | 5/48/4 | 96176/34706432; 1.419x | wrong/na/na/0/na | 2.466/0.000/1.424/2.343; 886304 |
| E2 | 3/3 | 0/0/0 | 20/20; 19/20 | 1.176; 0 | 0/0/none | 3/24/8 | 165224/34706432; 2.437x | wrong/na/na/0/na | 2.450/0.000/1.396/2.324; 888116 |
| E3 | 3/3 | 0/0/0 | 20/20; 18/20 | 3.218; 0 | 0/0/none | 5/48/22 | 96168/34706432; 1.419x | wrong/na/na/0/na | 2.368/0.000/1.368/2.285; 884784 |
| E4 | 3/3 | 0/0/0 | 20/20; 20/20 | 0.000; 0 | 0/0/none | 3/24/16 | 142120/34706432; 2.097x | wrong/na/na/0/na | 2.525/0.000/1.548/2.579; 887148 |
| E5 | 3/3 | 0/0/0 | 20/20; 11/20 | 6.084; 0 | 0/0/none | 5/48/20 | 96208/34706432; 1.419x | wrong/na/na/0/na | 2.556/0.108/1.661/2.410; 880168 |
| F1 | 0/0 | 0/0/0 | 20/20; 18/20 | 2.124; 0 | 0/0/none | 8/192/39 | 74528/34706432; 1.099x | wrong/na/na/0/na | 8.111/0.000/0.350/11.103; 884484 |
| F2 | 0/0 | 0/0/0 | 20/20; 19/20 | 7.231; 0 | 0/0/none | 8/192/28 | 82072/34706432; 1.211x | wrong/na/na/0/na | 8.953/0.000/0.322/11.190; 881592 |
| F3 | 0/0 | 0/0/0 | 20/20; 15/20 | 1.348; 0 | 13/5736/234 | 13/5736/216 | 37064/34706432; 0.547x | wrong/na/na/0/na | 9.584/0.000/0.310/8.679; 885620 |
| F4 | 0/0 | 0/0/0 | 20/20; 18/20 | 0.000; 0 | 217/6600/200 | 222/6768/183 | 107392/34706432; 1.584x | wrong/na/na/0/na | 9.630/0.000/0.322/11.209; 875556 |
| F5 | 0/0 | 0/0/0 | 20/20; 12/20 | 3.102; 0 | 0/0/none | 8/192/27 | 75336/34706432; 1.111x | wrong/na/na/0/na | 8.713/0.112/0.428/8.817; 878004 |
| B1 | 16/16 | 0/0/0 | 20/20; 19/20 | 8.341; 0 | 0/0/none | 29/848/20 | 158464/34706432; 2.338x | eio/na/na/0/na | 4.968/0.000/0.761/0.601; 878608 |
| B2 | 16/16 | 0/0/0 | 20/20; 19/20 | 5.312; 0 | 0/0/none | 27/848/21 | 227096/34706432; 3.350x | ok/1/0/0/yes | 4.636/0.000/0.349/0.457; 877724 |
| B3 | 16/16 | 0/0/0 | 20/20; 19/20 | 3.022; 0 | 0/0/none | 23/656/3 | 219704/34706432; 3.241x | ok/na/na/0/na | 4.624/0.000/0.416/0.447; 879232 |
| B4 | 16/16 | 0/0/0 | 20/20; 20/20 | 0.000; 0 | 0/0/none | 17/464/2 | 388080/34706432; 5.725x | ok/na/na/0/na | 4.646/0.000/0.402/0.435; 879940 |
| B5 | 22/22 | 0/0/0 | 20/20; 18/20 | 5.200; 0 | 0/0/none | 28/1168/18 | 230232/34706432; 3.396x | ok/na/na/0/na | 7.412/15.136/0.335/0.420; 883292 |
| L1 | 9/9 | 0/0/0 | 20/20; 19/20 | 4.167; 0 | 0/0/none | 6/56/3 | 96168/34706432; 1.419x | wrong/na/na/0/na | 42.940/17.469/1.568/2.576; 889492 |
| L2 | 9/9 | 0/0/0 | 20/20; 16/20 | 4.114; 0 | 0/0/none | 8/88/2 | 96160/34706432; 1.419x | wrong/na/na/0/na | 44.542/13.743/1.704/2.482; 887540 |
| L3 | 83/83 | 0/0/0 | 20/20; 18/20 | 4.076; 0 | 1/88/6 | 1/88/14 | 283304/34706432; 4.179x | eio/na/na/0/na | 85.056/2772.469/5.354/2.723; 848720 |
| I1 | 74/74 | 0/0/0 | 20/20; 20/20 | 6.369; 0 | 0/0/none | 1/176/26 | 359376/34706432; 5.302x | eio/na/na/0/na | 87.221/2607.235/0.239/1.953; 856612 |
| I2 | 47/47 | 0/0/47* | 20/20; 15/20 | 7.033; 0 | 4/8/7 | 8/40/7 | 107464/34706432; 1.585x | eio/na/na/0/na | 43.314/2540.236/1.523/5.173; 855592 |

`na`はそのtest/configで該当しない値。T1 I2の`47`は停止したretryの部分summaryであり、損失を示す値ではない。I2 T1の両attemptは次項に分けて記録する。

T4-syncで非0だった観測値（write_ios/write_sectors/last_write_s）は、F3が13/5736/234、F4が217/6600/200、L3が1/88/6、I2が4/8/7だった。

### T2 `manifest_ok`の再評価

phase1-r2ではT2の`recovered`は全構成で20/20だった。一方、`manifest_ok`は11/20から20/20まで構成ごとに差があった。次の調査で、W2 checkerの比較方法とfscrypt keyの生成・policy設定処理にそれぞれ問題があることを確認した。phase1-r2の`manifest_ok`は、追試したE5/F5/F3については[別記録](2026-11-10-phase1-t2-manifest-recheck.md)の結果で置き換える。T2の`recovered`件数は有効なままである。

#### W2のhash不一致

phase1-r2の全33件のW2 hash不一致を調べたところ、実データのSHA-256は33/33件で、最後に記録されたackの直後にある次の更新payloadと一致した。一致しない件数は0だった。payloadは2048 bytesで、byte位置`j`の値は`(j * 31U + seed * 17U) & 0xff`、`seed=cycle * 100 + update_index`である。実データのhashは、最後のackより古い更新でも、破損データでもなかった。

run IDの共通接頭辞は`phase1-r2-T2-`。下表のmarkerは、最後のackから次のpayloadへの遷移を示す。

| 構成 | run IDの後半 | marker |
|---|---|---|
| B1 | `B1-r4-1794302117` | `000-021` → `000-022` |
| B2 | `B2-r2-1794302896` | `000-011` → `000-012` |
| B3 | `B3-r17-1794304436` | `000-004` → `000-005` |
| B5 | `B5-r15-1794306170`, `B5-r4-1794305656` | `000-049` → `000-050`, `000-028` → `000-029` |
| E2 | `E2-r17-1794294557` | `000-054` → `000-055` |
| E3 | `E3-r16-1794295432`, `E3-r8-1794295068` | `000-063` → `000-064`, `000-039` → `000-040` |
| E5 | `E5-r1-1794296496`, `E5-r3-1794296599` | `000-093` → `000-094`, `000-075` → `000-076` |
| F1 | `F1-r13-1794297949`, `F1-r3-1794297452` | `000-078` → `000-079`, `000-064` → `000-065` |
| F2 | `F2-r10-1794298688` | `000-058` → `000-059` |
| F3 | `F3-r1-1794299216`, `F3-r11-1794299630`, `F3-r12-1794299672`, `F3-r20-1794300035`, `F3-r8-1794299469` | `000-070` → `000-071`, `000-083` → `000-084`, `000-066` → `000-067`, `000-069` → `000-070`, `000-083` → `000-084` |
| F4 | `F4-r12-1794300605`, `F4-r3-1794300197` | `000-025` → `000-026`, `000-022` → `000-023` |
| F5 | `F5-r1-1794301041`, `F5-r10-1794301480`, `F5-r16-1794301745`, `F5-r9-1794301413` | `000-082` → `000-083`, `000-075` → `000-076`, `000-086` → `000-087`, `000-047` → `000-048` |
| I2 | `I2-r12-1794313346`, `I2-r15-1794313684`, `I2-r18-1794314038` | `000-086` → `000-087`, `000-019` → `000-020`, `000-071` → `000-072` |
| L1 | `L1-r10-1794306909` | `000-079` → `000-080` |
| L2 | `L2-r17-1794308363`, `L2-r19-1794308495`, `L2-r5-1794307724` | `000-077` → `000-078`, `000-026` → `000-027`, `000-048` → `000-049` |
| L3 | `L3-r13-1794309810`, `L3-r5-1794309026` | `000-020` → `000-021`, `000-027` → `000-028` |

#### fscrypt key

失敗したE5/F5と成功したE5の各1 runについて、`sdcard.img`の写しから`/data`を読み出した。写しのimage hashは保存元と一致した。失敗した二つでは`fscrypt.key`が存在するものの0 bytes、mode `0600`だった。成功したE5では64 bytesだった。

| run ID | image SHA-256 | `fscrypt.key` |
|---|---|---|
| `phase1-r2-T2-E5-r16-1794297137` | `4fd296d7b62a6dee43c37a2d8360635571ebfc3ee0d57c455f8a4b90f6c1476d` | 0 bytes、mode `0600` |
| `phase1-r2-T2-F5-r4-1794301168` | `be4c815e17845f6130f8d722623574b5ce9890e60ef9f38279ed41222b9ec232` | 0 bytes、mode `0600` |
| `phase1-r2-T2-E5-r2-1794296528` | `0d3a6cc0b577e5d15bc9d75af88ba394864c144ac3e829dd2be7db52944eae87` | 64 bytes |

失敗した二つのrecovery logには、`file or directory already encrypted`を含むpolicy設定errorと201件の`manifest_missing`が記録され、`manifest_ok=no`だった。log上では`/data`はread-writeでmountされ、読み取り専用や`head`/`chmod`のerrorは見つからなかった。code pathでは`verify_recovery`から`mount_volume`へ進み、`make_keyfiles`の空key判定`[ ! -s "$FSCRYPT_KEY" ]`が新しい乱数keyを書き出す経路に達する。空fileは直接確認したが、そのbootで作られた乱数key自体はlogやimageに残っていないため、再生成は到達可能なcode pathに基づく推定である。成功したE5のkeyは`debugfs -n`で読んだ。読み取り専用`e2fsck -fn`はその写しにmetadata errorを報告したため、成功例のfilesystem状態にはこの制約がある。

L*/B5の`luks.key`にも、従来は同じくfsyncしない生成手順があった。検証時はmount前にそのkeyで`cryptsetup open`するため、keyが失われればopen failureになる。phase1-r2でL*/B5にそのfailureはなく20/20 recoveredしたが、これは当該試行でのdurability riskがないことまでは示さない。

## 失敗・中止した試行

### I2 T1

I2 T1の状態は「**timed out (attempt 1) / stopped by operator (attempt 2)**」である。attempt 1は`phase1-r2-T1-I2-r1-1794252814`で、14,409秒後に14,400秒timeoutとなった。263 points（setup 54、workload 209）まで進み、`T1_SETUP_DONE`はentry 469、最後の点はentry 1918のworkload flushで`elapsed_seconds=70`だった。点ごとの所要時間はsetupがmin/median/mean/max = 1/20.5/21.26/79秒、workloadが9/62/60.09/108秒、全点が1/58/52.11/108秒。最後の10点は`(entry, seconds)`で`(1846,79) (1858,67) (1861,70) (1873,81) (1876,66) (1888,67) (1891,75) (1903,65) (1906,77) (1918,70)`。

attempt 2は`phase1-r2-T1-I2-r1-1794315353`で、operator stopまで3,003秒、90 points（setup 53、workload 37）に達した。`T1_SETUP_DONE`はentry 466、最後の点はentry 712のworkload flushで`elapsed_seconds=61`。点ごとの所要時間はsetupが1/20/18.87/67秒、workloadが4/38/37.14/72秒、全点が1/21/26.38/72秒（各min/median/mean/max）。最後の10点は`(640,47) (652,37) (655,41) (667,43) (670,47) (682,56) (685,53) (697,49) (700,72) (712,61)`。

attempt 1の49件、attempt 2の47件の`T1_MOUNT_ERR`は、すべてそれぞれentry 469、466のsetup-doneより前に発生した。両attemptともsetup-done以降のmount failureはなく、`T1_MANIFEST_FAIL`も発生しなかった。workload pointはmount=yes、fsck=0、manifest=yesだった。

attempt 1のpartial summaryでは`loss_points=49`、`setup_mount_fail=49`となった。guestのfallbackは`T1_POINT ... manifest=no`を検索するが、mount不能時の`manifest=not_mounted`も部分文字列`manifest=no`に一致する。したがってこの49件はsetup時のmount失敗の再計上であり、データ損失ではない。attempt 2も同じfallbackのため、集計表の`loss_points=47`は47件のsetup mount failureの再計上である。I2 T1のいずれのpartial summaryもデータ損失の証拠として扱わない。

### F5 T3 rep 4

attempt 1のrun `phase1-r2-T3-F5-r4-1794289618`は2026-11-10 05:46:58 UTCごろに開始し、host logに`Timed out waiting for msd.fscmp: writer-start`と記録された。開始時刻はhost session migration付近だった。retryの`phase1-r2-T3-F5-r4-1794318001`は197秒で`ok`となった。初回の失敗はraw CSVに残し、retryを最終値として集計した。

最終attemptで成功しなかったrowはI2 T1だけである。driver PIDとmatrix bash PIDをSIGTERM後に終了確認し、残存する`fs-compare.sh`または`qemu-system` processがないことを確認した。全run directoryとlogを保持し、`run-meta.txt`にoperator noteを追記した。

## 結論

620 plan keyを記録し、最終attemptは619件成功、I2 T1は既知timeout後のoperator stopで未完了。F5 T3 rep 4は初回失敗とretry成功を区別した。T2 recovered/manifest_okは別々に保持し、単一matrixから採否は決めない。T2 manifest_okとI2 T1は[phase1-r3追試](2026-11-11-phase1-t2-rerun.md)で置換する。

このQEMU環境にはSDカードのFTL、カード内write cache、物理的な電源断挙動がない。結果はQEMU上のfilesystem・stack・回復処理の比較であり、実SDカードの電源断試験ではない。

## 未確認の点

- I2 T1の全modeを完了するには、既知timeoutより長い上限を設定したtargeted rerunが必要。
- T1/T4/T5/T6/T7は各構成1回であり、性能比較の統計的結論には反復が不足する。
- matrix固有のhost OS/kernel、container digest、QEMU/kernel binary SHA-256はrun metadataに記録していない。
- 実SDカードのFTL、write cache、電源断後の状態は未確認。

## ログと再集計

[raw CSV](2026-11-10-phase1-matrix-r2.csv)は`matrix-summary.csv`の622 attemptを保存し、SHA-256は`47acbded029e5ac48f9f6ba6ea7ac620f57b35c6b916ab4ad1373d0b22e0e4ac`。planのSHA-256は上記のとおり。`host-load.txt`のSHA-256は`5dc4a071c913adeabee81863f57aed61d0b0d4eee22a45a3af1d413d93009cab`。aggregation outputのSHA-256は`653831297a6f2e47c1aedfaac01b164b7e377e8bbd08c9582a1411289a06c3ac`。`aggregate.py`は620 plan row、622 attemptを検証し、T1-T7の構成別metricsを出力する。

raw log: [data branch](https://github.com/uist1idrju3i/MSD-Linux/tree/data/fs-compare-experiments)の`fs-compare/phase1-r2.tar.zst`。SHA-256: `5138e019255284911bbee38a3cddcdf350b0c62c6d17f6cca4c206ea6a46aa79`。

### 診断に用いた主要logのSHA-256

| run | QEMU log | host log |
|---|---|---|
| I2 T1 attempt 1 | `1a819e00b5564ce7d9963442d1f2581cccbf2a4b35af2d511027f81f0ff96675` | `75aabcf8765fd13ffe2ecd9afd77c815bb9a7d6197e72b16e309b4dd25a30800` |
| I2 T1 attempt 2 | `a146557acdedf5be04224492f212af60a7efbed20bee2f8f6a36ac3d1bb1df20` | `e62d006a7a23fbe9ce5e786ca9f8dc0372b2fc5d089398aeec16f9088f270b36` |
| F5 T3 rep 4 attempt 1 | `708dfa9e66719a93e905e66a90ac934402eb214bff5d7dbfc7df166e206ec51c` | `caef8dd71281f262425d6bbbed66bfee23050a5c777b9dc70af7b5e2110fc805` |
| F5 T3 rep 4 attempt 2 | `744b08814a403ed3d5c5845fcb192d345ef4d28bf3bc0a33f8cfb7cad24d5387` | `b502bae8e52483e3dcf65046442c37f1720c03b5bd1224e7c6f68ff295e74e3e` |

`progress.log`、`host-load.txt`、`run-meta.txt`、plan、全run directoryは永続run保存先に保持し、repoには大きなlogを複製していない。
