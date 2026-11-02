# 起動シーケンスと高速起動の根拠

[起動・カーネルの入口](boot-and-kernel.md) / [調査の索引](../../RESEARCH.md)

以下は公開資料の調査記録です。測定条件と未確認の記述を含め、元の節を保持しています。現在の実装は [BUILD.md](../BUILD.md) で確認してください。

## 5. 超高速起動の調査

### 5.1 起動シーケンスと M5 BENCHMARK.md
【未確認】起動順は boot ROM → bootcode.bin → start.elf（VideoCore GPU ファームウェア）→ kernel8.img とされます。Raspberry Pi の公開起動資料を確認先とします。GPU 段を公式に省く手段、armstub・TF-A・U-Boot・Circle の実行順、rpi-open-firmware と lk-overlay の対応 SoC は未確認です。確認先: https://www.raspberrypi.com/documentation/computers/configuration.html#boot-folder-contents<br>https://github.com/search?q=rpi-open-firmware&type=repositories<br>https://github.com/search?q=lk-overlay&type=repositories

【一次・自己申告】CardputerZero の `circle-boot-splash` BENCHMARK.md は、独自の 227 KB ベアメタルカーネルを読む構成について次の値を掲載します。リポジトリは archived です。
- GPU ファームウェア（`bootcode.bin` + `start_cd.elf`）: **2112 ms**
- 画面点灯: **2.26 s**。「Linux 可用」: **約 7〜9 s**（実測と概算の合算で、終点の定義なし）
- `boot_delay=0`、`gpu_mem=16`、`start_cd.elf`、`force_eeprom_read=0`、`initial_turbo=60` などの `config.txt` 最適化を行っても、ARM 開始は 2112 ms で不変
- gzip 圧縮 9.2 MB カーネルの 2 回目の読込に 2.1 s、Linux からユーザー空間まで 3〜5 s、合計は約 7〜9 s

【推測・未測定】GPU ファームウェア段の 2112 ms は短縮困難な下限として扱います。カーネル読込・展開、初期化、ユーザー空間を合わせて 1〜2 秒に収められれば、電源投入からユーザー空間までの総時間は 3.5〜4.5 秒を目標にできます。実機での測定値ではありません。

出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21<br>https://api.github.com/repos/CardputerZero/circle-boot-splash

【推測】2112 ms は小型カーネルを読んだ場合の GPU 段で、通常の大きなカーネルと initramfs を読む構成の下限とは別です。GPU 段の時間がカーネルサイズに比例するかは未確認です。RP-010196-WP-1 の Pi 3B+ ログでは、kernel8.img が 10,156,403 B で `Loaded` 4.131 s、`Device tree loaded` 6.760 s（差 2.63 s）です。この区間の内訳は未確認です。KittenLabs の Zero 2 W は 9,276,375 B で約 1.54 s とします。サイズ比は 1.09、時間比は約 1.7 ですが、機材とログ区間が異なるため比例関係は示せません。同一 SD・同一構成でカーネルサイズを変え、実機で測る必要があります。

出典: https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/

【一次】CardputerZero org に U-Boot リポジトリがあります（2026-06-11）。https://github.com/CardputerZero/u-boot

### 5.2 数値と計測条件（異なる SoC・条件の値は合成できません）

