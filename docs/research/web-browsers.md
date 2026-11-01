# ウェブブラウザの調査

CardputerZero（CM0 / 512MB / VC4 GPU）で動かせるウェブブラウザを、表示経路（[display-servers.md](display-servers.md)）と Buildroot 2026.08 の収録状況、エンジン世代・RAM の観点で調査しました。テキストブラウザ（w3m・Lynx・links のテキストモード等）は [fb-terminals-and-text-browsers.md](fb-terminals-and-text-browsers.md) に既出のため、本書は画像・JS を伴う系を中心に整理します。確認日は 2026-11-02 です。

## 1. 選択肢の全体像

表示経路とエンジンで分けると、候補は次のように整理できます。

| 分類 | ブラウザ | エンジン | 表示経路 | Buildroot |
|---|---|---|---|---|
| 組込み向けフル機能 | cog + WPE WebKit | WebKit（Safari 系、現行世代） | KMS/DRM 直 または Wayland | 収録 |
| Qt 系 | Qt WebEngine / Qt WebKit | Chromium 系 / 旧 WebKit | eglfs（KMS）・X11 | 収録 |
| 軽量独自エンジン | NetSurf | 独自エンジン＋duktape JS | SDL（fbdev）・GTK3 | 収録 |
| レガシー軽量 | Dillo、links `-g` | 独自エンジン（JS なし） | X11 / fbdev | 収録 |
| X11/Wayland フル機能 | WebKitGTK 系（surf、vimb、Epiphany 等） | WebKit | GTK3/4 経由の X11 か Wayland | エンジンのみ収録 |
| デスクトップ大物 | Firefox、Chromium 系 | Gecko / Blink | X11/Wayland | 未収録 |

## 2. cog + WPE WebKit（組込み向け本命）

| 項目 | 内容 |
|---|---|
| 収録 | `cog` 0.18.5、`wpewebkit` 2.50.5、`libwpe` 1.16.3、`wpebackend-fdo` 1.16.1 |
| 表示経路 | `BR2_PACKAGE_COG_PLATFORM_DRM`（compositor なしで KMS/DRM に直接フルスクリーン）または `BR2_PACKAGE_COG_PLATFORM_FDO`（Wayland backend、weston/cage 等の compositor が前提） |
| 前提 | libinput・udev・EGL・GBM・dbus・MMU・スレッド。glibc ツールチェーン |
| 位置付け | Igalia 系の WPE（WebKit Platform for Embedded）は組込み Linux 向けの WebKit 実装で、現在も活発にメンテされる系列です【一次: package/cog、wpewebkit】 |

MSD での要点：

- `mdev` 構成のままでは `HAS_UDEV` が立たず cog DRM platform を選べません。`eudev` 導入が前提になります（[display-servers.md](display-servers.md) §5）。
- DRM platform なら compositor すら要らず、HDMI card1 にだけ cog を立てて内蔵液晶は fbcon のまま、という構成が最小の依存で実現できます。
- 512MB RAM ではフル機能ブラウザとして最も軽い部類ですが、現代の重いサイトでは OOM 級になり得ます【推測】。

## 3. Qt 系

| ブラウザ | 版 | 内容 |
|---|---|---|
| qt5webengine | Qt5.15 系（Chromium 系） | `BR2_PACKAGE_QT5WEBENGINE`。要 glibc・udev・EGL・GLES（eglfs 経路）。Chromium 87 相当のエンジンで現在は旧世代 |
| qt5webkit | 5.212.0-alpha4 | 旧 WebKit。`qt-webkit-kiosk`（a7720e5…）がこの上に kiosk ブラウザを提供 |
| qt-webkit-kiosk | — | qt5webkit 上で動く専用 kiosk ブラウザ。要 `JSCORE_AVAILABLE`（aarch64 は対象内） |

MSD での要点：

- qt5webengine は Chromium 系で現行サイトの互換性は高い反面、RAM・ストレージとも最重クラスです。512MB では現実的に厳しいと見込みます【推測】。
- qt5webkit 系はエンジンが古く（2016 年相当）、TLS/JS の現行サイト対応が弱いため、kiosk で自前のページを表示する用途向きです。
- eglfs を使えば X11/Wayland なしで動きますが、やはり `udev`（libinput）依存のため eudev が前提です。

## 4. 軽量・独自エンジン系

