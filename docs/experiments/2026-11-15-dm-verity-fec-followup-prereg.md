# B3追試の事前登録

- 状態: 計画（harness拡張・追試は未実施）
- 日付: 2026-11-15
- 担当: Devin
- 関連: [旧B3](2026-11-15-dm-verity-fec-corruption.md)、[RS由来の初期監査](../research/storage/rs-formatter-provenance-2026-11-15.md)

利用者は2026-11-15の本sessionで、provenance監査と並行するRS formatterの**研究限定利用**を承認しました。製品への組込み・出荷は監査完了まで禁止のままです。旧B3の期待と結果は変更しません。

## 目的・根拠

検討基準`1a45089`、登録基準はmain `cc4a9522999b22f6bf00c38bb9650678369d8309`です。[v2期待表](../../board/cardputerzero/tools/bench/dm-verity-fec/expectations-v2.tsv)・runner・verdict、旧B3、[訂正記録](../research/storage/storage-integrity-corrections.md)、[root設計](../research/storage/rootfs-squashfs-verity-fec-design.md)に基づきます。旧raw/CSV/F3旧ready期待は保存します。

## 開始条件

- RS移植元revision・著作権・改変・配布条件の監査を並行します。利用者承認は研究限定で、監査前の製品出荷は禁止です。違反とは断定しません。
- standalone cloneのDockerで実施。commit/patch、kernel/config、QEMU/OCI/compiler/formatter、入出力hash、cmdline、cache状態を固定・保存する。
- `tests/dm-verity-format/run.sh`を通す。SHA-256はveritysetup、crc32c/FECは独立codecで照合。同じRS実装の再計算だけでは合格にしない。
- generator入力は`BASE/V0/rootfs.squashfs`・V0 sdcard/DTB・`BASE/T0/images/Image`。F0から生成し、新規case/results先だけを使う。旧binary cacheは禁止。
- 現行generatorはcrc32c/roots8・F0〜F6限定。EIO、initramfs、任意注入・roots/hash、reset観測の拡張は承認後に実装する。

| 固定・採取する条件 | 登録時の扱い |
|---|---|
| OS/QEMU | Ubuntu。開発imageのQEMU 11.1.2を検討時に確認。実行時にOS版、binary hash、OCI digestを再採取 |
| Buildroot/kernel | submodule `75f325ad84251ee9d903467f84d3683e3bcf3fd5`、旧B3のkernel 6.18.59。計装kernelは別buildしconfig/patch/hashを保存 |
| GCC/codec | 実行に使うcompiler binaryの版・hashを開始前に採取。独立codec照合は未実施 |
| 変更する条件 | 表A〜Fのmode・読取り経路・注入領域・roots・hash |
| 維持する条件 | 4K、固定salt、同一のclean data、icount shift=0、QEMU raspi3ap。機能比較で性能採否を決めない |
| 初回・失敗 | boot0も保存。欠損・中断・timeoutを除去せず、成功時間へ混ぜない |

## F3: 仮説と反証する測定

旧条件はD=5832、H=5833、hash 7 block、roots=8。F3は`H*4096+17=23891985`（topのdigest index 4）。新imageでは値を固定せずparamsとtreeから再計算する。

| 仮説 | 判別する測定 |
|---|---|
| 注入位置・入力不一致 | cleanとの差分とp5抽出を照合。offset/before/after、物理block、tree level/digest、FEC論理番号を保存。1 byte以外の差なら停止 |
| 容量超過・parity欠陥 | 同columnを独立decodeしerrors/erasuresを数える。単独top破損は容量内の候補。RS到達前の停止とdecode失敗を区別する |
| top依存の再入 | 6.18.59の`verity_fec_decode`内`fio->level` guard、`fec_decode_rsb`→`verity_hash_for_block`→`verity_handle_err`の経路を確認。io ID/type/block/level、rsb/column、neras、decode戻り値・modeをtraceし、nested guardへの到達を測る |
| panicが回復前に停止 | 同じbytesでpanic/restart/EIO（両flagなし、option数も修正）を比較。両flag併記禁止。EIOでnested失敗後に回復なら支持、独立decode失敗・guard未到達なら反証 |
| initの読取り経路 | 通常mount後readallと、RAM initramfsから未mount dm-0の指定offset→全readを比較。mount・init読取り前後にmarker。readall削除だけでは初期readを除けない |

旧stack全件は今回再照合しておらず、再入説は未確定。同じ計装kernelのclean A/Aで計装由来の停止を除く。

## F6: restart要求と実resetを分ける

まず現行`qemu-no-reboot.sh`でcorruption→`reboot: Restarting system`→自然終了を待つ。`test-qemu.sh`は自然終了0を1に変えるためQEMU exitとwrapper statusを別記。これはrestart要求の確認で、再boot成功ではない。

次に`-no-reboot`を外し、専用観測器でQMP RESETと2個目の`Linux version`を待つ。同じ破損imageの再停止も保存。証拠採取後のhost停止は別欄に記録し、SIGTERMを成功の根拠にしない。

現行verdictはnatural_exit・signalなし・status 0/1も要求する。reset継続とは衝突するため判定器を拡張する。timeout 480秒は失敗/未観測。

## caseと事前期待（各条件5 boot、boot0も別記）

`--runs 4`はloopが0〜4なので5 boot。順に実施し、前段の入力不整合やclean失敗で後段を止める。

