# QEMU の console で出る `tty->count` の警告

- 状態: 完了（2026-10-25 に、`run-qemu.sh` の既定で無効にしたあとの測り直しを追加）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [振り返り](../research/retrospective-2026-10.md) の残タスク「tty の警告」、[2026-10-21-qemu-lynis](2026-10-21-qemu-lynis.md)

## 目的と仮説

QEMU のシリアルログに、起動の終わり近くで次の行が出ます。原因を確かめます。

```text
ttyAMA ttyAMA1: tty_open: tty->count(2) != (#fd's(1) + #kopen's(0))
```

仮説: QEMU の console は `console=ttyAMA1`（PL011）です。CM0 の DTB では、PL011 の子に Bluetooth の node（`brcm,bcm43438-bt`、`status = "okay"`）があり、serdev の controller になります。起動中に `hci_uart` が読み込まれると、serdev が `tty_init_dev()` で tty を開きます。このとき file は登録されず、`tty->count` だけが 1 増えるはずです。そのあとで `/dev/console` を開くと、file の数より `tty->count` が 1 多くなり、`check_tty_count()` が警告を出します。

## 採否の基準（結果を見る前に書く）

1 回ずつの予備試行（後述）のあと、本番の前に書きました。

- 仮説を支持する条件: stock の 5 回すべてで `warnings_total` が 1 以上かつ `serdev_registered` が 1。bt-off の 5 回すべてで `warnings_total` が 0 かつ `serdev_registered` が 0。
- 副次の指標: シリアルから `root` でログインし、`echo TTYPROBE-$((6*7))` の結果 `TTYPROBE-42` が返るか（`shell_probe`）。予備試行では stock で返りませんでした。stock 5/5 で no、bt-off 5/5 で yes なら、「serdev がシリアルの入力を受け取っている」と記録します。
- 1 回でも外れたら、仮説は支持されないと書き、ログを読んで原因を記録します。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | 87aadf5（ビルド成果物）。runner は 20d696a、基準は 8773940 で記録 |
| ホスト | Ubuntu 26.04.1 LTS、12 CPU。`docker/msd-dev` の中で実行 |
| QEMU | `QEMU emulator version 11.1.2`（`-M raspi3ap -m 512M`、icount なし） |
| Buildroot / カーネル | Buildroot submodule d6061d653d、Linux 6.18.57-v8（固定 commit 2341883150） |
| image | `sdcard.img` `5610e093…`、`Image` `1c085405…`（87aadf5 のビルド） |
| DTB | stock: `bcm2710-rpi-cm0.dtb` `e035db23…`。bt-off: stock を `fdtput` で 1 か所だけ変えたもの `b3e809de…` |
| 変える条件 | `/soc/serial@7e201000/bluetooth` の `status`（stock は `okay`、bt-off は `disabled`）。dtc で戻して比べ、差はこの 1 行だけだった |
| 変えない条件 | image、kernel、kernel の command line（`console=ttyAMA1,115200` など `run-qemu.sh` の既定） |
| 繰り返し | 各 5 回。値はすべての回で同じだったため、中央値と最小・最大は同じ値になる |

## 手順

```sh
docker/msd-dev board/cardputerzero/tools/bench/tty-count/run-tty-count.sh \
  output/tty-formal output/tty-formal/tty-count.csv 5
```

runner は 1 回ごとに `run-qemu.sh` を起動し、`login:` が出たら `root` を送ります。`# ` が返れば、`TTYPROBE-$((6*7))` の echo、`/proc/modules` の `hci_uart` の数、`/sys/bus/serial/devices` の一覧を出させます。CSV の `valid` 列は「シェルの応答まで進んだか」を表します。stock では副次の指標のとおりシェルに入れないため、`valid` は 0 になります。`warnings_total` と `serdev_registered` はログ全体から数えており、`valid` が 0 でも値は有効です。

## 計測器の検証

