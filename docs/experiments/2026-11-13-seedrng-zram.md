# seed非保存と初回起動からのzram swap

- 状態: 完了（実装・QEMU、実機と単独module比較は未実施）
- 日付: 2026-11-13
- 関連: [製品方針](../design/product-decisions.md)、[書き込み台帳](../design/write-policy.md)

## 目的と採否の基準（測定前）

seed保存を止め、RAMだけのzram swapを初回から有効にします。kernelのhwrngは維持します。基準はPR1の`0d86c849db69d2f544ec9695ff7c07380932cd99`です。

- 同じwarm出力先で変更前後をbuildし、既存boottime harnessのTCGで初回1回と通常5回を分けます。ready時間の中央値・最小・最大を記録し、中央値の増加が10%を超えた場合は原因を調べます。これはQEMUの基準で、実機性能とはしません。
- 変更後はseed init・設定・`/data/seedrng`の作成がなく、zram0がlogin経路開始後に有効となること。容量はMemTotalの50%、圧縮はzstd優先、priorityは100、永続backing deviceは使いません。
- dmesgの`crng init done`時刻を採取します。marker欠落は0秒とせず未観測とします。hwrngの品質・実機の初期化時間は未確認です。
- 既存write-inventoryを120秒×5区間で実行します。seed書き込み経路の削除と、残るpartition書き込みを区別し、RAM・diskの対照でcounterを確かめます。
- 変更後のmemory-pressure試験は1回の機能確認とし、free RAMを超える圧縮可能な非ゼロデータをtmpfsに置きます。swap使用量が0より大きく、負荷完了とOOM kill増加0を満たすこと。速度や一般のOOM耐性の証明にはしません。
- `=y`対`=m`の起動比較は、追加buildが合理的な時間で終わる場合に行い、未実施なら明記します。kernel Imageの論理byte数も比較します。

## 条件

| 項目 | 実行した条件 |
|---|---|
| 基準 | PR1の`0d86c849db69d2f544ec9695ff7c07380932cd99`。変更後は同commitのdirty treeに今回の製品差分を適用。CSVの`product_patch`が差分のhash |
| 出力先 | 両側とも既存warmな`output-openssl-lts`。beforeはdefconfig後にfull make、afterはBusyBox・Linuxの`-reconfigure`後にfull make。最後の変更はShellCheck向けcommentだけで、再度full makeした |
| 入力の保存 | beforeは`before-images`、最終afterは`final-images`へcopy。測定中のscriptは編集していない |
| 実行環境 | 開発OCI内のDebian 13、QEMU 11.1.2、GCC 14.3.0、Buildroot固定`8b238854d909c9cce32ef9671d968b03e323b55d`、Linux 6.18.59-v8 |
| QEMU | raspi3ap、512 MiB、CM0 dtb、TCG。`run-qemu.sh`が実行binaryと入力のhashを出す |
| 固定条件 | SquashFS、ext4のmount方針、同じboottime hookとkernel command line。boot測定中は別のbuild・memory-pressure試験を実行しない |
| 変える条件 | seed init・設定・mkdirの削除、zram built-in・writeback無効、遅延init、BusyBoxのswap priority対応 |
| bootの反復 | 各variantは同一の測定用imageで初回0と通常1〜5。初回のgrowと通常回を分け、中央値・最小・最大を出す |
| 機能試験 | seed・zram状態・負荷は通常rootfsへserialからprobeし、初回1回。boottimeのrootfsはrcSとdmesg dumpだけを測定用に置換 |

zram backendのKconfigは`ZSTD_COMPRESS`・`ZSTD_DECOMPRESS`をselectします。最終生成configで双方とZSMALLOCが`=y`、BCM2835 hwrngも`=y`、writeback無効を照合しました。console待機で使う`/proc/1/task/1/children`は、今回の`CONFIG_CHECKPOINT_RESTORE=y`で提供されます。hwrngの品質をconfigの存在だけで保証しません。

## 手順

以下はrepo rootから開発OCIで実行します。出力名が既にある場合は新しいrun名へ変え、元のログを上書きしません。beforeのbuild・snapshot・boot測定が終わってから製品差分を適用しました。

