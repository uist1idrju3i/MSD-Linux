# B3 stage E：9/24 block破損の集中と分散

[実験索引](README.md) / [事前登録・amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [host全43入力](2026-11-15-dm-verity-fec-host-dry-resume.md) / [先行D](2026-11-16-dm-verity-fec-stage-d.md)

## 条件と実行

2026-11-16 UTC、crc32c/roots8の4条件を各1 bootのsmoke後、各5 boot実行しました。期待は集中9/24 blockが`verity-panic`、分散9/24 blockが`normal-read`のままです。入力不一致・timeout・失敗・中断はありません。監視には再接続しましたが、稼働中のcontainer・process・script・入力は変更も再起動もしていません。Cのlower hash両端の期待不一致は先行結果として保持します。

standalone Docker cloneのbench sourceは`400ff62`から不変で、記録再開時のbranch HEADは`6577a1b`でした。固定image、QEMU 11.1.2、研究kernel 6.18.59-v8-b3trace、Buildroot/GCC・host OSは[正式B](2026-11-15-dm-verity-fec-stage-b.md)と同じです。kernel/rootfsはwarm artifactを再利用し、reconfigure・再build・ccache測定はしていません。Bと同じclean pack、root hash `3711f47a`、data 5832 block、4 KiB/blockです。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  qemu-system-aarch64
run-qemu: sha256 bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69  Image
clean pack: fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205
Docker: sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d
```

binary hash行はserial実出力のパスだけ省略しました。各blockのbyte 0をXOR `0xff`で反転し、集中はblock `24*i`、分散はblock `i`（`i=0..8`または`0..23`）を選びます。前者のFEC columnはすべて`[0,0]`、後者は`[i,0]`で、同じcodeへの負荷を変えています。全offset、前後byte、block、column/symbolはarchiveのcase設定にあります。旧F2の注入条件やrawは変更していません。

全入力をhostで事前照合し、runnerもcaseごとにmanifestを照合しました。保存入力はread-onlyの`/prior`、結果はfresh出力先です。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-e output-e4-smoke --runs 1
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-e output-e4-formal --runs 5
```

panic mode、watchdog driver無効、`-no-reboot`、600秒/bootです。QEMU環境変数は固定source・case設定、実cmdlineはserialに保存しました。bootごとのPopen argv/env全体の独立snapshotは未保存です。入力不一致・clean失敗・未観測timeout・判断を要する計測器失敗で停止する規則を維持しました。E自体にclean条件はなく、先行B/Dのclean成功後に実行しています。

## raw結果

smokeは4/4、正式は20/20期待一致でした。全24件の非丸め値は[CSV](2026-11-16-dm-verity-fec-stage-e.csv)にあります。次表だけ小数第3位への丸めで、全条件5/5期待一致、guard hitは0です。

| case（E-接頭辞省略） | 正式5回のwall秒（repeat0→4） | 中央値［最小–最大］秒 |
|---|---|---|
| 24-concentrated | 212.040, 210.504, 225.283, 211.189, 208.878 | 211.189［208.878–225.283］ |
| 24-dispersed | 270.862, 275.648, 280.079, 282.035, 285.432 | 280.079［270.862–285.432］ |
| 9-concentrated | 206.807, 200.340, 210.338, 219.107, 212.691 | 210.338［200.340–219.107］ |
| 9-dispersed | 256.552, 255.205, 255.811, 264.129, 244.946 | 255.811［244.946–264.129］ |

集中の正式10件はverity固有panic、分散の10件はreadall完了→ready→loginでした。全24件で証拠観測後にhost停止しており、最終exit 0は自然終了成功の根拠ではありません。smokeを正式反復に混ぜていません。

## 仮説別の判定

**試した9/24 blockについて、同column集中はpanic、異column分散は訂正後の正常読取りという期待を各5回支持**しました。破損block総数だけでなくcodeごとの負荷を区別する必要があります。全column・全byte位置・全patternの保証ではありません。

集中の全正式10件で、RSの位置なし試行が`result=-74`、消失位置あり試行が`neras=8 result=8`、その後の`failed to correct (8 erasures)`と`B3_EXIT ... result=-84`を観測しました。代表は9-concentrated repeat0です。

```text
B3_PHASE id=1 rsb=0 erasures=0
B3_RS id=1 column=0 neras=0 result=-74
B3_PHASE id=1 rsb=0 erasures=1
B3_RS id=1 column=0 neras=8 result=8
FEC 0: failed to correct (8 erasures)
B3_EXIT id=1 level=1 result=-84
data block 0 is corrupted
Kernel panic - not syncing: dm-verity device corrupted
```

timestamp・共通prefixを省略しました。再入guardは0回なので、Cのlower hash破損と同じguard経路だけでは説明できません。[Dで照合した同じkernel source](2026-11-16-dm-verity-fec-stage-d.md)では、上の`failed to correct`は復号候補のhash比較不一致から出ます。RS正値だけを完全回復とはしていません。

分散の全正式10件には`B3_RS ... result=1`と`B3_EXIT ... result=0`があり、FECを使わず単に起動しただけではありません。ただしQEMU内の候補block全bytesをdumpしてhostのclean参照と比較したわけではなく、host独立decoderの全bytes回復判定とは区別します。

## 保存・検査・予算

[archive](2026-11-16-dm-verity-fec-stage-e/evidence.tar.gz)は118 member、1,119,573 byte、SHA-256 `fe5e85f7327fd34b9fc1497c59d1614a7e19c474cf51cc1f828c337af52bc8d6`です。全memberを再読込みしてhash照合しました。全24件のserial/QMP/判定、case設定・入力manifest・注入位置、固定source、driver log・wall、collectorとsummaryを保存しています。入力本体の再構成に用いる共通packはhost記録のarchiveを参照します。

```text
ok - stage E: 24 trials, 20 formal, 20 formal matches; 118 members hash-verified
formal_boot_wall_sum=4787.875741162046
wall_seconds=4799.697
```

smoke driver wallは980.684秒、正式は4799.697秒（1時間19分59.697秒）です。E終了時の保守的累積時計は約23時間2分。残りFの1 smoke＋5正式を600秒/boot、保存・検査に1時間を予約しても累積約25時間2分の見積りです。deadlineは2026-11-17 00:17:52 UTCのままで、36時間上限の延長は不要です。wallはhost資源の記録で、実機性能ではありません。

文書検査とyomiyasuの結果は本段階のcommit・報告に添付します。bench sourceはhost fixture後から不変で、追加ShellCheckは不要です。既知のmodule署名拒否はrawに残し、正常製品boot・全module loadとは区別します。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認。RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。
