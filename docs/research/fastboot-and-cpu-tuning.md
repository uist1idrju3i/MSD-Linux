# 高速起動記事とCortex-A53調整

## 調査範囲

確認基準日は2026年10月19日です。対象カーネルは本リポジトリが指定するRaspberry Pi Linux commit `234188315037848e5b07d65b85d38edc64095caa`、Buildrootはmainのgitlink commit `d6061d653d7fb215c2409c59e4bfad1b9d677215`です。外部ページは「出典と抜粋」に示したURLを取得して確認しました。推定は【推測】、第三者の実機情報は【二次】、確認できなかった値は【未確認】と記します。

本リポジトリの設計条件をこの文書の表では6観点に整理します。①短い起動時間、②CLIと対象周辺機能の維持、③M5公式ドライバーとカーネル互換性、④読み取り専用rootfsとA/B更新、⑤電源断耐性、⑥保守・再現可能なビルドと検証です。これは既存文書の条件を分類したもので、プロジェクトが正式に命名した「6本柱」ではありません。

## 「Linux boots in 1 second」記事

TechFeedの見出しは「Linuxを1秒で起動させる — たった1個のファイルで実現する最小構成システム」です。紹介ページは原著者をNick Thomas氏と記します。原文の見出しは「Boot Naked Linux」、日付欄は`2026-05-19 — 2026-06-18 c / linux`と表示されます。欄の意味は判別できません。TechFeedは原記事を2026年6月15日公開としています。記事本文は取得でき、ペイウォールはありません。原文には「Building a tiny Linux from scratch」という別記事の紹介がありますが、この実験用のリポジトリやスライドは本文から確認できません。

記事はhostのx86_64向けLinux `6.8.0-111-generic`をKVMで起動します。CPU型番・周波数は記載されません。コマンドは`-m 1G`、`-kernel vmlinuz`、gzip cpio形式の`-initrd`、`console=ttyS0`を渡します。静的リンクした単一の`/init`が実行され、QEMU仮想ATAディスク上のファイルも読みます。掲載ログでは`Run /init as init process`が0.805419秒、読み出し例が0.816634秒、電源停止ログが0.819849秒です。記事は「電源投入からプログラムとディスク読み出しまで1秒未満」と表現しますが、時刻はKVMゲスト内のカーネルログです。hostがカーネルとinitrdを用意した後の実行であり、実機の電源投入、VideoCore firmware、SD初期化を含む実測とは確認できません。

