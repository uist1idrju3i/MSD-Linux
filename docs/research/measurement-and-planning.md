# 未確認事項・測定・調査限界

## 10. 未確認事項の整理(旧 U 表の更新)

| 旧 # | 事項 | 現状 | 出典URL |
|---|---|---|---|
| U2 | CM0 が arm_64bit の対応リストに入っているか | **解消**:対応表に CM0 なし(5.4 節)。arm_64bit=1 か kernel8.img 明示が必要。実機動作は未確認 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| U6 | rpi-6.18.y の ZRAM/FRAMEBUFFER_CONSOLE | **一部解消**:ZRAM=m、ZSWAP=y(6.6 節)。FRAMEBUFFER_CONSOLE の最終有効性は .config 未確認 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 |
| U7 | RAUC PR #1599 | **解消**:open・未マージ(2026-10-18、7.3 節) | https://api.github.com/repos/rauc/rauc/pulls/1599 |
| U8 | 404 の原因 | **一部解消**:404 は再確認、内容は Wayback(報告)。原因は未確認 | https://github.com/CardputerZero/cardputer-zero-os |
| U10 | Ubuntu Core/Minimal Ubuntu/BusyBox/Yocto | **解消**(3 章)。ただし起動時間と A/B の実証は未確認 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| U12 | stable 7.2.11 | **解消(報告)**:2026-10-15(kernel.org、報告) | https://www.kernel.org/releases.json |
| U9 | microSD FTL の一次資料(LWN/Bootlin/JEDEC) | 未確認(取得していない) | URL未取得 |
| U11 | MCUboot の arm64 実績 | 未確認 | URL未取得 |

### 10.1 現在残る【未確認】一覧
| # | 事項 | 出典URL |
|---|---|---|
| U1 | **BCM2837(CM0)で tryboot/autoboot.txt が動くか**(実機) | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc |
| U3 | Wi-Fi の chip ID(43430/43436s/43439)(実機) | https://docs.m5stack.com/en/CardputerZero |
| U4 | HDMI コネクタ形状(Type A/D) | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| U5 | CM0 での GPT の挙動 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| U8' | cardputer-zero-os/shell の 404 の原因(削除/非公開/改名) | https://github.com/CardputerZero/cardputer-zero-os |
| U9 | microSD FTL の電源断挙動の一次資料 | URL未取得 |
| U11 | MCUboot の arm64 実績 | URL未取得 |
| U13 | CM0 での起動時間(ベースライン)。CM0 の GPU 段が M5 の自己申告値どおりか | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| U14 | 実際に有効な FRAMEBUFFER_CONSOLE と `fbcon=map:off` の扱い | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1135<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247 |
| U15 | overlay 名の不整合(cardputerzero-overlay と -v3/-v5)の正誤 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20 |
| U16 | image-rota 相当を zero2w/pi3 で動かした場合の挙動、Canonical Zephyr フォークの内容 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11 |
| U18 | Ubuntu Core 26 の A/B 相当機構と Pi 3/Zero 2 W での実起動(公式テスト対象は Pi4/5=報告) | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json<br>最小 RAM・how-to:URL なし(【報告による】の部分) |
| U19 | `-mcpu=cortex-a53`/LTO の効果、dirty/printk 系 sysctl の根拠 | URL未取得 |
| U20 | fork(vicliu624、stanley-fork)の中身 | https://github.com/vicliu624/cardputer-zero-os |

### 10.2 実機が届いたら最初に測る項目(優先順の案)
1. **公式イメージの起動時間**(systemd-analyze、vclog)。ベースライン
2. **tryboot/autoboot.txt の動作**(A/B 方式の成否を左右する)
3. **CM0 の arm_64bit/kernel8.img の挙動**
4. **kernel8.img の非圧縮と gzip の比較**
5. **vc4 除去の効果**(HDMI/cma を外した場合)
6. **Wi-Fi の chip ID**
7. **GL852G のリセット挙動**(PYG3 はキーボードと共用)
8. **電源断試験**(書込み中/アイドル時の電源断を多数回)

---

## 11. 推奨案と次の選択肢

> 以下は【**作成者の見立て**】に基づく推奨です。**方針は山城さんの合意をいただいてから決めます。**

