# HDMI 外部ディスプレイ出力の調査

CardputerZero に HDMI 出力端子を繋いだ場合の挙動、および Wayland/X11 を使わない表示経路の調査です。[ハードウェア機能の対応表](hardware-spec.md) の HDMI 行の詳細としてまとめます。確認日は 2026-11-02 です。

## 1. ハードウェア上の HDMI 出力

| 事実 | 出典 | 確認度 |
|---|---|---|
| 回路図に 19pin の HDMI コネクタ（P10 J5、「HDMI-001」シルク）があり、CM0 エッジコネクタの PIN17–33 が HDMI 信号です。 | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf | 一次（回路図） |
| 公式製品ページが「Supports 1080P 30fps video output and codec」を明記しています。 | https://docs.m5stack.com/en/CardputerZero | 一次 |
| 物理コネクタ形状（Type A / D 等）は回路図のシルク名からは確定できません。 | 同上 | 未確認 |
| 給電側に `HDMI_5V` レールがあります。バッテリー時の VSYS_5V 総枠は平均 6W、CM0 本体で約 3W との注記があるため、外部ディスプレイ側の供給電力は残枠内に収める設計です。 | 同上回路図（電源ツリー注記） | 一次（回路図注記） |
| DSI（PIN1–16）は CM0 エッジコネクタ上に信号がありますが、基板上の外部コネクタとしては HDMI のみです。カメラは MIPI CSI（PIN40–63）。 | 同上 | 一次 |

## 2. 表示経路の全体像

BCM2837 の表示パイプライン（vc4: HVS + PixelValve + HDMI/DSI/VEC）と、SPI 経由の ST7789V3 内蔵液晶は**別々の出力**です。

- 内蔵液晶：`cardputerzero-v5-overlay` が `spi0` の CS0 に `cardputerzero,st7789v_lcd`（compatible `panel-mipi-dbi-m5stack`）を登録し、panel-mipi-dbi が DRM デバイス化。`DRM_FBDEV_EMULATION` で `/dev/fb0`、fbcon がコンソールを表示します。
- HDMI：2 つの経路が選択可能です（排他）。
  1. **firmware framebuffer**（既定）: ファームウェアが HVS/HDMI を駆動し、Linux 側は `&fb` 経由の bcm2835-fb（`CONFIG_FB_BCM2835`）や simplefb として受け取ります。Linux からは単純なフレームバッファに見えます。
  2. **vc4 KMS**（`dtoverlay=vc4-kms-v3d`）: overlay が `&vc4`、`&hdmi`、`&hvs`、`&pixelvalve0–2`、`&v3d`、`&vec`、`&txp` を有効化し、`&fb` を無効化します。Linux の DRM ドライバが HDMI コネクタを直接持ち、`/dev/dri/cardN` + fbdev エミュレーション + `HDMI-A-1` コネクタになります。モードは EDID からの自動選択、ホットプラグ検出（HPD）が効きます。
- `vc4-fkms-v3d`：ファームウェアがモードセットを行いつつ ARM 側 vc4 がレンダリングを受け持つ中間形。dispmanx 系ツール（dispmanx_vnc 等）との互換で使われます。

## 3. 各 OS での HDMI 対応