| 技法 | 記事での実施状況 | BCM2837とRPi firmwareへの適用 | origin/mainでの採用状態 | 期待効果【推測】・コスト・6観点へのリスク | 検証案 |
|---|---|---|---|---|---|
| ROM、bootloader、firmwareを飛ばす | KVMがカーネルを直接ロード。Pi実機のfirmware計測なし | RPiのVideoCore firmware段階を置き換えたり丸ごと省いたりはできません。選択可能なfirmware設定の範囲に限られます | `config.txt:17,19`は`start_cd.elf`と`fixup_cd.dat`を指定。ただしRPi公式文書はcut-down版の選択に`gpu_mem=16`を必要とするとし、現設定にはその行がありません。実機での選択結果は未確認 | ①に効き得るが、firmwareとの不整合は起動不能につながる。②③の初期化も変わり得る | firmwareログ、実機UART、冷起動の電源投入からloginまでを測る |
| 最小カーネル、カーネル設定 | hostの一般的な`vmlinuz`を使用。自前で最小化する案は任意の提案 | Pi用カーネルを置き換える話とは別。対応するrootfs・ドライバーを落とす変更は限定して評価 | `bcm2711_defconfig`と追加fragmentを使用。周辺機能用設定を含む | 小さくなる可能性はあるが、未使用判定を誤ると②③④を損なう。ビルド時間と保守負担が増える | `Image`、モジュール、rootfsサイズ、QEMU機能試験 |
| 圧縮 | initrdをgzipで作成。kernel圧縮方式の比較なし | firmwareが読み込む`kernel8.img`の圧縮と、Linuxが後段で展開するinitrd/rootfsは別 | `post-image.sh:15-21`で`Image`をgzip化して`kernel8.img`にする。rootfsはSquashFS | SD読出し量を減らせる一方、A53の展開時間が増える【推測】。⑤と起動時間の測定が必要 | `kernel8.img`サイズ、QEMU `-icount`、実機の読出し時間 |
| initramfs対直接root | 小さなgzip cpio initrdを使う。kernelはcpioをRAM上のinitramfsへ展開して`/init`を実行 | Pi firmwareからLinuxへinitramfsを渡す構成は可能だが、記事の仮想環境とfirmware時間は同一視できない | `cmdline_rootfs_a.txt:1`と`cmdline_rootfs_b.txt:1`はrootデバイスを直接指定し、initramfsなし | 小initramfsなら初期処理を集約できる可能性。現在のA/B・mount・更新経路を移すと④⑤にリスク | `initramfs`のサイズ、root選択ログ、A/B試験 |
| initの置き換え | 1ファイルの静的`/init`がPID 1。devtmpfsをmountして仮想ディスクを読む | 可能だが、CardputerZeroのサービスを丸ごと置換できるわけではない | `configs/msd_cardputerzero_defconfig:13,15`でBusyBox initとmdevを採用し、起動スクリプトで機能を開始 | 立ち上がりは短くなる可能性があるが、②③④⑤⑥に高い影響。記事の単一initをそのまま移植しない | 各サービスの依存・起動時間、ホストテスト、実機全機能試験 |
| デバイス探索・ドライバー | devtmpfsを使い、QEMUのATA diskを認識してから読む。Piのprobe時間を測っていない | Pi用のprobe停止・削減は可能でも、対象デバイスの機能を失うおそれ | カーネルはCM0向けDTSと周辺機能を含む。`initcall_debug`による実機内訳は未取得 | ①の改善候補だが、②③への回帰リスクが大きい | `initcall_debug`ログ、QEMU機能、実機UART |
| 非同期probe・非同期起動 | 記事本文から使用を確認できず | 対応ドライバー単位で評価する必要 | 採用状況は未監査。設定だけで全probeの並列化を保証しない | 待ち時間を重ねる可能性【推測】。依存順の誤りは②③④の起動失敗につながる | boot traceで依存とクリティカルパスを確認 |
| XIP、hibernate、snapshot boot | 記事本文から使用を確認できず | CM0の通常SD起動でXIPや休止状態復元を行う根拠なし | その採用を示す設定は確認できない | 対応ストレージ・firmware・RAM保存経路の追加コストが大きい。⑤に強い影響 | 対応条件の一次資料と実機試験が必要 |
| CPU周波数・時計 | 記事はKVM実行環境を指定するが、CPU型番・周波数・固定設定を報告しない | firmwareの設定範囲内で比較できるが、過電圧・overclockは別のリスク | `arm_boost=1`を指定。カーネルbase configはCPUFreqとondemand governorを有効にする | 高い周波数ならCPU-bound処理が短くなる可能性【推測】。熱・電力・安定性を損なうと⑤⑥に影響 | 周波数・温度・消費電力と起動区間を同時採取 |
| ストレージの読み出し | 1 KiB block×1,024のrandom disk imageをQEMU仮想ATA diskとして読む。SDカード測定なし | SD速度・firmware・カード内部の挙動は再現しない | rootfsと`/data`はSD上。記事の速度値を転用できない | 低レイテンシ媒体なら記事と近づく可能性はあるが未測定。⑤の耐久性も別評価 | 実カードでcold/warm boot、読出しと同期書込みを測定 |
| 実機手順 | UEFI boot用USBを作る説明はあるが、1秒の実機測定結果はなし | 対象機器はCM0ではない | 本リポジトリの実機測定なし | 記事のheadlineを性能目標の根拠にしない | 電源投入からUART、login、各機能readyの複数endpointを記録 |

