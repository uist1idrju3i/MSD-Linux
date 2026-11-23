# CM0向けSDIO firmware配送の最小化

- 状態: 計画。比較の結果は実行後に追記する
- 日付: 2026-11-23
- 基準: `922b245f9eb674d7ea27d508dca1d58fbda0328f`
- 関連: [kernel・firmwareの設定面](../research/component-options/kernel-firmware.md)

## 目的と採否の基準

候補1〜3を適用した現行CI artifactから、対象外の無線firmwareだけを削る。
採用条件は、保持集合の欠損を削除前に拒否すること、残すfileとsymlinkの不変、
rootfs通常file合計と同条件SquashFSの減少、前後のQEMU A/B全4 boot成功、
各bootのloadkeys終了0、moduleの名前・サイズ・依存・状態の一致である。
同じ入力のA/AはSquashFSのSHA-256一致を要求する。
容量と構築可否の単回比較なので性能の中央値は求めない。容量削減を起動時間の短縮とは扱わない。

## chipの資料と保持方針

[M5の製品資料](https://docs.m5stack.com/en/CardputerZero)は搭載moduleをRaspberry Pi CM0としている。
[CM0 datasheet Release 3、§2.1（印刷ページ4）](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)はCypress CYW43439を明記する。
datasheet PDFのSHA-256は`861c9d1849bf206cce79bfa1beaabe8f86b195356f8db8d534b58cb49e8cd28e`。
一方、固定firmwareにはCM0専用の43430/43436s名から43436sの実体へのaliasがある。
[Raspberry Piの配送commit](https://github.com/RPi-Distro/firmware-nonfree/commit/be2ca149fd609844a5d43b4dfa7d5ee56d9a7534)にも同じ対応がある。

datasheetとfirmware aliasが一致せず、対象実機のchip ID・revision・BT subversionも未取得なので、
単一familyには絞らない。利用者の承認に従いCYW43439、CM0専用43436sとそのfallbackを保持する。
両者が同一chipの別名だと確認したわけではない。chipを識別できないまま他board向けのfirmwareを流用する変更もしない。
board固有のCYW43439 fileが存在すれば優先して残すが、別boardのNVRAMから新しいCM0用fileは作らない。

## kernelが名前を作る規則

固定kernelはRaspberry Pi Linux `b3495ea401d709af0701a85babcba5e3d788a602`（6.18.59）。
以下はそのsourceから導いた規則で、実機で選択された名前の観測ではない。

| source | 名前の選択と保持への対応 |
|---|---|
| [sdio.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/sdio.c) | chip IDとrevision maskで基底名を選ぶ。43439は`brcmfmac43439-sdio`、43430 revision 1は`brcmfmac43430-sdio`。`.bin`、`.txt`、`.clm_blob`を区別する |
| [of.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/of.c) | `brcm,board-type`がなければroot compatibleの先頭をboard名にする。CM0 DTSは`raspberrypi,0-compute-module`。Wi-Fi compatible自体は汎用の`brcm,bcm4329-fmac` |
| [firmware.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/firmware.c) | 拡張子の前に`.`とboard名を挿入した候補を先に探し、汎用名へfallbackする。board固有のbin・txt・clm_blobも保持対象にする |
| [btbcm.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/bluetooth/btbcm.c) | UARTのsubversion表からhw名を得る。`0x2310`はBCM4343A2、`0x2209`はBCM43430A1、`0x410c`はBCM43430B0。`brcm/HW.BOARD.hcd`、`brcm/HW.hcd`、`brcm/BCM.BOARD.hcd`、`brcm/BCM.hcd`の順に探す |

CYW43439とBCM4343A2の対応は[Infineonの公開サポート記録](https://community.infineon.com/t5/AIROC-Wi-Fi-and-Wi-Fi-Bluetooth/CYW43439-LWB-Bluetooth-Signal-Strength-Issues/td-p/365369)でも確認した。
他moduleの記録なので、CardputerZeroのBT初期化成功の証拠にはしない。
実際のBT subversionが未取得であるため、43430A1/B0の汎用patchも保持する。

## 配送optionと代替手段

固定Buildrootは`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`、
firmwareはLibreELECの`6596d332eaadd63e2413e3937715a084f61c39e2`。
upstreamのfirmwareはデータfileで、configure等によるchip選択optionはない。
`Config.in`のconfig token全3件を次の表と機械照合する。

| option | 意味・既定値 | 固定版での扱い・採否と理由 |
|---|---|---|
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI` | firmware package。有効化の既定値なし | 維持。現行の供給元・版・許諾を変更しない |
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_BT` | BTの全hcd。有効化の既定値なし | 維持。chip単位の選択肢がなく、post-buildで絞る |
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI` | Wi-Fiのbrcmfmac/cyfmac一式。有効化の既定値なし | 維持。CM0専用aliasとその実体が必要 |

recipeは`brcm/*.hcd`・`synaptics/*.hcd`と`brcm/brcmfmac*`・`cypress/cyfmac*`をまとめてcopyする。
`rpi-firmware`はboot/GPU側であり、このSDIO配送の供給元ではない。
linux-firmwareへの切替は、CM0専用NVRAM・alias・BT patchの対応と許諾を別に確認する必要があるため見送る。
vendorを編集せず、external post-buildの保持集合とsymlink到達先を検査してから不要分を削る。
未知の別package用fileやlicenseは削除しない。firmware探索path等の実行時設定は変更しない。

## 条件と実行計画

比較元は[CI run 45151315876](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/45151315876)のartifact `14806469903`。
producer HEADは`99c89412ede4571955e72c73065c8ec74d7836ca`で、候補1〜3適用済み。
ZIPのSHA-256は`01b9950a0bac0cd848e619b843981f15a0da945d94527fc51f2a4625d64059f2`。
原本は読取り専用とし、SD・rootfsは使い捨ての写しを使う。新規full buildやccacheの比較ではない。
同じhost tool、sort、zstd level 22、block 131072、時刻0、root所有者でpackする。
観測hookは両側で同じものを使う。rootfs通常file合計はhook追加前、SquashFSはhook追加後のbytesである。
symlinkのbytesは通常file合計に加えない。

runnerは実行commit、入力・tool・script・serial除外一覧のhash、tool版、UUIDのrun_prefixを保存する。
planとCSVはtemplate列を使い、失敗後の再試行でも新しい空の出力先とUUIDを使う。
欠損した必須BT patchを使った負の対照では、他fileの削除前に拒否することを要求する。
各条件のA/Bを1回ずつ起動し、moduleはaddress・参照数を除いて比較し、生の行も保存する。

## 実機で確認する残件

- brcmfmacが報告するchip ID・revision、実際に選んだbin・NVRAM・clm_blobのfile名と成功/失敗log。
- btbcmが報告するchip ID・revision・HCI/LM subversion、実際に選んだhcdのfile名とpatch適用結果。
- CM0の製造版・board compatible、Wi-Fiの接続・再接続・国別規制、BTの接続。

QEMUには対象SDIO hardwareがない。QEMUのA/B成功やmodule一覧の一致はfirmware読込みの実機検証ではない。
LCD・keyboard・M5 I2C・firmware tryboot・実機SDの電源断耐性もこの比較の対象外である。
