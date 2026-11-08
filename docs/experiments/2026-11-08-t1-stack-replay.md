# 20構成向けT1 stack replayの検証

- 状態: 完了（QEMU）
- 日付: 2026-11-08
- 担当: Devin
- 関連: [filesystem比較の予備実験](2026-10-30-s4-fs-compare.md)

## 目的と仮説

T1を20構成で実行できるよう、log-writesをloop deviceの直上に置く。暗号化・integrity stackはreplay snapshot上に別名で開き、filesystem recovery、manifest照合、fsckを行う。fscryptではreplay mountに同じkeyを追加し、workload rootにある全acknowledged fileを照合する。これによりstack構成でもT1のfinal pointを検査できると予想する。

## 採否の基準（結果を見る前に書く）

- F1、L3、I2、E5の並列run、B5、E1の各T1-finalで、`T1_FINAL_CHECK`が`mount=yes fsck=0 manifest=yes`を示し、`expected_files`と`actual_files`が一致する。
- stack構成ではfinal pointの`stack_open=yes`、その他では`stack_open=not_applicable`とする。
- 各pointのsnapshot statusに`Invalid`または`Overflow`がなく、runのsummary statusが`ok`で、QEMU logにguestの`finished` markerがある。
- SIGTERM対照はhost終了code 143でsummaryが`fail:terminated_signal_15`となり、QEMU logに`finished` markerがない。
- 各条件は1回とする。これはfinal checkerとstack経路の動作確認であり、全20構成の網羅や性能の結論には用いない。

## 条件

| 項目 | 値 |
|---|---|
| 基準のcommit | `1d3a7d47ede960137a8267d55768989c3105543a`。測定対象のharness変更はこのcommit上の作業treeに含め、入力hashを保存する。 |
| ホスト | 6 core、30 GB RAM、Ubuntu 26.04.1 LTS、Linux 7.0.0-43-generic、x86_64。 |
| QEMU | QEMU emulator 11.1.2。binary SHA-256: `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`。 |
| Buildroot / GCC / カーネル | Buildroot 2026.08.1、GCC 14.3.0、Linux `6.18.59-v8`。 |
| 使ったツールのバージョン | QEMUのバージョンは各`qemu.log`で確認した。Buildroot build logは`phase0-review-build-t1-stack-retry-1794163525`に保存し、SHA-256は`e5d5752d00e66d929b33e2cde2fd4a94f37296283bb18a8df4d5a75084ec6c45`。 |
| 出力先と状態 | `output-fscmp`を再利用した。`fs-compare-build.sh`でbuildし、`*-reconfigure`は指定していない。各runは固有のrun dirとSD imageを使った。 |
| 変える条件 | T1-finalのconfig: F1、L3、I2、E5を同時実行し、B5、E1を順に実行する。別にE1 T1-finalを約60秒後にSIGTERMで中断する。 |
| 変えない条件 | 256 MiB test device、1 GiB sparse log-writes file、64 MiB snapshot COW、T1 reduced workload（W1=50 files、W2=25 updates、W3=250 records・50件ごとにfsync、W4=8 MiB）、kernelとBuildroot設定。 |
| 繰り返し | 各構成1回。L3 setup markの失敗後に別runで再試行した。性能測定ではないため中央値を算出しない。 |
| 入力とバイナリ | runの`inputs.sha256`、`qemu.log`のSHA-256、QEMU binaryとkernel ImageのSHA-256を記録する。`replay-log`はcommit `7b70d8a6863c5de30933d42a7672d35d01d2dc6c`、SHA-256 `e02779a201b41bf34897c3bc72daafa7e0b13dfc148bb91400599471ffae2750`。workload binary SHA-256は`5926b57671c9813808d41b4577bb968460ee1a5246da714f309917a3c7c8d08e`。QEMU logに出たkernel Image SHA-256は`33454149eb370971ee08cea85aed61a0a14bda6eb3b4b7cef762c56d64ebbdac`。 |
| 初回と失敗の扱い | 失敗・中断runを残し、成功runと混ぜない。最初のL3 runはsetup markを検索できず失敗し、別runで再試行した。SIGTERM対照は最初にdocker launcherへ送った試行も保存し、約60秒後にharnessへ直接送った試行を判定に使う。 |

## 手順

