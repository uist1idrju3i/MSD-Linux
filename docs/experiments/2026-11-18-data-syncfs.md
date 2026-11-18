# /data初期設定末尾のsyncfs

- 状態: 最終版の初回・起動時間・second boot各5回を完了。QEMUで事前基準を満たした
- 基準: `9e89357a1df590ff0c85f4e8fd952f635bcc5129`。実行前に入力hashとsourceの写しを保存
- 関連: [残量の帰属](2026-11-17-data-idle-residual.md)

## 目的と事前基準

grow・mkdir後のsyncfsが、journal commitだけでなくmetadataの本来位置へのwritebackを待つか検証する。最初に未変更imageのRAM上でhelperを呼ぶpilotを行う。boot counterに従って切り分けたtraceで、既知の11 metadata blockがsyncfs終了前へ移り、120秒idleのp7が0でなければ製品への組込みを停止する。

pilot合格後、同じwarm tree・kernel・QEMU・計測器でbefore/after各5回、初回起動のboot・idle1・idle2を測る。idleは各120秒。変更後の全5回で両idleが0、RAM対照0、disk正対照2,048 sector以上を採否基準とする。起動時間の絶対値と差も記録し、実機性能とは扱わない。

拡張・directory作成済みのsecond bootもbefore/after各5回測り、同期を省略できることと追加費用を確認する。同期失敗はhost fault injectionで非zeroと診断を確認する。実SD・電源断・LCDとprogressは未確認のままとする。失敗した試行も保存し、既存の出力は上書きしない。

## 時間計測の追加登録

元runnerのboot snapshotはlogin後のhook転送も含むため、起動時間の代用にはしない。旧runnerを変更せず、`run-timed.py`の写しでQEMU launcher起動からlogin promptまでのmonotonic wall時間を記録する。provenanceの入力hash計算も含む値であり、kernel内だけの時間ではない。初回起動はこの写しでbefore/after各5回、idleを1秒1窓として時間だけを追加測定する。second bootは同じ写しで各5回、120秒1窓とする。正式な初回idleの採否は元runnerの120秒2窓で行う。

second bootの入力は共通の拡張済みp7を使い、disk正対照fileを除去してoffline fsckでcleanにする。before/afterで同一p7を使うことで、前回runnerの強制終了によるrecovery差を起動時間へ混ぜない。

## 実行条件と事前登録との差

beforeは基準commitのS02、afterは末尾同期を加えたS02です。helper packageはpilotのため双方のrootfsへ収録し、beforeのS02からは呼びません。事前登録に書いたRAMへのhelper投入ではなく、S02以外のpackageを揃える方式にしました。純粋なmain imageとの比較ではなく、S02の変更による差を測ります。

Buildrootの同じwarm treeで両imageを作り、kernel・DTBを共通にします。通常のgenimageが作った64 MiBのp7を1 GiBのSD imageで初回起動し、352 MiBまで広げます。全runにQEMU block write traceを付け、各runのSDは独立した写しです。予備v1の120秒測定はbefore/afterを交互に5回ずつ実行しました。最終版は後述の再登録条件で測ります。時間測定は別の交互5回で、短いidleを遅延writebackの採否には使いません。

固定版はQEMU 11.1.2、Linux `6.18.59-v8`（source `b3495ea401d709af0701a85babcba5e3d788a602`）、BusyBox 1.38.0、e2fsprogs 1.47.4、target GCC 14.3.0です。ImageのSHA-256は`c651cfd86fcb08943a863ecbc31f6fa0f2f6fea0f7c7bcd25fc8e3cdd327c261`、DTBは`f6c9ee59ccc5adb164ddba6508acc99e8038d2fe2017bd1f5fd5567af4999094`です。rootfs・SD・container・生成configのhashは証拠内に保存します。

second bootはpilotのp7を取り出し、offline fsck、正対照fileの除去、再fsckを行った共通のclean imageを使います。p5/p6へ各variantのrootfsを入れ、p7の同一性を維持します。実際に1回目を起動して強制終了した直後のrecovery costではなく、拡張・directory作成済みでcleanな起動の比較です。

既存post-buildはQEMU読取り順のsortlistをmksquashfsへ渡します。両buildで`Cannot stat sortlist entry "etc/default/seedrng"`などの警告が出ました。固定containerとBuildroot toolは動作しており、原因は現在のrootfsにない項目が既存sortlistに残ることです。実験間でsortlistを変えず、警告も保存します。

## 方式とhome-locationの確認

[一次資料による比較](../research/storage/data-syncfs.md)から、小さいC helperを選びました。globalな`sync()`は対象を限定できず、戻り値でwriteback errorも通知できません。固定BusyBox 1.38.0は`FEATURE_SYNC_FANCY`が無効で、有効にしても`sync -f /data`が`syncfs()`のerrorを捨てます。helperは`open`・`syncfs`・`close`の失敗を診断して非zeroを返し、S02も同期失敗を記録して終了1とします。target上のhelperは5,920 byteです。他方式のbinary sizeは比較していません。

