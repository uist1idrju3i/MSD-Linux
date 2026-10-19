# 調整項目（sysctl・I/O スケジューラーなど）の既定値の取得

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin
- 関連: [CPU・割り込み・sysctl の調整余地](../research/cpu-irq-and-sysctl.md)、[調整項目の全一覧](../research/tunables-defaults.md)

## 目的と仮説

本リポジトリのイメージで設定できる sysctl の全項目と既定値、ブロックデバイスの I/O スケジューラーと queue の設定、その他の調整項目（cpuidle、mm、thermal、モジュールパラメーター、Kconfig）を、通常の起動が終わった状態で一覧にします。rootfs に `/etc/sysctl.d/` の設定はないので、sysctl の値はカーネルの既定値になると予想しました。

## 採否の基準（結果を見る前に書く）

これは採否を決める比較ではなく、現状の記録です。次の条件をすべて満たせば、記録として採用します。

1. 各試行で `MSD_TUNABLES_BEGIN` と `MSD_TUNABLES_END` の両方が出て、sysctl の行が 1 行以上ある。
2. 同じ条件の 2 回（a1 と a2）で、項目の集合が一致する。値の差は、実行中に変わる値（UUID、カウンター、空きメモリーに依存する値）に限られる。
3. A スロットと B スロット（a1 と b1）で、cmdline 以外の差が 2 と同じ種類に限られる。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | イメージは CI run 39308965520（commit `ed42686237581a286b30c132991a58d950267221`）の成果物 `msd-cardputerzero-build`。この commit と、記録時の main `c65c85701e4e130668bbc7093832e03812d1a5a6` の間で `board/`、`configs/`、`vendor/`、`package/` に差分はない |
| 成果物の SHA-256 | `sdcard.img` `4e8e5f0454c0a276d46a0d13a6727a0ed1f6f0fe8cc6388aa72652e19f1ce9f4`、`Image` `38ee7560244e59558fe8fc6627187a90987820e86afcf6e5b534fbf96d5f507c`、`bcm2710-rpi-3-b.dtb` `cd922193672e391b6194d6d94e34ffab6fc154205375fcfb362cad191f7f8aae` |
| ホスト | Ubuntu 22.04.5 LTS、カーネル 6.8.0-1061-aws、x86_64、2 CPU |
| QEMU | `qemu-system-aarch64 --version`：QEMU emulator version 6.2.0（Debian 1:6.2+dfsg-2ubuntu6.31）、`-M raspi3b -m 1G` |
| カーネル | 6.18.57-v8（ゲストの `/proc/version`）。Buildroot の外部 toolchain は GCC 14.3.0、binutils 2.43.1 |
| 使ったツールの版 | unsquashfs／mksquashfs 4.5（2021/07/22）、Python 3.12.13 |
| 出力先と状態 | 成果物の展開先を `--output-dir` で渡した。ビルドはしていない |
| 変える条件 | 起動するスロット（A：`/dev/mmcblk0p5`、B：`/dev/mmcblk0p6`）、cmdline の `mem=512M` の有無 |
| 変えない条件 | カーネル、DTB、rootfs の中身（下の注入スクリプト 1 本を除く）、QEMU の機種と RAM |
| 繰り返し | a1、a2（A、1 GiB、同条件の 2 回）、b1（B、1 GiB）、m1（A、`mem=512M`）の 4 回 |

## 手順

QEMU の `raspi3b` のシリアルコンソールは、この環境では入力を受け付けませんでした（「捨てた試行」を参照）。そのため `dump-tunables.py` は、イメージの複製を作り、起動するスロットの SquashFS を展開して `/etc/init.d/S99zz-msd-tunables-dump` と `/usr/libexec/msd-bench/guest-dump.sh` を加え、zstd で作り直してから起動します。元のイメージは変えません。作り直した rootfs は所有者がすべて root になり、xattr を持ちません。この 2 点は sysctl などの値には影響しないと考えています【推測】。ダンプは `S98msd-ready` と `S99msd-health` の後に動き、`/proc/sys` と `/sys` に書き込みません。

```sh
gh run download 39308965520 -R uist1idrju3i/MSD-Linux -n msd-cardputerzero-build -D "$ART"
xz -dk "$ART/images/sdcard.img.xz"
tools=board/cardputerzero/tools/bench/tuning
python3 $tools/dump-tunables.py --output-dir "$ART" --slot 5 --csv a1.csv --log a1.log
python3 $tools/dump-tunables.py --output-dir "$ART" --slot 5 --csv a2.csv --log a2.log
python3 $tools/dump-tunables.py --output-dir "$ART" --slot 6 --csv b1.csv --log b1.log
QEMU_EXTRA_APPEND="mem=512M" python3 $tools/dump-tunables.py --output-dir "$ART" --slot 5 --csv m1.csv --log m1.log
python3 $tools/make-tables.py docs/experiments/2026-10-19-tunables-dump.csv docs-appendix.md \
  a1=a1.csv a2=a2.csv b1=b1.csv m1=m1.csv
```

