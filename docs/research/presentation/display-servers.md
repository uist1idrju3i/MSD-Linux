# 表示サーバー・描画基盤の調査（X11 / Wayland / 代替技術）

X11・Wayland とそれらを使わない代替描画経路を、Buildroot 2026.08 の収録状況と CardputerZero（CM0 / 512MB / VC4 GPU）での現実性込みで調査しました。表示先の前提（fb0/fb1、vc4 KMS、fbcon）は [hdmi-output.md](../hardware/hdmi-output.md) 、テキスト端末側は [fb-terminals-and-text-browsers.md](fb-terminals-and-text-browsers.md) を参照します。確認日は 2026-11-02 です。

## 1. 表示経路の分類

Linux 上でアプリが画面を得る経路は、おおよそ 6 系統に分かれます。

| 系統 | 概要 | 代表実装 |
|---|---|---|
| X11 サーバー | ディスプレイサーバー＋ウィンドウシステム。歴史が長く対応アプリが多い | X.Org server、KDrive（Xfbdev）、Xephyr、Xvfb |
| Wayland コンポジター | プロトコル＋コンポジターが描画と入力を兼務。現行の主流 | weston、cage、sway、labwc、phoc、wlroots 系 |
| KMS/DRM＋GBM 直結 | compositor を置かず、アプリが DRM デバイスを直接使う | mpv `--vo=drm`、kmscube、Qt `eglfs`、cog DRM platform、SDL `kmsdrm` |
| fbdev（`/dev/fbN`） | DRM の fbdev エミュレーションや firmware-fb に直接描く | fbv、fbi、links `-g`、NetSurf SDL 1.2、fbterm、w3m-img |
| ライブラリ内蔵描画 | アプリのツールキットが自分で fb/DRM に書く | Qt eglfs/linuxfb、SDL 1.2 fbcon、LVGL |
| 仮想・中継 | ローカル画面を持たず外部へ転送 | Xvfb、Xephyr、Xwayland、x11vnc、VNC/RDP 系 |

## 2. X11 系

Buildroot 2026.08 の収録状況です。【一次: vendor/buildroot/package/】

| 部品 | 版 | 役割 |
|---|---|---|
| xserver_xorg-server | 21.1.24 | X.Org 本体。`BR2_PACKAGE_XSERVER_XORG_SERVER` |
| xdriver_xf86-video-fbdev | — | fbdev 上に X を出す万能ドライバ。GPU 非依存 |
| xdriver_xf86-video-vesa | — | VESA/VBE 経路。実質レガシー |
| xserver（kdrive） | — | `BR2_PACKAGE_XSERVER_XORG_SERVER_KDRIVE`（Xfbdev 系の小型サーバー） |
| xwayland | 24.1.13 | Wayland 上で X11 アプリを動かす互換層 |
| xapp_* / xlib_* / xcb_* | — | クライアントライブラリ・ツール群（34 個の xdriver_* を含む X11R7 一式） |

MSD 向けの論点：

- X.Org は構成が大きく、`udev`（入力ホットプラグ検出）を前提とする部分があります。MSD は busybox `mdev`（`BR2_ROOTFS_DEVICE_CREATION_DYNAMIC_MDEV`）のため、`HAS_UDEV` 前提の経路は `eudev` 等への切替が必要です【一次: msd_cardputerzero_defconfig、xserver .mk】。
- fbdev ドライバなら「`/dev/fb1` に X を出す」だけなら小さく組めますが、現行ブラウザやアプリの多くは Wayland/GL 前提に移行しており、X 固有の利点は縮小しています。
- リモートからの X 転送（SSH -X）はネットワーク透過なので別経路として残ります（[ssh-implementations.md](../security/ssh-implementations.md) 参照）。

## 3. Wayland 系

| 部品 | 版 | 役割 |
|---|---|---|
| wayland | 1.24.0 | プロトコルライブラリ本体 |
| wayland-protocols | — | 拡張プロトコル定義 |
| wlroots | 0.20.0 | compositor 構築ライブラリ（KMS/DRM、libinput、seatd 連携） |
| weston | 15.0.1 | リファレンス compositor。DRM backend で直接 KMS に出せる |
| cage | 0.3.0 | 単一アプリをフルスクリーンで走らせる kiosk 向け compositor |
| sway | 1.12 | タイル型 compositor（デスクトップ用途） |
| seatd | 0.9.1 | logind 非依存の座席管理。busybox/s6 系と相性がよい |
| xwayland | 24.1.13 | Wayland 上で X11 アプリを動かす |
| 未収録 | — | labwc、wayfire、phoc、mir、river、hyprland、dwl、niri は Buildroot にありません |

MSD 向けの論点：

- wlroots 系は `libinput`・`udev`・`EGL`・`GLES`・`GBM`・`seatd` を要求します。`eudev` 化すれば wlroots/weston/cage/sway が選択肢になります【一次: wlroots/Config.in】。
- compositor は DRM デバイスを選べるため、「液晶 fb0 は fbcon の CLI、HDMI card1 にだけ compositor」という分業が構成できます。
- X11 アプリだけ残したい場合は XWayland を載せる併用形も取れます。

## 4. compositor を置かない代替経路

「display server を立てない」選択肢です。表示先が 1 面固定の用途（kiosk、サイネージ、専用アプリ）ではこれが最も軽い系統です。

