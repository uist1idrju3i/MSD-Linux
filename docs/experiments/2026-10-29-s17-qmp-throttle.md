# S17: QMP `block_set_io_throttle` によるストレージ速度模擬（QEMU）

S17 のうち、カーネル・rootfs の再構築が不要な範囲として、QEMU の QMP で SD drive の I/O 帯域を実行中に絞り、ゲストの読み出し時間への影響を測った。

## 条件

- QEMU 11.1.2、`raspi3ap`、512 MiB、`QEMU_COPY_IMAGE=0`、1 GiB padding 済みの複製 image。
- `QEMU_QMP_SOCKET=/work/output/s17.sock`（`-drive` は node-name 未指定で `sd0` として現れた）。
- ゲストで 4 MiB のファイルを `dd conv=fsync` で作成し、`echo 3 > /proc/sys/vm/drop_caches` 後に `cat` の `real` 時間を比較。

## 手順と生の値

1. 起動 → `/data/tf2` に 4 MiB 作成 → drop_caches → 無制限で読み出し: `real 0m 1.72s`（約 2.4 MiB/s）。
2. ホストから QMP `block_set_io_throttle`（`device=sd0, bps=131072` ほか 0 埋め必須）を適用。
3. drop_caches → 同一ファイルを読み出し: `real 0m 32.18s`。

理論値: 4 MiB ÷ 128 KiB/s = 32 s と一致し、throttle が正確に効いている。

## 結論

- S17 の「速度の模擬」は `QEMU_QMP_SOCKET` + `block_set_io_throttle` で無改造に実現できる。起動時間・fsck・ログローテーションなど低速メディア影響の試験に使える。
- `block_set_io_throttle` では error 注入はできない。fault（drop/corrupt）系は dm-flakey（kernel config 未設定）と blkdebug（drive 定義の変更が必要）が次の手段。
- `dmsetup` と `dm-flakey`/`dm-log-writes` は現行 image に無く、guest 側の error 模擬には `BR2_PACKAGE_DMSETUP` とカーネル設定の追加が必要。

## 失敗した試行

- `QEMU_QMP_SOCKET=/tmp/...` はコンテナ内の /tmp に作られ、ホストから届かない。`/work`（=リポジトリ）配下に置く必要がある。
- `block_set_io_throttle` は `bps`/`iops` だけでは `Parameter 'iops_rd' is missing` で拒否された。`bps_rd`,`bps_wr`,`iops`,`iops_rd`,`iops_wr`,`*_max`,`iops_size` を全て指定して受理された。
- Python の `socket.makefile('rw')` は UNIX socket で `OSError: [Errno 22]` となり、`recv`/`sendall` 直呼びに変えた。

## 未検証

- blkdebug（delay/error 注入）・dm-flakey・dm-log-writes + replay、実カード FTL の振る舞い。
- throttle 下での fsck・起動時間・更新処理の挙動。
