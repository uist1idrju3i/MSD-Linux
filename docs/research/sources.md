# 出典 URL と取得記録

- 取得日は全て 2026-10-18 (JST) です。各表には公開 URL、取得日、HTTP 結果、確認度を記載しています。
- 「確認済み」は、URL が HTTP 200 で、その内容または同一コミットの公開ソースで該当事項を確認したことを指します。HTTP 200 でも内容を読んでいない場合は「到達のみ」と記載しています。
- 二次情報(検索要約・SNS)は確認度欄に『二次』と付けています。
- 出典一覧の短縮 ID は、この文書内で出典を参照するためのものです。

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
| RUGD | https://rugix.org/docs/bakery/devices/ | 2026-10-18 | 確認済み。Pi 3 = rpi-tryboot、Zero 2 W = rpi-uboot | Rugix のデバイス表 |
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

### 本文を確認した URL
本文または該当行を読み、「該当」欄の内容を確認した URL です。コミット固定の raw URL は取得時のファイル内容です。日付は全て 2026-10-18 (JST) です。

| URL | HTTP | 該当(原文・該当行の要旨) | 確認度 |
|---|---|---|---|
| https://raw.githubusercontent.com/openssh/openssh-portable/V_10_5_P1/myproposal.h | 200 | KEX の先頭が `mlkem768x25519-sha256`、続いて `sntrup761x25519-sha512`、暗号の先頭が `chacha20-poly1305@openssh.com`(ファイルのリスト順) | 一次 |
| https://www.openssh.org/txt/release-10.0 | 200 | 「mlkem768x25519-sha256 is now used by default … considerably faster than the previous default」 | 一次 |
| https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/src/default_options.h | 200 | `DROPBEAR_CHACHA20POLY1305 1`、`DROPBEAR_ENABLE_GCM_MODE 0`、`DROPBEAR_SNTRUP761 1`、`DROPBEAR_MLKEM768 1`、コメント「sntrup uses ~9kB code size, mlkem uses ~34kB code size (32-bit armv7)」 | 一次 |
| https://raw.githubusercontent.com/mkj/dropbear/DROPBEAR_2026.94/CHANGES | 200 | 「These do increase code size, at least sntrup761 is recommended」 | 一次 |
| https://openvpn.net/community-docs/community-articles/openvpn-2-7-manual.html | 200 | `--data-ciphers` 既定 `AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305`、`--tls-groups` のマニュアル記載は「OpenSSL 1.1+ の既定 `X25519:secp256r1:X448:secp521r1:secp384r1`」(ML-KEM なし。実効既定は OpenSSL 版依存)、`--auth` 既定 SHA1 | 一次(マニュアルの記載内容のみ) |
| https://www.wireguard.com/protocol/ | 200 | ChaCha20-Poly1305・Curve25519・BLAKE2s・HKDF。PSK は「for, say, post-quantum resistance」 | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openssh/openssh.mk | 200 | `OPENSSH_VERSION_MAJOR = 10.5`、`OPENSSH_VERSION_MINOR = p1` | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/dropbear/dropbear.mk | 200 | `DROPBEAR_VERSION = 2026.94` | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/openvpn/openvpn.mk | 200 | `OPENVPN_VERSION = 2.7.6` | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-tools/wireguard-tools.mk | 200 | `WIREGUARD_TOOLS_VERSION = 1.0.20260223` | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/wireguard-linux-compat/wireguard-linux-compat.mk | 200 | `WIREGUARD_LINUX_COMPAT_VERSION = 1.0.20220627` | 一次 |
| https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 200 | 「boot into a Linux user space program in less than 3.5s」、「~400ms is spent in the Linux kernel」、カーネル 8.5MiB(非圧縮)、「Loading 9276375 Bytes takes about 1.54s」、「(self reported) boot time from 5.38s down to 4.75s」 | 二次(個人ブログの自己申告) |
| https://discuss.cachyos.org/t/7-2-kernel-boot-times-drastically-slower-than-6-18-lts/35306.json | 200 | 投稿者の後続投稿「Disabling TPM in BIOS “fixed” the issue for me」(2026-09-10)。critical-chain は `cryptsetup.target @1min 31.207s` を含み graphical.target @1min 32.184s(7.2)、6.18.48-1-cachyos-lts は @8.960s | 二次(ユーザー投稿) |
| https://api.github.com/repos/omacom/omarchy/issues/6996 | 200 | 題名「Linux 7.1 initramfs_async=0 causes ~76-second kernel phase on mixed AMD/NVIDIA system」、state=open、作成 2026-08-15、Omarchy 4.0.0-1 / Linux 7.1.8-arch1-3、`1min 15.918s (kernel)` | 二次(ユーザー報告) |
| https://docs.mender.io/release-information/supported-releases | 200 | 表に「Mender Client 6.1 / 2026-10 / Supported」 | 一次 |
| https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md | 200 | officially supported の構成一覧に `raspberrypi/uboot/debian/raspberrypi3_bookworm_64bit_config`(RaspberryPi 3, Raspberry Pi OS "bookworm" 64bit) | 一次 |
| https://raw.githubusercontent.com/plougher/squashfs-tools/db038ef265ed00bb17aaf695a72f9b0c3489eb20/squashfs-tools/sort.c | 200 | `sort_files_and_write` が `for(i = 65535; i >= 0; i--)` で優先度の高い順に処理(S_IFREG のみ追加) | 一次 |
| https://raw.githubusercontent.com/erofs/erofs-utils/f36cadb/man/mkfs.erofs.1 | 200 | `--sort` はタール入力用の inode データ順序。`-z` は圧縮アルゴリズムの指定 | 一次 |
| https://raw.githubusercontent.com/erofs/erofs-utils/f36cadb/mkfs/main.c | 200 | 圧縮は `-z` の処理経路(main.c 内で他の圧縮指定経路は見つからず)。`--MZ`、`-m#[:alg]`、`-C` のオプション処理 | 一次 |
| https://erofs.docs.kernel.org/en/latest/faq.html | 200 | 「LZ4 by default」は圧縮する場合の記述 | 一次 |
| https://api.github.com/repos/torvalds/linux/compare/fb0f3ef5601a...v7.3-rc1 | 200 | status=ahead(再適用 fb0f3ef5601a は v7.3-rc1 に含まれる) | 一次 |
| https://api.github.com/repos/torvalds/linux/compare/fb0f3ef5601a...v7.2 | 200 | status=diverged(再適用は v7.2 に含まれない) | 一次 |
| https://api.github.com/repos/torvalds/linux/compare/f102131c842d...v7.2-rc1 | 200 | status=ahead(ahead_by 17683、behind_by 0)=revert f102131c842d は v7.2-rc1 に含まれる | 一次 |
| https://api.github.com/repos/torvalds/linux/commits/f102131c842d | 200 | 「Unmapping the kernel '.bss' appears to break KVM initialisation on some devices, breaking the boot on popular platforms such as RaspberryPi3 and 4」 | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-7.2.y/arch/arm64/mm/mmu.c | 200 | 「Map the kernel data/bss read-only」(旧コード) | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-7.3.y/arch/arm64/mm/mmu.c | 200 | `mark_linear_data_alias_valid` と PM notifier を含む | 一次 |
| https://www.kernel.org/releases.json | 200 | mainline 7.3-rc7(2026-10-12)、stable 7.2.11、longterm 6.18.57 ほか | 一次 |
| https://ubuntu.com/blog/zephyr-lts-announcement | 200 | 題名「Canonical announces Zephyr 26.04 LTS, delivering up to 15 years of support for MCU-grade devices」、日付 21 September 2026 | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts | 200 | L14-16:`serial0 = &uart1;`、`serial1 = &uart0;` | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm283x.dtsi | 200 | uart1 は `brcm,bcm2835-aux-uart`、uart0 は `arm,pl011` | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/r8152.c | 200 | L10070:`{ USB_DEVICE(0x0fe6, 0x9900) },` | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile | 200 | L74 付近:`rpi-config.py --no-backup section-set all enable_uart 1` | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/tools/verify-image.sh | 200 | L158-161:cmdline に `console=serial0,115200` が残っていないことを検査 | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/docs/CARDPUTERZERO-IMAGE-DESIGN.md | 200 | L41:`console=serial0,115200` を保持する旨(スクリプトの挙動と食い違う) | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh | 200 | cmdline から `console=serial0,115200` を除去する処理 | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh | 200 | M5 の `make … config_setup` を実行 | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/export-image/04-set-partuuid/00-run.sh | 200 | cmdline の整形で `console=serial0,115200` を除去 | 一次 |
| https://raw.githubusercontent.com/raspberrypi/documentation/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/configuration/reference.adoc | 200 | L1408:`enable_uart=1` implies `core_freq=250`(`force_turbo=1` を除く) | 一次 |
| https://raw.githubusercontent.com/raspberrypi/documentation/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | 200 | L98:`enable_uart=1` と `console=serial0,115200` でシリアルコンソール(GPIO14/15) | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h | 200 | ヘッダが存在。rpi-6.12.y の同じパスは HTTP 404 だが、6.12 系全体でヘッダがないかは未確認 | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c | 200 | L18:`#include <drm/clients/drm_client_setup.h>` | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | 200 | `handle_sysrq('i')`(L74)・`'s'`(L83)・`kernel_power_off()`(L106)はコメントアウト、`handle_sysrq('u')`(L93)は実行 | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | 200 | L292-293:`irq-gpios = <&gpio 6 0>`(falling edge) | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | 200 | L580・591-592:`USB_RTL8152=m`、`USB_NET_SR9700=m`、`USB_NET_SR9800=m` | 一次 |
| https://docs.m5stack.com/en/CardputerZero | 200 | 製品ページ(USB 節、UART ピン、SW_DET 等) | 一次(本文確認済み) |
| https://docs.m5stack.com/en/CardputerZero | 200 | 「EXT 2.54-14P」表(列は FUNC/PIN/左/右/PIN/FUNC):データ 6 行目 `SPI0_MISO \ | G9 \ | 11 \ | 12 \ | G15 \ | UART_RXD`、7 行目 `SPI0_CS1 \ | G7 \ | 13 \ | 14 \ | G14 \ | UART_TXD`。HY2.0-4P は `GND / 5V / G14_UART_TXD / G2_I2C1_SDA / G15_UART_RXD / G3_I2C1_SCL`(色 Black/Red/Yellow/White)。`G6_SW_DET`、`PYG6_MIC_SW`、`PYG12_LCD_RST` も同ページ | 一次(本文確認済み) |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c | 200 | L1164:`.compatible = "epson,rx8130",`(rx8130 の `rx8130_irq` は L577、alarm 関数は `rx8130_read_alarm` L608・`rx8130_set_alarm` L647・`rx8130_alarm_irq_enable` L692。いずれも grep -n) | 一次 |
| https://api.github.com/repos/m5stack/m5stack-linux-dtoverlays/contents/modules/rx8130?ref=75518549a2640486f5d13ea72ca4935b198d7c20 | 200 | `modules/rx8130` の内容は `Makefile` と `rx8130-overlay.dts` の 2 件のみ | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130/rx8130-overlay.dts | 200 | `compatible = "epson,rx8130"; reg = <0x68>;`(CardputerZero overlay は 0x32) | 一次 |
| https://raw.githubusercontent.com/CardputerZero/circle-boot-splash/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md | 200 | L19:`二次固件加载 \ | +2.1s \ | 加载 Linux kernel (9.2MB gzip)`、L20:`Linux 内核启动 \ | +3-5s \ | 到 userspace`、L21:`总计到 Linux 可用 \ | ~7-9s` | 一次(M5 の自己申告) |
| https://api.github.com/repos/mendersoftware/mender-convert/releases | 200 | tag 5.1.0 の published_at=2025-12-02T10:38:33Z、5.3.0 は 2026-10-01T12:54:27Z | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | 200 | L290 `debounce-ms = <500>;`、L292 `interrupts = <6 2>;`、L293 `irq-gpios = <&gpio 6 0>;`、L295 `disabled-gpios = <&m5ioe1 11 1>;` | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | 200 | L108-110 バックライトを 0 に設定、L113-115 `disabled_gpiod` を駆動 | 一次 |
| https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 200 | `pdftotext -layout` 後の `grep -n`:L1039 `Loaded 'kernel8.img' to 0x200000 size 0x9af973`(=10,156,403 B)、L1015 `Loaded 'initramfs8' ... size 0xb2483c`(=11,683,900 B)、L1020 `bcm2710-rpi-3-b-plus.dtb`、ARM 開始 `06.79s`、L1040 `Device tree loaded`(6.760 s。kernel の `Loaded` は 4.131 s) | 一次 |
| https://raw.githubusercontent.com/raspberrypi/linux/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | 200 | `grep -n` の結果:L10 PREEMPT=y、L86 ZSWAP=y、L467 ZRAM=m(L468 LZ4、L469-473)、L513 DM_VERITY=m、L580 USB_RTL8152=m、L1110 DRM_VC4=m、L1115 DRM_PANEL_MIPI_DBI=m、L1135 FRAMEBUFFER_CONSOLE_ROTATION=y、L1470 RTC_DRV_DS1307=m、L1641 F2FS_FS=y、L1650 OVERLAY_FS=m、L1663 TMPFS=y、L1671-1675 SQUASHFS(L1671 =m)、L1679-1680 EROFS | 一次 |
| https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | 200 | L93 `handle_sysrq('u')`(実行)、L106 `// kernel_power_off();`(コメントアウト。L102 はコメント行)、先頭コメント L7-L9 に S/U/O | 一次 |
| https://raw.githubusercontent.com/CardputerZero/pi-gen/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh | 200 | L20 `git clone --depth=1`(m5stack-linux-dtoverlays)、L31・L32 `CONFIG_CARDPUTERO_V0_5=y`、L36 `dtoverlay=vc4-kms-v3d,cma-64` の sed | 一次 |
| https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml | 200 | L34 `X-Env-Var-rootfs_type: erofs`、L41 `-z zstd,3`(erofs 時の mkfs 引数) | 一次 |
| https://raw.githubusercontent.com/OpenVPN/openvpn/v2.7.6/src/openvpn/ssl.c | 200 | L552 `if (options->tls_groups)`、L554 `tls_ctx_set_tls_groups`(指定時のみグループを設定) | 一次 |
| https://raw.githubusercontent.com/openssl/openssl/openssl-3.6.4/ssl/t1_lib.c | 200 | L209 既定グループ一覧の先頭 `?*X25519MLKEM768` | 一次 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/libopenssl/libopenssl.mk | 200 | L7 `LIBOPENSSL_VERSION = 3.6.4` | 一次 |
| https://raw.githubusercontent.com/torvalds/linux/v7.3-rc7/Documentation/admin-guide/ext4.rst | 200 | L175-176・L422-423 に data=journal 等の非推奨と「removed in January 2028」 | 一次 |
| https://raw.githubusercontent.com/torvalds/linux/v7.2/Documentation/admin-guide/ext4.rst | 200 | v7.2:`grep -c 'January 2028'` が 0(否定。27,676 B) | 未確認(公開 URL の該当内容を再確認する必要あり) |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-7.2.y/Documentation/admin-guide/ext4.rst | 200 | rpi-7.2.y:`grep -c 'January 2028'` が 0(否定。27,676 B) | 未確認(公開 URL の該当内容を再確認する必要あり) |
| https://raw.githubusercontent.com/torvalds/linux/v6.18/Documentation/admin-guide/ext4.rst | 200 | v6.18:`grep -c 'January 2028'` が 0(否定。27,676 B) | 未確認(公開 URL の該当内容を再確認する必要あり) |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/Documentation/admin-guide/ext4.rst | 200 | rpi-6.18.y:`grep -c 'January 2028'` が 0(否定。27,676 B) | 未確認(公開 URL の該当内容を再確認する必要あり) |
| https://docs.kernel.org/admin-guide/ext4.html | 200 | 本文に「removed in January 2028」が 2 か所(HTML タグ除去後) | 一次 |
| https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf | 200 | `pdftotext -layout` 後の `grep -n`:L25 Release 3、L152-153 CM0Lite は eMMC なし版、L157 BCM2837、L166 無線はオプション、L193-195 無線は Cypress CYW43439(Wi-Fi 2.4GHz + Bluetooth 5.0)、L208 無線なしモジュールではそのピンは予約、L349 SDIO(CM0Lite のみ) | 一次 |
| https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt | 200 | L1 `2026-10-06:`、L38 `Linux kernel 6.18.50 - cff533aec2fa601846766b32ff57204e0a61bed7`、L39 は次の項 `2026-09-15:` | 一次 |
| https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token= | 200 | Arm DDI 0501F(Cortex-A53 Cryptography Extension TRM r0p4)。`pdftotext` 後 L303-304「The optional Cryptography Extension is not included in the base product. ARM supplies the Cryptography Extension only under an additional licence…」 | 一次 |
| https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html | 200 | blame の注意:「does not display results for services with Type=simple」(即時起動扱いで測定不能)、キュー待ちは含まれない | 一次 |
| https://gist.github.com/hadrianw/ad07a76f338f09565703ae6ea35993c8 | 200 | 「`Intel Celeron N3060 under ChromeOS Crostini: regular fork 1762 µs …`」(HTML タグ除去後の本文) | 二次(単一の gist) |