```sh
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output-openssl-lts" msd_cardputerzero_defconfig
make -C output-openssl-lts -j8
OUTPUT_DIR="$PWD/output-openssl-lts" \
  board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --variant before --runs 5 --mode tcg \
  --csv "$PWD/output-seedrng-zram/boot-before.csv" \
  --log-dir "$PWD/output-seedrng-zram/bt-before"

# 製品差分の適用後
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output-openssl-lts" msd_cardputerzero_defconfig
make -C output-openssl-lts -j8 busybox-reconfigure linux-reconfigure
make -C output-openssl-lts -j8
OUTPUT_DIR="$PWD/output-openssl-lts" \
  board/cardputerzero/tools/bench/boottime/run-boottime.sh \
  --variant after --runs 5 --mode tcg \
  --csv "$PWD/output-seedrng-zram/boot-after.csv" \
  --log-dir "$PWD/output-seedrng-zram/bt-after"

output-openssl-lts/host/bin/aarch64-linux-gcc -O2 -Wall -Wextra -Werror \
  board/cardputerzero/tools/bench/seedrng-zram/pressure.c -o output-seedrng-zram/pressure
python3 board/cardputerzero/tools/bench/seedrng-zram/run.py \
  --output output-openssl-lts --run-dir output-seedrng-zram/probe-after-final \
  --load output-seedrng-zram/pressure
python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-openssl-lts --run-dir output-seedrng-zram/idle-after-retry \
  --variant after --seconds 120 --windows 5
```

beforeの通常probeとidleは、同じ入力4 fileを保存した`before-images`を`before/images`として参照し、保存済みBuildroot `.config`も`before/.config`へcopyして実行しました。通常probeは`--load`なし、idleは同じ120秒×5区間です。full make・probe・idleは`docker/msd-dev`経由で実行しました。

## 計測器の確認と結果

同名[CSV](2026-11-13-seedrng-zram.csv)はboottimeの全行、idleの全stat、失敗したserialのsample、crng時刻、入力とログのhashを保持します。複製されたdmesg dumpの同じcrng行を、独立した2回として数えません。空の記録・欠けたmarkerはunit testで拒否します。

### boot・乱数初期化・容量

通常5回の値です。単位は秒、括弧は最小〜最大。boottime hookは`initcall_debug`とdmesg出力を加えるため、通常imageの単発probeとは条件が違います。

| 指標 | before | after |
|---|---:|---:|
| kernelからinit開始 | 6.245787（6.121726〜7.014043） | 6.323028（6.056822〜6.753780） |
| kernelからready | 22.797078（21.823048〜24.659973） | 22.324116（21.603241〜23.951127） |
| crng init done | 2.704825（2.476772〜3.070187） | 2.912791（2.532518〜3.038366） |
| kernel Image | 18,016,768 bytes | 18,082,304 bytes |

ready中央値は約2.1%小さく、10%劣化の基準には達しません。ただし範囲が重なり、速度向上や統計的同等性の証明にはしません。初回readyはbefore 27.729866秒、after 25.567503秒で、通常回の集計には入れません。

通常rootfsの単発probeでcrngはbefore 2.129048秒、after 2.293392秒でした。実機の初期化時間・hwrngの品質・jitter供給の保証ではありません。Imageは65,536 bytes増えました。

readyはS98のmarkerです。zramはそれより後のbackground workerで有効になるので、readyを「swap準備まで全て完了」と扱いません。`=y`対`=m`だけを分離したboot比較は未実施です。module側の実験用late load経路と追加buildが必要なため今回は省略し、seed停止も含む今回の差をその代わりにはしません。

### seed・zram・memory pressure

最終afterの通常rootfsでは、`S01seedrng`・`S05seedrng`・既定設定・`/data/seedrng`がありません。post-buildはwarm rebuildで再混入するinitも削除します。既存SDに残るseedは自動消去しません。

zramのworkerはPID 1のgetty／login／shellを待って1秒遅延します。QEMUではserialのlogin promptより後にcapacity設定とswaponの行が現れました。最終probeの有効化はkernel時刻24.757204秒です。これはprompt文字列自体を解析する仕組みではありません。