### 11.1 推奨案(暫定)
| 項目 | 推奨 | 推奨理由 | 出典URL |
|---|---|---|---|
| 方向性 | **Linux** | Zephyr は 26.04 LTS も v4.4.0 も CM0 で動く根拠がなく、upstream main も SDHCI 未対応(報告)で microSD 不可 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w |
| ベース | **Buildroot が第一候補**、Yocto(meta-raspberrypi wrynose、raspberrypi0-2w-64)が有力な代替 | CLI 専用の最小構成、起動短縮、ro rootfs を設計で詰めやすい。Ubuntu Core/Minimal Ubuntu は A/B と起動時間の根拠が取れていない | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf |
| カーネル | **rpi-6.18.y をコミット固定**(6.18.57) | M5 の panel-mipi-dbi-m.c が rpi-6.12.y に無いヘッダを include する(6.12 では解決せず、6.18 にはある。一次。6.13〜6.17 は未確認)、公式 pi-gen も 6.18.39 固定。6.18 は LTS(2028-12、報告) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3 |
| rootfs | **SquashFS(または EROFS)ro+overlayfs(upper は tmpfs/zram)+小さな ext4 RW データ** | RPi 公式ホワイトペーパーの推奨と一致(報告) | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| A/B | **MBR+tryboot/autoboot.txt+RAUC custom バックエンド**(試行カウンタとフォールバックは自前) | U-Boot 無しで GPU 段より後の追加遅延を避けられる。**ただし公式 A/B(image-rota)は GPT かつ Pi4/5 クラス限定で CM0 向けの公式裏付けは無く、BCM2837 での tryboot は未検証**。代替は U-Boot 方式(Rugix では Zero 2 W = rpi-uboot。Pi 3 は rpi-tryboot。v4 訂正) | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/rauc/rauc/pulls/1599 |
| UI | **CLI 専用**(HDMI/vc4 は外す方向で実測評価) | R3 | 出典なし(ユーザー指示/作成者の判断) |
| 電源断 | 上記の ro 設計に加え **GPIO6 のスイッチ検知で正常停止**を併用 | powerfail_suo は 'u' のみで sync も poweroff もしないため、自前で拡張が要る。電池の突然の抜けは ro 設計で備える | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |

### 11.2 次の選択肢(ご判断をお願いします)
- **① Buildroot 設計案を書いてよいか**(パーティション表、config.txt、defconfig 方針、RAUC custom バックエンド仕様、起動短縮の手順。コンパイルは行いません)
- **② Yocto(wrynose)と Rugix(Pi 3=tryboot / Zero 2 W=U-Boot)を同じ観点で詳細比較するか**
- **③ 実機の到着を待ち、10.2 節の測定を先に行う**(tryboot の可否とベースライン起動時間の確認後に①または②)

※ ①と②は並行して進めることもできます。

> **記号の注意(v6)**:旧版は ①②③ を A/B/C と書いていました。ユーザーの t26u「Bです。」は**旧メニューの B(Ubuntu Core/Yocto の調査)** への回答で、本節の②とは別です(旧メニューの文面は会話ログ行 37(行 36 は作成担当の要約)にあり、A=Buildroot 設計案、B=Ubuntu Core/Yocto の調査、C=実機の到着を待って先に測る。t26u は行 40、返信「B を進めます」は行 41。0 章の脚注)。

