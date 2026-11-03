# init・device管理・遅延起動の資料と履歴

[ユーザー空間の案内へ戻る](README.md) / [現在のinit比較](../alternatives/init.md)

以下は初期の選定案、上流の機能、当時の未確認事項と既存試験の記録です。現行はBusyBox initとmdevであり、systemd unitやudev ruleを置くだけで同じ処理が動く構成ではありません。固定deviceパス、moduleのロード、権限と起動順を個別に検証する必要があります。

63 appletのQEMU試験は、その実験の構成とbinaryを確認したものです。製品の保守・対話用コマンドを含む最終範囲や、全周辺機能の実機動作を保証しません。後半の要約と統合した範囲は[原文記録](original-summaries.csv)を参照します。

## 16. ユーザー空間の除去・遅延起動・init 選択

### 16.1 BusyBox 最小化と実使用の洗い出し
| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| 静的リンク BusyBox | FAQ に「静的ビルドは `LDFLAGS=--static`」と記載。静的リンクのコスト/利点(共有ライブラリ読込の省略)は FAQ の「relocatable code, PIC, and static linking」節にある | https://busybox.net/FAQ.html | 一次 |
| 最小アプレット選定 | `make menuconfig` でアプレット単位に選択できる（BusyBox の標準手順）。QEMU の静的・動的調査で試験用の 63 applet の集合を作成し、起動と link を確認した。保守・対話用を含む製品用の範囲は未決である（[実験記録](../../experiments/2026-10-21-qemu-busybox.md)）。実使用を洗い出すには、`strace -f -e trace=execve,openat` などで記録し、使われたコマンドだけを残す方法が考えられる（手順案・推測）。 | https://busybox.net/FAQ.html<br>https://man7.org/linux/man-pages/man1/strace.1.html | 一次（ツール） / 推測（手順） |
| 依存確認 | `ldd` はターゲット実行になる場合があるため、クロス環境では `readelf -d`（NEEDED）で確認する方が安全との情報があります。根拠となる一次資料は未確認です。 | — | 推測 |
| fork 削減 | シェルスクリプトの外部コマンド呼び出し(fork+exec)を減らす、BusyBox の `NOFORK/NOEXEC`(ash の組込み実行)機能など。**BusyBox の該当設定の一次確認は未実施** | — | 未確認 |

### 16.2 init の選択:全機能維持(LCD/キーボード/音声/IMU/RTC/電池/Wi-Fi/Ethernet/IR/カメラ)で何が使えるか

事実(一次)と見立て(推測)を分けます。

| 論点 | 事実(出典) | 判断への含意(見立て=推測) |
|---|---|---|
| M5 の LCD / キーボード設定は **udev 前提** | M5 の公開 udev ルールは `ENV{ID_PATH}`（udev の path_id）でデバイスを特定し、`/dev/dri/cardputer-zero-internal`、`/dev/fb_lcd`、`/dev/input/cardputer-zero-internal` の symlink と seat タグを作ります。LED ルールは `RUN+="/bin/chgrp gpio ..."` を使います。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/99-cardputer-zero-lcd.rules<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/60-cardputerzero-leds.rules | BusyBox mdev が ID_PATH を同じ形式で提供するかは未確認です。udev 形式のルールをそのまま使えるかも未確認です。BusyBox init / 自作 init を選ぶ場合、(a) eudev / systemd-udevd を単体で入れる、(b) 固定パス（例：`/dev/input/event0`）を前提にアプリを書く、のいずれかが案です（推測）。 |
| M5 の fb 表示サービスが **systemd unit** | `fb_load.service` は `After=systemd-udev-trigger.service systemd-udevd.service systemd-modules-load.service`、`WantedBy=sysinit.target` を指定します。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/fb_load.service | systemd 以外では同等のスクリプト化が必要です。スプラッシュを使わない要件では、fb_load 自体が不要となる可能性があります（推測）。 |
| LCD パネルの設定は **ファームウェア .bin** | `panel-mipi-dbi.c` は `<compatible>.bin` を `request_firmware` で取得します。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/gpu/drm/tiny/panel-mipi-dbi.c#L220-L232 | rootfs が見える前に probe すると失敗または待機する可能性があります。built-in 化する場合は firmware のビルド埋め込み（`EXTRA_FIRMWARE`）か initramfs が必要です（構成が増えるため推測）。 |
| モジュールの自動ロード | M5 のモジュールソースには `MODULE_DEVICE_TABLE(of/i2c)` があり、modalias による自動ロードに利用できます。自動ロードには udev / `mdev -s` / `modprobe` 呼び出しが必要です。https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules | systemd なら systemd-udevd + modules-load、BusyBox なら `modprobe` を明示列挙する自作スクリプトが案です（推測）。 |
| IMU / カメラ / 音声の上位ソフト | IMU は IIO、音声は ALSA（ASoC）、カメラは media / libcamera、IR は rc-core です。udev / systemd が必須との記述は未確認で、`libcamera` など上位ソフトも未調査です。https://docs.kernel.org/driver-api/iio/index.html<br>https://www.alsa-project.org/wiki/ASoC<br>https://docs.kernel.org/userspace-api/media/index.html<br>https://libcamera.org/docs.html<br>https://docs.kernel.org/driver-api/rc-core.html | 全機能維持には「ドライバが動く」ことと「上位ライブラリが動く」ことの 2 段階が必要です。後者は未調査です。 |
| Wi-Fi / Ethernet | `wpa_supplicant` / `dhcpcd` / `udhcpc` などを使う案があります。BusyBox の `udhcpc` の有無は未確認です。https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wpa_supplicant/Config.in<br>https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dhcpcd/Config.in<br>https://busybox.net/downloads/BusyBox.html | systemd-networkd なしでも構成可能と考えられます（推測）。 |
| 電池 / 電源 | BQ27220 は power_supply sysfs を使います。電源断処理は `handle_sysrq('u')` の後、バックライト輝度を 0 にし、disabled GPIO をアサートします。SysRq `i` / `s` と `kernel_power_off()` はコメントアウトされています。https://docs.kernel.org/power/power_supply_class.html<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/power/supply/bq27xxx_battery.c<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L472-L510 | userspace daemon が必須かは未確認です。 |