- 陽性: stock の予備試行で、警告を 7 行数えた。ログを目で数えた数と一致した。
- 陰性: bt-off では 0 行だった。同じ runner で `TTYPROBE-42` が返り、ログインの手順そのものは動くことを確かめた。

## 結果

生の値は [2026-10-25-qemu-tty-count.csv](2026-10-25-qemu-tty-count.csv) にあります。

| 条件 | 回数 | `warnings_total` | `serdev_registered` | `hci_uart` の probe | シェルの応答 |
|---|---|---|---|---|---|
| stock | 5 | 7（5 回とも） | 1（5 回とも） | 5 回とも出た | 5 回とも no |
| bt-off | 5 | 0（5 回とも） | 0（5 回とも） | 5 回とも出ない。`/proc/modules` の `hci_uart` は 0 | 5 回とも yes（`TTYPROBE-42`） |

stock のログからは、次のことを読み取りました。

- `hci_uart_bcm serial0-0` の行は 23.7〜24.9 秒、最初の警告は 25.6〜27.0 秒に出た。5 回とも、警告は `hci_uart` の probe の後だった。
- 5 回とも `Bluetooth: hci0: BCM: Reset failed (-110)` と `Bluetooth: hci0: Frame reassembly failed (-84)` が 1 行ずつ出た。QEMU には Bluetooth の chip がないため、初期化は失敗する。
- `msd login:` は出たが、送った `root` は表示されず、シェルにも入らなかった。シリアルの入力は getty に届かず、`hci_uart` が受け取ったと考えられる。`Frame reassembly failed` は、入力を Bluetooth の frame として読もうとした結果と見られる。
- `MSD/Linux ready` は 5 回とも出た。test-boot.sh が見る印は変わらない。

## 捨てた試行と経緯

- 予備試行（各 1 回、`output/tty-pilot`）は、本番の基準を決めるために行った。結果は本番と同じだった（stock は警告 7 行でシェルなし、bt-off は警告 0 行でシェルあり）。
- 予備試行の runner は、ログの NUL バイトで bash の `ignored null byte` の警告を出した。`tr -d '\r\000'` に直してから commit し、本番を行った。
- 本番は S12 の測定（icount）と同じ時間帯に行った。この実験は時間を測っていないため、結果への影響はない。S12 側の影響は S12 の記録に書く。

## 結論

結果は仮説を支持しました。CM0 の DTB は PL011 を Bluetooth に割り当てていますが、`run-qemu.sh` は同じ PL011 を console にしています。このため、`hci_uart` が serdev として tty を開いた後は、`/dev/console` を開くたびに `check_tty_count()` が警告を出します。

同じ理由で、QEMU のシリアル console からは、`hci_uart` の読み込み後にログインできません。いまの QEMU の試験は出力を grep で調べるだけなので、失敗していません。シリアルから入力する試験を足すと、この問題に当たります。

製品の cmdline は `console=tty1 console=serial0,115200` で、DTB の `serial0` は mini UART（`serial@7e215040`）です。製品では PL011 を Bluetooth が、mini UART を console が使うので、同じ衝突は起きない見込みです。ただし実機では試していません。

改善案: QEMU の試験だけで使う DTB で、PL011 の子の Bluetooth を `disabled` にする。この案では、QEMU の試験で `hci_uart` と btbcm の probe が行われなくなります。ただ、いまも QEMU には chip がないため、初期化は失敗しています。利用者がこの案を採ると決めたので、`run-qemu.sh` の既定にしました。結果は次の節にあります。

## 2 回目の本番: `run-qemu.sh` の既定で無効にしたあと

`run-qemu.sh` は、`QEMU_DTB_BLUETOOTH` が `0`（既定）のとき、DTB の複製を作り、`fdtput` で `/soc/serial@7e201000/bluetooth` の `status` を `disabled` にしたうえで、`run-qemu: dtb bluetooth=disabled base_sha256=<元の DTB>` をログに出します。`QEMU_DTB_BLUETOOTH=1` のときは、DTB をそのまま使います。変えるのは QEMU に渡す複製だけで、製品の DTB と SD カードの image の中身はそのままです。