| OS | HDMI の扱い | 出典 | 確認度 |
|---|---|---|---|
| CardputerZero 公式OS | Raspberry Pi OS Trixie arm64 ベース。pi-gen が `dtoverlay=vc4-kms-v3d,cma-64` と `fbcon=map:off` を設定し、内蔵液晶は `panel-mipi-dbi-spi → DRM/KMS → labwc（Wayland）` でアプライアンス UI。README は「標準の HDMI Pi OS デスクトップ経路を置き換えない」と明記し、**HDMI は通常の Pi OS デスクトップがそのまま出る**構成です。 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L36<br>https://github.com/CardputerZero/cardputer-zero-os | 一次 |
| Raspberry Pi OS 本体 | 近年の既定は `dtoverlay=vc4-kms-v3d`。HDMI を繋ぐと EDID モードでコンソール+デスクトップが出ます。内蔵液晶は m5stack overlay を入れない限り表示しません。 | 同上 pi-gen の config 設定 | 一次 |
| MSD/Linux 現状 | `CONFIG_DRM_VC4=m`、`DRM_FBDEV_EMULATION=y` はありますが、`config.txt` に `vc4-kms-v3d` 系 overlay がなく、`linux.fragment` に `CONFIG_FB_BCM2835`/`CONFIG_FB_SIMPLE` 等の firmware-fb 指定もありません（最終 .config はビルド時解決のため要確認）。**現状では HDMI を繋いでも Linux 側の表示出力が出ない可能性が高い**です（vc4 がバインドするノードが無効のまま）。 | board/cardputerzero/config.txt、board/cardputerzero/linux.fragment | 一次（コード）+ 挙動は未実機確認 |
| 将来 HDMI を使う場合 | `dtoverlay=vc4-kms-v3d`（公式は `,cma-64`）を config.txt に追加する案。mdev coldplug が modalias で vc4 モジュールを自動ロードし、`/dev/fb1`（液晶が fb0 のまま）ができます。fbcon は既定で fb0 に残るため、HDMI 側コンソールは `fbcon=map:` 指定か `con2fbmap` で切替えます。両 fb を別アプリで占有も可能です。 | overlays/vc4-kms-v3d-overlay.dts、S10mdev の coldplug | 一次（コード）+ 推測 |

## 4. Wayland/X11 なしの表示経路

Wayland・X11 は前提ではありません。表示先は fbdev（`/dev/fbN`）、DRM/KMS（GBM/dumb buffer）、SPI/DBI パネルの 3 系統です。

| 用途 | Wayland/X11 なしで動く経路 | Buildroot 収録 | ライセンス | 備考 |
|---|---|---|---|---|
| 動画・VLC 系 | mpv `--vo=drm`（KMS/GBM 直接）、`--vo=tct`（端末出力）、`--vo=sdl`（SDL2→kmsdrm） | mpv 0.40.0 | GPL-2.0+ | SPI 液晶は帯域が細く低 fps、HDMI 側（vc4 KMS）なら実用的。HW デコードは start_cd でコーデックが削られているためソフトウェアデコード見込み【未確認】 |
| VLC 本体 | 旧来の `vout_fb`（fbdev）モジュール経路が VLC3 系にはありますが、対象版での残存は要確認 | vlc | GPL-2.0+ | 未確認 |
| PDF（pdf.js 代替） | `mutool draw`（mupdf）でページを PNG 化して fbv/fbi へ、`python-pymupdf` でページを直接 fb へ描画、`pdftoppm`（poppler）経由 | mupdf 1.23.9、python-pymupdf、poppler 25.10.0、qpdf、ghostscript 10.08.0 | AGPL-3.0+ / GPL-2.0+ | **pdf.js そのものは JS+DOM 依存で、duktape/mujs/quickjs では動かず現実的ではありません**。jfbview/fbpdf（fbdev PDF ビューア）は上流に存在するが未収録 |
| リモートデスクトップ（装置の画面を外へ出す） | `kmsvnc`（KMS/DRM をキャプチャして VNC、未収録だが上流に実装あり）、`libvncserver`（自前サーバーの部品、0.9.15 収録）、`ffmpeg -f kmsgrab`（DRM プレーンキャプチャ→ストリーム送信、ffmpeg 収録）、`dispmanx_vnc`（FKMS 時のファームウェア面キャプチャ、未収録・KMS では効かない見込み） | libvncserver、ffmpeg | LGPL-2.1+ / GPL | x11vnc は X 前提で対象外 |
| リモートデスクトップ（外部画面を装置に表示する） | `directvnc`（fbdev 上で動く VNC ビューア、未収録・上流に実装あり）、`sdl-freerdp`（FreeRDP の SDL クライアント、Buildroot の freerdp では SDL クライアント選択肢が無く要個別ビルド） | freerdp 2.11.8（X11/Wayland クライアントのみ） | Apache-2.0 | ビューア側は X/Wayland 前提のものが多く、fbdev 直結は薄い。freerdp の server/X11 client は X.Org 必須と Buildroot が明記 |
| Web/文書系 | netsurf-fb（SDL framebuffer）、links `-g`（fbdev）、lynx/w3m+fbterm、cog（WPE WebKit、KMS/DRM 直） | 詳細は [web-browsers.md](web-browsers.md)、[fb-terminals-and-text-browsers.md](fb-terminals-and-text-browsers.md) 参照 | 各種 | pdf.js 系の JS ブラウザは netsurf の JS 範囲では不十分見込み |

