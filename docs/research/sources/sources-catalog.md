# 出典一覧

sources.md から分割した出典記録です。

### 出典一覧

| ID | URL | 取得日 | 確認度 | 備考 |
|---|---|---|---|---|
| AUD | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c#L25 | 2026-10-18 | 確認済み | KERNEL_VERSION(7, 0, 0) 分岐 |
| AUTOB | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60 | 2026-10-18 | 確認済み | tryboot/autoboot.txt([all]/[tryboot]、L36 tryboot_a_b、L58-L60 例) |
| BENCH | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L14 2112ms/227KB、L18 2.26s、L21 ~7-9s、L64 config.txt 最適化でも 2112ms(#L64)。自己申告文書 |
| BFE | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc | 2026-10-18 | URL 到達確認のみ(HTTP 200。該当箇所は本文未確認) | EEPROM 起動の文書 |
| BOOTA | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | arm_64bit の対応モデル表(Zero 2 W/CM3/CM3+/CM4/CM4S。CM0 の記載なし)、L22 kernel 既定名 |
| BRC | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1 | 2026-10-18 | 確認済み(HTTP 200。HEAD d5180309) | Buildroot 2026.08 系 |
| CBAPI | https://api.github.com/repos/CardputerZero/circle-boot-splash | 2026-10-18 | 確認済み(API GET。archived=true、pushed_at=2026-05-14T09:39:49Z) | ARCHIVED の根拠 |
| CFG | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12 | 2026-10-18 | 確認済み | L12 fbtft st7789v、L32 vc4-kms-v3d、L58 cardputerzero-overlay |
| COND | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43 | 2026-10-18 | 確認済み | [cm0] フィルタ |
| CZOS404 | https://github.com/CardputerZero/cardputer-zero-os | 2026-10-18 | 確認済み(curl -sI で HTTP 404、2026-10-18。shell 側も 404) | URL の 404 を確認 |
| CZVIC | https://github.com/vicliu624/cardputer-zero-os | 2026-10-18 | 確認済み(HTTP 200。HEAD 7d9b078) | 第三者ミラー/fork(中身は部分的にのみ確認) |
| DEF | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L467 ZRAM=m、L468 ZRAM_BACKEND_LZ4=y、L469-473 ZSTD/LZO/DEF_COMP_ZSTD/WRITEBACK/MULTI_COMP、L86 ZSWAP=y、L10 PREEMPT=y、L513 DM_VERITY=m、L1110 DRM_VC4=m、L1115 DRM_PANEL_MIPI_DBI=m、L1135 FRAMEBUFFER_CONSOLE_ROTATION=y、L1470 RTC_DRV_DS1307=m、L1641 F2FS_FS=y、L1650 OVERLAY_FS=m、L1671-L1675 SQUASHFS、L1679-L1680 EROFS |
| DOC_EN | https://docs.m5stack.com/en/CardputerZero | 2026-10-18 | 確認済み(HTTP 200。本文確認済み) | 公式 docs(英) |
| DOC_JA | https://docs.m5stack.com/ja/CardputerZero | 2026-10-18 | 確認済み(HTTP 200。本文確認済み) | 公式 docs(日) |
| DTS3 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90 | 2026-10-18 | 確認済み | rest-gpios 記述(L90) |
| DTS5 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100 | 2026-10-18 | 確認済み | rest-gpios 記述(L100) |
| EEP541 | https://github.com/raspberrypi/rpi-eeprom/issues/541 | 2026-10-18 | URL 到達のみ確認(HTTP 200)。内容は未読 | rpi-eeprom issue #541 |
| FW1635 | https://github.com/raspberrypi/firmware/issues/1635 | 2026-10-18 | URL 到達のみ確認(HTTP 200)。内容は未読 | raspberrypi/firmware issue #1635 |
| GCC | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L6 既定 `BR2_GCC_VERSION_15_X`、L64 15.3.0 |
| GF | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c#L204 | 2026-10-18 | 確認済み | KERNEL_VERSION(6, 18, 0) 分岐 |
| GHORG | https://api.github.com/orgs/CardputerZero | 2026-10-18 | 確認済み(API GET。public_repos=33) | org 概要。リポジトリ一覧: https://api.github.com/orgs/CardputerZero/repos |
| IMGJSON | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json | 2026-10-18 | 確認済み(HTTP 200 + JSON 確認:Ubuntu Core 26(64-bit) 2026-06-05 と Ubuntu Server 26.04.1 2026-08-26 は pi5/pi4/pi3-64bit) | Raspberry Pi Imager の OS 一覧 |
| IOE | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c#L472 | 2026-10-18 | 確認済み | KERNEL_VERSION(6, 18, 0) 分岐 |
| KORG | https://www.kernel.org/releases.json | 2026-10-18 | 確認済み(HTTP 200 + JSON 確認:mainline 7.3-rc7=2026-10-12、stable 7.2.11=2026-10-15、longterm 6.18.57=2026-10-15、6.12.113=2026-10-15) | EOL 予定 2028-12 は未確認 |
| KS403 | URL未取得(kickstarter.com は HTTP 403。トップ階層 /projects/m5stack を試したが 403 で、ページの実在は確認できていない) | 2026-10-18 | 取得不可(HTTP 403)。プロジェクト個別 URL・更新 URL(posts/4829886)は確認できず | Kickstarter の期間・支援者数・金額・価格・更新 13 は未確認 |
| M5REPO | https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20 | 2026-10-18 | 確認済み(HEAD 7551854、コミット日 2026-09-23) | リポジトリ全体(obj-m 方式・dkms.conf の有無など、ツリー単位の事実) |
| MAN | https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/static/pdf/static/en/CardputerZero.pdf | 2026-10-18 | URL 到達のみ確認(HTTP 200)。内容は未読 | docs ページ内の PDF リンク |
| MEN | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 | 2026-10-18 | 確認済み | MENDER_VERSION = 3.5.3 |
| MENDOC | https://docs.mender.io | 2026-10-18 | URL 到達のみ(HTTP 200) | Mender docs トップ |
| MK | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L67 | 2026-10-18 | 確認済み | config_setup が gist から rpi-config.py を curl(L67) |
| MRC | https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a | 2026-10-18 | URL 到達のみ確認(HTTP 200)。内容は未確認 | meta-rauc-community |
| PF | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L93 handle_sysrq('u')、L74/L83 は ’i’/’s’ がコメントアウト、L3-L9(先頭コメント。S は L7、U は L8、O は L9)と L250(MODULE_DESCRIPTION)は S-U-O の記述。先頭コメント: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L3-L9 / MODULE_DESCRIPTION: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L250 |
| PGB | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L36 | 2026-10-18 | 確認済み | L36 vc4-kms-v3d,cma-64、L20 dtoverlays を --depth=1 で clone、L31 CONFIG_CARDPUTERO_V0_5=y |
| PGC | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247 | 2026-10-18 | 確認済み | cmdline に quiet fbcon=map:off cfg80211.ieee80211_regdom=AE |
| PGCI | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml#L52-L54 | 2026-10-18 | 確認済み | FIRST_USER_NAME=pi / FIRST_USER_PASS=raspberry / ENABLE_SSH=1(L52-L54、L255-L257 にも) |
| PGCM | https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc | 2026-10-18 | 確認済み(HTTP 200。API でコミット日 2026-10-08T11:15:57Z=JST 20:15 を確認) | pi-gen HEAD 791a985(branch cardputerzero_v1.0) |
| PGH | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32 | 2026-10-18 | 確認済み | apt-mark hold(L32)、--allow-change-held-packages(L29) |
| PGK | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3 | 2026-10-18 | 確認済み | Pin: version 1:6.18.39-1+rpt1(L3)、Pin-Priority 1001(L4) |
| PGS | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel-packages.sha256 | 2026-10-18 | 確認済み(HTTP 200 + ファイル存在) | sha256 一覧(検証処理の実装行は未特定) |
| PKG | https://github.com/CardputerZero/packages | 2026-10-18 | 確認済み(HTTP 200) | apt リポジトリ。ほか https://github.com/m5stack/CardputerZeroRepository 、https://github.com/CardputerZero/launcher 、https://github.com/CardputerZero/Template 、https://github.com/CardputerZero/m5stack-imager も HTTP 200 |
| QPC | https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5 | 2026-10-18 | 確認済み(HTTP 200。コミット日 2018-01-05T16:13:45+01:00) | 最終コミット |
| QPR | https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L15 『plug in to login prompt around 5.5 seconds』 |
| PI3CFG | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig#L12-L13 | 2026-10-18 | 確認済み | 同上(同一コミット固定) |
| RAUCPR | https://api.github.com/repos/rauc/rauc/pulls/1599 | 2026-10-18 | 確認済み(API GET。state=open、merged=false、題名『bootchooser: add Raspberry Pi firmware initial support』) | PR ページ: https://github.com/rauc/rauc/pull/1599 |
| RAUCREL | https://api.github.com/repos/rauc/rauc/releases/latest | 2026-10-18 | 確認済み(API GET。v1.15.2=2026-03-27T10:47:01Z) | RAUC の最新リリース |
| RIG153 | https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153 | 2026-10-18 | 確認済み(API GET。closed、closed_at 2026-02-18T10:07:14Z、題名『Documentation for image-rota and device compatibility』) | 旧版が根拠にした issue |
| RIGDEV | https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device | 2026-10-18 | 確認済み(device 配下に cm4/cm5/pi3/pi4/pi5/zero2w) | device 層 |
| RIGMBR | https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual | 2026-10-18 | 確認済み | MBR レイアウト(layer 名 image-rpios) |
| RIGREL | https://api.github.com/repos/raspberrypi/rpi-image-gen/releases | 2026-10-18 | 確認済み(API GET。最新 v2.8.0=2026-08-13T14:26:12Z UTC、v2.7.0=2026-06-26) | rpi-image-gen のリリース |
| RLC | https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa | 2026-10-18 | 確認済み(HTTP 200。branch rpi-6.18.y の HEAD、コミット日 2026-10-16T16:36:30+01:00) | rpi-6.18.y HEAD 2341883 |
| RLMK | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4 | 2026-10-18 | 確認済み | VERSION=6 / PATCHLEVEL=18 / SUBLEVEL=57 |
| ROTA | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11 | 2026-10-18 | 確認済み(HTTP 200 + 該当行確認) | L2 レイヤ名 image-rota、L11 regex `^(cm4\|pi4\|cm5\|pi5)$`、L34-L41 rootfs erofs/zstd |
| ROTAC | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml | 2026-10-18 | 確認済み(device: rpi5 を確認) | 例設定 |
| ROTAH | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L42 | 2026-10-18 | 確認済み | autoboot.txt 生成(tryboot_a_b=1 は L42) |
| RTC | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L118 | 2026-10-18 | 確認済み | RX8130 レジスタ定義(L118-L119) |
| RUG | https://api.github.com/repositories/642546697/releases | 2026-10-18 | 確認済み(API GET。v1.3.0=2026-08-05T05:05:29Z) | silitics/rugix。API は旧 URL から 301 で遷移 |
| RUGD | https://rugix.org/docs/bakery/devices/ | 2026-10-19 | 【一次】確認済み | Pi 5/Pi 4（Tier 1）/CM4（Tier 2）= `rpi-tryboot`。Pi 3/Zero 2 W（Tier 2）、Pi 2 v1.2/Pi 2/Pi 1/Zero（Tier 3）= `rpi-uboot` |
| RUGP | https://rugix.org/docs/bakery/devices/raspberry-pi | 2026-10-19 | 【一次】確認済み | Pi 5/Pi 4/Pi 400/CM4 以外は `rpi-uboot` を使う。U-Boot flow は実験的で Raspberry Pi bootloader/firmware を更新できない |
| RPBOOT | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91 | 2026-10-19 | 【一次】確認済み | “All Raspberry Pi models support `tryboot`” |
| SCH | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 2026-10-18 | 確認済み(HTTP 200。PDF 本文に HDMI/G6_SW_DET 等の記載) | 回路図 V0.6.1(2026-07-02)。ページ番号(P10 J5)の再照合は未実施 |
| SKU | https://docs.m5stack.com/en/products/sku/C154 | 2026-10-18 | 確認済み(HTTP 200。今回ページ内リンクから回路図 PDF の URL を抽出) | 製品ページ(C154) |
| SWU | https://api.github.com/repos/sbabic/swupdate/releases/latest | 2026-10-18 | 確認済み(API GET。2026.05.1=2026-06-22T07:54:11Z) | SWUpdate の最新リリース |
| UBOOT | https://github.com/CardputerZero/u-boot | 2026-10-18 | URL 到達のみ確認(HTTP 200)。作成日 2026-06-11 は今回未確認 | org の u-boot |
| WPB | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 2026-10-18 | 確認済み(PDF 取得、pdftotext で本文確認。Release 1) | 付録の Pi 3B+ ログに『MESS:00:00:06.790801 Watchdog stopped / 06.794412 arm_loader: Starting ARM』を確認=ARM 開始 約 6.79s。CM5 約 7s・initramfs/カーネルサイズの条件は未再確認 |
| WPF | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf | 2026-10-18 | 確認済み(HTTP 200。本文に Release 2・Build date 07/08/2026 とあり、URL の「WP-3」と版表記が一致しない) | data=ordered/metadata_csum/SquashFS・EROFS/overlayfs/F2FS の記述、CM0 を含む対応表(L97)を確認 |
| XCM0 | https://x.com/M5Stack/status/2110949681601871946 | 2026-10-18 | 確認済み(X API で取得。2026-10-16T04:23:18Z=JST 13:23、本文『The first batch of CM0 arrived.』) | @M5Stack の投稿。製品出荷開始ではない |
| XKLP | https://x.com/Rw7DVtscPX/status/2111293684952289420 | 2026-10-18 | 確認済み・二次(X API。2026-10-17 の第三者投稿。Klipper が CardputerZero で動作との記述) | @Rw7DVtscPX |
| XSAI | https://x.com/saitotetsuya/status/2111008950107910198 | 2026-10-18 | 確認済み・二次(X API。2026-10-16 の第三者投稿『最初のバッチが3,000，次が12,000か』+ Kickstarter 更新へのリンク(t.co 短縮のため遷移先は未展開)) | Kickstarter 本文は未確認 |
| XZR | https://x.com/HarrisonXu1998/status/2111387043775512697 | 2026-10-18 | 確認済み・二次(X API。2026-10-17、ZeroRadio が CardputerZero Store にある旨と Dirtywave M8 風アプリ) | @HarrisonXu1998 |
| YKR | https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d/recipes-kernel/linux | 2026-10-18 | 確認済み(API で linux-raspberrypi_6.18.bb 等を確認) | recipes-kernel/linux |
| YLC | https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf#L12 | 2026-10-18 | 確認済み(raw で LAYERSERIES_COMPAT_raspberrypi = "wrynose" を確認) | L12 |
| YML | https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf | 2026-10-18 | 確認済み(HTTP 200。wrynose ブランチの取得時点 HEAD 9195883、コミット日 2026-10-02T15:44:55Z) | GitHub API/URL で確認。同ブランチの最新コミットは 2026-10-10 でありこの固定ハッシュとは別(要注意) |
| Z2W | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig#L11-L12 | 2026-10-18 | 確認済み(カーネルはコミット 21b41014… のタールボール固定) | カーネル「6.12.61」という版表記は defconfig では確認できません。公開 tarball の内容確認が必要です |
| Z44 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi | 2026-10-18 | 確認済み(HTTP 200。tag v4.4.0 の HEAD 684c9e8。boards/raspberrypi に rpi_zero_2w がないことをディレクトリ一覧で確認) | 『存在しないこと』は URL 単体では示せない。ディレクトリ一覧で不在を確認 |
| Z44T | https://github.com/zephyrproject-rtos/zephyr/releases/tag/v4.4.0 | 2026-10-18 | 確認済み(HTTP 200) | タグの存在 |
| ZM | https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w | 2026-10-18 | 確認済み(HTTP 200。HEAD a915b2f、コミット日 2026-10-16T15:53:07-05:00) | upstream main の rpi_zero_2w ボード |
| ZPR | https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 | 2026-10-18 | 確認済み(API GET。state=closed、merged_at=2026-08-17T08:24:09Z、題名『boards: raspberrypi: add Raspberry Pi Zero 2 W』) | 『単コア+ミニ UART のみ/SDHCI 未対応』の記述は PR 本文を未読のため未確認 |

### 出典・取得記録の読み方

本文まで確認した出典には「一次」または「二次」を付け、URL への到達だけを確認した場合は「到達のみ」と記載しています。HTTP 403・404・接続不可、タイトルだけ取得できた項目は本文の根拠として扱いません。数値の出典や未確認事項は、各テーマの本文と出典表を参照してください。
