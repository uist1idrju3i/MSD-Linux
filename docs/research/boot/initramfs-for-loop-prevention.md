# loop防止用initramfsの負担と代替案（調査・未決定）

[研究の配置](../document-map.md) / [保存領域の索引](../storage/README.md) / [loop防止設計][LP]

2026-11-17。fresh origin/main `082c50e36a1388acbd793277cc86472b2a905ec5`を基準に、直前の調査報告を保存します。**利用者はFATへの書込みを避けたい意向で、検討時間を希望しています。initramfs・状態保存方式は未決定です。** 採用・例外承認・Phase C計画変更はしません。新しい実験・buildもありません。

【実測】は既存実験、【再集計】は保存済みrawの読取り、【静的確認】はcode・一次資料、【推定】は仮定付き試算・設計上の比較、【未確認】は測定・実証なしを表します。QEMUの仮想秒、host wall、電源投入からの実機秒を区別します。

## 1. 現行がinitramfsを使わない理由

【静的確認】[fastboot-ideas:18][FI]には次の記録があります。

> initramfs 読込・展開と RAM 使用を削減
>
> 採用済み（`root=` 直接指定、cmdline_rootfs_a/b.txt）

条件は起動必須driverとrootfs driverのbuilt-in化、外部moduleのfirmware配布設計です。`git log -S initramfs / initrd`をdocs/・board/・configs/・RESEARCH.mdで検索し、`7270d88`では案・未検証、現在の表では採用済みであることを確認しました。**CM0で何秒削減したから不採用にした、という実測付き判断は確認できません。** [product-decisions][PD]にも独立した不採用決定の行は見当たりません。

現行は[cmdline A](../../../board/cardputerzero/cmdline_rootfs_a.txt):1／[B](../../../board/cardputerzero/cmdline_rootfs_b.txt):1でSDのSquashFSを直接root指定。[loop設計:20][LP]のとおり製品initramfs・dm tableは未実装です。理由の記録と、効果の実証は別です。

## 2. 保存済みの起動時間

| 区分・対象 | 値 | 根拠と限界 |
|---|---|---|
| 実測：SD直接root、6.18.59-v8の既存構成 | QEMU icount通常5回中央値：t_ready=1.644829秒、t_init=0.907秒 | [zram比較:19-42][ZR]。基準733d27e、計測用rootfs。最新mainそのものではない。readyはkernel開始→rcS完了で、firmware/LCD待ちを含まない |
| 実測：過去の直接root比較 | baseline ready=3.037890／24.327573秒、FTRACE無効=1.887120／22.944577秒（icount／TCG） | [測定記録:24-38][BM]。QEMU mode間の差は大きく実機秒へ換算不可 |
| 再集計：B3 clean、kernel→init | 通常1.532259秒、RAM 1.797014秒、差約0.265秒（各5回中央値） | [B3 archive][BA]のraw/formal/B-clean-{normal,ram}-boot0〜4/serial.log。研究kernel 6.18.59-v8-b3trace。小型chooserや実機の追加時間ではない |
| 再集計：B3 gzip cpio | 圧縮7,255,137 B（約6.92 MiB）、展開後cpio 16,538,580 B（約15.77 MiB） | archive内payload/initramfs.cpio.gz。RAMのunpack開始→initrd領域解放は約0.332秒。純粋な解凍時間とは限らない |
| 実測：B3 host wall | clean通常232.385秒、RAM 227.808秒（中央値） | [stage B:18,33-38][B]。RAMが約4.6秒短いが処理と終点が違う。initramfsで高速化した証拠ではない |
| 未確認：MSD/Linuxの実機 | 未測定 | [測定記録:11-22][BM]。M5のbare-metal splash約2.1秒、他機種Linuxの値を追加遅延へ流用しない |

通常boot0ではserial:1919が`Run /sbin/init`=1.528645秒、:1951がready=2.745645秒。RAM boot0では:745がunpack=0.747858秒、:1028がinitrd解放=1.079941秒、:1918が`Run /init`=1.797014秒です。上表の中央値は保存log5本ずつの再集計で、新しいbootではありません。

**B3は小型chooserではありませんが、製品rootfs丸ごとでもありません。** [生成code:96-129][FG]はBusyBox、専用/init、lib・usr/lib直下のlibrary群を収録します。OpenSSL等を含む大きめの研究用RAM環境です。[ram-init:23-31][RI]はmapperの指定blockと全範囲を読み、その後待機します。製品rootへswitch_rootせず、通常側のroot mount→readall→readyとは終点が違います。

## 3. 小型環境の遅延をどう見積もるか

【静的確認】[Pi公式仕様:63-85][PI]はboot partitionから追加fileを読み、kernelへ渡す方法を定義しています。ただし**CM0のFAT実効読込み速度は今回の資料から確定できません**。[既存調査:22][BM]もsize比例の実証なしとしています。

以下は【推定】の試算例です。速度の仮定は測定値・一次資料の保証値ではなく、**本機の所要時間予測ではありません**。

