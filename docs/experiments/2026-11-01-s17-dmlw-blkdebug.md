# S17: dm-log-writes の再生と QEMU blkdebug によるストレージ障害注入

S17 の残り 2 項目を実施した。速度模擬（QMP throttle）は [2026-10-29-s17-qmp-throttle](2026-10-29-s17-qmp-throttle.md)、dm-flakey の error 注入は [2026-10-30-s17-error-injection](2026-10-30-s17-error-injection.md) で実施済み。

## 目的と事前の判定基準

結果を取る前に次を判定基準とした。

1. **dm-log-writes**: ゲストで決定的な書き込み列を dm-log-writes デバイスに流し、ログをホストの `replay-log` で再生した結果のディスクイメージが、ゲスト内で計算したディスクの SHA-256 と一致する。5 回連続で一致を合格とする。
2. **blkdebug**: QEMU の blkdebug ドライバーで EIO を注入したとき、注入が発火することをホスト側ログ（`sd_blk_*: * error on host side`）で確認し、注入範囲に対応するゲスト内操作の挙動を記録する。`control`（注入なし）は全操作成功かつホスト側エラー 0 件を期待値とする。

   なお当初は「注入範囲の read/write がゲストで失敗する」を基準にしたが、後述のとおり QEMU の SD エミュレーションがホスト側エラーをゲストに伝播しないことが判明し、ホスト側カウントを主検証に変更した。

## 条件

- 基準: `origin/main`（kernel b3495ea 含む）に加え、実験用 output2 ツリーは `CONFIG_BLK_DEV_DM=y`・`CONFIG_DM_LOG_WRITES=y`・`CONFIG_DM_FLAKEY=y`・`CONFIG_DM_DELAY=y`（`s17-dm.fragment`）と Buildroot `BR2_PACKAGE_LVM2=y`（`STANDARD_INSTALL=n` → dmsetup のみ）を追加
- QEMU: msd-dev 同梱の 11.1.2。`-drive file=blkdebug:<conf>:<disk>,if=sd,format=blkdebug`
- 観測側: repack した捨て rootfs に init hook（`S97zz-dmlwtest`・`S97zz-blkdbgtest`）を入れ、`msd.*test=1` の cmdline でのみ動作。`QEMU_COPY_IMAGE=0` で使い捨てディスクコピーに書き込む
- ホストの `replay-log`: josefbacik/log-writes を x86_64 用にビルド（実験のみ・製品には含めない）

## 手順

### dm-log-writes（5 回）

1. `s17-dm-log-writes.sh` が実験 rootfs を作り、A スロットに差し込んだ SD イメージで QEMU を起動
2. ゲスト内で `/data/dmlw-disk.img`（16 MiB）と `/data/dmlw-log.img`（64 MiB）を loop デバイスに割当て、`dmsetup create dmlw --table "0 32768 log-writes ..."` で log-writes デバイスを作成
3. 決定的な書き込み列: `dd if=/bin/busybox count=128`＋`seek=200 count=64`＋`dd if=/dev/urandom seek=400 count=32`（いずれも bs=4096 conv=notrunc,fsync）
4. `dmsetup message dmlw 0 mark done` でマーカーを打ち、disk_sha と log_size を console に出力
5. ホスト側で `debugfs` を使い p7（/data）から 2 ファイルを回収し、`replay-log --log dmlw-log.img --replay dmlw-replay.img` で再生して SHA-256 を比較

### blkdebug（5 ケース × 5 回）

1. `s17-blkdebug.sh` が実験 rootfs 入りの SD イメージを作り、blkdebug conf を生成して QEMU を起動
2. ケース: `control`（注入なし）、`wio`（全 write に EIO）、`rio`（全 read に EIO）、`p6w`（B スロット rootfs 先頭 4096 sector の write に EIO）、`p7w`（/data 先頭 4096 sector の write に EIO）
3. ゲスト内で `/data` への 4 MiB 書き込み、`/dev/mmcblk0p6` への 2 MiB 書き込み、`/data`・`/dev/mmcblk0p5` の読み出しを試行し、dmesg の I/O error 数を記録。ホスト側は `sd_blk_write/read: * error on host side` の出現数を `host_werr`/`host_rerr` として CSV に記録

## 生の値

### dm-log-writes（5 回、`s17-dmlw.csv`）

