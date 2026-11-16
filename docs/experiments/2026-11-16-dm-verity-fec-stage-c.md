# B3 stage C：hash・parity・data境界の破損

[実験索引](README.md) / [事前登録・amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [host全43入力](2026-11-15-dm-verity-fec-host-dry-resume.md) / [先行B](2026-11-15-dm-verity-fec-stage-b.md)

## 条件と実行

2026-11-15〜16 UTC、Cの10条件を各1 bootのsmoke後、各5 boot実行しました。期待は全条件`normal-read`のままです。lower hash先頭・末尾のpanicは期待に反する結果として保存し、結果を見て期待を変更していません。clean入力はCに含まず、先行Bの通常/RAM clean成功後に実行しました。入力不一致・timeout・中断はありません。

standalone Docker cloneのsourceは`400ff62`から不変です。固定image、QEMU 11.1.2、研究kernel 6.18.59-v8-b3trace、Buildroot/GCC・host OSは先行Bと同じです。kernel/rootfsはwarm artifactを再利用し、reconfigure・再build・ccache測定はしていません。Bと同じcrc32c/roots8のclean packから、位置だけを変えて破損入力を生成しました。root hashは`3711f47a`、dataは5832 blockです。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  qemu-system-aarch64
run-qemu: sha256 bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69  Image
clean pack: fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205
Docker: sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d
```

binary hash行はserial実出力のパスだけ省略しました。全入力をhostで事前照合し、runnerもcaseごとにmanifestを照合しました。入力・出力は次のCLIで選び、実行中のscriptを変更していません。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-c output-c4-smoke --runs 1
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-c output-c4-formal --runs 5
```

`/prior`は保存入力のread-only mountです。QEMU環境変数と設定は固定source・case設定に、実cmdlineはserialに保存しています。bootごとのPopen argv/env全体の独立snapshotは未保存で、再現用のcase設定とは区別します。600秒/boot、入力不一致・clean失敗・未観測timeoutで停止する既定規則を維持しました。

## raw結果

smokeは8/10、正式は40/50期待一致でした。不一致はlower hash先頭・末尾の各smoke1件と正式5件で、すべてverity panicでした。全60件の非丸め値は[CSV](2026-11-16-dm-verity-fec-stage-c.csv)にあります。次表だけ小数第3位へ丸めています。

| case（C-接頭辞省略） | 正式5回のwall秒（repeat0→4） | 中央値［最小–最大］秒 | 期待一致 |
|---|---|---|---:|
| data-first | 245.125, 239.592, 243.638, 241.636, 252.783 | 243.638［239.592–252.783］ | 5/5 |
| data-last | 243.184, 234.113, 233.012, 233.740, 241.132 | 234.113［233.012–243.184］ | 5/5 |
| lower-head | 219.060, 204.467, 222.069, 216.051, 219.316 | 219.060［204.467–222.069］ | 0/5 |
| lower-tail | 232.951, 199.117, 171.374, 210.301, 219.955 | 210.301［171.374–232.951］ | 0/5 |
| parity-data-head | 224.936, 217.646, 239.184, 233.900, 217.663 | 224.936［217.646–239.184］ | 5/5 |
| parity-data-tail | 229.570, 232.435, 235.590, 235.217, 225.454 | 232.435［225.454–235.590］ | 5/5 |
| parity-head | 222.414, 229.850, 246.738, 233.538, 224.636 | 229.850［222.414–246.738］ | 5/5 |
| parity-tail | 239.713, 227.527, 233.152, 239.655, 232.222 | 233.152［227.527–239.713］ | 5/5 |
| post-parity | 238.023, 234.415, 242.408, 234.108, 244.327 | 238.023［234.108–244.327］ | 5/5 |
| superblock | 246.275, 229.454, 229.644, 237.115, 232.224 | 232.224［229.454–246.275］ | 5/5 |

成功40件は全mapper読取り完了→ready→loginを確認しました。全50件を証拠観測後にhost停止しており、最終exit 0を自然終了成功とは数えません。

## 仮説別の判定

**lower hash先頭・末尾の単一byteでも、panic方針では訂正後正常読取りにならない**という反証を各5回得ました。先頭はpack offset23896064、physical block5834、level0のdigest index0、末尾はoffset23919388、block5839、digest index5831です。どちらも正式全5回でguardを1回通りpanicへ進みました。例えば先頭のrepeat0は次の順でした。

```text
B3_ENTER id=1 type=1 block=5834 level=0 mode=3
B3_HASH id=1 data_block=1 level=1
B3_ENTER id=1 type=1 block=5834 level=1 mode=3
B3_GUARD id=1 level=1 result=-5
```

抜粋はtimestamp・共通prefixを省略しています。再入guardのmarkerを持つ実sourceと合わせ、Bで観測した経路がlower hash両端にも到達することを強く支持します。RS訂正能力だけで正常読取りを予測する仮説には反します。guard無効化対照や他hash/rootsのmetadata破損は試していません。

**data両端とparity＋対応dataは各5/5正常読取り**でした。data block0/5831のrepeat0、parity＋対応data両端のrepeat0でFEC enter・RS・exitを確認し、単に破損位置へ到達しなかった対照とは区別します。読み出した全data bytesは保存しておらず、host独立decoderのclean bytes比較と同じ判定ではありません。

**parityだけ・superblock・post-parityは各5/5正常読取り**でした。各repeat0ではFEC enter/RSがなく、parity修復の実証ではありません。superblockはoffset23887872、parityの先頭/末尾は23920640/24707071、post-parityは24707072です。superblockと範囲外はFEC columnを持たず、cmdlineでmapper tableを指定する本条件での観測に限定します。範囲外bytesやsuperblockの一般的なintegrityを保証しません。

全位置のbyte/block、tree level、digest index、FEC column/symbol、変更前後bytesはarchiveの`inputs/*/case.json`にあります。既知消失位置を与えるhost検査はkernelの未知誤り訂正とは区別します。

## 保存・検査・予算

[archive](2026-11-16-dm-verity-fec-stage-c/evidence.tar.gz)は244 member、1,761,010 byte、SHA-256 `6501a5846f40978157f125391849f47e972241591218eba5e3a25756dae5e244`です。全memberを再読込みしてhash照合しました。60件のserial/QMP/判定、全caseの設定・manifest・位置、固定source、driver log・計時、collector、summaryを保存しています。共通image本体は[host archive](2026-11-15-dm-verity-fec-host-dry/evidence.tar.gz)、新initramfsとkernel trace/configは先行Bのarchiveを参照します。

```text
ok - stage C: 60 trials, 50 formal, 40 formal matches; 244 members hash-verified
formal_boot_wall_sum=11511.65046835682
wall_seconds=11540.900
```

smokeのdriver wallは2375.707秒、正式は**11540.900秒（3時間12分20.900秒）**です。終了時の保守的累積時計は約14時間20分。残りD〜Fは23 smoke＋115正式bootを240秒/boot、準備2時間として、累積約25時間半を見込みます。deadlineは2026-11-17 00:17:52 UTC、36時間上限の延長は不要です。wall値はhost資源の消費記録で、実機の性能比較に転用しません。

文書検査・yomiyasuの結果は本段階のcommit・報告に添付します。host fixture後からbench sourceは不変で、追加ShellCheckは不要です。既知のmodule署名拒否はrawに保持し、全module loadや製品bootの合格にはしません。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認。RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。