### 11.3 未決の設計論点と選択肢(v5 追加。**どれも「確定」ではなく、山城さんの合意が要る**)
| # | 論点 | 選択肢(それぞれの根拠と、書けていない前提) | 関連要件 | 詳細(双方向) | 状態 |
|---|---|---|---|---|---|
| D1 | 起動の終点の定義 | **A**:LCD にプロンプト+キー入力可まで(体感に直結。ただし M5IOE1→LCD/キーボードの鎖を早期に読む必要=R11/R12 と相反)/ **B**:init(PID1)が終点マーカーを書くまでを終点とし、LCD・キーボードは終点後に遅延読込(R12 に沿う。体感指標として「プロンプト+キー可」までの時間を別に併記)/ **C**:両方を測る | R1, R11, R12 | 14.3, 15.1 | 未決 |
| D2 | rootfs の読取専用 FS | **SquashFS**(`-sort` で優先度の高いファイルを先頭へ)/ **EROFS**(`-z` を指定すれば圧縮、`--sort` は tar 入力のみ)。実機で 2 構成を比較する案。どちらが速いかは未測定 | R2, R7, R17 | 16.4 | 未決 |
| D3 | init と libc | systemd 最小化+glibc(M5 の udev ルール・unit をそのまま使える)/ BusyBox init+eudev+musl 静的(軽いが udev ルール移植と NSS 非対応を負う)/ 自作 init(最終手段)。**17 章と 16.2 の結論は同じ向き(全機能維持なら glibc+systemd)だが、起動時間は未測定** | R1, R15, R18 | 16.2, 17.5 | 未決 |
| D4 | A/B 方式 | MBR+tryboot/autoboot.txt+RAUC custom(U-Boot なしで GPU 段後の遅延を避けられるが **BCM2837 の tryboot は未検証**)/ U-Boot 系(Mender の mender-convert は RPi3 64bit を公式構成に持つ。RAUC も可。段が増える)/ Rugix(Pi 3=rpi-tryboot、Zero 2 W=rpi-uboot)。**「必ず前の面へ戻せる」とは言えない**(tryboot・WDT が CM0 で効くことが前提で未検証。FAT の boot 領域は単一障害点) | R4, R13 | 7 章, 18 章 | 未決 |
| D5 | カーネル版 | **6.18.y**(VOLUNTARY 選択可、M5 モジュールの前提に合う)/ **7.2.y・7.3.y**(PREEMPT は LAZY/FULL のみ。7.1 で DRM API が変わり M5 の `panel-mipi-dbi-m.c` は未ビルド確認。7.3 は alias unmap の再適用を含み CM0 での起動が未確認)。同一構成での比較はあり | R5, R10 | 20.2, 20.3, 20.5 | 未決 |
| D6 | 開発中ログの置き場 | 案 3:開発中は ext4 に書き、電断試験時は専用領域/pstore へ切替(R14)。R2(完全 ro)との緊張は「モード切替でビルドを分ける」ことで扱う案。測定条件が変わる点は記録が要る | R2, R14 | 19.2, 19.3 | 未決(ユーザーは t59u「案3で良いのでは？」と疑問形で案 3 を支持する発言をしたが、同意の確定ではない。実装方式も未決) |
| D7 | SSH 実装 | Dropbear(小さい。PQ 既定有効)/ OpenSSH(標準的。依存大。PQ 既定有効)。VPN は WireGuard(カーネル内蔵。ChaCha)/ OpenVPN(要 `--data-ciphers` 設定)。**終点の後に socket activation で起動**する案 | R18 | 21.3, 21.5 | 未決 |
| R21 | イメージに名称を付けたいという要件。名称の由来は RESEARCH.md を参照 | t69u〜t76u | 24 | 名前の決定は山城さん |

### 11.4 山城さんに決めていただくこと(着手前)
1. **D1(終点の定義)**:A / B / C のどれにするか。B または C なら 14.3 の built-in 集合が小さくなり、R11 の「極限まで小さく」に近づく。
3. **11.2 の①②③**:設計案を書いてよいか、実機を待つか。
4. D2〜D7 は、実機測定の結果を見てから決めてもよいか(推奨:測定可能な D2・D3・D5 は実機後、D4 は実機で tryboot を試してから)。

### 11.5 推奨・選択肢と 14〜21 章の対応(双方向)
| 11 章の項目 | 関連する章(その章の先頭にも 11 章への戻りリンクを置いた) |
|---|---|
| 11.1 カーネル/UI/D1/D5 | 14(縮小)、15(終点と測定)、20(カーネル比較・PREEMPT) |
| 11.1 rootfs/D2 | 16(ユーザー空間・SquashFS・EROFS)、6 章 |
| 11.1 A/B/D4、電源断 | 18(失敗検知と自動復旧)、7 章、6.3 |
| D3(init・libc) | 16.2、17 |
| D6(開発中ログ) | 19 |
| D7(SSH/VPN) | 21(21.5 に PQ 鍵交換を追加) |
| D8(名前) | 24 |

