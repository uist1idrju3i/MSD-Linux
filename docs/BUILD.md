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

成果物は `output/images/sdcard.img` と更新用の `output/images/msd-update-bundle.tar` です。構成は MBR と拡張パーティションを使い、p1 に起動選択用 FAT、p2/p3 に同一内容の FAT ブート領域、p5/p6 に同一内容の SquashFS rootfs、p7 に ext4 の `/data` を置きます。p5/p6 は各 256 MiB、p7 は初期 64 MiB で、初回起動時にパーティション末尾まで拡張し、ext4 をオンライン拡張する実装です。A/B 両スロットには同じ `boot.vfat` を配置します。`config.txt` の `[boot_partition=2]` / `[boot_partition=3]` 条件が、それぞれ `cmdline_rootfs_a.txt` / `cmdline_rootfs_b.txt` を選ぶ構成です。CM0 実機での partition selector、tryboot、p7 拡張は未確認です。

各ブート領域には `kernel8.img` を配置します。元データは未圧縮の `Image` です。post-image スクリプトは `pigz -11 -n` で圧縮し、展開結果と元データの一致を確認します。比較用の `gzip -9n` と `pigz -11` のサイズはビルドログに記録する仕様です。QEMU 用の未圧縮 `Image` は `output/images/` に残ります。更新 bundle は `rootfs.squashfs`、共通の `boot.vfat`、SHA-256 の `manifest` を含み、どちらのスロットにも利用可能な構成です。SHA-256 は整合性確認用で、bundle の署名、鍵保管、secure boot は未実装です。

`BR2_PACKAGE_KBD` の keymap/font データは post-build で削除し、TCA8418 用 map だけを残します。map 自体は 1,593 bytes です。展開後の `loadkeys` 実行ファイルと必要ライブラリのサイズは rootfs をビルドして測る必要があります。`S04msd-keymap` が `loadkeys -C /dev/tty0 -q` で読み込み、mdev helper が入力デバイスの symlink を作成・削除します。keymap の読み込みと symlink は実機未検証です。

`/usr/sbin/msd-hwinfo` は Standard/Lite を判定し、起動時に `/run/msd/hardware` へ結果を書きます。この判定は実機未検証です。

## QEMU での起動確認

```sh
board/cardputerzero/qemu/test-boot.sh
board/cardputerzero/qemu/test-ab.sh
```

`test-boot.sh` は A スロット（p5）、`test-ab.sh` は B スロット（p6）を rootfs として起動し、`MSD/Linux ready` marker と login prompt を検出した時点で QEMU を停止します。`QEMU_BOOT_TIMEOUT` は検出を待つ上限時間です。両スクリプトはイメージをコピーし、サイズを次の 2 の累乗にそろえます。対話的な起動には `board/cardputerzero/qemu/run-qemu.sh` を使ってください。

## カーネル設定の範囲

`board/cardputerzero/linux.fragment` では、CardputerZero の基板と有効なオーバーレイで使わないサウンドカード／コーデック、RTC・hwmon、FB_TFT／DRM パネル、赤外線・入力、USB misc の周辺機器、Ethernet・Bluetooth ドングル、旧式 USB gadget、Pi 4/5・HAT 向けドライバーを無効にします。LCD（ST7789V）、TCA8418 キーボード、IIO センサー、電源・GPIO、DS1307 ドライバー経由の Epson RX8130 RTC、BCM 系 Wi-Fi/Bluetooth、必要な ASoC 機能など、製品の構成に使う機能は残します。

netfilter、md/dm、暗号・スケジューリング、USB serial/NIC、USB_CONFIGFS、HID、NLS、ATA、joystick、IIO は今回の削減対象に含めません。

QEMU では A/B の起動を確認しますが、このカーネル設定を実機で再確認する作業は未完了です。

QEMU の `raspi3b` マシンは BCM2837 をエミュレートしますが、Raspberry Pi の GPU ファームウェアを実行しません。そのため `autoboot.txt` と firmware の `tryboot` による切替・自動フォールバックは確認できません。CardputerZero の LCD、内蔵キーボード、M5Stack の I2C デバイスも再現しません。実機での表示、入力、電源断耐性、watchdog、firmware レベルの A/B 更新は実機で別途検証する必要があります。QEMU の起動テストでは PL011 コンソールに `ttyAMA1` を使い、`initcall_blacklist=bcm2835_wdt_driver_init` で BCM2835 watchdog ドライバーを無効にするため、watchdog の動作は実機でのみ確認します。

## 現在の検証状況

この構成に対するフルビルド、QEMU 起動、実機起動はまだ確認していません。更新処理のシェルロジックは `tests/msd-update/run.sh` でホスト上の一時ディレクトリを使って確認できます。
