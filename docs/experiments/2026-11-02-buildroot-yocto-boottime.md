# Buildroot と Yocto の QEMU での起動時間の比較

- 状態: 完了（QEMU のみ）
- 日付: 2026-11-02
- 担当: Devin
- 関連: [成果物の比較](2026-11-02-buildroot-yocto-artifacts.md)、[Yocto の QEMU 起動確認](2026-11-02-yocto-qemu-boot.md)、[Pros/Cons（2026-11）](../research/yocto-migration/pros-cons-2026-11.md)、`board/cardputerzero/tools/bench/yocto-compare/`

## 目的と仮説

Buildroot と Yocto（Wrynose 6.0.4）で作ったイメージを、同じ QEMU と同じ起動方法で起動し、起動の段階ごとの時刻を比べます。Yocto 側には CardputerZero の完成イメージがないため、イメージ同士の単純な比較では、ビルドシステムの違いと中身の違いが混ざります。そこで、カーネルと rootfs を入れ替えた組み合わせも測り、差がカーネルから来るのか rootfs から来るのかを分けます。

## 採否の基準（結果を見る前に書く）

この実験は採否を決めるものではありません。差の読み方を、測る前に次のとおり決めました。

- 主な指標は、通常起動 5 回の中央値です。初回起動（boot 0）は、/data の拡張などの初回処理を含むため除きます。
- 二つの条件の差は、中央値の差の絶対値が、両条件の最小〜最大の幅のうち大きいほうの 2 倍を超え、かつ icount と TCG で差の向きが同じときだけ「差がある」とします。満たさないときは「差があるとは言えない」とします。
- QEMU の値は実機の値ではありません。

## 条件

| 条件 | カーネル | rootfs とイメージ | 準備完了の目印 |
|---|---|---|---|
| C1-br | Buildroot の `Image`（6.18.59-v8、Bootlin GCC 14.3.0） | Buildroot の `sdcard.img`（p5 の SquashFS） | `MSD/Linux ready`（`S98msd-ready` が `/dev/kmsg` に書く） |
| C2-yocto-e | Yocto E の `Image`（6.18.33-v8、meta-raspberrypi の既定設定、GCC 15.3.0） | Yocto E の wic（p2 の ext4）に getty と目印の 2 行を足した写し | `msd-compare: ready`（inittab の rcS の直後で `/dev/kmsg` に書く） |
| C3-yocto-b2k | Yocto B2 の `Image`（6.18.59-v8、MSD の fragment、GCC 15.3.0） | C2 と同じ | 同上 |
| C4-brk-yroot | Buildroot の `Image` | C2 と同じ | 同上 |
| C1-br-aa | C1 と同じ（icount だけ。A/A 試行） | C1 と同じ | C1 と同じ |

| 項目 | 値 |
|---|---|
| 基準の commit | `c26028c38076e008e3e6f649cdc0cc38818b63da`（Buildroot の出力）。計測スクリプトは本 PR の `board/cardputerzero/tools/bench/yocto-compare/` |
| ホスト | Ubuntu 26.04.1、x86_64、12 CPU。計測中はほかのビルドを止めた |
| QEMU | 11.1.2（`docker/msd-dev`、`sha256:c5beb4973cad6bef273fd0efc51deb89e334de5f5b1700de2f41980410d65d77`）。`raspi3ap`、512 MiB |
| DTB | すべての条件で Buildroot の `bcm2710-rpi-cm0.dtb`（`f6c9ee59ccc5adb164ddba6508acc99e8038d2fe2017bd1f5fd5567af4999094`）。`run-qemu.sh` が Bluetooth のノードを無効にする |
| 起動方法 | すべて `board/cardputerzero/qemu/run-qemu.sh`（`console=ttyAMA1`、`ro`、ウォッチドッグのドライバーを除外）。追加の引数は `printk.time=1 msd.sweep=1`（`msd.sweep=1` は `S98msd-ready` が目印を `/dev/kmsg` に書くためだけに使う） |
| モード | icount（`shift=0,sleep=off`。命令 1 個を 1 ns とする仮想時間）と TCG |
| 繰り返し | 条件とモードごとに、イメージを 1 回写してから初回起動 1 回と通常起動 5 回。毎回、目印とログイン画面が出た時点で QEMU を止める |

