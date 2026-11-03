# UART・通信・ログによる観測

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

開発・通常運用・電源断試験で条件を分けます。観測のための給電やSDへのログ書き込みが、測る対象を変えないようにします。
下の手段・ピン表は調査時の条件を保存しています。SR9900Aは[生成物の照合](../../experiments/2026-11-02-hardware-artifact-audit.md)だけでは実機USB IDと対応driverを確定できません。
実機での到達性は[未確認事項](open-questions.md)、実行する測定は[実機測定](hardware-measurements.md)へ記録します。

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
| Ethernet（SR9900A）経由 SSH | M5 documentation は USB 2.0 → Ethernet チップ SR9900A、10/100M、Host モードのみと説明しています。 | https://docs.m5stack.com/en/CardputerZero | USB ID が 0fe6:9900 の場合の r8152 系ドライバ利用を想定していますが、実機の ID は未確認です。実 ID は `lsusb` または起動ログで確認します。SSH の選択肢は[ユーザー空間・セキュリティ調査](../userspace-and-security.md)を参照してください。 |
| pstore / ramoops | RAM 上の予約領域にクラッシュログを残し、再起動後に読みます。`reserved-memory` または `mem=` で領域を指定します。 | https://docs.kernel.org/admin-guide/ramoops.html<br>https://docs.kernel.org/admin-guide/pstore-blk.html | 電源断後の RAM 保持、リセット再起動時の保持、RPi firmware が DT に付与するメモリとの競合は未確認です。公開カーネル文書と実機試験で確認します。 |
| SD 専用領域への直書き | ファイルシステムを介さず、未使用パーティションまたは生セクターへ固定形式でログを書く方法です（自作）。 | — | 電断試験でもファイルシステムの破損を避けられる可能性がありますが（推測）、SD のページ書き込み中断リスクは残ります。ストレージ仕様と電断試験で確認します。実装は未着手です。 |
| 開発中のみ ext4 にログ | 開発ビルドだけ RW パーティションに `data=ordered` の ext4 を置きます。 | https://docs.kernel.org/admin-guide/ext4.html | 量産ビルドには含めません。測定結果に I/O が混ざるため、起動時間測定時は無効化します。 |
| sysrq | `s` (sync) / `u` (remount ro) / `b` (reboot) / `o` (poweroff) を使えます。 | https://docs.kernel.org/admin-guide/sysrq.html | 電断試験のソフトな近似にのみ使用します。本物の電断とは別です。 |

### 電源断試験時の切替方針（推測）
- **起動時間測定モード**:ログ最小(quiet)、シリアル接続は固定、ext4 ログ無効。
- **電断試験モード**:UART は**外す/読み取り専用** にして給電経路を分離(USB-UART の給電が基板に回り込むと電断にならない)。ログは pstore/SD 直書き/電断後に外部から回収できる形で。
- **障害解析モード**:UART + printk 全開 + ext4 ログ有効。
- モードは SD 上のフラグ(または別ビルド)で切替え、**同一ビルドで測定条件が変わらないこと**を試験記録に書く。

## ログと観測


### 開発中の観測方法

- UART: M5 の資料では HY2.0-4P と EXT 2.54-14P に G14 / G15 がある。G4 の切替で I2C1 / UART を切り替える。EXT の物理ピンは RX=12、TX=14。3.3 V logic。GPIO14/15 の最終 pinmux と UART 種別は M5 overlay / config 実機確認が必要。`enable_uart=1` が mini-UART の core frequency を固定する場合があり、速度測定に影響し得る。
- USB gadget serial: `g_serial` で `/dev/ttyGS0` を作れる。右 USB-C が OTG slave のときのみ CM0 直結し、host 側の hub / Ethernet / USB-A は同時に使えない。公式 config は `dwc2,dr_mode=host` のため gadget 運用は別設定が必要との推測。
- Ethernet SSH は実装しない。Ethernet は USB 2.0 の SR9900A、10/100 Mb/s。実際の USB ID とドライバは未確認。
- pstore / ramoops は panic / watchdog 等の reset 再起動後のログ候補。完全な電源断では RAM が消える。予約領域と firmware のメモリ配置衝突は未確認。
- 開発用 ext4 ログや専用 raw partition は候補だが、量産 rootfs に含めない。起動測定では無効にする。
- 起動時間測定は UART 設定・ログ量を固定。電断試験は給電経路を分離。障害解析では UART + printk 全開を使う。

出典: [CardputerZero docs](https://docs.m5stack.com/en/CardputerZero)、[USB gadget serial](https://docs.kernel.org/usb/gadget_serial.html)、[ramoops](https://docs.kernel.org/admin-guide/ramoops.html)、[SysRq](https://docs.kernel.org/admin-guide/sysrq.html)。