**init 3 方式の比較（推測。起動時間はすべて未測定）**

| 観点 | systemd(最小化) | BusyBox init(+mdev または eudev) | 自作 init(静的 PID 1) |
|---|---|---|---|
| M5 の udev/unit 前提との整合 | **高**(そのまま流用可) | 中(udev ルール移植 or eudev 併用) | 低(全て自作) |
| 全機能維持の実装コスト | 低 | 中 | 高 |
| 並列起動 | 標準(依存解析・socket activation・timer) | `::once`/バックグラウンド `&`で手動 | 完全に自由(fork 後 wait しない等) |
| 静的リンク・小ささ | 小さくはない(バイナリ+依存多) | 小さい | 最小 |
| 失敗時の挙動 | 診断が強い(journal, analyze) | 弱い | 自前 |
| 終点(プロンプト+キー)までの最短化余地 | 中(unit を削り、`systemd-analyze critical-chain` で詰める) | 高 | 最高(ただし作り込み) |

- systemd の起動可視化・並列化・活性化機能:`systemd-analyze blame/critical-chain/plot`(https://man7.org/linux/man-pages/man1/systemd-analyze.1.html)、socket activation(https://man7.org/linux/man-pages/man5/systemd.socket.5.html)、`sd_notify`(https://man7.org/linux/man-pages/man3/sd_notify.3.html)、`Type=` 等(https://man7.org/linux/man-pages/man5/systemd.service.5.html)。【一次】
- 【推測・初期案】初期ユーザー空間は BusyBox init + mdev + glibc とし、M5 の udev ルールを mdev 向けに移植できるか試します。M5 のルールは少数のため移植候補になりますが、mdev が `ID_PATH` を同じ形式で提供するかは未確認です。必要な機能を再現できない場合は systemd 最小化または eudev との比較に戻り、musl は必要に応じて比較します。systemd の起動オーバーヘッドは A53 / RAM 512 MB で数百 ms〜1 秒という推測がありますが、実測値はありません。

### 16.3 systemd の起動短縮手段(一次の範囲)
- critical-chain で終点ユニットに至る最長経路を可視化し、そこにないものは `WantedBy` を変えて後段化できる(systemd-analyze man)。【一次】
- socket activation：`.socket` ユニットで待受を先に作り、サービス本体を初回接続時に起動します（Dropbear / OpenSSH サーバーやネットワーク系サービスの遅延に使えます）。https://man7.org/linux/man-pages/man5/systemd.socket.5.html 【一次（機能） / CM0 での効果は推測】
- timer で終点後に重い処理を遅延できます（`OnBootSec=`）。本文は未確認です。https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html 【未確認】
- `systemd-analyze blame` の値は並列起動のため起動時間への寄与と一致しません。また `Type=simple` のサービスは即時起動扱いで blame に表示されず、キュー待ち時間も含まれません。【一次】https://man7.org/linux/man-pages/man1/systemd-analyze.1.html