Kconfig は、ゲストに `/proc/config.gz` がなかったため（`CONFIG_IKCONFIG=m` で、`configs.ko` が読み込まれていない）、rootfs の `lib/modules/6.18.57-v8/kernel/kernel/configs.ko.xz` を展開し、`IKCFG_ST` と `IKCFG_ED` の間を gzip として展開して取り出しました（8,824 行）。

## 計測器の検証

- a1 と a2 は、どちらも 2,447 行で、項目の集合が一致しました。値が違ったのは 32 項目で、すべて実行中に変わる値でした（`fs/dentry-state`、`fs/file-nr`、`kernel/random/boot_id`、`kernel/random/uuid`、`vm/user_reserve_kbytes`、各ブロックデバイスの `bdi/max_bytes`、`/proc/meminfo`、`/proc/interrupts`）。
- a1 と b1 では、上の種類の値を除くと、違いは `/proc/cmdline`（`root=`）だけでした。
- `mem=512M` が効いたことは、m1 のログの `Kernel command line: ... mem=512M` と、`MemTotal` が 938,092 kB から 489,192 kB に減ったことで確かめました。
- `kernel.sysrq` が 502（`0x1f6`）で、Kconfig の `CONFIG_MAGIC_SYSRQ_DEFAULT_ENABLE=0x1f6` と一致しました。`vm.swappiness` 60 などの既知の既定値とも一致しました。

## 結果

生の値は [2026-10-19-tunables-dump.csv](2026-10-19-tunables-dump.csv)（列は `run_id,variant,repeat,metric,value,unit,valid,note`。`metric` がパス、`unit` が種類）です。全一覧は [調整項目の全一覧](../research/tunables-defaults.md) にあります。

| 種類 | 項目数（a1） |
|---|---|
| sysctl（`/proc/sys`） | 606（net 363、kernel 118、fs 54、vm 45、user 12、sunrpc 6、abi 4、dev 3、debug 1） |
| ブロックデバイス（25 台：`mmcblk0`、`loop0`〜`loop7`、`ram0`〜`ram15`） | 1,385（`mmcblk0` は 65） |
| CPU | 27 |
| sysfs（mm、power、thermal） | 25 |
| モジュールパラメーター（81 モジュール） | 395 |

`mem=512M` で値が変わった sysctl は 24 項目でした（例：`fs/file-max` 86,624 → 41,792、`kernel/threads-max` 7,007 → 3,500、`vm/min_free_kbytes` 3,869 → 2,791、`net/ipv4/tcp_mem` `10899 14534 21798` → `5658 7545 11316`、`user/max_*_namespaces` 3,503 → 1,750）。

主な値と判断は [CPU・割り込み・sysctl の調整余地](../research/cpu-irq-and-sysctl.md#qemu-で取得した既定値) にまとめました。

## 捨てた試行と経緯

1. シリアルからログインして命令を送る方式（`expect` 相当）は、`root` を送っても応答がなく失敗しました。対話端末から手で入力しても同じでした。出力は届くので、QEMU 6.2.0 の `raspi3b` で PL011 の受信が届いていないと考えています【推測】。原因は調べていません。
2. `/data/etc` を `/etc` の overlay の下層に置く経路で init スクリプトを足す案は、`rcS` が `/etc/init.d/S??*` を overlay の mount より前に展開するため、使えないと判断しました。
3. 最初の版のスクリプトはリポジトリの最上位を誤って求め（`parents[3]`）、起動前に失敗しました。`parents[4]` に直しました。

## 結論

記録として採用します（基準 1〜3 を満たしました）。rootfs に sysctl の設定はなく、値はカーネルの既定値です。I/O スケジューラーは `mmcblk0` で `mq-deadline` が選ばれ、`none`、`kyber`、`bfq` も選べます。QEMU の値は実機の値ではありません。メモリー量、SD、cpufreq、温度に関わる値は実機で取り直す必要があります。

## 未確認の点

- CM0 実機での値（RAM はファームウェアの取り分を引いた量になる。SD コントローラーと SD カードが違う。cpufreq ドライバーが動く）。
- 実機の cmdline（`quiet`、`console=tty1 console=serial0,115200`）での `kernel/printk` の値。
- 新しい QEMU（10.x 以降）で、シリアル入力が使えるか。

## ログ

シリアルログはリポジトリに入れていません。上の手順で再生成できます。今回の SHA-256 は次のとおりです。

| 試行 | SHA-256 |
|---|---|
| a1.log | `f85532d8bd454ef008d090e1980aa03cec55a7df9ed600c3278728bfb15c4d98` |
| a2.log | `6c09c2ddacddffc26047d566f42ce2bc7d151421063a1466c3761a28258ec9ba` |
| b1.log | `fa84f2e808dc06a5ce6341e851746305dea84fcce39a8d38704cce5069635c8d` |
| m1.log | `33b07f908f3c1b826e878b56be38d8a51a412974478d0b982f5769be777dff81` |