---

## 19. 開発中の観測手段(提案 6)

> 11 章との対応: 11.3 D6(開発中ログ)(11.5 に対応表)

### 19.1 UART(CM0 の GPIO で使えるか)
UART の既定・ピン・コンソールは 3 種の出典(公式 DT / 公式イメージ設定 / 公式 docs)で確認しました。
| 事実 | 出典URL | 確認度 |
|---|---|---|
| **公式 docs**:`G14_UART_TXD` / `G15_UART_RXD` が **HY2.0-4P ポート**(G4 の `G4_I2C/UART_SW` が LOW=UART(既定)、HIGH=I2C1)と **EXT 2.54-14P の物理ピン 12 と 14**(右列。G15=UART_RXD が 12 番、G14=UART_TXD が 14 番)に出ている。ピン番号と GPIO 番号は下の別表。HY2.0 は 5V 出力あり(M5IOE1 の GROVE_EN) | https://docs.m5stack.com/en/CardputerZero | 一次(v6 で本文を再取得、2026-10-18 21:3x JST、HTTP 200。v5 は到達のみ) |
| **回路図 V0.6.1**(ローカル取得 PDF のテキスト):ネット名 `G14_UART_TXD`(PIN110)、`G15_UART_RXD`(PIN108)、`NLG140UART0TXD`/`NLG150UART0RXD`、HAT 側 `HAT_UART_TXD` | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 一次(ローカル PDF。v5 では再読せず) |
| **公式 DT**(`arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts`、rpi-6.18.y @2341883)L14-16:`serial0 = &uart1;`(mini-UART)、`serial1 = &uart0;`(PL011)。uart1 は `brcm,bcm2835-aux-uart`(bcm283x.dtsi L385-387)、`uart1_pins` は空。uart0(`arm,pl011`、bcm283x.dtsi L304-305)は GPIO30〜33(BT 用)。**つまり `serial0`(= `/dev/serial0`)は mini-UART** | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L14-L16 | 一次(HTTP 200、v5 で行を確認) |
| **公式イメージ設定(pi-gen、cardputerzero_v1.0 @791a985)**:`stage2/05-cardputerzero/01-run.sh` が M5 の `make … config_setup` を実行し、M5 の `modules/CardputerZero/Makefile` L74 が `rpi-config.py --no-backup section-set all enable_uart 1` を実行(= **ビルド時に `enable_uart=1` を [all] に設定**。最終 config.txt は v5 では未検査)。cmdline の `console=serial0,115200` は `02-run.sh` と `export-image/04-set-partuuid/00-run.sh` で**除去**され、`tools/verify-image.sh` L158-161 が除去を検査 | pi-gen @791a985 の `tools/verify-image.sh`、M5 @7551854 の `modules/CardputerZero/Makefile`(ローカル clone の該当行。リポジトリは 13.1 の PIGEN / M5 行) | 一次(スクリプトの実行行) |
| **公式 pi-gen の文書と実装の食い違い**:`docs/CARDPUTERZERO-IMAGE-DESIGN.md` L41 は「`console=serial0,115200` を保持」と書くが、スクリプトは除去する。**実装(スクリプト)を実際の挙動とみなし、文書は古い可能性がある**(どちらが意図かは未確認) | 同上 | 一次(2 ファイルを比較) |
| **RPi 公式 docs**:`configuration/reference.adoc` L1408「If the primary UART is `ttyAMA0`, `enable_uart` defaults to 1 (enabled), otherwise it defaults to 0 (disabled)… `enable_uart=1` implies `core_freq=250` (unless `force_turbo=1`). In some cases this is a performance hit」。`config_txt/boot.adoc` L98「`enable_uart=1` (in conjunction with `console=serial0,115200` in `cmdline.txt`) requests that the kernel creates a serial console, accessible using GPIOs 14 and 15」 | raspberrypi/documentation @ddea98e(ローカル clone の該当行) | 一次(sparse clone の行確認) |
| **帰結**:**公式 DT では `serial0`(`/dev/serial0`)は mini-UART(`uart1`)を指す。GPIO14/15 に出る UART が mini-UART か PL011 かは、DT が uart0 を GPIO30〜33(BT)、`uart1_pins` を空としているため DT だけでは断定できない(M5 の overlay/config での pinmux は未確認)。** 一次 3 件(DT・pi-gen・docs)が揃って言えるのは「console は serial0(mini-UART)を前提とし、pi-gen は cmdline からその console を外す」まで。`enable_uart=1` は(プライマリ UART が mini-UART の場合)コア周波数を 250MHz に固定する(docs)=**コア周波数を上げる最適化(R1)と干渉しうる**。開発用コンソールとして使うには (1) HY2.0 は I2C1(G2/G3)と共用で `G4` の切替が必要、(2) 3.3V ロジック、(3) mini-UART の速度条件(`core_freq`)に注意 | — | 推測(GPIO14/15 の pinmux は未確認) |

