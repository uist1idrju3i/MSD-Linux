# 第1段T2全構成の再測定（phase1-r3-t2-retry）

- 状態: 完了（QEMU、20構成のT2、E1/I2のT1）
- 日付: 2026-11-10 - 2026-11-11
- 担当: Devin
- 関連: [phase1-r2](2026-11-10-phase1-matrix-r2.md)、[T2 manifest再検査](2026-11-10-phase1-t2-manifest-recheck.md)、[実験一覧](README.md)

## 目的と仮説

W2/W3のmanifest検査とfscrypt keyfileの永続化を修正した後、全20構成のT2を再測定する。I2 T1はtimeoutを延長して完了させ、E1 T1はW3 validator変更の回帰確認に使う。QEMUの結果を実SDの電源断耐性やFTLの評価には用いない。

## 採否の基準（結果を見る前に書く）

本試験は構成を採用するための性能閾値を決めない。phase1-r2と同じ基準を使う。T2は各構成20回すべてで自動回復すること。`manifest_ok`は回復完了とは別に記録する。T1はsetup後のworkloadでmount失敗、修復不能なfsck失敗、fsync済みデータの損失がいずれも0であること。

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | `179b849737ac91cbac41b188470ccd863857a533` |
| 環境 | `docker/msd-dev`。QEMU、Buildroot、GCC、kernelのバージョンは[phase1-r2記録](2026-11-10-phase1-matrix-r2.md)と同じ |
| 計画 | 402 rows。I2 T1×1、E1 T1×1、全20構成のT2×20 |
| plan SHA-256 | `7d01dcd328c96329061e22a7e2db63030d405d1bf9a021cfa121c324541456ca` |
| 並列度 | `-j 4` |
| I2 T1 timeout | 43,200秒。E1 T1は回帰確認として1回 |
| 出力 | `phase1-r3-t2-retry`。build成果物はcommitに対応しており、再buildは不要だった |
| 反復 | 各T2 invocationで電源断・再起動を1回、各構成20 invocation |

## 手順

matrixはDocker経由で実行し、進捗とhost loadを記録した。再実行する場合は永続保存先を`RUNS_DIR`に設定する。

```sh
: "${RUNS_DIR:?set RUNS_DIR to persistent storage}"
QEMU_LOG_DIR="$RUNS_DIR" nohup setsid docker/msd-dev \
  board/cardputerzero/tools/bench/fs-compare-matrix.sh \
  --matrix-id phase1-r3-t2-retry -j 4 \
  --runs-dir "$RUNS_DIR" \
  "$RUNS_DIR/phase1-r3-t2-retry/plan.tsv"
```

容量確保のため、利用者に知らせた上でrunごとの`build/`だけに次の重複排除を行った。`sdcard.img`、log、CSVは変更・削除していない。

```sh
hardlink -t -X -v */build > dedup-build-hardlink-20261111.log 2>&1
```

## 計測器の検証

T2では各回のrecovery markerとmanifest結果を別々に確認した。W2のack直後のin-flight更新、W3の最後のfsync marker以後に残る正しいrecord列は、[T2 manifest再検査](2026-11-10-phase1-t2-manifest-recheck.md)に記録したvalidator仕様で判定する。T1のnegative controlは同記録でlossを検出しており、本matrixではE1 T1をW3 validatorの回帰確認に使った。

## 結果

全20構成のT2（計400件）で、recoveredと`manifest_ok`はどれも20/20となった。event列は各成功runのQEMU logに現れた行数である。

