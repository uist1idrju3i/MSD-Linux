# ビルドと起動確認

## 共通の開発環境

ローカル開発とCI/CDは、プロジェクトが構築・配布する開発用Docker imageを共用します。OS標準のcompilerやQEMUの版に依存しないよう、構築・テストに必要な版とパッチをimageの入力として固定します。ホストへ個別にビルド依存を導入する手順ではなく、`docker/msd-dev`を標準の実行経路にします。

## ホスト側の準備

Git、DockerとBashを利用できるホストで、submoduleを含むリポジトリを取得してください。製品buildは現行Bootlin toolchainの制約によりx86_64 LinuxのDocker実行環境が必要です。arm64向けの開発imageはlint・host回帰・QEMUに使えますが、製品buildには使えません。macOSやWindowsからの製品構築は本リポジトリでは試していません。
rootless Docker では実行モードを自動で判定するため、sudo なしで利用可能です。詳しくは[開発用コンテナーの説明](../docker/README.md)を参照してください。

```sh
docker/msd-dev ensure
docker/msd-dev bash
```

イメージの選定理由、GHCRからの取得・attestation検証、未公開時のローカルbuildは[開発用コンテナーの説明](../docker/README.md)を参照してください。以下のコマンドもリポジトリのルートで実行します。

コミット前に CI と同じ文字・リンク検査をローカルで回すフックを用意しています。任意ですが、PR 到達後の往復を減らせます。

```sh
git config core.hooksPath .githooks
```

staged なファイルに JIS X 0213 の検査と、リポジトリ全体のリンク検査を実行します（`MSD_SKIP_LINKCHECK=1` でリンク検査を省略可）。`docs/` と `.agents/` の Markdown は yomiyasu の推敲候補も警告として出します。

## イメージのビルド

リポジトリのルートで、Buildroot の defconfig を適用してビルドします。

```sh
docker/msd-dev ensure
docker/msd-dev bash -lc 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
```

Buildrootがtarget用のBootlin toolchainを取得し、コンテナー内で製品を構築します。CIもこの経路を使い、ホスト側のcompilerへ置き換えません。Buildrootのダウンロードとccacheは対応する世代の入力でのみ再利用します。

PRは累積差分、`main`へのpushは対象差分から製品buildの要否を判定します。文書だけなら省略し、製品入力・未知のpath・判定失敗ではbuildします。週次・手動は常にbuildします。正確な除外範囲とcacheの扱いは[CIの説明](CI.md)を参照してください。

成果物は `output/images/sdcard.img` と更新用の `output/images/msd-update-bundle.tar` です。構成は MBR と拡張パーティションを使い、p1 に起動選択用 FAT、p2/p3 に同一内容の FAT ブート領域、p5/p6 に同一内容の SquashFS rootfs、p7 に ext4 の `/data` を置きます。p5/p6 は各 256 MiB、p7 は初期 64 MiB で、初回起動時にパーティション末尾まで拡張し、ext4 をオンライン拡張する実装です。`msd-data-grow` は `/sys/class/block/mmcblk0/size` からディスク容量を読み取るため、fstab で `/sys` を sysfs としてマウントします。容量を読み取れない場合は明示的に失敗します。`/var/run`、`/var/lock`、`/var/log` などの書き込み先は `/run` または `/tmp` への symlink なので、`/var` 自体には tmpfs を重ねません。A/B 両スロットには同じ `boot.vfat` を配置します。`config.txt` の `[boot_partition=2]` / `[boot_partition=3]` 条件が、それぞれ `cmdline_rootfs_a.txt` / `cmdline_rootfs_b.txt` を選ぶ構成です。CM0 実機での partition selector、tryboot、p7 拡張は未確認です。

各ブート領域には `kernel8.img` を配置します。元データは未圧縮の `Image` です。post-image スクリプトは `pigz -11 -n` で圧縮し、展開結果と元データの一致を確認します。比較用の `gzip -9n` と `pigz -11` のサイズはビルドログに記録する仕様です。QEMU 用の未圧縮 `Image` は `output/images/` に残ります。更新 bundle は `rootfs.squashfs`、共通の `boot.vfat`、SHA-256 の `manifest`、Ed25519 署名 `manifest.sig` の4ファイルです。端末は書き込み前に `/usr/share/msd-update/update-key.pem` で署名を検証します。最低更新番号は `/usr/share/msd-update/version`、鍵の由来は `/usr/share/msd-update/key-origin` に記録します。これらは `/etc` overlay の対象外です。target には検証用の `openssl` コマンドも含めます。`MSD_UPDATE_SIGNING_KEY=/path/to/private.pem` を指定するとリリース鍵を使います。未指定時は `$BASE_DIR/msd-update-dev-key.pem` を生成・再利用し、開発用鍵である旨を警告します。秘密鍵は成果物に含めず、開発用鍵をリリースに使わないでください。ビルド成果物の署名は実機未検証です。

