# 訂正済み事項

### 12.2 訂正した旧記述と正しい内容
| 旧記述(v1 または他の調査) | 正しい内容 | 出典URL |
|---|---|---|
| Kickstarter の 3,000/12,000 台を SNS の未検証情報として扱う | **Update 13 は公式更新**の引用(X のリンクカード由来。本文は取得できていない=403) | https://x.com/saitotetsuya/status/2111008950107910198<br>URL未取得(Kickstarter 本文) |
| pi-gen は rpi-v8 カーネルを apt から導入(版の固定なし) | **6.18.39-1+rpt1 を sha256 検証+apt pin 1001+hold で固定**。M5 dtoverlays は `--depth=1` で最新追従 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20 |
| 起動時間の数値(2.1s、5〜6s、3.5s 未満)を同列に並べた | 数値は SoC・条件・終点が異なり**合成不可**。2112ms は 227KB の小型カーネル構成、Linux 可用 7〜9s は自己申告、Pi 3B+ は ARM 開始 6.79s(報告)。数値が不足していたので台帳化 | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| rpi-eeprom の Pi5 stable(2026-09-25)で A/B 更新 | A/B 更新の記載は 2026-05-13 の Pi5 系エントリ。**CM0 には無関係** | https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md (HTTP 200 のみ確認。内容は未読) |
| Mender Client 6.1.0 は二次情報/CM0 向け統合は不明 | **6.1 は Supported(docs.mender.io)、mender-convert に RPi3(64bit)の U-Boot 構成あり。CM0 の構成・動作は未確認**。Buildroot の mender は 3.5.3(古い系列) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://docs.mender.io |
| zram は defconfig 未確認 | **ZRAM=m、ZSWAP=y**(rpi-6.18.y bcm2711_defconfig) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 |
| Buildroot 2026.08 は GCC 16.2.0 が既定(前回報告) | **GCC 既定は 15.3.0**(14.x/16.x は選択式) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6 |
| powerfail_suo は S→U→O(sync/ro/poweroff)を実行 | **実行は 'u'(ro 再マウント)のみ**。's' と 'i' はコメントアウト。冒頭コメントだけが S-U-O | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |
| rpi-image-gen の最新は v2.3.0(cm4/pi4/cm5/pi5 のみ)、issue #153 で image-rota は GPT・BCM2837 は MBR 要 | **最新 v2.8.0(2026-08-13、報告)/master d7616a2**。device 層に pi3/zero2w はあるが、**image-rota は現行 master でも cm4/pi4/cm5/pi5 のみ**(コードで確認)。issue #153 は closed(2026-02-18)のため根拠をコードに変更 | https://api.github.com/repos/raspberrypi/rpi-image-gen/releases<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153 |
| 「検証ボードに RPi が無いから Zephyr 26.04 LTS は非対応」 | 根拠は「v4.4.0 に BCM2710/rpi_zero_2w が無い」。Canonical フォークの中身は未確認 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi |
| CM5 で display_auto_detect=0 の差は 9ms(旧版は確認済み扱い) | 出典を特定できず【未確認】に降格 | URL なし |
| 「GL852G のリセットは PYG3 経由」(推測) | docs に明記:PYG3 は**キーボードとハブの共用リセット** | https://docs.m5stack.com/en/CardputerZero |
| RAUC PR #1599 の状態は未確認 | open・未マージ(2026-10-18) | https://api.github.com/repos/rauc/rauc/pulls/1599 |
| arm_64bit の CM0 対応は未確認 | 対応表に CM0 なし。`[cm0]` フィルタはある | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43 |
| M5 モジュールのカーネル版前提を「報告による」とした記述(v5 の旧記述) | **panel-mipi-dbi-m.c の include は 6.12 で解決せず 6.18 で解決する(一次、13.4A)。M5 コード全般が 6.18 以上必須とは言えない**。メインライン panel-mipi-dbi 経路もある(報告) | https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c |


## 追補に含まれていた事実の訂正

版の履歴や作業記録は除き、そこに記されていた事実訂正だけを整理しています。