先に行ったpilotでは、helper前のp7 counterが16,848、戻った後が16,936 sectorで、差は88でした。in-flightは境界で0です。traceをcounterで切ると、次のhome-locationがそれぞれ8 sectorずつ、helperが戻る前に書かれています。journal領域へのcommitだけでは説明できません。その後の120秒idleは0、RAM対照0、disk正対照2,112 sectorでした。

| 対象 | p7内の4 KiB block | sector |
|---|---|---:|
| directory | 10、2097、2098 | 24 |
| bitmap | 9、25、32779 | 24 |
| inode table | 41、32781 | 16 |
| superblock | 0、32768 | 16 |
| GDT | 1 | 8 |
| 合計 | 11 block | 88 |

blockの用途は前回の帰属と一致し、今回の`dumpe2fs`・`debugfs`でもdirectory・各group・journal inodeの配置を保存しました。helperはfilesystem内のpending writebackを待つもので、実SDの内部cacheやFTLの永続性を証明しません。

## 予備試行v1: df判定での初回5回

単位は512 byte sectorです。bootはhookの最初のsnapshotまでの累積値で、boot時間ではありません。両idle窓は各120秒sleepです。

| 反復 | before boot | after boot | before idle1 | after idle1 | idle2（双方） |
|---|---:|---:|---:|---:|---:|
| 1 | 16,848 | 16,968 | 88 | 0 | 0 |
| 2 | 16,880 | 16,936 | 88 | 0 | 0 |
| 3 | 16,880 | 16,936 | 88 | 0 | 0 |
| 4 | 16,848 | 16,936 | 88 | 0 | 0 |
| 5 | 16,880 | 16,936 | 88 | 0 | 0 |

全10回のRAM対照は0、disk正対照は2,112 sectorでした。idleへの88 sectorをboot側へ移せましたが、総量を減らしたとは結論しません。boot＋idleの総量は双方16,936〜16,968 sectorです。r1のafterとbeforeの総量差32 sectorは、journal内のphysical block 15、1072〜1074への各8 sectorでした。beforeの反復間にも32 sectorの差があり、すべてをhelper固有の増加・削減とは扱いません。

このv1ではgrow前後の`df -Pk`を比較していました。しかしext4の値はmetadata overheadを差し引くため、最終版はsuperblockの実block数を`dumpe2fs -h`で読みます。途中だったv1時間測定はcontainerを停止して中断し、失敗した試行を含めて保存します。v1を最終版の5回測定に数えず、最終imageで測り直します。

再登録した最終測定では、counter測定のbefore/afterを1組ずつ同時に起動し、組を5回繰り返します。両variantの条件は同じ2 VMです。初回idleは120秒2窓、起動時間は別途1 VMで交互5回、second bootも1 VMで交互5回・120秒1窓とします。時間測定をcounter測定やbuildと並行させません。実block数の検出不能・grow失敗・mkdir失敗は保守的に同期し、fsck修復も同期します。

## 補助確認: directoryが既にある未拡張p7

genimageの64 MiB p7へhostのdebugfsで`/etc`と`/msd-update`を作り、offline fsck後に最終S02で起動しました。guestのfsckは`data: clean, 14/16384 files`で、formatやdirectory不足によらずgrowの変更を検出するケースです。helperは1回呼ばれ、boot 16,792、120秒idle 0、RAM対照0、disk正対照2,112 sectorでした。最初から両directoryがある通常のgrowでも同期することを確認しました。この1回は主比較の5回には数えません。

## 最終版の初回5回

| 反復 | before boot | after boot | before idle1 | after idle1 | idle2（双方） |
|---|---:|---:|---:|---:|---:|
| 1 | 16,880 | 16,968 | 88 | 0 | 0 |
| 2 | 16,880 | 16,968 | 88 | 0 | 0 |
| 3 | 16,848 | 16,968 | 88 | 0 | 0 |
| 4 | 16,848 | 16,936 | 88 | 0 | 0 |
| 5 | 16,880 | 16,936 | 88 | 0 | 0 |

全10回のRAM対照は0、disk正対照は2,112 sectorでした。afterのhelperは各1回です。boot平均はbefore 16,867.2、after 16,955.2 sectorで88増え、boot＋idleの平均は双方16,955.2 sectorでした。idleを起動の同期内へ移した結果で、総量を減らす変更ではありません。

## 初回の起動時間

単位は秒、表示は小数第3位までです。生の精度はCSVに残します。launcherからloginまでの値で、driverによるSD copy・事前hashは含みません。launcher自身のhash処理は含みます。

| 反復 | before | after | 差（after - before） |
|---|---:|---:|---:|
| 1 | 33.870 | 34.120 | 0.250 |
| 2 | 34.409 | 33.767 | -0.643 |
| 3 | 34.618 | 36.041 | 1.423 |
| 4 | 34.845 | 35.309 | 0.464 |
| 5 | 33.664 | 36.684 | 3.021 |

中央値は34.409から35.309秒で差は+0.900秒、対応する反復差の中央値は+0.464秒でした。差の範囲は-0.643〜+3.021秒です。n=5のばらつきがあり、helper syscallだけの費用や統計的な有意差、実機の起動時間とは扱いません。

## 拡張・directory作成済みのsecond boot