| 成分 | 仮定 | 算術上の追加時間 |
|---|---|---|
| firmwareのFAT読込み | 圧縮0.25〜2 MiB、実効2〜10 MiB/秒 | 約0.025〜1秒 |
| 解凍・cpio展開 | 展開後2〜6 MiB、処理20〜100 MiB/秒 | 約0.02〜0.3秒 |
| /init、device待ち、dm設定、mount、switch_root | 仮予算。長いdevice待ちは別 | 約0.02〜0.2秒 |
| 合計の仮予算 | 上記の範囲を丸める | おおむね0.1〜2秒 |

LCD初期化、状態writeのfsync、署名検証、SDの再試行は含みません。これらが支配的なら範囲を超えます。数百KB〜2MBは圧縮後の目標として考えられるだけで、英日LCD・dm設定を含む達成値ではありません。

## 4. 最小chooserに入れるもの（案の内訳）

【推定】最小chooserと、bundleを書直せる完全なrecovery環境は分けられます。STOPでPCによる再作成を案内するだけなら、network・更新tool一式は不要です。以下は採用・実装の決定ではありません。数値は特記しない限り非圧縮fileのbytesです。

| 内容 | 大きさの手掛かり・根拠 |
|---|---|
| /init、slot・状態判定、STOP、引継ぎscript | 未実装・未採寸。BusyBoxのsh、mount、file操作、switch_root、必要ならmodprobe/watchdogを使う案 |
| BusyBox | 【実測】通常動的870,848 B、全applet静的1,831,360 B、63 appletへ削減した動的版509,960 B。[BusyBox実験:63-67,109][BB]。削減＋静的の組合せは未測定 |
| 動的link用lib | 【保存物採寸】glibc 1,613,984 B、loader 198,152 B。B3 cpioにも含む。静的版なら別fileとしては不要だが、他toolの依存は別途必要。最新mainとの再build一致は未確認 |
| dm設定tool | dmsetup＋lib、または専用ioctl helper。B3収録libdevmapper=313,224 B。tool・依存一式の合計は未採寸。veritysetupをそのまま入れる案ではない |
| device・mountpoint | /dev/console、devtmpfs、proc、sysfs、/run、新root用directory。一時状態はRAM |
| LCDと英日表示 | panel/backlight/M5IOE1等のmodule・firmware、表示tool、必要字形のfont。前回の保存build採寸はpanel-mipi-dbi.ko.xz=5,320 B、LCD firmware=93 B。依存合計ではなく、main一致・対応binaryの公開保存は未確認 |
| 状態・設定・信頼情報 | schema、slot対応、初期状態の定義、root hash・salt・FEC情報。永続arm/STOPの正本は[現案:65-78][LP]ではp1で、cpio初期値で毎boot上書きしない |
| 署名用の情報 | 認証方式を採るなら公開鍵・証明書。秘密署名鍵は入れない。bundle復旧まで担当するときだけ検証tool等を追加 |

B3 cpioにはlibcrypto.so.3=5,347,008 B等も含まれます。このlibrary群を全て持込む必要はありません。最小環境の合計・圧縮率は未測定です。

## 5. 速度以外の負担

| 項目 | 静的確認と、推定・未確認の負担 |
|---|---|
| kernel設定 | [製品defconfig:31-33][DC]が採る[固定bcm2711_defconfig:36][KD]はBLK_DEV_INITRD=y。INITRD対応をゼロから追加する状態ではない。[usr/Kconfig:55-108][KC]のRD_*既定はgzip/bzip2/lzma/xz/lzo/lz4/zstd有効。保存buildでも確認したが最新mainの最終.config再生成は未実施。外付けcpioならkernel埋込みは必須でない |
| 圧縮方式 | [同Kconfig:135-215][KC]はgzipを均衡型、LZ4を速いが大きめ、XZを小さいが展開・memoryに不利、zstdを中間と説明。本機での優劣は未測定。SquashFS用設定とは別 |
| dm設定の責任 | initramfsがあるとdm-mod.createを使えないわけではなく、B3も併用。[dm-init.c:271-322][DM]はlate_initcall。本案はroot読取り前のarmのため設定をchooser後へ移す（[設計:66-68][LP]）。device待ち・table生成・失敗処理をuserspaceで保守する負担が増える |
| OpenSSL | initramfs/dmsetup自体に必須ではない。crc32cはveritysetupが拒否し、直接tableが必要（[rootfs設計:86-95][RD]）。bundle署名確認まで担当させる場合は別。[固定Buildrootのlvm2設定][LVM]にもdmsetupだけの導入optionがある |
| root hashの信頼 | 配布・認証は未確定。initramfs追加だけでは信頼起点にならず、kernel・cpio・設定の整合と認証が必要。crc32cに改ざん耐性はない（[rootfs設計:128-133,154][RD]）。現行更新公開鍵の既定pathは/usr/share/msd-update/update-key.pem（[msd-update:10][U]）で、壊れたrootの鍵に依存する復旧にはできない |
| A/B・容量 | boot-a/b各64 MiBへ対応kernelとcpioを配置する案。実使用量・配布payloadは増えるが、現行boot.vfatは固定64 MiBなので収まる限りfileのbyte数がその分増えるとは限らない（[genimage:11-25,52-61][G]） |
| Buildroot | 全rootfsをcpio化すると大きくなる。subset生成か別構成が必要。[固定Buildroot cpio設定:1-48][CP]にはdracutによる部分cpioもあるが、本製品向け設定は未作成。第二Buildroot buildは選択肢であって必須ではない |
| RAM | 圧縮file・展開file・buffer等の一時memory増。適切なswitch_rootで旧fileを解放できるが、残したdaemon等が保持し得る（[kernel説明:91-128][RAM]） |
| LCD・日本語 | DRM/fbconは有効でもroot前のLCD一式は未実証。VC4はmodule（[fragment:44-57][LF]）、保存buildのpanelもmodule。既定fontは欧文、rootfsのconsolefont一式は削除済み（[font調査:19-37][FONT]）。英日STOPは追加作業・描画未確認 |
| watchdog | 現行はS01開始。chooserで先に開始するなら引継ぎ・二重起動・STOP中の給餌が必要（[設計:18,83][LP]）。panic=0でも稼働WDTがresetすれば停止できない |
| security・license・debug | 早期parser/script/libと更新対象が増える。SBOM・対応source・font等のlicenseも対象。LCD firmwareは現行でもlicense不明（[package:9-13][PK]）。chooser自身の故障をroot故障と区別するserial診断が必要。実装・監査は未完了 |

