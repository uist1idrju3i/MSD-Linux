# 未確認事項・測定・調査限界

## 未確認事項

| 確認事項 | 現状 | 出典URL |
|---|---|---|---|
| CM0 の 64-bit 起動設定 | 公開対応表に CM0 はありません。`arm_64bit=1` または `kernel8.img` の明示が必要です。実機動作は未確認です。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| Linux 6.18 の ZRAM / framebuffer console | ZRAM=m、ZSWAP=y です。`FRAMEBUFFER_CONSOLE` の最終的な有効状態は `.config` で未確認です。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 |
| RAUC の変更案 #1599 | Devin が 2026-10-18 に公開情報で確認した時点では open・未マージでした。 | https://api.github.com/repos/rauc/rauc/pulls/1599 |
| 公開 OS リポジトリの 404 | リポジトリ URL が 404 を返すことは確認されていますが、削除・非公開・改名のどれが理由かは未確認です。公開アーカイブの有無を確認する必要があります。 | https://github.com/CardputerZero/cardputer-zero-os<br>https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os |
| Pi 用 OS の候補 | 公式一覧には Ubuntu Core / Minimal Ubuntu 等があります。起動時間と A/B の実証は未確認です。 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| Linux stable 7.2.11 | 2026-10-15 の公開リリース一覧で確認しました。 | https://www.kernel.org/releases.json |
| microSD FTL の電断挙動 | 一次資料は未確認です。LWN、Bootlin、JEDEC、SD Association の公開資料で確認する必要があります。 | URL未取得 |
| MCUboot の arm64 実績 | 未確認です。MCUboot の公開ソースと対応ボード一覧で確認する必要があります。 | URL未取得 |

### 残る未確認事項
| 事項 | 確認内容 | 出典URL |
|---|---|---|
| BCM2837（CM0）での tryboot | `tryboot` / `autoboot.txt` が動作するか、実機で確認する必要があります。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc |
| Wi-Fi チップ ID | 43430 / 43436s / 43439 のどれか、実機のチップ ID を確認する必要があります。 | https://docs.m5stack.com/en/CardputerZero |
| HDMI コネクタ形状 | Type A / D のどちらか、回路図または実機で確認する必要があります。 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| CM0 の GPT 挙動 | CM0 での動作を実機で確認する必要があります。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52 |
| 公開 OS リポジトリの 404 | `cardputer-zero-os` / `cardputer-zero-shell` が 404 となる理由（削除・非公開・改名）は未確認です。 | https://github.com/CardputerZero/cardputer-zero-os<br>https://github.com/CardputerZero/cardputer-zero-shell<br>https://web.archive.org/web/20260623195631/https://github.com/CardputerZero/cardputer-zero-os<br>https://web.archive.org/web/20260527131053/https://github.com/CardputerZero/cardputer-zero-shell |
| microSD FTL の電源断挙動 | 一次資料は未確認です。ストレージ仕様と電源断試験で確認する必要があります。 | URL未取得 |
| MCUboot の arm64 実績 | 未確認です。公開ソースと対応ボード一覧で確認する必要があります。 | URL未取得 |
| CM0 の起動時間 | ベースラインと、GPU 段が公開ベンチマーク記載の時間どおりかを実機で測定する必要があります。 | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21 |
| framebuffer console | `FRAMEBUFFER_CONSOLE` の実効値と `fbcon=map:off` の扱いを `.config` と起動ログで確認する必要があります。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1135<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh#L247 |
| overlay 名 | `cardputerzero-overlay` と `-v3` / `-v5` の対応を公開設定と overlay 定義で照合する必要があります。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt#L12<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20 |
| image-rota と Zephyr | image-rota 相当の機構が Zero 2 W / Pi 3 でどう動くか、Canonical Zephyr フォークの内容を確認する必要があります。 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11 |
| Ubuntu Core 26 | A/B 相当機構と Pi 3 / Zero 2 W での起動は未確認です。公式テスト対象は Pi 4 / 5 との情報がありますが、対象機種を公開資料で確認する必要があります。最小 RAM と手順は未確認です。 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| カーネル・ツールチェーン最適化 | `-mcpu=cortex-a53` / LTO の効果と `dirty` / `printk` 系 sysctl の根拠は未確認です。公開カーネル文書と実機測定で確認する必要があります。 | URL未取得 |
| fork の内容 | vicliu624 / stanley-fork の変更内容を比較する必要があります。 | https://github.com/vicliu624/cardputer-zero-os |

