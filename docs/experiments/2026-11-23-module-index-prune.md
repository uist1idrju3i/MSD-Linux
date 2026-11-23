# 製品のmodule binary index削除

## 実行前の計画

2026-11-23、利用者が通常製品のBusyBox経路を対象とする削除を承認した。
基準は`901bd8a1e8c97498f1cde69531cace27d3606acc`。
[削除前の監査](2026-11-23-module-binary-index.md)は当時の停止判断として残し、過去のOpenSSL実験記録も書き換えない。

仮説は、テキストindexとmodule本体を保持すれば通常起動のmodule loadを維持し、製品の非圧縮容量を938,282 bytes減らせること。
binary indexの削除はhost depmod・署名後のexternal post-buildで行い、kmodのmodprobeに変わった構成では削除を拒否する。
OpenSSL測定器は各fixtureを展開した後、reference内のhost depmodで自前のindexを作る。元の製品imageは変更しない。

採否条件はbinary index残存0、テキストindexとmodule本体のhash差0、SquashFS容量差が減少方向であること。
同じ既存rootfsを2回packするA/Aでhash差0を確認する。
変更前後それぞれQEMU A/Bを1回ずつ起動し、ready・login・3 moduleのload確認に成功すること。
`/proc/modules`の名前・サイズ・依存先・状態を比較し、差0を条件とする。addressと参照数は比較から除き、生の行は保存する。
構築可否の試験なので各1回とし、起動時間の性能差や実SDの効果は結論にしない。

製品へのruntime書込み・表示・hookは追加しない。inventoryの出力は測定用の写しだけに入れる。
最新設定の製品buildと、既存artifactの再packの証拠は区別する。full buildが重い場合は前回の許可に従ってCIへ残す。

## 結果

### 条件と入力

| 項目 | 実行条件 |
|---|---|
| host | Ubuntu 26.04.1 LTS、開発用OCIで実行 |
| OCI ID | `sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65` |
| QEMU | 11.1.3、raspi3ap、512 MiB、TCG。kernel・DTBは全条件で同一 |
| compiler | C測定器は既存SDKのGCC 14.3.0でcompile |
| kernel | 既存imageの6.18.59-v8、2026-11-15 build。kernelは再compileしない |
| Buildroot | 既存referenceの設定は2026.08.1-27-g8b238854d90。作業treeの固定版は`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`で、両者を同一buildとは扱わない |
| image tools | 既存host mksquashfs 4.7.5、host depmod 34.2、zstd level 22・128 KiB block・2 processors |
| 入出力 | referenceは既存`output-integrity`を読取り専用で利用。新規出力は`output-module-index-r1`。全条件を同じrootfsの展開結果から作る |
| build状態 | SDK・kernel・referenceは再利用。packageのreconfigure、ccacheを使う製品buildは未実施。各SquashFSは新規出力へpack |

新しい[runner](../../board/cardputerzero/tools/bench/module-index.py)は元のimageを展開し、変更前・A/A・変更後・測定fixtureの4種類を作る。
容量のrootfs欄は計測hook挿入前の通常file合計。今回の入力ではhardlinkによる重複はなかった。
SquashFSは全条件で同じsort list、mtime 0、圧縮条件を使い、変更前後に同じ`/proc/modules`出力hookを入れている。
fixture条件だけにはC測定器も入れるので、その圧縮後容量は製品の削減量に使わない。

元のSquashFSのSHA-256は`b68236f9612b010d42a0a9227d59332d94b2b84d19a593dc16ea9f269e2ea885`。
展開したrootfsは37,048,525 bytesで、以前の監査の`target/`集計37,049,861 bytesとは入力が異なる。両者を変更前後の差には使わない。
元imageの再取得元は今回確認しておらず、最新版の製品buildを再現した証拠ではない。下の手順で新しいreferenceにも同じ比較を適用できるが、容量やhashの一致は保証しない。

### 容量とA/A

| 条件 | rootfs通常fileのbytes | SquashFS bytes |
|---|---:|---:|
| 変更前 | 37,048,525 | 20,500,480 |
| A/A | 37,048,525 | 20,500,480 |
| 変更後 | 36,110,243 | 20,332,544 |
| 変更後−変更前 | −938,282 | −167,936 |

A/AのSquashFS SHA-256は両方`f586296e056f05fce6d6a0b9d596428bea8df87471aa51275edb219571992243`で一致した。
削除したのは5 binary indexだけで、module本体・テキストindexを含む残りの通常fileのhash差は0だった。
非圧縮約0.895 MiBに対し、この条件での圧縮後削減は164 KiB。起動時間の短縮とは扱わない。

### QEMU A/Bとmodule比較