## 6. FAT書込み／initramfsを避ける代替案（推論）

| 代替 | 得られるもの | 諦めるもの・条件 |
|---|---|---|
| trialのみ自動復帰、既定は停止・手動復旧 | initramfs・毎boot counterを避けやすい | 既定はpanic待機等とし、WDTによるresetも止める／開始しない方針が必要。既定の自動復旧・hang回復を失う。早期panicの英日LCDは別途未解決 |
| warm-reset保持RAMのmarker/counter | FAT writeなしでwarm reboot loopを制限する候補 | CM0の保持・予約・読取り時機の実証が必要。電断で失う。initramfsなしならkernel等のroot前処理が必要。ramoopsは確実なcounterではない |
| firmwareの一回partition指定／tryboot | SDを書かず別slotへ移る候補 | 単独では往復loop上限なし。dm-verity reasonは固定で、そのまま使えずpanic/WDTも別経路。PM_RSTSを空きcounter扱いする根拠はない |
| STOP時だけ一度保存 | 通常bootのFAT writeを減らせる | STOPへ到達する独立基盤が必要。毎回panic/resetでは保存まで到達できず単独対策にならない。panic中FAT writeも避ける |
| 小型chooser＋毎bootの手動選択／確認 | 自動counterを書かずreset後はmenu待機 | initramfsは残る。通常bootにも操作が必要で、無操作の自動復旧を失う |
| 状態をFAT以外へ置く | FATの更新を避ける | SD write自体は残る。専用領域の耐電断設計が必要。将来の暗号化dataでは解錠前判定との循環にも注意 |

根拠は[loop設計:30-57,83-95][LP]と[固定kernel・firmwareの調査](../storage/dm-verity-error-options.md)。CM0のRAM保持・partition切替・WDT停止は未確認です。boot/kernel/chooser自体が読めなければ同じSDだけで表示を保証できません。

**initramfsと毎boot FAT writeは別の選択です。** 小型initramfsの追加遅延は未測定で、独立した復旧環境を保守する負担はあります。trialのone-shot復帰と、既定slotの自動復旧・確実な停止を分けて比較します。どの案も選択せず、書込み例外も承認しません。表示・中断・書込み条件は[設計:78-95][LP]と[書込み規則](../../design/write-policy.md)のままです。

[LP]: ../../design/boot-loop-prevention.md
[FI]: ../tuning/fastboot-ideas.md
[PD]: ../../design/product-decisions.md
[ZR]: ../../experiments/2026-11-15-zram-builtin-vs-module.md
[BM]: measurements.md
[BA]: ../../experiments/2026-11-15-dm-verity-fec-stage-b/evidence.tar.gz
[B]: ../../experiments/2026-11-15-dm-verity-fec-stage-b.md
[FG]: ../../../board/cardputerzero/tools/bench/dm-verity-fec/followup.py
[RI]: ../../../board/cardputerzero/tools/bench/dm-verity-fec/ram-init.sh
[BB]: ../../experiments/2026-10-21-qemu-busybox.md
[DC]: ../../../configs/msd_cardputerzero_defconfig
[RD]: ../storage/rootfs-squashfs-verity-fec-design.md
[U]: ../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update
[G]: ../../../board/cardputerzero/genimage.cfg
[LF]: ../../../board/cardputerzero/linux.fragment
[FONT]: ../presentation/fonts.md
[PK]: ../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk
[PI]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/boot.adoc#L63-L85
[KD]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/arch/arm64/configs/bcm2711_defconfig#L36
[KC]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/usr/Kconfig
[DM]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-init.c#L271-L322
[CP]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/fs/cpio/Config.in#L1-L48
[LVM]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/lvm2/Config.in#L25-L32
[RAM]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/filesystems/ramfs-rootfs-initramfs.rst#L91-L128