- MemTotal: 430,888 KiB。zram disksizeは220,614,656 bytes、usable swapは215,440 KiB、priority 100、選択algorithmはzstdでした。
- writebackはkernelで無効、`backing_dev`のsysfs file自体がありません。zswap使用量は0です。log・lock・負荷binaryは`/run`に置き、SD上のswapは作りません。
- 非ゼロの圧縮可能なpageに異なるoffsetを埋め、処理前のMemAvailable 383,944 KiBより大きい426,713,088 bytesを確保・書込みました。compiler barrierでstoreの除去を防ぎます。
- 負荷完了時にswapを33,792 KiB使用し、`MSDLOAD_DONE=0`、OOM marker増加0でした。単発の機能試験であり、非圧縮データ・長時間thrash・実機のCPU費用を保証しません。

計画のtmpfs file負荷から、実施時はprocessのheapへ変更しました。MemAvailableを超える容量条件は同じですが、tmpfs固有の負荷を試したとはしません。OOMについてはdmesgのmarkerを採取し、`/proc/vmstat`のoom_kill差分は採取していません。

### idleと書き込みの帰属

追加操作なしの120秒×5区間です。独立した5回のbootではありません。

| 条件 | p7の増加（512-byte sector） | RAM対照 | disk対照 |
|---|---|---:|---:|
| before | 8320, 0, 0, 0, 0 | 0 | 2104 |
| after retry | 8304, 0, 0, 0, 0 | 0 | 2112 |

disk全体も同じ区間差で、p1〜p6は全区間0でした。RAM対照はcacheへの1 MiBとlogger、disk対照はidle区間後の意図的な`/data`への1 MiBです。counterがdisk負荷を検出することを確認しました。

seed保存経路の削除と実際の不在から、自動seed書き込みを止めたと判断します。partition counterだけではprocess別の帰属は分かりません。最初の8304 sectorは残っており、idleの0 sector基準は未達です。beforeとの差16 sectorをseedの削減量と断定しません。resize・初期化・journalの寄与は未分離のまま[台帳](../design/write-policy.md)へ残します。

## 失敗した試行と再実行

- 最初のafter idleはzramのkernel console出力がstat行へ割り込み、`int()`が`0[`を拒否しました。全serialとsampleをCSVの無効行へ保持し、集計に混ぜていません。
- 終了後にguest側の測定hookへ`dmesg -n 1`を加え、consoleだけを静かにして新しいrun名で再実行しました。kernel ring buffer・製品rootfs・counterの意味は変えません。
- 新initのspace区切りPID一覧についてShellCheck SC2013が出たため、意図を示す局所的な抑制を加えました。その後の最終build・A/B boot・5回の測定はこのcommentを含みます。
- 最初の機能probeはcomment追加前のrootfsでswapを37,708 KiB使用しました。保存はしていますが、上表の最終probeの値とは混ぜません。
- collectorをretryの完了前に呼び出した際は欠落CSVとして停止しました。空の値を0にせず、完了後に再実行しました。

## ログと再集計

証拠はrepo内の`output-seedrng-zram`へ保存しています。巨大なimageとログはcommitしません。CSVは実際のQEMU binary、Image・SquashFS・dtb、config、入力manifest、serial・build・testログのSHA-256を記録します。最終Imageは`d3a6e2845154b006d867ede6f25274d4c2ef0dfd763ed7b2a02ae5af08da943e`です。

snapshotは元を残してcopyし、CSVのartifact hashと入力manifestで照合します。再集計はhostで次のとおりです。出力CSVがあれば別名を指定します。

```sh
python3 board/cardputerzero/tools/bench/seedrng-zram/collect.py \
  --run-root output-seedrng-zram --csv seedrng-zram-recomputed.csv \
  --base 0d86c849db69d2f544ec9695ff7c07380932cd99
```

## 結論と未確認

seed非保存とbuilt-in zramを実装し、full build、QEMU A/B、通常rootfsでの遅延有効化・swap負荷を確認しました。QEMUのblock counterは実SD・FTLの書き込み量ではありません。実機のentropy品質、boot、SD、停止・電断、CPU負荷・thrash、`=y`対`=m`単独比較は未確認です。`/data`のmount方針や残るidle書き込みを解決したとはしません。