### URL への到達結果（205 件）
出典一覧に掲載した URL 205 件を 1 件ずつ取得した結果です(2026-10-18 20:54〜20:55 JST)。**「到達のみ」は HTTP 200 を確認しただけで、本文の該当箇所は確認していません**。HTTP 403/404・タイトルのみ・接続不可は「取得できず」とし、一次/二次の確認度は付けません。リダイレクト先が異なる場合は最終 URL を併記しています。

| URL | HTTP / 最終 URL | タイトル(取得時) | 判定 | 取得時刻(JST) |
|---|---|---|---|---|
| https://api.github.com/orgs/CardputerZero | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/raspberrypi/linux/branches/rpi-6.12.y | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153 | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/CardputerZero/circle-boot-splash | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/raspberrypi/rpi-image-gen/releases | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/rauc/rauc/releases/latest | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/sbabic/swupdate/releases/latest | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/raspberrypi/rpi-eeprom/releases | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/rauc/rauc/pulls/1599 | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://deb.debian.org/debian/dists/trixie/main/binary-arm64/Packages.xz | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/bootconfig.html | 200 | Boot Configuration &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/ext4.html | 200 | ext4 General Information &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repos/zephyrproject-rtos/zephyr/pulls/110189 | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/orgs/CardputerZero/repos | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/kernel-parameters.html | 200 | The kernel’s command-line parameters &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/pstore-blk.html | 200 | pstore block oops/panic logger &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/ramoops.html | 200 | Ramoops oops/panic logger &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/filesystems/erofs.html | 200 | EROFS - Enhanced Read-Only File System &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/admin-guide/sysrq.html | 200 | Linux Magic System Request Key Hacks &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/filesystems/overlayfs.html | 200 | Overlay Filesystem &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/kbuild/kconfig.html | 200 | Configuration targets and editors &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/trace/boottime-trace.html | 200 | Boot-time tracing &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/aarch64/APKINDEX.tar.gz | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/filesystems/squashfs.html | 200 | Squashfs 4.0 Filesystem &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/usb/gadget_serial.html | 200 | Linux Gadget Serial Driver v2.0 &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://discuss.cachyos.org/t/7-2-kernel-boot-times-drastically-slower-than-6-18-lts/35306 | 200 | 7.2 kernel boot times drastically slower than 6.18 LTS - General - CachyOS Forum | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.kernel.org/watchdog/watchdog-api.html | 200 | The Linux Watchdog driver API &#8212; The Linux Kernel  documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://api.github.com/repositories/642546697/releases | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://busybox.net/FAQ.html | 200 | BusyBox | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.mender.io/release-information/supported-releases | 200 | Supported releases / Mender documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.mender.io/release-information/release-notes-changelog/mender-convert | 200 | mender-convert / Mender documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.mender.io | 200 → https://docs.mender.io/ | Mender Docs / Mender documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://erofs.docs.kernel.org/en/latest/faq.html | 200 | `🙋 Frequently Asked Questions — EROFS filesystem project` | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://forums.raspberrypi.com/viewtopic.php?t=207888 | 403 | Just a moment... | 取得できず | 2026-10-18 20:54 |
| https://forums.raspberrypi.com/viewtopic.php?t=263234 | 403 | Just a moment... | 取得できず | 2026-10-18 20:54 |
| https://gist.github.com/hadrianw/ad07a76f338f09565703ae6ea35993c8 | 200 | Test Linux fork/vfork+exec(dynamic/static binary) performance. Dependecies: gcc, | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.yoctoproject.org/migration-guides/release-notes-6.0.html | 200 | Release notes for 6.0 (wrynose) &mdash; The Yocto Project ® 6.0-tip documentatio | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://downloads.raspberrypi.com/os_list_imagingutility_v4.json | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.yoctoproject.org/ref-manual/variables.html | 200 | 14 Variables Glossary &mdash; The Yocto Project ® 6.0-tip documentation | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/cardputer-zero-os | 404 | Page not found · GitHub · GitHub | 取得できず | 2026-10-18 20:54 |
| https://github.com/CardputerZero/Template | 200 | GitHub - CardputerZero/Template: The template project for CardputerZero · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 | 200 → https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md | circle-boot-splash/app/cardputerzero-splash/BENCHMARK.md at b80d7c6a537c09c1ca23 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.m5stack.com/en/CardputerZero | 200 | m5-docs | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/launcher | 200 | GitHub - CardputerZero/launcher · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/m5stack-imager | 200 | GitHub - CardputerZero/m5stack-imager · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.m5stack.com/ja/CardputerZero | 200 | m5-docs | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/packages | 200 | GitHub - CardputerZero/packages · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml#L52-L54 | 200 → https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml | pi-gen/.github/workflows/build.yml at 791a985d4efca7327ae1fdb6c48230ac0d1ee1bc · | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://docs.m5stack.com/en/products/sku/C154 | 200 → https://docs.m5stack.com/en/CardputerZero | m5-docs | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32 | 200 → https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh | pi-gen/stage0/02-firmware/01-run.sh at 791a985d4efca7327ae1fdb6c48230ac0d1ee1bc | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel-packages.sha256 | 200 | pi-gen/stage0/02-firmware/files/kernel-packages.sha256 at 791a985d4efca7327ae1fd | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/commit/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc | 200 | Simplify is_hidden_prerelease logic · CardputerZero/pi-gen@791a985 · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3 | 200 → https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref | pi-gen/stage0/02-firmware/files/kernel.pref at 791a985d4efca7327ae1fdb6c48230ac0 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247 | 200 → https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh | pi-gen/stage2/05-cardputerzero/02-run.sh at 791a985d4efca7327ae1fdb6c48230ac0d1e | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L36 | 200 → https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh | pi-gen/stage2/05-cardputerzero/01-run.sh at 791a985d4efca7327ae1fdb6c48230ac0d1e | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/basecamp/omarchy/issues/6996 | 404 | タイトル未取得 | 取得できず | 2026-10-18 20:54 |
| https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf | 200 | meta-raspberrypi/conf/machine/raspberrypi0-2w-64.conf at 919588393f41b48cb6c5d83 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/ThomasKaiser/sbc-bench/blob/master/results/ARMv8-Crypto-Extensions.md | 200 | sbc-bench/results/ARMv8-Crypto-Extensions.md at master · ThomasKaiser/sbc-bench | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf#L12 | 200 → https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf | meta-raspberrypi/conf/layer.conf at 919588393f41b48cb6c5d832aa35e58a19b6762d · a | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/agherzan/meta-raspberrypi/tree/919588393f41b48cb6c5d832aa35e58a19b6762d/recipes-kernel/linux | 200 | meta-raspberrypi/recipes-kernel/linux at 919588393f41b48cb6c5d832aa35e58a19b6762 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/CardputerZero/u-boot | 200 | GitHub - CardputerZero/u-boot: &quot;Das U-Boot&quot; Source Tree · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/2026.08/package/rauc/Config.in | 200 | buildroot/package/rauc/Config.in at 2026.08 · buildroot/buildroot · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/2026.08/Config.in | 200 | buildroot/Config.in at 2026.08 · buildroot/buildroot · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/2026.08/package/systemd/Config.in | 200 | buildroot/package/systemd/Config.in at 2026.08 · buildroot/buildroot · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/2026.08/toolchain/toolchain-buildroot/Config.in | 200 | buildroot/toolchain/toolchain-buildroot/Config.in at 2026.08 · buildroot/buildro | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig#L12-L13 | 200 → https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig | buildroot/configs/raspberrypi3_64_defconfig at d5180309b1b66ef3b8eaccca70ad69be8 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6 | 200 → https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host | buildroot/package/gcc/Config.in.host at d5180309b1b66ef3b8eaccca70ad69be8e0729a1 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 | 200 → https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk | buildroot/package/mender/mender.mk at d5180309b1b66ef3b8eaccca70ad69be8e0729a1 · | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig#L11-L12 | 200 → https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig | buildroot/configs/raspberrypizero2w_64_defconfig at d5180309b1b66ef3b8eaccca70ad | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/johschmitz/buildroot-quickpi/commit/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5 | 200 | Add python needed for LCD Keypad control and update related init script · johsch | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 | 200 → https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md | buildroot-quickpi/README.md at 2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5 · johsch | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1 | 200 | Update for 2026.08 · buildroot/buildroot@d518030 · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/CardputerZeroRepository | 200 | GitHub - m5stack/CardputerZeroRepository · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/CardputerZero-AppBuilder | 200 → https://github.com/CardputerZero/AppBuilder | GitHub - CardputerZero/AppBuilder · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt | m5stack-linux-dtoverlays/firmware/CardputerZero/config.txt at 75518549a2640486f5 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L67 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile | m5stack-linux-dtoverlays/modules/CardputerZero/Makefile at 75518549a2640486f5d13 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c#L25 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-audio.c at 75518549 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L449-L457 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v3-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L46-L54 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L70-L77 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L89-L107 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overlay.dts at 7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c#L204 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c | m5stack-linux-dtoverlays/modules/CardputerZero/gpio-forwarder.c at 75518549a2640 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/powerfail_suo.c at 75518549a26404 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L3-L9 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | m5stack-linux-dtoverlays/modules/CardputerZero/powerfail_suo.c at 75518549a26404 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L250 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | m5stack-linux-dtoverlays/modules/CardputerZero/powerfail_suo.c at 75518549a26404 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c | m5stack-linux-dtoverlays/modules/CardputerZero/powerfail_suo.c at 75518549a26404 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/bq27220-1.0/bq27220_v5.dts#L14 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/bq27220-1.0/bq27220_v5.dts | m5stack-linux-dtoverlays/modules/bq27220-1.0/bq27220_v5.dts at 75518549a2640486f | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/99-cardputer-zero-lcd.rules | 200 | m5stack-linux-dtoverlays/modules/st7789v-1.0/99-cardputer-zero-lcd.rules at 7551 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c#L472 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c | m5stack-linux-dtoverlays/modules/m5ioe1-1.0/m5ioe1.c at 75518549a2640486f5d13ea7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/fb_load.service | 200 | m5stack-linux-dtoverlays/modules/st7789v-1.0/fb_load.service at 75518549a2640486 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/imu-1.0 | 200 | m5stack-linux-dtoverlays/modules/imu-1.0 at 75518549a2640486f5d13ea72ca4935b198d | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules | 200 | m5stack-linux-dtoverlays/modules/tca8418-1.0/99-cardputer-zero-keyboard.rules at | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20 | 200 | GitHub - m5stack/m5stack-linux-dtoverlays at 75518549a2640486f5d13ea72ca4935b198 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules/rx8130 | 200 | m5stack-linux-dtoverlays/modules/rx8130 at 75518549a2640486f5d13ea72ca4935b198d7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mcu-tools/mcuboot/releases/tag/v2.4.0 | 200 | Release MCUboot v2.4.0 · mcu-tools/mcuboot · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c#L220-L232 | 200 → https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c | m5stack-linux-dtoverlays/modules/st7789v-1.0/panel-mipi-dbi-m.c at 75518549a2640 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mendersoftware/mender-convert | 200 | GitHub - mendersoftware/mender-convert: An easy way to integrate the Mender clie | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/microsoft/mimalloc/blob/main/readme.md | 200 | mimalloc/readme.md at main · microsoft/mimalloc · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mendersoftware/mender-convert/releases | 200 | Releases · mendersoftware/mender-convert · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mkj/dropbear/blob/master/README.md | 200 → https://github.com/mkj/dropbear/blob/main/README.md | dropbear/README.md at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mkj/dropbear/blob/master/SMALL.md | 200 → https://github.com/mkj/dropbear/blob/main/SMALL.md | dropbear/SMALL.md at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/mkj/dropbear/blob/master/src/default_options.h | 200 → https://github.com/mkj/dropbear/blob/main/src/default_options.h | dropbear/src/default_options.h at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/4.7.5/USAGE-MKSQUASHFS | 200 | squashfs-tools/Documentation/4.7.5/USAGE-MKSQUASHFS at db038ef265ed00bb17aaf695a | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/manpages/mksquashfs.1#L179-L181 | 200 → https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/manpages/mksquashfs.1 | squashfs-tools/Documentation/manpages/mksquashfs.1 at db038ef265ed00bb17aaf695a7 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/omacom/omarchy/issues/6996 | 200 | Linux 7.1 initramfs_async=0 causes ~76-second kernel phase on mixed AMD/NVIDIA s | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc | documentation/documentation/asciidoc/computers/config_txt/autoboot.adoc at ddea9 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc | documentation/documentation/asciidoc/computers/config_txt/autoboot.adoc at ddea9 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | documentation/documentation/asciidoc/computers/config_txt/boot.adoc at ddea98e98 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L255 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | documentation/documentation/asciidoc/computers/config_txt/boot.adoc at ddea98e98 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L30-L40 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | documentation/documentation/asciidoc/computers/config_txt/boot.adoc at ddea98e98 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc | 200 | documentation/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/linux_kernel/building.adoc#L160-L206 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/linux_kernel/building.adoc | documentation/documentation/asciidoc/computers/linux_kernel/building.adoc at dde | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43 | 200 → https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc | documentation/documentation/asciidoc/computers/config_txt/conditional.adoc at dd | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Makefile#L165-L176 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Makefile | linux/arch/arm64/Makefile at 234188315037848e5b07d65b85d38edc64095caa · raspberr | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile | linux/Makefile at 234188315037848e5b07d65b85d38edc64095caa · raspberrypi/linux · | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1778 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b85d38edc64 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b85d38edc64 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b85d38edc64 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/firmware/issues/1635 | 200 | Hibernation (suspension to disk), sleep (suspension to memory, low-power mode) r | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/i2c/imx219.c | 200 | linux/drivers/media/i2c/imx219.c at 234188315037848e5b07d65b85d38edc64095caa · r | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/media/rc/gpio-ir-tx.c | 200 | linux/drivers/media/rc/gpio-ir-tx.c at 234188315037848e5b07d65b85d38edc64095caa | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/wireless/broadcom/brcm80211/brcmfmac/Makefile | 200 | linux/drivers/net/wireless/broadcom/brcm80211/brcmfmac/Makefile at 2341883150378 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/sr9700.c | 200 | linux/drivers/net/usb/sr9700.c at 234188315037848e5b07d65b85d38edc64095caa · ras | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig#L75-L83 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig | linux/drivers/net/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · raspberr | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c | 200 | linux/drivers/watchdog/bcm2835_wdt.c at 234188315037848e5b07d65b85d38edc64095caa | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L118 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c | linux/drivers/rtc/rtc-ds1307.c at 234188315037848e5b07d65b85d38edc64095caa · ras | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1545-L1556 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig | linux/init/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · raspberrypi/lin | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig#L1710-L1719 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig | linux/init/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · raspberrypi/lin | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/configs/tiny.config | 200 | linux/kernel/configs/tiny.config at 234188315037848e5b07d65b85d38edc64095caa · r | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt#L17-L52 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt | linux/kernel/Kconfig.preempt at 234188315037848e5b07d65b85d38edc64095caa · raspb | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig#L46-L52 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig | linux/lib/crypto/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · raspberry | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/kconfig/Makefile#L115-L118 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/kconfig/Makefile | linux/scripts/kconfig/Makefile at 234188315037848e5b07d65b85d38edc64095caa · ras | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl#L13-L33 | 200 → https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl | linux/scripts/bootgraph.pl at 234188315037848e5b07d65b85d38edc64095caa · raspber | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa | 200 | drm/connector: hdmi: Prefer YUV422 over dropping RGB to 8 bpc · raspberrypi/linu | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml | 200 | rpi-image-gen/config/trixie-minbase-ab.yaml at d7616a28bbb552db77cfd7bf90888f7a9 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/tree/rpi-6.18.y | 200 | GitHub - raspberrypi/linux: Kernel source tree for Raspberry Pi-provided kernel | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/tree/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/arm64 | 200 | linux/lib/crypto/arm64 at 234188315037848e5b07d65b85d38edc64095caa · raspberrypi | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt#L17-L45 | 200 → https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt | linux/kernel/Kconfig.preempt at 61d337138d273f134f41ef06eb0dd97c90123934 · raspb | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig#L44 | 200 → https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig | linux/arch/arm64/Kconfig at 61d337138d273f134f41ef06eb0dd97c90123934 · raspberry | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L42 | 200 → https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates | rpi-image-gen/image/gpt/ab_userdata/image.d/hooks/preimage05-templates at d7616a | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual | 200 | rpi-image-gen/image/mbr/simple_dual at d7616a28bbb552db77cfd7bf90888f7a9ef22f33 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device | 200 | rpi-image-gen/device at d7616a28bbb552db77cfd7bf90888f7a9ef22f33 · raspberrypi/r | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-eeprom/issues/541 | 200 | Support booting &quot;zboot&quot; kernel images? · Issue #541 · raspberrypi/rpi- | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a | 200 | GitHub - rauc/meta-rauc-community at 4d666ae4956f1cfacbd1a844f2e1794cb7784e2a · | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11 | 200 → https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml | rpi-image-gen/image/gpt/ab_userdata/image.yaml at d7616a28bbb552db77cfd7bf90888f | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/systemd/systemd/releases/tag/v259 | 200 | Release systemd v259 · systemd/systemd · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/zephyrproject-rtos/zephyr/releases/tag/v4.4.0 | 200 | Release Zephyr 4.4.0 · zephyrproject-rtos/zephyr · GitHub | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi | 200 | zephyr/boards/raspberrypi at 684c9e8f32e4373a21098559f748f06915f950c9 · zephyrpr | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/vicliu624/cardputer-zero-os | 200 | GitHub - vicliu624/cardputer-zero-os: `cardputer-zero-os` is the system profile | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/torvalds/linux/commit/f102131c842d | 200 | Revert &quot;arm64: mm: Unmap kernel data/bss entirely from the linear map&quot; | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/torvalds/linux/commit/56e3ee721b33 | 200 | driver core: Make deferred_probe_timeout default a Kconfig option · torvalds/lin | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/torvalds/linux/commit/fb0f3ef5601a | 200 | arm64: mm: Unmap kernel data/bss entirely from the linear map · torvalds/linux@f | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w | 200 | zephyr/boards/raspberrypi/rpi_zero_2w at a915b2f12675b48b16d56653ea145dcd8f20cbb | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://lkml.iu.edu/2609.2/00512.html | 200 | Linux-Kernel Archive: [PATCH] mmc: core: apply a per-command tuning timeout inst | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://lkml.iu.edu/2512.0/00981.html | 200 | Linux-Kernel Archive: [GIT PULL] printk for 6.19 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://lwn.net/Articles/1067029/ | 200 | The 7.0 scheduler regression that wasn't [LWN.net] | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://libc.llvm.org/full_host_build.html | 200 | Full Host Build - The LLVM C Library | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ | 200 | Extreme Pi Boot Optimization / KittenLabs | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/systemd/systemd/pull/38825 | 200 | Add experimental musl support by yuwata · Pull Request #38825 · systemd/systemd | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man1/systemd-bootchart.1.html | 404 | 404 Not Found | 取得できず | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man1/strace.1.html | 200 | strace(1) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man1/systemd-analyze.1.html | 200 | systemd-analyze(1) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man2/readahead.2.html | 200 | readahead(2) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man3/sd_notify.3.html | 200 | sd_notify(3) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://github.com/rauc/rauc/pull/1599 | 200 | bootchooser: add Raspberry Pi firmware initial support by gportay · Pull Request | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://mender.io/blog/new-in-mender-significantly-smaller-delta-updates-now-for-containers-too | 200 | New in Mender: Significantly smaller delta updates, now for containers too | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man5/systemd.socket.5.html | 200 | systemd.socket(5) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man7/fanotify.7.html | 200 | fanotify(7) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man5/systemd.service.5.html | 200 | systemd.service(5) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/busybox/busybox.mk | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://man7.org/linux/man-pages/man8/blktrace.8.html | 200 | blktrace(8) - Linux manual page | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://raw.githubusercontent.com/wbx-github/uclibc-ng/master/extra/Configs/Config.in | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://openvpn.net/community-resources/reference-manual-for-openvpn-2-6/ | 200 → https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual.html | OpenVPN 2.6 Manual | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://support.arm.com/documentation/101433/0102/Register-descriptions/AArch64-system-registers/ID-AA64ISAR0-EL1--AArch64-Instruction-Set-Attribute-Register-0--EL1 | 403 | タイトル未取得 | 取得できず | 2026-10-18 20:54 |
| https://techfeed.io/entries/6a30698b931f6b51a25b8f57 | 200 | 【海外記事紹介】Linuxを1秒で起動させる — たった1個のファイルで実現する最小構成シス | 取得できず(タイトルのみ) | 2026-10-18 20:54 |
| https://sourceware.org/git/?p=newlib-cygwin.git;a=tree;f=newlib/libc/sys;hb=HEAD | 200 | Making sure you&#39;re not a bot! | **取得できず**(bot 防御ページ。200 でも本文なし) | 2026-10-18 20:54 |
| https://rugix.org/docs/bakery/devices/ | 200 | Supported Devices — Rugix | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://web.archive.org/web/20260218015810/https://forums.raspberrypi.com/viewtopic.php?t=394171 | 200 | tryboot on Pi3: Some observations. - Raspberry Pi Forums | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://wiki.musl-libc.org/functional-differences-from-glibc.html | 200 | musl libc - Functional differences from glibc | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.kernel.org/releases.json | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/static/pdf/static/en/CardputerZero.pdf | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os | 200 | GitHub - CardputerZero/cardputer-zero-os: `cardputer-zero-os` is the system prof | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.spinics.net/lists/kernel/msg6184200.html | 200 | [PATCH v4] mm/page_alloc: replace kernel_init_pages() with batch page clearing & | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.phoronix.com/news/Linux-7.3-KThreads-NBCON | 200 | Linux Lands Fix for Rare, Varying SMP Boot Hangs Affecting Kernels Since 2024 - | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.usenix.org/system/files/atc19-gao.pdf | 200 | タイトル未取得 | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.wireguard.com/performance/ | 200 | Performance - WireGuard | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.wireguard.com/install/ | 200 | Installation - WireGuard | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.wireguard.com/quickstart/ | 200 | Quick Start - WireGuard | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://www.yoctoproject.org/development/releases/ | 200 | Releases - The Yocto Project | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://ubuntu.com/blog/zephyr-lts-announcement | 200 | Canonical announces Zephyr 26.04 LTS, delivering up to 15 years of support for M | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://x.com/HarrisonXu1998/status/2111387043775512697 | 200 | Harrison Xu on X: &quot;The great app ZeroRadio is already on the #CardputerZero | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://x.com/Rw7DVtscPX/status/2111293684952289420 | 200 | NDenchi@11/1 3DPの集いin大阪 on X: &quot;印刷もできます | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://web.archive.org/web/20260527131053/https://github.com/CardputerZero/cardputer-zero-shell | 200 | GitHub - CardputerZero/cardputer-zero-shell: `cardputer-zero-shell` is a lightwe | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://x.com/M5Stack/status/2110949681601871946 | 200 | M5Stack on X: &quot;The first batch of CM0 arrived.&quot; / X | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://x.com/saitotetsuya/status/2111008950107910198 | 200 | さいとてつや on X: &quot;https://t.co/wkcgXgqeIB 最初のバッチが3,000，次が12,000か #m5stack #card | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://uclibc-ng.org/ | 200 | Welcome to uClibc-ng! - Embedded C library | 到達のみ(本文未抽出) | 2026-10-18 20:54 |
| https://musl.libc.org/releases.html | 200 | musl libc Release History | 到達のみ(本文未抽出) | 2026-10-18 20:55 |
| https://www.etalabs.net/compare_libcs.html | 200 | Comparison of C/POSIX standard library implementations for Linux | 到達のみ(本文未抽出) | 2026-10-18 20:55 |

