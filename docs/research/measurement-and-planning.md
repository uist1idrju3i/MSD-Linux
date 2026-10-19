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
| カード固有の erase/AU 情報と速度 | `preferred_erase_size` 等のカーネル報告値と実測性能はカード・ホストに依存し、CM0 実機では未確認です。 | [Linux MMC sysfs attributes](https://docs.kernel.org/driver-api/mmc/mmc-dev-attrs.html) |
| GPT / MBR と 4 MiB alignment | firmware の互換性および速度・寿命・電断への効果は実機で未確認です。 | [Raspberry Pi boot documentation](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc) |
| `/data` の ext4 移行 | 現行 `data=journal` から `data=ordered` へ移す場合のアプリ整合性、barrier、`commit=`、電断時挙動は未検証です。 | [ext4 documentation](https://docs.kernel.org/admin-guide/ext4.html) |
| secure update / dm-verity | 署名検証、鍵・root digest の信頼起点、全カード交換への耐性は未実装・未検証です。 | [dm-verity documentation](https://docs.kernel.org/admin-guide/device-mapper/verity.html) |
| ハードウェア機能 | LCD、入力、音声、センサー、RTC、充電、USB、HDMI 等の実機動作は未検証です。 | [CardputerZero hardware matrix](scope-and-hardware.md#ハードウェア機能の対応表) |

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
9. **GPIO6 電源断スイッチの hold-up 時間**（信号発生から電源が失われるまでを実機測定し、正常停止を追加できるか判断する）
10. **microSD の実測特性:** `/sys/block/mmcblk0/device/preferred_erase_size`、queue の `minimum_io_size` / `optimal_io_size` / `discard_granularity` / `discard_max_bytes`、MMC card 情報を記録し、モデル・容量・firmware とともに保存する。
11. **パーティション比較:** 現行、`align=1M`、`align=4M` の各 image で開始 sector、FAT data-area 絶対位置、image size を記録する。4 MiB alignment が速度や寿命を改善すると先に仮定しない。
12. **SD 性能:** 同じカード・ホスト・温度で sequential / random read-write と同期書込みを測り、反復回数、中央値、p90、card 使用状態を記録する。A1/A2 のラベルのみから性能を推定しない。
13. **ext4 と電断:** `/data` の実 mount options、`data=journal` / `data=ordered`、barrier、`commit=` を記録し、アプリケーションの `fsync`/rename を含む更新と電源断試験を行う。
14. **discard:** target card が報告する discard 能力、`fstrim` の成否・時間・結果を記録する。対応や効果をカード仕様から推定しない。
15. **ハードウェア機能:** matrix の各 driver probe、firmware load、ユーザー空間利用を別々に確認し、電源異常・通常 shutdown は実測で区別する。
16. **セキュリティ:** 署名不正／鍵違いの更新拒否、read-only root 上の鍵、dm-verity digest の信頼起点を確認する。試験でカード全体を差し替えた場合に防げないことも記録する。
17. **割り当て単位と小さい file:** 同一の file tree を使い、FAT／exFAT の cluster、ext4 の 1 KiB／4 KiB block と `inline_data`、SquashFS fragment の有無を比較する。容量、fsck 時間、連続／4 KiB random I/O、同期書込み latency をカード別に記録し、外部公開の速度差をそのまま当てはめない。
 
 本リポジトリでは試していません。flashbench は手順案のみで、カード内部の erase unit を確定する計測として扱いません。【未確認】

### 今後の検討アイデア

- **実装済み・実機未検証:** GPIO6 電源断イベントの通知と `/`, `/boot`, `/data` の同期を Buildroot package patch で SysRq-U より前に行う。正常停止は hold-up 時間の実機測定後に判断する。
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
| 電源断 | 読み取り専用 rootfs に加え、GPIO6 の通知・同期を実装。正常停止は hold-up 時間の測定後に判断 | package patch が通知と同期を SysRq-U より前に実行します。バックライト消灯と disabled GPIO の処理は維持しています。 | [電源断処理](power-and-updates.md#63-powerfail_suo) |

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

## シミュレーターと検証基盤の比較

QEMU 公式 release ページで確認できた最新 stable は 11.1.2（2026-09-28）です。手元の `/usr/bin/qemu-system-arm` は 6.2.0（Debian `1:6.2+dfsg-2ubuntu6.31`）。CI は `ubuntu-26.04` 上で unpinned の `apt-get install qemu-system-arm` を実行します。CI runner の package version は workflow に pin されず、実行ログにも version が保存されていないため【未確認】です。

QEMU 6.2 docs には `raspi3b` があり、`raspi4b` はありません。`raspi4b` は QEMU 9.0 で追加されました。同 release notes は Raspberry Pi の SPI と BSC I2C も追加したとします。QEMU 11.1.2 の raspi docs は UART、DMA、clock/reset、timer、GPIO、RNG、framebuffer、USB、SD/MMC host、thermal sensor、MBOX、SPI、I2C を実装 device として列挙します。watchdog は一覧にありません。SD/MMC host の正確な controller 実装（SDHCI か BCM SDHOST か）は概要資料から確定できず【未確認】です。`VideoCore firmware (property)` は property mailbox interface であり、実機 VideoCore firmware と boot path の再現ではありません。【一次】

TCG plugin の `insn` は guest 命令数、`hotblocks` は頻出 translation block、`cache` は指定 cache 構成での guest memory access の hit/miss を集計します。`libinsn` は plugin が instruction を decode / 表示するための補助 library で、独立した性能計測器ではありません。host 実時間や実 SD latency は測りません。QEMU `-icount` は guest instruction count に基づく仮想時間を進め、決定的な実行モードを提供しますが、wall-clock 性能比較の根拠にはなりません。plugin による同一入力の命令数・cache event 比較に用途を限定します。【一次】

QEMU `virt` は汎用 Arm machine と virtio block / network 等を提供し、更新処理・userspace の機能試験に使えますが、CM0 firmware、VideoCore、SD host、CardputerZero 固有 device を検証しません。`raspi3b` も target の RAM 容量・clock・実 microSD 性能を忠実に再現するものではありません。

gem5 の最新公式 release は 25.1.0.1（2026-04-21）。26.0 milestone は 2026-10-19 時点で release 済みと確認できませんでした。gem5 は `MinorCPU` や full-system Arm Linux 構成を提供します。Arm の HPI は「modern in-order Armv8-A implementation」の代表モデルで Cortex-A53 の cycle-accurate replica ではありません。`ex5_LITTLE` は Cortex-A7 based model と明記され、A53 proxy ではありません。full-system simulation は model・kernel・disk 準備と実行時間の負担が大きく、CM0 固有 device もありません。【一次】【推測】

Arm Fast Models の公開ページは Architecture FVP version 11.32（2026-07-30）と Base RevC AEMvA platform を掲載します。Base RevC は architecture envelope platform で Cortex-A53 microarchitecture model ではありません。Cortex-A53 FVP の説明も公開されていますが、download entitlement / license は【未確認】です。Renode 最新 release は 1.17.0（2026-09-07）。v1.17.0 の `platforms` tree から BCM2835 / BCM2837 / Raspberry Pi platform は見つかりませんでした。【一次】【未確認】

CM0 と Raspberry Pi Zero 2 W は RP3A0 SiP 系で、公開資料はどちらも 1 GHz quad-core Cortex-A53、512 MB LPDDR2 を記載します。Zero 2 W の microSD host / board routing が CM0 と同一とは扱いません。SD interface の clock、bus 幅、UHS / 1.8 V 対応も未確認のため、software-level proxy に留めます。【一次】

| 基盤 | 目的・忠実度 | 速度・コスト | 検証できる範囲 / できない範囲 |
|---|---|---|---|
| QEMU `raspi3b` | BCM2837 系の機能試験・中 | TCG は比較的高速、導入コスト低 | 起動、UART、rootfs、init、A/B userspace / VideoCore boot、実 tryboot、CM0 device、SD 性能・実時間は対象外 |
| QEMU `virt` | generic Arm userspace・低～中 | 高速、導入コスト低 | updater、filesystem、サービス / BCM2837・firmware・M5 hardware は対象外 |
| QEMU TCG plugin + `-icount` | 命令量・cache event の比較 | 実時間性能は対象外 | build option 間の instruction/cache 傾向 / A53 cycle・SD latency は対象外 |
| gem5 | CPU/cache pipeline の詳細化・設定依存 | 遅く、model 構築コスト高 | 合成 workload の CPU/cache 感度 / 実機 firmware・board は対象外 |
| Arm FVP / Renode | Arm architecture / 対応 platform の検証 | 入手条件・model 構築に依存 | architecture または Renode 対応 platform / CM0 board 固有経路は未確認 |
| Zero 2 W / CardputerZero | RP3A0 software proxy / 実 target | 遅く、装置と測定治具が必要 | software timing・SD・温度・周辺機器。board 間差を無視して一般化できない |

**提案（【推測】）:** 第1段は QEMU `raspi3b` で機能・起動 regression、第2段は QEMU TCG instruction-count/cache events と build size で option の傾向を比較、第3段は Zero 2 W を proxy とし最終判断は CardputerZero/CM0 実機で boot time・SD・温度・RAM を測ります。QEMU の instruction count だけで実時間の最適化を採択しません。

### 次の比較測定

| 比較 | 記録項目 | 条件 |
|---|---|---|
| SquashFS codec / 128 KiB・1 MiB block | image bytes、CPU decode throughput、SD sequential/random read、起動時刻 | 同じ rootfs・カード・温度。cache cold/warm を分ける |
| SD / CPU / RAM | 実 read rate、decoder throughput、RAM・cache miss、CPU clock / 温度 | CM0 と Zero 2 W を別機種として記録 |
| Buildroot `-O2` / `-Os` | package size、rootfs size、起動時刻、CPU workload、build time | 同一 GCC 14.3.0 toolchain・config・rootfs |
| kernel compressor removal / optimize option | `Image` / `vmlinux` bytes、boot milliseconds、feature regression | `CONFIG_SQUASHFS_XZ/LZ4`、`EROFS_FS`、size/performance config を一つずつ変更 |
| LTO / PGO | build time、profile 生成・回収時間、binary size、CPU workload、再現性 | 実機 profile と QEMU profile を分離し、profile source と生成条件を保存 |

出典: [QEMU 11.1.2 release](https://www.qemu.org/download/)、[raspi machine models](https://qemu.readthedocs.io/en/v11.1.2/system/arm/raspi.html)、[TCG plugins](https://qemu.readthedocs.io/en/v11.1.2/devel/tcg-plugins.html)、[gem5 25.1.0.1](https://github.com/gem5/gem5/releases/tag/v25.1.0.1)、[Arm HPI model](https://github.com/gem5/gem5/blob/c8222cc6/configs/common/cores/arm/HPI.py)、[Arm FVP 11.32](https://support.arm.com/tools-and-software/fixed-virtual-platforms/arm-architecture-fvps)、[Renode 1.17.0](https://github.com/renode/renode/releases/tag/v1.17.0)、[CM0 datasheet](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)、[Zero 2 W product page](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)。

## シミュレーション検証計画（S1–S17）

`~/work/plan-sim-verification.md` の調査項目を試験単位に分け、根拠・成果物・担当範囲を記録する計画である。ここに記載する試験は計画であり、実施済みを意味しない。Filesystem の書き込み fault・速度模擬 S17 の詳細と取得済み出典は[読み取り専用領域と FS 比較](readonly-data-and-fs.md#s17-ストレージの障害速度の模擬)を参照する。

| ID | 対象 | 主な方法・成果物 |
|---|---|---|
| S1 | Linux kernel option sweep | 一候補ずつ変更して baseline `.config` と依存差分、`Image` size、build log を保存する。 |
| S2 | camera | DT・driver・firmware の有無と target の要件を確認し、実機で接続・capture を確認する。QEMU は実 camera を保証しない。 |
| S3 | `/data` format/options | ext4 block size、`noatime`、`lazytime`、`data=`、mount flags の組合せを比較する。 |
| S4 | ext4/F2FS/btrfs | 同じ data set と update/fsync workload で create, sync, mount, fsck, power-cut recovery、write volume を記録する。 |
| S5 | OverlayFS mode | `/etc`-only、full-root、`/data` bind/symlink 案を比較し、xattr、whiteout、rename、A/B lower update を試す。 |
| S6 | kernel hardening | `kernel-hardening-checker` を使い設定差を記録し、必要機能と boot regression を確認する。 |
| S7 | IR | IR driver/DT input/output、既存機能と競合する GPIO を調査し、実機送受信を確認する。 |
| S8 | charger IC | IC driver/DT、状態読み出し、充電状態・電圧表示を実機で検証する。 |
| S9 | power-fail shutdown | 実電源を切る前後の `powerfail_suo`、shutdown deadline、filesystem recovery を反復測定する。QEMU は GPIO/電源回路を代替しない。 |
| S10 | update signature rejection | 署名不正・破損・古い bundle を host test と QEMU で与え、非 active slot と state が変化しないことを確認する。 |
| S11 | watchdog fallback | 起動中 hang、health failure、watchdog reset 後の slot selection と recovery を QEMU・実機で分けて確認する。 |
| S12 | SquashFS codec/block size | gzip/xz/zstd/lz4 と block size ごとに image size、decode throughput、SD I/O、RAM を記録する。 |
| S13 | userland `-O2`/`-Os`/LTO | 同一 GCC/config で package/rootfs size、CPU workload、boot timing、build time を比較する。 |
| S14 | CPU specialization | `-mcpu`/`-mtune` と kernel CPU options を一つずつ変え、`Image`/package size、命令数、実機時間、全機能を検証する。 |
| S15 | QEMU versions | version と machine/device model 差を記録し、同一 image/command line の機能・virtual-time regression を比較する。 |
| S16 | normally-RO `/etc` and `/data` | boot、persistent config, seedrng, updater, fsck/recovery の各 writer が maintenance RW window だけで動くか試験する。 |
| S17 | storage fault/speed emulation | `dm-log-writes` + `replay-log`、`dm-flakey`/`dm-delay`、QEMU `blkdebug`/throttle/cache mode を使い、error/replay/prefix ごとに fsck・data invariant を記録する。実 card FTL/timing は含まない。 |

### 検証ツールと実行境界

- **Buildroot differential build:** まず baseline image、kernel `.config`、Buildroot config、`Image`/rootfs size を保存し、その後に一 option ずつ変える。build log と変更理由を S ID に結び付ける。
- **QEMU function test:** `board/cardputerzero/qemu/run-qemu.sh` と `raspi3b` を使い、rootfs、init、A/B、update、watchdog の再現可能な機能範囲を確認する。標準 boot の成功と実機機能の保証を混同しない。
- **仮想時間・initcall:** CPU option 比較では QEMU `-icount shift=0` と `initcall_debug` を使い、ready marker までの virtual time と initcall 数・所要時間を記録する。これは real-time benchmark ではない。
- **filesystem fault:** 使い捨て image 上で forced QEMU stop、`kill -9`、dm-log-writes の replay、QEMU block statistics を使う。`kill -9` や `cache=unsafe` は実機の給電遮断と同じではない。再生前後に fsck とアプリケーション invariant を確認する。
- **hardening/host tests:** `kernel-hardening-checker` と `tests/msd-update/run.sh` 等の対象 host tests を実行し、結果を該当 S ID に紐付ける。
- **実機測定:** CM0/CardputerZero でのみ、電源断、物理 SD 性能、温度・周波数、camera/IR/charger、周辺機器の全機能を確認する。Zero 2 W は software timing の proxy にとどめ、同一 SoC でも board 差を別に記録する。

### 実施順と抜け防止

1. Baseline config/image、kernel version、firmware、DT、measurement endpoints を固定して保存する。
2. S1 と S2/S7/S8 の hardware/driver inventory を行い、変更候補が製品機能に触れるか特定する。
3. S3–S5 と S16 の filesystem/mount policy を、S17 fault matrix と組み合わせて検証する。
4. S9–S11 の power/update recovery を続け、最後に S12–S15 の image/CPU/simulator 比較を行う。実測候補を選ぶ場合は実機で再確認する。
5. 試験票に S ID、hypothesis、source URL、config/hash、command、device/card、始点・終点、artifact path、結果、未確認点を記録する。変更した config key と六つの製品要件の影響を照合し、各要件に「試験済み/未試験」の根拠が一つ以上あるまで完了扱いにしない。

この計画で CI に追加するのは日本語 lint、relative-link、host test など軽い回帰検査に限り、既存 workflow は変更しない。kernel option sweep、複数 filesystem の電断/replay、full differential Buildroot、実機試験はローカルで行い、CI に長時間の sweep を追加しない【推測】。

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