| run | dm_create | mark | disk_sha（先頭 12 桁） | replay_sha | match | finished |
|---|---|---|---|---|---|---|
| 1 | ok | ok | 3a967321db8c | 一致 | yes | yes |
| 2 | ok | ok | f53ad706e8f8 | 一致 | yes | yes |
| 3 | ok | ok | 882a77c103a8 | 一致 | yes | yes |
| 4 | ok | ok | 6116f50e8aea | 一致 | yes | yes |
| 5 | ok | ok | 05a452bd709b | 一致 | yes | yes |

- 5 回とも、ゲスト内で計算したデバイスの SHA-256 と、ホスト側で `replay-log` がログを再生したイメージの SHA-256 が完全一致。`mark done` までの書き込み列がログに欠落なく記録され、再生で同一状態に到達することを確認した。
- disk_sha はランごとに異なる。ワークロード内の `/dev/urandom` 由来ブロックがランごとに変わるためで、基準は「同一ラン内で disk_sha と replay_sha が一致すること」と定義していたとおりに達成。
- log_bytes はコミット前の版では `stat` 依存で未取得（空欄）。リポジトリ側のスクリプトは `wc -c <` に修正済み（失敗した試行 10 を参照）。

### blkdebug（5 ケース × 5 回、`s17-blkdebug.csv`）

| run | case | ゲスト write | ゲスト read | data_mount | io_errors | host_werr | host_rerr | finished |
|---|---|---|---|---|---|---|---|---|
| 1-5 | control | ok / ok | ok / ok | ext4 | 0 | 0 | 0 | yes |
| 1 | wio | ok / ok | ok / ok | ext4 | 0 | 21176 | 0 | yes |
| 2 | wio | ok / ok | ok / ok | ext4 | 0 | 21240 | 0 | yes |
| 3-5 | wio | ok / ok | ok / ok | ext4 | 0 | 21176 | 0 | yes |
| 1-5 | rio | （未到達） | （未到達） | none | 0 | 0 | 8 | no（timeout） |
| 1-5 | p6w | ok / ok | ok / ok | ext4 | 0 | 256 | 0 | yes |
| 1-5 | p7w | ok / ok | ok / ok | ext4 | 0 | 21 | 0 | yes |

- control は 5 回ともホスト側エラー 0 件で、注入 conf の発火誤りはない。
- wio は「guest 側の全 write が成功を返すのに、ホスト側では約 2.1 万件の write エラーが発火」という、ゲスト観測とホスト観測が完全に乖離する結果が 5 回とも再現した（run2 だけ 21240 で残りは 21176。ブートごとの書き込み量ゆらぎ）。
- rio はブート段階の read 注入で 8 件発火した後、ゲストが進まず S17_TIMEOUT で打ち切り。ゲストにはエラーが返らないため、読み取りエラーで止まるのではなく、stale バッファ内容で起動シーケンスが進まない状態になる。
- p6w（p6 先頭の write 注入）はゲスト書き込み側で host_werr=256 だけ発火し、その他の書き込みには発火しない。注入範囲の狙いどおりにだけ効いている。p7w も同様に 21 件だけ発火。
- **5 回とも結果が完全に一致した**（wio の 64 件差を除き件数まで再現）。

## 結論

1. **blkdebug は注入範囲（セクタ・iotype）どおりに確実に発火する**。p6w/p7w が対象パーティションの write にだけ発火したこと、wio が全 write に発火したことで、conf 生成と `inject_offset`/`sector`（512 B 単位）・iotype の解釈は正しい。
2. **しかし QEMU の SD モデルはホスト側エラーをゲストに伝播しない**。`hw/sd/sd.c` の `sd_blk_write`/`sd_blk_read` は失敗を `* error on host side` として stderr に出すだけで、SD コマンド応答には反映されず、ゲストの syscall は成功・あるいは stale バッファの読み値を返す。ゲスト側で「書き込みエラーで起きる挙動」を観測するには、QEMU では手段がない。
3. **S17 の QEMU 網羅表への影響**: 「ストレージ障害をゲストに観測させる」項目は QEMU では到達不能と確定。残りは実機（S9 の電源断など）での検証になる。QEMU でできるのは「注入が発火すること」をホスト側で確認する段階まで。
4. **dm-log-writes の書き込みログは完全再生できる**。5 回とも `replay-log` 再生イメージの SHA-256 がゲスト計測値と一致し、`mark done` までの全 write がログに記録され再生で再現できることを確認。msd-update の書き込み列をこの仕組みで検証する土台になった。

## 失敗した試行・注意点