| 数値 | 対象/版 | 条件・終点 | 確認度 | 出典URL |
|---|---|---|---|---|
| 電源→ARM 開始 2112 ms、画面点灯 2.26 s | CM0（M5 の自己申告） | 小型ベアメタルカーネル 227 KB、`start_cd.elf` | 一次・自己申告 | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| 「Linux 可用」約 7〜9 s | CM0（M5 の自己申告） | 実測と概算の合算、終点定義なし | 一次・自己申告。値の信頼性は低い | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| ARM 開始時刻 06.79s | Pi 3B+（BCM2710 系）、RP-010196-WP-1（Release 1、2026-06-01）付録のログ | 既定ファーム + initramfs 11.7 MB（0xb2483c = 11,683,900 B）+ kernel8.img 10.2 MB（`Loaded 'kernel8.img' to 0x200000 size 0x9af973` = 10,156,403 B、9.69 MiB）、標準ログ | 一次（PDF 付録のログ） | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf |
| 約 7 s | CM5、RP-010196-WP（2026-07-16 版との情報） | Pi OS 既定、主に Pi 4/5 対象、zstd 推奨。EROFS 16K が 3 倍超との値は CM5 + 6.18 | 未確認。CM5 の 7 s 値と文書版を確認する必要がある。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf |
| 5.38 s → 4.75 s → 4.47 s | Pi Zero 2 W + HQ カメラ（IMX477）、Raspbian ベース（KittenLabs、2024-09-01） | 5.38 → 4.75 s はカメラ/ディスプレイの自動検出を無効化、4.75 → 4.47 s は initramfs 削除。いずれも自己申告。kernel8.img は 9,276,375 B。ログ時刻 03.816 → 05.364 の差は 1.54 s、ブログの値は約 6 MiB/s、計算値は約 5.74 MiB/s。ログ行がロード完了後に出るため、差がロード時間とは限らない。`core_freq=550` でカーネル読込 20% 短縮との記述があるが、最終結果に適用されたか不明。 | 二次（単一ブログ）。フォーラムでのロード時間に関する指摘は未確認。 | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/<br>https://forums.raspberrypi.com/viewtopic.php?t=376022 |
| <3.5 s | Zero 2 W + Buildroot 2024.02.1（aarch64、フル glibc） | 電源投入から userspace プログラムの GPIO トグルまで（カーネル実行は約 400 ms）。カーネル 8.5 MiB（非圧縮、gzip 4.1 MiB。Raspbian 標準は 25 MiB、gzip 8.9 MiB）。sound、SD/MMC + ext4 以外の block/FS、RAID、USB、HID、DVB、video/framebuffer、高度なネットワークを無効。KASLR と Spectre 緩和は無効、モジュールは非圧縮。 | 二次（個人ブログの自己申告） | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| 約 5〜6 s（Pi Zero 系 Buildroot） | 条件不明 | buildroot-quickpi README は Pi 1 で約 5.5 s と記載。ほかの第三者値の出典は未特定。 | 二次（quickpi の 5.5 s のみ）。他の値は未確認。 | https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| 差 9 ms（`display_auto_detect=0` 等） | CM5 とされる | RP-010196-WP-1 に該当記述を確認できず、秒単位の大きな改善は見込めないとしています。 | 未確認。判断の根拠には使用しない。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf |

- 【未確認】CM0 の起動時間ベースラインは実測されていません。
- 【推測】「電源投入から CLI まで数秒」という目標は、GPU 段とカーネル読込だけで超える可能性があります。Pi 3B+ の ARM 開始値は約 6.79 s ですが、カーネルサイズや initramfs の有無で条件は大きく変わります。

### 5.3 config.txt 系の最適化（RP-010196-WP など）
- 【未確認】`max_framebuffers=0` で HDMI の EDID probe を省略できること、早期 splash が出なくなること、`disable_fw_kms_setup=1`、`camera_auto_detect=0` / `display_auto_detect=0`、`systemd-udev-settle` の注意点は、公開資料で個別に再確認が必要です。`initial_turbo=60` は 2024-11 以降との情報があり、SHA-256 検証を有効にすると数秒増えるとの記述もあります。確認先: https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf
- 【一次】M5 の `firmware/CardputerZero/config.txt` に `dtoverlay=fbtft,...st7789v`（コメント状態は未確認）、`dtoverlay=vc4-kms-v3d`、`dtoverlay=cardputerzero-overlay` などがあります。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12
- 【一次】公式 pi-gen の cmdline/config は `quiet fbcon=map:off cfg80211.ieee80211_regdom=AE`、`dtoverlay=vc4-kms-v3d,cma-64` を設定します。`regdom` が UAE（AE）固定のため、日本向けには変更が必要です。https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L36

