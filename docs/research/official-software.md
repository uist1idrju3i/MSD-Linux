# 公式OS・BSPとMSD/Linuxの比較

[RESEARCH](../../RESEARCH.md) / [部品と回路接続](hardware-wiring-audit.md) / [生成物の確認記録](../experiments/2026-11-02-hardware-artifact-audit.md)

## 結論と確認範囲

2026-11-02 UTCに公開ソースとMSD/LinuxのCI生成物を照合した。公式OSはDebian系のGUI、MSD/LinuxはBuildrootのCLIであり、同じ利用者向け構成ではない。BSPの接続情報は再利用するが、公式のサービス・権限・GUI・可変版の取得方法をそのまま取り込まない。

GPIO、電源保持、reset、Ethernetには実機でしか解決できない項目が残る。資料の曖昧さを理由にGPIOの極性やUSB IDを推測して変更していない。生成DTBOの合成、カーネル設定、モジュールとfirmwareの収録は確認したが、実機の表示・入力・撮像・通信・電断耐性は確認していない。公式配布imageのバイナリ内容も未確認である。

## 比較する版

| 記号 | 固定した資料・実装 | 根拠 |
|---|---|---|
| P | `CardputerZero/pi-gen`、`cardputerzero_v1.0`、`791a985d4efca7327ae1fdb6c48230ac0d1ee1bc` | [ソース](https://github.com/CardputerZero/pi-gen/tree/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc)。取得時のbranch HEAD |
| M | `m5stack-linux-dtoverlays`、`37b42d9451495b5597dd7e50cab502da8028f9c2` | [ソース](https://github.com/m5stack/m5stack-linux-dtoverlays/tree/37b42d9451495b5597dd7e50cab502da8028f9c2)。MSD/Linuxのsubmodule固定値と取得時のmain HEADが一致 |
| K | Raspberry Pi Linux、`b3495ea401d709af0701a85babcba5e3d788a602`、`6.18.59` | [ソース](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602)。MSD/Linuxのdefconfig固定値 |
| D | MSD/Linux、CI checkout `c96e5faf015c828a213c8ea64f613b4a429196c7`、PR head `84ca145032216b696a8944d54b4f820edc1ac565` | [CI run](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41477653658)。両者のtree `61584002a3ee682ff6b7f7d891d705a5fce079be` は一致。headと実際のcheckoutは区別する |

PとKの取得ファイルのURL・bytes・SHA-256は [ソース取得記録](official-software-sources.json)、Dのimage・DTBO・モジュールの値は [生成物の記録](../experiments/2026-11-02-hardware-artifact-audit.json) に保存した。旧調査のM5 `7551854`、Linux `2341883`は現在の固定値ではない。回路図の版と製品差は [ハードウェア監査](hardware-wiring-audit.md) を参照する。

## 公式OSの作り方

PはDebian trixie / arm64、systemd、labwc / Waylandを使うRaspberry Pi OS派生である。kernelとGUIアプリでは固定方法が異なる。

- **kernel**: [`stage0/02-firmware`](https://github.com/CardputerZero/pi-gen/tree/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware) は期待SHA-256を検査し、APT preferencesとholdで `6.18.39-1+rpt1` を固定する。Kと同じ版ではない。
- **M5ドライバ**: [`01-run.sh`](https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh) はmainを浅くcloneし、取得commitを `/etc/cardputerzero-dtoverlays.commit` に記録する。事前固定ではない。`CONFIG_CARDPUTERO_V0_5=y` で `install` と `config_setup` を呼ぶ。Pは `rpi-config.py` を先に配置するため、Mの未固定Gist取得fallbackはこの手順では使わない。
- **APPLaunch**: [`02-run.sh`](https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/02-run.sh) は指定版・local `.deb` を受け付け、未指定なら公開日の新しいassetを選ぶ。draftは除外するが、prereleaseの除外は書かれていない。LaunchWizardの存在とarm64 packageを検査する。ダウンロードのSHA-256表示は、期待hashとの照合とは別である。
- **付属アプリ**: [`03-run.sh`](https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/03-run.sh) はdraftとprereleaseを除外する一方、版・URL・local fileの指定より最新releaseを優先する。kernelと同じ再現性はない。
- **表示**: Pは同梱の `start.elf` / `fixup.dat` とsplashを配置し、`gpu_mem=128`、`vc4-kms-v3d,cma-64` を設定する。APTのfirmwareだけで決まる構成ではない。APPLaunchの配布binaryとLVGLの実際の版は、本照合では調べていない。
- **起動と既定値**: U-Bootを使う経路ではない。ADB関連サービスは既定off、journalは永続化して上限50MB、cmdlineに `quiet fbcon=map:off cfg80211.ieee80211_regdom=AE` を加える。日本で使う場合の無線規制値としてAEをそのままコピーしない。

以上は公開ビルドscriptが指示する内容である。配布imageの全サービス、packageのpostinst、launcher内部の更新処理まで検査したことを意味しない。read-only rootfs、overlayfs、tryboot、RAUC、Menderの有無も、配布image全体の確認なしに断定しない。公開URLの404やorg一覧への非掲載は「機能が存在しない」証拠にはしない。周辺実装の探索経緯は [コミュニティ調査](community-2026-11.md) に分ける。

## BSP・DeviceTree・運用の差異

「意図した差」は製品方針による選択、「未確認」は追加のソースまたは実機が必要な項目である。Mを取得時の公式ドライバ基準とするが、Pの可変main取得で作った過去の全imageと一致するとは扱わない。

| 対象 | MSD/Linux D | 公式P / M / Kとの照合 | 分類・採否・訂正 | 実機での確認事項 |
|---|---|---|---|---|
| OS / init / UI | Buildroot、BusyBox init、mdev、fbconとkeyboardのCLI | PはDebian、systemd、udev、Wayland、APPLaunch | 意図した差。GUIや `.deb` 互換は導入しない | LCDへのgetty表示と内蔵keyboardでのログイン |
| kernel / M5固定 | KとMを事前固定しlocal Buildroot packageで構築 | Pはkernel固定、M5はmain取得後に記録 | 意図した差。固定を維持 | 上流更新ごとの回帰試験 |
| base DTB / overlay | CM0 DTBにv5、BQ27220、BMI270/BMM150、IMX219 | KとMに同じ定義。QEMUのPi3 DTBとは別 | 選択と生成DTBOは整合。合成成功 | 基板版、firmwareが選ぶDT、runtime DT、probe順 |
| camera | 明示的IMX219、UnicamとIMX219 module、raw V4L2 | Mも明示的に有効化。Kの既定endpointは2 lane | 整合。物理4 laneとLinux既定2 laneを区別 | sensor ID、2-lane raw capture。4lane overrideは別試験 |
| GPU / CMA / firmware | `gpu_mem=16`、cut-down firmware、GUIなし | Pは128MBとKMS用64MB CMA、同梱splash firmware | 意図した差。CLIの容量削減を優先、表示成立は未確認 | firmware起動、LCD、camera buffer割当 |
| LCD | MのLCD関連module、panel firmware、v5を収録 | MにはST7789vとDRM panelの実装がある | 収録とaliasを確認。実際のbindは未確認 | driver symlink、fb/DRM device、fbcon表示 |
| audio | `everest,es8390` とMの音声modules | Mのcompatibleと一致、回路の部品はES8389 | 名前の誤記と決めつけてcompatibleを変えない | I2S clock、録音再生、GPIO17/24、CTIA/OMTP |
| RTC | `epson,rx8130` と `rtc-ds1307` module | Mのv5、Kのdriverと一致 | 収録とDT宣言は整合。停電保持は未確認 | RTC値、時刻同期、backup回路 |
| IMU / 磁力計 | `0x68` BMI270、AUX側BMM150、firmware | Mはrootの磁力計nodeと `bmi270-parent` で表現 | 整合。主I2CのES8389との衝突ではない | IIO値、AUX初期化、Liteの不在時動作 |
| reset | GPIO16宣言、TCAの `rest-gpios` | MのTCA Cはこのpropertyを取得せず、M5IOE1のGPIO reset処理もコメントアウト | 上流継承・責務未確認。typo修正だけで解決とはしない | MCU仕様、PYG3共有reset、hubとkeyboardへの影響 |
| USB | DWCOTGとDWC2を構築、`dwc2` overlay未指定 | Mの `config_setup` は `dwc2` を追加 | 設定差。意図的なUSB運用かは未確認 | Type-Cのhost/device、GL852G列挙、reset、給電 |
| Ethernet | SR9700 / SR9800 / DM9601を収録 | KのID表に `0fe6:9700/9702/9800/8101` 等。確認範囲に `0fe6:9900` の登録なし | SR9900A対応は未確認。型番からIDを追加しない | 実機VID:PID、bind driver、通信と再接続 |
| IR | 既存RC modules収録、IR overlay未指定 | MはGPIO13受信、GPIO12送信overlayを追加 | 公式より機能が未設定。対応済みとはしない | 有効化する場合のpin競合と送受信 |
| device権限 | mdevでinput `root:root 0640`、audio `root:audio 0660`。initはroot | Mの `config_setup` はudev / tmpfilesでLED権限を追加 | 実装差。udev規則をmdevへコピーしても動かない | 利用者UID/GID、必要な操作、LED / backlight書込み |
| 無線 | BRCMFMAC / HCIUARTとfirmware収録、BlueZ未選択 | PのGUI運用と異なる。AEをDへコピーしていない | 接続対応は未確認。firmwareの存在と区別 | 型番、SDIO ID、firmware filename、UART、規制国 |
| 電源異常 | local patchでsyncと通知、SysRq-U | M原版はGPIO/バックライト操作とSysRq-U。通常shutdownはコメントアウト | 意図した差。QEMUで通知とRO化を確認 | hold-up時間、sync完了、電断反復。通常poweroffは未導入 |
| rootfs / 更新 | SquashFS RO、`/data` ext4、署名bundle、A/B tryboot | Pの公開scriptだけでは同等のOS全体A/Bは確認できない | MSD/Linux独自設計。公式にないと断言しない | trybootとrollback、FAT、更新中電断、カード全交換 |

### resetの未解決事項

Mの [v5 overlay](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/37b42d9451495b5597dd7e50cab502da8028f9c2/modules/CardputerZero/cardputerzero-v5-overlay.dts) は `rest-gpios = <&m5ioe1 2 1>` を宣言する。生成DTにも残るが、宣言は制御実行の証拠ではない。[m5ioe1.c](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/37b42d9451495b5597dd7e50cab502da8028f9c2/modules/m5ioe1-1.0/m5ioe1.c) はresetの取得・駆動コードをコメントアウトし、特定のrevision値ならREADY registerを書く処理を持つ。公開Linux側だけからMCUの電源投入時処理や担当は確定できない。

PYG3はkeyboardとUSB hubで共有する。GPIO index 2と物理PYG3を混同せず、一方の初期化中に他方をresetしない設計を確認する。上流へのIssue・PRは作成していない。

## 誤解を避ける境界

- `PARTITION_WALK` はEEPROM bootloader向けで、CM0用A/B実装の根拠に使わない。trybootはRaspberry Pi文書で全モデル対応とされるが、CM0実機で確認済みではない。詳細は [firmware仕様](rpi-firmware-spec.md)。
- MのDRM driverが要求するheaderはKのソースと実際のビルドで確認する。ある6.12系URLの404だけで、6.12系列全体の不在を証明したとは扱わない。
- Dの16 M5 modulesは署名者・vermagic・aliasを読み取った。署名metadataの存在だけで全moduleの暗号検証・probe・実機動作を完了したとは書かない。
- DTBO合成は開発用imageのDTC 1.7.2で成功した。ホストDTC 1.6.1ではIMX219適用が失敗した。旧ツールの失敗と製品の不具合を区別し、失敗試行も [確認記録](../experiments/2026-11-02-hardware-artifact-audit.md) に残す。
