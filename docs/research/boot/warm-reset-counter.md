# warm resetをまたぐ非SD counter（調査・未決定）

[保存領域の索引](../storage/README.md) / [loop防止設計](../../design/boot-loop-prevention.md) / [initramfsの負担](initramfs-for-loop-prevention.md)

2026-11-17。fresh main `082c50e`を確認し、未mergeの先行調査`62e8e41`に積み重ねます。対象は**tryboot成功・commit後、既定slotのSD dataが壊れた場合**。短い間隔のreset・電源入切ではFATへ書かず、書くなら起動後に破損を確認して数秒待った後だけ、という利用者条件です。採用・mode・例外承認は未決定、製品変更・新実験・buildはありません。

【静的確認】は固定source、【推論】は条件付き案、【未確認】は実機等の証拠なし。【既測定】と【二次報告】は適用範囲を限定します。保持の事実は本書、条件付きのA→B→STOPと実行基盤は[root前policy比較](pre-root-loop-policy.md)、通知・待機・遅延FAT切替は[稼働後の調査](verity-delayed-failover.md)へ、問いごとに分けます。

## 1. 判定と固定版

| 対象 | 調査上の判定 |
|---|---|
| 現構成のまま保証付きRAM-only A→B→STOP | **不可**。予約・counter policy・root前gateがなく、CM0の保持保証も未確認 |
| ramoopsを診断用に有効化 | 既存kernel設定を利用しDT/config追加で可能な構成。CM0でのreset後回収は未確認 |
| initramfsなしのroot前counter | **kernel変更で構成する候補**。保持領域・原子更新・起動順・全fatal経路・WDT/表示の実装と実証が条件。製品として可能と実証したわけではない |
| 無FAT initramfs chooser | kernel内policyの一部を独立userspaceへ移せる候補。ただしRAM保持依存は同じ。initramfsだけではcounterにならない |
| PM_RSTS/trybootだけを汎用counterへ転用 | 公開仕様の保証なし。現driverが使うpartition/flagを独自counter扱いしない |

製品pinは[defconfig:31-44][DC]とBuildroot gitlink。kernel K=`b3495ea401d709af0701a85babcba5e3d788a602`（6.18.59）、Buildroot=`75f325ad84251ee9d903467f84d3683e3bcf3fd5`、[rpi-firmware.mk:8-18][BR]が選ぶfirmware=`063bcab6c8a90efb0d19f69d88cbbc7ec79cab68`。bootcode.bin、start_cd.elf/fixup_cd.datを使います。公式文書D=`c6a64966af136da21a1e55551c5a395cb6987fce`は調査用snapshotで、固定binaryの対応保証ではありません。

Kの[CM0 DTS:10-12][CM]はraspberrypi,0-compute-module / brcm,bcm2837。[公式legacy経路:3-11][LEG]はBCM2837を対象とし、Pi4/5 EEPROM経路とは別です。製品はSD直接SquashFS rootでdm table未実装（[設計:20](../../design/boot-loop-prevention.md)）。以下のdm-verity動作は予定のmapper導入後を検討するsource上の事実です。

## 2. DRAMは保持されるのか

【静的確認】固定[firmware README][FWR]はprecompiled binariesの配布です。bootcode/startの全書込み範囲・DRAM再初期化処理を公開sourceで追える状態ではありません。**CM0＋固定firmwareについて、各resetで任意の予約DRAMが必ず残る／全消去される、どちらの保証も今回確認できませんでした。**

一方でKの[ramoops overlay:10-23][OV]と[overlay README:4617-4629][OR]はrebootをまたぐcrash log保存を明示。既定は0x0b000000、64 KiB、record 16 KiB、console 0です。これは保持を利用する公式の入口ですが、当製品の全reset種別での保持証明ではありません。

| reset経路 | 固定sourceで確認できること | DRAM・flagの未確認部分 |
|---|---|---|
| 通常reboot、dm-verity restart | T:207-208,535-537は固定reason付きkernel_restart。R:288-299はnotifier→SHUTDOWN dump→machine_restart。W:101-138はpartition符号化後FULL_RESETを要求 | handler登録sourceはあるが実機dispatch・FW応答・再初期化範囲は未確認。FULL_RESETという定数名だけでDRAM全消去とは言えない |
| emergency_restart | R:93-98はEMERG dump→machine_emergency_restart。arm64は[generic実装:5-7][ER]でmachine_restart(NULL)を使う | 通常reboot notifierを通らず、tryboot mailboxの処理を期待できない |
| panic＋timeout | [panic.c:558-582][P]でtimeout後emergency_restart。panic dumpは別に行う | 保存backend登録前のpanicは記録できない |
| panic＋hardware WDT | timeout待機中でも稼働WDTがresetし得る。kernel_restartのcallbackではない | PM_RSTSの実値、firmwareの解釈、DRAM保持は別途確認が必要 |