集計:205 件中、到達のみ **197** 件、取得できず **8** 件(HTTP 403×3〔フォーラム 2 件、Arm〕、404×3、techfeed〔200 だがタイトルのみ〕、sourceware〔200 だが bot 防御ページ〕)。
### その他の URL の到達結果（59 件）
本文から抽出した URL は合計 **309 件** です。URL の重複を除き、`#L…` の行アンカー付き URL は別として数えています。このうち、上記の一覧に含まれない 54 件を 2026-10-18 21:36〜21:45 JST に取得しました。取得結果は、到達のみ **50 件**、取得できず **4 件** です。Dropbear・bcm2710 の blob URL (200)を含みます。HTTP 200 は到達の確認であり、本文の該当箇所を確認したことを意味しません。

| URL | HTTP / 最終 URL | タイトル(取得時) | 判定 | 取得時刻(JST) |
|---|---|---|---|---|
| https://docs.mender.io/ | 200 | Mender Docs / Mender documentation | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/AppBuilder | 200 | GitHub - CardputerZero/AppBuilder · GitHub | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md | 200 | circle-boot-splash/app/cardputerzero-splash/BENCHMARK.md at b80d7c6a53 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L19-L21 | 200 | circle-boot-splash/app/cardputerzero-splash/BENCHMARK.md at b80d7c6a53 | 到達のみ(本文未抽出) | 2026-10-18 21:45 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/.github/workflows/build.yml | 200 | pi-gen/.github/workflows/build.yml at 791a985d4efca7327ae1fdb6c48230ac | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh | 200 | pi-gen/stage0/02-firmware/01-run.sh at 791a985d4efca7327ae1fdb6c48230a | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref | 200 | pi-gen/stage0/02-firmware/files/kernel.pref at 791a985d4efca7327ae1fdb | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh | 200 | pi-gen/stage2/05-cardputerzero/01-run.sh at 791a985d4efca7327ae1fdb6c4 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh | 200 | pi-gen/stage2/05-cardputerzero/02-run.sh at 791a985d4efca7327ae1fdb6c4 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/layer.conf | 200 | meta-raspberrypi/conf/layer.conf at 919588393f41b48cb6c5d832aa35e58a19 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypi3_64_defconfig | 200 | buildroot/configs/raspberrypi3_64_defconfig at d5180309b1b66ef3b8eaccc | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/configs/raspberrypizero2w_64_defconfig | 200 | buildroot/configs/raspberrypizero2w_64_defconfig at d5180309b1b66ef3b8 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host | 200 | buildroot/package/gcc/Config.in.host at d5180309b1b66ef3b8eaccca70ad69 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk | 200 | buildroot/package/mender/mender.mk at d5180309b1b66ef3b8eaccca70ad69be | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md | 200 | buildroot-quickpi/README.md at 2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt | 200 | m5stack-linux-dtoverlays/firmware/CardputerZero/config.txt at 75518549 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/Makefile at 75518549a26 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-audio.c | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-audio.c a | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v3-overla | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/cardputerzero-v5-overla | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/gpio-forwarder.c | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/gpio-forwarder.c at 755 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L108-L115 | 200 | m5stack-linux-dtoverlays/modules/CardputerZero/powerfail_suo.c at 7551 | 到達のみ(本文未抽出) | 2026-10-18 21:45 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/bq27220-1.0/bq27220_v5.dts | 200 | m5stack-linux-dtoverlays/modules/bq27220-1.0/bq27220_v5.dts at 7551854 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/m5ioe1-1.0/m5ioe1.c | 200 | m5stack-linux-dtoverlays/modules/m5ioe1-1.0/m5ioe1.c at 75518549a26404 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c | 200 | m5stack-linux-dtoverlays/modules/st7789v-1.0/panel-mipi-dbi-m.c at 755 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/mkj/dropbear/blob/DROPBEAR_2026.94/src/default_options.h | 200 | dropbear/src/default_options.h at DROPBEAR_2026.94 · mkj/dropbear · Gi | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/mkj/dropbear/blob/main/README.md | 200 | dropbear/README.md at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/mkj/dropbear/blob/main/SMALL.md | 200 | dropbear/SMALL.md at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/mkj/dropbear/blob/main/src/default_options.h | 200 | dropbear/src/default_options.h at main · mkj/dropbear · GitHub | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/plougher/squashfs-tools/blob/db038ef265ed00bb17aaf695a72f9b0c3489eb20/Documentation/manpages/mksquashfs.1 | 200 | squashfs-tools/Documentation/manpages/mksquashfs.1 at db038ef265ed00bb | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc | 200 | documentation/documentation/asciidoc/computers/config_txt/autoboot.ado | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | 200 | documentation/documentation/asciidoc/computers/config_txt/boot.adoc at | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc | 200 | documentation/documentation/asciidoc/computers/config_txt/conditional. | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/linux_kernel/building.adoc | 200 | documentation/documentation/asciidoc/computers/linux_kernel/building.a | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile | 200 | linux/Makefile at 234188315037848e5b07d65b85d38edc64095caa · raspberry | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L14-L16 | 200 | linux/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts at 23418831503784 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Makefile | 200 | linux/arch/arm64/Makefile at 234188315037848e5b07d65b85d38edc64095caa | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/Kconfig | 200 | linux/drivers/net/Kconfig at 234188315037848e5b07d65b85d38edc64095caa | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c | 200 | linux/drivers/rtc/rtc-ds1307.c at 234188315037848e5b07d65b85d38edc6409 | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/init/Kconfig | 200 | linux/init/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · raspb | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt | 200 | linux/kernel/Kconfig.preempt at 234188315037848e5b07d65b85d38edc64095c | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/lib/crypto/Kconfig | 200 | linux/lib/crypto/Kconfig at 234188315037848e5b07d65b85d38edc64095caa · | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/bootgraph.pl | 200 | linux/scripts/bootgraph.pl at 234188315037848e5b07d65b85d38edc64095caa | 到達のみ(本文未抽出) | 2026-10-18 21:36 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/scripts/kconfig/Makefile | 200 | linux/scripts/kconfig/Makefile at 234188315037848e5b07d65b85d38edc6409 | 到達のみ(本文未抽出) | 2026-10-18 21:37 |
| https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig | 200 | linux/arch/arm64/Kconfig at 61d337138d273f134f41ef06eb0dd97c90123934 · | 到達のみ(本文未抽出) | 2026-10-18 21:37 |
| https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt | 200 | linux/kernel/Kconfig.preempt at 61d337138d273f134f41ef06eb0dd97c901239 | 到達のみ(本文未抽出) | 2026-10-18 21:38 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates | 200 | rpi-image-gen/image/gpt/ab_userdata/image.d/hooks/preimage05-templates | 到達のみ(本文未抽出) | 2026-10-18 21:37 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml | 200 | rpi-image-gen/image/gpt/ab_userdata/image.yaml at d7616a28bbb552db77cf | 到達のみ(本文未抽出) | 2026-10-18 21:37 |
| https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual.html | 200 | OpenVPN 2.6 Manual | 到達のみ(本文未抽出) | 2026-10-18 21:37 |
| https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/include/drm/clients/drm_client_setup.h | 404 | タイトル未取得 | 取得できず | 2026-10-18 21:37 |
| https://t.co/wkcgXgqeIB | 403 → https://www.kickstarter.com/projects/m5stack/cardputerzero/posts/4829886 | Just a moment... | 取得できず | 2026-10-18 21:37 |
| https://www.kickstarter.com/projects/m5stack/cardputerzero/posts/4829886 | 403 | Just a moment... | 取得できず | 2026-10-18 21:45 |