```sh
RUNS_ROOT=/persistent/fscmp/runs
epoch=1794162416
for config in F1 L3 I2 E5; do
  QEMU_LOG_DIR="$RUNS_ROOT" docker/msd-dev \
    board/cardputerzero/tools/bench/fs-compare.sh \
    "$config" T1-final "phase0-review-T1-final-${config}-${epoch}" &
done
wait
QEMU_LOG_DIR="$RUNS_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/fs-compare.sh \
  B5 T1-final phase0-review-T1-final-B5-1794165151
QEMU_LOG_DIR="$RUNS_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/fs-compare.sh \
  E1 T1-final phase0-review-T1-final-E1-1794165612
```

SIGTERM対照では別runを起動し、60秒後にrun IDから特定した`fs-compare.sh` processへSIGTERMを送った。harness processをsignalの対象にした。すべてのrun dirと`output-fscmp`を保持した。

## 計測器の検証

各final pointでmount、manifest、fsck、stack openの結果とacknowledged file数を照合した。SIGTERM対照で異常終了のsummary分類を確認した。性能評価を目的としないため、A/A比較は行わない。

## 結果

| 構成 | run ID | status / wall_seconds | setup-done entry | 候補setup / workload points | final check |
|---|---|---|---:|---:|---|
| F1 | `phase0-review-T1-final-F1-1794162416` | `ok` / 163 | 1040 | 1 / 137 | 53/53 files、stack not applicable、mount yes、fsck 0、manifest yes |
| E5 | `phase0-review-T1-final-E5-1794162416` | `ok` / 243 | 105 | 5 / 222 | 53/53 files、stack not applicable、mount yes、fsck 0、manifest yes |
| I2 | `phase0-review-T1-final-I2-1794162416` | `ok` / 1038 | 465 | 52 / 279 | 53/53 files、stack yes、mount yes、fsck 0、manifest yes |
| L3 初回 | `phase0-review-T1-final-L3-1794162416` | `fail:guest_exit_status=1` / 433 | なし | 算出前 | `t1_setup_done_mark_not_found` |
| L3 再試行 | `phase0-review-T1-final-L3-retry-1794163586` | `ok` / 1556 | 2628 | 105 / 320 | 53/53 files、stack yes、mount yes、fsck 0、manifest yes |
| B5 | `phase0-review-T1-final-B5-1794165151` | `ok` / 452 | 1348 | 24 / 222 | 53/53 files、stack yes、mount yes、fsck 0、manifest yes |
| E1 | `phase0-review-T1-final-E1-1794165612` | `ok` / 343 | 105 | 5 / 219 | 53/53 files、stack not applicable、mount yes、fsck 0、manifest yes |
| E1 SIGTERM（有効な対照） | `phase0-review-T1-terminated-E1-1794166081` | `fail:terminated_signal_15` / 61 | 未到達 | 0 / 0 | guest finished markerなし |

各final pointで`loss_points=0`だった。`setup_points=0`はfinal modeで選択された点がworkload phaseだったことを示す。候補setup point数は`candidate_setup_points`で別に記録した。T1-finalは最終候補点だけを検査するため、各pointに対するsnapshot statusの基準は未確認である。選択したfinal pointではsnapshot overflowがなく、正常終了した6構成の`summary.csv`は`ok`で、guestのfinished markerも確認した。

`summary.csv`のデータ行は次のとおり。

```text
phase0-review-T1-final-F1-1794162416,F1,T1-final,ok,163,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-E5-1794162416,E5,T1-final,ok,243,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-I2-1794162416,I2,T1-final,ok,1038,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-L3-1794162416,L3,T1-final,fail:guest_exit_status=1,433,t1-reduced,0,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-L3-retry-1794163586,L3,T1-final,ok,1556,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-B5-1794165151,B5,T1-final,ok,452,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-final-E1-1794165612,E1,T1-final,ok,343,t1-reduced,1,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-terminated-E1-1794165972,E1,T1-final,fail:terminated_signal_15,91,t1-reduced,0,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
phase0-review-T1-terminated-E1-1794166081,E1,T1-final,fail:terminated_signal_15,61,t1-reduced,0,0,0,0,,,,,,,,,,,,,,,,,,,,,,0,0,0
```

T1-finalは各構成で1点だけを検査するモードであり、`candidate_setup_points`と`candidate_workload_points`は全候補点の数である。T1 `mode=all`は実行していない。

## 捨てた試行と経緯

最初のL3 runは`T1_SETUP_DONE`のentryを検索できず、`t1_setup_done_mark_not_found`で終了した。60回まで検索する修正版で再実行すると`entry=2628`が得られ、final checkも成功した。ただし初回の失敗原因は特定していない。検索の再試行を増やしたことと成功の時間的な対応は確認できたが、markが遅れた機序は未確認である。