## CM0のCPU機能と確認度

Arm Cortex-A53 TRM r0p4はA53をArmv8-A実装とし、Advanced SIMD/FPとArmv8 Cryptography Extensionsを「Optional」と記します。これはArmv8.0-A世代のA53を特定しますが、各SoCが暗号拡張を実装したかは別の確認が必要です。GCC 14.3.0のCPU一覧もA53を`V8A`として定義し、追加機能欄を`(CRC)`とします。これは`-mcpu=cortex-a53`がCrypto Extensionsを暗黙に有効化しないことを示します。

| 確認対象 | 確認結果 |
|---|---|
| Pi 3 Model BのAArch64 `Features` | 【二次】公開採取例は`fp asimd evtstrm crc32 cpuid`。`crc32`は存在し、`aes`、`pmull`、`sha1`、`sha2`は表示されません |
| Pi 3上のcrypto実装 | 【二次】別のcryptsetup調査も同じFeatures行を掲載し、AES CEではなく汎用AES driverのみと報告します |
| BCM2837搭載CM0/RP3A0の直接採取 | 【未確認】CM0で採取した`/proc/cpuinfo`または起動ログを取得できていません。Pi 3の記録をCM0の一次測定として扱いません |
| CRC32と暗号 | Pi 3 A53についてはCRC32命令あり、AES/SHA/PMULL暗号拡張なしを二次資料で確認。CM0も同じと推定する場合は【推測】であり、実機採取が必要 |

## 現行arm64 kernel設定と縮小候補

### base defconfigの実値

指定commitの`arch/arm64/configs/bcm2711_defconfig`では、`CONFIG_ARCH_BCM=y`、`CONFIG_ARCH_BCM2835=y`、`CONFIG_ARCH_BRCMSTB=y`、`CONFIG_NR_CPUS=4`、`CONFIG_HOTPLUG_CPU=y`、`CONFIG_ARM64_VA_BITS_39=y`、`CONFIG_NO_HZ=y`、`CONFIG_NUMA=y`、`CONFIG_NUMA_EMU=y`、`CONFIG_CPU_IDLE=y`、`CONFIG_CPU_FREQ=y`、`CONFIG_CPU_FREQ_DEFAULT_GOV_ONDEMAND=y`、`CONFIG_CMA=y`、`CONFIG_CMA_AREAS=7`が明記されています。`CONFIG_ARM64_4K_PAGES`や`HZ`、`SCHED_MC`、`SMT`の有効値はdefconfig本文にありません。Kconfigの既定値だけから、fragment適用後の生成済み`.config`を断定しません。CI生成物または同commitでの`olddefconfig`結果が必要です。

`VA_BITS=39`は4 KiB pageの39-bit virtual address設定で、48-bit設定よりページテーブル階層が浅くなり得ます。TLB miss時のwalkとページテーブル量への影響は【推測】であり、現機で計測していません。A53専用化で`NR_CPUS`を小さくする変更も、4コア構成を超える試験対象との互換性に注意します。`NO_HZ=y`は起動時に不要な周期tickを減らす設定ではありません。CPUFreqの初期governorはondemand、CPU idleも有効です。起動中の実クロック遷移は実機ログで確認していません。