### 実機が届いたら最初に測る項目（優先順の案）
1. **公式イメージの起動時間**(systemd-analyze、vclog)。ベースライン
2. **tryboot/autoboot.txt の動作**(A/B 方式の成否を左右する)
3. **CM0 の arm_64bit/kernel8.img の挙動**
4. **kernel8.img の非圧縮と gzip の比較**
5. **vc4 除去の効果**(HDMI/cma を外した場合)
6. **Wi-Fi の chip ID**
7. **GL852G のリセット挙動**(PYG3 はキーボードと共用)
8. **電源断試験**(書込み中/アイドル時の電源断を多数回)

### 今後の検討アイデア

- **未着手:** GPIO6 のスイッチ検知をユーザー空間へ通知し、同期後に正常停止する経路を追加する。現行 `powerfail_suo` は SysRq-U とバックライト消灯、disabled GPIO の駆動までで、正常停止を実装していません。
- **実装済み・実機未検証:** 初回起動時に p7 の末尾まで拡張し、ext4 `/data` を拡張する。
- **実装済み・実機未検証:** Ed25519 で更新 bundle の manifest を署名・検証する。リリース鍵の配布・更新手順は今後の運用課題として残る。
- **未着手:** 実機の公式イメージをベースラインとして測定し、比較条件を固定する。
- **未着手:** 電源断耐性の合格条件の例として、更新中を含む 200 回の電源断試験で起動不能を 0 件とする。
- **未着手:** 山城さん向けに、各フェーズの書き込み・観測・ログ採取方法を記した実機手順書を作る。

---

## 推奨案と未決事項

以下は公開資料と未測定事項を踏まえた暫定案です。設計上の選択肢は候補であり、実機での確認が必要な項目は未確認または推測として記します。

