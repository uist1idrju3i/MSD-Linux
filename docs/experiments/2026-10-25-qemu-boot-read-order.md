# 起動時に SD カードから読むファイルとその順番（QEMU）

- 状態: 完了（QEMU のみ）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [ユーザー空間とセキュリティ](../research/userspace-and-security.md)（fanotify、blktrace、`mksquashfs -sort` の手順案）、[シミュレーション検証計画](../research/simulation-plan.md)、`board/cardputerzero/tools/bench/read-order/`

## 目的と仮説

起動のあいだに、SD カードのどこが、どの順番で読まれるかを QEMU で記録します。rootfs（SquashFS）への読み出しは、どのファイルや表の範囲かに対応づけます。`mksquashfs -sort` でファイルの配置を変える前に、起動で読むファイルとその順番を知ることが目的です。

仮説は次のとおりです。

- 起動で読むのは、rootfs のうち一部（BusyBox、libc、`/data` の準備に使う e2fsprogs と util-linux の library など）に限られる。
- TCG でも、読むファイルの順番は起動ごとに大きくは変わらない。

調査文書の手順案は fanotify や blktrace を使います。今回は、ゲストに何も足さずに済む QEMU の trace event（`sdcard_read_block`）を使いました。SD のコントローラーに届いた読み出しを、block の単位で記録できます。

## 採否の基準

この測定は採否を決める実験ではなく、観測です。有効とする条件は次の 4 つで、どれも、本測定の前に runner と map の道具が出力または検査するようにしてありました（commit `316bdba` と `5c56219`）。ただし、この Markdown に書いたのは本測定の後です。

- 5 回の起動が、すべて `test-boot.sh` の終了コード 0 で終わる。
- 各起動の trace に `sdcard_read_block` の行が 1 行以上ある。
- image の rootfs のパーティションが、map に使った `rootfs.squashfs` と byte 単位で一致する（`map-reads.py` が検査する）。
- map が SquashFS の `bytes_used` を漏れも重なりもなく覆う（`squashfs-map.py` が検査する）。

## 条件

| 項目 | 値 |
|---|---|
| image を作った commit | `87aadf5`（main）。カーネルは 6.18.57 |
| runner と試験の script の commit | `5c56219`（base は main の `78eb4f0`。QEMU 用 DTB の Bluetooth を無効にする #105 を含む） |
| ホスト | Ubuntu、x86_64。開発用イメージ `msd-dev:local`（image ID `sha256:2a2c70d17140`） |
| QEMU | 11.1.2（開発用イメージの `/opt/qemu/bin/qemu-system-aarch64`、SHA-256 `a1dfa3b632e3`）。machine `raspi3ap`、memory 512M、icount なし（TCG） |
| カーネル | `6.18.57-v8`、GCC 14.3.0、GNU ld 2.43.1（serial log の `Linux version` の行から） |
| 入力 | `sdcard.img` `5610e093d0d3`、`rootfs.squashfs` `28164bdda81a`（23,891,968 B、`bytes_used` 23,888,865 B）、`Image` `1c085405fedf`、QEMU に渡した DTB `b3e809de61af`（Bluetooth 無効。元の DTB は `e035db2336d4`） |
| trace | `-trace enable=sdcard_read_block -D <log>`（`qemu-trace-wrap.sh` を `QEMU_SYSTEM_AARCH64` に渡す） |
| map の道具 | ホストの Python 3.14.4。開発用イメージの Python 3.13 には `compression.zstd` がなく、zstd の metadata を展開できないため |
| 範囲 | QEMU の起動から、`test-boot.sh` が login prompt を見て QEMU を止めるまで |
| 繰り返し | 5 回 |

## 手順

