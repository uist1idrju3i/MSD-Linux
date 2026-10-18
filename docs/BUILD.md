# ビルドと起動確認

## ホスト環境

Ubuntu 24.04 を想定しています。Buildroot のホスト依存パッケージと、QEMU の `qemu-system-aarch64` が必要です。CI では必要なパッケージをインストールしてからビルドします。

## イメージのビルド

リポジトリのルートで、Buildroot の defconfig を適用してビルドします。

```sh
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig
make -C output
```

成果物は `output/images/sdcard.img` です。現在は ext4 rootfs を使っています。読み取り専用 SquashFS と A/B 更新への切り替えは後続作業で行います。

## QEMU での起動確認

```sh
board/cardputerzero/qemu/test-boot.sh
```

スクリプトはイメージのコピーを次の 2 の累乗サイズに拡張し、QEMU の起動後に `MSD-Linux ready` とログインプロンプトを確認します。対話的に起動する場合は `board/cardputerzero/qemu/run-qemu.sh` を使います。

QEMU の `raspi3b` マシンは BCM2837 をエミュレートしますが、GPU ファームウェア、CardputerZero の LCD、内蔵キーボード、M5Stack の I2C デバイスは再現しません。実機での表示、入力、電源断耐性、起動時間は実機で別途検証する必要があります。

## 現在の検証状況

Buildroot の設定とボード構成を追加した段階です。フルビルド、QEMU 起動、実機起動はまだ確認していません。