`test-boot.sh`と`test-ab.sh`を変更前後それぞれ実行した。
4 boot全てでready・login、usbnet・bcm2835-unicam・imx219のmodprobe/lsmod確認に成功し、QMP quit後の終了値は0、強制終了は0回だった。
各slotの`/proc/modules`は19件。名前・サイズ・依存先・状態をsortして比較し、変更前A対変更後A、変更前B対変更後B、変更前A対Bの差は全て0だった。
参照数とaddressは比較から除き、生の行をserial logへ保存した。snapshotから1件を除いた負の対照では不一致になった。
launcherからreadyまでのhost時間は変更前A/Bが27/30秒、変更後が27/31秒だが、性能試験の反復ではなく、短縮の結論に使わない。

### 測定器の分離

製品の削除判断は通常起動のBusyBox経路に限定する、という利用者の決定を受けた。
OpenSSL測定器をBusyBoxへ置き換えるとlibkmodの試験を失うため、`openssl-cnf/run.py`は各fixtureを展開してからhost depmodを実行する形にした。
index生成はC0/C1/C2へ同じように行い、元の製品imageには書き戻さない。depmod失敗、module version不在、`modules.dep.bin`未生成は停止する。

実機能の確認では、展開した写しからbinary indexを全て除いた後、新しい準備関数を使って5 indexを再生成した。
このfixtureでのQEMU A起動は終了0。既存のC測定器は`libkmod configs load rc=0`を出し、snapshotにはconfigsを加えた20件があった。
OpenSSLのTLS全matrixは再実行しておらず、ここで確認したのはindexの準備とlibkmodのload経路である。
過去の実験記録・archive・元imageは変更していない。

### 失敗と未確認

- 既存出力先へ再実行する負の対照は`FileExistsError`、終了1で停止した。先の出力は上書きしていない。
- 正式なpack 4件とQEMU 5 bootの失敗は0。pack時の警告を含むbuild logも保存した。
- 最新設定はkernel、Btrfs、cryptsetup等がreferenceと異なる。最新HEADからのfull Buildroot buildは未実施。環境の所要見込みが1〜2時間のため、前回許可に従って製品buildと新imageのA/BはCIへ残す。
- branchへのpushだけでは製品build workflowは起動しない。PRまたは`build.yml`のworkflow_dispatchが必要。ローカルのghには認証がなく、今回dispatchしていない。
- LCD、実機hotplug、SDの速度・電源断・firmware trybootは未確認。
- 製品にはruntimeの書込みや表示を追加していないので、write-policyの新しい例外は不要。測定hookは製品に入れない。

## 再実行と証拠

出力先は未使用の名前を選び、repository rootで実行する。
`--reference`にはbinary index削除前のbuild出力を指定する。
その`images/rootfs.squashfs`には`lib/modules/<version>/modules.*.bin`が必要で、現在のpost-buildでindexを削除済みの製品imageは比較元に使えない。
該当fileがない場合は、展開直後に`--reference must be a pre-pruning image containing modules.*.bin`というerrorで停止する。
以下の`output-integrity`は今回使った削除前の既存出力であり、削除済みの新しい出力へそのまま置き換える手順ではない。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/module-index.py \
  --reference output-integrity --out output-module-index-r1
for variant in before after; do
  for script in test-boot.sh test-ab.sh; do
    docker/msd-dev env OUTPUT_DIR="/work/output-module-index-r1/$variant" \
      QEMU_LOG_DIR="/work/output-module-index-r1/$variant/logs" \
      board/cardputerzero/qemu/"$script"
  done
done
docker/msd-dev env OUTPUT_DIR=/work/output-module-index-r1/fixture \
  QEMU_LOG_DIR=/work/output-module-index-r1/fixture/logs \
  board/cardputerzero/qemu/test-boot.sh
```

[CSV](2026-11-23-module-index-prune.csv)に全条件と未実施を分けて収録した。
[証拠archive](2026-11-23-module-index-prune-evidence.tar.gz)にはbuild log、5 serial、process結果、wrapper出力、snapshot、容量、入力・source hashを保存した。
archiveのSHA-256は`e0ad1ecc9cbb01f629655aa22dc8aea174ac23970b6549c7d284a793facb3664`。
QEMU binaryのSHA-256は`8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73`、kernelは`45d52f6e148cebaee66ecbc9735c6260ec23ca8c9ad0b00032cf04d20f1420e8`で、各serial冒頭の`run-qemu: sha256`行にも残る。
snapshotはserial内の`MODULE_INVENTORY_BEGIN`と`MODULE_INVENTORY_END`の間で、同じ行を比較用JSONにも収録した。

## Review後の測定器修正

`899a5d2`の測定器はfixture内のC probeが失敗してもreadyへ進めた。
保存済みlogの`libkmod configs load rc=0`は当時の成功の観測として保持するが、起動試験だけでprobeの成功を保証する設計ではなかった。
修正版は終了値を`MODULE_INDEX_PROBE_RESULT`としてserialへ出し、0以外ならS98を終了してreadyを出さない。
既存boot harnessはreadyとloginの両方を要求するため、この場合は起動成功にならない。
host試験では、成功らしい文字列を出しても終了7のprobeはreadyへ進めず、probe不在も終了127になることを確かめる。
この修正後のQEMUは未再実行。以前の5 bootと容量のCSV・archiveは変更していない。