| Kconfig記号（指定commitの`arch/arm64/Kconfig`） | A53/Armv8.0との関係 | 縮小時の判断 |
|---|---|---|
| `ARM64_LSE_ATOMICS`、`ARM64_USE_LSE_ATOMICS` | LSE atomicsはArmv8.1-A以降の機能でA53にはない | A53のみなら無効化候補。ただしgeneric kernelのalternativesとLL/SC fallbackを壊さないこと |
| `ARM64_HW_AFDBM`、`ARM64_PAN`、`ARM64_RAS_EXTN`、`ARM64_CNP` | A53で利用できる機能としては確認できない | 実際の`.config`とCPU feature検出を確認してから比較 |
| `ARM64_PTR_AUTH`、`ARM64_BTI`、`ARM64_E0PD`、`ARM64_AMU_EXTN`、`ARM64_TLB_RANGE` | A53のArmv8.0実装にはない後続拡張 | 無効化でユーザーABIや他SoCの保護機能を落とさないか確認 |
| `ARM64_MTE`、`ARM64_SVE`、`ARM64_SME`、`ARM64_EPAN`、`ARM64_POE`、`ARM64_GCS` | A53非対応の後続拡張 | A53専用kernelなら候補だが、configが未生成のため削減量は未測定 |
| `ARM64_4K_PAGES`、`ARM64_VA_BITS_39` | base defconfigは39-bitを明示。4 KiBは明示なし | 4 KiBは一般に最小ページテーブル量を得やすい。別page sizeとのQEMU/実機比較なし |
| `NUMA`、`NUMA_EMU`、`HOTPLUG_CPU`、`CPU_IDLE` | Pi 3/CM0は4コア単一SoC。baseでは上記が有効 | NUMA/NUMA_EMUは縮小候補。CPU hotplugとidleは保守・電力・熱への影響を測るまで維持 |
| `SCHED_MC`、`SMT`、`HZ` | base defconfigだけでは有効状態を確定できない | SMT無効化等を断定せず、生成configを取得して計測 |
| `ARCH_BRCMSTB`等の他platform | base defconfigはBCM2835に加えて`BRCMSTB`等を有効にする | platform削減はA53専用化候補だが、全周辺機能・外部DTS対応を先に棚卸し |

### errataとCPU固有workaround

同commitのKconfigにあるA53対象は`ARM64_ERRATUM_826319`、`827319`、`824069`、`819472`、`845719`、`843419`です。定義は各A53のaffected revisionを記し、多くは`default y`です。該当リビジョンに対するworkaroundを残すべきです。`ARM64_ERRATUM_843419`のhelpはリンカーに`--fix-cortex-a53-843419`を渡すと明記します。GCCの`-mfix-cortex-a53-835769`および`-mfix-cortex-a53-843419`の存在は確認しましたが、Bootlin配布コンパイラでの既定値と生成コマンドラインは未確認です。両workaroundのサイズ・実行コストも本リポジトリでは測っていません。

他CPU用のerrataはKconfigに共存します。A53以外の定義は`832075`、`834220`、`1742098`、`1024718`、`1418040`、`1165522`、`1319367`、`1530923`、`2441007`、`1286807`、`1463225`、`1542419`、`1508412`、`2051678`、`2077057`、`2658417`、`2119858`、`2139208`、`2054223`、`2067961`、`2253138`、`2224489`、`2441009`、`2064142`、`2038923`、`1902691`、`2457168`、`2645198`、`3821522`、`2966298`、`3117295`、`3194386`、`4193714`、`4118414`です。Kconfigの説明はA57/A72/A55/A76/A77/A510/A710/A715/A520/A725/C1-Pro/Neoverse等を対象とします。Caviumの`CAVIUM_ERRATUM_22375`、`23144`、`23154`、`27456`、`30115`とQualcomm Falkorの`QCOM_FALKOR_ERRATUM_1003`、`1009`、`E1041`も別CPU向けです。A53専用イメージで他SoC対応を外す場合に限り削減候補になります。Pi 4/5を含む共通kernelから無条件に外す提案ではありません。

## Buildroot、compiler、crypto

現在のdefconfigは`BR2_aarch64=y`、`BR2_cortex_a53=y`、外部Bootlin AArch64 glibc stable toolchainを指定します。Buildroot mainの選択はBootlin `stable-2025.08-1`で、GCCは14.3.0です。Buildrootの`BR2_cortex_a53`はtarget CPU名を`cortex-a53`にし、wrapperは呼出し側が`-march`、`-mtune`、`-mcpu`を指定していない時に`-mcpu=cortex-a53`を足します。GCC 14.3.0のcore定義は`V8A, (CRC)`です。したがってCRCは有効になりますが、`CRYPTO`は付加されません。