| ブラウザ | 版 | エンジン/JS | 表示経路 |
|---|---|---|---|
| NetSurf | 3.10 | 独自エンジン。HTML4/CSS2.1＋限定的な JS（内部 duktape） | `BR2_PACKAGE_NETSURF_SDL`（SDL 1.2 → fbdev）または `BR2_PACKAGE_NETSURF_GTK3` |
| Dillo | 3.3.0 | 独自エンジン。JS なし、CSS 限定 | FLTK 上の X11（`BR2_PACKAGE_XORG7` 前提） |
| links `-g` | 2.30 | JS なし | framebuffer / DirectFB / X11。`BR2_PACKAGE_LINKS_GRAPHICS` は GPM または X11 を要求 |
| lynx | — | テキストのみ | 端末（fbcon/fbterm 上で動く） |

- NetSurf はこの中で唯一 JS 実行を持つ軽量系ですが、対応範囲は限定的で、SPA 系サイトはまず動きません【推測】。
- Dillo・links `-g` は JS なしで、表示中心の使い方（ドキュメント・画像付きページの閲覧）に向きます。
- NetSurf の SDL frontend は SDL 1.2（fbcon バックエンド）で、`/dev/fbN` に直接出せるため compositor 不要です。

## 5. 収録されていない主要ブラウザ

Buildroot 2026.08 に無いものです。

| ブラウザ | 理由/状況 |
|---|---|
| Firefox | 未収録。X11/Wayland と大きな依存ツリーが前提 |
| Chromium 本体 | 未収録。規模が大きく Buildroot 化されにくい |
| Servo | 未収録。研究/実験段階のエンジンで、組込み向けの実用経路はまだ薄い |
| Ladybird | 未収録。新興ブラウザでまだ発展段階 |
| Falkon / Qutebrowser / surf / vimb / luakit / badwolf / midori / Epiphany / nyxt / Otter | 未収録。いずれも X11/Wayland と GTK/Qt 依存 |
| browsh / carbonyl | 未収録。ブラウザを別プロセスで起こして端末に表示する方式で、本体に大きな依存が要る |

## 6. 表示先の固定と運用

- `/dev/dri/cardN` や `/dev/fbN` の番号は probe 順依存です。HDMI 側に出す場合は `/dev/dri/by-path/` や `card*-HDMI-A-1` のコネクタ名で固定するのが確実です（[hdmi-output.md](hdmi-output.md) §4）。
- 内蔵液晶を CLI のまま、HDMI 側にだけブラウザを立てるには、cog DRM platform・mpv `--vo=drm`・Qt `eglfs`・SDL `kmsdrm` が該当します（[hdmi-output.md](hdmi-output.md) §6 参照）。
- 電力面では、ブラウザエンジン（特に WebKit/Chromium 系）の常駐メモリと描画が支配的で、表示サーバー自体の差よりエンジン選択の影響が大きいです。

## 7. 未確認事項

- cog DRM platform の実機動作（vc4 + GBM + libinput、入力はキーボード/タッチを libinput 経由で拾えるか）。
- qt5webengine が aarch64 CM0/512MB で OOM にならないか、実運用でのページ読み込み可否。
- NetSurf の JS 実行範囲（duktape 版の対応度）と、SDL1.2 fbcon 経路での描画安定性。
- `eudev` 化による mdev coldplug（S10mdev）との整合。
- `Broadcast RGB`・`video=` 強制と、cog/Qt eglfs のモード選択の干渉。
- TLS（libsoup3/openssl）と証明書束の整備状況（HTTPS の必須条件）。

## 8. 主な出典（2026-11-02 確認）

- Buildroot パッケージ定義: vendor/buildroot/package/ 以下の `cog/`、`wpewebkit/`、`wpebackend-fdo/`、`libwpe/`、`qt5/qt5webengine/`、`qt5/qt5webkit/`、`qt-webkit-kiosk/`、`netsurf/`、`dillo/`、`links/`、`webkitgtk/`、`duktape/`、`quickjs/`、`lynx/`、`minetest/`、`openjdk/` の各 `Config.in`・`*.mk`（当該リポジトリ内の一次資料）
- WPE WebKit / cog: https://wpewebkit.org/ 、https://github.com/Igalia/cog
- WebKitGTK: https://webkitgtk.org/
- NetSurf: https://www.netsurf-browser.org/ 、Dillo: https://dillo-browser.github.io/ 、links: http://links.twibright.com/
- Qt（eglfs / QtWebEngine）: https://doc.qt.io/ 、Chromium / Firefox / Servo / Ladybird は各公式サイトの動作要件・収録状況に拠る
- 表示経路の前提: [display-servers.md](display-servers.md)、[hdmi-output.md](hdmi-output.md)、[fb-terminals-and-text-browsers.md](fb-terminals-and-text-browsers.md)