入力の SHA-256: Buildroot `Image` `5e730f3da4b4ab31bff38fc2c1bff7a9d9dfb48127d7722e3976c01a5a5fed63`、`sdcard.img` `117370a1c8376eda74e9d4e1245f79c6d2e00210788c97151ee3e266a621324a`、Yocto E `Image` `24e7ae28cdb6542e6718d301ed19087f60387b7c73ceb1a996bb463633d1cd45`、Yocto B2 `Image` `368d312d9bb47a7afd945730574df31f0c561359b01874714dc1672294168171`、Yocto の wic（256 MiB に伸ばした後）`c94da9d5b99bceb3ea04b2f19ef011eeec19142818debd1ff90a2d9d45623874`。

Yocto の wic は、[QEMU 起動確認](2026-11-02-yocto-qemu-boot.md) の `run7.wic`（getty を `ttyAMA1` に 1 行足した写し）に、次の 1 行を rcS の行の直後に足したものです。

```text
::sysinit:/bin/sh -c 'echo "<6>msd-compare: ready" > /dev/kmsg'
```

## 手順

```sh
# 入力をリポジトリ内の 1 か所に集める（docker/msd-dev は checkout だけを /work に載せる）
mkdir -p output/yocto-qemu/cmp
cp <Buildroot の output/images>/Image output/yocto-qemu/cmp/br-Image
cp <Buildroot の output/images>/bcm2710-rpi-cm0.dtb output/yocto-qemu/cmp/br-cm0.dtb
cp --sparse=always <Buildroot の output/images>/sdcard.img output/yocto-qemu/cmp/br-sdcard.img
cp <Yocto E の kernel8.img> output/yocto-qemu/cmp/yocto-e-Image
cp <Yocto B2 の Image> output/yocto-qemu/cmp/yocto-b2-Image
cp <上の wic> output/yocto-qemu/cmp/yocto-cmp.wic && truncate -s 256M output/yocto-qemu/cmp/yocto-cmp.wic
docker/msd-dev board/cardputerzero/tools/bench/yocto-compare/run-all.sh output/yocto-qemu/cmp output/yocto-qemu/cmp/run2 5
```

`run-compare.sh` は条件ごとにイメージを 1 回写し、`run-qemu.sh` を起動して、目印とログイン画面がシリアルに出た時点で QEMU を止めます。`summarize.py` は通常起動の中央値・最小・最大を出します。

## 計測器の検証

- A/A: C1 を icount で 2 組測りました。`t_ready` の中央値は 1.589585 s と 1.605504 s で、差は 0.015919 s（1.0 %）です。
- 一貫性: C1 と C4 はカーネルと DTB が同じで rootfs だけが違います。カーネルの段階（`t_init`）の中央値は icount で 0.897116 s と 0.888118 s で、判定の基準では差がありません。rootfs を変えても、カーネルの段階の値は変わりませんでした。
- 判定の目印は、条件ごとに決めた 1 行だけを数えます（Buildroot は `MSD/Linux ready`、Yocto は `msd-compare: ready`）。
- `wall_login_s` はホストの経過時間です。icount ではゲストの時刻とホストの時間が対応しないため、TCG の値だけを参考にします。

## 結果

生の値は [2026-11-02-buildroot-yocto-boottime.csv](2026-11-02-buildroot-yocto-boottime.csv) にあります（初回起動を含む 54 行。すべて `pass`）。下表は通常起動 5 回の中央値（最小〜最大）で、単位は秒です。

| 条件 | モード | `t_root`（root のマウント） | `t_init`（`/sbin/init` の開始） | `t_ready`（準備完了の目印） | ログインまでのホスト時間 |
|---|---|---|---|---|---|
| C1-br | icount | 0.896（0.892〜0.928） | 0.897（0.893〜0.929） | 1.590（1.586〜1.622） | 参考外 |
| C1-br-aa | icount | 0.912（0.900〜0.928） | 0.913（0.901〜0.929） | 1.606（1.593〜1.629） | 参考外 |
| C2-yocto-e | icount | 1.881（1.880〜1.918） | 1.885（1.883〜1.922） | 1.959（1.957〜1.973） | 参考外 |
| C3-yocto-b2k | icount | 0.870（0.863〜0.874） | 0.871（0.864〜0.875） | 0.916（0.908〜0.920） | 参考外 |
| C4-brk-yroot | icount | 0.887（0.884〜0.919） | 0.888（0.884〜0.919） | 0.937（0.929〜0.965） | 参考外 |
| C1-br | TCG | 7.122（6.041〜7.513） | 7.431（6.333〜7.752） | 25.955（25.360〜27.792） | 27.3（26.7〜29.2） |
| C2-yocto-e | TCG | 5.394（5.276〜6.018） | 5.677（5.512〜6.284） | 9.261（8.600〜9.789） | 12.7（12.1〜13.1） |
| C3-yocto-b2k | TCG | 6.707（5.956〜7.011） | 6.962（6.165〜7.226） | 10.834（9.488〜11.280） | 11.9（10.7〜12.5） |
| C4-brk-yroot | TCG | 6.902（6.778〜7.119） | 7.143（7.085〜7.371） | 10.897（10.773〜11.650） | 12.1（11.9〜12.9） |