`BR2_PACKAGE_KBD` の keymap/font データは post-build で削除し、TCA8418 用 map だけを残します。map 自体は 1,593 bytes です。展開後の `loadkeys` 実行ファイルと必要ライブラリのサイズは rootfs をビルドして測る必要があります。`S04msd-keymap` が `loadkeys -C /dev/tty0 -q` で読み込み、mdev helper が入力デバイスの symlink を作成・削除します。`S05seedrng` は `S02msd-data` と `S03msd-etc-overlay` の後に起動し、`SEEDRNG_ARGS=--seed-dir=/data/seedrng` で乱数シードを永続領域に保存します。実機では `/var/lib` が読み取り専用 rootfs 上にあるため、seedrng の保存先を `/data` にしています。keymap の読み込みと symlink は実機未検証です。

`BR2_PACKAGE_LIBV4L_UTILS` は meson の単一トグルで全 utility を target に入れるため、post-build で `v4l2-ctl`、`media-ctl`、`ir-keytable`、`ir-ctl` の 4 本だけを残し、CEC・RDS・TV tuner・compliance 系のツールと RC keymap・udev rule を削除します。削除する対象は `post-build.sh` に列挙しています。実機でのカメラ確認手順は [VERIFY.md](VERIFY.md) を参照してください。

`/usr/sbin/msd-hwinfo` は Standard/Lite を判定し、起動時に `/run/msd/hardware` へ結果を書き、シリアルコンソールにも判定結果を出力します。この判定は実機未検証です。

## QEMU での起動確認

```sh
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
docker/msd-dev board/cardputerzero/qemu/test-ab.sh
```

`test-boot.sh` は A スロット（p5）、`test-ab.sh` は B スロット（p6）を rootfs として起動し、`MSD/Linux ready` marker と login prompt を検出した時点で QEMU を停止します。`QEMU_BOOT_TIMEOUT` は検出を待つ上限時間です。両スクリプトはイメージをコピーし、サイズを次の 2 の累乗にそろえます。対話的な起動には `board/cardputerzero/qemu/run-qemu.sh` を使ってください。

既定では `raspi3ap`（512 MiB）と `bcm2710-rpi-cm0.dtb` を使います。1 GiB の `raspi3b` と `bcm2710-rpi-3-b.dtb` に切り替えるには、`QEMU_MACHINE=raspi3b` を設定します。`raspi3ap` の起動には、ASB パッチを含む開発用イメージ内の QEMU が必要です。

## カーネル設定の範囲

`board/cardputerzero/linux.fragment` では、CardputerZero の基板と有効なオーバーレイで使わないサウンドカード／コーデック、RTC・hwmon、FB_TFT／DRM パネル、赤外線・入力、USB misc の周辺機器、Ethernet・Bluetooth ドングル、旧式 USB gadget、Pi 4/5・HAT 向けドライバーを無効にします。LCD（ST7789V）、TCA8418 キーボード、IIO センサー、電源・GPIO、DS1307 ドライバー経由の Epson RX8130 RTC、BCM 系 Wi-Fi/Bluetooth、必要な ASoC 機能など、製品の構成に使う機能は残します。CardputerZero は HDMI audio、camera、MMAL を使わず、SPI 接続 LCD と I2S codec を使うため BCM2835 VCHIQ とその依存機能を無効にします。QEMU の mailbox は VCHIQ を実装しません。

netfilter、md/dm、暗号・スケジューリング、USB serial/NIC、USB_CONFIGFS、HID、NLS、ATA、joystick、IIO は今回の削減対象に含めません。

QEMU では A/B の起動を確認しますが、このカーネル設定を実機で再確認する作業は未完了です。

QEMU の `raspi3ap` と `raspi3b` は BCM2837 をエミュレートしますが、Raspberry Pi の GPU ファームウェアを実行しません。そのため `autoboot.txt` と firmware の `tryboot` による切替・自動フォールバックは確認できません。CardputerZero の LCD、内蔵キーボード、M5Stack の I2C デバイスも再現しません。実機での表示、入力、電源断耐性、watchdog、firmware レベルの A/B 更新は実機で別途検証する必要があります。QEMU の起動テストでは PL011 コンソールに `ttyAMA1` を使い、`initcall_blacklist=bcm2835_wdt_driver_init` で BCM2835 watchdog ドライバーを無効にするため、watchdog の動作は実機でのみ確認します。

## 現在の検証状況