#### EXT 2.54-14P と HY2.0-4P の UART 関連ピン(物理ピンと GPIO を別列。出典 docs の表の行番号を併記)
| コネクタ | 機能 | **物理ピン番号** | 列(左/右) | **GPIO 番号** | docs 表の行 |
|---|---|---|---|---|---|
| EXT 2.54-14P | UART_RXD | 12 | 右 | G15 | 「EXT 2.54-14P」表のデータ 6 行目(左 11=G9 SPI0_MISO、右 12=G15) |
| EXT 2.54-14P | UART_TXD | 14 | 右 | G14 | 同 7 行目(左 13=G7 SPI0_CS1、右 14=G14) |
| EXT 2.54-14P | (参考)I2C1_SDA / SCL | 8 / 10 | 右 | G2 / G3 | 同 4・5 行目 |
| HY2.0-4P | G14_UART_TXD(I2C 時は G2_I2C1_SDA) | (番号の記載なし)Yellow | — | G14 | 「HY2.0-4P」表の 1 行(列順は Black=GND、Red=5V、Yellow、White) |
| HY2.0-4P | G15_UART_RXD(I2C 時は G3_I2C1_SCL) | (番号の記載なし)White | — | G15 | 同 |

出典: https://docs.m5stack.com/en/CardputerZero(HTTP 200、v6 の再取得は 2026-10-18 21:3x JST。13.4A V6A-001)。HY2.0 は docs が色(Black=GND、Red=5V、Yellow、White)の列で示すだけで物理ピン番号の記載が無いため、番号は書かない。v5 のピン番号の記載は誤りで、13 番ピンは G7(SPI0_CS1)。