| 構成 | recovered | manifest_ok | W2 inflight | W3 tail | hash mismatch | missing | fscrypt policy failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 | 20/20 | 20/20 | 1 | 0 | 0 | 0 | 0 |
| B2 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| B3 | 20/20 | 20/20 | 2 | 0 | 0 | 0 | 0 |
| B4 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| B5 | 20/20 | 20/20 | 2 | 0 | 0 | 0 | 0 |
| E1 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| E2 | 20/20 | 20/20 | 2 | 1 | 0 | 0 | 0 |
| E3 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| E4 | 20/20 | 20/20 | 2 | 0 | 0 | 0 | 0 |
| E5 | 20/20 | 20/20 | 3 | 0 | 0 | 0 | 0 |
| F1 | 20/20 | 20/20 | 3 | 0 | 0 | 0 | 0 |
| F2 | 20/20 | 20/20 | 0 | 1 | 0 | 0 | 0 |
| F3 | 20/20 | 20/20 | 1 | 0 | 0 | 0 | 0 |
| F4 | 20/20 | 20/20 | 4 | 0 | 0 | 0 | 0 |
| F5 | 20/20 | 20/20 | 2 | 2 | 0 | 0 | 0 |
| I1 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| I2 | 20/20 | 20/20 | 1 | 0 | 0 | 0 | 0 |
| L1 | 20/20 | 20/20 | 3 | 0 | 0 | 0 | 0 |
| L2 | 20/20 | 20/20 | 1 | 0 | 0 | 0 | 0 |
| L3 | 20/20 | 20/20 | 0 | 0 | 0 | 0 | 0 |
| 合計 | 400/400 | 400/400 | 27 | 4 | 0 | 0 | 0 |