### 追加 URL の取得結果（19 件）
本文から抽出した URL は合計 **339 件** です。URL の重複を除き、`#L…` の行アンカー付き URL は別として数えています。追加で取得した 17 件の取得日は 2026-10-18 22:14 JST です。結果は、到達のみ **17 件**、取得できず **0 件** です。本文から削除された旧アンカー付き URL も記録に含まれます。HTTP 200 はページへの到達のみを示し、アンカー先の内容確認を意味しません。

| URL | HTTP / 最終 URL | タイトル(取得時) | 判定 | 取得時刻(JST) |
|---|---|---|---|---|
| https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20 | 200 | pi-gen/stage2/05-cardputerzero/01-run.sh at 791a985d4efca7327ae1fdb6c4 | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1110-L1135 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1135 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1470 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641-L1680 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1650 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1663 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1671-L1675 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1679-L1680 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L513 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L580 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 | 200 | linux/arch/arm64/configs/bcm2711_defconfig at 234188315037848e5b07d65b | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L1164 | 200 | linux/drivers/rtc/rtc-ds1307.c at 234188315037848e5b07d65b85d38edc6409 | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/rtc/rtc-ds1307.c#L608 | 200 | linux/drivers/rtc/rtc-ds1307.c at 234188315037848e5b07d65b85d38edc6409 | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L44 | 200 | rpi-image-gen/image/gpt/ab_userdata/image.d/hooks/preimage05-templates | 到達のみ(本文未抽出) | 2026-10-18 22:14 |
| https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L34-L41 | 200 | rpi-image-gen/image/gpt/ab_userdata/image.yaml at d7616a28bbb552db77cf | 到達のみ(本文未抽出) | 2026-10-18 22:14 |