glibc 2.44のAArch64 multiarch `memcpy`はIFUNCで汎用・ThunderX・A64FX・SVEなどを選ぶ実装を持ちます。確認した実装一覧にCortex-A53専用版はありません。IFUNC最適化が起動初期の各プロセスに与える影響は本リポジトリでは測っていません。

Linux arm64にはCRC32、AES CE、SHA2 CEなどの命令拡張向け実装があります。Kconfigの説明はAES CEを「ARMv8 Crypto Extensions」使用とします。AES CE glueの初期化は`module_cpu_feature_match(AES, ...)`を通り、CPU featureがない場合にdriverを登録しません。これらの命令をA53で無条件実行してよいことを意味せず、kernelのCPU capability検出とdriver登録が前提です。Pi 3でcrypto HWCAPがない例ではCE実装を選べず、汎用実装に留まると考えられます【二次】。`zlib`、`zstd`、`xz`等のユーザー空間ライブラリがどの最適化を有効にするかは各Buildroot packageの実buildを確認する必要があり、現在の実行時dispatch状態は【未確認】です。

| 対象 | 現状と候補 |
|---|---|
| Buildroot最適化/LTO | 現defconfigに`BR2_ENABLE_LTO`の指定なし。`-Os`、LTO、strip設定の最終値はBuildroot生成configを確認する。GCCのLTOはビルド時間と外部toolchainのplugin整合性が必要で、効果は未測定 |
| `-mfix-cortex-a53-835769` | GCC 14.3 manualはmemory命令と64-bit multiply-accumulate命令の間へのNOP挿入と説明。Bootlin compilerでの既定値とBuildrootが渡す最終flagは【未確認】。A53向けなので削除を先行しない |
| `-mfix-cortex-a53-843419` | GCC manualはlink時に対応linker flagを渡すと説明。kernel KconfigのA53 workaroundは`default y`。機械語サイズと時間差は未測定 |
| glibc IFUNC | 2.44 AArch64に複数のmultiarch実装。ただしA53専用`memcpy` variantなし |
| kernel CRC32/AES/SHA | ISA拡張を使う実装と汎用実装がある。Pi 3 cpuinfoはCRC32あり、Crypto CEのfeatureなし。CM0上の選択driverは未採取 |

## CM0向けの追加候補

RPi firmwareはVideoCore firmwareを起動し、`start_file`と`fixup_file`はGPUへ渡すfirmwareの対です。公式設定資料は`start*cd.elf`/`fixup*cd.dat`について、cut-down版の有効化は`gpu_mem=16`によると説明し、codec、3D、debug loggingを制限するとしています。現`config.txt`は`start_cd.elf`と`fixup_cd.dat`を指定しますが`gpu_mem=16`を指定していません。この設定が対象firmwareで実際に有効かは本リポジトリでは試していません。変更前に実機起動ログとfirmware実体を確認する項目です。

