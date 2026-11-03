# 音声・表示・IR・無線・GPIO・カメラの利用部品

[比較の索引](README.md) / [BSPと機能の責務](peripherals.md)

## 比較の前提

ここでは上位アプリが利用するAPIとdaemonを比べます。IC・配線・DeviceTree・driverの一致は[BSP比較](peripherals.md)が正本です。取得した上流資料と固定Buildrootのrecipeを根拠とし、代替構成のbuild・実行は本リポジトリでは試していません。端末の全機能を実機確認した記録でもありません。

| 候補 | 観測した公開版・固定Buildrootの版 | 機能と置換の条件 | licenseの確認範囲 |
|---|---|---|---|
| tinyalsa | GitHub公開版`v2.0.0`、Buildrootも`2.0.0` | kernel ALSAのPCM・mixer向けの小さなAPI。ALSA pluginやsession managerと等価とはしない | `LICENSE`は`NOTICE`への参照。`NOTICE`のBSD-3-Clause本文まで確認 |
| SDL3 | GitHub公開版`release-3.4.18`、Buildrootは`3.4.12` | 表示・入力・音声等の共通API。LCD driverやSDL2の無改変置換ではない | `LICENSE.txt`はZlib。外部backendと内包物の全license閉包は未確認 |
| LIRC | 公式入口は`0.10.2`、Buildrootも同版 | protocolのdecodeとsocketを介した利用。kernel rc-coreとLIRC UAPIを置換するものではない | BuildrootはGPL-2.0+。Debian配布版のcopyrightにはMIT等の部分もある。全upstream配布物の監査とは区別 |
| BlueZ | GitHub公開版`5.87`、Buildrootは`5.86` | Bluetoothのdaemon・library・tool。firmware収録だけではpairingを実装したことにならない | `COPYING`と`COPYING.LIB`はGPL-2.0、LGPL-2.1の文面。BuildrootはGPL-2.0+、LGPL-2.1+。各利用ファイルの許諾条件で判断 |
| libgpiod 2系 | kernel.orgの非prerelease tarは`2.3.1`。Buildrootは`libgpiod2=2.3.1`と`libgpiod=1.6.5`を別packageで提供 | GPIO character deviceのlibrary・CLI。旧API・CLIやsysfsの単純な版更新ではない | 現行`COPYING`はlibrary LGPL-2.1-or-later、tools等GPL-2.0-or-later、kernel UAPI headerはsyscall例外付き、文書はCC-BY-SA-4.0と区別 |
| libcamera | GitHub mirrorのtag一覧に`v0.8.0`。取得した公式master資料も同版を表示 | pipeline handler・sensor制御等を提供。Raspberry Pi側のfork・kernel・IPA・tuningと一致するとは限らない | 本文の採用判断だけではIPAや同梱物を含めたlicense閉包を認定しない。固定recipeの扱いは[BSP比較](peripherals.md)を参照 |

観測版は更新の推奨や動作保証ではありません。release API、tag、開発HEAD、配布版の情報を区別し、固定版の設定を上流の既定値で置き換えて説明しません。

## tinyalsa: 小ささと機能削減の対応

