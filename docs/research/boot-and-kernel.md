# 起動高速化・カーネル

## 5. 超高速起動の調査

### 5.1 起動シーケンスと M5 BENCHMARK.md
- 【**報告による**】 起動順は boot ROM → bootcode.bin → start.elf(VideoCore GPU ファーム)→ kernel8.img です。(v5 が示した boot.adoc L26-52 は `arm_64bit` の説明で、この起動順の根拠ではないことを v6 で確認。起動順そのものの一次ページは示せていません)
- 【**報告による**】 GPU 段を公式にスキップする方法は見つかっていません(「存在しないこと」は確認できないため、確認済みにはしません)。armstub、TF-A、U-Boot、Circle はいずれも GPU 段より後に動くとされます。rpi-open-firmware と lk-overlay は実験的な代替です。(出典なし)
- 【**確認済み**】(circle-boot-splash `app/cardputerzero-splash/BENCHMARK.md`、HEAD b80d7c6、最終 push 2026-05-14、**リポジトリは ARCHIVED**。AI 支援文書で自己申告。ローカル grep 2026-10-18)(出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21<br>https://api.github.com/repos/CardputerZero/circle-boot-splash)
  - GPU ファーム(bootcode.bin + start_cd.elf)**2112ms**(行内に「227KB kernel をロード」とあり、**独自の小型ベアメタルカーネルを読む構成**)(出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21)
  - 画面点灯 **2.26s**、「Linux 可用」**~7〜9s**(実測と概算の合算、終点の定義なし)(出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21)
  - config.txt の最適化(boot_delay=0、gpu_mem=16、start_cd.elf、force_eeprom_read=0、initial_turbo=60 等)でも ARM 開始は 2112ms で不変(出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21)
  - 【**確認済み・一次(M5 の自己申告)**】 gzip 9.2MB カーネルの 2 回目の読込(二次固件加载)+2.1s、Linux→ユーザー空間(Linux 内核启动)+3-5s、総計 ~7-9s は、同じ BENCHMARK.md の表にあります(HTTP 200、2026-10-18。v5 は「監査報告による」としていたが誤りで、既に引用している URL で確認できる)(出典: https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L19-L21)
- 【**作成者の見立て**】 2112ms は「小さなカーネルを読んだ場合の GPU 段」であり、通常の大きなカーネル+initramfs を読む構成の下限とは別物です。【**推測**】 GPU 段がカーネルサイズに比例するかは未確認です。参考値:WP-1 の Pi 3B+ ログは kernel8.img 10,156,403 B で `Loaded` 4.131 s → `Device tree loaded` 6.760 s(差 2.63 s。この区間の中身は未確認)、KittenLabs の Zero 2 W は 9,276,375 B で約 1.54 s。サイズ比 1.09 に対し時間比は約 1.7 で、機材もログの区切りも異なるため比例とは言えない。確かめるには実機で同一 SD・同一構成のカーネルサイズ違いを測る必要がある(10.2)。
- 組織には CardputerZero/u-boot リポジトリ(2026-06-11)もあります(【**報告による・未確認**】)。(出典: https://github.com/CardputerZero/u-boot)

### 5.2 数値の台帳(**合成不可**:対象 SoC・条件が異なる)

| 数値 | 対象/版 | 条件・終点 | 確認度 | 出典URL |
|---|---|---|---|---|
| 電源→ARM 開始 2112ms、画面点灯 2.26s | CM0(M5 自己申告) | 小型ベアメタルカーネル 227KB、start_cd.elf | 確認済み(BENCHMARK.md)。自己申告 | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| 「Linux 可用」~7〜9s | CM0(M5 自己申告) | 実測+概算の合算、終点定義なし | 確認済み(同上)。値の信頼性は低い | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| ARM 開始 約 6.79s | Pi 3B+(BCM2710 系)、RP-010196-WP-1(Release 1、2026-06-01)付録のログ | 既定ファーム+initramfs 11.7MB(0xb2483c=11,683,900 B)+kernel8.img 約 10.2MB(`Loaded 'kernel8.img' to 0x200000 size 0x9af973`=10,156,403 B。9.69MiB。v6 までの値は誤り)、標準ログ | 確認済み(v7:PDF 付録のログで ARM 開始 06.79s、initramfs 0xb2483c、kernel8.img 0x9af973 を `pdftotext` 後の `grep -n` で確認。22:06 JST) | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>(v7:PDF 付録の `bcm2710-rpi-3-b-plus.dtb` のログ行で Pi 3B+ を確認。kernel8.img は 10,156,403 B、initramfs は 11,683,900 B。v6 までのカーネルサイズの値は誤り) |
| 約 7s | CM5、同ホワイトペーパー(RP-010196-WP、2026-07-16 版は**報告**) | Pi OS 既定、主に Pi4/5 対象、zstd 推奨。EROFS 16K が 3 倍超の値は CM5+6.18 | 報告による・未確認 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>(CM5 の 7s 値は今回未再確認) |
| 5.38s→4.75s→4.47s | Pi Zero 2 W+HQ カメラ(IMX477)、Raspbian ベース(KittenLabs ブログ 2024-09-01。**第三者ではなく出典は同ブログ**)。5.38→4.75s=カメラ/ディスプレイの自動検出を無効化、→4.47s=initramfs 削除(いずれも「self reported」) | カーネル 9,276,375B(Raspbian 標準 kernel8.img)の読込 1.54s は、ブログ中のログのタイムスタンプ 03.816→05.364 からの値で、ブログは「約 6MiB/s」(計算値は約 5.74MiB/s)。**ログ行がロード完了後に出るためロード時間とは限らない**(RPi フォーラム t=376022 の指摘、監査報告。フォーラム本文は読めておらず【報告による】。13.4B)。`core_freq=550` でカーネル読込 20% 短縮の記述があるが、最終結果に適用されたかは不明 | 確認済み・二次(個人ブログ本文を v5 で再読) | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| <3.5s | Zero 2 W+Buildroot 2024.02.1(aarch64、フル glibc)(KittenLabs) | 電源投入→userspace プログラムの GPIO トグルまで(カーネル実行は約 400ms)。カーネル 8.5MiB(非圧縮。gzip で 4.1MiB。Raspbian 標準は 25MiB・gzip 8.9MiB)、sound・SD/MMC+ext4 以外の block/FS・RAID・USB・HID・DVB・video/framebuffer・高度なネットワークを無効、KASLR 無効、Spectre 緩和無効、モジュール非圧縮 | 確認済み・二次(個人ブログ本文を v5 で再読。本人の自己申告) | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| 約 5〜6s(Pi Zero 系 Buildroot) | 第三者の別条件値 | 条件不明 | 確認済み・二次(buildroot-quickpi の 5.5 秒のみ。参考のみ) | 参考値(https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 )。他の第三者値は【報告による】で URL なし |
| 差 9ms(display_auto_detect=0 等) | CM5 とされる | **出典を特定できない。RP-010196-WP-1 には該当記述が無く、同書は「秒単位の大きな改善は見込めない」と述べる**(監査報告) | 【**未確認**】(旧版の「確認済み」から降格。判断の根拠に使わない) | URL なし(出典自体が未特定。WP-1 には該当記述なし:https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |

- 【**未確認**】 CM0 でのベースライン実測値はありません。
- 【**作成者の見立て**】 「電源→CLI で数秒」は、GPU 段+カーネル読込だけで超えうる(Pi 3B+ の ARM 開始が約 6.79s という報告値があるため)。ただし前提(カーネルサイズ、initramfs の有無)で大きく変わります。

### 5.3 config.txt 系の最適化(RP-010196-WP 等)
- 【**報告による・未確認**】(旧版で【確認済み】としていたが、今回のローカル再確認の対象外)
  - max_framebuffers=0 で HDMI の EDID プローブを省略できる(早期スプラッシュは出なくなる)(出典: URL未取得(RP-010196-WP-1 の該当節は未再確認: https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf))
  - disable_fw_kms_setup=1、camera_auto_detect=0 / display_auto_detect=0、systemd-udev-settle に注意
  - initial_turbo=60(2024-11〜)。sha256 検証を有効にすると数秒増える
- 【**確認済み**】(M5 firmware/CardputerZero/config.txt、HEAD 7551854、2026-10-18 grep)`dtoverlay=fbtft,...st7789v`(コメント状態は未確認)、`dtoverlay=vc4-kms-v3d`、`dtoverlay=cardputerzero-overlay` など。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12)
- 【**確認済み**】(CardputerZero/pi-gen 791a985)公式 pi-gen の cmdline/config: `quiet fbcon=map:off cfg80211.ieee80211_regdom=AE`、`dtoverlay=vc4-kms-v3d,cma-64`。**regdom が UAE(AE)固定である点は日本向けには要変更** です。(出典: https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L36)

### 5.4 カーネル圧縮(LZ4/LZO/ZSTD)
- 【**報告による**】 arm64 には圧縮方式の選択肢(HAVE_KERNEL_*)がありません(旧版の記述。否定の主張のため確認済みにはしない)。v6 の参考確認:rpi-6.18.y @2341883 の `arch/arm64/Kconfig` を grep すると HAVE_KERNEL は 0 件(`init/Kconfig` に 17 件)。(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig)
- 【**確認済み**】 start.elf(VPU)が読めるのは非圧縮か gzip のみで、VPU コードに他の展開形式を追加しない方針です(rpi-eeprom #541、2024-02-11。ただし #541 は Pi4 の start4.elf の話。timg236 は「カスタム ARM スタブや TF-A なら展開できる」と述べている=監査報告による)。(出典: https://github.com/raspberrypi/rpi-eeprom/issues/541)
- 【**推測**】 armstub/TF-A 経由の展開は理論上の余地ですが、実績は【**未確認**】です。EFI zboot は start.elf からの起動では期待できません。
- 【**確認済み**】 arm_64bit の対応表(raspberrypi/documentation ddea98e、2026-10-13、`config_txt/boot.adoc`)には Zero 2 W/CM3/CM3+/CM4/CM4S が載っています。【**報告による**】(否定。範囲:ddea98e の `boot.adoc` に対する `grep -c CM0` が 0 件、2026-10-18 22:08 JST に再実行)**CM0 は載っていません**(その他の既定は 0)。config.txt には `[cm0]` フィルタがあります(`conditional.adoc`)。→ CM0 では `arm_64bit=1` か kernel8.img の明示が必要、と整理します(旧 U2 は解消。実機動作は別問題)。(出典: https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43)
- **推奨:** 非圧縮と gzip を実機で比較測定する(SD 読込速度と展開時間のトレードオフ)。

### 5.5 外部手法の評価
| 手法 | 確認済み事実 | 評価 | 出典URL |
|---|---|---|---|
| Boot Naked Linux | 【**報告による**】 tinyconfig+静的 init、QEMU 上で約 0.8 秒で init に到達(techfeed の記事は本文を読めていない。13.4B) | カーネル削減/init 簡素化の手法として参考 | URL なし(記事本文の確認なし) |
| johschmitz/buildroot-quickpi | 【**確認済み**】(clone、2026-10-18)Buildroot 2017.11、最終コミット 2018-01-05、Pi1 と 32bit Pi3 のみ、Pi1 で約 5.5 秒、ro ext4 root。【**報告による**】(否定。範囲:README の `grep -in overlay`。v8 で再実行せず)overlayfs の記述は見当たらない。Pi3 版は root パスワード固定等(報告) | カーネル削減手法のみ参考 | https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |

### 5.6 vc4/HDMI、cma、LCD(追加質問 Q2・Q3)
- 【**確認済み**】(raspberrypi/linux rpi-6.18.y 234188315、2026-10-16、`arch/arm64/configs/bcm2711_defconfig`)`CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y` はあるが `CONFIG_FRAMEBUFFER_CONSOLE=` の明示行は【**報告による**】(否定。範囲:`grep -c '^CONFIG_FRAMEBUFFER_CONSOLE='` が 0 件、`grep -n FRAMEBUFFER_CONSOLE` は L1135 の ROTATION のみ。2026-10-18 22:12 JST)見当たらない。DRM_VC4=m、DRM_PANEL_MIPI_DBI=m(監査報告による値を含む)。(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1110-L1135<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa)
- 【**推測**】 `FRAMEBUFFER_CONSOLE_ROTATION=y` は FRAMEBUFFER_CONSOLE が依存/既定で有効であることを示唆します。「defconfig に明示行が無い」ことは無効の証拠になりません。実際の有効性は最終 .config か Kconfig 依存の確認が必要で【**未確認**】です。また公式 pi-gen の cmdline は `fbcon=map:off` です(5.3 節)。LCD にシェルを出すには fbcon の割当て方が論点になります。
- **【推測】Q2(LCD のみで速くなるか):** HDMI 関連(EDID プローブ、vc4 初期化)を省く効果は見込めますが、大きさは CM0 での実測が必要です。旧版が根拠にした「CM5 で 9ms」は出典未特定のため根拠から外しました(5.2 節)。
- **【推測】Q3(HDMI ドライバの遅延ロード):** vc4 はモジュール(=m)なので遅延ロード/非ロードは可能と考えられます。LCD ドライバを遅延させると LCD 上のシェル表示も遅れます。

### 5.7 M5 ドライバとカーネル版の前提
- 【**確認済み**】(m5stack-linux-dtoverlays HEAD 7551854、2026-09-23、grep 2026-10-18)(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
  - 外部モジュール(obj-m)方式で、Kconfig はありません。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
  - ドライバごとのバージョン分岐:`gpio-forwarder.c:204` が >= 6.18、`m5ioe1.c:472` が >= 6.18、`cardputerzero-audio.c:25` が >= 7.0.0。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c#L204<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c#L472<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c#L25)
  - `dkms.conf` があるのは bq27220/es8389/m5ioe1/st7789v のみ。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
  - `modules/CardputerZero/Makefile:67` の config_setup は外部 gist から rpi-config.py を curl する(**自前イメージでは同梱物への置換が必要**)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L67)
  - firmware/CardputerZero/config.txt の overlay 名は `cardputerzero-overlay` だが、Makefile のターゲットは `cardputerzero-v3-overlay`/`cardputerzero-v5-overlay`(**名称の不整合**。どちらが正かは実機/公式イメージで確認が必要=【**未確認**】)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20)
- 【**一次**】 M5 の `panel-mipi-dbi-m.c`(@7551854)L18 は `#include <drm/clients/drm_client_setup.h>` を持つ。このヘッダは rpi-6.12.y の同パスで raw GET が HTTP 404、rpi-6.18.y で HTTP 200。→ **6.12 ではこの include が解決しない**。6.13〜6.17 は未確認(UN-24)。(出典: https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c / https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h)
- 【**報告による・未確認**】 公式プロファイル cardputer-zero-os(Wayback 版)は、メインライン既存の `panel-mipi-dbi-spi`+ファームウェア blob(`cardputerzero,st7789v.bin`)を使う経路を持っていた。つまり「LCD 全般が 6.18 以上前提」ではなく「M5 の外部モジュールが前提」(8.2 節)。(出典: URL未取得(Wayback のスナップショット URL は取得できず))
- 【**確認済み**】 CardputerZero/pi-gen は 6.18.39-1+rpt1 に固定しており、公式イメージが 6.18 系であることと整合します(8.1 節)。(出典: https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3)
- 【**確認済み**】 Buildroot 2026.08 の raspberrypi3_64/raspberrypizero2w_64 defconfig は 6.12.61 固定、【**報告による**】(否定。範囲:Buildroot d518030 の `configs/` のファイル名。CM0 専用 defconfig は見当たらず、`bcmrpi3_defconfig` も見当たらない。監査 5.1 の再現による)。確認できた肯定:arm64 の RPi 用は bcm2711_defconfig(`git ls-tree --name-only HEAD arch/arm64/configs/` の結果は bcm2711_defconfig・bcm2711_rt_defconfig・bcm2712_defconfig のほか汎用の defconfig・hardening.config・virt.config の 6 つ。2026-10-18 22:08 JST 再実行。**v6 の『bcm2711/bcm2711_rt/bcm2712 のみ』は誤り**)。(出典: https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig#L11-L12<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig#L12-L13)
- 【**推測**】 BR2_LINUX_KERNEL_CUSTOM_GIT で rpi-6.18.y(6.18.57)をコミット固定するのが妥当です。
- 【**確認済み**】 RX8130(RTC)は `drivers/rtc/rtc-ds1307.c`(rpi-6.18.y @2341883)で扱われます(いずれも `grep -n`):レジスタ定義 `RX8130_REG_ALARM_MIN` が L118、`.compatible = "epson,rx8130"` が L1164、alarm 関数は `rx8130_read_alarm` L608・`rx8130_set_alarm` L647・`rx8130_alarm_irq_enable` L692(L577 は `rx8130_irq`)。bcm2711_defconfig L1470 は `CONFIG_RTC_DRV_DS1307=m`。したがって**別ドライバは不要**(12.6 #2・14.3 と同じ結論)。【**報告による**】(否定。範囲:rpi-6.18.y @2341883 の `git ls-tree --name-only HEAD drivers/rtc/ | grep -ci rx8130` が 0 件、`modules/rx8130` の `git ls-tree -r --name-only HEAD` が Makefile と rx8130-overlay.dts のみ)M5 の `modules/rx8130`(@7551854)は Makefile とオーバーレイ DTS だけで C ソースは無く、別名ファイル `rtc-rx8130*` は見当たりません。実機の I2C アドレス(0x32 か 0x68)は【**未確認**】(UN-26)。(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L118<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L1164<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L608<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1470)

### 5.8 ツールチェーン・チューニング(Buildroot 2026.08 周辺)
- 【**確認済み**】 GCC 既定 **15.3.0**(`package/gcc/Config.in.host`、選択式で 14.4.0/16.2.0)。(出典: https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6)
- 【**報告による・未確認**】 binutils 既定 2.45.1、glibc 2.44、musl 1.2.6、BusyBox 1.38.0、uClibc-ng 1.0.59。(出典: URL未取得)
- 【**報告による**】 zram 使用時の sysctl:vm.swappiness 100〜180、page-cluster 0(vm.rst/Arch Wiki)。zram を使うなら zswap は切る。(出典なし)
- 【**未確認**】 dirty 系/printk 等の sysctl の根拠、`-mcpu=cortex-a53` や LTO の効果(一次資料なし)。

---

## 14. カーネル縮小(提案 1)

> 11 章との対応: 11.1(カーネル縮小)、11.3 D5(11.5 に対応表)

### 14.1 ベース構成の作り方

| 項目 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| `allnoconfig` と `KCONFIG_ALLCONFIG` | allnoconfig は大半のオプションを無効化し、`KCONFIG_ALLCONFIG=<file>` で指定した値だけ有効にできる | https://docs.kernel.org/kbuild/kconfig.html | 一次 |
| `tinyconfig` の定義 | `kernel/configs/tiny-base.config` を ALLCONFIG にして allnoconfig → `tiny.config` を適用するターゲット(scripts/kconfig/Makefile L115-118) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/kconfig/Makefile#L115-L118 | 一次 |
| `tiny.config` の中身 | `CC_OPTIMIZE_FOR_SIZE=y`、`KERNEL_XZ=y`、`SLUB=y`、`SLUB_TINY=y`、`LD_DEAD_CODE_DATA_ELIMINATION=y` | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/configs/tiny.config | 一次 |
| arm64 には in-kernel 圧縮方式の選択肢が無い | arm64 の Kconfig に `HAVE_KERNEL_*` の select は見つからず(grep)、`KBUILD_IMAGE` は `Image.gz`(EFI_ZBOOT 無効時)。よって tinyconfig が入れる `KERNEL_XZ` は arm64 の Image 生成には効かない見込み(**grep 結果からの解釈**) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Makefile#L165-L176 | 一次(事実)/ 推測(解釈) |
| `localyesconfig` / `localmodconfig` | scripts/kconfig 配下の標準ターゲット。ただし**開発機のホスト上で稼働中のモジュール一覧**を元にするため、クロスビルドでは「実機(CM0)で `lsmod` した一覧」を持ち込む運用になる。CM0 実機での実績は未確認 | https://docs.kernel.org/kbuild/kconfig.html (localmodconfig/localyesconfig の語は同ページ内の記載を確認できず。**ターゲットの存在は scripts/kconfig を要確認**) | 推測(要確認) |
| RPi 既定 defconfig の性格 | `bcm2711_defconfig` は `CONFIG_PREEMPT=y`、zram 等を多数有効にした汎用構成(縮小前提ではない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 | 一次 |

> 【作成者の見立て】tinyconfig は組込みの出発点として妥当だが、arm64+DT+SD 起動に必要なもの(bcm2835 SD ホスト、SPI、I2C、DRM/fbdev、input、ext4/SquashFS or EROFS、overlayfs、devtmpfs、bcm2835_wdt)を積み上げる作業になり、**どのオプションがいくら起動時間に効くかは実機測定まで推測**。まず `bcm2711_defconfig` から不要ドライバを削る減算方式の方が、動作する構成を早く得られる(推測)。

### 14.2 個別項目

| 提案 | 事実 | 出典URL | 確認度 / 速度効果 |
|---|---|---|---|
| `CONFIG_PRINTK=n` | EXPERT 時のみ選択可。「メッセージ文字列の大半がイメージから消え、カーネルがほぼ無言になる。診断が非常に困難になるので N は強く非推奨」と Kconfig help にある | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1710-L1719 | 一次(事実)/ **速度効果は推測(未測定)** |
| `PRINTK=n` の副作用 | `printk.time`、`initcall_debug`(printk 出力に依存)、dmesg 経由の計測が使えなくなる(printk が無ければ出力先が無いという**論理的帰結**。ソースでは未確認) | https://docs.kernel.org/admin-guide/kernel-parameters.html(`initcall_debug` = 「initcall 実行をトレース」、`printk.time` = 「printk 各行に時刻を付ける」) | 一次(パラメータの定義)/ 推測(帰結) |
| 方針(作成者の見立て) | 開発・測定ビルドは PRINTK=y + `quiet`/`loglevel=` で運用。量産ビルドで PRINTK=n を試す場合は、**測定ビルドと別バイナリ** にし、差が出なければ採用しない(診断不能になるコストが大きい) | — | 推測 |
| `CC_OPTIMIZE_FOR_SIZE`(-Os) | Kconfig help は「より小さいカーネルになる」とのみ記載。既定 `-O2` は「最良の性能」と記載 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1545-L1556 | 一次(定義)/ **速度影響は未測定=推測**(カーネル -Os の実行速度への公表ベンチは今回見つけていない) |
| 無圧縮 `kernel8.img` vs gzip | ファームウェアは 64bit カーネルとして「無圧縮イメージ」と「gzip アーカイブ」の両方を受け付け、先頭の署名バイトで判別する。`make Image.gz` が既定の arm64 ビルド対象、RPi 手順も `Image.gz` を `$KERNEL.img` にコピー | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L30-L40 / https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/linux_kernel/building.adoc#L160-L206 | 一次(受理形式)。**無圧縮が速いかは未測定=推測** |
| 無圧縮 vs gzip のトレードオフ式 | 総時間 ≒ SD 読込(サイズ÷GPU ローダのスループット)+(gzip なら)展開(【**推測**】:この線形モデルは未検証。5.2 の注)。KittenLabs は Pi で 9.3MB を約 1.54 秒(ブログは約 6MiB/s、9,276,375B÷1.54s の計算値は約 5.74MiB/s。Zero 2 W、Raspbian 標準 kernel8.img、ログ時刻の差でありロード時間とは限らない。条件固有)。CM0 の A53 での gunzip 時間は未測定 | https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 二次(単一ブログ)/ 推測(CM0 への当てはめ) |
| 圧縮方式(lz4/zstd)を変更 | arm64 の Image 圧縮は RPi 方式では gzip か無圧縮が受理形式として明記され、lz4/zstd は **明記なし**(=使えるとは言えない)。v3 5.4 節の記述も参照 | 上記 boot.adoc L30-L40 | 一次(記載の範囲)/ 未確認(他形式) |
| 判断基準 | 実機で「無圧縮」「gzip」を同一ビルドから作り、`[1]firmware 読込 [2]展開 [3]initcall` の各区間を比較(15 章) | — | 推測 |

### 14.3 モジュール(M5 ドライバ)の分類と依存関係(M5 @ 7551854 の v5 overlay と各ソースから)

| 機能 | M5 側の実体(overlay の compatible) | 依存(DT から読める範囲) | 遅延読込の可否(見立て) | 出典URL |
|---|---|---|---|---|
| IO エキスパンダ M5IOE1 | `m5stack,m5ioe1`(I2C1 0x4f)。`m5ioe1.c`(out-of-tree .ko) | I2C1。**LCD の RST/BL(PWM)、キーボードの rest-gpio と LED、powerfail の disabled-gpio、LED(gpio-leds)が参照する**ため、これらの親 | LCD/キーボードを後読みにするなら M5IOE1 も同時に後読み | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L46-L54 / #L100-L107 / #L294-L295 / #L313-L314 |
| LCD(ST7789V3, SPI0) | `cardputerzero,st7789v_lcd` / `panel-mipi-dbi-m5stack`、DRM ドライバ `panel-mipi-dbi-m.c`、`pwm_bl_m5stack.c` | SPI0(CS GPIO8)、DC=GPIO25、backlight=M5IOE1 PWM、**`<compatible>.bin` を request_firmware で読む**(`cardputerzero,st7789v_lcd.bin` が repo にある) | 終点の定義(15.1)が案 A なら先に必要、案 B なら終点後の遅延読込が可(**未決**)。「開発中は先行読込不要」(R12)=開発中は後読みで可 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c#L220-L232 / https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L449-L457 |
| キーボード(TCA8418) | `m5stack,tca8418c`(I2C1 0x34、IRQ=GPIO27)、`tca8418_keypad_m5stack.c` | I2C1、M5IOE1(rest/LED)、input。udev ルールは `ID_PATH==platform-3f804000.i2c` を使い `/dev/input/cardputer-zero-internal` を作る | 終点の定義(15.1)が案 A なら必須、案 B なら終点後の遅延読込が可(未決。R12 は遅延読込を認めている)。udev 依存の記述が M5 側にある(16.3) | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L89-L107 / https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules |
| 音声(ES8389 系 codec) | overlay は `everest,es8390`(I2C 0x10)、`m5stack,cardputerzero-audio`(ASoC カード)、`simple-audio-amplifier`(enable=GPIO24)、HP 検出 GPIO17、I2S | I2C1、I2S クロック(fragment@0)、amp GPIO。`cardputerzero-audio.c` は 7.0 以降で `dapm` ポインタ化の分岐あり(6.18 は埋込側) | 起動に不要。**後読み向き**。ただしモジュール間依存(snd-soc 一式)が多い | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L70-L77 / #L336-L339 / #L379-L386 |
| RTC(RX8130) | `epson,rx8130`(I2C 0x32。CardputerZero overlay L82-84)。ドライバは rpi-6.18.y(@2341883)の `drivers/rtc/rtc-ds1307.c` L1164 の `.compatible = "epson,rx8130"` で、mainline の ds1307 が扱う(別名の `rtc-rx8130.c` は無い)。bcm2711_defconfig L1470 は `RTC_DRV_DS1307=m`。**M5 の `modules/rx8130` は `Makefile` と `rx8130-overlay.dts` のみで C ソースは無い**(@7551854 の tree。13.4A)=**必要なのはドライバではなくオーバーレイ(DT)**。なお単体の `rx8130-overlay.dts` は `reg = <0x68>`、CardputerZero overlay は `<0x32>` で食い違う(実機の値は未確認=UN-26) | I2C1 | 時刻が必要なアプリ次第。起動直後は後読みで可(見立て) | https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c / https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130 / overlay#L82-L84 |
| 電池ゲージ(BQ27220) | **v5 メイン overlay には無く**、別 overlay `bq27220_v5.dts`(`ti,bq27220`)+ `bq27xxx_battery{,_i2c}.c` | I2C1 | 後読み向き | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/bq27220-1.0/bq27220_v5.dts#L14 |
| IMU(BMI270 + BMM150) | 別 overlay `bmi270_overlay.dts` / `bmi270_bmm150_overlay.dts`(`bosch,bmi270`)。ファームウェア `bmi270-init-data.fw` が同梱。upstream に `drivers/iio/imu/bmi270` あり | I2C1、`.fw` ロード | 後読み向き | https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/imu-1.0 |
| powerfail_suo | `cardputerzero,powerfail-suo`(IRQ=GPIO6 falling、backlight、disabled-gpio=M5IOE1) | M5IOE1、GPIO6 | **電源断対策で早期に必要になり得る**(18 章) | overlay#L289-L295 |
| gpio-forwarder / LED | `m5stack,gpio-forwarder`(GPIO22)、gpio-leds(G4 等) | M5IOE1 の一部 | 後読み可 | overlay#L345-L372 / #L490-L498 |
| Wi-Fi(2.4GHz 802.11b/g/n)/ BT | 公式 docs に記載。upstream `brcmfmac` ドライバは RPi ツリーに存在(Makefile で確認)。ファームウェア blob の取得元・同梱は**未確認** | SDIO/UART、firmware | 後読み向き | https://docs.m5stack.com/en/CardputerZero / https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/wireless/broadcom/brcm80211/brcmfmac/Makefile |
| Ethernet(SR9900A, USB) | USB ハブ(GL852G)の USB1 に SR9900A。**Host/Slave スイッチが Slave だとハブごと切断され Ethernet 不可**。USB ID 0fe6:9900 は `r8152.c`(RTL8152 系)の ID 表にある(L10070、rpi-6.18.y @2341883)。sr9700.c は 0fe6:9700/9702、sr9800.c は 0fe6:9800 のみ。bcm2711_defconfig は `USB_RTL8152=m`・`USB_NET_SR9700=m`・`USB_NET_SR9800=m`。**M5 docs は「SR9900A」としか書かず、実際の USB ID が 0fe6:9900 かは未確認** | USB(dwc2 or dwc_otg)、hub、firmware 不要かは未確認 | 後読み向き | https://docs.m5stack.com/en/CardputerZero(USB 2.0 節)/ https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/sr9700.c |
| カメラ(IMX219) | 公式 docs に IMX219 8MP。upstream `imx219.c` あり。M5 repo の camera overlay は GPIO16 を High にするもの(`camera-gpio16-high`)で、センサー本体の DT は RPi 標準 overlay 側と思われる(**未確認**) | CSI、unicam/libcamera 系 | 後読み向き(使うときだけ) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/i2c/imx219.c |
| IR(TX/RX) | 公式 docs に IR_TX / IR_RX(G13 系)。M5 repo に専用 overlay は見つからず。upstream `gpio-ir-recv.c` / `gpio-ir-tx.c` が存在 | GPIO | 後読み向き。DT の追加は自前になる可能性(推測) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/rc/gpio-ir-tx.c |

**依存の要点(一次の DT から)**:LCD・キーボード・powerfail は M5IOE1(I2C1)に連鎖する。したがって「LCD/キーボードは後読みで良い開発段階」と「終点(プロンプト+キー入力可)に必要な量産段階」で、built-in にする集合が変わる。built-in 化するなら `I2C1 → M5IOE1 → (PWM backlight) → SPI0 → panel → tca8418 → input` の鎖(見立て)。

### 14.4 遅延読込の仕組み(カーネル側の一次情報)
- `initcall_debug` / `initcall_blacklist=` / `initramfs_async=` はカーネルパラメータとして文書化されている(https://docs.kernel.org/admin-guide/kernel-parameters.html)。【一次】
- 起動後の modprobe 運用では、overlay(DT)はファームウェアが起動前に適用するため、**DT 上のデバイスは存在するがドライバ未ロード**の状態になる。ドライバを後でロードすると `deferred probe` の対象になる(7.1 で `CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT` が新設:v3/6.18 比較資料の A4)。待ち時間への影響は未測定=推測。
- 【作成者の見立て】Wi-Fi/音声/IMU/カメラ/IR/Ethernet は「終点の後」に systemd の依存順で後読み(または BusyBox 系なら終点後に自前スクリプト)にするのが素直。実際の削減量は実機の `initcall_debug` で上位を見て決める。

## 15. 起動の終点定義と測定手法(提案 2)

> 11 章との対応: 11.1(測定)、11.3 D1・11.4(11.5 に対応表)

### 15.1 終点の定義(**未決。v4 で終点をユーザーの要件と書いたのは誤りで、ユーザー発言に終点の定義は無い**)
ユーザー発言(R1、R11、R12)にあるのは「起動時間を最短に」「LCD・キーボードは開発中は先行読込不要(遅延読込可)」であり、「終点=LCD にプロンプト+キー入力可」とは言っていません(0 章 R12 と衝突)。終点は事前に固定しないと比較不能になる(6.18 比較資料の手順 6 と同じ)ため、**次の案から山城さんに選んでいただく**(11.3 D1、11.4):

| 案 | 終点 | 利点 | 欠点・衝突 |
|---|---|---|---|
| **A** | LCD にシェルのプロンプトが表示され、かつキー入力が受け付けられる時点 | 体感に直結 | M5IOE1→バックライト→LCD→キーボードの鎖を終点前に読む必要。R12(遅延読込可)・R11(極限まで小さく)と相反 |
| **B** | init(PID1)が終点マーカー(例:`/run/boot-done`)を書く時点。LCD/キーボードは終点後に遅延読込 | R12 に沿い、14.3 の built-in 集合を小さくできる | 体感(プロンプトが出る時刻)とずれる。体感は別指標として併記する |
| **C** | A と B の両方を測り、差を「遅延読込の効果」として記録 | 比較材料が増える | 測定の手間が増える |

【作成者の見立て=推測、未実施】A の機械的な判定案:
- E1:`/dev/input/event*`(内蔵キーボード)が出現し、かつ getty/シェルが当該 tty を open した時刻をタイムスタンプ化(`/proc/uptime` を使う軽い自作ログ)。
- E2:プロンプト文字の描画完了は外部測定(スマホのハイスピード撮影で電源投入〜プロンプトを計る)が最も確実。LCD 更新の遅延が内部時刻に出ないため。
- 内部時刻(E1)と外部測定(E2)の差が「LCD 描画遅れ」。両方を記録する。
- B の判定:終点マーカーの時刻(`/proc/uptime`)+外部測定(電源投入〜マーカー相当の GPIO トグル。KittenLabs は GPIO トグルで測定=22 章)。
どの案でも、測定条件(始点=電源投入、`console=`・quiet の有無)を固定する。

### 15.2 測定ツール

| 手法 | 事実 | 出典URL | 確認度 |
|---|---|---|---|
| `initcall_debug` | カーネルパラメータ。initcall 実行をトレース | https://docs.kernel.org/admin-guide/kernel-parameters.html | 一次 |
| `printk.time=1` / `CONFIG_PRINTK_TIME` | printk 各行に時刻を付ける(bcm2711_defconfig は `PRINTK_TIME=y`) | https://docs.kernel.org/admin-guide/kernel-parameters.html / https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1778 | 一次 |
| `scripts/bootgraph.pl` | `dmesg \| perl scripts/bootgraph.pl > out.svg`。`initcall_debug` を付けた dmesg から initcall の SVG を作る | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33 | 一次 |
| `systemd-analyze` | `blame` / `critical-chain` / `plot`(SVG)。「blame は並列起動のため待ち時間を反映しない」旨の注意が man にある。さらに **`Type=simple` のサービスは即時起動扱いのため blame に出ず(測定不能)**、キュー待ちも含まれない(man、13.4A V9A-004) | https://man7.org/linux/man-pages/man1/systemd-analyze.1.html | 一次 |
| bootchart(ユーザー空間) | systemd-bootchart の man7 ページは 404(今回取得できず)。**bootchart の一次情報は未取得** | (取得失敗:https://man7.org/linux/man-pages/man1/systemd-bootchart.1.html → HTTP 404) | 未取得 |
| strace | 実使用のシステムコール/ファイル open の洗い出しに使う(man) | https://man7.org/linux/man-pages/man1/strace.1.html | 一次 |
| ブート時 ftrace | カーネルパラメータ/bootconfig でブート時から tracing を有効化できる | https://docs.kernel.org/trace/boottime-trace.html / https://docs.kernel.org/admin-guide/bootconfig.html | 一次(存在)/ CM0 での有効性は未確認 |
| RPi 公式の区間分割 | EEPROM → GPU FW → カーネル展開・初期化 → initramfs → rootfs mount → systemd(RP-010196。CM0 に EEPROM は無い=区間が異なる点に注意) | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 二次(v3 時点で内容は部分確認) |

### 15.3 再現性(作成者の見立て=推測、未実施)
- 固定:同一個体・同一 SD・同一 firmware/bootcode・同一 cmdline。変えるのは 1 要素だけ。
- コールドブート N≥15、**1 回目は別扱い**、中央値と p90 を記録。電源は同一(バッテリ残量・USB 給電の別を固定)。
- 測定ビルドと量産ビルドの差(printk/initcall_debug の出力量自体が時間を伸ばす)を明記。シリアル出力はコンソール速度が起動時間に影響するため、**測定時のコンソール設定を固定**(`console=` と quiet の有無)。
- 数値の条件(機種・カーネル・始点終点)を必ず併記し、他条件と合成しない(本レポートの方針)。

## 20. 6.18 以降の起動時間変更・カーネル比較・PREEMPT(提案 7)

> 11 章との対応: 11.3 D5(カーネル版)(11.5 に対応表)

### 20.1 起動時間（6.18 以降の変更。確認度は原資料のまま）
- **結論**:BCM2837 級 arm64 で「6.18 以降に起動が速く/遅くなった」と実測した情報は**見つからなかった**(Phoronix 7.0〜7.3 は性能記事中心)。
- 起動時間に効きうる変更は少なく、多くは条件付き(RT のみ・eMMC のみ・x86/大メモリ向け)か未マージ:
  - printk スレッド化の「console_lock を record ごとに解放」は **RT 限定**(printk-for-6.19 pull 文面。一次):https://lkml.iu.edu/2512.0/00981.html → 非 RT の CM0 には**効かない可能性が高い(推測)**。
  - 7.3:`printk: Postpone kthread startup`(NBCON printer kthread を subsys_initcall へ)=安定化。https://www.phoronix.com/news/Linux-7.3-KThreads-NBCON(二次)
  - 7.1:`deferred_probe_timeout` を Kconfig 化(`56e3ee721b33`、一次):https://github.com/torvalds/linux/commit/56e3ee721b33
  - MMC:`bcm2835.c`(sdhost)は 6.18→7.2 で差分 0(7.2→7.3-rc7 で 36 行の DMA デバイス取得変更)。tuning/CMD1 ポーリングの短縮提案(2026-09)は**未マージ**かつ eMMC/dw_mmc 向けで SDHCI 標準経路は対象外(https://lkml.iu.edu/2609.2/00512.html)。
  - init_on_alloc 一括クリア(7.2。数値は **AMD 送信・16GB HugeTLB 条件**:0.445s→0.166s。CM0 に当てはめ不可):https://www.spinics.net/lists/kernel/msg6184200.html
  - 「mmc: core: Optimize boot time by detecting cards simultaneously」は **2015 年のコミット** で 6.18 以降の変更ではない。
- 外部の起動時間報告(x86、CM0 に外挿不可。原因がカーネル回帰とは限らない事例):**Omarchy #6996**(Omarchy 4.0.0-1 / Linux 7.1.8-arch1-3、AMD+NVIDIA 混在機。約 266MiB の initramfs と `initramfs_async=0`。`1min 15.918s (kernel)`。2026-08-15 作成、取得時 open)https://github.com/omacom/omarchy/issues/6996 (リポジトリ移転済み。旧 URL は HTTP 404)。**CachyOS**(7.2 カーネルで graphical.target @1min 32.184s、6.18.48-1-cachyos-lts は @8.960s、x86)https://discuss.cachyos.org/t/7-2-kernel-boot-times-drastically-slower-than-6-18-lts/35306 :critical-chain に `cryptsetup.target` があり、**投稿者は後に「BIOS で TPM を無効にして解消」と報告(2026-09-10)**。7.2 カーネル自体の回帰と断定できない【二次・ユーザー報告】
- 調査範囲の限界(原資料):kernelnewbies 7.3 は後半未読、LWN 個別記事の精読は一部のみ、clone による全文 `git log` 検索は未実施、乱数サブシステムの 6.18 以降の変更は未調査。

### 20.2 カーネル比較（6.18 対 7.x）
| 項目 | 内容 | 確認度 |
|---|---|---|
| RPi 公式既定 | `rpi-6.18.y`(6.18.57、リポジトリ既定ブランチ)。RPi OS Trixie 2026-10-06 イメージは 6.18.50(【**確認済み**】 公式 release_notes.txt の 2026-10-06 の項。V9A-002)。`rpi-7.2.y`=7.2.11、`rpi-7.3.y`=7.3.0-rc7(いずれも 2026-10-18 時点) | 一次 |
| M5 ドライバ互換 | **7.1 で `drm_simple_display_pipe` 系/`mipi_dbi_dev_init_with_formats` 等が削除**され、M5 の `panel-mipi-dbi-m.c` は 7.2 ではそのままでは API 不整合(ヘッダに存在しない関数 6 個)。7.0 で `snd_soc_dapm_kcontrol_component/dapm` の別名が削除され `es8389_m5stack.c` が影響。**ビルド可否は未確認(API 存在確認のみ)** | 一次(API 存在確認まで) |
| 起動時間(6.18 vs 7.2/7.3) | 同条件の公表実測は見つからず。ソース差分:SD ホスト(bcm2835 sdhost)・KASLR・圧縮展開コードは 6.18→7.2 で差分 0 | 一次(差分の有無)/ 推測(速度影響) |
| 運用 | 7.0/7.1 は約 11 週で EOL(Wikipedia、二次)。6.18 LTS は予定 EOL 2028-12(kernel.org)。次の LTS 候補 7.4 は kernel.org が事前に公表しない | 一次/二次 |
| 作成者の見立て | **本番基準は 6.18.y。7.2 は同一構成での比較用**。7.3 final 後または LTS 化された 7.4 を狙う。差(中央値 −300ms 以上等)が出たら移行検討(閾値は仮置き) | 推測 |
- 7.3 final は 2026-10-18 公開予定と報じられるが、取得時点で未確認。

### 20.3 PREEMPT の確認結果(今回、clone のソースで再確認)
| カーネル | 事実 | 出典URL(コミット固定) |
|---|---|---|
| **6.18**(K618) | `Kconfig.preempt` の選択肢 `default PREEMPT_NONE`。`PREEMPT_VOLUNTARY` は `depends on !ARCH_NO_PREEMPT` と `!PREEMPT_RT` のみ。**arm64 の Kconfig は `ARCH_NO_PREEMPT` を select していない**(grep で該当なし)ため **VOLUNTARY は選択可能**。RPi の `bcm2711_defconfig` は `CONFIG_PREEMPT=y`(VOLUNTARY ではない) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt#L17-L52 / https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 |
| **7.2**(K72) | 既定は `default PREEMPT_LAZY if ARCH_HAS_PREEMPT_LAZY`(arm64 は `select ARCH_HAS_PREEMPT_LAZY`、arch/arm64/Kconfig L44)。`PREEMPT_NONE` は **`depends on ARCH_NO_PREEMPT`**、`PREEMPT_VOLUNTARY` は **`depends on !ARCH_HAS_PREEMPT_LAZY`**。arm64 は LAZY を持つので **NONE も VOLUNTARY も選べない**(FULL/LAZY のみ) | https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt#L17-L45 / https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig#L44 |
- 帰結(【作成者の見立て】):起動時間のために VOLUNTARY/NONE を使いたいなら **6.18 系に留まる必要がある**。7.2 以降は PREEMPT_LAZY(または FULL)固定。**VOLUNTARY が起動時間に有利かは未測定**(推測)。ユーザー方針どおり PREEMPT_RT は不採用。
- 注意:7.2 のツリーに `bcm2711_defconfig` は sparse clone の範囲外のため、7.2 の RPi defconfig の PREEMPT 値は今回未確認(6.18 比較資料では両版とも `PREEMPT=y` と記載=原資料)。
- 7.0 の preempt モデル制限(コミット `7dadeaa6e851`)の外部報告:Graviton4(96vCPU)で pgbench 0.51x(スループット。**起動時間ではない・CM0 に不適用**)、LWN は「実は回帰ではない」と整理 https://lwn.net/Articles/1067029/ (二次)。

### 20.4 printk 方針
- 原資料の結論と 14.2 を合わせ、**測定ビルド:PRINTK=y(`initcall_debug`・`printk.time=1`)/ 量産ビルド:`quiet`+低 loglevel、PRINTK=n は別バイナリで試すのみ**(見立て=推測)。
- 6.19 の printk 改善は RT 限定の記述であり、非 RT の CM0 には効果が見込みにくい。7.3 の NBCON kthread 起動遅延は安定化目的で、コンソール出力開始が遅れる可能性は**推測**(測定なし)。

### 20.5 リスク:arm64 linear alias unmap 変更(v5 で GitHub API により確認)
一次(GitHub compare API / commit API、2026-10-18):
- **63e0b6a5b693**(2026-06-02、「kernel data/bss の線形エイリアス unmap」)と、その **revert f102131c842d**(2026-06-10)は**ともに v7.2-rc1 に含まれ**、v7.2・v7.3-rc1 にも含まれる(= v7.2 では「導入+revert」で差し引きなし)。revert のメッセージ:「Unmapping the kernel '.bss' appears to break KVM initialisation on some devices, breaking the boot on popular platforms such as RaspberryPi3 and 4」。
- **再適用 fb0f3ef5601a**(2026-08-07)は **v7.3-rc1 にのみ**入る(v7.2-rc1 より後、v7.2 とは分岐、v7.3-rc1 より前)。メッセージはハイバネーション時の map/unmap 処理を追加する内容で、**KVM の問題が解消した旨は書かれていない**。
- RPi ツリー:`rpi-7.2.y` の mmu.c は「Map the kernel data/bss read-only」の旧コード(影響なし)。`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid` と PM notifier)を含む。
- **CM0(BCM2837、Cortex-A53)で 7.3 系(再適用後)が起動するかは未確認**。revert メッセージは RPi 3/4 を挙げている(BCM2837 は RPi 3)ので、7.3 採用時は「起動確認を最初の実機試験に置く」(推測)。7.2 系は上記の理由で当該リスクを持たない(7.2 にその他の CM0 固有の問題が無いことは別途未確認)。

## 22. 既存 idea 資料の取り込み(提案 8)

出典:事前資料(同日作成の別資料。確認度は原資料のラベル【確認済み】【報告】【推測】を維持)。v4 では項目の所在のみ整理し、各項目の詳細は原資料を参照してください。**原資料の本文は再検証していません**。

| 原資料の項目 | v4 での扱い(取り込み先) |
|---|---|
| F-1 config.txt 最適化(boot_delay, disable_splash 等) | v3 5.3 節に既出。`disable_fw_kms_setup` 等の BCM2837 での有効性は**未確認**のまま |
| F-2 DTB 最小化 | 14 章(カーネル縮小)。furkantokac(Pi3 の単一ブログ実測=条件固有、合成不可) |
| F-3 initcall 非同期化・モジュール化 | 14.3/14.4 と 15 章 |
| F-4 initramfs 非同期展開 | 20.1(`initramfs_async` は kernel-parameters に記載あり。メインライン化は 2021 の e7cb072eb988。**Victron 由来の説明は古い**) |
| F-5 GPU ロード=kernel サイズが鍵(【**推測**】。比例関係は未確認。5.2 の注) | 14.2 の無圧縮 vs gzip(KittenLabs。9,276,375B を 1.54s=約 5.74MiB/s の計算値、ブログは約 6MiB/s。Raspbian 標準 kernel8.img・Zero 2 W。単一ブログ) |
| F-6 rpi-open-firmware/U-Boot Falcon | 優先度低(原資料の判断。【報告】) |
| F-8 LCD 先行点灯 | **ユーザー要件(スプラッシュ不要・開発中の先行読込不要)により不採用**。14.3 の依存鎖のみ参考 |
| F-9 init 直起動 / s6・runit | 16.2 |
| F-10 EROFS(LZ4)+配置最適化 | 16.4(c) |
| F-11 静的リンク/LTO/UPX | 16.1・17 章 |
| F-12/13/14 ネット遅延・readahead 等 | 16.3・16.4(b) |
| P-1/P-2 電断検知(SW_DET, BQ27220 GPOUT) | 18 章・v3 6.3(powerfail_suo)。**GPIO6**:公式 docs の SW_DET=G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`(L292-293、falling)は同じ GPIO6 で食い違いなし(一次)。GPIO6(CM0 側)は SW_DET。M5IOE1 側の PYG6 は MIC_SW(別物)で、powerfail_suo の `<&m5ioe1 11 1>` が PYG12(LCD_RST)に当たるかは index の推論で未確認(UN-25) |
| P-3 RW 極小化+ext4 data=ordered | v3 6.5・19.2 |
| P-4 アトミック書込み | 21.4・18.1 |
| P-5 PLP 付き SD(UCSD 論文 DAC2011 ほか) | v3 6.4 と併読。pSLC は eMMC 向けで microSD には不可(RP WP)。ベンダ主張は未検証 |
| P-7 dm-verity | CM0 に AES/SHA 命令なし(21.1)→SHA256 のソフト実装コストが読込に乗る(推測)。「A/B 切替時のみ全検証」案 |
| P-9 WDT/boot counter/最小回復イメージ | 18 章(ただし**回復モードは不要**というユーザー要件により「最小回復イメージ」は不採用) |
| P-10 電断試験手法(dm-flakey, dm-log-writes, CrashMonkey) | v3 6 章・19.3 |
| P-11 スーパーキャパ | 筐体設計上ほぼ不可(原資料の推測) |