CI では開発用イメージ内で Buildroot のフルビルド、QEMU の A/B 起動（p5/p6 とも成功）、テストを実行します。ローカル QEMU では、拡大イメージで p7 の ext4 拡張と `/data/seedrng/seed.credit` の作成を確認しました。実機起動、LCD・キーボード、tryboot、watchdog、更新署名は未検証です。

## 最終カーネル設定の監査

カーネル・Buildroot・ツールチェーンを更新したら、fragment で要求した行だけでなく最終 `.config` 全体を比較します。同じ defconfig と fragment でも、Yocto 比較では [544 項目の差](experiments/2026-11-02-buildroot-yocto-kconfig-diff.csv)がありました。`CONFIG_THERMAL` も fragment 外で変わりました。差の原因を説明できないまま機能が同等だとは判断しません。

ビルドは git worktree ではなく単独の clone と固定の `docker/msd-dev` を使います。submodule の `.git` が外側を指す worktree はコンテナから見えず、[過去の BR1](experiments/2026-11-02-buildroot-yocto-artifacts.md#失敗した試行)で停止しました。

1. 更新前の commit、submodule SHA、defconfig、fragment、Buildroot の `.config`、`output/build/linux-custom/.config`、入力・成果物の hash を新しい証拠ディレクトリへ保存する。
2. 更新後は別の clean 出力を構築し、同じ一式を保存する。ccache、取得物、出力ツリーの cold/warm を記録する。
3. Linux ソースの `scripts/diffconfig` で、保存した前後の最終 `.config` を比較する。`CONFIG_X=value` と `# CONFIG_X is not set` を区別し、未掲載と明示的な `n` の差も確認する。

   ```sh
   python3 output/build/linux-custom/scripts/diffconfig before.config after.config
   board/cardputerzero/tools/check-kernel-fragment.sh \
     board/cardputerzero/linux.fragment output/build/linux-custom/.config
   ```

4. 変更した項目だけでなく連動した差を調べる。特に thermal、watchdog、I2C/SPI、LCD/fbcon、入力、rootfs、暗号・署名、ハードニングをハードウェア対応表と照合する。
5. モジュール依存、QEMU の A/B、ホストテストを実行し、実機でしか確認できない項目は未確認として残す。fragment の一致だけで全体の同等性や実機動作を主張しない。

比較 runner とライセンス監査の扱いは [Buildroot への還元](research/yocto-migration/buildroot-lessons.md)を参照してください。

## カーネル候補のローカル測定

`board/cardputerzero/tools/kernel-variant-sweep.sh` は、Linux のビルドが済んだ Buildroot output ディレクトリから実行します。総当たりビルドと QEMU 比較はローカル専用で、CI では実行しません。

```sh
REPO=<リポジトリのルート>
OUTPUT_DIR=<Buildroot の O= ディレクトリ>
cd "$OUTPUT_DIR"
"$REPO/board/cardputerzero/tools/kernel-variant-sweep.sh" \
  --candidates "$REPO/board/cardputerzero/tools/kernel-candidates.txt"
```

`--no-qemu` はビルドとサイズだけを測定し、`--only SYMBOL` は候補を一つに絞ります（`--jobs` と併用不可）。`--jobs N` は N 本のワーカーを並列に走らせます。各ワーカーは `linux-custom` を複製した独立ツリー（reflink 優先、なければ完全コピーで 1 本あたり数 GB）で動き、候補は行番号で分け、出力 CSV は `SWEEP_CSV.wN` に分けてから自動で結合します。QEMU 試験もワーカーごとに独立して走ります（QMP ソケット未指定・sdcard は起動ごとに複製）。CPU・メモリ・ディスクが余るなら `--jobs 2` から試してください。

出力 CSV は `symbol,value,category,status,image_bytes,gz_bytes,delta_gz,collateral,qemu_ready_vtime,initcalls` の列を持ちます。`collateral` は基準 `.config` から連動して変わった記号、`delta_gz` は基準との差です。`gz_bytes` は `pigz -11` があればその値、なければ `gzip -9` で測ります。QEMU の仮想時間は同一環境内の相対比較に限り、実機の起動時間を表しません。

QEMU 比較では `initcall_debug` と `printk.time=1` を付け、スイープ専用の `msd.sweep=1` で ready marker を printk 経由にして仮想時刻を記録します。通常起動では既存の console marker を維持します。`qemu_ready_vtime` が `~` で始まる場合は、旧 artifact の時刻なし ready marker より前に最後に出た kernel timestamp です。

Devin VM では Buildroot の recipe shell が `BASH_ENV` の影響を受けるため、初回設定とビルドは `env -u BASH_ENV make ...` で実行してください。スイープスクリプトもカーネルの `make` を呼ぶ前に `BASH_ENV` を解除します。
