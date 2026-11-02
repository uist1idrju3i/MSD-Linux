# CM0・CardputerZero の部品・回路接続監査

[RESEARCH](../../RESEARCH.md) / [機能とドライバの対応表](hardware-spec.md) / [公式ソフトウェア](official-software.md)

## 結論と確認範囲

2026-11-02 UTC に取得した公式製品ページ、回路図 V0.6.1、CM0 データシート Release 3 を照合した。回路図の全10ページをテキスト抽出し、描画した図面でも接続、部品名、抵抗値、NC 表記を確認した。以下は資料とソースの照合結果であり、実機測定ではない。

主な訂正は、CM0 の4レーン CSI 能力と Linux の標準2レーン設定の区別、CM0Lite の無線付き型番の存在、BMM150 の BMI270 経由接続である。SR9900A の実機 USB ID、共有 reset の制御責務、公式図面内の電源表記差は未解決として残す。推測で GPIO・電源・ドライバ設定は変更しない。

MSD/Linux の比較基準は [f2030c7](https://github.com/uist1idrju3i/MSD-Linux/commit/f2030c7ee70c33cf86828a53379c06873bc3fd1e)。M5 ソースは submodule の [37b42d9](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/37b42d9451495b5597dd7e50cab502da8028f9c2)、Linux は [b3495ea](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602) を基準にする。M5 main の取得時の先端は同じコミットだった。古い調査の `7551854` と `2341883` を現行の固定値と混同しない。

## 一次資料の固定

取得日時、HTTP 状態、サイズ、SHA-256、取得失敗を [資料台帳](hardware-source-manifest.json) に記録した。PDF の JavaScript は実行していない。HTML の更新日時や PDF 名だけで実機の基板版・搭載部品を決めない。

| 記号 | 資料と版 | 用途 |
|---|---|---|
| M | [M5Stack CardputerZero 製品ページ](https://docs.m5stack.com/en/CardputerZero)、Last-Modified 2026-10-30 | Standard/Lite、主要 IC、ピン表、切替の論理値 |
| S | [C154 回路図 V0.6.1、2026-07-02](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)、全10ページ | reference designator、net、電源、pull、NC、信号の経路 |
| C | [CM0 datasheet RP-009251-DS-3](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)、Release 3、build `205dd78e0f0d`、08/07/2026 | モジュールの能力、pin、電源制約、ordering table |

取得に失敗した別名 URL や、通常の取得での403も台帳に残した。CM0 PDF は通常の browser User-Agent と `Accept: application/pdf` を付けて取得したもので、認証付き資料ではない。

## 製品名とモジュールの型番を分ける

| 製品 | RAM・SoC | ストレージ | 無線 | 製品差 |
|---|---|---|---|---|
| CardputerZero Standard / C154 | RP3A0 / BCM2837、Cortex-A53 4 core、1GHz、512MB LPDDR2 | microSD slot、32GB card 付属という M の記載 | M は2.4GHz Wi-Fi / Bluetooth を記載 | IMX219、BMI270、BMM150 あり |
| CardputerZero Lite / C155 | M の比較表では同じ | slot はある。card は付属しない | M の比較表では無線あり | camera と IMU なし |
| CM0 / CM0Lite | C の全型番で512MB | CM0 は8GB / 16GB eMMC、CM0Lite は eMMC なし・外部 SDIO | 無線の有無は独立した選択肢 | 下表の module part number で識別 |

C の Table 11 は、無線なし `CM0000000 / SC2230`、`CM0000008 / SC2231`、`CM0000016 / SC2232` と、無線あり `CM0100000 / SC2233`、`CM0100008 / SC2234`、`CM0100016 / SC2235` を区別している。末尾 `000` の2型番は Lite、`008` は8GB、`016` は16GBである。「CM0Lite には無線の記載がない」という以前の記述は訂正する。

CardputerZero Lite と CM0Lite は別の製品区分である。CardputerZero の製品名だけから、基板に載る CM0 の注文型番や無線 chip ID を断定しない。C の optional wireless の記載と、M の完成品に無線があるという記載は矛盾しない。実機の module 刻印、SDIO ID、読み込む firmware は未確認である。

C は無線部品に CYW43439 を記載する。確認した生成imageには43430 / 43436s / 43439系のfirmwareが含まれるが、その存在から実機で選ばれるchipやfirmwareを決めない。

## 表示・音声・外部拡張の仕様

M は取得時にも Work in progress と表示していた。次は公開仕様と回路図の記載であり、表示・音声・外部接続の実測値ではない。

| 対象 | 公開資料の値と制限 |
|---|---|
| LCD | M は1.9 inch、ST7789v3、320×170を記載。信号接続は後掲のGPIO表を参照 |
| 音声 | M はMEMS microphone、8ohm / 1W speaker、3.5mm TRRS入出力を記載。codecはES8389、amplifierはAW8737A |
| 映像出力 | M は1080P 30fpsの映像出力とcodecを記載。S p.10 J5は19pinの `HDMI-001`。コネクタ形状と実出力は未確認で、[HDMI調査](hdmi-output.md) に分ける |
| 拡張端子 | M はHY2.0-4PのI2C / UART切替、EXT 2.54-14PのSPI / UART / I2C / USB / GPIOを記載 |
| Capの抜挿 | M はhot-swap非対応を明記し、挿入・取り外し前に本体の電源を切るよう求める。未測定だから許容するとは扱わない |

## 全部品の台帳

[hardware-components.csv](hardware-components.csv) に、S の U1〜U37 の37参照番号を全件記録した。列は `ref,pdf_page,part,kind,power_or_rail,interface,control,notes`。U11 は CM0 モジュール、U17 は microSD socket であり、37個の単体 IC があるという意味ではない。37行・8列・重複なし・欠番なし・空欄なしを機械検査した。

部品名は図面の表記を採った。LCD controller と IMX219 は製品ページにあるが、S の U1〜U37 の単体 IC ではない。抵抗、コンデンサ、MOSFET、diode、connector の全 BOM を作ったという意味でもない。ソフトウェアに関係するこれらの接続は以下と CSV の notes に含めた。

### I2C の経路とアドレス

以下は7-bitアドレスである。8-bitの read/write byte と混ぜない。C の I2C0 と I2C1、CM0 の内部 GPIO と外部 GPIO、M5IOE1 の PYG 番号も別に扱う。

| 接続先 | 経路・アドレス | 資料・実装との照合 |
|---|---|---|
| M5IOE1 / U14 | I2C1、GPIO2 SDA / GPIO3 SCL、`0x4f` | S p.6、v5 overlay。reset は GPIO16、R80 100k pull-up |
| TCA8418 / U27 | I2C1、`0x34` | S p.8。5行×10列に46キー。IRQ GPIO27、R124 100k pull-up、active-low。reset は PYG3 |
| ES8389 / U30 | I2C1、`0x10` | S p.9。v5 overlay の compatible は `everest,es8390`。物理部品名を ES8390 へ変更しない |
| RX8130CE:B3 / U19 | I2C1、`0x32` | S p.7。nIRQ / nRSTO / FOUT は NC。BAT1 は NC、R95 は0ohm。バックアップ電池搭載・停電時保持を断定しない |
| BQ27220YZFR / U4 | I2C1 から U6 を介した BQ_I2C1、`0x55` | S p.3。10mohm R15 と BAT_NTC。充電器 IP2315 とは別の燃料計 |
| BMI270 / U18 | I2C1、`0x68` | S p.7。INT1 / INT2 は NC、SDO は R96 10k pull-down |
| BMM150 / U20 | BMI270 の ASDx / ASCx の AUX I2C、`0x10` | S p.7。主 I2C1 上の ES8389 と同じ segment ではない。M5 overlay は root 配下の `magnetometer@10` と `bmi270-parent` で表現 |
| IMX219 | SDA0 / SCL0、CSI connector JP5 | S p.5/p.10。外部 I2C1 GPIO2/3 と混同しない |

S p.5 の GPIO2/3 は VSYS_3V3 へ各2.2k pull-up、GPIO_VREF は R74 0ohm で CM0_3V3 へ接続している。I2C の同一アドレスだけを根拠に BMM150 と ES8389 の衝突とは判定しない。BMI270 の AUX 初期化と実測値はドライバ・実機で別途確かめる。

### GPIO・選択信号・active level

| 用途 | 接続と論理 | 根拠と注意 |
|---|---|---|
| LCD | GPIO10 MOSI、11 CLK、8 CS0、25 DC、5 TE。PYG12 reset、PYG10 backlight PWM | M、S p.4/p.7。LCD の初期化 firmware と SPI 設定も必要 |
| LCD backlight | U9 AW9967 の CTRL は PYG10、R54 100k pull-down | S p.4。panel 電源と backlight 電源を混同しない |
| 音声 | GPIO18 BCLK、19 LRCK、20 DIN、21 DOUT | M、S p.9。GPIO21 から0ohm R160を通る MCLK 経路もある。overlay の fixed-clock は12.288MHzで、実際の波形は未測定 |
| speaker / headphone | GPIO24 → Q7等 → AW_SPK_EN、GPIO17 HP_DET | S p.9。単純な GPIO24 だけの制御ではなく検出回路との関係も実機確認する |
| TRRS | PYG6 MIC_SW、LOW=CTIA / HIGH=OMTP、R172 100k pull-down | M、S p.9。U32 FSW7227 の SEL。固定値を全イヤホンに適用しない |
| keyboard / hub reset | PYG3 が U27 RESET# と U15 RST# を共有 | M、S p.6/p.8。各10k pull-up。片方の reset が他方にも波及する。DT の GPIO index 2 と物理 PYG3 を区別 |
| keyboard LED | PYG8 / PYG9 / PYG11、VSYS_3V3 → LED → 4.7k → PYG | M、S p.8。low側で点灯する回路。LED とキー matrix は別 |
| IR | GPIO12 → Q5 の送信、GPIO13 の受信 | M、S p.7。現行 board config に IR overlay の指定はない |
| power detect | SW_EN の分圧等から GPIO6 SW_DET と PYG5 PWR_DET | S p.4。v5 の powerfail は GPIO6 falling edge、500ms debounce、LOW を有効状態として扱う |
| power hold | SW_EN と PYG14_PWR_EN → diode → VSYS_PW_EN → U7 EN | S p.4。ソフト制御だけが唯一の電源保持経路ではない。PYG14 の読書きだけで安全な電断を保証しない |
| hardware revision | PYG2_HW_DET、R43 120k / R46 75k の分圧 | S p.4。図面の表は2.5V=V0.3内部用、2.0V=V0.6。実機の検出電圧・版は未確認 |
| Grove mux | GPIO4、LOW=UART GPIO14/15 / HIGH=I2C1 GPIO2/3 | M、S p.10。R184 100k pull-down、既定 UART。v5 overlay も `grove_fun` default off |
| Grove power | PYG4 → U35、R188 100k pull-down | S p.10、M は供給電流500mA未満。GPIO4 の mux とは別の制御 |
| HAT P0/P1 | PYG1、LOW=GPIO26/23 / HIGH=GL_USB4 D+/D- | M、S p.7。R105 100k pull-down。U22 の電源は VSYS_5V |
| HAT power / bus | PYG13 → U23 EXT_5VOUT → U25 EXT_3V3、既定 off | S p.7、v5 overlay。U24 は SPI0 GPIO10/11/7/9、U26 は I2C1、U37 は UART GPIO14/15 を level translate。GPIO22 は HAT JP3 へ接続 |
| USB host/device | USB_SW LOW=CM0 USBを右USB-Cへ / HIGH=hubへ | M、S p.6。Q4 と USB_OTG の関係もあり、software の `dr_mode` だけでは物理経路は切り替わらない |

M5IOE1 の物理 PYG 番号と DT の0始まり GPIO index、PWM channel は別の番号体系である。例えば reset の `<&m5ioe1 2 1>` は index 2、powerfail の `disabled-gpios = <&m5ioe1 11 1>` は index 11 である。後者を「PYG14 を切る設定」と解釈しない。ドライバの GPIO/PWM mapping と MCU firmware の責務は [公式ソフトウェア](official-software.md) の照合対象である。

### 電源・ストレージ・USB

S p.3 の U5 TPS2116 は USBC_R_5V / VEXT_5V から VCHG_5V を選ぶ充電入力 mux である。VBAT と外部電源を直接切り替える mux と記述しない。IP2315 の充電経路と、diode / MOSFET 等を介して VSYS_IN へ入る経路は分かれている。図面には USB 入力優先とある。

U7 は VSYS_IN → VSYS_CM0、U12 は CM0 入力保護、U10 SY8003 は VSYS_CM0 → VSYS_3V3 で CM0_3V3 を EN に使う。U8 は VSYS_IN → VSYS_5V、EN は VSYS_3V3 の分圧である。U7/U8 の図面式は5.2Vだが、実機の電圧・立上り順・電源保持時間を測った値ではない。

S p.2 は U28 相当の audio LDO の入力を VSYS_IN、p.9 の U28 は VSYS_CM0 としており、**公式資料内の相違**がある。AW8737A / U31 は p.9 でも VSYS_IN。CSV は詳細図 p.9 の接続を書き、相違を notes に残した。実基板を確認せず、都合のよい方を唯一の正解にはしない。p.2 の HAT power switch の ME1502AM5G 表記と p.7 の U23 AW35112FDR、power-up sequence の表記も、詳細図と同一視しない。

U15 GL852G の給電は VSYS_3V3、V5 pin は NC。USB1 は SR9900A、USB2 は USB-A、USB3 は左USB-C、USB4 は HAT。U33 の USB-A / 左USB-C 給電経路は合計1A、Grove は別の500mA未満という記載である。S p.2 の電池動作時6W平均・CM0約3W・残り3W未満という見積りは、全出力を同時に最大で使用できる保証ではない。外部 port の逆給電・突入・熱・電池時の上限は未測定である。

U17 の microSD 電源 SD_3V3 は VSYS_3V3 由来。一方 CM0 の SD_VREF は R75 0ohm で CM0_3V3 に接続され、CM0_1V8 側の R78 は NC。S p.5 には eMMC 時の SDVREF 1.8V 条件がある。eMMC版モジュールと microSD向け配線・起動手順を互換だと仮定しない。

C の通常動作入力は regulated 5V、4.75〜5.25Vであり、絶対最大6Vとは別の制約である。5V → GLOBAL_EN → CM0_3.3V → 1ms以上後に CM0_1.8V の順序、GPIO_VREF の接続、外部 pin からの逆給電回避も必要。WiFi_ON / BT_ON は LOW で無効化できるが、S p.5 の GND 側 R67/R68 は NC。MSD/Linux が常に無線を物理遮断する回路ではない。

C の温度範囲は-20〜+85°C、wireless RFは-20〜+75°C。本文の idle / operating 225 / 675mA と DC table の250 / 670mAは資料内の異なる記載として残す。MSD/Linux の実測値へ置き換えない。

## 差異の分類と採否

| 対象 | 従来の記述・現行値 | 公式値・固定ソース | 分類と採否 | 必要な修正・実機確認 |
|---|---|---|---|---|
| CSI lane | 「CM0 CSI1 は2 lane」 | C は4 lane能力、S p.5/p.10 は D0〜D3配線。固定 CM0 DTS は2-lane include、IMX219 overlay は標準2 lane・`4lane` overrideあり | 文書の表現誤り。能力・配線・動作設定を分離して訂正 | 標準2 lane設定は変更しない。4 lane captureは sensor / endpoint両側と動作を検証してから判断 |
| camera GPIO | GPIO16をcamera電源ENとする可能性 | S p.5/p.10で CAM_GPIO=CM0 pin44 / JP5 pin17、Cと DTSでは内部GPIO40。U36 EN は VSYS_5V に100k pull-up | GPIO16 camera hog 不採用を維持。GPIO16はM5IOE1 reset | GPIO40とU36電源ENを同じnetとしない。sensor ID、topology、撮像、Liteのprobe結果は未確認 |
| CM0Lite wireless | 無線有無の記載なしとしていた | C Table11に無線付き CM0100000 / SC2233 | 文書の誤りを訂正 | CardputerZero搭載品の注文型番は実機刻印で確認 |
| I2C `0x10` | BMM150とES8389が同じ値 | S p.7とM5 IMU overlayで BMM150はBMI270経由 | 電気的な衝突としない。文書を訂正 | AUX初期化・両機能の同時動作は未確認 |
| SR9900A | `USB_NET_SR9700` module選択 | S U13はSR9900A。固定 sr9700.c は `0fe6:9700/9702`、sr9800.c は `0fe6:9800`。取得した dm9601.cにも `0fe6:9900` の登録を確認できない | driver対応は未確認。近い名前の型番だけで対応済みとしない | 実機VID:PID / bcdDevice、modalias、bind先、RX/TXを取得。USB IDの追加だけを先行しない |
| shared reset | DTに `rest-gpios` | 固定TCA8418 Cにこのpropertyの取得・駆動を確認できず、M5IOE1 Cのreset取得はコメント内 | ソース上の未消費property。実機不具合とは未確定 | `devm_add_action_or_reset` はcleanup APIでありreset pin制御ではない。typoだけと決めずMCUの初期化・probe順を確認 |
| audio power | audio LDO input | S p.2 VSYS_IN / p.9 VSYS_CM0 | 公式資料内の相違、実基板未確認 | 部品実装と導通・各railの時系列確認。Linux設定は変更しない |
| Standard / Lite | 同一imageでcamera / IMU overlay選択 | MではLiteにcamera / IMUなし | 意図した製品共通化。ただし「失敗は無害」とする実機証拠はない | missing-device、retry、依存待ち、起動遅延、ログ量をLite実機で確認 |
| GPU firmware | `gpu_mem=16` | [firmware調査](rpi-firmware-spec.md)と[PR #180](https://github.com/uist1idrju3i/MSD-Linux/pull/180)で訂正済み | 今回の基準commitに反映済み | cut-down firmwareとcamera / displayの実機互換性は未確認。QEMUではこのGPU段階を通らない |

## 検証結果と残る確認

今回実施したのは、公式資料の取得・hash記録、PDFのテキストと画像の照合、CSVの全参照番号検査、固定ソースとの上記比較である。実機の電源、撮像、Ethernet、LCD、keyboard、audio、RTC、無線、拡張端子の動作確認は行っていない。

再検査は、台帳 URL の内容を取得して SHA-256 を比較し、S の該当ページと CSV の `pdf_page` を照合する。PDF全体のhashを固定し、ページ抽出ツールの違いを元資料の差と混同しない。CSV の構造は次で検査できる。

```sh
python3 - <<'PY'
import csv
from pathlib import Path
rows = list(csv.DictReader(Path('docs/research/hardware-components.csv').open()))
assert len(rows) == 37
assert {r['ref'] for r in rows} == {f'U{i}' for i in range(1, 38)}
assert all(None not in r and len(r) == 8 and all(r.values()) for r in rows)
print('37 references; 8 columns; no duplicate/missing refs or empty cells')
PY
```

過去のQEMUカメラmodule load試験の統制相対 ready-marker 中央値 `+0.0510%` と `+1.0%` 判定基準は [S2実験](../experiments/2026-10-19-s02-camera.md) の条件に属する。今回の資料照合や実機撮像の測定結果ではない。生成 `.dtbo`、最終 kernel config、module / firmware / permission の照合は、[公式ソフトウェア](official-software.md) と [生成物の確認記録](../experiments/2026-11-02-hardware-artifact-audit.md) に分ける。