---

## 意図的に含めないもの

| 対象 | 理由 |
|---|---|
| 特定の外部製品を比較した記述 | 指定された調査範囲外の内容として除外 |
| 商標・候補名に関する個別情報 | 権利の個別照会と候補比較は対象外とし、関連 URL は掲載しない。URL 取得結果で残差が増えたものは、取得区分別に 4 件・2 件を含め、いずれもこのカテゴリとして意図的に除外する |
| 調査時の検索式・一時的な検証コマンド | 個別の作業手順は公開資料に基づく事実ではないため収録しない |
| 内部管理情報（ID、版履歴、監査記録、私的ファイル名、作業用パスなど） | 公開資料に基づく記録に不要な情報として除外し、個別の ID やファイル名は列挙しない |
| URL 抽出時の句読点による差分 2 件 | URL 直後の全角句点・括弧が抽出結果に含まれる差分です。正規の URL は本書に掲載済みで、出典の欠落ではありません |

### ストレージ・セキュリティ・機能対応表で追加した出典

次の URL は本文の新規記述に使った公開資料です。短い英文は取得した資料からの抜粋です。社内の計測ファイル名や作業用パスは本文・表に記載していません。

| URL | HTTP / 取得状況 | 短い抜粋 | 確度 |
|---|---|---|---|
| https://github.com/pengutronix/genimage/blob/v20/README.rst | 200・本文確認 | “the final offset rounded up to the partition's `align` value” | 【一次】 |
| https://docs.kernel.org/admin-guide/ext4.html | 200・本文確認 | “All data are committed into the journal prior to being written into the main file system.” | 【一次】 |
| https://man7.org/linux/man-pages/man8/mke2fs.8.html | 200・本文確認 | “Configure the file system for a RAID array with stride-size file system blocks” | 【一次】 |
| https://www.sdcard.org/developers/sd-standard-overview/application-performance-class/ | 200・本文確認 | “the number of 4KB read/write commands can be executed per second” | 【一次】 |
| https://www.sdcard.org/developers/sd-standard-overview/speed-class/ | 200・本文確認 | “All speed class types assures minimum sequential card access performance” | 【一次】 |
| https://github.com/raspberrypi/linux/blob/5d64d1ea73716526ed9c0ed184a9cb5f6042e32c/drivers/mmc/core/sd.c#L722-L797 | 200・本文確認 | `MMC_DEV_ATTR(preferred_erase_size` | 【一次】 |
| https://lwn.net/Articles/428584/ | 200・本文確認 | “reverse engineering based on timing data” | 【二次】 |
| https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md | 200・本文確認 | “how secure-boot works on a Raspberry Pi 4 (or newer)” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc | 200・本文確認 | “check primary SD for `bootcode.bin`” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc | 200・本文確認 | “All Raspberry Pi models support `tryboot`” | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271 | 200・本文確認 | “enables a hardware watchdog timer that is handed over to the operating system” | 【一次】 |
| https://docs.kernel.org/admin-guide/device-mapper/verity.html | 200・本文確認 | “This hash should be trusted as there is no other authenticity beyond this point.” | 【一次】 |
| https://docs.kernel.org/admin-guide/sysctl/kernel.html | 200・本文確認 | `dmesg_restrict` / `kptr_restrict` / `unprivileged_bpf_disabled` | 【一次】 |
| https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token= | 200・PDF 本文確認 | “The optional Cryptography Extension is not included in the base product.” | 【一次】 |
| https://docs.m5stack.com/en/CardputerZero | 200・本文確認 | “GL852G-OHY60 USB 2.0 Hub / SR9900A USB 2.0 to Ethernet chip” | 【一次】 |
| https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 200・PDF 本文確認 | “The battery charging has a separate input path. Input priority: USB IN > EXT. IN” | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/etc/fstab | 200・本文確認 | `/dev/mmcblk0p7 /data ext4 noauto,noatime,data=journal,errors=remount-ro 0 2` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/usr/sbin/msd-update | 200・本文確認 | `sha256sum -c manifest` / `rootfs read-back SHA-256 mismatch` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog | 200・本文確認 | `watchdog -T 15 -t 5 /dev/watchdog` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/linux.fragment | 200・本文確認 | `CONFIG_BCM2835_WDT=y` / `# CONFIG_MEDIA_SUPPORT is not set` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/board/cardputerzero/config.txt | 200・本文確認 | `dtoverlay=cardputerzero-v5-overlay` / `dtoverlay=bq27220_v5` | 【一次】 |
| https://raw.githubusercontent.com/uist1idrju3i/MSD-Linux/main/package/m5stack-cardputerzero/m5stack-cardputerzero.mk | 200・本文確認 | `modules/st7789v-1.0` / `modules/tca8418-1.0` / `modules/es8389-1.0` | 【一次】 |
| https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93-L115 | 200・本文確認 | `handle_sysrq('u')` / `// handle_sysrq('s');` | 【一次】 |
| https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39178538327 | CI artifact 取得済み | `p1=1, p2=32769, p3=163841, p4=294913, p5=294914, p6=819203, p7=1343492` | 【実測】 |
| https://man7.org/linux/man-pages/man5/mke2fs.conf.5.html | 200・本文確認 | `small = { blocksize = 1024` | 【一次】 |
| https://man7.org/linux/man-pages/man8/mke2fs.8.html | 200・本文確認 | “heuristically determined by the file system size and the expected usage” | 【一次】 |
| https://kspp.github.io/Recommended_Settings | 200・本文確認 | `CONFIG_STACKPROTECTOR_STRONG=y` / `CONFIG_HARDENED_USERCOPY=y` | 【一次】 |
| https://documentation-service.arm.com/static/5e9075f9c8052b1608761519?token= | 本文確認 | “The Cortex-A53 processor implements the ARMv8-A architecture.” | 【一次】 |
| https://support.arm.com/documentation/102433/0200/Return-oriented-programming | 本文確認 | Armv8.3-A で pointer authentication を導入 | 【一次】 |
| https://developer.arm.com/documentation/109697/latest/Feature-descriptions/The-Armv8-5-architecture-extension | 本文確認 | `FEAT_BTI` は Armv8.4-A で optional | 【一次】 |
| https://github.com/raspberrypi/firmware/issues/694 | 本文確認 | 試験用 firmware が `/chosen/kaslr-seed` を 8 byte の乱数として追加したとの記録 | 【一次・履歴】 |
| https://github.com/raspberrypi/firmware/issues/1595 | 本文確認 | “There is a new firmware available ... that adds `/chosen/rng-seed`.” | 【一次・履歴】 |
| https://github.com/raspberrypi/rpi-eeprom/commit/cbd599e30dd3a8e7bbc7646364f3d3907f3027e0 | 本文確認 | Pi 5 の `kaslr-seed` / `rng-seed` が正しい entropy source を使うよう修正 | 【一次】 |
| https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/os/graphics-utilities.adoc | 本文確認 | `0x10000` は過去の undervoltage、`0x80000` は過去の soft temperature limit | 【一次】 |