| 候補 | origin/mainの状態 | 期待効果【推測】 | コスト・6観点の主なリスク | 優先度と検証 |
|---|---|---|---|---|
| 実機起動の区間計測を先行 | 未実施 | 遅い段階を識別し誤最適化を防ぐ | UART配線と再現手順。⑥に必要 | P0。cold bootを複数回測り、電源投入・kernel entry・login・周辺機能readyを分ける |
| `initcall_debug`でprobe内訳を取得 | 未確認 | 起動時間を使うprobe/driverを絞れる | ログ量増加。②③を維持した削減が必要 | P1。既存機能を落とさず、まず実機ログとboot trace |
| A53以外のISA設定を外す | generic `bcm2711_defconfig`を使用 | kernelとalternativesの縮小【推測】 | 他Pi SoC互換、⑥の保守性に影響 | P1。生成`.config`とsize差、QEMU `-icount`、全周辺機能試験 |
| NUMA/NUMA_EMUを無効化 | base defconfigで有効 | 単一SoCでは不要コード縮小【推測】 | page allocation、Pi共通kernel互換に影響 | P1。config差分、Image/vmlinux、boot測定 |
| platformとDTSをCM0専用に縮小 | `config.txt`はCM0 DTB選択。BuildrootはCM0とPi 3BのDTSを指定 | build成果物や初期選択を減らす可能性 | ②③とQEMU/Pi 3試験を損なう | P2。DTS別成果物サイズ。CM0実機で全I/O試験 |
| CPUFreq governorと`arm_boost`比較 | firmwareに`arm_boost=1`、base configはondemand | 起動CPU-bound処理の短縮可能性 | 温度・電力・安定性、⑤ | P2。固定条件、温度とクロックを記録した実機比較 |
| `CPU_IDLE`比較 | base defconfigで有効 | wake/idle遷移の影響を切り分ける | 消費電力・熱と実時間への影響 | P2。QEMUでなく実機で測る |
| `gpu_mem=16`とcut-down firmware | 現configは`start_cd.elf`指定、`gpu_mem=16`なし | system RAMを増やし、cut-down版を選ぶ可能性 | codec/3D/debug、初期framebuffer、②③に影響 | P2。仕様照合後にだけ実機比較。保証なしで断定しない |
| `CMA`と`gpu_mem`の調整 | base defconfigは`CMA=y`、7領域。gpu split値はconfig.txtにない | 大きい連続メモリ領域やOS側RAMを調整 | display/codec/driver割当、②③に影響 | P3。DMA/CMA利用状況と表示を測定 |
| `force_turbo`、`initial_turbo`、overclock | 指定なし | 高い周波数でCPU処理を短縮する可能性 | 熱、電力、周波数安定性、firmware条件。⑤⑥のリスクが高い | P4。採用を推奨しない。許容範囲と保証条件を公式資料で確認 |

`arm_freq`、`core_freq`、`sdram_freq`、`over_voltage`の許容値や保証への影響は、Compute Module 0の実装・基板・firmware版まで対応する公式条件を確認できていません【未確認】。Overclockや過電圧は安定性と電力のリスクがあるため推奨しません。`force_turbo`と`initial_turbo`についても、現設定に採用済みとは扱いません。

カーネルの未使用ライブラリコードを削ることによる起動時間短縮は未測定です。起動時間の優先調査は、`initcall_debug`やboot traceで実際に走るprobe、initcall、root mount、サービス開始を特定することです。単なる`vmlinux`サイズ減少を起動時間改善と同一視しません。

## 出典と抜粋