初回起動（boot 0）の `t_ready` は、C1 が icount で 2.118 s（通常起動より 0.53 s 長い。/data の初回処理を含む）でした。Yocto の条件では、icount で初回と通常の差は 0.01 s 未満でした。

### 組み合わせごとの読み

| 比べた組み合わせ | 違い | icount の差（中央値） | TCG の差（中央値） | 判定 |
|---|---|---|---|---|
| C4 − C3（`t_init`、`t_ready`） | カーネルを Buildroot で作ったか Yocto で作ったか（同じソース・fragment、GCC 14.3.0 と 15.3.0、`.config` は 544 項目違う） | +0.017 s、+0.021 s | +0.181 s、+0.063 s | 差があるとは言えない（icount の基準は 0.070 s と 0.072 s、TCG の基準は 2.12 s と 3.58 s で、どちらにも届かない） |
| C1 − C4（`t_ready`） | rootfs と init の中身（Buildroot の完成イメージか、Yocto の最小イメージか） | +0.653 s | +15.06 s | 差がある（Yocto の最小イメージが短い）。ただし MSD の init スクリプト（/data、ウォッチドッグ、キーマップ、mdev、hwinfo、health）がないためで、ビルドシステムの差ではない |
| C1 − C4（`t_init`） | 同上 | +0.009 s | +0.288 s | 差があるとは言えない |
| C3 − C2（`t_init`） | カーネルの設定（MSD の fragment か meta-raspberrypi の既定か）と版（6.18.59 と 6.18.33） | −1.014 s | +1.285 s | 向きが逆なので判定しない。icount では既定の設定が命令数で大きく不利 |
| C1 − C2（`t_ready`） | イメージ全体 | −0.369 s | +16.69 s | 向きが逆なので判定しない |

### 失敗した試行

| 試行 | 内容 | 原因と対処 |
|---|---|---|
| smoke | C2 を TCG で 1 回だけ起動して計測スクリプトを確かめた | 合格（`t_ready` 9.358 s）。本番の値には含めない |
| run1 | 最初の本番。C1 の icount で `t_ready` が取れなかった | `S98msd-ready` は `msd.sweep=1` のときだけ目印を `/dev/kmsg`（時刻付き）に書き、それ以外は時刻のない console に書く。`msd.sweep=1` を全条件の引数に足し、run2 として最初からやり直した。run1 の 1 行は捨てた |

## 結論

- 同じカーネルのソースと fragment を使う限り、Yocto で作ったカーネルと Buildroot で作ったカーネルの起動時間に、QEMU で差は見えませんでした（icount と TCG の両方）。`.config` の 544 項目の差とコンパイラーの版の違いは、この測り方では起動時間に表れていません。
- イメージ全体の差（C1 と C2）は、モードによって向きが逆になり、比べる意味がありません。中身が違うためです。Yocto で完成イメージを作ったら、同じ方法で測り直します（移行計画の Y3 と §4 の受け入れ基準）。
- meta-raspberrypi の既定のカーネル設定は、icount で `t_init` が約 1 s 長くなりました。MSD の fragment を当てることが前提です。
- 確かめていないこと: 実機、Yocto の完成イメージ、`quiet` など実機の `cmdline.txt` の引数（QEMU では `run-qemu.sh` の引数で起動するため、どの条件にも入っていない）。

## 再実行の方法

上の手順で再実行できます。シリアルログ（54 ファイル）はリポジトリに入れていません。入力の SHA-256 は条件の節にあります。