### 5.4 カーネル圧縮（LZ4/LZO/ZSTD）
- 【未確認】arm64 に `HAVE_KERNEL_*` 圧縮方式の選択肢はないとされます。RPi Linux の `init/Kconfig` を確認先とします。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig
- 【一次・Pi 4 の記載】Raspberry Pi firmware は 64-bit カーネルに非圧縮イメージと gzip アーカイブを受け付けると説明します。rpi-eeprom issue #541 は Pi 4 の `start4.elf` を扱い、カスタム ARM stub や TF-A で展開する案も言及されています。CM0 での挙動や他形式のサポートは未確認です。https://github.com/raspberrypi/rpi-eeprom/issues/541<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52
- 【推測】armstub/TF-A 経由での展開は理論上の余地ですが、実績は未確認です。EFI zboot は start.elf からの起動では期待できません。
- 【一次】Raspberry Pi の `arm_64bit` 対応表には Zero 2 W/CM3/CM3+/CM4/CM4S が載り、CM0 は記載されていません。`config.txt` には `[cm0]` フィルターがあります。CM0 では `arm_64bit=1` または `kernel8.img` の明示が必要と整理しますが、実機動作は未確認です。https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43
- **推奨:** 非圧縮と gzip を実機で比較測定する（SD 読込速度と展開時間のトレードオフ）。

### 5.5 外部手法の評価
| 手法 | 確認済み事実 | 評価 | 出典URL |
|---|---|---|---|
| Boot Naked Linux | QEMU 上で tinyconfig + 静的 init により約 0.8 秒で init に到達したとの情報は未確認。 | カーネル削減と init 簡素化の手法として参考にする。 | 未確認。公開記事の確認先: https://techfeed.io/ |
| johschmitz/buildroot-quickpi | 【一次】Buildroot 2017.11、最終コミット 2018-01-05、Pi 1 と 32-bit Pi 3、Pi 1 で約 5.5 秒、read-only ext4 root と記載されています。README に overlayfs の記載は確認できません。Pi 3 版の root password 固定との情報は未確認です。 | カーネル削減手法のみ参考 | https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |

### 5.6 vc4/HDMI、CMA、LCD
- 【一次】`bcm2711_defconfig` には `CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y` があり、`DRM_VC4=m`、`DRM_PANEL_MIPI_DBI=m` です。`CONFIG_FRAMEBUFFER_CONSOLE=` の明示行は確認できません。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1110-L1135<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa
- 【推測】`FRAMEBUFFER_CONSOLE_ROTATION=y` は FRAMEBUFFER_CONSOLE が依存/既定で有効であることを示唆します。「defconfig に明示行が無い」ことは無効の証拠になりません。実際の有効性は最終 .config か Kconfig 依存の確認が必要で、現時点では未確認です。また公式 pi-gen の cmdline は `fbcon=map:off` です。LCD にシェルを出すには fbcon の割当て方が論点になります。
- **【推測】** HDMI 関連（EDID probe、vc4 初期化）を省くと起動が速くなる可能性がありますが、効果の大きさは CM0 での実測が必要です。CM5 で 9 ms 改善するとの値は出典を確認できず、根拠に使いません。
- **【推測】** vc4 はモジュール（=m）のため、遅延ロードまたは非ロードにできると考えられます。LCD ドライバを遅延させると LCD 上のシェル表示も遅れます。

### 5.7 M5 ドライバとカーネル版
【一次】以下は公開された M5 overlay ソースと Linux ソースで確認できます。https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20
  - 外部モジュール(obj-m)方式で、Kconfig はありません。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
  - ドライバごとのバージョン分岐:`gpio-forwarder.c:204` が >= 6.18、`m5ioe1.c:472` が >= 6.18、`cardputerzero-audio.c:25` が >= 7.0.0。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c#L204<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c#L472<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c#L25)
  - `dkms.conf` があるのは bq27220/es8389/m5ioe1/st7789v のみ。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
  - `modules/CardputerZero/Makefile:67` の config_setup は外部 gist から rpi-config.py を curl する(**自前イメージでは同梱物への置換が必要**)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L67)
  - M5 overlay はビルドごとに `main` から取得されるため、入力ソースが固定されません。本リポジトリでは [submodule の宣言](../../.gitmodules)でコミットを固定しています。https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L67-L74
  - `firmware/CardputerZero/config.txt` の overlay 名は `cardputerzero-overlay` ですが、Makefile のターゲットは `cardputerzero-v3-overlay` / `cardputerzero-v5-overlay` です。名称の不整合があり、正しい組み合わせは実機または公式イメージでの確認が必要です（未確認）。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile
