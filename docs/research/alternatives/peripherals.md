# 周辺機能・BSP・device APIの代替

[比較の索引](README.md) / [部品・配線の照合](../hardware-wiring-audit.md) / [公式OSとの差異](../official-software.md)

## 結論と比較の境界

CardputerZeroの全機能を使う目標は維持します。ただし、ユーザー空間のlibraryを追加しても、未接続のdevice、未対応のdriver、電源・resetの制御は補えません。**BSP、kernel driver、標準API、利用アプリ、権限、実機試験**を別の層として比較します。2026-11-02 UTCに確認した公開資料と固定Buildrootを根拠とする提案であり、製品設定は変更していません。代替構成のbuild・実行は本リポジトリでは試していません。

現行のM5ソースは`37b42d9451495b5597dd7e50cab502da8028f9c2`です。[local package](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)がkernel module、DTBO、LCD・IMUのfirmwareとkeymapを扱います。回路、GPIO番号、製品の版、16 moduleの収録確認は既存の監査を正本とし、ここでは再転記しません。収録・DT合成は実機動作の確認ではありません。

## 機能ごとの責務と代替

| 機能・現行の層 | 比較する方法 | 利点と費用・危険 | 提案と採用前の確認 |
|---|---|---|---|
| LCD、M5のST7789V関連driver、fbcon | 現行driverを維持 / upstream DRM panel・小型DRM driverへ寄せる | upstream化は追従の負担を減らせる可能性がある。一方、controller名が同じでも初期化列、SPI、reset、backlight、回転は一致するとは限らない | upstream化の実験候補。cold boot、再起動、blank/unblank、色順、文字表示、電源保持を同じ実機で比較。firmware blobを不要にできるとは未確認 |
| 表示アプリ、現在はCLI | fbcon継続 / LVGL / SDL等の直接描画 / Wayland compositor | CLIにはcompositor不要。LVGLはGUI libraryで、LCD driverの代替ではない。Waylandは複数clientの分離・表示管理を設計できるが、compositor・seat・inputの責務が増える | CLIを基準に維持。GUIが要件になった時点で独立比較。描画権限をupdate権限と共用しない。GUI障害時にもconsoleで復旧できること |
| TCA8418 keyboard driver、keymap、kbd | console keymap / evdev直接利用 / libinputを介すGUI | `kbd`はconsoleの配列・font等を扱う。libinputは上位のinput処理で、I2C keyboard driverやconsoleの`loadkeys`を置換しない。evdevを読める主体は他の利用者の入力も盗み見できる | CLIはkbdを基準に維持。配列、修飾key、押し続け、取りこぼし、disconnect、login前後の権限を実機試験。入力deviceの一括world-readable化はしない |
| ES8389、ASoC、音声経路 | ALSA直接 / tinyalsa等の限定API / PipeWire / PulseAudio・JACKの用途別構成 | ALSA直接は単一用途に小さくできるが、mixer、sample format、録音・再生の競合をアプリ側で扱う。PipeWireはaudio/video graphと複数clientを扱い、session managerのpolicyも必要 | まずcodec・DAI・mixer・speaker/micの実機確認。単一用途はALSAを実験の基準、複数clientが必要ならPipeWireを再評価。音量初期値、無音時の消費、録音権限、異常終了時のdevice解放を確認 |
| CSI camera、Unicam・sensor、libv4l tools | V4L2/media-ctl直接 / libcameraのpipeline / GStreamerによる利用 | V4L2はkernel UAPI、libv4lはその補助library群。libcameraは複雑なpipeline・制御を統合する別の層。GStreamerは処理の接続を担い、sensor driverの代替ではない | raw撮像と調整済みの画像を分ける。sensor、レーン数、clock、ISP、露光・色調整、buffer、権限の確認後に選定。詳細は次節 |
| BMI270・磁気sensor | 現行M5 driver / upstream IIO driver / userspace I2C直叩き | IIOはchannel、scale、trigger、buffer等の共通の枠組みを使える。I2C直接操作はkernel driverとの競合、初期化firmware、軸・単位、電源管理を自前で引き受ける | upstream IIOとの機能差を実機で埋める候補。部品名だけで互換とせず、firmware、calibration、軸向き、周波数、buffer overflowを比較。raw I2Cを通常アプリへ渡さない |
| RTC | kernel RTC class / userspace I2Cの自作制御 | RTC classは共通の時刻・alarm APIを提供する。RTCがあっても値の正しさや初回の時刻は保証されず、TLS・metadata expiryの信頼できる時刻と同義ではない | RTC classを基準にする。電池切れ、初期化されていない値、逆行、電源断後の保持、alarmの必要性を実機で確認。認証できない時刻を理由にTLS検証を無効化しない |
| BQ27220等の電池・充電・電源保持 | power_supply class / 固有daemon / userspace I2C | classの属性は単位まで定義されるが、hardwareが全属性を供給するとは限らない。残量の表示と、安全な充電・shutdown制御は別の責務 | 既存driverとclassを基準にする。電圧、残量、充電・放電、温度、電池なし、低残量shutdown、USB給電と再起動を確認。監視のために任意GPIO/I2C書き込みを許さない |
| IR | kernel rc-coreと既存tools / LIRC daemon / raw GPIO波形の自作 | protocolの変換、raw送受信、学習、GPIO波形生成は異なる機能。LIRCを入れれば回路やDTの差異が解消するわけではない | 公式OSとの未解決の設定差を先に確認。送信・受信・repeat、誤入力、負荷時の時序、権限を試験。必要なprotocolを確定してからdaemonの要否を判断 |
| GPIO・共有reset・電源制御 | kernelの各subsystem / GPIO character device v2とlibgpiod / 旧sysfs GPIO | Linuxの資料は、適切なkernel driverがある機能をuserspace GPIOで置換しないよう求める。character deviceでもline競合・active-low・初期値の責務は残る | 正規driverを優先。保守用GPIO操作は用途を限定し、常用アプリへ全lineを許可しない。共有resetを誰がいつ操作するかは既存の未解決事項として残す |
| USB・Ethernet・Wi-Fi・Bluetooth | kernel driver / 接続・pairing・role管理のuserspace | driver、firmware、認証、IP設定、USB gadget/hostは別。Bluetooth firmwareの収録はBlueZやpairingの実装を意味しない。network managerはEthernet driverを置換しない | [通信比較](network.md)と公式OS差異へ集約。無線を一括で常時onにせず、用途と起動順を決める。USB role、LAN、Wi-Fi、Bluetoothは各々実機確認 |

