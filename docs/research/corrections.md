# 訂正済み事項

### よくある誤解と正しい内容
| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| Kickstarter の販売数 | 3,000/12,000 台の情報を未検証の SNS 情報と扱う | **Update 13 は公式更新**の引用（X のリンクカード由来。本文は取得できていない=403） | https://x.com/saitotetsuya/status/2111008950107910198<br>URL未取得（Kickstarter 本文） |
| pi-gen は rpi-v8 カーネルを apt から導入 | pi-gen は rpi-v8 カーネルを apt から導入(版の固定なし) | **6.18.39-1+rpt1 を sha256 検証+apt pin 1001+hold で固定**。M5 dtoverlays は `--depth=1` で最新追従 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20 |
| 起動時間の数値 | 起動時間の数値(2.1s、5〜6s、3.5s 未満)を同列に並べた | 数値は SoC・条件・終点が異なり**合成不可**。2112ms は 227KB の小型カーネル構成、Linux 可用 7〜9s は自己申告、Pi 3B+ は ARM 開始 6.79s です。各値の条件を併記します | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| rpi-eeprom の Pi5 stable | rpi-eeprom の Pi5 stable(2026-09-25)で A/B 更新 | A/B 更新の記載は 2026-05-13 の Pi5 系エントリ。**CM0 には無関係** | https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md (HTTP 200 のみ確認。内容は未読) |
| Mender Client 6.1.0 は二次情報/CM0 向け統合は不明 | Mender Client 6.1.0 は二次情報/CM0 向け統合は不明 | **6.1 は Supported(docs.mender.io)、mender-convert に RPi3(64bit)の U-Boot 構成あり。CM0 の構成・動作は未確認**。Buildroot の mender は 3.5.3(古い系列) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://docs.mender.io |
| zram は defconfig 未確認 | zram は defconfig 未確認 | **ZRAM=m、ZSWAP=y**(rpi-6.18.y bcm2711_defconfig) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 |
| Buildroot 2026.08 は GCC 16.2.0 が既定 | Buildroot 2026.08 は GCC 16.2.0 が既定(旧記述) | **GCC 既定は 15.3.0**(14.x/16.x は選択式) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6 |
| powerfail_suo は S→U→O | powerfail_suo は S→U→O(sync/ro/poweroff)を実行 | SysRq-U(読み取り専用で再マウント)に加え、バックライトと GPIO を操作します。's'、'i'、`kernel_power_off()` はコメントアウトされています | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |
| rpi-image-gen の最新は v2.3.0 | rpi-image-gen の最新は v2.3.0(cm4/pi4/cm5/pi5 のみ)、issue #153 で image-rota は GPT・BCM2837 は MBR 要 | **最新 v2.8.0(2026-08-13)/master d7616a2**。device 層に pi3/zero2w はあるが、**image-rota は現行 master でも cm4/pi4/cm5/pi5 のみ**(コードで確認)。issue #153 は closed(2026-02-18)のため根拠をコードに変更 | https://api.github.com/repos/raspberrypi/rpi-image-gen/releases<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153 |
| 「検証ボードに RPi が無いから Zephyr 26.04 LTS は非対応」 | 「検証ボードに RPi が無いから Zephyr 26.04 LTS は非対応」 | 根拠は「v4.4.0 に BCM2710/rpi_zero_2w が無い」。Canonical フォークの中身は未確認 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi |
| CM5 で display_auto_detect=0 の差は 9ms | CM5 で display_auto_detect=0 の差は 9ms(旧版は確認済み扱い) | 出典を特定できず【未確認】に降格 | URL なし |
| 「GL852G のリセットは PYG3 経由」 | 「GL852G のリセットは PYG3 経由」(推測) | docs に明記:PYG3 は**キーボードとハブの共用リセット** | https://docs.m5stack.com/en/CardputerZero |
| RAUC PR #1599 の状態は未確認 | RAUC PR #1599 の状態は未確認 | open・未マージ(2026-10-18) | https://api.github.com/repos/rauc/rauc/pulls/1599 |
| arm_64bit の CM0 対応は未確認 | arm_64bit の CM0 対応は未確認 | 対応表に CM0 なし。`[cm0]` フィルタはある | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43 |
| M5 kernel compatibility | kernel 版の前提に関する旧記述 | **panel-mipi-dbi-m.c の include は 6.12 で解決せず 6.18 で解決する（一次）。M5 code 全般が 6.18 以上必須とは言えません**。mainline panel-mipi-dbi 経路もありますが、実機確認は未確認 | https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c |