- 【一次（Devin が 2026-10-18 に確認）】M5 の `panel-mipi-dbi-m.c` は `#include <drm/clients/drm_client_setup.h>` を持ち、このヘッダーは rpi-6.18.y にあります。rpi-6.12.y の同じパスは HTTP 404 ですが、6.12 系全体でヘッダーがないかは未確認です。6.13〜6.17 も未確認です。https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/include/drm/clients/drm_client_setup.h
- 【未確認】Wayback 版の cardputer-zero-os は、既存の `panel-mipi-dbi-spi` と firmware blob（`cardputerzero,st7789v.bin`）を使う経路を持つとの情報があります。したがって「LCD 全般が 6.18 以上を必要とする」わけではなく、「M5 の外部モジュールが前提」との整理です。確認先: https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os
- 【一次】CardputerZero/pi-gen は `6.18.39-1+rpt1` に pin されています。https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3
- 【一次】Buildroot 2026.08 の `raspberrypi3_64` / `raspberrypizero2w_64` defconfig は 6.12.61 に固定されています。CM0 用 defconfig と `bcmrpi3_defconfig` の有無は未確認です。確認先: https://github.com/buildroot/buildroot/tree/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs
- 【一次（Devin が 2026-10-18 に確認）】Buildroot 2026.08（2026-09-04 公開、2026-10-18 時点の最新安定版）の `raspberrypizero2w_64_defconfig` は BCM2711 defconfig を使い、DTS は `bcm2710-rpi-zero-2-w` です。RPi カーネルはコミット固定の tarball で取得します。CM0 の出発点候補であり、CM0 向けの直接対応ではありません。RPi Linux rpi-6.18.y には `bcm2710-rpi-cm0.dts` もあります。https://buildroot.org/download.html<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/boot/dts/broadcom/bcm2710-rpi-zero-2-w.dts<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts
- 【一次】RPi Linux の arm64 configs には `bcm2711_defconfig`、`bcm2711_rt_defconfig`、`bcm2712_defconfig`、汎用 `defconfig`、`hardening.config`、`virt.config` の 6 ファイルがあります。https://github.com/raspberrypi/linux/tree/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs
- 【**推測**】 BR2_LINUX_KERNEL_CUSTOM_GIT で rpi-6.18.y(6.18.57)をコミット固定するのが妥当です。
- 【一次】RX8130（RTC）は `drivers/rtc/rtc-ds1307.c` で扱われ、`RX8130_REG_ALARM_MIN`（L118）、`.compatible = "epson,rx8130"`（L1164）、`rx8130_read_alarm`（L608）、`rx8130_set_alarm`（L647）、`rx8130_alarm_irq_enable`（L692）、`rx8130_irq`（L577）が定義されています。`bcm2711_defconfig` は `CONFIG_RTC_DRV_DS1307=m` です。M5 の `modules/rx8130` には Makefile と overlay DTS があり、C ソースや別名 `rtc-rx8130*` は未確認です。CardputerZero overlay は I2C 0x32、単体 `rx8130-overlay.dts` は `reg = <0x68>` で食い違います。実機アドレスは未確認です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L118<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L1164<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L608<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1470<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130/rx8130-overlay.dts

### 5.8 ツールチェーン・チューニング(Buildroot 2026.08 周辺)
- 【一次】Buildroot 2026.08 の GCC 既定は **15.3.0**（選択式の候補は 14.4.0 / 16.2.0）です。https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6
- 【未確認】binutils 2.45.1、glibc 2.44、musl 1.2.6、BusyBox 1.38.0、uClibc-ng 1.0.59 が既定との情報があります。確認先: https://github.com/buildroot/buildroot/tree/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package
- 【未確認】zram 使用時の `vm.swappiness` 100〜180、`page-cluster=0` が推奨され、zram 使用時は zswap を無効にするとの情報があります。確認先: https://docs.kernel.org/admin-guide/sysctl/vm.html<br>https://wiki.archlinux.org/title/Zram
- 【未確認】dirty 系/printk 等の sysctl の根拠、`-mcpu=cortex-a53` や LTO の効果は確認できていません。確認先: https://docs.kernel.org/admin-guide/sysctl/vm.html<br>https://gcc.gnu.org/onlinedocs/gcc/AArch64-Options.html

---