補足：

- **fbcon の対象選択**：fbdev エミュレーションが作る `/dev/fbN` は DRM デバイスの probe 順に振られます（液晶が先に来て fb0、vc4 が後から fb1 になる想定）。順序がずれる可能性はあり、固定化するにはデバイス名で選択する設計が安全です。
- **コンソールの割り当て**：`fbcon=map:0`（既定）なら vt は fb0 のまま。`fbcon=map:1` で vt を fb1 へ、または起動後に `con2fbmap`/`/sys/class/vtconsole` 経由で切替え。`fbcon=map:off`（公式OSが採用）は vt-console の fb 割当をしません。
- **SPI 液晶と HDMI の同時利用**：二つの DRM デバイスとして独立なので、液晶に fbcon、HDMI にアプリ描画（例：`mpv --vo=drm /dev/dri/card1`、fbv/fbi の fb1）という分業が可能です。
- **音声**：HDMI 音声は vc4-hdmi の ALSA デバイスで別経路。内蔵の ES8389 コーデック経路とは別に出ます。
- **電力**：公式回路図の注記どおり VSYS_5V の総枠は平均 6W（CM0 で約 3W）。HDMI_5V の供給・外部ディスプレイ駆動の増分は残枠に依存します。

## 5. 未確認事項

- MSD/Linux の最終 `.config` で `FB_BCM2835`/`FB_SIMPLE`/simpledrm がどう解決されるか（linux.fragment に指定なし、ベース defconfig 側の既定を要ビルド確認）。
- `start_cd.elf`（cut-down ファームウェア）での firmware framebuffer 動作と HW コーデック可否。
- 実機での HDMI 出力確認：vc4-kms-v3d 追加後の fb 割当、EDID モード、ホットプラグ、音声。
- `start_cd.elf` + `vc4-kms-v3d` の組合せ（cut-down で必要なファームウェア面が足りるか）。
- VLC の fbdev vout の対象版での有無、mpv の実効パス（mesa3d/GBM の構成次第）。
- kmsvnc / directvnc / sdl-freerdp / jfbview の個別ビルド可否。

## 6. 主な出典（2026-11-02 確認）

- CardputerZero 回路図: https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf
- CardputerZero 製品ページ: https://docs.m5stack.com/en/CardputerZero
- cardputer-zero-os（公式 OS プロファイル）: https://github.com/CardputerZero/cardputer-zero-os
- pi-gen の CardputerZero 設定: https://github.com/CardputerZero/pi-gen
- m5stack-linux-dtoverlays: https://github.com/m5stack/m5stack-linux-dtoverlays
- vc4-kms-v3d overlay: https://github.com/raspberrypi/linux/blob/rpi-6.18.y/arch/arm/boot/dts/overlays/vc4-kms-v3d-overlay.dts
- kmsvnc: https://github.com/cojac/kmsvnc
- directvnc: https://github.com/drinkmystery/directvnc
- mupdf: https://mupdf.com/ 、poppler: https://poppler.freedesktop.org/
- mpv: https://mpv.io/ 、ffmpeg kmsgrab: https://ffmpeg.org/ffmpeg-devices.html
- Buildroot パッケージ定義: vendor/buildroot/package/ 以下の各 `*.mk`（当該リポジトリ内の一次資料）