### 推奨案
| 項目 | 推奨 | 推奨理由 | 出典URL |
|---|---|---|---|
| 方向性 | **Linux を第一候補** | Zephyr 26.04 LTS と v4.4.0 の CM0 対応、microSD、SDHCI の有無は公開ボード情報だけでは確認できていません。実機で確認する必要があります（未確認）。 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi<br>https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w |
| ベース | **Buildroot が第一候補**、Yocto（meta-raspberrypi wrynose、raspberrypi0-2w-64）が代替候補 | Buildroot は単一リポジトリの最小構成として管理しやすく、対象システムに apt を含めない設計を取りやすいと考えます（推測）。Yocto は opkg/rpm を利用できますが、初回ビルドは数時間・50 GB 超となる見込みです（推測、実測なし）。pi-gen は公式 Debian 互換性が高い一方、読み取り専用 rootfs と A/B は追加実装が必要で、既存資料の起動時間は 7〜9 秒です。 | https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://docs.yoctoproject.org/overview-manual/concepts.html#package-management<br>https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf<br>https://github.com/CardputerZero/pi-gen<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| カーネル | **rpi-6.18.y をコミット固定**（6.18.57） | M5 の `panel-mipi-dbi-m.c` は `drm_client_setup.h` を include します。このヘッダーは rpi-6.18.y にあります。rpi-6.12.y の同じパスは HTTP 404 ですが、6.12 系全体でヘッダーがないかは未確認です。6.13〜6.17 も未確認です。pi-gen は 6.18.39 を指定しています。Linux 6.18 の LTS 期間は 2028-12 までです。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/include/drm/clients/drm_client_setup.h<br>https://www.kernel.org/category/releases.html |
| rootfs | **SquashFS または EROFS の読み取り専用 rootfs + overlayfs（upper は tmpfs / zram）+ 小さな ext4 RW データ領域** | Raspberry Pi の公開ホワイトペーパーは、読み取り専用 rootfs と書き込み領域を分ける方式を推奨しています。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| A/B | **MBR + tryboot / autoboot.txt + RAUC custom バックエンド**（試行カウンターとフォールバックは自前） | Raspberry Pi の文書は tryboot を全モデル向けに説明していますが、BCM2837 での実動作は未確認です。U-Boot なしで追加段を避けられる可能性はあります（推測）。公式 image-rota は GPT を使い、対応モデルは Pi 4 / 5 です。代替候補の Rugix は Pi 3 で rpi-tryboot、Zero 2 W で rpi-uboot を示します。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/rauc/rauc/pulls/1599<br>https://rugix.org/docs/bakery/devices/ |
| UI | **CLI 専用を候補とし、HDMI / vc4 を外す構成を実測で評価** | ユーザー要件に基づく案です。HDMI / vc4 を外した実機での動作は未確認です。 | — |
| 電源断 | 読み取り専用 rootfs に加え、**GPIO6 のスイッチ検知による正常停止**を併用 | `powerfail_suo` は SysRq-U の後にバックライトを消灯し disabled GPIO をアサートします。電池の突然の取り外しには読み取り専用 rootfs で備える案です。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L472-L510 |

### 設計上の未決事項
| 論点 | 選択肢・留保 | 状態 |
|---|---|---|
| 起動完了条件 | 主指標は **T_shell**（LCD にプロンプトが表示され、キー入力できる時点）、副指標は **T_init**（PID 1 の完了マーカー）とし、両方を測ります。 | 測定方針 |
| 読み取り専用 rootfs | SquashFS（`-sort` で優先度の高いファイルを先に配置）と EROFS（`-z` を指定すれば圧縮でき、`--sort` は tar 入力向け）を実機で比較する案です。どちらが速いかは未測定です。 | 未決 |
| init と libc | 初期案は BusyBox init + mdev + glibc とします。mdev への udev ルール移植、必要なら musl との比較、systemd の最小化も検討します。起動時間は未測定です。[関連資料](userspace-and-security.md) | 未着手 |
| A/B 方式 | MBR + tryboot / autoboot.txt + RAUC custom、U-Boot 系、Rugix を候補とします。tryboot と watchdog が CM0 で動作するか未確認です。FAT の boot 領域が単一障害点となる可能性があります（推測）。 | 未決 |
| カーネル版 | Linux 6.18.y、7.2.y、7.3.y を候補とします。7.2.y / 7.3.y の PREEMPT は LAZY / FULL のみです。7.1 で DRM API が変わり、7.3 の alias unmap 再適用後の CM0 起動は未確認です。 | 未決 |
| 開発中のログ | 開発ビルドでは ext4 に記録し、電断試験時は専用領域または pstore に切り替える案です。完全 read-only との両立方法と、測定条件の差を記録する必要があります。 | 未決 |
| SSH / VPN | Dropbear または OpenSSH、WireGuard または OpenVPN を候補とします。SSH サーバーは起動完了後に socket activation で起動する案です。[関連資料](userspace-and-security.md) | 未決 |
| 名称 | MSD/Linux の由来は [RESEARCH.md](../../RESEARCH.md) に記載しています。 | — |