| 段階・条件数 | 内容・期待 |
|---|---|
| A: 7 | v2のF0/F1=ready、F2〜F5=verity-panic、F6=verity-restart。F3新期待は再現仮説で、旧ready期待を修正しない |
| B: 8 | F3の3 mode×2経路=6、両経路clean=2。clean成功、top破損はpanic/restart、EIOは読取り-EIOを期待。訂正成功なら反証。後段mount panicは別記しverity-panic成功にしない |
| C: 10 | crc32c/roots8/panicで下位hashの先頭・末尾の有効digest各1=2（訂正して全read成功を仮説とする）。superblock署名破損=1（直接table経路は不変・ready、header読取りtoolは別途拒否）。parity先頭/末尾のみ=2（readyだがFEC未使用ならparity健全性の証明でない）、各々と同じRS columnのdata1 byteを併壊=2（訂正ready）。data block 0/D-1=2（訂正ready）、parity直後1 byte=1（非保護領域としてready） |
| D: 18 | hash{crc32c,sha256}×roots{2,8,16}×{clean,data1 byte,同column R+1 block}=18。前2種はready、R+1はverity-panicを仮説とする。hash毎にtree配置・FEC範囲を再算出。roots0はAのF5が対照 |
| E: 4 | roots8/crc32cで9/24 block×同column集中/異column分散。集中は双方panic、分散は各codeの負荷が容量内なら訂正readyを仮説とする |
| F: 1 | F6のreset許可観測。corruption→restart→QMP RESET→2回目banner。ready不要、別slot選択は対象外 |

合計48条件・240 boot。期待との相違は失敗として保持し、事後に成功へ変更しない。EIO・parity無影響・reset継続は現行3分類を拡張する。

## 注入設計の注意

- 4K固定。D=data blocks、H=hash_start、L=hash blocks、P=fec_start、E=parity終端とし、D-1/D/H/H+L-1/P/E-1/Eを監査する。Dはsuperblock、FEC論理上のhash先頭Dは物理Hへ写る。superblockを保護範囲に含めない。C/Aで境界を網羅し、paddingや未使用digestを有効hash破損に数えない。
- roots=Rでrsn=255-R、rounds=ceil((D+L)/rsn)。dataだけの範囲内でblock=i*rounds等を選び、byte laneを揃える。独立codecで`2*errors+erasures <= R`の境界（R/2、R/2+1、R、R+1）もhost試験する。kernelのerasures同定が実行されたかtraceで確認し、「R rootsなら常にR errors訂正」としない。
- F2の旧sourceはroots+1/1 bit、記録は24 block/byte反転。保存F2のclean差分を先に照合。同一性不明なら明記する。Eは9/24とも新規XOR=0xffとし件数・block・column一覧を保存。
- toolのheader拒否とkernel破損検出は別。hash変更時に5833を転用しない。

## 実行可否・資源見積り

検討時のVMは空き178 GiB、RAM available 27 GiB、6 CPU。Docker 29.9.3、開発imageのQEMU 11.1.2・cc・veritysetupを確認しました。開始時に再確認します。

旧`output-b3` 2.2 GiBにF0〜F6のsdcard/kernel/DTB/appendとV0/T0が残る。hash照合前なので再生候補に限定。standaloneの通常boot imageは736 MiB（実割当73 MiB）、verity/FEC有効kernelもあるが注入imageではない。資源上は実行可能。今回はboot・旧image同一性の検証はしない。

48条件のimage/rootfs/tree等に60〜80 GiBを予約し、開始時空き100 GiB以上を要求。原本は保護しQEMU_COPY_IMAGE=1。逐次を基本、並列は2まで。

旧CSV wall中央値はF0 234.7秒、F1 271.0秒、F3約480秒（旧timeout）。240 bootで16〜24時間、全timeoutで32時間。生成・host照合・kernel buildを暫定2〜4時間、上限36時間とする。Aの35 boot（2〜5時間）後に再見積りし、超過は承認待ち。

## 合否・保存・対象外

全5回で期待・marker順が一致すること。通常起動はreadall完了・ready/login、RAM試験はread結果/完了marker、訂正はFEC根拠、panicはverity固有causeを要求。ready+corruption、generic panic、timeout、host killは成功でない。boottime validと機能合否を分け、wallは中央値/最小/最大を出す。

functional.json、serial/QMP、cmdline、終了理由、params、注入差分、trace、hashを失敗・中断含め保存します。実行結果はresearch/dataへ保存します。

## 手順・計測器・結果欄

現行7条件の再現入口は以下です。base/casesは別途新規生成してから渡します。新しい出力先だけを使い、実行中のscriptは編集しません。

```sh
docker/msd-dev bash board/cardputerzero/tools/bench/dm-verity-fec/run-all-v2.sh /work/output-integrity /work/output-b3-followup/cases /work/output-b3-followup/results-a 4 480
```

B〜Fの単一実行入口・期待表・生成引数は次段のharness拡張で実装し、実行前に本記録へ固定します。現行runnerだけで全48条件を実行できるとはしません。clean A/A、generic panic、ready+corruption、host signal、timeout、上書き拒否をfixtureで検査します。

新しい追試の結果・CSV・serial/QMP・入力binary hashは未取得です。未実行なので捨てた新試行もなく、採否・原因・license監査完了の結論は出しません。途中停止した試行も次回は理由とrun IDを残します。

実機限定: firmware trybootと既定/trial slot選択、watchdog/panic timeout、S99health後・両slot破損の復旧、永続flag書込み時機/電断整合、SD実I/Oエラー、LCD/操作表示、全hashの実機性能。QEMU resetをA/B自動復帰・§10適合・製品安全性へ拡張しない。03914の台帳同期保留を維持する。