```sh
# 開発用イメージの中で 5 回起動し、trace を残す（OUTPUT_DIR は image の出力先）
docker/msd-dev env OUTPUT_DIR="$O" READ_ORDER_VARIANT=tcg \
  board/cardputerzero/tools/bench/read-order/run-read-order.sh

# ホストで、rootfs の map を作り、読み出しを対応づける
B=board/cardputerzero/tools/bench/read-order
python3 $B/squashfs-map.py --csv rootfs-map.csv "$O/images/rootfs.squashfs"
for i in 1 2 3 4 5; do
  python3 $B/map-reads.py --trace "$O/read-order/tcg/boot$i/sd-trace.log" \
    --image "$O/images/sdcard.img" --rootfs-map rootfs-map.csv \
    --rootfs-squashfs "$O/images/rootfs.squashfs" \
    --csv boot$i-reads.csv --order-csv boot$i-order.csv
done
python3 $B/summarize-reads.py --rootfs-map rootfs-map.csv \
  $(for i in 1 2 3 4 5; do echo --boot boot$i boot$i-reads.csv boot$i-order.csv; done) \
  --csv summary.csv --files-csv files.csv
```

実際には、開発用イメージを `docker run` で直接起動しました。`docker/msd-dev` と同じ mount で、`OUTPUT_DIR` と `READ_ORDER_VARIANT` を渡しています。

## 計測器の検証

- map は 405 の範囲で `bytes_used` の 23,888,865 B を覆い、漏れと重なりは 0 でした。map のファイルの一覧は `unsquashfs` の一覧と一致しました（試運転で確認）。
- rootfs のパーティションと `rootfs.squashfs` は、5 回とも byte 単位で一致しました。
- trace が実際の読み出しを捉えていることは、最初に読まれる範囲で確かめました。rootfs の先頭（superblock）が最初に読まれ、次に BusyBox の data block が読まれます。init が BusyBox であることと合っています。

## 結果

生の値は [2026-10-25-qemu-boot-read-order.csv](2026-10-25-qemu-boot-read-order.csv)、最初に読まれた順番は [-order.csv](2026-10-25-qemu-boot-read-order-order.csv)、ファイルごとの読み出し量は [-files.csv](2026-10-25-qemu-boot-read-order-files.csv) にあります。5 回とも有効でした（`valid=1`）。

| 指標 | 5 回の値 |
|---|---|
| `test-boot.sh` の終了コード | 0, 0, 0, 0, 0 |
| trace の行数（1 行は 512 B の block） | 10,994、10,994、11,106、10,994、10,994 |
| rootfs のパーティションから読んだ量（同じ block の再読み込みを含む） | 4,647,936 B（3 回目だけ 4,705,280 B） |
| rootfs から読んだ量（再読み込みを 1 回と数える） | 3,947,520 B（`bytes_used` の 16.52 %）。5 回とも同じ |
| `/data`（p7）から読んだ量 | 272,384 B |
| パーティションの外（MBR、EBR など）から読んだ量 | 704,512 B |
| boot パーティション（p1）から読んだ量 | 4,096 B |
| 最初に読まれた順番に並べた名前の数 | 440。順番の SHA-256 は 5 回とも `9379a23cf5b7903733ac71524d8403a9d49d98efceada53f0d166792d01deffe` |

rootfs から読んだ 3,947,520 B の内訳です（再読み込みを 1 回と数える）。

| 範囲 | 読んだ量 |
|---|---|
| ファイルの data block | 2,511,152 B |
| fragment（小さいファイルをまとめた block） | 1,394,285 B（141 個のうち 44 個） |
| directory table | 22,471 B |
| inode table | 16,629 B |
| export table、fragment table、id table、superblock | 1,996 B、842 B、18 B、96 B |

data block を全部読んだファイルは、次の 13 個でした。最初に読まれた順に並べると、BusyBox、`ld-linux-aarch64.so.1`、`libblkid`、`libsmartcols`、libc、`libmount`、`e2fsck`、`libext2fs`、`partx`、`sfdisk`、`libfdisk`、`loadkeys`、`modules.alias` です（順番の詳細は -order.csv）。合わせて 2,503,280 B で、data block を読んだ量のほぼすべてです。ほかの 12 個は 4 KiB 未満しか読まれていません。隣のファイルの block を読んだときに、境目が掛かったものと考えています（確かめてはいません）。