T=[dm-verity-target.c][T]、R=[kernel/reboot.c][R]、W=[bcm2835_wdt.c][W]。**固定dm-verityのrestartはemergency_restartではありません。** Cは`dm-verity device corrupted`、Eは`dm-verity device has I/O error`というkernel_restart引数です。上表はsourceの接続であり、CM0で全linkが実行されたという観測ではありません。

上書きとの衝突も必要条件です。製品[config.txt:1-18][CF]はkernel8.img、gpu_mem=16、cut-down firmwareを選択。[公式kernel_address:38-44][KA]は64bit既定0x200000、[GPU memory:16-35][GM]はGPU用領域を説明します。kernel本体・展開作業域・DTB・firmware作業域・GPU carveoutを避ける必要があり、**Linuxのreserved-memoryはfirmwareの上書きを禁止する契約ではありません**。製品用addressは選定しません。

### 反例・他環境の記録

【既測定】[S21](../../experiments/2026-10-21-s21-qemu-sysctl-ramoops.md)は6.18.57-v8、QEMUで、Amendment 3のR1 5/5がreset後にrecordを回収。R0は5/5でrecordなし。runnerの早期終了等の失敗とAmendmentを保持しており、CM0/6.18.59の実証へ読み替えません。

【二次報告】[Pi issue #5063][I5063]には3Bでbuilt-in ramoopsが早期登録された報告、[#5298][I5298]にはPi4で成功・空record・bit化けの報告があります。後者にはEEPROMのSD電圧復旧resetがRAM保持へ影響した事例もあります。保持を当然とする見方への反例ですが、Pi4の修正をEEPROMのないCM0へ適用できる証拠ではありません。公式overlayの存在と、この失敗例の両方を踏まえて保持は未確認とします。

## 3. ramoops/pstoreでできることと不足

| 項目 | 静的確認・製品現値 |
|---|---|
| 設定 | [fragment:55-56][LF]はCONFIG_PSTORE=y、CONFIG_PSTORE_RAM=y。RAMOOPSという別の必須Kconfig名ではなくPSTORE_RAMがramoops driverを有効化（[Kconfig:68-82][PC]） |
| 保存build | PSTORE_COMPRESS=y、CONSOLE=y、PMSG=n、BLK=n、REED_SOLOMON_ENC8/DEC8=yを既存.configで確認。ただし最新mainの再build一致は未検証。PMSGを使う案は設定追加が必要 |
| 現在の予約 | config/cmdline/製品overlayにramoops予約指定・pstore回収daemonは見当たらない。[書込み台帳:69](../../design/write-policy.md)も予約と回収を実測済みとはしていない。CONFIG=yだけではbackendにならない |
| DT方式 | /reserved-memoryのcompatible=ramoops、reg、record/console等の非zero size。Kのoverlayを使う入口はあるが配置・全boot系の一致が必要。[binding:9-24,36-85][BIND] |
| cmdline方式 | ramoops.mem_address/mem_size/record_size/console_size等。mem_size既定0ならdummy deviceなし（[ram.c:917-937][RC]）。address指定だけでLinux allocatorから保護できると考えず、早期予約が別に必要（[ramoops.rst:123-140][RD]）。reserve_memは同address保証なしのbest effort |
| ECC/cache | ramoops.ecc=1は16 byte ECC（ram.c:961-965）、DTはecc-size。既定ECCなし。小さいbit損傷の対策で全消去・上書きは回復不能。mem_typeはwrite-combined既定、cached等へ変えるならatomic/cache/reset時の可視性を確認（RD:29-57） |
| 何を記録するか | max_reason既定2はPANIC/OOPS。通常kernel_restartのSHUTDOWN=4、emergencyのEMERG=3は既定対象外（[kmsg_dump.h:18-29][KH]、R:95,298）。CONSOLEは別frontendで記録できる構成。理由・backend・sizeごとの欠測を区別する |
| 回収 | mount -t pstore後の/sys/fs/pstore/dmesg-ramoops-N等（RD:148-153）。rootが読めればS00等で回収できるが、root前の障害には間に合わない。自動SD転記は行わない |

【静的確認】RD:51-52は内部dump counterがrebootでresetすると説明。[ram_core.c:528-567][CORE]も旧bufferを検査・保存／zapします。**pstoreのlog件数は永続boot counterではありません。** log欠損を正常と判定したり、専用counterを同じbufferへ直接書いてdriverと競合させたりしません。

【推論】counterは別の予約領域に、magic/schema/generation、試行mask、armed slot、reason、checksum、世代付き二重record等を持たせる案です。更新完了・可視性をreset前に保証する必要があり、単なるvolatile変数・health fileでは代用できません。原因不明resetは破損「疑い」であって、FAT writeを許す確認にはしません。

## 4. DRAM以外の状態

| 候補 | 固定source・公式仕様 | counterとしての限界 |
|---|---|---|
| PM_RSTS partition bit | W:24-35,101-138は32bit registerのbit0,2,4,6,8,10へ6bit値を格納。通常restartは0〜62、poweroff専用63はhalt。mask=0xfffffaaaでこのfieldを更新 | 6bitの汎用scratchではない。非数値dm-verity reasonでは0になる。次の通常restartも上書きする。firmwareがいつどのbitをclearするかの固定版CM0契約は未確認 |
| tryboot flag | [firmware driver:186-222,500-516][FW]はreboot notifierで文字列` tryboot`を検出しmailboxへbit0を送る。[公式one-shot][TB]はboot前clearを規定 | 1bitの一回試行であって試行済み2slot＋STOPの状態量ではない。reset/電源断ごとの保持方式はmodel依存 |
| mailbox reboot params | [header:80,98-99][FH]にNOTIFY_REBOOT、GET/SET_REBOOT_FLAGS。driverはtryboot bitだけを使用 | arbitrary counterの幅・保持・未使用bitの契約は確認できない。panicでsleep可能なmailbox処理を安全に呼べるとはしない |
| chosen/bootloader | [公式reference:1015-1052][CH]のpartition、pm_rsts、trybootはboot時snapshot、32bit big-endian。kernelからも参照可能 | /proc/device-treeはその写しで、書換え可能な不揮発counterではない。CM0固定版でのfield存在・値は未実測 |
| boot_count/arg1 | 同reference:1054-1060はPi5限定の8bit count/引数 | CM0の機能として扱わない |
| firmware WDT partition/rescue | [boot.adoc:242-269][WD]にkernel_watchdog_timeout/partition。EEPROMのBOOT_WATCHDOG_*等とは別 | CM0固定版対応は未確認。全4 fatal modeを覆う回数上限ではない。OTP、外部MCU/RTC等にも本製品用counterの契約は確認していない |

PM_RSTSは一回の別partition指定には使う経路があり、[autoboot:13-19][AB]はrebootの数値指定優先を記載します。ただしbitを直接再利用するとboot選択と衝突します。firmwareがclearしないと仮定して独自counterにする根拠にはしません。

## 5. 調査の境界

保持・cache・予約address・register契約は未確認です。条件付きの有限試行と欠損時STOPは[root前policy比較](pre-root-loop-policy.md)、commit後の破損通知と遅延writeは[稼働後の調査](verity-delayed-failover.md)を参照します。どちらも採用せず、QEMUの回収成功をCM0のfirmware保持の実証とはしません。

[DC]: ../../../configs/msd_cardputerzero_defconfig
[LF]: ../../../board/cardputerzero/linux.fragment
[CF]: ../../../board/cardputerzero/config.txt
[BR]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/rpi-firmware/rpi-firmware.mk#L8-L18
[FWR]: https://github.com/raspberrypi/firmware/blob/063bcab6c8a90efb0d19f69d88cbbc7ec79cab68/README.md
[CM]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts#L10-L12
[OV]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/overlays/ramoops-overlay.dts#L10-L23
[OR]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm/boot/dts/overlays/README#L4617-L4629
[T]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-verity-target.c
[R]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/kernel/reboot.c
[W]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/watchdog/bcm2835_wdt.c
[P]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/kernel/panic.c#L558-L582
[ER]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/include/asm-generic/emergency-restart.h#L5-L7
[KA]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/legacy_config_txt/boot.adoc#L38-L44
[GM]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/legacy_config_txt/memory.adoc#L16-L35
[LEG]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc#L3-L11
[PC]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/pstore/Kconfig#L37-L82
[RC]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/pstore/ram.c
[CORE]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/pstore/ram_core.c#L528-L567
[BIND]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/devicetree/bindings/reserved-memory/ramoops.yaml#L9-L85
[RD]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/ramoops.rst
[KH]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/include/linux/kmsg_dump.h#L18-L29
[FW]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/firmware/raspberrypi.c
[FH]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/include/soc/bcm2835/raspberrypi-firmware.h#L80-L99
[CH]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/configuration/reference.adoc#L1015-L1060
[TB]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L80-L98
[AB]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/autoboot.adoc#L13-L40
[WD]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L269
[I5063]: https://github.com/raspberrypi/linux/issues/5063
[I5298]: https://github.com/raspberrypi/linux/issues/5298
