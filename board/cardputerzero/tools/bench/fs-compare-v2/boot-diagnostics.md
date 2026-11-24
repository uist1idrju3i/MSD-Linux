# raspi3bの既知boot診断

第4段の最初のE1/smoke（QEMU 11.1.2、Linux 6.18.59-v8）で得た24行を分類した。元のphaseは全て`run`。[実験記録](../../../../../docs/experiments/2026-11-19-s04-fs-compare-v2-stage4.md)の失敗を成功へ書き換えない。raw logのSHA-256は`b679683dc85511b800b10625a94beba8880d2b1ebd597c2e5250c29e49636b5b`で、host試験の`fixtures/raspi3b-first-run.log.gz`に同じ内容を可逆圧縮して置いた。consoleの制御文字は削除しない。

## 現在の適用条件

`boot-diagnostics.json`には理由と発生元を記録する。現在の固定条件はQEMU 11.1.3、raspi3b、1 GiB、icount無効、Linux 6.18.64-v8、Raspberry Pi 3 Model Bの起動logと`SMOKE_PROFILE`がそろうこと。`run`と`verify`の各`qemu-PHASE.log`が対象で、host logと通常測定は対象外である。一般の既知診断はguestの最初の`msd.fscmp:`より前だけ許容する。

`wifi-sdio`だけは、同じ固定条件を満たすphase全体で1回だけ許容する。timestampを除いた文面が`mmc1: Failed to initialize a non-removable card`と完全一致する場合に限る。DTの`mmc1`はQEMUにdeviceがないWi-Fi SDIO hostで、imageのSD hostは`mmc0`である。2回目はfatalとし、runとverifyは別々に数える。`mmc0`、別のMMC error、未知のmachineや版には広げない。[試行06の調査・再判定](../../../../../docs/experiments/2026-11-24-s04-fs-compare-v2-wifi-sdio.md)に根拠を記録した。

許容した診断も最終error一覧に元の文面・行番号・理由・出典を残す。別kernelやQEMUで文面が変わったら再確認する。

## 元logの全24行

| 行番号 | 数 | 発生元と判断 |
|---|---:|---|
| 14 | 1 | EFIのFDT検査。UEFIなしの直接DT起動であり、後にSquashFSと`/sbin/init`へ到達する |
| 175、214、215 | 3 | firmware仮想GPIO bufferの設定・mappingとdriver coreのprobe結果。QEMUのproperty modelには対応tagがなく、測定用block deviceではない |
| 216–223、289、290 | 10 | firmware GPIO expanderのconfig取得。要求した80–87が変更されず返る場合の診断。GPIO番号と値の対応も照合する |
| 291–293 | 3 | camera regulatorのGPIO取得失敗。expanderから`-EIO`が伝播し、gpiolib、driver helper、driver coreが出力する。**fatalのまま** |
| 295、296 | 2 | 補助8250 UARTの登録失敗とdriver core。測定consoleは別のPL011 `ttyAMA1`で、このUARTは測定対象外。登録失敗の内部の分岐までは特定していないため、**fatalのまま** |
| 304 | 1 | initramfsの`/init`がなく、kernelが`prepare_namespace()`へ進む通常root mount経路。後に`/sbin/init`を実行する |
| 322、324 | 2 | `msd-data-grow`がpartition 4/7を拡張した直後のlibfdisk `BLKRRPART`のEBUSY。後続のpartx更新・resize2fs・setup同期を伴う |
| 330 | 1 | firmware GPIOに依存するactivity LEDのdeferred probe。測定対象のblock deviceではない |
| 331 | 1 | alias `mmc1`はWi-Fi SDIOでcardは未実装。imageのSD hostは`mmc0`。`mmc0`へ対象を広げない |

partition再読込みの例外は、既知の拡張メッセージに続く**次のuserspace行**で、同じlog内にsetup同期完了がある場合だけ認める。間にkernel行が割り込むことは許すが、そのkernel診断の判定は変えない。errno違い、番号違い、setup未完了はfatalとする。panic、Oops、BUG、guest error、EIO、ENOSPCは既知診断へ分類しない。T1/T6の明示的な破損区間に関する既存規則も変更しない。

固定条件を満たすphase全体で、行の途中のkernel timestampから始まる断片を分け、続くuserspace行を保留中の断片へ連結する。markerの種類によらず同じ分離器を使う。kernel断片と連結したuserspace行はそれぞれ既存の規則で判定し、一般のboot許容区間は延ばさない。guest markerで保留を打ち切る。log本体は変更せず、診断の行番号は断片が始まった物理行を指す。混在した行全体を許可するpatternは追加しない。

再診断03の316–317行にあった`mmc1: Timeout waiting for hardware interrupt.`は、分離後は既存のfatal patternに一致しない。このためcontrollerを追加で無効化していない。この判定はtimeoutの原因や実機での安全性を確認したことを意味しない。

camera regulatorのEIOと原因未確定の補助UART errorを隠さないため、v2 smokeの使い捨てDTB写しだけで`/cam1_regulator`と`/soc/serial@7e215040`をdisabledにする。QEMUにはcameraもGPIO expanderもなく、このharnessでは補助UARTも使わない。PL011 console・mmc0・filesystem経路は維持する。各phaseのDTB・hashを保存し、共通launcherは従来どおりBluetoothだけを別の写しで無効にする。製品DTB・共通launcher・kernel configは変更しない。EIOや補助UART errorが再び出れば失敗する。

## 現在の固定source

kernelはraspberrypi/linux commit `a40f735325391b1705161b07f36ed45e1bf04521`、QEMUは11.1.3である。

- [mmc1のaliasとWi-Fi node](https://github.com/raspberrypi/linux/blob/a40f735325391b1705161b07f36ed45e1bf04521/arch/arm/boot/dts/broadcom/bcm2710-rpi-3-b.dts)、[non-removableのscan](https://github.com/raspberrypi/linux/blob/a40f735325391b1705161b07f36ed45e1bf04521/drivers/mmc/core/core.c#L2265)。
- [QEMUのSD card作成](https://github.com/qemu/qemu/blob/v11.1.3/hw/arm/raspi.c#L279)、[SD busの切替え](https://github.com/qemu/qemu/blob/v11.1.3/hw/gpio/bcm2835_gpio.c#L210)。

## 初回logのsource

以下は初回の24行を調べた時のsourceで、現在の適用条件とは区別する。kernelはraspberrypi/linux commit `b3495ea401d709af0701a85babcba5e3d788a602`。

- [EFI](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/firmware/efi/fdtparams.c#L131)、[initramfs fallback](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/init/main.c#L1567)。
- [仮想GPIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpio-bcm-virt.c#L119)、[GPIO configとEIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpio-raspberrypi-exp.c#L55)。
- [補助UART](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/tty/serial/8250/8250_bcm2835aux.c#L168)、[probe結果](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/base/dd.c#L656)。
- [camera regulatorのGPIO取得](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/regulator/fixed.c#L320)、[gpiolibの設定失敗](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpiolib.c#L4746)。
- [LED](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/leds/leds-gpio.c#L189)、[SDIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/mmc/core/core.c#L2337)。
- [QEMU property tagのdefault処理](https://github.com/qemu/qemu/blob/v11.1.2/hw/misc/bcm2835_property.c#L420)、[libfdiskの再読込み](https://github.com/util-linux/util-linux/blob/v2.41.5/libfdisk/src/context.c#L863)。