起動ごとの違いは 3 回目だけでした。libc の data block 3 個（57,344 B）をもう一度読み、`/data` の 1 回の読み出しの位置が前後しました。最初に読む名前の順番は変わりませんでした。

## 捨てた試行と経緯

1. 最初の本測定は icount（`QEMU_ICOUNT=shift=0`）で始めました。1 回目の起動が、ゲストの時刻で 1.4 秒（dwc2 の初期化）の後に進まなくなり、300 秒で時間切れになりました（終了コード 124、trace は 0 行）。中止しています。
2. 原因を分けるため、icount で trace を付けた場合と付けない場合を 1 回ずつ起動しました。どちらも 280 秒で時間切れになり、同じ位置で止まりました。trace は原因ではありません。同じ時刻に S15 で icount の起動を並べて走らせており、そちらは 1 回 340 秒ほどかかって login まで進みました。ホストの負荷（load average 16〜18）で、icount の起動が `test-boot.sh` の時間切れより遅くなったと考えていますが、確かめてはいません。そのため、本測定は icount なしにしました。読むファイルの順番を見る測定では、時間の正確さは要りません。
3. 1 で、runner の `conditions.log` に trace の行数が `0` と 2 回書かれました。`grep -c` が 0 件で終了コード 1 を返し、`|| echo 0` も動いたためです。本測定の前に直しました（`5c56219`）。
4. 試運転（`a39d68d`）では、map に export table と id table がなく、名前の数が 438 でした。表の範囲を足し、map が `bytes_used` をちょうど覆うことを検査するようにしました（`316bdba`）。

## 結論

- QEMU では、起動で読む rootfs は `bytes_used` の 16.5 % で、5 回とも同じ範囲でした。読むファイルの順番も 5 回とも同じでした。
- 読んだ量の大半は、BusyBox、libc と、`/data` の準備に使う e2fsprogs と util-linux（`e2fsck`、`sfdisk`、`partx`、`libext2fs`、`libfdisk`、`libmount`、`libblkid`、`libsmartcols`）でした。
- `mksquashfs -sort` を試すなら、この 13 個と directory table、inode table を先頭に寄せる案が候補になります。効果は SD の読み出しの速さで決まるため、QEMU では測れません。採否は実機で決めます。

QEMU の値は実機の値ではありません。

## 未確認の点

- QEMU の SD のモデルは、実際のカードの速さと内部の動作を模していません。実機では読み出しが遅いため、並んで動く処理の順番が変わり、読む順番も変わる可能性があります。
- カーネルと DTB は QEMU が直接読み込んでいます。実機の GPU firmware が boot パーティションから読む `kernel8.img`、DTB、`config.txt` などは、この trace に含まれません。
- 測った image のカーネルは 6.18.57 です。6.18.58（#106）の image では試していません。
- login の後に動く処理（アプリなど）の読み出しは含みません。
- 実機では試していません。

## ログ

trace（1 回 483 KB ほど）と serial log はコミットしていません。手順のコマンドで作り直せます。SHA-256 は [2026-10-25-qemu-boot-read-order.sha256](2026-10-25-qemu-boot-read-order.sha256) にあります。

## 製品採用（2026-10-30 追記）

A ordem medida virou o arquivo `board/cardputerzero/squashfs-sort.txt` (prioridades = rank × 10), aplicado via `mksquashfs -sort`. O token `@KVER@` é resolvido no `post-build.sh` para a versão real do kernel a cada build. QEMU 回帰 na imagem resultante (kernel 6.18.58-v8 PREEMPT_RT + FTRACE off + squashfs ordenado, zstd -Xcompression-level 22): `MSD/Linux ready` 到達 e ext4 resize normal. Impacto no tempo de leitura da rootfs em SD real é efeito esperado da ordenação física — 実機では試していません.