### 19.2 その他の手段
| 手段 | 事実 | 出典URL | CM0 での注意 |
|---|---|---|---|
| USB ガジェットシリアル | `g_serial` で `/dev/ttyGS0` を作れる(`modprobe g_serial`) | https://docs.kernel.org/usb/gadget_serial.html | **Slave モードのとき右側 USB-C が CM0 に直結(OTG)**。Host/Slave スイッチが Slave だとハブ・Ethernet・USB-A は使えない(公式 docs)。M5 の pi-gen の config は `dtoverlay=dwc2,dr_mode=host`(ローカル clone で確認)なので、ガジェット運用には `dr_mode=peripheral` 相当が要る(推測・未確認) |
| Ethernet(SR9900A)経由 SSH | 公式:USB2.0→Ethernet チップ SR9900A、10/100M。Host モードのみ | https://docs.m5stack.com/en/CardputerZero | ドライバは USB ID 0fe6:9900 なら r8152 系(14.3。実 ID は未確認)。SSH は 21 章 |
| pstore/ramoops | RAM 上の予約領域にクラッシュログを残し再起動後に読む。`reserved-memory` か `mem=` で領域を指定 | https://docs.kernel.org/admin-guide/ramoops.html / https://docs.kernel.org/admin-guide/pstore-blk.html | **電源断では RAM が消えるため、残るのは panic/ウォッチドッグ等の「リセット再起動」のみ**(RAM 保持特性は未確認)。RPi のファームが DT に付与するメモリ配置との衝突は未確認 |
| SD 専用領域への直書き | ファイルシステムを介さず、未使用のパーティション/生セクタに固定フォーマットでログを書く(自作) | — | 案(推測):電断試験でも FS 破損の影響を受けないが、SD のページ書込み中断リスクは残る(v3 6.4)。実装は未着手 |
| 開発中のみ ext4 にログ(案 3) | 開発ビルドだけ RW パーティションに `data=ordered` の ext4 を置く(ext4 のマウントオプション文書:https://docs.kernel.org/admin-guide/ext4.html) | https://docs.kernel.org/admin-guide/ext4.html | 量産ビルドには含めない。測定結果に I/O が混ざるため、起動時間測定時は無効化 |
| sysrq | `s`(sync)/`u`(remount ro)/`b`(reboot)/`o`(poweroff) | https://docs.kernel.org/admin-guide/sysrq.html | 電断試験のソフトな近似にのみ使用(本物の電断とは別物) |

### 19.3 電源断試験時の切替方針(見立て=推測)
- **起動時間測定モード**:ログ最小(quiet)、シリアル接続は固定、ext4 ログ無効。
- **電断試験モード**:UART は**外す/読み取り専用** にして給電経路を分離(USB-UART の給電が基板に回り込むと電断にならない)。ログは pstore/SD 直書き/電断後に外部から回収できる形で。
- **障害解析モード**:UART + printk 全開 + ext4 ログ有効。
- モードは SD 上のフラグ(または別ビルド)で切替え、**同一ビルドで測定条件が変わらないこと**を試験記録に書く。

## 23. 調査範囲・未調査・限界(v4 の記述を v5 で更新)

**調査済み(v4 まで)**:kernel.org docs(kbuild/kconfig、kernel-parameters、ramoops/pstore、watchdog、sysrq、bootconfig/boot-time trace、ext4、overlayfs、SquashFS、EROFS、USB gadget serial)、EROFS FAQ、squashfs-tools 4.7.5/4.7.6 USAGE と mksquashfs.1、man7(systemd-analyze、systemd.socket/service、sd_notify、fanotify、blktrace、strace、readahead)、BusyBox FAQ、Dropbear README/SMALL/default_options、WireGuard 公式(performance/install/quickstart)、musl wiki、mimalloc README、M5 公式 docs(CardputerZero)、M5 overlay/モジュール/udev ルール(@7551854)、raspberrypi/linux の Kconfig 等(K618/K72)、raspberrypi/documentation の boot.adoc/autoboot.adoc。


**v5 で解消した v4 の未調査**:libc 比較(17 章に取り込み済みで、v4 の 23 章の記述が古かった)、mkfs.erofs の man(`--sort`)とソース、OpenVPN の暗号選択(`--data-ciphers`)、UART の PL011/mini-UART(19.1)、`-sort` の向き。

**依然として未取得・未調査(25.3 に番号付き)**:
- bootchart(man7 は HTTP 404)、OpenSSH sshd の man(接続不可)、RPi の processors ページ(403)、Arm の ID_AA64ISAR0_EL1 定義ページ(403)、Broadcom/RPi の BCM2837 暗号拡張に関する**メーカー一次仕様**。
- `systemd.timer` 本文、BusyBox の NOFORK/NOEXEC 設定、mdev の仕様。
- WireGuard/OpenVPN/Dropbear/OpenSSH の CM0 実測(公表値も未発見)。
- IR・カメラの DT の所在、brcmfmac のファームウェア取得元、SR9900A の実際の USB ID。
- 7.2/7.3 の RPi `bcm2711_defconfig` の PREEMPT 値(sparse clone の範囲外)。
- 実機測定は全て未実施(実機未入手)。したがって**速度効果は全て推測**。

### 25.3 残る未確認一覧(番号付き。v9 時点)
| # | 未確認の内容 | 関連章 |
|---|---|---|
| UN-01 | BCM2837 での tryboot/autoboot.txt の動作、再起動での復帰、ウォッチドッグ | 7, 18 |
| UN-02 | CM0 での起動時間のベースライン、各最適化の実測効果(実機未入手) | 全般 |
| UN-03 | CM0 での `kernel8.img`/GPT/`arm_64bit` の起動可否 | 7, 8 |
| UN-04 | Wi-Fi チップの型番(CM0 データシートは無線搭載版が CYW43439。無線版か Lite・無線なし版かの別、実機の chip ID は未確認)、HDMI コネクタ形状、IR・カメラの DT の所在 | 2, 14 |
| UN-05 | fbcon/FRAMEBUFFER_CONSOLE の要否と overlay 名の不整合 | 14 |
| UN-06 | image-rota 相当の Zero 2 W/Pi 3 での挙動、Canonical Zephyr の内容 | 7, 3 |
| UN-08 | Ubuntu Core 26 の A/B 相当と Pi 3/Zero 2 W での実起動 | 3 |
| UN-09 | `-mcpu`/LTO/sysctl 等の効果 | 14, 16 |
| UN-10 | vicliu624 fork の中身、`CardputerZero/cardputer-zero-os` が 404 の理由 | 8 |
| UN-11 | microSD の FTL・電断耐性の一次情報 | 18 |
| UN-12 | MCUboot の arm64 実績 | 7 |
| UN-13 | BCM2837 に AES/SHA 命令が無いことのメーカー一次仕様(A53 の Crypto Extension がオプションであることは DDI 0501F で確認済み。BCM2837 が実際に載せていないことの一次仕様は未取得。二次:RPi フォーラムの報告) | 21 |
| UN-14 | SSH/VPN/PQ の CM0 実測、古いクライアントとの PQ 互換性、OpenVPN で ML-KEM を使えるか | 21 |
| UN-15 | 7.3(alias unmap 再適用後)の CM0 起動、7.x での M5 モジュールのビルド可否、7.2/7.3 の PREEMPT 値 | 20 |
| UN-17 | M5Stack の名称利用ガイドライン原文(docs.m5stack.com/en/brand は 404) | 24 |
| UN-18 | Kickstarter(403)、RPi フォーラム t=207888/263234/376022(403/取得不可)、techfeed(タイトルのみ)ほか 13.4B の「取得できず」 | 13 |
| UN-19 | 最終 config.txt の `enable_uart`、GPIO14/15 の pinmux(mini-UART か PL011 か)、pi-gen の文書と実装のどちらが意図か | 19 |
| UN-20 | SR9900A の実際の USB ID(0fe6:9900 か) | 14, 19 |
| UN-21 | 再適用後の alias unmap が RPi 3/4 の KVM 問題を解消したか | 20 |
| UN-22 | KittenLabs の `core_freq=550` が最終の 3.5 秒に含まれるか | 5, 22 |
| UN-23 | 開発ログ方式(D6)の電断試験時の実装 | 11, 19 |
| UN-24 | rpi-6.13〜6.17 に `drm_client_setup.h` があるか(6.12 は無し・6.18 は有り) | 5 |
| UN-25 | `powerfail_suo` の `disabled-gpios = <&m5ioe1 11 1>` が M5IOE1 の PYG12(LCD_RST、docs 記載)に当たるかの対応(index+1 の推論で未確認。**GPIO6=SW_DET と PYG6=MIC_SW は別物** で、混同しない) | 6.3、22 |
| UN-26 | RX8130 の I2C アドレス:CardputerZero overlay は 0x32、単体 `modules/rx8130` は 0x68(実機は未確認) | 14.3 |
| UN-27 | OpenVPN 2.7.6 + OpenSSL 3.6.4 の実接続で ML-KEM(X25519MLKEM768)が使われるか(ソース読みのみ。CM0 での所要時間も未測定) | 21.5 |
| UN-28 | WP-1 の Pi 3B+ ログで kernel の `Loaded` 4.131 s から `Device tree loaded` 6.760 s までの 2.63 s の内訳、GPU 段とカーネルサイズの関係(実機で同一構成のサイズ違いを測る) | 5.2, 14.2 |
| UN-29 | Newlib に Linux 用の sys ディレクトリが無いか(sourceware の取得ができず) | 17.2 |
| UN-30 | (v9 で解消)RPi OS Trixie 2026-10-06 の kernel 版は 6.18.50(公式 release_notes.txt で確認)。イメージ内の実際のカーネルパッケージ版は実機・イメージ展開では未確認 | 20.2 |