| 出典 | 確認版・抜粋 | 確度 |
|---|---|---|
| [TechFeed紹介](https://techfeed.io/entries/6a30698b931f6b51a25b8f57) | 2026-06-16取得。「Linuxを1秒で起動させる」「Nick Thomas」 | 【二次】見出し・紹介者情報 |
| [原著者のBoot Naked Linux](https://nick.zoic.org/art/boot-naked-linux/) | Linux `6.8.0-111-generic`。ログ抜粋「Run /init as init process」「0.805419」 | 【二次】記事本文と実験ログ。実機電源投入の測定ではない |
| [Raspberry Pi 3 AArch64 cpuinfo](https://gist.github.com/Terminus-IMRC/8b4b0e666222c04623034917e0572ae6) | 公開採取例。「Features : fp asimd evtstrm crc32 cpuid」 | 【二次】対象はPi 3 Model B |
| [Pi 3 cryptsetup調査](https://artemis.sh/2025/10/03/pi3-cryptsetup-benchmarks.html) | 2025-10-03。「The raspberry pi 3 doesn’t have the hardware crypto extensions」および同じFeatures行 | 【二次】作者の機器での観測 |
| [Arm Cortex-A53 TRM r0p4](https://developer.arm.com/documentation/ddi0500/latest/BABHJJBC) | 「The Cortex-A53 processor implements the Armv8-A architecture」「Optional Armv8 Cryptography Extensions」 | 【一次】Arm製品資料 |
| [GCC 14.3 AArch64 CPU定義](https://github.com/gcc-mirror/gcc/blob/releases/gcc-14.3.0/gcc/config/aarch64/aarch64-cores.def#L55-L59) | 「`cortex-a53 ... V8A, (CRC)`」 | 【一次】GCC 14.3.0 |
| [GCC 14.3 AArch64 options](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/AArch64-Options.html) | 「inserting a NOP instruction between memory instructions and 64-bit integer multiply-accumulate instructions」「made at link time」 | 【一次】GCC 14.3.0。Bootlin binaryの既定値は未確認 |
| [Buildroot ARM target mapping](https://github.com/buildroot/buildroot/blob/d6061d653d7fb215c2409c59e4bfad1b9d677215/arch/Config.in.arm)・[toolchain wrapper](https://github.com/buildroot/buildroot/blob/d6061d653d7fb215c2409c59e4bfad1b9d677215/toolchain/toolchain-wrapper.c#L388-L405) | wrapperの抜粋「`-march/mtune/mcpu`」および「`-mcpu=`」 | 【一次】Buildroot gitlink commit |
| [Bootlin AArch64 toolchains](https://toolchains.bootlin.com/releases_aarch64.html) | `aarch64--glibc--stable-2025.08-1`の列に「GCC 14.3.0」「glibc 2.41」 | 【一次】本リポジトリが選択するexternal toolchain |
| [Raspberry Pi Linux `bcm2711_defconfig`](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig) | 「`CONFIG_NR_CPUS=4`」「`CONFIG_ARM64_VA_BITS_39=y`」「`CONFIG_CPU_FREQ_DEFAULT_GOV_ONDEMAND=y`」 | 【一次】kernel commit |
| [Raspberry Pi Linux arm64 Kconfig](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Kconfig#L494-L682) | A53 errataの説明と`843419`のリンカーworkaround | 【一次】kernel commit |
| [Raspberry Pi Linux arm64 Kconfig feature options](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/Kconfig#L1927-L2340) | `ARM64_LSE_ATOMICS`、`ARM64_SVE`等の定義 | 【一次】kernel commit |
| [Raspberry Pi Linux arm64 crypto Kconfig](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/crypto/Kconfig) | AES driver説明。「ARMv8 Crypto Extensions」 | 【一次】kernel commit |
| [Raspberry Pi Linux AES CE runtime registration](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/crypto/aes-ce-glue.c) | 「`module_cpu_feature_match(AES, aes_mod_init)`」 | 【一次】kernel commit |
| [Raspberry Pi firmware config reference](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/reference.adoc) | 「The only way to enable the cut-down firmware is to specify `gpu_mem=16`」 | 【一次】RPi文書commit |
| [本リポジトリのBuildroot defconfig](https://github.com/uist1idrju3i/MSD-Linux/blob/379d8f05783c62f2d8a7877787a60e8de6d67533/configs/msd_cardputerzero_defconfig)・[firmware設定](https://github.com/uist1idrju3i/MSD-Linux/blob/379d8f05783c62f2d8a7877787a60e8de6d67533/board/cardputerzero/config.txt) | `BR2_cortex_a53=y`、`arm_boost=1`、`start_file=start_cd.elf` | 【一次】origin/main |
| [glibc 2.44 AArch64 memcpy IFUNC](https://github.com/bminor/glibc/blob/glibc-2.44/sysdeps/aarch64/multiarch/memcpy.c)・[閲覧用ソース](https://codebrowser.dev/glibc/glibc/sysdeps/aarch64/multiarch/memcpy.c.html) | 「Multiple versions of memcpy. AARCH64 version.」とgeneric/ThunderX/A64FX/SVE実装一覧。A53専用variantなし | 【一次】glibcソース |