| 反復 | before秒 | after秒 | 差（after - before） |
|---|---:|---:|---:|
| 1 | 28.262 | 30.216 | 1.955 |
| 2 | 28.967 | 29.924 | 0.957 |
| 3 | 28.988 | 29.016 | 0.029 |
| 4 | 27.479 | 28.370 | 0.891 |
| 5 | 26.477 | 28.496 | 2.018 |

中央値は28.262から29.016秒で差は+0.755秒、対応する反復差の中央値は+0.957秒でした。同期helperは全10回で呼ばれず、afterでは判定用の読取りが加わります。差の範囲は+0.029〜+2.018秒で、実機の費用や判定コマンドだけの費用とは断定しません。

p7のbootは双方全5回24 sector、120秒idleは0でした。RAM対照0、disk正対照は全回2,120 sectorです。同期を省略してもmount等の既存boot書き込みまで0になるわけではありません。second bootのidle2は測っていません。

最終30 runのtrace総量と各idle窓をguest counterに照合し、全snapshotのin-flight 0、全RAM対照0、全disk正対照2,048 sector以上を確認しました。afterの正式な初回5回は、11 home-location block全てがboot内に書かれています。時間だけの初回1秒窓を120秒idleの成功例には数えていません。

## 再実行する時のコマンド

以下はrepo rootから固定containerで実行します。`INPUT`はkernel・DTB・rootfs・SDと`.config`を持つBuildroot形式の入力directory、`NEW_DIR`は未使用のrun directoryです。入力hash・生成config・sourceの写しは証拠archiveで照合します。beforeは基準S02を使い、helper packageはafterと同じです。

```sh
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-openssl-lts msd_cardputerzero_defconfig && make -C output-openssl-lts -j8'
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output INPUT --run-dir NEW_DIR --variant VARIANT \
  --seconds 120 --windows 2 --trace-writes \
  --guest-script board/cardputerzero/tools/bench/write-inventory/residual-guest.sh
```

最終のcounter測定はbefore/afterを同時に1組起動して両者のexit 0を待ち、5組です。起動時間は旧runnerを変更しない`run-timed.py`の写しを使い、`--seconds 1 --windows 1`でbefore/afterを交互に5回ずつ。second bootは同じ写しの`--seconds 120 --windows 1`で交互5回ずつです。全て`--trace-writes`と同じguest scriptを指定しました。

共通p7の準備はpilotのSDから4 MiB単位でskip 168・count 88を抽出し、固定host e2fsprogsの`e2fsck -fy`、`debugfs -w -R 'rm /.msd-write-probe'`、再度`e2fsck -fy`です。そのp7を保ち、p5/p6だけを各variantのrootfsへ置換しました。最終afterのp7とbeforeのp7はbyte一致し、SHA-256は`174d74d760afb0d9ef05508c5c89dab7f3143640c7b957f2fbf1ccbcd25985ae`です。

## 残る範囲

既存runnerのmarker後にVMを停止する方式を使いました。終了判定器は改修しておらず、正常shutdown・電源断試験とは扱いません。fs-compare新版、dm-verity/FEC、kernel設定、mount optionは変更していません。実SDの内部cache・FTL、実機性能、power cut、既存SDの未zero tableは未確認です。LCDでの英日progress・中断可否の表示も未実装です。今回のidle 0は書き込み規則への適合を意味せず、write-policyの未対応を維持します。

## buildとhost確認

固定containerでtargetのbuild、A/B両rootのQEMU起動、7 partitionの8192 sector alignment検査が終了0でした。init-scriptを含むaggregate host testsは10 suite全て成功です。helperのopen・syncfs・close失敗、S02の同期失敗、変更なし・検出不能・部分失敗の分岐をhostで確認しました。write-inventoryの21 testとshellcheck-trackedも成功しました。画面の視覚確認はしていません。

## 保存した証拠

[run別CSV](2026-11-18-data-syncfs.csv)は最終30 runのp7累積・差分・起動時間です。[証拠archive](2026-11-18-data-syncfs.evidence.tar.gz)には各deviceのraw.csv、serial、QEMU trace、事前登録、source・生成configの写し、入力hash、build log、集計器を入れました。予備v1・pilot・中断した時間測定も残しています。v1の`timing-before-r5`は判定器の変更ではなく、df判定を取り替えるためcontainerを止めた試行で、controller exitは137です。最終結果には含めません。

archiveは357 fileを読み戻し、全fileのSHA-256・byte数・mtime_nsをmanifestと照合しました。4,201,970 byte、SHA-256は`4b9a246ec3f3d376fd2364cda91fe329d2028f3fcef9a2a0949e04d86442d2ff`です。大きいkernel・DTB・rootfs・SDはarchiveに入れず、`input-binaries.json`にhashとbyte数を収録しました。元入力は削除していませんが、repositoryだけから同じUUID等を含むimageをbit単位で再現できるとはしません。

warm treeにあったmksquashfs wrapperとsortlistの写しも保存しています。再build時はその差分も確認が必要です。imageは基準commitと保存したsource差分でbuildしたもので、最終commit名を埋めた再buildではありません。
