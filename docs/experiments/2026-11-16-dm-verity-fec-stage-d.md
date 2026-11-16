# B3 stage D：hash方式・rootsと容量超過

[実験索引](README.md) / [事前登録・amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [host独立復号](2026-11-15-dm-verity-fec-host-dry-resume.md) / [先行C](2026-11-16-dm-verity-fec-stage-c.md)

## 条件と実行

2026-11-16 UTC、crc32c/SHA-256×roots2/8/16×clean/data1 byte/容量超過の18条件を各1 smoke、各5正式boot実行しました。超過条件は同じFEC columnのR+1 symbol（roots2/8/16で3/9/17 block）です。cleanとdataは`normal-read`、超過は`verity-panic`という事前期待を維持しました。smokeのclean6条件すべてが成功してから正式を開始し、正式もclean30件を先に実行しました。入力不一致・clean失敗・timeout・中断はありません。

standalone Docker cloneのbench sourceは`400ff62`から不変です。固定Docker image、QEMU 11.1.2、研究kernel 6.18.59-v8-b3trace、host OS・Buildroot/GCCは[先行B](2026-11-15-dm-verity-fec-stage-b.md)と同じです。kernel/rootfsはwarm artifact再利用で、reconfigure・再build・ccache測定はしていません。Dの6 packはhost再検査で生成・独立検査済みです。data bytesは共通で、hash方式・rootsに応じたtree/parity/mapper設定を使用しました。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  qemu-system-aarch64
run-qemu: sha256 bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69  Image
Docker: sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d
crc32c root: 3711f47a
SHA-256 root: ff515c66942eae031137172e6a4d6916cf4e7cdd93d48321d7fca1827ab9e0e5
```

binary hash行はserial実出力のパスだけ省略しています。各入力manifestを実行前に照合し、新しい出力先を使いました。実行中script・入力・期待は変更していません。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  output-d2 output-d4-smoke --runs 1
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  output-d2 output-d4-formal --runs 5
```

固定sourceとcase設定にQEMU環境変数、serialに実cmdlineを保存しました。bootごとのPopen argv/env全体の独立snapshotは未保存です。600秒/boot、入力不一致・clean失敗・未観測timeoutで停止する規則はB/Cと同じです。

## raw結果

smokeは18/18、正式は90/90期待一致でした。全108件の非丸め値は[CSV](2026-11-16-dm-verity-fec-stage-d.csv)にあります。次表は小数第3位への丸めで、全行5/5期待一致です。c=clean、d=data、o=容量超過を表します。

| hash・roots・条件 | 正式5回のwall秒（repeat0→4） | 中央値［最小–最大］秒 |
|---|---|---|
| crc32c・16・c | 230.625, 225.232, 240.414, 236.663, 248.485 | 236.663［225.232–248.485］ |
| crc32c・16・d | 250.882, 232.197, 244.166, 239.399, 246.821 | 244.166［232.197–250.882］ |
| crc32c・16・o | 221.614, 208.933, 215.423, 212.208, 215.850 | 215.423［208.933–221.614］ |
| crc32c・2・c | 237.932, 227.056, 245.512, 224.570, 227.513 | 227.513［224.570–245.512］ |
| crc32c・2・d | 237.920, 253.115, 232.091, 227.214, 232.675 | 232.675［227.214–253.115］ |
| crc32c・2・o | 220.554, 219.833, 203.995, 208.459, 221.629 | 219.833［203.995–221.629］ |
| crc32c・8・c | 224.463, 240.665, 234.266, 235.007, 235.268 | 235.007［224.463–240.665］ |
| crc32c・8・d | 248.321, 243.115, 254.714, 239.918, 239.914 | 243.115［239.914–254.714］ |
| crc32c・8・o | 206.990, 217.496, 212.623, 224.825, 219.003 | 217.496［206.990–224.825］ |
| SHA-256・16・c | 223.071, 226.897, 232.632, 231.547, 228.570 | 228.570［223.071–232.632］ |
| SHA-256・16・d | 232.192, 220.357, 242.997, 239.230, 243.042 | 239.230［220.357–243.042］ |
| SHA-256・16・o | 226.637, 208.012, 226.667, 221.377, 225.359 | 225.359［208.012–226.667］ |
| SHA-256・2・c | 225.889, 246.905, 243.379, 238.704, 231.158 | 238.704［225.889–246.905］ |
| SHA-256・2・d | 230.048, 245.914, 244.168, 232.461, 244.361 | 244.168［230.048–245.914］ |
| SHA-256・2・o | 205.562, 214.626, 213.645, 210.678, 218.730 | 213.645［205.562–218.730］ |
| SHA-256・8・c | 230.223, 236.982, 238.959, 234.850, 232.900 | 234.850［230.223–238.959］ |
| SHA-256・8・d | 236.496, 250.765, 242.344, 238.251, 232.350 | 238.251［232.350–250.765］ |
| SHA-256・8・o | 214.520, 202.871, 220.547, 223.336, 205.060 | 214.520［202.871–223.336］ |

clean/dataの正式60件は全mapper読取り完了→ready→login、超過30件はverity panicで、全90件のguard hitは0でした。すべて証拠観測後にhost停止しており、最終exit 0は自然終了成功の根拠ではありません。

## 仮説別の判定

**hash/rootsを変えた6構成でclean・1 byte訂正・R+1超過panicの期待を各5回支持**しました。これは試した入力の反復結果で、全破損patternの容量限界を測った結果ではありません。R/2、R/2+1、R、R+1と混合誤り/消失境界はhost独立codecの記録を参照します。QEMUでその全境界を試したとはしません。

**roots2の超過では、RSの正の戻り値だけではintegrityを判定できないことをQEMUでも観測**しました。crc32c/SHA-256とも正式5/5で、次の順を確認しました。

```text
B3_PHASE id=1 rsb=0 erasures=0
B3_RS id=1 column=0 neras=0 result=1
FEC 0: failed to correct (0 erasures)
B3_PHASE id=1 rsb=0 erasures=1
B3_RS id=1 column=0 neras=2 result=2
FEC 0: failed to correct (2 erasures)
B3_EXIT id=1 level=1 result=-84
```

抜粋はSHA-256 repeat4からtimestamp・共通prefixを省略しました。B archiveの実kernel source `kernel/drivers/md/dm-verity-fec.c`では、`fec_decode_rsb()`が復号したblockを`verity_hash()`で再計算し、期待hashとの`memcmp()`不一致だけが上の`failed to correct`を表示して`-EILSEQ`（-84）を返します。`verity_fec_decode()`は消失位置なしの試行が負なら位置ありで再試行し、両方失敗した経路で`B3_EXIT`を出します。runtimeの両error行により、単に到達可能なsourceを見ただけでなく、この比較不一致の実行を確認しました。guardが0回という対照により、B/Cの再入guardだけでpanicを説明する仮説を除外できます。

hostでは同じroots2超過入力が独立decoderで別codewordとなりました。ただしkernelの候補bytesはdumpしておらず、host候補とkernel候補の全bytes一致は未確認です。QEMUの成功readも、hostの候補imageとclean全bytes比較とは区別します。

RS能力超過の誤訂正は想定される挙動です。veritysetup終了0/repairableやRS正値をintegrityの証明にせず、kernelのFEC後hash再検査を防御として扱う設計上の示唆を維持します。従来のhost限定の観測に、本条件のQEMU拒否経路を追加したもので、製品適合・全誤訂正の拒否・crc32cの暗号学的保証・実機検証を主張しません。

## 保存・検査・予算

[archive](2026-11-16-dm-verity-fec-stage-d/evidence.tar.gz)は412 member、3,167,895 byte、SHA-256 `5ba4d7d0e0d84c1636e0e504a0070d85d0ea04f23358f7ea8d2ecf90382077c3`です。全memberを再読込みしてhash照合しました。全108件のserial/QMP/判定、case設定・入力manifest・注入位置、固定source、driver log・wall、collectorとsummaryを保存しています。6 packの共通dataとsuffix、独立復号・CLI・中間結果はhost記録のarchiveを参照します。CLIは観測値だけで、回復判定には独立候補とclean参照の全bytes一致を要求する規則は不変です。

```text
ok - stage D: 108 trials, 90 formal, 90 formal matches; 412 members hash-verified
formal_boot_wall_sum=20680.84396872096
wall_seconds=20734.782
```

smoke driver wallは4175.688秒、正式は20734.782秒（5時間45分34.782秒）です。終了時の保守的累積時計は約21時間22分。残りE/Fは5 smoke＋25正式bootを240秒/boot、準備1時間で、累積約24時間半の見積りです。deadlineは2026-11-17 00:17:52 UTCのまま、36時間上限の延長は不要です。wallはhost資源の記録で、実機性能ではありません。

文書検査とyomiyasuの結果は本段階のcommit・報告に添付します。bench sourceはhost fixture後から不変で、追加ShellCheckは不要です。既知のmodule署名拒否はrawに残し、正常製品boot・全module loadとは区別します。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認。RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。