1. **`output/host/bin/mksquashfs` がコンテナ内で動かない**: Buildroot が生成するこのファイルは実体ではなく、`mksquashfs.orig` をビルド時の絶対パスと `-sort` ファイルの絶対パスで起動するシェルスクリプトだった。msd-dev コンテナは `/work` にだけマウントするため `exec` に失敗した。対処: docker run に `-v <repo>:<repo の絶対パス>` を追加し、ホストと同じパスをコンテナ内でも解決できるようにした。
2. **blkdebug の `iotype` 値は enum の完全名でないと QEMU が起動時に死ぬ**: 最初 `iotype = "w"` / `"r"` を書いていたが、blkdebug の IOType enum は `"read"` / `"write"` などの完全名のみ受け付ける。`qemu-system: invalid parameter value: w` で QEMU が即終了し、wio/rio は「注入による起動失敗」ではなく「起動不能」になっていた。
3. **guest 側の page cache が注入をすり抜ける**: `dd conv=fsync` でも write_p6/write_data は buffer cache に吸収され、read_data/read_p5 は書いたばかりのデータを cache から返した。p6w/p7w で `write_p6=ok, io_errors=0` と注入不発になった。ホスト側の `qemu-img convert` で同じ conf が byte 432013312（= sector 843776×512、p6 先頭）で EIO を出すことは確認したため、conf 側の問題ではなく guest 側のキャッシュと判断し、`sync` と `drop_caches` を追加した。
4. **QEMU の SD エミュレーションは注入エラーをゲストに伝播しない**: `sd_blk_write`（hw/sd/sd.c）は `blk_pwrite` 失敗時に `sd_blk_write: write error on host side` を stderr に出すだけで、SD コマンドのステータスには影響しない（戻り値なし）。read も同様で、失敗した read には古いバッファ内容が返る。monitor の `qemu-io` で確認: `write -P` は EIO（iotype=write が発火）、`write -z` は write-zeroes 扱いで iotype=write の対象外、read 注入は `read failed: Input/output error` で発火。つまり QEMU 上では注入は発火してもゲストのシステムコールは成功を返す。ゲストへの障害伝播が必要な検証は実機（S9 の電源断など）でしかできない。
5. **blkdebug の注入単位は iotype enum で分かれる**: `write -z` は `WRITE_ZEROES`、通常 write は `WRITE`。iotype=write だけでは write-zeroes を捕まえない。
6. **BusyBox の `losetup` に `--show` はない**: ゲスト側テストが `losetup -f --show FILE`（util-linux 構文）を使っていたため、BusyBox losetup が usage エラーで終了し `loop_setup=fail` で全ラン失敗（stderr を捨てていたため `loops=,` としてだけ見えた）。`losetup -f` で空きデバイス名を取得 → `losetup DEV FILE` で割当てる BusyBox 互換の書き方に修正。
7. **`images/Image` が `.config` より古いカーネルから来ていた**: dmsetup create が `log_writes: unknown target type` で失敗。`linux-custom/vmlinux` には `log_writes_ctr` 等があるのに `images/Image`（と sdcard.img 内のカーネル）には `log_writes` の文字列自体がなく、`flakey` だけある。output2 の stamp flake 対処で古い arch/arm64/boot/Image が images/ に残ったままだったと判断し、linux-custom で Image を再ビルドして差し替えた。
8. **dm-log-writes の docker 起動を 2 重に行い、片方を停止した**: 1 回目の実行は `replay-log` のコンテナ内パス未マウントで失敗。修正して再起動した際、先のコンテナも動いていたため CSV が混ざる恐れがあり、両方止めて CSV・build ディレクトリを退避して 1 本で回し直した。
9. **dm ターゲット名は `log-writes`**: スクリプトは当初 `log_writes`（アンダースコア）で `dmsetup create` しており、`log_writes: unknown target type` で失敗。`drivers/md/dm-log-writes.c` の `.name` は `log-writes` であり、ハイフンに修正。
10. **ゲストに `stat` がない**: ログサイズを `stat -c%s` で取っていたため BusyBox で `stat: not found` となり log_bytes が空欄になった（match 判定には無関係）。リポジトリ側は `wc -c <` に修正済み。


## 未検証

- 実機 SD カードの障害応答とゲストへのエラー伝播（QEMU の SD モデルはホスト側エラーを伝播しないため、ゲスト側の失敗検証は実機依存）
- dm-log-writes のログを msd-update の実書き込み列に適用した検証（今回は合成ワークロード）