最初のSIGTERM操作ではDocker launcherを対象にしてしまい、harness自体は停止しなかった。その後、実際の`fs-compare.sh` processへSIGTERMを送り、`fail:terminated_signal_15`のsummaryがwall 91秒で記録された。このrunは60秒対照には使わず、run ID一致のharness processへ60秒後にsignalを送った別runを判定に使った。後者はwall 61秒で終了し、`finished` markerがないことも確認した。

前の並列試行`phase0-par4-T1-all-*-1794161722`では、F1とL3が`T1_requires_E1_or_B2`で失敗した。未対応configのエラーを受けてE1/B2も停止した。これらは本試験の結果に含めない。

## 結論

指定した6構成のT1-finalで、スタックの再open、filesystem mount、fscrypt manifest照合、およびfsckを含むfinal checkが成功した。異常終了対照も要求どおり`fail:terminated_signal_15`となった。L3初回のsetup mark未検出は別runで再試行して成功したが、失敗原因は確定していない。これは6構成のfinal pointを確認した結果であり、全20構成の検証、T1 mode=allの性能、実機の挙動を示すものではない。

## 未確認の点

残り14構成のT1-final、全構成のT1 mode=all、実SDの電源断、書き込み特性、性能、wearは未確認であり、本試験の対象外である。

## ログ

raw logとrun dirは永続的な測定出力先に保持し、リポジトリには入れない。各行は`qemu.log`と`inputs.sha256`のSHA-256である。

| run ID | `inputs.sha256` SHA-256 | `qemu.log` SHA-256 |
|---|---|---|
| `phase0-review-T1-final-F1-1794162416` | `b1af3d7ff0c259708427d283f82a0d5e3837f742d3690b0edfb913c53189e227` | `173d500f82868c3e72657b9f1cff440b43f258d3e76bc5d5a517da3eefb859ef` |
| `phase0-review-T1-final-L3-1794162416` | `4f6f4f5ce9dc13e1cad8868a4797d41f5c2bdc78bad1e567a69611f772da41f7` | `07ed5be8de7821a3ae7d4683015846fd7ed99954d514760c55a4fd4b1f5aab34` |
| `phase0-review-T1-final-I2-1794162416` | `05f4e16f2e78d1e11ddca280fad9667b1e3cc9cb320ce427357550bdff6d4a5a` | `25fbe7d40fe729b9d2184c10cbe2fa12e9a3de9965bd0569376a55e32dee666e` |
| `phase0-review-T1-final-E5-1794162416` | `9ecd457940836ff09154e2c1e1ea6343820670fb5b3ef6101196f655545b3e97` | `680f41ff2142212965d144e9963c998203aa49d168545a109a8b5e0df77c54d9` |
| `phase0-review-T1-final-L3-retry-1794163586` | `936a34eb18c8f452a80c5fa19964b3285efa9f67e01fef5a957128fcadf50d2f` | `8615496bee94f9c53476445a3d64c04d8f53bb7ff9416e26632708d6bbc32236` |
| `phase0-review-T1-final-B5-1794165151` | `b6dd80a92d606ff3f16b7566a480af0f4286c661afd774aa6264405002fa6b36` | `286a32bb5591f1bab8ac10ecec59f65a657c0ebca3dfe8381849c09dcb0885c5` |
| `phase0-review-T1-final-E1-1794165612` | `dd455ee5418ab78a844f82d4e07fd39305bcbff99bf72ef4cf1a614062f62cef` | `5ecf48a7bb7b3241bdd54a51caa6f05aff0709414246d480f851bdd15a4c869f` |
| `phase0-review-T1-terminated-E1-1794165972` | `43d478a67efea4cdca0167a90917087b1fcf32142d5d451fd67809fb52da678b` | `4f85f97116f8735df52ade8821410b2936b04e83af2d8b4a793ddd063b357b21` |
| `phase0-review-T1-terminated-E1-1794166081` | `2c8ad4faa7ef43b39550f71d6f8f56a604549ac12cdc2e675a53c5f290e69191` | `ab7c19ec59185fb8636e40f4aad637162cec0a38a16a34f4d05cb5333bf2d277` |

SIGTERM runのlog hashは、harnessがtrapで終了した後に保存ファイルから計算した。全run dirと`output-fscmp`は保持している。
