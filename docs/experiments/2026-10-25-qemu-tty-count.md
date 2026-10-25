# QEMU の console で出る `tty->count` の警告

- 状態: 実施中
- 日付: 2026-10-25
- 担当: Devin
- 関連: [振り返り](../research/retrospective-2026-10.md) の残タスク「tty の警告」、[2026-10-21-qemu-lynis](2026-10-21-qemu-lynis.md)

## 目的と仮説

QEMU のシリアルログに、起動の終わり近くで次の行が出ます。原因を確かめます。

```text
ttyAMA ttyAMA1: tty_open: tty->count(2) != (#fd's(1) + #kopen's(0))
```

仮説: QEMU の console は `console=ttyAMA1`（PL011）です。CM0 の DTB では、PL011 の子に Bluetooth の node（`brcm,bcm43438-bt`、`status = "okay"`）があり、serdev の controller になります。起動中に `hci_uart` が読み込まれると、serdev が `tty_init_dev()` で tty を開きます。このとき file は登録されず、`tty->count` だけが 1 増えます。そのあとで `/dev/console` を開くと、file の数より `tty->count` が 1 多くなり、`check_tty_count()` が警告を出します。

## 採否の基準（結果を見る前に書く）

1 回ずつの予備試行（後述）のあと、本番の前に書きました。

- 仮説を支持する条件: stock の 5 回すべてで `warnings_total` が 1 以上かつ `serdev_registered` が 1。bt-off の 5 回すべてで `warnings_total` が 0 かつ `serdev_registered` が 0。
- 副次の指標: シリアルから `root` でログインし、`echo TTYPROBE-$((6*7))` の結果 `TTYPROBE-42` が返るか（`shell_probe`）。予備試行では stock で返りませんでした。stock 5/5 で no、bt-off 5/5 で yes なら、「serdev がシリアルの入力を受け取っている」と記録します。
- 1 回でも外れたら、仮説は支持されないと書き、ログを読んで原因を記録します。
