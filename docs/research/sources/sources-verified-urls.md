# 本文を確認した URL

sources.md から分割した出典記録です。

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