## 訂正済み事項

この表には公開資料から確認できる訂正をまとめています。

| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| Mender を RPi3 の対象外 | Mender は RPi3 をサポートしない | mender-convert の README(HEAD 4b3f04a、2026-10-12 コミット)が `raspberrypi/uboot/debian/raspberrypi3_bookworm_64bit_config`(Raspberry Pi 3、Raspberry Pi OS bookworm 64bit)を「officially supported」の Core 構成に載せ、Mender Client 6.1 は 2026-10 にサポート対象(docs.mender.io supported-releases)。Mender Client 6.1.0 は mender.io のブログ(2026-10-16)に記載。CM0 自体の記載と動作は未確認 | [公開出典一覧](sources.md) |
| `/data` のマウントオプション | `/data` に `nosuid`、`nodev`、`noexec` が指定されていない（security-hardening.md の旧記述） | `fstab` は `noatime,nodev,nosuid,data=ordered,errors=remount-ro`。未指定なのは `noexec` だけです（2026-10-19 に main の `fstab` で確認） | [現行 fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| powerfail_suo の動作 | S→U→O を実行する | SysRq-U に加えてバックライトと GPIO を操作します。`'i'`・`'s'`・`kernel_power_off()` はコメントアウトされています（powerfail_suo.c @7551854 の L74/L83/L93/L106） | [公開出典一覧](sources.md) |
| UART0 の種別を PL011 と断定 | UART0 が PL011 である | 公式 DT は `serial0 = &uart1`(mini-UART、`uart1_pins` は空)、`serial1 = &uart0`(PL011、GPIO30〜33=BT)。公式 pi-gen は cmdline の `console=serial0,115200` を除去。「公式 pi-gen に enable_uart が無い」という記述は不正確でした。一部訂正として、pi-gen は M5 の Makefile(`config_setup`)経由で `enable_uart 1` を [all] に設定する(最終 config.txt は未検査) | [公開出典一覧](sources.md) |
| 「OpenSSH の既定は AES-GCM 候補」 | 「OpenSSH の既定は AES-GCM 候補」 | `chacha20-poly1305@openssh.com` が先頭(myproposal.h、V_10_5_P1)。OpenVPN は暗号の設定が要る(`--data-ciphers` 既定は AES-GCM 先頭) | [公開出典一覧](sources.md) |
| arm64 linear alias unmap の記述 | 修正が v7.2 に適用され、revert 後も残る | 導入(63e0b6a5b693)と revert(f102131c842d)はともに v7.2-rc1、再適用(fb0f3ef5601a)は v7.3-rc1 に入る(v7.2 には入らない)。`rpi-7.2.y` の mmu.c は data/bss を「read-only で map」する旧コードで影響なし、`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid`)を含む。compare API と各ブランチの raw で確認(再適用で RPi3/4 の問題が解消したかはコミットメッセージから読み取れず未確認のまま) | [公開出典一覧](sources.md) |
| CachyOS の遅延と kernel 回帰 | CachyOS の遅延を kernel 7.2 の回帰とする | 投稿者は BIOS で TPM を無効にして解消(2026-09-10)。Omarchy #6996 は Omarchy 4.0.0-1 / Linux 7.1.8、約 266MiB の initramfs と `initramfs_async=0` の x86 事例です。Omarchy の URL は移転前の組織配下で 404、現行は `omacom/omarchy` です | [公開出典一覧](sources.md) |
| KittenLabs の数値を条件なしで書いたのは不備 | 測定条件を示さず <3.5 秒とする | <3.5 秒は Zero 2 W+Buildroot 2024.02.1(フル glibc)、カーネル 8.5MiB(非圧縮。Raspbian 標準は 25MiB)、KASLR 無効、Spectre 等の緩和無効、sound/USB/HID/DVB/video・fb/RAID/高度なネットワーク機能無効、モジュール非圧縮、測定は電源投入から userspace が GPIO をトグルするまで(カーネル実行約 400ms)。「5.38→4.75→4.47 秒」と「9,276,375 B を 1.54 秒」は同じブログの Raspbian ベースの段階(HQ camera/display の自動検出無効、initramfs 削除)。「第三者・URL 未取得」とするのは誤りで、出典は同ブログ | [公開出典一覧](sources.md) |
| 起動終点を LCD+キーとする案 | 起動終点は LCD+キーと確定している | ユーザー要件に終点の定義はなく、LCD+キーは暫定案です。設計判断が確定するまでは選択肢を併記します | [公開出典一覧](sources.md) |
| GPIO6 の割り当て | SW_DET と keypad IRQ は GPIO6 を異なる用途で使う | 公式 docs の SW_DET=G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`(L292-293)は同じ GPIO6 で食い違いなし | [公開出典一覧](sources.md) |
| libc 比較の記述 | libc 比較の有無について異なる記述があった | libc 比較は取り込み済みで、未完成とする記述が古いものでした | [公開出典一覧](sources.md) |
| UART 物理ピン番号 | EXT 2.54-14P の UART 物理ピン番号を 13・14 番とした記述 | 12 番と 14 番(右列)。G15(UART_RXD)が 12 番、G14(UART_TXD)が 14 番で、13 番ピンは G7(SPI0_CS1)。物理ピンと GPIO を別列で示し、13 番ピンは G7(SPI0_CS1)と区別します。他の箇所に同じ誤記はありません | [公開出典一覧](sources.md) |
| M5 の `modules/rx8130` を RTC に必須とした記述 | RX8130 専用 driver が必要 | RX8130 は rpi-6.18.y(@2341883)の `rtc-ds1307.c` L1164 の `epson,rx8130` で扱われ(`RTC_DRV_DS1307=m`)、`modules/rx8130` は Makefile とオーバーレイ DTS だけで C ソースはありません。必要なのはドライバではなくオーバーレイです。単体オーバーレイの reg=0x68 と CardputerZero overlay の 0x32 の違いは未解決です | [公開出典一覧](sources.md) |
| 失敗検知・確定条件の扱い | 起動終点が未定なのに、失敗検知・確定条件を確定事項として扱う | 起動終点と設計案が決まるまで、失敗検知・確定条件を保留します | [公開出典一覧](sources.md) |
| M5 の既定 DT における UART | GPIO14/15 に出る UART の種別まで確定している | M5 の既定 DT では serial0 は mini-UART を指しますが、GPIO14/15 に出る UART の種別は未確認です | [公開出典一覧](sources.md) |
| `PYG12(LCD_RST)` の操作 | `disabled-gpios` の index から PYG12 であることまで確認済み | 確認できるのは `disabled-gpios = <&m5ioe1 11 1>` を駆動することで、それが PYG12 に当たるのは index+1 の推論(【推測】)。PYG6(MIC_SW)と GPIO6(SW_DET)は別の信号です | [公開出典一覧](sources.md) |
| mender-convert の公開日と状態 | changelog の日付を公開日とし、compare status を見誤った | mender-convert 5.1.0 の日付 2025-12-01 は changelog の日付で、GitHub release の公開は 2025-12-02T10:38:33Z(= 19:38 JST)です。compare API の status は ahead(ahead_by 17683)で、docs ページの本文も取得して確認しました | [公開出典一覧](sources.md) |
| RX8130 の driver に関する記述 | どの driver を使うか未確認 | `rtc-ds1307.c`(`epson,rx8130`)で扱え、別ドライバは不要です。rtc-ds1307.c の L1470 で確認しました | [公開出典一覧](sources.md) |
| Newlib の Linux 対応 | Newlib を Linux 非対応とする | sourceware のページは bot 防御により取得できず、Linux 対応は【未確認】です | [公開出典一覧](sources.md) |
| `kernel_power_off()` の行番号 | `kernel_power_off()` は L102 | L106(L102 はコメント行)。先頭コメントは L3-L9(S L7、U L8、O L9) | [公開出典一覧](sources.md) |
| ext4 の `data=journal` 削除予告 | v7.2 で削除予定とする | docs.kernel.org の最新版と v7.3-rc7・rpi-7.3.y にあり、v7.2・rpi-7.2.y・v6.18・rpi-6.18.y には記載がありません | [公開出典一覧](sources.md) |
| OpenVPN の ML-KEM の実効既定 | マニュアルの記載がそのまま実効既定になる | ソース(v2.7.6 `ssl.c` L552)は指定時のみグループを設定し、OpenSSL 3.6.4(Buildroot 2026.08 同梱)の既定グループは先頭が `X25519MLKEM768`(`ssl/t1_lib.c` L209)。実接続での使用は未確認 | [公開出典一覧](sources.md) |
| カーネルサイズの数値 | WP-1 の kernel size は 9.8MB | WP-1 のログの `size 0x9af973` = 10,156,403 B(約 10.2MB、9.69MiB)。initramfs 11.7MB(0xb2483c)は正しい | [公開出典一覧](sources.md) |
| GPU 段と kernel サイズの関係 | GPU 段の時間が kernel サイズに連動する | 【推測】サイズ比 1.09 に対し時間比は約 1.7 です。機材と測定区間が異なるため、両者の関係は推測です | [公開出典一覧](sources.md) |
| RPi OS kernel 6.18.50 の確認度 | RPi OS kernel 6.18.50 を一次資料で確認済みとする | 【未確認】（Imager 一覧では版の存在のみ確認できます） | [公開出典一覧](sources.md) |
| OpenVPN の PQ 鍵交換 | OpenVPN に PQ 鍵交換はないと言い切る | マニュアル上の記載はなく、実効既定は OpenSSL 版に依存します。実接続は未確認です | [公開出典一覧](sources.md) |
| `powerfail_suo` の先頭コメント範囲 | URL が O の行(L9)を含まない | URL 範囲を L3-L9 に修正し、O の行を含めます | [公開出典一覧](sources.md) |
| Compute Module Zero のデータシート | RP-009251-DS を CYW43439 のデータシートとし、URL を未確認とする | データシート Release 3 で BCM2837、無線はオプション(CYW43439)、CM0Lite は eMMC なしで SDIO と確認できます。「CM0 内蔵」ではなく「無線搭載版に搭載」と表現します。CM0Lite に無線があるかはデータシートに明記がなく【未確認】です | [公開出典一覧](sources.md) |
| Celeron benchmark の条件 | benchmark の測定条件が不明確 | ChromeOS の Crostini VM 上で測定された値です(gist 本文で確認)。blame には Type=simple の service は測定不能という注意が欠けていたことを man で確認しました | [公開出典一覧](sources.md) |
| `/var` の filesystem | `/var` を tmpfs として扱う | この image では `/tmp`、`/run`、`/dev/shm` が tmpfs mount で、`/var` は tmpfs ではありません | [fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| SD の page size | 多くの SD card の page size は 16 KiB 以上 | 取得した公開資料が示すのは 2 KiB または 4 KiB の例であり、「多くは 16 KiB 以上」とする根拠はありません。個別カードの値は未確認です | [S3 記録](../experiments/2026-10-19-s03-data-ext4-writes.md)、[読み取り専用領域と FS 比較](readonly-data-and-fs.md) |
| CI の `mke2fs` version | PATH の `mke2fs 1.47.2` が image 作成にも使われた | image 作成に使われたのは Buildroot host `output/host/sbin/mke2fs` 1.47.4。PATH 上の version log は誤った binary を示していました | [storage-and-flash.md](storage-and-flash.md)、[Build run](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529) |
| module dependency index より前の状態 | boot smoke test が通るので module autoload も正常 | host depmod に XZ support がなく `.ko.xz` を飛ばし、`modules.dep` が空で `modprobe` できませんでした。実機 autoload への影響は未確認です | [S6 modules.dep 記録](../experiments/2026-10-19-s06-modules-dep-xz.md) |
| NUMA=n の結果 | gzip size が 64,784 B 減った候補は成功 | raw CSV の状態は `QEMU_FAILED`。保持した QEMU log がなく、サイズ差だけで判定できません | [S1 記録](../experiments/2026-10-19-s01-kernel-sweep-trial.md) |
| カメラ電源の GPIO 割当て | 「カメラの power-enable GPIO は回路図から特定できない」 | 以前の記述は PDF の文字列だけを抽出し、回路図を読まずに結論づけていました。C154 V0.6.1 p.10 は `CAM_3V3`、`SSP7615-33DFR`、`R190 100K`、`R192 NC` を示し、LDO の EN は VSYS_5V に pull-up されています。p.5 は CM0 pin 44 と JP5 pin 17 を `CAM_GPIO` と表示します。CM0 DTS は GPIO40 を `CAM_GPIO` と名付け、`&cam1_reg` に `gpio = <&gpio 40 GPIO_ACTIVE_HIGH>` を設定するため、既定の cam1 IMX219 overlay が正しい pin を使います。v5 の GPIO16 は `G16_PY32_RST` で、M5 Makefile の GPIO16-high camera overlay は非 V0_5 側だけで追加されます。v5 に追加 GPIO hog は不要です。【一次】 | [C154 V0.6.1 schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)<br>[CM0 DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts)<br>[M5 CardputerZero Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile) 【一次】 |
| S11 v2 QEMU の patch provenance | v2 の結果を commit 済み QEMU patch の結果として扱った | v2 image は prebuilt layer の QEMU を含み、commit 済み patch から build されたものと確認できません。v2 の測定値は invalid とはせず、別 build の参考値として保持し、patch 適用可能な `c01f6e7` の QEMU で v3 を再測定しました | [S11 記録](../experiments/2026-10-20-s11-qemu-watchdog.md) |

| S21 SysRq-U marker と remount | driver marker は実 remount の証拠 | `dev_emerg()` marker は `handle_sysrq('u')` より前に出ます。kernel action line で判定した再測定では `kernel.sysrq=0` は remount なし 5/5、32 は remount 5/5 でした。製品採否は未決定 | [S21 記録](../experiments/2026-10-21-s21-qemu-sysctl-ramoops.md) |

## 個別訂正の補足

| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| Lite 版の microSD | Lite 版には microSD がない | スロットはあるが、カードは付属しない | [公開出典一覧](sources.md) |
| `PARTITION_WALK` | 適用範囲の明記なし | EEPROM ブートローダー搭載機の機能で、Pi 4 以降が対象。CM0 では使えない | [公開出典一覧](sources.md) |
| tryboot | Raspberry Pi 文書は Pi 4 / 5 を主に扱うとし、CM0 では未検証 | 文書では全モデル対応と記載。CM0 実機での動作は未確認 | [公開出典一覧](sources.md) |
| `powerfail_suo` | 要約は SysRq-U のみと記載 | SysRq-U に加えてバックライト制御と GPIO 操作を行う | [公開出典一覧](sources.md) |
| ES8389 | compatible 値の記載なし | compatible は `everest,es8390` | [公開出典一覧](sources.md) |
| Rugix の Pi 3 対応 | 対応表では Pi 3 が `rpi-tryboot` とする | 【一次】（2026-10-19 確認）Pi 3 は Rugix では `rpi-uboot`（Tier 2）です。これは Rugix の target 制約であり、Raspberry Pi firmware 自体は全モデルで tryboot に対応します。CM0 で Rugix を使う場合は実験的な U-Boot flow が必要ですが、firmware 更新不可のため U-Boot 非採用の MSD 方針とは合いません。MSD 自身の tryboot 設計は影響を受けず、CM0 実機確認は継続します。 | https://rugix.org/docs/bakery/devices/<br>https://rugix.org/docs/bakery/devices/raspberry-pi<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91 |
| `align = 4M` と `kernel8.img` の gzip 再圧縮の状態 | ideas-overview.md に `align = 4M` は「未着手（origin/main 未反映）」、fastboot-ideas.md に gzip 再圧縮は「案・未検証」とあった | どちらも main に実装済みです。`align = 4M` は #19 で `genimage.cfg` に入り、CI が検査しています。gzip 再圧縮は #8 で `post-image.sh` に入り、展開結果を `cmp` で比べています。実機での効果は未確認です（2026-10-20 に main のコードで確認） | [genimage.cfg](../../board/cardputerzero/genimage.cfg)、[post-image.sh](../../board/cardputerzero/post-image.sh) |