`manifest_ok=no`はなく、該当run IDはない。T2のsummary `status=ok`はexit statusと`recovery_finished`で決まり、manifest成功を意味しない（[fs-compare.sh:113-117](../../board/cardputerzero/tools/bench/fs-compare.sh#L113-L117)）。`recovered`と`manifest_ok`は別々に読み取る（[fs-compare.sh:164-167](../../board/cardputerzero/tools/bench/fs-compare.sh#L164-L167)）。

E5 repetition 8（`phase1-r3-t2-retry-T2-E5-r8-1794334721`）では、kernel printkが同じconsole行に続いたためsummaryの`recovered`値が`ok[`となった。元の行は`recovery_mount=ok[`で、後続に`manifest_ok=yes`と`recovery_finished`があるため、回復成功として数えた。

| 構成・run | 状態 | 秒 | points | setup points / mount fail / fsck fail | workload points / mount fail / fsck fail / loss |
|---|---|---:|---:|---|---|
| E1 `phase1-r3-t2-retry-T1-E1-r1-1794326508` | ok | 2,276 | 227 | 5 / 3 / 3 | 222 / 0 / 0 / 0 |
| I2 `phase1-r3-t2-retry-T1-I2-r1-1794326508` | operator stop | 4,183 | 107 | 59 / 49 / 49 | 48 / 0 / 0 / 0 |
| I2 `phase1-r3-t2-retry-T1-I2-r1-1794333024` | ok、attempt 2 | 16,600 | 310 | 56 / 46 / 46 | 254 / 0 / 0 / 0 |

I2のattempt 1は、disk headroom確保のためのmatrix停止で未完了となった。attempt 2はtimeout内に完了した。両attemptともsetup後のworkloadでmount/fsck失敗とlossは0。

## 捨てた試行と経緯

| 試行 | 経緯 |
|---|---|
| invalid `phase1-r3-t2` | 初回起動をDocker外で実行し、804 attemptsすべてが`exit_127`となった。QEMU起動前の失敗で、`mksquashfs.orig: not found`が原因。matrix結果には含めない。archive hashは「ログ」節に記録した。 |
| `phase1-r3-t2-retry`の初回 | 62/402 logical rows（58成功、4件が`terminated_signal_15`）で一度停止した。空きは48 GiBで、残行の容量を考慮してdisk fullを避けた。停止run IDは`phase1-r3-t2-retry-T2-E3-r18-1794330532`、`phase1-r3-t2-retry-T2-E3-r19-1794330583`、`phase1-r3-t2-retry-T2-E3-r20-1794330594`、`phase1-r3-t2-retry-T1-I2-r1-1794326508`。attempt 2は`phase1-r3-t2-retry-T2-E3-r18-1794333024`、`phase1-r3-t2-retry-T2-E3-r19-1794333024`、`phase1-r3-t2-retry-T2-E3-r20-1794333024`、`phase1-r3-t2-retry-T1-I2-r1-1794333024`として再実行し、すべて成功した。 |
| build dedup | runごとの`build/`だけをhardlinkで重複排除した。util-linux 2.41.3のsummaryは2,434,465 files、2,430,074 linked、3,668,618 filesとxattrsを比較、76.51 GiB saved、1,703.05秒。`df -B1`のfreeは50,521,534,464 bytesから136,597,553,152 bytesへ増加した（delta 86,076,018,688 bytes、80.16 GiB）。2つの容量値は未照合である。 |
| 容量 | dedup前後の`df`は同じfilesystem `/dev/md1p1`、total 499,472,506,880 bytes。usedは423,503,921,152から337,427,902,464 bytes、use率は90%から72%。matrix終了後のfreeは55,561,400,320 bytesで、25 GiBの停止閾値を下回らなかった。 |

| phase1-r2 runのrootfs | SHA-256（metadataと一致） |
|---|---|
| `phase1-r2-T2-E1-r1-1794292830` | `46b935183cb8397cad8e131c313a6a7fd92c25153be6c764a6d4837b0cabf17e` |
| `phase1-r2-T2-F3-r1-1794299216` | `34ee7139754e9add32cc2c942ffed39105265b4dfc02875d5f2fc0f8315af9cd` |
| `phase1-r2-T1-I2-r1-1794315353` | `26d63076926b98f131796f8e1112bd8b020f331fc647de6cd76855a5e3d3ed9b` |

matrixは2026-11-10 16:01:37 UTCに開始し、2026-11-11 00:19:03 UTCにclean exitした。dedupの停止時間を含むelapsedは8時間17分26秒、active matrix時間の合計は7時間38分34秒。host-loadは459 samplesで、1/5/15分の最大値は8.14/7.23/6.86。

## 結論

修正後のT2は全20構成でrecoveryとmanifest検査が20/20となった。phase1-r2の`manifest_ok`不足は、W2 ack race、fscrypt keyfileの非永続化、W3のmarker後tailを扱う判定経路の問題に対応した再測定で置き換える。回復数そのものはphase1-r2の値から変更しない。この結果だけでfilesystemの採否は決めない。

測定はQEMU上の仮想電源断試験であり、実microSDのFTL、write cache、物理電源断は検証していない。W2 in-flightとW3 tailの受け入れ条件は[T2 manifest再検査](2026-11-10-phase1-t2-manifest-recheck.md)を参照。

## 未確認の点

実SDカードのFTL、write cache、物理電源断後の状態は未確認である。SD imageとbuild treeはrun archiveに含まず、作業VM上にのみ残っているため、後日の利用可能性も未確認である。matrixのhost OS/kernel版とcontainer digestはrun metadataに記録されていない。

## ログ

生データは[data branch `data/fs-compare-experiments`](https://github.com/uist1idrju3i/MSD-Linux/tree/data/fs-compare-experiments)、commit `5d9cacf`に保存されている。

| archive / log | 参照先とSHA-256 |
|---|---|
| phase1-r3-t2-retry | [archive](https://github.com/uist1idrju3i/MSD-Linux/blob/data/fs-compare-experiments/fs-compare/phase1-r3-t2-retry.tar.zst)、`ecf3a040544671a07449a4134f355e84fe7b85f04f8df4916949acafba4d073f`。[files.sha256](https://github.com/uist1idrju3i/MSD-Linux/blob/data/fs-compare-experiments/fs-compare/phase1-r3-t2-retry.files.sha256)は2,845 filesを列挙する。 |
| invalid phase1-r3-t2 | [archive](https://github.com/uist1idrju3i/MSD-Linux/blob/data/fs-compare-experiments/fs-compare/phase1-r3-t2-invalid.tar.zst)、`82d3d03ef3fdd5fe97a78657e17ae250d4c8b48a863b528ab04fd3e94559e09f` |
| phase1-r2 | [archive](https://github.com/uist1idrju3i/MSD-Linux/blob/data/fs-compare-experiments/fs-compare/phase1-r2.tar.zst)、`5138e019255284911bbee38a3cddcdf350b0c62c6d17f6cca4c206ea6a46aa79` |
| hardlink log | [compressed log](https://github.com/uist1idrju3i/MSD-Linux/blob/data/fs-compare-experiments/fs-compare/misc/dedup-build-hardlink-20261111.log.zst) |

[raw CSV](2026-11-11-phase1-t2-rerun.csv)はmatrix summaryの406 attemptsをbyte-exactに保存する。SHA-256: `bda08330e0eba025c19f36a35d152abda80ad80187fe1562db4286446cab9570`。
