# 永続storageへの書き込みの台帳

[文書の案内へ戻る](../README.md)

[AGENTS.md §10](../../AGENTS.md) の規則（利用者が意図しない時に書き込まない、2秒以上かかり得る処理ではprogressを表示する）について、現行の製品で永続storage（SDカード）に書き込む箇所と、その扱いを記録します。手順は「product-io-policy」スキル（`.agents/skills/product-io-policy/SKILL.md`）にあります。

書き込みの経路を調べた過去の記録は、[書き込み経路・read-only policy案・S3](../research/storage/write-policy-and-s3.md) にあります。この台帳は、現在の規則に照らした判定だけを書きます。

## 状態の意味

| 状態 | 意味 |
|---|---|
| 例外 | 規則の例外として認めた書き込みです。理由と時機を書きます |
| 未対応 | 規則に合わない可能性がある現行の箇所です。直すPRで状態を変えます |
| 未確認 | 書き込みがあるかどうかを、まだ測っていない箇所です |

## 現行の箇所

この表は、2026-11-03の `origin/main` のコードを静的に確かめた範囲です。QEMUと実機で、書き込みの量と時機はまだ測っていません。

| 箇所 | 書き込み先と時機 | progress | 状態 | 扱いの案 |
|---|---|---|---|---|
| [S02msd-data](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data) の `mkfs.ext4` | 空の `/data`（p7）を、初回起動の時にformatします | なし | 未対応 | `/data` の初期暗号化を実装する時に、progressを表示する処理へ置き換えます |
| S02msd-data の `fsck.ext4 -p` | `/data` に問題があれば、起動のたびに修復を書き込みます | なし | 未対応 | 電源断の後の回復は必要なので、例外にする案です。修復した時は、そのことを表示します |
| S02msd-data の `mkdir -p` | `/data/etc`、`/data/msd-update`、`/data/seedrng` を、起動のたびに作ります（既にあれば書き込まない見込み、推測） | なし | 未確認 | QEMUの記録で確かめます |
| [msd-data-grow](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow) | 初回起動の時に、partition tableを書き換え、`resize2fs` で `/data` を広げます | なし | 未対応 | 初期暗号化と同じ処理の中で、progressを表示します |
| seedrng（`S05seedrng`、`--seed-dir=/data/seedrng`） | 起動と停止のたびに、乱数のseedを `/data/seedrng` に書きます（BuildrootのS01seedrngを後ろに移したもの） | なし | 未対応 | 起動のたびの書き込みです。seedを保存する時機（利用者の操作の時など）と、保存しない場合の乱数の質を比べます |
| [msd-update](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) の `install` | 利用者が実行した時に、待機中のslot（p2/p3、p5/p6）へ `dd ... conv=fsync` で書き、`/data/msd-update` に状態を書きます | なし | 未対応 | RAUCかSWUpdateへ移る時に、progressを表示します。利用者の操作で始まる点は規則に合います |
| [S99msd-health](../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health) からの `msd-update commit` | 試し起動（tryboot）の時だけ、`/data/msd-update` とFATの `autoboot.txt` を書きます | なし | 未対応 | 利用者が始めた更新の続きです。例外にする案で、起動の画面に更新中であることを表示します |
| ext4のjournal commit | 書き込みがある時に、既定で5秒ごとにcommitします。書き込みがなければ動かない見込みです（推測） | 対象外 | 未確認 | QEMUの記録で確かめます |
| ext4の `lazy_itable_init` | `mkfs.ext4` で指定していないので、mountの後にkernelが裏でinode tableを埋める見込みです（推測） | なし | 未確認 | QEMUの記録で確かめます。mkfsで `lazy_itable_init=0` を指定する案は、option表で比べます |

## RAMに置いているもの

| 対象 | 置き場所 | 根拠 |
|---|---|---|
| `/var/log`、`/var/cache` | `/tmp`（tmpfs）へのsymlink | Buildrootのskeleton |
| `/tmp`、`/run`、`/dev/shm` | tmpfs | [fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| `/etc` の変更 | overlayのupperが `/run/etc-overlay`（tmpfs） | [S03msd-etc-overlay](../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay) |

tmpfsは圧縮していないRAMです。zramを使うかどうかは、まだ決まっていません。過去にQEMUで試した記録は [zramの実験](../experiments/2026-10-21-qemu-zram.md) にあります。

## まだ確かめていないこと

- BusyBoxのsyslogdとklogdが、製品のimageで起動しているかと、書き込み先が `/var/log`（RAM）だけかどうか。
- Wi-FiとSSHを実装した後の、DHCP lease、`known_hosts`、shellのhistoryの書き込み先。
- QEMUでidleの状態のときに、blockへの書き込みが0件かどうか。
- 実機のSDで、`/sys/block/mmcblk0/stat` の書き込みの差分が0かどうか。
