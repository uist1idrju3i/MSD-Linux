# raspi3bの既知boot診断

第4段の最初のE1/smokeで得た24行を分類した。元のphaseは全て`run`。[実験記録](../../../../../docs/experiments/2026-11-19-s04-fs-compare-v2-stage4.md)の失敗を成功へ書き換えない。raw logのSHA-256は`b679683dc85511b800b10625a94beba8880d2b1ebd597c2e5250c29e49636b5b`で、host試験の`fixtures/raspi3b-first-run.log.gz`に同じ内容を可逆圧縮して置いた。consoleの制御文字は削除しない。

`boot-diagnostics.json`には理由と発生元を記録した。QEMU 11.1.2、raspi3b、1 GiB、icount無効、Linux 6.18.59-v8、Raspberry Pi 3 Model Bの起動logと`SMOKE_PROFILE`がそろい、guestの最初の`msd.fscmp:`より前にある時だけ使う。`run`と`verify`の各`qemu-PHASE.log`が対象で、host logと通常測定は対象外。文面はtimestampだけを除いて全体一致で照合し、既知診断も最終error一覧に理由と出典付きで残す。別kernelやQEMUで文面が変わったら再確認する。

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

camera regulatorのEIOと原因未確定の補助UART errorを隠さないため、v2 smokeの使い捨てDTB写しだけで`/cam1_regulator`と`/soc/serial@7e215040`をdisabledにする。QEMUにはcameraもGPIO expanderもなく、このharnessでは補助UARTも使わない。PL011 console・mmc0・filesystem経路は維持する。各phaseのDTB・hashを保存し、共通launcherは従来どおりBluetoothだけを別の写しで無効にする。製品DTB・共通launcher・kernel configは変更しない。EIOや補助UART errorが再び出れば失敗する。

## 固定source

kernelはraspberrypi/linux commit `b3495ea401d709af0701a85babcba5e3d788a602`。

- [EFI](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/firmware/efi/fdtparams.c#L131)、[initramfs fallback](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/init/main.c#L1567)。
- [仮想GPIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpio-bcm-virt.c#L119)、[GPIO configとEIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpio-raspberrypi-exp.c#L55)。
- [補助UART](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/tty/serial/8250/8250_bcm2835aux.c#L168)、[probe結果](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/base/dd.c#L656)。
- [camera regulatorのGPIO取得](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/regulator/fixed.c#L320)、[gpiolibの設定失敗](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/gpio/gpiolib.c#L4746)。
- [LED](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/leds/leds-gpio.c#L189)、[SDIO](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/mmc/core/core.c#L2337)。
- [QEMU property tagのdefault処理](https://github.com/qemu/qemu/blob/v11.1.2/hw/misc/bcm2835_property.c#L420)、[libfdiskの再読込み](https://github.com/util-linux/util-linux/blob/v2.41.5/libfdisk/src/context.c#L863)。
