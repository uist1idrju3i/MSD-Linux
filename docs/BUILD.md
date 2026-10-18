# ビルドと起動確認

## ホスト環境

Ubuntu 26.04 を想定しています。Buildroot のホスト依存パッケージと QEMU が必要です。CI と同じ環境にする場合は、`bc`、`bison`、`build-essential`、`cpio`、`device-tree-compiler`、`file`、`flex`、`git`、`libelf-dev`、`libncurses-dev`、`libssl-dev`、`perl`、`python3`、`qemu-system-arm`、`rsync`、`unzip`、`wget`、`xz-utils` を用意してください。

## イメージのビルド

リポジトリのルートで、Buildroot の defconfig を適用してビルドします。

```sh
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig
make -C output
```

CI は Buildroot のダウンロードファイルと ccache をキャッシュし、`main` への push で共有キャッシュを更新します。文書だけを変更した pull request では、Buildroot のビルドを省略します。

成果物は `output/images/sdcard.img` と更新用の `output/images/msd-update-bundle.tar` です。構成は MBR と拡張パーティションを使い、p1 に起動選択用 FAT、p2/p3 に同一内容の FAT ブート領域、p5/p6 に同一内容の SquashFS rootfs、p7 に ext4 の `/data` を置きます。p5/p6 は各 256 MiB、p7 は 64 MiB です。p7 の初回起動時拡張は未実装です。共通ブート領域の `config.txt` は選択されたブートパーティションに応じて A/B の cmdline を選びます。

各ブート領域には `kernel8.img` を配置します。元データは未圧縮の `Image` です。post-image スクリプトは `pigz -11 -n` で圧縮し、展開結果と元データの一致を確認します。比較用の `gzip -9n` と `pigz -11` のサイズはビルドログに記録する仕様です。QEMU 用の未圧縮 `Image` は `output/images/` に残ります。更新 bundle は `rootfs.squashfs`、共通の `boot.vfat`、SHA-256 の `manifest` を含み、どちらのスロットにも利用可能な構成です。

## QEMU での起動確認

```sh
board/cardputerzero/qemu/test-boot.sh
board/cardputerzero/qemu/test-ab.sh
```

`test-boot.sh` は A スロット（p5）、`test-ab.sh` は B スロット（p6）を rootfs として起動し、`MSD/Linux ready` marker と login prompt を検出した時点で QEMU を停止します。`QEMU_BOOT_TIMEOUT` は検出を待つ上限時間です。両スクリプトはイメージをコピーし、サイズを次の 2 の累乗にそろえます。対話的な起動には `board/cardputerzero/qemu/run-qemu.sh` を使ってください。

## カーネル設定の範囲

`board/cardputerzero/linux.fragment` では、使わないメディア機能、Broadcom 以外の Wi-Fi ベンダー、XFS・Btrfs・OCFS2・GFS2・NILFS2・JFS・SMB クライアント・9P、CAN・アマチュア無線・ATM・IEEE 802.15.4・NFC・InfiniBand を無効にします。USB Wi-Fi ドングル、USB カメラ、TV チューナーは使えません。netfilter、md/dm、USB serial、HID/入力、サウンド、staging/fbtft は残します。

QEMU では A/B の起動を確認しますが、このカーネル設定を実機で再確認する作業は未完了です。

QEMU の `raspi3b` マシンは BCM2837 をエミュレートしますが、Raspberry Pi の GPU ファームウェアを実行しません。そのため `autoboot.txt` と firmware の `tryboot` による切替・自動フォールバックは確認できません。CardputerZero の LCD、内蔵キーボード、M5Stack の I2C デバイスも再現しません。実機での表示、入力、電源断耐性、watchdog、firmware レベルの A/B 更新は実機で別途検証する必要があります。

## 現在の検証状況

この構成に対するフルビルド、QEMU 起動、実機起動はまだ確認していません。更新処理のシェルロジックは `tests/msd-update/run.sh` でホスト上の一時ディレクトリを使って確認できます。