| 経路 | Buildroot | 内容 |
|---|---|---|
| KMS/DRM + GBM 直 | libdrm、mesa3d 26.1.8、libepoxy | アプリが `/dev/dri/cardN` を開き、GBM/EGL で描く。mpv `--vo=drm`、kmscube、glmark2 が代表例 |
| cog DRM platform | cog 0.18.5 | WPE WebKit のランチャーが compositor なしで KMS/DRM にフルスクリーン描画（`BR2_PACKAGE_COG_PLATFORM_DRM`）。要 libinput/udev/EGL/GBM |
| Qt `eglfs` / `linuxfb` | qt5base、qt6base | Qt アプリが EGLFS_KMS 経由で単一画面に直接描画。X11/Wayland 不要 |
| SDL2/SDL3 `kmsdrm` | sdl2 2.32.10、sdl3 | SDL アプリが KMS/DRM に直接描画（`BR2_PACKAGE_SDL2_KMSDRM` 等） |
| fbdev 直 | fbterm、fbv、links `-g`、NetSurf SDL | `/dev/fbN` を mmap して書く最も素朴な経路。DRM_FBDEV_EMULATION 前提 |
| DirectFB | 未収録 | 上流が長期停滞し Buildroot からも外れた経路。新規採用は向きません【推測】 |
| kmscon | 未収録 | KMS 上のコンソール置き換え。fbterm の近縁、上流停滞 |

## 5. 経路ごとの前提と MSD での準備

| 経路 | 前提条件 | MSD 現状からの差分 |
|---|---|---|
| X11 fbdev | fbdev デバイス、kbd/mouse 入力 | 追加パッケージのみ。入力面は mdev でも概ね可【推測】 |
| X11 + udev | eudev、xf86-input-* | mdev→eudev 切替が事実上必須 |
| Wayland compositor | eudev、libinput、EGL/GLES、GBM、seatd、vc4 KMS | eudev 導入＋mesa3d EGL/GLES＋overlay |
| KMS/DRM 直（cog/mpv/eglfs） | vc4 KMS ノード有効、GBM/EGL、入力は libinput（udev） | `dtoverlay=vc4-kms-v3d` 追加＋mesa3d＋eudev |
| fbdev | DRM_FBDEV_EMULATION（既に y）または firmware-fb | 現状のまま使える最小経路 |

- **udev/eudev**：MSD は busybox mdev。libinput・wlroots・cog DRM・qt5webengine・X の入力ホットプラグは `BR2_PACKAGE_HAS_UDEV` を要求するため、本格的な GUI 経路では eudev 導入が鍵です【一次: 各 Config.in】。
- **GPU/メモリ**：mesa3d の `GALLIUM_DRIVER_VC4` で VC4 世代の OpenGL ES（2.x 系）が使えます。512MB RAM で WebKit/Chromium 系エンジンは重く、compositor の有無よりエンジン本体がボトルネックになります【推測】。
- **CMA**：vc4 KMS/GBM 系は連続メモリを要するため、公式 OS が `,cma-64` を付ける例がある点に注意します（[hdmi-output.md](../hardware/hdmi-output.md) 参照）。

## 6. 参考：要求の重いアプリの可否（Minecraft / OpenJ9）

表示系が立っても、アプリ側の要件が別にあります。例として Minecraft Java 版を見ます。

- Buildroot には target 向け `openjdk`（17/21/25、aarch64 対応）があり、JVM 搭載自体は可能です。OpenJ9（Eclipse Semeru）は未収録で、別途 aarch64 バイナリを持ち込む形になります【一次: package/openjdk】。
- ただし Minecraft Java 版は現行版で実質 2GB 級のヒープとデスクトップ GL 3.2（1.17 以降）を要求し、CM0 の 512MB と VC4 の GLES2 級では現実的ではありません。古い版でも LWJGL の aarch64 natives と gl4es（GL→GLES 変換、未収録）の整備が必要です【推測】。
- 現実的な代替として Buildroot には `minetest`（Minecraft 系の軽量 OSS ゲーム）が収録されています。

## 7. 未確認事項

- eudev 導入が mdev 前提の既存 init（S10mdev coldplug、modalias 自動ロード）に与える影響。
- wlroots 0.20 / weston 15 / cage 0.3 が card1（HDMI）だけを対象にできるかの実機確認。
- xserver の `HAS_UDEV` 分岐の具体的な機能差（mdev 下で X がどこまで動くか）。
- VC4（GLES2 級）で wlroots/Qt eglfs が要求する EGL/GLES 機能の充足度。
- XWayland・KDrive（Xfbdev）の対象版での動作とリソース量。
- `seatd` と busybox/s6 系の組合せでの権限まわり。

## 8. 主な出典（2026-11-02 確認）

- Buildroot パッケージ定義: vendor/buildroot/package/ 以下の `x11r7/`、`wayland/`、`wlroots/`、`weston/`、`cage/`、`sway/`、`seatd/`、`cog/`、`qt5/`、`sdl*/`、`mesa3d/`、`libdrm/`、`openjdk/` の各 `Config.in`・`*.mk`（当該リポジトリ内の一次資料）
- Wayland: https://wayland.freedesktop.org/ 、wlroots: https://gitlab.freedesktop.org/wlroots/wlroots
- weston: https://gitlab.freedesktop.org/wayland/weston 、cage: https://github.com/cage-kiosk/cage 、sway: https://swaywm.org/
- X.Org: https://www.x.org/ 、XWayland: https://gitlab.freedesktop.org/xorg/xserver
- seatd: https://git.sr.ht/~kennylevinsen/seatd 、libinput: https://www.freedesktop.org/wiki/Software/libinput/
- Qt eglfs: https://doc.qt.io/qt-6/embedded-linux.html 、SDL kmsdrm: https://wiki.libsdl.org/SDL2/README/kmsdrm
- Eclipse OpenJ9: https://eclipse.dev/openj9/ 、Minecraft Java 版動作要件（LWJGL/GL 版）は Mojang 公式システム要件・LWJGL ドキュメントに拠る