[公式README](https://github.com/tinyalsa/tinyalsa)は、必要最小限のPCM・mixer APIを目的とします。`tinyplay`、`tinycap`、`tinymix`、`tinypcminfo`の用途を、再生・録音・mixer・能力照会に分けて選べます。取得した開発HEADのMeson設定にはdocs・examples・utilsがあり、必要なlibraryと試験toolを別に構成できます。ただし、公開版の全optionと同一とは認定しません。

比較するのは、ALSAの直接利用、tinyalsaへの呼出しの移植、複数clientを扱うPipeWire等です。小さなAPIでも、hardwareのsample format、rate、channel、buffer、underrun、mixerの安全な初期値はアプリ側に残ります。公開版が2021年だからといって、現在のHEADの変更や保守状況を確認せずEOLとは呼びません。

固定Buildrootのtinyalsaはdynamic libraryを要求します。静的リンクを選ぶ案にはこの制約も含めます。READMEにある試験用の`chmod 777 /dev/snd/*`は製品へ導入しません。再生・録音のUID/GIDとdeviceへのアクセス範囲を先に設計し、録音を許さない利用者による拒否試験を行います。

## SDL3: APIの更新と描画経路を分ける

[SDL3資料](https://wiki.libsdl.org/SDL3/)と[SDL2からの移行資料](https://wiki.libsdl.org/SDL3/README-migration)を比較の入口とします。公開版と固定Buildrootは上表のとおりです。BuildrootにはSDL1・SDL2・SDL3があり、「新しい系列だからrecipeがない」とは扱いません。

一方、固定BuildrootのSDL3 KMS/DRM経路には、threads、GBM provider、EGL、OpenGLまたはOpenGLES等の条件があります。取得した開発HEADのCMakeにもKMSDRM、libudev、EGLの経路があります。`/dev/fb0`に書けるだけでこの経路を利用できるとは言えません。現在のLCD表示、DRMへの移行、描画backend、入力、seat管理、音声を分けて設計します。BSD用のKMSDRM READMEにあるdevice権限を、そのままLinux製品の手順へ転用しません。

採用前には、ソフトウェア描画を含む依存closure、起動時間、RAM、描画遅延、消費電力、権限を実機で比較します。小さな単独GUIならLVGL等も比較し、CLIを残すだけならSDLを導入しない案も基準にします。アプリのSDL2→3移植と、driverのfbdev→DRM移行は別の実験です。

## LIRC: socketへの接続も操作権限

[公式入口](https://www.lirc.org/)のニュースは`0.10.2`を2022-10-04の公開版とします。一方、取得した[lircd manual](https://www.lirc.org/html/lircd.html)の更新表記は2017年です。古いmanualの値を現在の実行binaryで確認した既定値とせず、採用時に固定版のsource・help・実行結果で照合します。公開版の間隔だけをEOLやsecurity supportの保証にしません。

同manualでは、Unix socketの初回作成時の既定permissionが`0666`、`--listen`の既定addressが`0.0.0.0`と説明されています。`--allow-simulate`は任意IR eventの模擬を許し、shutdown等の割当てによっては大きな操作権限になります。受信だけを許す利用者と、送信・模擬event・設定変更を許す管理者を分け、不要なTCP listenerとsimulateは有効にしません。既存socketではpermission指定が効かないという条件も試験します。

kernelで必要なprotocolを処理できるなら、`ir-keytable`等のtoolだけで足りるかを先に調べます。学習・raw送信・独自protocolが必要な場合にdaemonを比較します。IR設定の公式OSとの差は未解決のため、ユーザー空間のtool選定だけで対応済みとはしません。

## BlueZ: pairingとpolicyを製品側で決める

[BlueZ repository](https://github.com/bluez/bluez)はkernel.orgのmain repositoryのmirrorです。取得したsecurity policyにはprivate advisory窓口と、volunteerによるbest effortで応答時間を保証しない旨があります。窓口の存在を固定版の長期保守保証とは扱いません。

`bluetoothd`、必要なprofile、D-Bus、pairing agent、discoverable/pairable状態、bond情報の保存、再接続、firmwareとkernel driverを別々に確認します。全profile・OBEX・試験tool・experimental機能を一括で入れる必要はありません。取得したpolicyは上流systemd unitのsandboxも評価条件にしますが、MSD/LinuxのBusyBox initが同じ制限を提供するわけではありません。

無認証でdiscoverableな常時起動を既定にせず、初回pairingの利用者の確認と期限、keyboard等の入力権限、bondの削除・復旧を設計します。Bluetooth対応、音声profile、Bluetooth経由のnetworkは別々に検証し、一つの成功を全機能へ広げません。

## GPIOとカメラ: 標準化を進めても残る条件

[libgpiod公式資料](https://libgpiod.readthedocs.io/en/master/)はsysfs GPIOからcharacter deviceへの移行を説明します。固定Buildrootの1系recipeは`CONFIG_GPIO_CDEV_V1`を有効化する処理も持つため、2系へ移る案ではkernel UAPI、アプリの要求API、CLIの引数とline保持時間、既存scriptを合わせて確認します。libraryのlicenseをGPIO toolや文書へ一律に当てはめません。

GPIO lineの初期値・極性・競合・権限は標準APIでも残ります。kernel driverが管理するresetや電源を、userspaceが横から操作してよいわけではありません。製品の未解決の共有reset制御をGPIO libraryの更新だけで解決したとは扱いません。

[libcamera公式master資料](https://docs.libcamera.org/master/)とtag一覧は、取得できなかった旧URLやRelease APIとは別に保存しました。GitHubの`releases/latest`の404はtag不在や開発停止の証拠ではありません。Raspberry Pi用のsensor・Unicam/ISP・IPA・tuningの整合性を確かめ、raw取得と調整済み画像を区別します。cameraを接続していない状態、sensor違い、権限拒否、buffer枯渇、停止・再起動も採用試験に含めます。

## 保守の判断と残る試験

各候補のlicense・版・security窓口について、取得できた範囲を上記に明示しました。明示的なsupport期限が見つからないことは、無期限保守やEOLの証拠ではありません。採用前には固定する配布物、内包・外部依存、全licenseと通知、脆弱性監視、必要APIを再確認します。

全deviceの実機動作、代替binaryのRAM・起動・消費電力、権限の強制・拒否試験は残っています。取得失敗と訂正を含む一次資料の台帳は[sources.json](sources.json)、資料照合の反復と負の対照は[追加調査の検査記録](../../experiments/2026-11-02-alternatives-followup-audit.md)に保存します。
