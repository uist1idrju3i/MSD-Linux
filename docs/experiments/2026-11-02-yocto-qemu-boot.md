# Yocto 最小イメージの QEMU 起動確認

- 状態: 完了（QEMU のみ）
- 日付: 2026-11-02
- 担当: Devin
- 関連: [Yocto Wrynose の構築試験](2026-11-02-yocto-wrynose-probe.md)、[Yocto 移行の調査](../research/yocto-migration/README.md)、[移行計画（案）](../research/yocto-migration/migration-plan.md)

## 目的と仮説

[構築試験](2026-11-02-yocto-wrynose-probe.md) の E（Wrynose 6.0.4、`raspberrypi0-2w-64` の `core-image-minimal`）で作ったカーネル・dtb・wic が、QEMU でシリアルのログイン画面まで起動するかを確かめます。現行の Buildroot イメージと同じく、512 MiB の `raspi3ap` には ASB パッチ入りの開発用 QEMU が必要で、標準の QEMU では `bcm2835-power` で止まると予想しました（[docker/README.md](../../docker/README.md)）。

この試験は CardputerZero の完成イメージの確認ではありません。E は A/B も SquashFS の root も持たない最小イメージで、確かめるのはカーネル、dtb、rootfs のマウント、BusyBox init、getty までです。

## 採否の基準（結果を見る前に書く）

- 合格: シリアルのログに `login:` が出ること。現行の `board/cardputerzero/qemu/test-boot.sh` と同じ考え方です。
- 繰り返し 5 回で 5 回とも合格すること。時間は参考値として記録し、合否には使いません。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `c26028c38076e008e3e6f649cdc0cc38818b63da`（構築試験の記録を含む main） |
| ホスト | Ubuntu 26.04.1、x86_64 |
| QEMU（開発用） | 11.1.2（`docker/msd-dev` の公開イメージ `sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`、バイナリの SHA-256 `037b8388afae4e96082b83b80008c4e1e583ee541ee6e653a44e903b479746a7`） |
| QEMU（標準） | 10.2.1（Ubuntu の `1:10.2.1+ds-1ubuntu3.3`、バイナリの SHA-256 `ed02064f80fc8d4e5207effc416881fc05935dd2614ee9f413bb618adcc9f2cb`） |
| カーネル | E の `kernel8.img`（Linux 6.18.33-v8、SHA-256 `24e7ae28cdb6542e6718d301ed19087f60387b7c73ceb1a996bb463633d1cd45`） |
| dtb | E の `bcm2710-rpi-zero-2.dtb`（`ce3ca3176658cddfad2ef6414d858bad61ce5242382eb0755248ea0edfcb0783`）。QEMU 用に Bluetooth のノード（`brcm,bcm43438-bt`）の `status` を `disabled` にした `qemu.dtb`（`2d16e7cab4420ab297a48ad7c3a1aab83ee3bfdcf95c3952f0e6e53ceb16aa1f`） |
| イメージ | E の `core-image-minimal-raspberrypi0-2w-64.rootfs-20261102002833.wic.bz2`（26,116,676 bytes、SHA-256 `e66f30e6447e33d00c0914dde35f2762eb261116ba8d43c6e2f1f7801159bd06`）を展開した wic（`026e9a4f11e351c5db53c1d8331e7e4ba8dab2881e97a8a4992fd5714d8cd00d`）。p1 が vfat、p2 が ext4 |
| 変える条件 | QEMU（開発用 / 標準）、machine（`raspi3ap` 512M / `raspi3b` 1G）、console、inittab の getty 行 |
| 変えない条件 | カーネル、dtb、カーネル引数のうち root 関係（`root=/dev/mmcblk0p2 rootfstype=ext4 rootwait`）、`initcall_blacklist=bcm2835_wdt_driver_init` |
| 繰り返し | 開発用 `raspi3ap` と標準 `raspi3b` で各 5 回 |

### イメージに加えた変更

E の inittab は、シリアルの getty を `ttyS0`（mini UART）にだけ置いています（`ttyS0::respawn:/usr/sbin/ttyrun ttyS0 /sbin/getty -L 115200 ttyS0`）。QEMU では mini UART のドライバーが pinctrl の段階で失敗し（`bcm2835-aux-uart 3f215040.serial: there is not valid maps for state default`）、`/dev/ttyS0` ができません。そこで、イメージの写しの p2 に debugfs で 1 行だけ足しました。元のイメージは変えていません。

```text
ttyAMA1::respawn:/sbin/getty -L 115200 ttyAMA1
```

PL011 は `ttyAMA1` として登録されます（ログに `3f201000.serial: ttyAMA1 at MMIO 0x3f201000`）。これは現行の `board/cardputerzero/qemu/run-qemu.sh` が `console=ttyAMA1` を使うのと同じです。変更後の写し `run7.wic` の SHA-256 は `ddd68be66386bab425be21975c2f6430bf261b1c0f07c9e5f04777ee226c779e` です。

## 手順

```sh
# wic の p2（開始 278528 セクター、47672 セクター）を取り出し、inittab を 1 行足して書き戻す
dd if=e.wic of=p2.ext4 bs=512 skip=278528 count=47672
debugfs -R 'cat /etc/inittab' p2.ext4 > inittab.run7
echo 'ttyAMA1::respawn:/sbin/getty -L 115200 ttyAMA1' >> inittab.run7
printf 'rm /etc/inittab\nwrite inittab.run7 /etc/inittab\nsif /etc/inittab mode 0100644\nsif /etc/inittab uid 0\nsif /etc/inittab gid 0\n' > dbg.cmd
debugfs -w -f dbg.cmd p2.ext4
cp e.wic run7.wic && dd if=p2.ext4 of=run7.wic bs=512 seek=278528 conv=notrunc

# 起動（各回、run7.wic の写しを 256 MiB に伸ばして使う）
cp run7.wic run.img && truncate -s 256M run.img
qemu-system-aarch64 -M raspi3ap -m 512M -kernel kernel8.img -dtb qemu.dtb \
  -drive file=run.img,if=sd,format=raw \
  -append "earlycon=pl011,mmio32,0x3f201000 console=ttyAMA1,115200 root=/dev/mmcblk0p2 rootfstype=ext4 rootwait initcall_blacklist=bcm2835_wdt_driver_init" \
  -display none -serial file:run.log -serial null -monitor none
```

