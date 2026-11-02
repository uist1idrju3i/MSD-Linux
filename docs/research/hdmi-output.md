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

## 5. HDMI 接続先との互換性最大化

vc4 KMS ではモードは EDID から自動選択され、ホットプラグ（HPD）で再交渉されます。「繋いだ相手に確実に映る」を崩す典型要因は EDID 欠損・限定モード・アダプタ・RGB 範囲・給電です。

| 接続先 | 期待される動作 | 詰まりやすい点と対策 |
|---|---|---|
| PC モニター（HDMI/DVI 入力） | EDID の推奨モードで自動的に映る。1080p までなら最も安定 | DVI 入力は音声なし（アナログ 3.5mm/ES8389 側へ）。`hdmi_drive=1`（DVI）相当の扱い |
| テレビ（HDMI） | CEA モードで自動選択 | オーバースキャンで端が切れることがある（`disable_overscan` やモード/アンダースキャン調整）。RGB 範囲不一致で白飛び・黒つぶれが出ることがある → vc4 の `Broadcast RGB` コネクタプロパティ（modetest/proptest 系）で full/limited を合わせる |
| 4K/高解像度ディスプレイ | パネル側が EDID で 1080p 等の下位モードを提供すればそれで映る | BCM2837 の HDMI 実効上限は 1080p 級。公式仕様は「1080P 30fps」なので 60Hz 要求や 4K 直出しは期待しない |
| HDMI→VGA 変換アダプタ | アダプタ内部の EDID/変換で映ることが多い | アダプタ側が HDMI_5V ピンから給電する。電力が大きいと落ちる・映らない。アダプタ品質差が大きい |
| 低解像度 HDMI パネル（800×480/1024×600 等） | EDID 提供ならその解像度で映る | EDID が正しくない製品ではモードを強制する必要あり（後述）。「映らない」より「ずれる・端が切れる」系が多い |
| プロジェクター・キャプチャカード | 通常のモニター同様 | 固定モードが要る場合は cmdline `video=` で強制 |
| アダプタ無しで LCD だけ（HDMI 未接続） | vc4 はコネクタ無しでプローブ、HDMI は出ない | 電力・初期化時間を絞るなら vc4 非ロードという選択肢（[起動経路](boot/sequence.md) の max_framebuffers 系と関連） |

強制手段（EDID が信頼できない・無い場合）：

- **kernel cmdline `video=`**：`video=HDMI-A-1:1920x1080@60` のようにコネクタ名指定でモードを固定します。`e`/`d` 接尾で強制 enable/disable もできます。KMS 側の正式な上書き経路です。
- **`drm.edid_firmware=`**：`drm.edid_firmware=HDMI-A-1:edid/1920x1080.bin` のように内蔵 EDID ブロブを差し替えます（EDID が壊れている相手に有効）。
- **config.txt の firmware 系オプション**：`hdmi_group`/`hdmi_mode`/`hdmi_force_hotplug`/`hdmi_ignore_edid`/`hdmi_timings`/`hdmi_pixel_encoding`/`config_hdmi_boost`/`disable_overscan`/`overscan_*`/`edid_content_type`/`hdmi_drive` は **firmware-fb 経路および FKMS の初期モード決定に効きます**。vc4-kms-v3d の完全 KMS では最終モードは DRM 側が EDID から決めるため、確実な強制は `video=` 側です。
- **開始電圧・信号品質**：`config_hdmi_boost` は TMDS 駆動強度の調整で、ケーブル/アダプタの品質が悪い場合に試す手段として残っています。
- **音声**：HDMI 音声は vc4-hdmi の ALSA デバイスで別経路。DVI 相手・音声不要なら無理に出す必要はありません。`audio` コネクタプロパティ（auto/on/off）で制御できます。
- **給電**：HDMI_5V は VSYS_5V（平均 6W 総枠・CM0 約 3W）からの供給で、規格上はソース側 55mA 級。大きく食うアクティブアダプタや長距離ケーブルでは外部給電側の余力が要ります。

## 6. 内蔵液晶を CLI のまま、HDMI 側で動かせるアプリ

液晶（fb0/DRM card0 想定）に fbcon CLI を残したまま、HDMI（fb1/card1 想定）をアプリ専用にする使い方です。fb の番号は probe 順で変わるため、固定が要る場合は `/dev/dri/by-path/` や `/sys/class/drm/card*-HDMI-A-1/` のコネクタ名で選ぶのが確実です。