| 旧記述 | 訂正内容 |
|---|---|
| Mender を RPi3 の対象外 | mender-convert の README(HEAD 4b3f04a、2026-10-12 コミット)が `raspberrypi/uboot/debian/raspberrypi3_bookworm_64bit_config`(Raspberry Pi 3、Raspberry Pi OS bookworm 64bit)を「officially supported」の Core 構成に載せ、Mender Client 6.1 は 2026-10 にサポート対象(docs.mender.io supported-releases)。Mender Client 6.1.0 は mender.io のブログ(2026-10-16)に記載。CM0 自体の記載と動作は未確認 |
| 「16.2 の powerfail_suo が kernel_power_off を呼ぶ」 | 実行されるのは `handle_sysrq('u')` のみで、`'i'`・`'s'`・`kernel_power_off()` はコメントアウト(powerfail_suo.c @7551854 の L74/L83/L93/L106)。6.3 と一致させた |
| 19.1 で UART0 を PL011 | 公式 DT は `serial0 = &uart1`(mini-UART、`uart1_pins` は空)、`serial1 = &uart0`(PL011、GPIO30〜33=BT)。公式 pi-gen は cmdline の `console=serial0,115200` を除去。監査報告は「公式 pi-gen に enable_uart が無い」としたが、一部訂正:pi-gen は M5 の Makefile(`config_setup`)経由で `enable_uart 1` を [all] に設定する(最終 config.txt は未検査) |
| 「OpenSSH の既定は AES-GCM 候補」 | `chacha20-poly1305@openssh.com` が先頭(myproposal.h、V_10_5_P1)。OpenVPN は暗号の設定が要る(`--data-ciphers` 既定は AES-GCM 先頭) |
| 20.5 の alias unmap 記述は不正確 | 導入(63e0b6a5b693)と revert(f102131c842d)はともに v7.2-rc1、再適用(fb0f3ef5601a)は v7.3-rc1 に入る(v7.2 には入らない)。`rpi-7.2.y` の mmu.c は data/bss を「read-only で map」する旧コードで影響なし、`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid`)を含む。compare API と各ブランチの raw で確認(再適用で RPi3/4 の問題が解消したかはコミットメッセージから読み取れず未確認のまま) |
| 「CachyOS の遅延は 7.2 カーネルの回帰」と読める書き方は誤解を招く | 投稿者が BIOS で TPM を無効にして解消(2026-09-10)。Omarchy #6996 は Omarchy 4.0.0-1 / Linux 7.1.8、約 266MiB の initramfs と `initramfs_async=0` の x86 事例。Omarchy の URL はリポジトリ移転で旧組織配下が 404、現行は `omacom/omarchy` |
| KittenLabs の数値を条件なしで書いたのは不備 | <3.5 秒は Zero 2 W+Buildroot 2024.02.1(フル glibc)、カーネル 8.5MiB(非圧縮。Raspbian 標準は 25MiB)、KASLR 無効、Spectre 等の緩和無効、sound/USB/HID/DVB/video・fb/RAID/高度なネットワーク機能無効、モジュール非圧縮、測定は電源投入から userspace が GPIO をトグルするまで(カーネル実行約 400ms)。「5.38→4.75→4.47 秒」と「9,276,375 B を 1.54 秒」は同じブログの Raspbian ベースの段階(HQ camera/display の自動検出無効、initramfs 削除)。v4 の「第三者・URL 未取得」は誤りで、出典は同ブログ |
| 15.1 で終点=LCD+キーをユーザーの要件 | ユーザー発言に終点の定義はなく v4 の仮置き。R12 とは両立しない(両案を併記、「確定」なし) |
| 22 章が GPIO6 を食い違い・未解決 | 公式 docs の SW_DET=G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`(L292-293)は同じ GPIO6 で食い違いなし |
| その他の記述 | 旧記述 17 章と 23 章の矛盾(17 章は libc 比較を取り込み済み、23 章は未完成と書いていた)は 23 章が古かった。23 章を訂正 |
| 19.1 で EXT 2.54-14P の UART を物理ピン番号を 13・14 番 | 12 番と 14 番(右列)。G15(UART_RXD)が 12 番、G14(UART_TXD)が 14 番で、13 番ピンは G7(SPI0_CS1)。物理ピンと GPIO を別列の表にし、docs 表の行番号を併記(19.1、13.4A V6A-001)。他に同じ番号を再掲した箇所は全文検索で 0 件 |
| 14.3 の RTC 行でM5 の `modules/rx8130` を必須 | RX8130 は rpi-6.18.y(@2341883)の `rtc-ds1307.c` L1164 の `epson,rx8130` で扱われ(`RTC_DRV_DS1307=m`)、`modules/rx8130` は Makefile とオーバーレイ DTS だけで C ソースは無い(@7551854)。必要なのはドライバではなくオーバーレイ。5 章の記述と揃えた。単体オーバーレイの reg=0x68 と CardputerZero overlay の 0x32 の食い違いを UN-26 に追加 |
| 18.1 の失敗検知・確定が、未決の D1 を決定済みとして「終点到達(案 A 専用の E1)」を使っていた | D1 が決まるまで保留(18.1 冒頭の注、項目 2・3・4) |
| H.2 #3 の見出しで UART の種別を断定したのは過大 | 「M5 の既定 DT では serial0 は mini-UART を指す」までで、GPIO14/15 に出る UART の種別は未確認(UN-19)。19.1 の留保と一致させた |
| 6.3 で「PYG12(LCD_RST)の操作」を確認済みブロックに入れた | 確認できるのは `disabled-gpios = <&m5ioe1 11 1>` を駆動することで、それが PYG12 に当たるのは index+1 の推論(【推測】)。UN-25 の PYG6(MIC_SW)と GPIO6(SW_DET)の混同も直した(別物) |
| その他の記述 | 旧記述の mender-convert 5.1.0 の日付 2025-12-01 は changelog の日付で、GitHub release の公開は 2025-12-02T10:38:33Z(= 19:38 JST)。併記した。13.4A V5A-023 の判定記述は誤りで、compare API の status は ahead(ahead_by 17683)。V5A-048(docs ページ)は v5 では到達確認のみだった旨を訂正し、v6 で本文を再取得した |
| 5.7 の RX8130 の記述(どのドライバを使うか未確認)は 12.6 #2・14.3 と食い違っていた | `rtc-ds1307.c`(`epson,rx8130`)で扱え、別ドライバは不要。アンカーも ZRAM の行から RTC の L1470 に直した |
| 17.2 の Newlib「linux 無し」を一次 | sourceware のページは bot 防御ページで取得できず【未確認】(13.4B V5B-181) |
| の `kernel_power_off()` の行番号(L102) | L106(L102 はコメント行)。12.5、V5A-043、15 章の表を直した。先頭コメントは L3-L9(S L7、U L8、O L9) |
| の「ext4 の data=journal 削除予告は 7.2.x にある」 | docs.kernel.org の最新版と v7.3-rc7・rpi-7.3.y にあり、v7.2・rpi-7.2.y・v6.18・rpi-6.18.y には無い(6.1) |
| の OpenVPN の ML-KEM に関する記述は、マニュアルの文面を引き写したもので実効既定ではなかった | ソース(v2.7.6 `ssl.c` L552)は指定時のみグループを設定し、OpenSSL 3.6.4(Buildroot 2026.08 同梱)の既定グループは先頭が `X25519MLKEM768`(`ssl/t1_lib.c` L209)。実接続での使用は未確認 |
| のカーネルサイズ(9.8 系の数値) | WP-1 のログの `size 0x9af973` = 10,156,403 B(約 10.2MB、9.69MiB)。initramfs 11.7MB(0xb2483c)は正しい |
| GPU 段がカーネルサイズに連動すると述べたのは根拠不足 | 【推測】(サイズ比 1.09 に対し時間比 約 1.7、機材も区切りも異なる)。5.2 の注、F-5、14.2 の式に反映 |
| 20.2 が RPi OS の kernel 6.18.50 を一次 | 【未確認】(Imager 一覧の版の存在のみ)。5.x・13.2 N27 と揃えた |
| 21.5 の本文が、表と食い違い、OpenVPN を PQ 無しと言い切っていた | 「マニュアル上は無し・実効既定は OpenSSL 版依存・実接続は未確認」(表・H.2 #6・UN-27 と一致) |
| 先頭コメントを L3-L9 と書きながら URL の範囲が L8 までで、O の行(L9)を含まなかった | URL も L3-L9(13.1 の PF 行と 13.4B の V5B-086。後者は GET 時の URL との差を 13.4D 冒頭に注記) |
| N7・3 章の表で、RP-009251-DS を CYW43439 のデータシートとし、URL 未確認 | Compute Module Zero(CM0)のデータシート Release 3。URL を判明させて取得し、BCM2837、無線はオプション(CYW43439)、CM0Lite は eMMC なしで SDIO、を確認した(13.4A V9A-001)。「CM0 内蔵」も「無線搭載版に搭載」に直した。CM0Lite に無線が無いかはデータシートに明記がなく未確認。UN-04 に版の別を追記 |
| 17.3 の Celeron の値は測定条件が書かれていなかった | ChromeOS の Crostini VM 上での測定(gist 本文で確認、V9A-005)。16.1 の blame には、Type=simple のサービスは測定不能という注意が欠けていた(man で確認、V9A-004) |

## 事前レポートの誤りに関する追記訂正

| 項目 | 事前レポートの記述 | 訂正後 |
|---|---|---|
| Lite 版の microSD | Lite 版には microSD がない | スロットはあるが、カードは付属しない |
| `PARTITION_WALK` | 適用範囲の明記なし | EEPROM ブートローダー搭載機の機能で、Pi 4 以降が対象。CM0 では使えない |
| tryboot | Raspberry Pi 文書は Pi 4 / 5 を主に扱うとし、CM0 では未検証 | 文書では全モデル対応と記載。CM0 実機での動作は未確認 |
| `powerfail_suo` | 要約は SysRq-U のみと記載 | SysRq-U に加えてバックライト制御と GPIO 操作を行う |
| ES8389 | compatible 値の記載なし | compatible は `everest,es8390` |