### 判断と関連資料
| 項目 | 関連資料 |
|---|---|
| 起動完了条件・測定 | [実機で測る項目](#実機が届いたら最初に測る項目優先順の案) |
| カーネル・UI | [起動・カーネル調査](boot-and-kernel.md) |
| rootfs・init・libc | [ユーザー空間・セキュリティ調査](userspace-and-security.md) |
| A/B・電源断 | [電源・更新方式の調査](power-and-updates.md) |
| 開発中のログ | [開発中の観測手段](#開発中の観測手段) |
| SSH / VPN | [ユーザー空間・セキュリティ調査](userspace-and-security.md) |
| 名称の由来 | [RESEARCH.md](../../RESEARCH.md) |

---

## 開発中の観測手段

### UART
UART の既定値、ピン配置、コンソール設定は、公開された M5 documentation、回路図、Raspberry Pi Linux、pi-gen、Raspberry Pi documentation で確認しました。
| 事実 | 出典URL | 確認度 |
|---|---|---|
| M5 documentation では `G14_UART_TXD` / `G15_UART_RXD` が HY2.0-4P と EXT 2.54-14P の物理ピン 12 / 14（右列）に出ています。G4 の `G4_I2C/UART_SW` は LOW=UART（既定）、HIGH=I2C1 です。HY2.0 の物理ピン番号は記載されていません。HY2.0 には M5IOE1 の GROVE_EN による 5V 出力があります。 | https://docs.m5stack.com/en/CardputerZero | 一次 |
| 回路図 V0.6.1 には `G14_UART_TXD`（PIN110）、`G15_UART_RXD`（PIN108）、`NLG140UART0TXD` / `NLG150UART0RXD`、HAT 側 `HAT_UART_TXD` の記載があります。 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 一次 |
| `bcm2710-rpi-cm0.dts` は `serial0 = &uart1`（mini-UART）、`serial1 = &uart0`（PL011）と定義しています。`uart1` は `brcm,bcm2835-aux-uart`、`uart1_pins` は空、`uart0` は GPIO30〜33（Bluetooth 用）です。したがって `/dev/serial0` は mini-UART を指します。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L14-L16<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm283x.dtsi#L304-L305<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm283x.dtsi#L385-L387 | 一次 |
| pi-gen の `01-run.sh` は M5 の `make … config_setup` を実行します。M5 の Makefile は `rpi-config.py --no-backup section-set all enable_uart 1` を実行し、ビルド時に `[all]` へ `enable_uart=1` を設定します。pi-gen の `02-run.sh` と `04-set-partuuid/00-run.sh` は cmdline から `console=serial0,115200` を除去し、`verify-image.sh` はその状態を検査します。最終 config.txt は未確認です。 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/export-image/04-set-partuuid/00-run.sh<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/tools/verify-image.sh#L158-L161<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile#L74 | 一次 |
| pi-gen の `CARDPUTERZERO-IMAGE-DESIGN.md` は `console=serial0,115200` を保持すると説明しますが、公開スクリプトは cmdline から除去します。どちらが意図した状態かは未確認です。 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/docs/CARDPUTERZERO-IMAGE-DESIGN.md#L41<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/export-image/04-set-partuuid/00-run.sh | 一次 |
| Raspberry Pi documentation は、`ttyAMA0` が primary UART の場合に `enable_uart` が既定で 1、それ以外は 0 であること、`enable_uart=1` が `force_turbo=1` でない場合に `core_freq=250` を伴うこと、`cmdline.txt` の `console=serial0,115200` が GPIO14 / 15 のシリアルコンソールを要求することを説明しています。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/configuration/reference.adoc#L1408<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L98 | 一次 |
| 公式 DT と公開イメージ設定から、`serial0` は mini-UART を前提とし、pi-gen は cmdline からその console を外すことが分かります。GPIO14 / 15 の pinmux は DT だけでは断定できず、M5 overlay/config で未確認です。`enable_uart=1` は（`force_turbo=1` でない場合）`core_freq=250`（250MHz）を伴い、コア周波数を上げる最適化に影響する可能性があります（推測）。開発用コンソールでは、HY2.0 が I2C1（G2 / G3）と共用で G4 の切替が必要なこと、3.3V ロジック、mini-UART の速度条件に注意します。 | 上記の公開出典 | Devin が 2026-10-18 に公開資料で確認。pinmux は未確認 |

#### EXT 2.54-14P と HY2.0-4P の UART 関連ピン（物理ピンと GPIO を別列）
| コネクタ | 機能 | **物理ピン番号** | 列(左/右) | **GPIO 番号** | docs 表の行 |
|---|---|---|---|---|---|
| EXT 2.54-14P | UART_RXD | 12 | 右 | G15 | 右列 12=G15、左列 11=G9 SPI0_MISO |
| EXT 2.54-14P | UART_TXD | 14 | 右 | G14 | 右列 14=G14、左列 13=G7 SPI0_CS1 |
| EXT 2.54-14P | （参考）I2C1_SDA / SCL | 8 / 10 | 右 | G2 / G3 | 左右列の 4・5 行 |
| HY2.0-4P | G14_UART_TXD（I2C 時は G2_I2C1_SDA） | 記載なし | Yellow | G14 | 色の列順は Black=GND、Red=5V、Yellow、White |
| HY2.0-4P | G15_UART_RXD（I2C 時は G3_I2C1_SCL） | 記載なし | White | G15 | 同上 |

出典: https://docs.m5stack.com/en/CardputerZero Devin が 2026-10-18 に公開資料で確認しました。HY2.0 は色で示され、物理ピン番号は記載されていません。EXT の 13 番ピンは G7（SPI0_CS1）です。

### その他の手段
| 手段 | 事実 | 出典URL | CM0 での注意 |
|---|---|---|---|
| USB ガジェットシリアル | `g_serial` で `/dev/ttyGS0` を作れます（`modprobe g_serial`）。 | https://docs.kernel.org/usb/gadget_serial.html | Slave モードでは右側 USB-C が CM0 に直結（OTG）します。Host / Slave スイッチが Slave だとハブ・Ethernet・USB-A は使えません。M5 の公開設定は `dtoverlay=dwc2,dr_mode=host` です。ガジェット運用に必要な `dr_mode=peripheral` は未確認です。https://docs.m5stack.com/en/CardputerZero<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/firmware/CardputerZero/config.txt |
| Ethernet（SR9900A）経由 SSH | M5 documentation は USB 2.0 → Ethernet チップ SR9900A、10/100M、Host モードのみと説明しています。 | https://docs.m5stack.com/en/CardputerZero | USB ID が 0fe6:9900 の場合の r8152 系ドライバ利用を想定していますが、実機の ID は未確認です。実 ID は `lsusb` または起動ログで確認します。SSH の選択肢は[ユーザー空間・セキュリティ調査](userspace-and-security.md)を参照してください。 |
| pstore / ramoops | RAM 上の予約領域にクラッシュログを残し、再起動後に読みます。`reserved-memory` または `mem=` で領域を指定します。 | https://docs.kernel.org/admin-guide/ramoops.html<br>https://docs.kernel.org/admin-guide/pstore-blk.html | 電源断後の RAM 保持、リセット再起動時の保持、RPi firmware が DT に付与するメモリとの競合は未確認です。公開カーネル文書と実機試験で確認します。 |
| SD 専用領域への直書き | ファイルシステムを介さず、未使用パーティションまたは生セクターへ固定形式でログを書く方法です（自作）。 | — | 電断試験でもファイルシステムの破損を避けられる可能性がありますが（推測）、SD のページ書き込み中断リスクは残ります。ストレージ仕様と電断試験で確認します。実装は未着手です。 |
| 開発中のみ ext4 にログ | 開発ビルドだけ RW パーティションに `data=ordered` の ext4 を置きます。 | https://docs.kernel.org/admin-guide/ext4.html | 量産ビルドには含めません。測定結果に I/O が混ざるため、起動時間測定時は無効化します。 |
| sysrq | `s` (sync) / `u` (remount ro) / `b` (reboot) / `o` (poweroff) を使えます。 | https://docs.kernel.org/admin-guide/sysrq.html | 電断試験のソフトな近似にのみ使用します。本物の電断とは別です。 |

### 電源断試験時の切替方針（推測）
- **起動時間測定モード**:ログ最小(quiet)、シリアル接続は固定、ext4 ログ無効。
- **電断試験モード**:UART は**外す/読み取り専用** にして給電経路を分離(USB-UART の給電が基板に回り込むと電断にならない)。ログは pstore/SD 直書き/電断後に外部から回収できる形で。
- **障害解析モード**:UART + printk 全開 + ext4 ログ有効。
- モードは SD 上のフラグ(または別ビルド)で切替え、**同一ビルドで測定条件が変わらないこと**を試験記録に書く。

## 調査範囲と限界

調査した公開資料は[出典一覧](sources.md)に記載しています。kernel.org の kernel 文書、EROFS FAQ、squashfs-tools documentation、man7、BusyBox FAQ、Dropbear、WireGuard、musl、mimalloc、M5 documentation と overlay、raspberrypi/linux、raspberrypi/documentation を参照しました。起動時間や電断耐性など、実機での測定は未実施です。したがって性能効果は推測です。

未取得・未調査事項は次の一覧にまとめます。bootchart の man7 は HTTP 404、OpenSSH sshd の man、Raspberry Pi の processors ページ、Arm の ID_AA64ISAR0_EL1 定義ページは取得できていません。BCM2837 の暗号拡張に関するメーカー一次仕様、`systemd.timer` の本文、BusyBox の NOFORK / NOEXEC 設定、mdev の仕様、WireGuard / OpenVPN / Dropbear / OpenSSH の CM0 実測値、IR・カメラの DT、brcmfmac firmware の取得元、SR9900A の実機 USB ID、Linux 7.2 / 7.3 の `bcm2711_defconfig` の PREEMPT 値も未確認です。

### 残る未確認事項
| 未確認の内容 | 関連資料・確認方法 |
|---|---|
| BCM2837 での tryboot / autoboot.txt の動作、再起動での復帰、watchdog | [電源・更新方式の調査](power-and-updates.md)、https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc |
| CM0 の起動時間ベースラインと各最適化の実測効果（実機未入手） | [実機測定計画](#実機が届いたら最初に測る項目優先順の案) |
| CM0 での `kernel8.img` / GPT / `arm_64bit` の起動可否 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc |
| Wi-Fi チップ型番（CM0 データシート上の無線搭載版は CYW43439。無線版か Lite・無線なし版か、実機の chip ID は未確認）、HDMI コネクタ形状、IR・カメラの DT の所在 | https://docs.m5stack.com/en/CardputerZero<br>https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf |
| fbcon / FRAMEBUFFER_CONSOLE の要否と overlay 名の不整合 | [起動・カーネル調査](boot-and-kernel.md)、https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20 |
| image-rota 相当の Zero 2 W / Pi 3 での挙動、Canonical Zephyr の内容 | https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml<br>https://github.com/zephyrproject-rtos/zephyr |
| Ubuntu Core 26 の A/B 相当機構と Pi 3 / Zero 2 W での起動 | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| `-mcpu` / LTO / sysctl 等の効果 | URL未取得。公開ツールチェーン文書と実機測定で確認します。 |
| vicliu624 fork の内容、`CardputerZero/cardputer-zero-os` が 404 となる理由 | https://github.com/vicliu624/cardputer-zero-os<br>https://github.com/CardputerZero/cardputer-zero-os |
| microSD の FTL・電断耐性に関する一次情報 | URL未取得。microSD 仕様書と電断試験で確認します。 |
| MCUboot の arm64 実績 | URL未取得。公開ソースと対応ボード一覧で確認します。 |
| BCM2837 に AES / SHA 命令がないことのメーカー一次仕様。A53 の Crypto Extension がオプションであることは DDI 0501F で確認済みですが、BCM2837 が実際に搭載していないことの一次仕様は未取得です。二次情報として Raspberry Pi forum の報告があります。 | URL未取得。Arm DDI 0501F と BCM2837 のメーカー資料を照合します。 |
| SSH / VPN / PQ の CM0 実測、古いクライアントとの PQ 互換性、OpenVPN で ML-KEM を使えるか | [ユーザー空間・セキュリティ調査](userspace-and-security.md)、実機測定は未実施です。 |
| Linux 7.3（alias unmap 再適用後）の CM0 起動、7.x での M5 モジュールのビルド可否、Linux 7.2 / 7.3 の PREEMPT 値 | [起動・カーネル調査](boot-and-kernel.md) |
| M5Stack の名称利用ガイドライン原文（`docs.m5stack.com/en/brand` は 404） | https://docs.m5stack.com/en/brand |
| Kickstarter（403）、Raspberry Pi forum `t=207888` / `263234` / `376022`（403 / 取得不可）、TechFeed（タイトルのみ）など、取得できなかった公開ページ | [公開出典一覧](sources.md) |
| 最終 config.txt の `enable_uart`、GPIO14 / 15 の pinmux（mini-UART か PL011 か）、pi-gen の文書と実装のどちらが意図か | 上記 UART 表と https://docs.m5stack.com/en/CardputerZero |
| SR9900A の実機 USB ID（0fe6:9900 か） | https://docs.m5stack.com/en/CardputerZero。実機で `lsusb` または起動ログを確認します。 |
| 再適用後の alias unmap が Raspberry Pi 3 / 4 の KVM 問題を解消したか | [起動・カーネル調査](boot-and-kernel.md)、実機確認は未実施です。 |
| KittenLabs の `core_freq=550` が最終の 3.5 秒に含まれるか | URL未取得。公開ベンチマークの測定条件を確認する必要があります。 |
| 開発ログ方式の電断試験時の実装 | [電源断試験時の切替方針](#電源断試験時の切替方針推測)を参照。 |
| rpi-6.12.y の同じパスは HTTP 404。6.12 系全体にヘッダーがないか、rpi-6.13〜6.17 に存在するか | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/include/drm/clients/drm_client_setup.h<br>https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.18.y/include/drm/clients/drm_client_setup.h |
| `powerfail_suo` の `disabled-gpios = <&m5ioe1 11 1>` が M5IOE1 の PYG12（LCD_RST、documentation 記載）に当たるか。index+1 の推論で未確認です。GPIO6=SW_DET と PYG6=MIC_SW は別物で、混同しません。 | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts |
| RX8130 の I2C アドレス。CardputerZero overlay は 0x32、単体 `modules/rx8130` は 0x68（実機未確認） | [起動・カーネル調査](boot-and-kernel.md) |
| OpenVPN 2.7.6 + OpenSSL 3.6.4 の実接続で ML-KEM（X25519MLKEM768）が使われるか。ソース確認のみで、CM0 での所要時間も未測定です。 | [ユーザー空間・セキュリティ調査](userspace-and-security.md) |
| WP-1 の Pi 3B+ ログにある kernel `Loaded` 4.131 s から `Device tree loaded` 6.760 s までの 2.63 s の内訳、GPU 段とカーネルサイズの関係。同一構成でサイズを変えて実機測定する必要があります。 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-1-Optimising%20boot%20time.pdf |
| Newlib に Linux 用の sys ディレクトリがないか（sourceware の取得ができていません） | URL未取得。公開ソースで確認する必要があります。 |
| Raspberry Pi OS Trixie 2026-10-06 の kernel 版は 6.18.50 です。公式 release notes で確認済みですが、イメージ内の実際のカーネルパッケージ版は実機・イメージ展開で未確認です。 | https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