runner に 3 つ目の条件 `default` を足し、3 条件を 5 回ずつ測り直しました。

- 変えた条件: stock は `QEMU_DTB_BLUETOOTH=1` で stock の DTB を使う。bt-off は、外で作った bt-off の DTB を `QEMU_DTB_BLUETOOTH=1` で渡す。default は、stock の DTB を既定のまま渡す（`run-qemu.sh` が無効にする）。
- 採否の基準（本番の前に決めた）: default の 5 回すべてで、bt-off と同じ値（`warnings_total` が 0、`serdev_registered` が 0、`shell_probe` が yes）になること。また、`run-qemu.sh` が渡した DTB の SHA-256 が bt-off の DTB（`b3e809de…`）と一致すること。stock は 1 回目の本番と同じ値になること（計測器の陽性の対照）。
- runner と `run-qemu.sh`: commit 23d9846（その後 main に rebase して 5a5de39 にしたが、この 2 ファイルの中身は同じ）。image、kernel、QEMU は 1 回目と同じ（`sdcard.img` `5610e093…`、`Image` `1c085405…`、`qemu-system-aarch64` `a1dfa3b6…`）。

```sh
QEMU_LOG_DIR=output/tty-default docker/msd-dev \
  board/cardputerzero/tools/bench/tty-count/run-tty-count.sh \
  output/tty-default/logs output/tty-default/tty-count.csv 5
```

生の値は [2026-10-25-qemu-tty-count-default.csv](2026-10-25-qemu-tty-count-default.csv) にあります。

| 条件 | 回数 | `warnings_total` | `serdev_registered` | `hci_uart_loaded` | シェルの応答 | `valid` |
|---|---|---|---|---|---|---|
| stock | 5 | 7（5 回とも） | 1（5 回とも） | none（シェルに入れず読めない） | 5 回とも no | 5 回とも 0 |
| bt-off | 5 | 0（5 回とも） | 0（5 回とも） | 0（5 回とも） | 5 回とも yes | 5 回とも 1 |
| default | 5 | 0（5 回とも） | 0（5 回とも） | 0（5 回とも） | 5 回とも yes | 5 回とも 1 |

- default の 5 本のログすべてに `run-qemu: dtb bluetooth=disabled base_sha256=e035db23…` が出た。stock と bt-off のログには出なかった。
- default で QEMU に渡した DTB の SHA-256 は、5 回とも `b3e809de…` だった。外で作った bt-off の DTB と同じ binary になる。
- stock の値は 1 回目の本番と同じだった。計測器は警告を数えられている。

結果は基準を満たしました。`run-qemu.sh` を使う QEMU の試験では、既定で警告が出なくなり、シリアルからログインできます。

5a5de39 で、既存の QEMU の試験も通しました。ready までの秒数は、カーネルのビルドと同時に走らせた値で、比較には使いません。

| 試験 | 結果 | `tty->count` の警告 | `dtb bluetooth=disabled` の行 |
|---|---|---|---|
| `test-boot.sh` | 通った（ready 33 秒、root `/dev/mmcblk0p5`、`login:` あり） | 0 行 | 1 行 |
| `test-ab.sh` | 通った（ready 47 秒、root `/dev/mmcblk0p6`、`login:` あり） | 0 行 | 1 行 |
| `tests/qemu-log-check/run.sh` | 通った（serial log の陰性の試験） | - | - |

## 未確認の点

- 実機で、mini UART の console からログインできるか。
- 実機で、`hci_uart` が PL011 の Bluetooth chip を初期化できるか。
- mini UART を console にした QEMU の起動は試していない。QEMU の raspi3ap では、mini UART の probe が `bcm2835-aux-uart 3f215040.serial: error -EINVAL` で失敗する（stock のログにも出る）。

## ログ

ログはコミットしていません。手順のコマンドで再生成できます。本番の 10 本のログの SHA-256 は、CSV の `log_sha256` の行にあります。
