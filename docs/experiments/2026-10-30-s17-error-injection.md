# S17: device-mapper flakey によるストレージエラー注入（QEMU）

S17 の error 注入側を `dm-flakey` で実施した。速度模擬は [2026-10-29-s17-qmp-throttle](2026-10-29-s17-qmp-throttle.md) で QMP throttle として実施済み。

## 条件

- 基準: `origin/main` + output2 実験ツリー。カーネル 6.18.58 に `CONFIG_BLK_DEV_DM=y`・`CONFIG_DM_FLAKEY=y` を追加（実験のみ）
- ターゲット: `/data/t.img`（128 MiB）を loop0 に割当て、`dmsetup create ftest --table "0 262144 flakey /dev/loop0 0 0 120 2 drop_writes error_reads"` で up=0s・down=120s・write 破棄・read エラーの flakey デバイス `/dev/mapper/ftest` を作成
- dmsetup: Buildroot lvm2（libdevmapper 1.02.205）

## 生の値

| 操作 | 結果 |
|---|---|
| `dd if=/dev/zero of=/dev/mapper/ftest bs=1M count=128 conv=fsync` | `128+0 records out`（エラー無し・正常終了扱い） |
| `dd if=/dev/mapper/ftest of=/dev/null bs=1M count=10` | `Buffer I/O error on dev dm-0, logical block 0, async page read` で中断 |

`drop_writes` は書き込みを「成功として報告しつつ破棄」するため、dd は正常終了したがデータは届いていない。`error_reads` は読み出しを即座にエラーにし、dmesg に Buffer I/O error が出た。

## 結論

- `dm-flakey` は QEMU のブロックデバイス上に確定的なエラー注入ができ、速度模擬（S17 の QMP throttle）と合わせて「遅い・壊れる・黙って消える」の 3 状態が再現できる。
- `drop_writes` は silent data loss（呼び出し側に成功と見える）を再現するため、電源断・メディア劣化の worst case に近い。
- 製品の /data（mmcblk0p7）を直接 flakey で包むのは再起動を要し現行構成では困難。実験は loop デバイス上で実施した。

## 失敗した試行・注意点

- `BLK_DEV_DM=m` では `/dev/mapper/control` が無く `dmsetup` は `open failed: No such device` で失敗する。`CONFIG_MODULE_SIG_FORCE=y` 環境では未署名モジュールを読めないため、実験用は `=y` 組み込みが必須（`BLK_DEV_DM=y`・`DM_FLAKEY=y`）。
- flakey の up/down 窓が長いと高速な QEMU 書き込みが up 窓内に完了してエラーが出ない。確定的にエラーを出すには `up_time=0`（常時 down 窓）とする。
- `dmsetup` の存在だけでは flakey は使えない。`CONFIG_DM_FLAKEY` がカーネルに必要（同様に `DM_DELAY` も追加済みだが今回は未使用）。

## 未検証

- flakey 中の fsck / journal replay の回復経路（ext4 上でのエラー注入）
- `dm-delay` による遅延注入（S17 QMP throttle と併用する想定）
- 実機 SD カードのエラー応答（QEMU のエラー注入は論理ブロック層のみ）