### 割り当て単位・小さいファイル調査（2026-10-19）

| 項目 | 版・日付 | URL | 短い抜粋 | 確認度 |
|---|---|---|---|---|
| e2fsprogs 最新版 | 1.47.4、2026-03-06 | https://github.com/tytso/e2fsprogs/releases/tag/v1.47.4 | “e2fsprogs 1.47.4” / “Mar 6, 2026” | 【一次】 |
| mke2fs の既定と ext4 profile | e2fsprogs 1.47.4 | https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in | `[defaults] blocksize = 4096` / `small { blocksize = 1024` / `orphan_file` | 【一次】 |
| small profile の比較 | e2fsprogs 1.46.5／1.47.4 | https://github.com/tytso/e2fsprogs/blob/v1.46.5/misc/mke2fs.conf.in<br>https://github.com/tytso/e2fsprogs/blob/v1.47.4/misc/mke2fs.conf.in | 両タグで `small` は `blocksize = 1024`、`inode_ratio = 4096` | 【一次】 |
| mke2fs.conf のサイズ型の説明 | e2fsprogs upstream、issue #74 | https://github.com/tytso/e2fsprogs/issues/74 | small は 3–512 MiB、floppy は 3 MiB 未満という maintainer の説明 | 【一次】 |
| Buildroot package | 2026.08 | https://raw.githubusercontent.com/buildroot/buildroot/2026.08/package/e2fsprogs/e2fsprogs.mk | `E2FSPROGS_VERSION = 1.47.4` | 【一次】 |
| mke2fs の blocksize 選択 | mke2fs(8)、2026-10-19 取得 | https://man7.org/linux/man-pages/man8/mke2fs.8.html | “heuristically determined by the file system size and the expected usage” | 【一次】 |
| genimage の ext4 引数 | v20 | https://github.com/pengutronix/genimage/blob/v20/image-ext2.c | `const char *extraargs = cfg_getstr` / `usage_type` があれば `-T` を付加 | 【一次】 |
| ext4 blocksize／inline data／bigalloc／orphan file | docs.kernel.org 現行ページ、2026-10-19 取得 | https://docs.kernel.org/filesystems/ext4/ | “Blocks can range in size from 1KiB to 64KiB” / “Bigalloc” / “Inline Data” / “Orphan file” | 【一次】 |
| ext4 inline-data 対応 | e2fsprogs 1.43、2016-05-17 | https://github.com/tytso/e2fsprogs/blob/v1.43/RELEASE-NOTES | “Add support for ... inline data” | 【一次】 |
| dosfstools の FAT cluster 選択 | 4.2 | https://github.com/dosfstools/dosfstools/blob/v4.2/src/mkfs.fat.c | “fs size <= 260M: 0.5k clusters” / FAT32 cluster-size 条件表 | 【一次】 |
| mkfs.fat の option／内部整列 | dosfstools 4.2 man page | https://man.cgr.dev/os/dosfstools/4.2-r46/man8/mkfs.fat.8.md | “align all the data structures to cluster size”; `-s`, `-S`, `--offset` | 【一次】 |
| genimage vfat handler | v20 | https://github.com/pengutronix/genimage/blob/v20/image-vfat.c | `mkdosfs` option と `extraargs` を取得して formatter に渡す | 【一次】 |
| Microsoft exFAT specification | 現行公開ページ、2026-10-19 取得 | https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification | cluster の最大値は 32 MiB。default-size table は見つからず | 【一次】【未確認】 |
| SD Association Formatter | 公開 FAQ／解説、2026-10-19 取得 | https://www.sdcard.org/downloads/formatter/faq/<br>https://www.sdcard.org/press/thoughtleadership/the-sd-memory-card-formatterhow-this-handy-tool-solves-your-memory-card-formatting-needs/ | formatter は容量に応じ FAT／exFAT を選び、internal flash boundary に合わせる説明 | 【一次】 |
| SD Association 仕様 PDF | Part 1、2026-10-19 取得 | PDF URL は HTTP 403 | SD Association の仕様書 PDF は取得できず（HTTP 403）、内容は未確認 | 【未確認】 |
| exfatprogs の default cluster／boundary-align | 1.4.3、2026-08-14 | https://github.com/exfatprogs/exfatprogs/releases/tag/1.4.3<br>https://github.com/exfatprogs/exfatprogs/blob/1.4.3/lib/libexfat.c<br>https://github.com/exfatprogs/exfatprogs/blob/1.4.3/man/mkfs.exfat.8.in | cluster default は volume size により選択。`--boundary-align` は FAT／cluster heap の境界を指定 | 【一次】 |
| SquashFS tools | 4.7.5、2026-03-01 | https://github.com/plougher/squashfs-tools/releases/tag/4.7.5<br>https://github.com/plougher/squashfs-tools/blob/4.7.5/README.md | `-b`、fragment、`-no-fragments`、`-always-use-fragments` | 【一次】 |
| EROFS tools | 1.9.4、2026-08-19 | https://github.com/erofs/erofs-utils/blob/v1.9.4/ChangeLog<br>https://erofs.docs.kernel.org/en/latest/mkfs.html | “erofs-utils 1.9.4” / `ztailpacking`／fragments | 【一次】 |
| F2FS small-file handling | docs.kernel.org 現行ページ、2026-10-19 取得 | https://docs.kernel.org/filesystems/f2fs.html | inline data／inline dentry を説明。kernel tag はページ上で未確認 | 【一次】【未確認】 |
| SD small-write 例 | LWN、2011-01-27 | https://lwn.net/Articles/428584/ | “small writes were slower than aligned larger writes” | 【二次】 |