開発用 QEMU は `docker/msd-dev bash -c '...'` の中で、標準 QEMU はホストで動かしました。5 回の繰り返しは、ログを 0.5 秒ごとに見て `login:` が出た時点の経過時間を記録し、QEMU を止めるスクリプトで行いました。

```sh
for i in 1 2 3 4 5; do
  cp run7.wic "$img"; truncate -s 256M "$img"; : > "$log"
  t0=$(date +%s.%N); "$Q" -M "$M" -m "$MEM" ...（上と同じ引数） & pid=$!
  for _ in $(seq 1 240); do sleep 0.5
    grep -aq 'login:' "$log" && { lw=$(awk -v a="$(date +%s.%N)" -v b="$t0" 'BEGIN{printf "%.1f", a-b}'); res=pass; break; }
    kill -0 $pid 2>/dev/null || { res=exited; break; }
  done
  kill $pid; wait $pid
  init=$(grep -a 'Run /sbin/init' "$log" | sed -E 's/^\[ *([0-9.]+)\].*/\1/')
done
```

## 計測器の検証

- 負の対照: inittab を変えていない E（Q2・Q3）と、getty の引数を誤った写し（Q6）では `login:` は出ませんでした。判定の marker は、getty が実際に動いたときだけ出ます。
- `init_s` はゲストのカーネルの時刻、`login_wall_s` はホストの経過時間で、0.5 秒の確認間隔の誤差を含みます。

## 結果

生の値は [2026-11-02-yocto-qemu-boot.csv](2026-11-02-yocto-qemu-boot.csv) にあります。

| 条件 | 合格 | `Run /sbin/init` の時刻（中央値、最小〜最大） | `login:` までのホスト経過時間（中央値、最小〜最大） |
|---|---|---|---|
| 開発用 QEMU 11.1.2、`raspi3ap`、512 MiB | 5 / 5 | 5.606 s（5.202〜5.935 s） | 12.1 s（11.6〜13.1 s） |
| 標準 QEMU 10.2.1、`raspi3b`、1 GiB | 5 / 5 | 5.475 s（5.247〜5.819 s） | 13.2 s（13.2〜13.7 s） |

いずれも QEMU での値で、実機の値ではありません。また、Buildroot のイメージの起動時間と比べられる値ではありません（rootfs の種類、init の中身、カーネルが違います）。

### 失敗・途中の試行

| 試行 | 内容 | 結果と分かったこと |
|---|---|---|
| Q1 | 標準 QEMU、`raspi3ap` | 4.34 s に `bcm2835_power_probe` で `synchronous external abort`。ASB 領域が未実装のためで、予想どおりです |
| Q2・Q3 | 開発用 `raspi3ap` / 標準 `raspi3b`、`console=ttyAMA0` | カーネルは root をマウントし、init が `/` を読み書き可能に戻すところまで進みます。init の出力はシリアルに出ません |
| Q4 | 写しに `ttyAMA0` の getty を追加 | 出力なし |
| Q5 | 写しの sysinit 行ごとに `echo` を追加 | marker も出ません。ログから、PL011 が `ttyAMA1` であると分かりました |
| Q6 | `console=ttyAMA1` | BusyBox v1.37.0 の init が sysinit の全行と `rcS` を実行することを確認しました。getty の引数を直し忘れていました |
| Q7 | `ttyAMA1` の getty | `raspberrypi0-2w-64 login:` が出ました |

Q2 以降のすべての回で、14〜15 s ごろに `mmc1: Timeout waiting for hardware interrupt.` が出ます。SDIO（無線）側のコントローラーと考えられますが、確かめていません。`mount: mounting devtmpfs on /dev failed: Device or resource busy` も出ます。カーネルが先に devtmpfs をマウントしているためで、起動には影響しませんでした。

## 結論

- Yocto Wrynose で作ったカーネル・dtb・rootfs は、QEMU でログイン画面まで起動しました。開発用 QEMU（ASB パッチ入り）の `raspi3ap` と、標準 QEMU の `raspi3b` の両方で 5 回とも合格です。
- 標準 QEMU の `raspi3ap` は、Buildroot のイメージと同じ理由で起動できません。ASB パッチは Yocto のイメージにも必要です。
- 製品の image では、シリアルの getty と console を `ttyAMA1`（QEMU）と実機の UART の両方で考える必要があります。meta-raspberrypi の既定（`raspberrypi3-64.conf` の `SERIAL_CONSOLES ?= "115200;ttyS0"`）をそのまま使うと、QEMU の起動試験でログイン画面が出ません。
- 確かめていないこと: LCD、内蔵キーボード、M5 の I2C 周辺機器、tryboot と A/B、SquashFS の root、電源断、実機。

## 再実行の方法

E は [構築試験の記録](2026-11-02-yocto-wrynose-probe.md) の手順で再生成できます。QEMU のログ（17 ファイル）はリポジトリに入れていません。上の手順で再生成でき、入力の SHA-256 は条件の表にあります。
