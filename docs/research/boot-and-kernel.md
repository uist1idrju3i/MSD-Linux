# 起動高速化・カーネル

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

## 14. カーネル縮小

### 14.1 ベース構成の作り方

| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| `allnoconfig` と `KCONFIG_ALLCONFIG` | allnoconfig は大半のオプションを無効化し、`KCONFIG_ALLCONFIG=<file>` で指定した値だけ有効にできる | https://docs.kernel.org/kbuild/kconfig.html | 一次 |
| `tinyconfig` の定義 | `kernel/configs/tiny-base.config` を ALLCONFIG にして allnoconfig → `tiny.config` を適用するターゲット(scripts/kconfig/Makefile L115-118) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/kconfig/Makefile#L115-L118 | 一次 |
| `tiny.config` の中身 | `CC_OPTIMIZE_FOR_SIZE=y`、`KERNEL_XZ=y`、`SLUB=y`、`SLUB_TINY=y`、`LD_DEAD_CODE_DATA_ELIMINATION=y` | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/configs/tiny.config | 一次 |
| arm64 には in-kernel 圧縮方式の選択肢が無い | arm64 の Kconfig に `HAVE_KERNEL_*` の select は見つからず(grep)、`KBUILD_IMAGE` は `Image.gz`(EFI_ZBOOT 無効時)。よって tinyconfig が入れる `KERNEL_XZ` は arm64 の Image 生成には効かない見込み(**grep 結果からの解釈**) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Makefile#L165-L176 | 一次(事実)/ 推測(解釈) |
| `localyesconfig` / `localmodconfig` | scripts/kconfig 配下の標準ターゲット。ただし**開発機のホスト上で稼働中のモジュール一覧**を元にするため、クロスビルドでは「実機(CM0)で `lsmod` した一覧」を持ち込む運用になる。CM0 実機での実績は未確認 | https://docs.kernel.org/kbuild/kconfig.html (localmodconfig/localyesconfig の語は同ページ内の記載を確認できず。**ターゲットの存在は scripts/kconfig を要確認**) | 推測(要確認) |
| RPi 既定 defconfig の性格 | `bcm2711_defconfig` は `CONFIG_PREEMPT=y`、zram 等を多数有効にした汎用構成(縮小前提ではない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 | 一次 |

> 【推測】tinyconfig は組込みの出発点として妥当ですが、arm64 + DT + SD 起動に必要なもの（bcm2835 SD host、SPI、I2C、DRM/fbdev、input、ext4/SquashFS または EROFS、overlayfs、devtmpfs、bcm2835_wdt）を積み上げる必要があります。どのオプションが起動時間にどれだけ影響するかは実機測定まで未確認です。まず `bcm2711_defconfig` から不要ドライバを削る方法の方が、動作する構成を早く得られる可能性があります。

### 14.2 個別項目

| 設定・方式 | 事実 | 出典 URL | 確認度 / 速度効果 |
|---|---|---|---|
| `CONFIG_PRINTK=n` | EXPERT 時のみ選択可。「メッセージ文字列の大半がイメージから消え、カーネルがほぼ無言になる。診断が非常に困難になるので N は強く非推奨」と Kconfig help にある | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1710-L1719 | 一次(事実)/ **速度効果は推測(未測定)** |
| `PRINTK=n` の副作用 | `printk.time`、`initcall_debug`(printk 出力に依存)、dmesg 経由の計測が使えなくなる(printk が無ければ出力先が無いという**論理的帰結**。ソースでは未確認) | https://docs.kernel.org/admin-guide/kernel-parameters.html(`initcall_debug` = 「initcall 実行をトレース」、`printk.time` = 「printk 各行に時刻を付ける」) | 一次(パラメータの定義)/ 推測(帰結) |
| 方針 | 開発・測定ビルドは PRINTK=y + `quiet` / `loglevel=` で運用します。量産ビルドで PRINTK=n を試す場合は、測定ビルドと別バイナリにし、差が出なければ採用しません（診断不能になるコストが大きいため）。 | — | 推測 |
| `CC_OPTIMIZE_FOR_SIZE`(-Os) | Kconfig help は「より小さいカーネルになる」とのみ記載。既定 `-O2` は「最良の性能」と記載 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1545-L1556 | 一次(定義)/ **速度影響は未測定=推測**(カーネル -Os の実行速度への公表ベンチは今回見つけていない) |
| 無圧縮 `kernel8.img` vs gzip | ファームウェアは 64bit カーネルとして「無圧縮イメージ」と「gzip アーカイブ」の両方を受け付け、先頭の署名バイトで判別する。`make Image.gz` が既定の arm64 ビルド対象、RPi 手順も `Image.gz` を `$KERNEL.img` にコピー | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L30-L40 / https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/linux_kernel/building.adoc#L160-L206 | 一次(受理形式)。**無圧縮が速いかは未測定=推測** |
| 無圧縮 vs gzip のトレードオフ式 | 総時間 ≒ SD 読込（サイズ ÷ GPU ローダのスループット）+ gzip の場合の展開時間です。この線形モデルは未検証です。KittenLabs は Pi で 9.3 MB を約 1.54 秒（ブログは約 6 MiB/s、9,276,375 B ÷ 1.54 s の計算値は約 5.74 MiB/s）とします。Zero 2 W、Raspbian 標準 kernel8.img のログ時刻差で、ロード時間とは限りません。CM0 の A53 での gunzip 時間は未測定です。 | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 二次（単一ブログ）/ 推測（CM0 への当てはめ） |
| pigz 2.8 の `-11` | Zopfli を使って標準 deflate/gzip 形式で圧縮するため、通常の inflate で展開できます。firmware による展開互換性と出力サイズは CM0 実機で未確認です。 | https://github.com/madler/pigz/tree/v2.8<br>https://github.com/madler/pigz/tree/v2.8/zopfli<br>https://www.rfc-editor.org/rfc/rfc1951<br>https://www.rfc-editor.org/rfc/rfc1952 | 一次（形式）/ 未確認（firmware 互換性・サイズ） |
| 圧縮方式（lz4/zstd）を変更 | arm64 の Image 圧縮は Raspberry Pi 方式では gzip か無圧縮が受理形式として明記されています。lz4/zstd は明記されておらず、使えるとは確認できません。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L30-L40 | 一次（記載の範囲）/ 未確認（他形式） |
| 判断基準 | 実機で「無圧縮」「gzip」を同一ビルドから作り、[1]firmware 読込 [2]展開 [3]initcall の各区間を比較します。 | — | 推測 |

### 14.3 モジュール（M5 ドライバ）の分類と依存関係

| 機能 | M5 側の実体(overlay の compatible) | 依存(DT から読める範囲) | 遅延読込の可否(見立て) | 出典URL |
|---|---|---|---|---|
| IO エキスパンダ M5IOE1 | `m5stack,m5ioe1`（I2C1 0x4f）。`m5ioe1.c`（out-of-tree .ko） | I2C1。LCD の RST/BL（PWM）、キーボードの reset GPIO と LED、powerfail の disabled GPIO、LED（gpio-leds）が参照するため、これらの親です。 | LCD / keyboard を遅延ロードするなら M5IOE1 も同時に遅延ロードします。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L46-L54<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100-L107<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L294-L295<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L313-L314<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0 |
| LCD(ST7789V3, SPI0) | `cardputerzero,st7789v_lcd` / `panel-mipi-dbi-m5stack`、DRM ドライバ `panel-mipi-dbi-m.c`、`pwm_bl_m5stack.c` | SPI0(CS GPIO8)、DC=GPIO25、backlight=M5IOE1 PWM、`<compatible>.bin` を `request_firmware` で読む（`cardputerzero,st7789v_lcd.bin` を含む） | 画面表示を起動完了条件に含める場合は先に必要です。含めない場合は後読みできます。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c#L220-L232<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L449-L457 |
| キーボード(TCA8418) | `m5stack,tca8418c`（I2C1 0x34、IRQ=GPIO27）、`tca8418_keypad_m5stack.c` | I2C1、M5IOE1（reset/LED）、input。udev ルールは `ID_PATH==platform-3f804000.i2c` を使って `/dev/input/cardputer-zero-internal` を作ります。 | キー入力を起動完了条件に含める場合は先に必要です。含めない場合は後読みできます。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L89-L107<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules |
| 音声(ES8389 系 codec) | overlay は `everest,es8390`（I2C 0x10）、`m5stack,cardputerzero-audio`（ASoC カード）、`simple-audio-amplifier`（enable=GPIO24）、HP 検出 GPIO17、I2S です。M5 の `es8389_m5stack.c` は compatible に対応します。 | I2C1、I2S clock（fragment@0）、amp GPIO。`cardputerzero-audio.c` は 7.0 以降で `dapm` ポインター化の分岐があり、6.18 は埋め込み側です。 | 起動に不要で、後読み向きです。ただし snd-soc 一式などモジュール間依存が多くあります。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L70-L77<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L336-L339<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c#L18-L31<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L379-L386 |
| RTC(RX8130) | `epson,rx8130`（I2C 0x32。CardputerZero overlay）。rpi-6.18.y の `drivers/rtc/rtc-ds1307.c` が対応し、`bcm2711_defconfig` は `RTC_DRV_DS1307=m` です。M5 の公開 `modules/rx8130` には Makefile と overlay DTS があり、独立した `rtc-rx8130.c` はありません。必要なのは別ドライバではなく DT overlay です。単体 `rx8130-overlay.dts` は `reg = <0x68>`、CardputerZero overlay は `<0x32>` で食い違い、実機アドレスは未確認です。 | I2C1 | 時刻が必要なアプリ次第です。起動直後は後読み可能と推測します。 | https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130/rx8130-overlay.dts<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L82-L84 |
| 電池ゲージ(BQ27220) | CardputerZero メイン overlay とは別の `bq27220_v5.dts`（`ti,bq27220`）と `bq27xxx_battery{,_i2c}.c` を使います。 | I2C1 | 後読み向き | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/bq27220-1.0/bq27220_v5.dts#L14 |
| IMU(BMI270 + BMM150) | 別 overlay `bmi270_overlay.dts` / `bmi270_bmm150_overlay.dts`(`bosch,bmi270`)。ファームウェア `bmi270-init-data.fw` が同梱。upstream に `drivers/iio/imu/bmi270` あり | I2C1、`.fw` ロード | 後読み向き | https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/imu-1.0 |
| powerfail_suo | `cardputerzero,powerfail-suo`（IRQ=GPIO6 falling、backlight、disabled-gpio=M5IOE1） | M5IOE1、GPIO6 | 電源断対策で早期に必要になる場合があります。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L289-L295 |
| gpio-forwarder / LED | `m5stack,gpio-forwarder`（GPIO22）、gpio-leds（G4 など） | M5IOE1 の一部 | 後読み可能です。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L345-L372<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L490-L498 |
| Wi-Fi(2.4GHz 802.11b/g/n) / Bluetooth | 公式 docs に記載。upstream `brcmfmac` ドライバは RPi ツリーに存在します（Makefile で確認）。firmware blob の取得元・同梱は未確認です。 | SDIO / UART、firmware | 後読み向き | https://docs.m5stack.com/en/CardputerZero<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/wireless/broadcom/brcm80211/brcmfmac/Makefile |
| Ethernet(SR9900A, USB) | USB hub（GL852G）の USB1 に SR9900A があります。Host/Slave スイッチが Slave だと hub ごと切断され Ethernet は使えません。USB ID 0fe6:9900 は `r8152.c`（RTL8152 系）の ID 表にあります。`sr9700.c` は 0fe6:9700/9702、`sr9800.c` は 0fe6:9800 のみです。`bcm2711_defconfig` は `USB_RTL8152=m`、`USB_NET_SR9700=m`、`USB_NET_SR9800=m` です。M5 docs は SR9900A とだけ記載しており、実際の USB ID が 0fe6:9900 かは未確認です。 | USB（dwc2 または dwc_otg）、hub。firmware 要否は未確認です。 | 後読み向き | https://docs.m5stack.com/en/CardputerZero<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/r8152.c<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/sr9700.c<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/sr9800.c<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig |
| カメラ(IMX219) | 公式 docs に IMX219 8MP とあります。upstream に `imx219.c` があります。M5 repo の camera overlay は GPIO16 を High にするもの（`camera-gpio16-high`）で、センサー本体の DT は RPi 標準 overlay 側と思われます（未確認）。 | CSI、unicam / libcamera 系 | 後読み向き（使うときだけ） | https://docs.m5stack.com/en/CardputerZero<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/i2c/imx219.c<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules |
| IR(TX/RX) | 公式 docs に IR_TX / IR_RX（G13 系）とあります。M5 repo に専用 overlay は見つかっていません。upstream に `gpio-ir-recv.c` / `gpio-ir-tx.c` があります。 | GPIO | 後読み向き。DT の追加は自前になる可能性があります（推測）。 | https://docs.m5stack.com/en/CardputerZero<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/rc/gpio-ir-recv.c<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/rc/gpio-ir-tx.c |

**依存の要点（一次の DT から）:** LCD・キーボード・powerfail は M5IOE1（I2C1）に連鎖します。LCD / キーボードを後読み可能とする開発段階と、プロンプトおよびキー入力を起動完了条件にする構成では、built-in にする集合が異なります。built-in 化する場合は `I2C1 → M5IOE1 → (PWM backlight) → SPI0 → panel → tca8418 → input` の依存があると推測します。

### 14.4 遅延読込の仕組み(カーネル側の一次情報)
- `initcall_debug` / `initcall_blacklist=` / `initramfs_async=` はカーネルパラメータとして文書化されている(https://docs.kernel.org/admin-guide/kernel-parameters.html)。【一次】
- 起動後に modprobe する場合、firmware が起動前に適用した overlay により DT 上のデバイスは存在してもドライバ未ロードの状態になります。後からドライバをロードすると `deferred probe` の対象になります。`CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT` の有無や待ち時間への影響は未確認です。確認先: https://docs.kernel.org/driver-api/driver-model/driver.html#deferred-probe<br>https://github.com/raspberrypi/linux/tree/rpi-6.18.y/drivers/base
- 【推測】Wi-Fi/音声/IMU/カメラ/IR/Ethernet は起動完了後に systemd の依存順で遅延ロードするか、BusyBox 系なら完了後に自前スクリプトでロードする案が考えられます。実際の削減量は実機で `initcall_debug` の上位項目を確認して決めます。

### 初期起動で必要なドライバ候補

【推測・未着手】T_shell を満たすための組み込み候補は SD、SquashFS/ext4、SPI、I2C、M5IOE1、LCD、keyboard です。Wi-Fi、Bluetooth、音声、カメラ、IMU、HDMI/vc4、Ethernet は起動後にモジュールとして遅延ロードする候補です。CM0 上の依存関係と起動時間への効果は未測定です。

## 15. 起動の終点定義と測定手法

### 15.1 終点の定義
主指標は **T_shell**（LCD にプロンプトが表示され、キー入力できる時点）、副指標は **T_init**（init / PID 1 が完了マーカーを書く時点）とします。両方を記録し、T_shell をユーザー向け起動時間として扱います。

| 案 | 終点 | 利点 | 欠点・衝突 |
|---|---|---|---|
| **A / T_shell** | LCD にシェルのプロンプトが表示され、かつキー入力が受け付けられる時点 | 主指標。体感に直結します。 | M5IOE1 → backlight → LCD → keyboard の依存を終点前に読み込む必要があります。 |
| **B / T_init** | init（PID 1）が終点マーカー（例: `/run/boot-done`）を書く時点 | 副指標。起動処理を一貫して比較できます。 | プロンプトが表示される時刻とはずれるため、T_shell と併記します。 |
| **C** | T_shell と T_init の両方を測り、差を遅延読込の効果として記録 | 両指標を比較できます。 | 測定の手間が増えます。 |

【推測・未実施】T_shell は内蔵 keyboard の `/dev/input/event*` 出現時刻と getty / shell が tty を開いた時刻を `/proc/uptime` で記録します。prompt の描画完了は LCD 更新遅延を内部時刻で捉えられないため、高速撮影で電源投入から表示までを外部測定します。T_init は完了マーカーの `/proc/uptime`、GPIO toggle、UART の時刻記録を照合します。printk のタイムスタンプも各起動段階の観測に使う案です。内部時刻と外部測定の差は LCD 描画遅れとして記録します。KittenLabs も GPIO toggle で測定しています。
どの案でも、測定条件(始点=電源投入、`console=`・quiet の有無)を固定する。

### 15.2 測定ツール

| 手法 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| `initcall_debug` | カーネルパラメータ。initcall 実行をトレース | https://docs.kernel.org/admin-guide/kernel-parameters.html | 一次 |
| `printk.time=1` / `CONFIG_PRINTK_TIME` | printk 各行に時刻を付ける(bcm2711_defconfig は `PRINTK_TIME=y`) | https://docs.kernel.org/admin-guide/kernel-parameters.html / https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1778 | 一次 |
| `scripts/bootgraph.pl` | `dmesg \| perl scripts/bootgraph.pl > out.svg`。`initcall_debug` を付けた dmesg から initcall の SVG を作る | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33 | 一次 |
| `systemd-analyze` | `blame` / `critical-chain` / `plot`（SVG）。man page は、`blame` が並列起動のため待ち時間を反映しないと注意しています。`Type=simple` のサービスは即時起動扱いのため blame に出ず、キュー待ちも含まれません。 | https://man7.org/linux/man-pages/man1/systemd-analyze.1.html | 一次 |
| bootchart(ユーザー空間) | systemd-bootchart の man7 ページは 404(今回取得できず)。**bootchart の一次情報は未取得** | (取得失敗:https://man7.org/linux/man-pages/man1/systemd-bootchart.1.html → HTTP 404) | 未取得 |
| strace | 実使用のシステムコール/ファイル open の洗い出しに使う(man) | https://man7.org/linux/man-pages/man1/strace.1.html | 一次 |
| ブート時 ftrace | カーネルパラメータ/bootconfig でブート時から tracing を有効化できる | https://docs.kernel.org/trace/boottime-trace.html / https://docs.kernel.org/admin-guide/bootconfig.html | 一次(存在)/ CM0 での有効性は未確認 |
| RPi 公式の区間分割 | EEPROM → GPU FW → カーネル展開・初期化 → initramfs → rootfs mount → systemd。CM0 には EEPROM がないため区間が異なります。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 一次 |

### 15.3 再現性（推測・未実施）
- 固定:同一個体・同一 SD・同一 firmware/bootcode・同一 cmdline。変えるのは 1 要素だけ。
- コールドブート N≥15、**1 回目は別扱い**、中央値と p90 を記録。電源は同一(バッテリ残量・USB 給電の別を固定)。
- 測定ビルドと量産ビルドの差(printk/initcall_debug の出力量自体が時間を伸ばす)を明記。シリアル出力はコンソール速度が起動時間に影響するため、**測定時のコンソール設定を固定**(`console=` と quiet の有無)。
- 数値の条件（機種・カーネル・始点終点）を必ず併記し、異なる条件の値を合成しません。

## 20. 6.18 以降の起動時間変更・カーネル比較・PREEMPT

### 20.1 起動時間（6.18 以降の変更）
- **結論:** BCM2837 級 arm64 で「6.18 以降に起動が速く/遅くなった」と実測した情報は見つかりませんでした。Phoronix の 7.0〜7.3 記事は性能記事が中心です。https://www.phoronix.com/search/Linux%207.3
- 起動時間に効きうる変更は少なく、多くは条件付き(RT のみ・eMMC のみ・x86/大メモリ向け)か未マージ:
  - printk スレッド化の「console_lock を record ごとに解放」は **RT 限定**(printk-for-6.19 pull 文面。一次):https://lkml.iu.edu/2512.0/00981.html → 非 RT の CM0 には**効かない可能性が高い(推測)**。
  - 7.3:`printk: Postpone kthread startup`(NBCON printer kthread を subsys_initcall へ)=安定化。https://www.phoronix.com/news/Linux-7.3-KThreads-NBCON(二次)
  - 7.1:`deferred_probe_timeout` を Kconfig 化(`56e3ee721b33`、一次):https://github.com/torvalds/linux/commit/56e3ee721b33
  - MMC: `bcm2835.c`（sdhost）は 6.18 → 7.2 で差分 0、7.2 → 7.3-rc7 で DMA device 取得の変更 36 行があります。tuning / CMD 1 polling の短縮提案（2026-09）は未 merge で eMMC / dw_mmc 向けのため、SDHCI 標準経路は対象外です。https://github.com/raspberrypi/linux/compare/rpi-6.18.y...rpi-7.2.y<br>https://github.com/raspberrypi/linux/compare/rpi-7.2.y...rpi-7.3.y<br>https://lkml.iu.edu/2609.2/00512.html
  - init_on_alloc 一括クリア(7.2。数値は **AMD 送信・16GB HugeTLB 条件**:0.445s→0.166s。CM0 に当てはめ不可):https://www.spinics.net/lists/kernel/msg6184200.html
  - 「mmc: core: Optimize boot time by detecting cards simultaneously」は 2015 年のコミットで、6.18 以降の変更ではありません。https://github.com/torvalds/linux/search?q=Optimize+boot+time+by+detecting+cards+simultaneously&type=commits
- 外部の起動時間報告(x86、CM0 に外挿不可。原因がカーネル回帰とは限らない事例):**Omarchy #6996**(Omarchy 4.0.0-1 / Linux 7.1.8-arch1-3、AMD+NVIDIA 混在機。約 266MiB の initramfs と `initramfs_async=0`。`1min 15.918s (kernel)`。2026-08-15 作成、取得時 open)https://github.com/omacom/omarchy/issues/6996 (リポジトリ移転済み。旧 URL は HTTP 404)。**CachyOS**(7.2 カーネルで graphical.target @1min 32.184s、6.18.48-1-cachyos-lts は @8.960s、x86)https://discuss.cachyos.org/t/7-2-kernel-boot-times-drastically-slower-than-6-18-lts/35306 :critical-chain に `cryptsetup.target` があり、**投稿者は後に「BIOS で TPM を無効にして解消」と報告(2026-09-10)**。7.2 カーネル自体の回帰と断定できない【二次・ユーザー報告】
- 未確認事項: kernelnewbies 7.3 は後半未読、LWN 個別記事の精読は一部のみ、全履歴の `git log` 検索は未実施、乱数サブシステムの 6.18 以降の変更は未調査です。確認先: https://kernelnewbies.org/Linux_7.3<br>https://lwn.net/Articles/

### 20.2 カーネル比較（6.18 対 7.x）
| 項目 | 内容 | 確認度 |
|---|---|---|
| RPi 公式既定 | `rpi-6.18.y`（6.18.57、リポジトリ既定ブランチ）。RPi OS Trixie 2026-10-06 イメージは 6.18.50。`rpi-7.2.y` = 7.2.11、`rpi-7.3.y` = 7.3.0-rc7（いずれも 2026-10-18 時点）。 | 一次。https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://github.com/raspberrypi/linux/tree/rpi-6.18.y<br>https://github.com/raspberrypi/linux/tree/rpi-7.2.y<br>https://github.com/raspberrypi/linux/tree/rpi-7.3.y |
| M5 ドライバ互換 | 7.1 で `drm_simple_display_pipe` 系 / `mipi_dbi_dev_init_with_formats` などが削除され、M5 の `panel-mipi-dbi-m.c` は 7.2 ではそのままでは API 不整合（header に存在しない関数 6 個）です。7.0 で `snd_soc_dapm_kcontrol_component/dapm` の別名が削除され、`es8389_m5stack.c` が影響します。ビルド可否は未確認で、API の存在確認までです。 | 一次（API 存在確認まで）。https://github.com/raspberrypi/linux/tree/rpi-7.2.y<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules |
| 起動時間(6.18 vs 7.2/7.3) | 同条件の公表実測は見つかっていません。ソース差分では SD ホスト（bcm2835 sdhost）・KASLR・圧縮展開コードは 6.18 → 7.2 で差分 0 です。 | 一次（差分の有無） / 推測（速度影響）。https://github.com/raspberrypi/linux/compare/rpi-6.18.y...rpi-7.2.y |
| 運用 | 7.0 / 7.1 は約 11 週で EOL（Wikipedia、二次）。6.18 LTS は予定 EOL 2028-12（kernel.org）。次の LTS 候補 7.4 は kernel.org が事前に公表しません。 | 一次 / 二次。https://en.wikipedia.org/wiki/Linux_kernel_version_history<br>https://www.kernel.org/category/releases.html |
| 評価 | 本番基準は 6.18.y、7.2 は同一構成での比較用とする案です。7.3 final 後または LTS 化された 7.4 を検討し、差（中央値 −300 ms 以上など）が出たら移行を検討します。閾値は仮置きです。 | 推測 |
- 7.3 final は 2026-10-18 公開予定と報じられるが、取得時点で未確認。

### 20.3 PREEMPT の確認結果
| カーネル | 事実 | 出典URL(コミット固定) |
|---|---|---|
| **6.18** | `Kconfig.preempt` の選択肢 `default PREEMPT_NONE`。`PREEMPT_VOLUNTARY` は `depends on !ARCH_NO_PREEMPT` と `!PREEMPT_RT` のみです。arm64 の Kconfig は `ARCH_NO_PREEMPT` を select していないため、VOLUNTARY は選択可能です。RPi の `bcm2711_defconfig` は `CONFIG_PREEMPT=y`（VOLUNTARY ではない）です。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt#L17-L52<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 |
| **7.2** | 既定は `default PREEMPT_LAZY if ARCH_HAS_PREEMPT_LAZY`（arm64 は `select ARCH_HAS_PREEMPT_LAZY`、arch/arm64/Kconfig L44）です。`PREEMPT_NONE` は `depends on ARCH_NO_PREEMPT`、`PREEMPT_VOLUNTARY` は `depends on !ARCH_HAS_PREEMPT_LAZY` です。arm64 は LAZY を持つため、NONE も VOLUNTARY も選べず、FULL / LAZY のみです。 | https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt#L17-L45<br>https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig#L44 |
- 【推測】起動時間のために VOLUNTARY / NONE を使う場合は 6.18 系に留まる必要があります。7.2 以降は PREEMPT_LAZY（または FULL）固定です。VOLUNTARY が起動時間に有利かは未測定です。PREEMPT_RT は採用しない方針です。
- 注意: 7.2 の RPi defconfig は確認できていません。6.18 では `CONFIG_PREEMPT=y` です。
- 7.0 の preempt モデル制限(コミット `7dadeaa6e851`)の外部報告:Graviton4(96vCPU)で pgbench 0.51x(スループット。**起動時間ではない・CM0 に不適用**)、LWN は「実は回帰ではない」と整理 https://lwn.net/Articles/1067029/ (二次)。

### 20.4 printk 方針
- **測定ビルドは PRINTK=y（`initcall_debug`・`printk.time=1`）、量産ビルドは `quiet` + 低 loglevel とし、PRINTK=n は別バイナリで試すのみ**とする案です（推測）。
- 6.19 の printk 改善は RT 限定の記述であり、非 RT の CM0 には効果が見込みにくい。7.3 の NBCON kthread 起動遅延は安定化目的で、コンソール出力開始が遅れる可能性は**推測**(測定なし)。

### 20.5 リスク: arm64 linear alias unmap 変更
一次（GitHub commit、2026-10-18 に確認）:
- **63e0b6a5b693**（2026-06-02、「kernel data/bss の線形エイリアス unmap」）と、その **revert f102131c842d**（2026-06-10）は、ともに v7.2-rc1、v7.2、v7.3-rc1 に含まれます。v7.2 では導入と revert が相殺されます。revert のメッセージ:「Unmapping the kernel '.bss' appears to break KVM initialisation on some devices, breaking the boot on popular platforms such as RaspberryPi3 and 4」。https://github.com/torvalds/linux/commit/63e0b6a5b693<br>https://github.com/torvalds/linux/commit/f102131c842d
- **再適用 fb0f3ef5601a**（2026-08-07）は v7.3-rc1 にのみ入り、v7.2-rc1 より後、v7.2 とは分岐し、v7.3-rc1 より前です。メッセージはハイバネーション時の map/unmap 処理を追加する内容で、KVM の問題が解消したとは記していません。https://github.com/torvalds/linux/commit/fb0f3ef5601a
- RPi ツリー:`rpi-7.2.y` の mmu.c は「Map the kernel data/bss read-only」の旧コード(影響なし)。`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid` と PM notifier)を含む。
- **CM0(BCM2837、Cortex-A53)で 7.3 系(再適用後)が起動するかは未確認**。revert メッセージは RPi 3/4 を挙げている(BCM2837 は RPi 3)ので、7.3 採用時は「起動確認を最初の実機試験に置く」(推測)。7.2 系は上記の理由で当該リスクを持たない(7.2 にその他の CM0 固有の問題が無いことは別途未確認)。

## 22. 関連する設計事項

以下は起動時間や電断耐性の検討項目です。公開根拠が不足している主張は未確認または推測として示します。

| 話題 | 内容・条件 |
|---|---|
| `config.txt` 最適化 | `boot_delay`、`disable_splash` などの候補があります。`disable_fw_kms_setup` 等が BCM2837 で有効かは未確認です。確認先: [Raspberry Pi 起動資料](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| DTB 最小化 | Pi 3 の単一ブログに実測例があるとの情報ですが、条件固有で、別機種の値とは合成できません。記事 URL を特定できていないため未確認です。確認先: https://furkantokac.com/ |
| initcall 非同期化・モジュール化 | カーネル初期化とモジュールのロードを分け、遅延ロードする案があります。`initcall_debug` で実機の時間を計測する必要があります。https://docs.kernel.org/admin-guide/kernel-parameters.html |
| initramfs 非同期展開 | `initramfs_async` は kernel parameter として文書化されています。mainline 化は 2021 年の `e7cb072eb988` です。Victron 由来とされる説明は古い可能性があります。https://docs.kernel.org/admin-guide/kernel-parameters.html<br>https://github.com/torvalds/linux/commit/e7cb072eb988 |
| GPU 読込とカーネルサイズ | サイズが読込時間に影響するとの見立ては推測で、比例関係は未確認です。KittenLabs は Zero 2 W の Raspbian 標準 kernel8.img（9,276,375 B）について、ログ時刻の差 1.54 s（計算値約 5.74 MiB/s、ブログ記載は約 6 MiB/s）を掲載しています。単一ブログの条件固有値です。https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| firmware の代替 | rpi-open-firmware、U-Boot Falcon などは候補ですが、CardputerZero での対応状況は未確認です。https://github.com/search?q=rpi-open-firmware&type=repositories<br>https://github.com/CardputerZero/u-boot |
| LCD の先行点灯 | 起動完了条件に画面表示を含める場合は早期ロードが必要です。含めない場合は M5IOE1 → backlight → LCD の依存を保ったまま遅延ロードする案があります（推測）。 |
| init・rootfs・ユーザー空間 | init 直起動、s6 / runit、EROFS（LZ4）と配置最適化、静的リンク / LTO / UPX、network の遅延起動や readahead は個別に検討します。[ユーザー空間とセキュリティ](userspace-and-security.md) |
| 電断検知 | 公式 docs の SW_DET = G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`（falling）は、同じ GPIO6 で矛盾しません。GPIO6 は CM0 側の SW_DET です。M5IOE1 側の PYG6 は MIC_SW で別信号です。`disabled-gpios = <&m5ioe1 11 1>` が PYG12（LCD_RST）に当たるかは index + 1 の推論で未確認です。https://docs.m5stack.com/en/CardputerZero<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L289-L295 |
| 書込み量と原子性 | rootfs を read-only にして書込みを最小化する案、ext4 `data=ordered`、更新時の atomic write が検討対象です。[電源と更新](power-and-updates.md) |
| 電源喪失保護付き SD | UCSD の DAC 2011 論文などに PLP 付きストレージの記述があります。pSLC は eMMC 向けで microSD には適用できないとの情報があり、ベンダー主張は未検証です。[公開出典一覧](sources.md) |
| dm-verity | CM0 に AES/SHA 命令がないとの前提と SHA-256 のソフトウェア実装コストは未確認です。A/B 切替時のみ全検証する案があります（推測）。確認先: https://developer.arm.com/documentation/ddi0500/latest/ |
| watchdog と復旧 | WDT、boot counter、最小復旧イメージは候補です。復旧方式は未決です。[電源と更新](power-and-updates.md) |
| 電断試験 | `dm-flakey`、`dm-log-writes`、CrashMonkey などの障害注入が候補です。これらは実カードの FTL や実際の電源遮断を再現しません。[公開出典一覧](sources.md) |
| スーパーキャパシタ | 筐体内に搭載するのは難しいとの見立てですが、寸法・電力条件の確認は未実施です（推測）。 |
