# ビルドと起動確認

## ホスト環境

Ubuntu 24.04 を想定しています。Buildroot のホスト依存パッケージと、QEMU の `qemu-system-aarch64` が必要です。CI では必要なパッケージをインストールしてからビルドします。

## イメージのビルド

リポジトリのルートで、Buildroot の defconfig を適用してビルドします。

```sh
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig
make -C output
```

成果物は `output/images/sdcard.img` です。構成は MBR と拡張パーティションを使い、p1 に起動選択用 FAT、p2/p3 に A/B の FAT ブート領域、p5/p6 に同一内容の SquashFS rootfs、p7 に ext4 の `/data` を置きます。p5/p6 は各 256 MiB、p7 は 64 MiB です。p7 の初回起動時拡張は未実装です。

各ブート領域には `kernel8.img` を配置します。元データは未圧縮の `Image` です。post-image スクリプトが `gzip -9n` で圧縮し、展開結果と元データの一致を確認します。QEMU 用の未圧縮 `Image` も `output/images/` に残ります。

## QEMU での起動確認

```sh
board/cardputerzero/qemu/test-boot.sh
```

`test-boot.sh` は A スロット（p5）、`test-ab.sh` は B スロット（p6）を rootfs として起動し、`MSD-Linux ready` marker を確認します。両スクリプトはイメージをコピーし、サイズを次の 2 の累乗にそろえます。対話的な起動には `board/cardputerzero/qemu/run-qemu.sh` を使ってください。

QEMU の `raspi3b` マシンは BCM2837 をエミュレートしますが、Raspberry Pi の GPU ファームウェアを実行しません。そのため `autoboot.txt` と firmware の `tryboot` による切替・自動フォールバックは確認できません。CardputerZero の LCD、内蔵キーボード、M5Stack の I2C デバイスも再現しません。実機での表示、入力、電源断耐性、watchdog、firmware レベルの A/B 更新は実機で別途検証する必要があります。

## 現在の検証状況

この構成に対するフルビルド、QEMU 起動、実機起動はまだ確認していません。更新処理のシェルロジックは `tests/msd-update/run.sh` でホスト上の一時ディレクトリを使って確認できます。