| 使い方 | 経路 | Buildroot 収録 | 備考 |
|---|---|---|---|
| HDMI に画像を出す | `fbv`/`fbi` を fb1 宛に | fbv あり | 静止画・サイネージの最小経路。スライドショーはループスクリプトで |
| HDMI に動画を出す | `mpv --vo=drm`（GBM 経由で card1）/`--vo=sdl`/`--vo=tct` | mpv、ffmpeg、SDL2 | mesa3d の `GALLIUM_DRIVER_VC4`（rpi0-3 向け VC4 ドライバ）で OpenGL ES が使える。CPU デコード前提のサイズに留めるのが現実的 |
| カメラプレビューを HDMI へ | imx219 → V4L2 → `ffplay`/`mpv`/gstreamer/`libcamera-apps` | libcamera 0.7.1、libcamera-apps、gstreamer1、v4l2grab、fswebcam | 内蔵カメラの外部モニター化。ネットワーク配信なら mjpg-streamer/motion もあり |
| HDMI 専用の GL/描画 | mesa3d VC4 + `kmscube`/`glmark2`（ベンチ・デモ）、Qt `eglfs_kms`、SDL2 `kmsdrm` | mesa3d、qt5/qt6、sdl2/3、kmscube、glmark2 | KMS/GBM が通る。アプリを card1 に固定するには各々のデバイス選択オプション |
| HDMI 専用 Wayland セッション | `cage`（単一アプリ kiosk）や `weston`/`sway` を card1 だけに立てる | cage、weston、sway 1.12 | 液晶の fbcon と独立して、HDMI 上にだけ Wayland を張る構成 |
| メディアセンター化 | `kodi`（GBM/KMS 向けにビルド可） | kodi 21.3 + 各種アドオン | CM0/512MB では重め。ヘッドレス運用は向きませんが選択肢として存在 |
| HDMI に第 2 コンソール | `con2fbmap` や `fbcon=map:` で別 vt を fb1 に割当、または fbterm を fb1 で起動 | fbterm | CLI は液晶、もう一枚のコンソールを HDMI に出す構成 |
| 画面を外へ配信 | `kmsvnc`（KMS を VNC 配信）、`ffmpeg -f kmsgrab`（プレーンキャプチャ→ストリーム） | ffmpeg、libvncserver | kmsvnc 自体は未収録・持ち込み対象 |
| デモ/サイネージ | 上記の組合せ + 起動スクリプトで fb1 専用化 | — | 液晶は保守 CLI、HDMI は常時表示という役割分担が MSD 向き |

補足：

- **どちらが card0/card1 になるか**は probe 順依存です。LCD の panel-mipi-dbi は組込みドライバで早く立ち、vc4 はモジュール + DT で遅れるため通常は LCD=card0/fb0、HDMI=card1/fb1 になりますが、固定が必要ならデバイス名指定を使います。
- **fbcon の割当**：既定は fb0 に集約されます。HDMI に vt を割るなら `fbcon=map:1` 相当の指定か、起動後に `con2fbmap`/`/sys/class/vtconsole` で振り分けます。
- **Wayland 系の選択**：compositor は DRM デバイスを選べます（cage/weston/sway の DRM backend 指定）。液晶に fbcon、HDMI にだけ compositor という分担はそのまま実現できます。
- **SDL2 の kmsdrm**：SDL2 が複数 DRM デバイスを扱う場合のデバイス選択はバージョン依存のため、実構成での確認が要ります【未確認】。
- **電力**：HDMI 出力の追加負荷（HVS/PV/TMDS + 外部側の HDMI_5V）は VSYS_5V 残枠内に収まる想定ですが、バッテリー駆動での連続運用は未測定です。

## 7. 未確認事項

- MSD/Linux の最終 `.config` で `FB_BCM2835`/`FB_SIMPLE`/simpledrm がどう解決されるか（linux.fragment に指定なし、ベース defconfig 側の既定を要ビルド確認）。
- `start_cd.elf`（cut-down ファームウェア）での firmware framebuffer 動作と HW コーデック可否。
- 実機での HDMI 出力確認：vc4-kms-v3d 追加後の fb 割当、EDID モード、ホットプラグ、音声。
- `start_cd.elf` + `vc4-kms-v3d` の組合せ（cut-down で必要なファームウェア面が足りるか）。
- VLC の fbdev vout の対象版での有無、mpv の実効パス（mesa3d/GBM の構成次第）。
- kmsvnc / directvnc / sdl-freerdp / jfbview の個別ビルド可否。
- DRM デバイス番号（card0/card1）の実機での割り当て順、および fb0/fb1 の対応。
- `Broadcast RGB` コネクタプロパティの対象 kernel 版での公開、およびテレビでの白飛び/黒つぶれの有無。
- `start_cd.elf` 環境での `video=` 強制モード、`drm.edid_firmware=` の適用可否。
- 物理コネクタ形状（Type A か D か）と、アクティブアダプタ・ケーブル品質による給電・信号の限界。
- mesa3d `GALLIUM_DRIVER_VC4`（VC4 世代の OpenGL ES）を有効化した場合の mpv/Qt/SDL/kodi の実動作。

## 8. 主な出典（2026-11-02 確認）

- CardputerZero 回路図: https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf
- CardputerZero 製品ページ: https://docs.m5stack.com/en/CardputerZero
- cardputer-zero-os（公式 OS プロファイル）: https://github.com/CardputerZero/cardputer-zero-os
- pi-gen の CardputerZero 設定: https://github.com/CardputerZero/pi-gen
- m5stack-linux-dtoverlays: https://github.com/m5stack/m5stack-linux-dtoverlays
- vc4-kms-v3d overlay: https://github.com/raspberrypi/linux/blob/rpi-6.18.y/arch/arm/boot/dts/overlays/vc4-kms-v3d-overlay.dts
- Raspberry Pi config.txt リファレンス（hdmi 系オプション）: https://github.com/raspberrypi/documentation/blob/develop/documentation/asciidoc/computers/config_txt/video.adoc
- Linux DRM `video=`/`drm.edid_firmware=`（modedb）: https://docs.kernel.org/fb/modedb.html
- kmsvnc: https://github.com/cojac/kmsvnc 、directvnc: https://github.com/drinkmystery/directvnc
- mupdf: https://mupdf.com/ 、poppler: https://poppler.freedesktop.org/
- mpv: https://mpv.io/ 、ffmpeg kmsgrab: https://ffmpeg.org/ffmpeg-devices.html
- Kodi: https://kodi.tv/ 、cage: https://github.com/cage-kiosk/cage 、sway: https://swaywm.org/
- libcamera: https://libcamera.org/ 、mjpg-streamer: https://github.com/jacksonliam/mjpg-streamer
- Buildroot パッケージ定義: vendor/buildroot/package/ 以下の各 `*.mk`（当該リポジトリ内の一次資料）