上表の小型library、一般的なframework、kernelの同種driverは候補の粒度が異なります。「用途がある」と「同等の代替である」を区別します。特にtinyalsa、SDL、LIRCの本機向け機能・版・licenseの詳細監査は今回の取得だけでは完了していません。これらを推奨実装として確定しません。

## カメラはlibv4lとlibcameraの二者択一ではない

固定Buildrootの`libv4l`は1.32.0で、[Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libv4l/Config.in)はC++・threads等を要求し、`LIBV4L_UTILS`に`v4l2-ctl`、`media-ctl`、`v4l2-compliance`、`ir-keytable`等を列挙しています。列挙された全toolが最終imageに入るかは、最終構成・install結果で確認する必要があります。cameraを使うために全DVB・IR関連toolを製品へ残す必要があるとも限りません。

一方、[libcameraの固定recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libcamera/libcamera.mk)はv0.7.1で、C++、libyaml、GnuTLS、host側のPython生成tool等を使います。`rpi/vc4`を含むpipeline選択があり、Python binding、compliance、GStreamer、V4L2互換層、GUIはそれぞれ別の条件です。[公式の構築案内](https://libcamera.org/getting-started.html)もcoreと追加機能の依存を分けています。互換層があることだけで、全cameraアプリを無変更で動かせるとは扱いません。

MSD/Linuxの[fragment](../../../board/cardputerzero/linux.fragment)はUnicamとIMX219を指定し、BCM2835 ISP等を無効にしています。libcameraのPi向けpipelineを評価する場合は、最終kernel・DT・ISP・firmware・sensor構成を改めて揃える必要があります。recipeを追加するだけの試験にはしません。撮像の成立、auto exposure/white balance、rawと処理済み画像、長時間のbuffer動作を別々に判定します。4レーンの配線能力と現在のDT設定の差も[回路監査](../hardware-wiring-audit.md)を参照します。

## BSPを小さくする順番

1. 機能ごとに、driverのprobe、DTの接続、必要firmware、利用API、実機結果を一行に対応づけます。無効な機能があるからといって、使用部品をBOMから消しません。
2. 現行M5 driverとupstreamの同種driverを、対応するcompatible、初期化、電源管理、interrupt、ABIで比較します。取り込む場合も`vendor/`を直接改変せず、固定値とpatchで差を管理します。
3. 必要なtoolを診断用imageと配布imageで分ける実験を行います。削除後の復旧手段を先に用意し、周辺機能の削除を性能向上として数えません。
4. deviceの読み取り、設定変更、raw bus操作を別の権限にします。device番号やminorは固定名を仮定せず、再列挙・USB hotplugでも正しい機器だけが許可されることを確認します。mdev/udevの比較は[init](init.md)を参照します。
5. display、camera、audio、IMU、networkを同時使用し、IRQ、DMA、RAM、電源・resetの競合を確認します。各機能の単独成功だけで全機能の同時使用を認定しません。

LCD初期化データ、BMI270 firmware、keymapにはlocal recipe上のlicense未確認項目が残ります。upstream driverへの移行で法的条件まで解決するとは限りません。module署名も実装の正しさやleast privilegeを証明しません。

## 一次資料と未確認範囲

取得URL・固定ref・bytes・hashと取得失敗は[sources.json](sources.json)に保存します。libcameraのGitHub mirrorは機能説明の補助とし、正式なソースの所在は公式ページとBuildroot recipeのGitLab URLで照合しました。GitHub Release APIの404を保守停止と判断していません。存在しないlibgpiodのGitHubパスを照会した失敗も残します。

- Linux 6.18: [GPIOの使い分け](https://docs.kernel.org/6.18/driver-api/gpio/using-gpio.html)、[character device v2](https://www.kernel.org/doc/html/v6.18/userspace-api/gpio/chardev.html)、[input UAPI](https://docs.kernel.org/6.18/input/input_uapi.html)、[IIO](https://docs.kernel.org/6.18/driver-api/iio/index.html)、[power_supply](https://docs.kernel.org/6.18/power/power_supply_class.html)、[RTC](https://docs.kernel.org/6.18/admin-guide/rtc.html)、[DRM UAPI](https://docs.kernel.org/6.18/gpu/drm-uapi.html)。subsystemの説明であり、本機の全driverの実装確認ではありません。
- [PipeWireのgraph・session・permissions](https://docs.pipewire.org/page_overview.html)では、serverとsession managerの責務を区別しました。ALSA等のbackendの存在をdeviceの動作実績とは扱いません。
- [libinputの範囲](https://wayland.freedesktop.org/libinput/doc/latest/what-is-libinput.html)と[LVGLの説明](https://github.com/lvgl/lvgl/blob/1918a999d700ef195a53a73f8765a353e74dc07e/README.md)を参照しました。LVGL coreのMITと別の開発製品の条件を混同せず、他環境のRAM・flash数値を本機の改善値として引用しません。

IRの指定した文書URL、libcameraの旧docs URL、BlueZ home、libgpiodの指定した文書URLは取得に失敗しました。また、ALSA wikiの同じURLを再取得した際に、初回のraw fileを上書きしました。初回のlength・hashは未照合として残し、後の取得分だけを実体と照合しています。取得成功と証拠の照合、本文の精読を区別します。IRの全protocol、Bluetoothの現行security設定、各候補の全release・EOL、配布licenseの完結した監査は残ります。実機の表示・音声・撮像・無線・電断試験は行っていません。

[比較の索引へ戻る](README.md)