### SoC・圧縮・最適化・シミュレーターの出典

この節は 2026-10-19 に確認しました。release tag がないページは取得日を記録し、固定 revision ではなく取得時点の公開資料として扱います。

| 項目 | 版・日付 | URL | 確認した抜粋・事実 | 信頼度 |
|---|---|---|---|---|
| CM0 | datasheet Release 3、2026-07-08 | https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf | 「Compute Module Zero」Release 3 | 【一次】 |
| CardputerZero | 2026-10-19 取得 | https://docs.m5stack.com/en/CardputerZero | “Quad-core Cortex-A53 @ 1 GHz”; “512 MB LPDDR2” | 【一次・製品資料】 |
| Cortex-A53 | TRM r0p4 | https://support.arm.com/documentation/ddi0500/j/Introduction/Implementation-options | L1/L2 実装範囲、SIMD/FP と暗号拡張は optional | 【一次】 |
| Raspberry Pi kernel image format | documentation commit `ddea98e98dafe9419feb4fd82710c2fbdef7dc44` | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc | arm64 image は非圧縮または gzip archive | 【一次】 |
| arm64 boot protocol | Linux v6.18.57 | https://github.com/torvalds/linux/blob/v6.18.57/Documentation/arch/arm64/booting.rst | arm64 Image の bootloader 要件 | 【一次】 |
| Buildroot 選択版 Bootlin toolchain | stable 2025.08-1 / GCC 14.3.0 | https://toolchains.bootlin.com/releases_aarch64.html | AArch64 glibc stable 2025.08-1 は GCC 14.3.0 | 【一次】 |
| Bootlin 最新 stable toolchain | 2026.08-1 / GCC 15.3.0 | https://toolchains.bootlin.com/releases_aarch64.html | 最新 stable は 2026.08-1 | 【一次】 |
| GCC 最適化 / AArch64 | GCC 14.3.0 | https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Optimize-Options.html<br>https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/AArch64-Options.html | `-Os`, `-Oz`, `-O2`, A53 tuning / errata options | 【一次】 |
| GCC PGO / instrumentation | GCC 14.3.0 | https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Instrumentation-Options.html | `-fprofile-generate` / `-fprofile-use` / `-fprofile-update` / `GCOV_PREFIX` | 【一次】 |
| Buildroot optimization / LTO | Buildroot 2026.08 commit `d5180309b1b66ef3b8eaccca70ad69be8e0729a1` | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/Config.in | `BR2_OPTIMIZE_2` default and LTO option | 【一次】 |
| SquashFS ARM64 BCJ | squashfs-tools 4.7.5 | https://github.com/plougher/squashfs-tools/blob/4.7.5/squashfs-tools/xz_wrapper_extended.c | source registers `"arm64"` BCJ filter | 【一次】 |
| XZ | XZ Utils 5.8.3 | https://github.com/tukaani-project/xz/releases/tag/v5.8.3 | release 5.8.3; ARM64 BCJ filter | 【一次】 |
| Linux kernel AutoFDO / Propeller / LTO | Linux v6.18.57 | https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/autofdo.rst<br>https://github.com/torvalds/linux/blob/v6.18.57/Documentation/dev-tools/propeller.rst<br>https://github.com/torvalds/linux/blob/v6.18.57/arch/Kconfig | arm64 sampling / Clang requirements / `LTO_CLANG` | 【一次】 |
| AutoFDO profile tools | commit `f95d1a170dfe24ec5ce4117aa4b0f6d836841703`、2026-09-30 | https://github.com/google/autofdo/tree/f95d1a170dfe24ec5ce4117aa4b0f6d836841703 | `create_gcov` toolset と GCC AutoFDO の手順 | 【一次】 |
| Kernel AutoFDO / Propeller merge | Linux 6.13、2024-11-30 報道 | https://www.phoronix.com/news/AutoFDO-Propeller-Linux-6.13 | upstream merge を報道 | 【二次】 |
| Clang kernel instrumentation PGO | 2021-06-03 | https://www.phoronix.com/news/Clang-PGO-Linux-Shot-Down | Linux 5.14 patch の撤回を報道 | 【二次】 |
| Zstandard benchmark | zstd 1.5.4、PTS result 2024-08-28 | https://mail.openbenchmarking.org/result/2408281-BOMM-240826011%26gru%26sro%26export=html | Pi 3B+ / A53、level 19 展開 67.9 MB/s | 【二次】 |
| LZ4 benchmark | lzbench 1.7.3、LZ4 1.8.3 | https://github.com/lz4/lz4/pull/713 | 投稿された A53 測定、Silesia `dickens` 展開 448 MB/s。board / clock 未記載 | 【二次】 |
| QEMU 最新 release | 11.1.2、2026-09-28 | https://github.com/qemu/qemu/releases/tag/v11.1.2 | latest stable release | 【一次】 |
| QEMU Raspberry Pi models | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/system/arm/raspi.html | DMA、SD/MMC host、MBOX、SPI、I2C と未実装 device | 【一次】 |
| QEMU Raspberry Pi model changes | QEMU 9.0 | https://wiki.qemu.org/ChangeLog/9.0 | `raspi4b`、SPI / BSC I2C 支援 | 【一次】 |
| QEMU Raspberry Pi models 6.2 | QEMU 6.2.0 | https://qemu.readthedocs.io/en/v6.2.0/system/arm/raspi.html | `raspi3b` model docs | 【一次】 |
| QEMU TCG plugins | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/devel/tcg-plugins.html | plugin callback、instruction / translation-block instrumentation | 【一次】 |
| QEMU cache plugin | QEMU v11.1.2 source | https://github.com/qemu/qemu/blob/v11.1.2/contrib/plugins/cache.c | guest cache hit/miss counter | 【一次】 |
| QEMU `-icount` | QEMU 11.1.2 | https://qemu.readthedocs.io/en/v11.1.2/system/invocation.html | instruction-count virtual clock | 【一次】 |
| gem5 latest release | 25.1.0.1、2026-04-21 | https://github.com/gem5/gem5/releases/tag/v25.1.0.1 | hotfix release。取得時点で 26.0 release 未確認 | 【一次】 |
| gem5 HPI | gem5 commit `c8222cc6` | https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/HPI.py | “representative of a modern in-order ARMv8-A implementation” | 【一次】 |
| gem5 ex5_LITTLE | gem5 commit `c8222cc6` | https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/ex5_LITTLE.py | Cortex-A7 based model | 【一次】 |
| Arm FVP | Fast Models 11.32、2026-07-30 | https://support.arm.com/tools-and-software/fixed-virtual-platforms/arm-architecture-fvps | Architecture FVP / Base RevC release list。license entitlement 未確認 | 【一次】【未確認】 |
| Renode | 1.17.0、2026-09-07 | https://github.com/renode/renode/releases/tag/v1.17.0 | release page と platform tree。BCM2835/2837 model は未発見 | 【一次】【未確認】 |
| Raspberry Pi Zero 2 W | 2026-10-19 取得 | https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/ | RP3A0、quad-core 1 GHz A53、512 MB LPDDR2 | 【一次・製品資料】 |
