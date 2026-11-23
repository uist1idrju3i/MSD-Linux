# Kernel・DeviceTree・firmwareの設定面

[調査の入口](../../../RESEARCH.md)へ戻る。

## 対象と証拠

対象kernelはRaspberry Pi Linuxの固定commit `b3495ea401d709af0701a85babcba5e3d788a602`。版は6.18.59で、単なるupstream Linux 6.18のソースとは区別する。[CI run 41486595026](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41486595026)の[生成物](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41486595026/artifacts/13163313182)から最終`.config`を読み、[全symbolと値](kernel-config.csv)へ展開した。MSD/Linuxのcompile要求はdefconfig、fragment、packageレシピにも分散する。

このCSVは最終設定の記録であり、固定ソースに存在する全Kconfig symbolの一覧でも、全ドライバーの実機動作記録でもない。追加候補の依存条件は、固定ソースの該当Kconfigで確認する。`=m`はmoduleとしての選択で、実行中に読み込まれていることを意味しない。

## 変更できる層と確認方法

| 層 | 一次資料・設定の置き場 | 変更時に確認すること |
|---|---|---|
| Kconfig | `arch/arm64/configs/bcm2711_defconfig`、`board/cardputerzero/linux.fragment`、依存先のKconfig、生成した`.config` | 指定の反映、依存解決、未反映項目、built-inとmodule、最終設定の差分 |
| compile・link | kernelのMakefile、`KCFLAGS`、`KCPPFLAGS`、`LDFLAGS_vmlinux`、toolchain、packageのMake引数 | 通常ユーザー空間のCFLAGSと混同しない。LTO・sanitizer・CFI等はcompilerとarchの条件も必要 |
| 起動引数 | `board/cardputerzero/cmdline_rootfs_a.txt`と`cmdline_rootfs_b.txt`、最終boot領域、`/proc/cmdline` | boot A/Bで同じ意図になるか。指定しても対応CONFIGや機器がなければ作用しない |
| module引数 | 固定ソースの`module_param*`、生成moduleの`modinfo -p`、実行中の`/sys/module/*/parameters` | built-inとloadableで渡し方が異なる。書込み可能なparameterだけを動的変更できる |
| sysctl | 固定ソースのsysctl登録と`Documentation/admin-guide/sysctl`、実行中の`/proc/sys` | CONFIG・起動・namespaceで項目と値が変わる。文書中の既定値を実測に読み替えない |
| DeviceTree | DTS、overlay、生成DTB/DTBO、実行中のDT | GPIO・interrupt・clock・regulator・compatibleの対応と、driverがpropertyを消費するか |
| firmware | Raspberry Piの`config.txt`、boot firmware、SDIO firmware/NVRAM、M5配布物 | kernelとは別の版・許諾・設定経路。QEMUでGPU・実チップの処理を確認したとしない |

kernelの起動引数は、組込みmoduleなら`module.parameter=value`、loadable moduleならmodprobeへの引数でも設定できる。未認識の引数にはinitへ渡されるものもあり、起動に成功しただけではkernelが消費した証明にならない。

## 生成物で確認した値と再検討候補

| 分野 | 最終設定の記録 | 効果・費用・未検証の候補 |
|---|---|---|
| preemption・時刻 | `CONFIG_PREEMPT_RT=y`、`CONFIG_HZ=250` | latencyとthroughput、CPU・電力・保守費用の比較が必要。一般的な低遅延への期待と、この機器の実測を区別する |
| CPU・page | `CONFIG_NR_CPUS=4`、`CONFIG_ARM64_4K_PAGES=y` | A53と512 MiBの前提で評価する。別arch向けのoptionを有効化候補へ混ぜない |
| cpufreq | default governorは`ondemand`。performance、powersave、userspace、conservative、schedutilも選択される | 実際のdriver・周波数・governorは起動後に読む。速さだけでなく温度・電力を測る |
| CMA | `CONFIG_CMA_SIZE_MBYTES=5` | 最終予約量は起動引数やDTにも依存する。camera/display/DMAの連続領域不足と空きRAMを比較する |
| LTO | `CONFIG_LTO_NONE=y` | BuildrootのLTO選択とは独立。Clang LTOやCFIへの変更にはkernelと全外部moduleの再検証が必要 |
| memory hardening | strong stack protector、strict kernel/module RWX、freelist hardening、`INIT_STACK_ALL_ZERO`等が有効 | 個々の脅威とコードへの適用を確認する。CONFIGの個数を安全性の点数としない |
| Arm固有機能 | `CONFIG_ARM64_PTR_AUTH=y`、`CONFIG_ARM64_BTI=y` | 対応コードを作れることと、Cortex-A53が機能を実装することは別。実行時に効く防御と数えない |
| module署名 | `CONFIG_MODULE_SIG_FORCE=y`、署名hashはSHA-256 | 生成したmoduleの署名・読み込みを確認する。A/B更新bundleのEd25519署名とは別の信頼経路 |
| confinement | AppArmor・Landlock・seccomp filterのCONFIGが有効 | profile、アプリケーションによる制限、LSMの起動状態が別に必要。機能があるだけでは対象processを制限しない |
| firewall | `CONFIG_NF_TABLES=m`、IPv4/IPv6等の対応あり | userspace、module、ruleset、起動順、失敗時の遮断が必要。「firewall適用済み」とはしない |
| 保存 | ext4とSquashFS zstdが有効、`CONFIG_DM_VERITY=m` | dm-verityは構成していない。moduleを選ぶだけではroot hash・信頼の起点・block検証は成立しない |
| 圧縮RAM | zswap有効、既定圧縮はlzo。zramはmodule、既定圧縮はzstd | swap/zram device・容量・優先順位・実行時設定とは別。二重圧縮とCPU費用を比較する |

`CONFIG_LSM`の文字列は複数LSM名を含むが、名前の列挙は、それぞれのbuild・起動・policy適用を保証しない。AppArmor、Landlock、nftablesの導入を評価する際には、kernel capability、userspace、policyと権限、起動後の状態、拒否試験を分ける。

## module binary indexの配送候補

2026-11-23の[監査](../../experiments/2026-11-23-module-binary-index.md)では、既存artifactの通常起動はBusyBox modprobeで、テキストindexを使っていた。
defconfigの`BR2_PACKAGE_KMOD_TOOLS=y`は`BR2_PACKAGE_BUSYBOX_SHOW_OTHERS`への依存で正規化後に残らず、kmod libraryだけの配送と区別する。
既存OpenSSL測定器はlibkmodからmoduleをloadするため、最初は削除前に停止した。
その後、利用者が製品と測定器を分けることを承認した。[続行の記録](../../experiments/2026-11-23-module-index-prune.md)では、external post-buildでbinary indexを削除し、測定器は展開したfixture内でhost depmodを実行する形にした。

| 選択肢 | 効果・背反 | 今回の扱い |
|---|---|---|
| binaryとテキストの両indexを維持 | libkmodはbinaryを必要とする | 製品では不採用。測定fixtureで自前生成し、製品imageへは書き戻さない |
| external post-buildでbinaryだけ削除 | BusyBoxのテキストlookupを維持。kmod CLIへ変われば不適合 | 採用。host depmod・署名後に実行し、modprobeのsymlinkがBusyBoxでなければ削除を拒否 |
| kmod CLIを有効化 | kmodのmodprobeはbinary indexを要求。BusyBoxと同じfileを読むわけではない | 今回は変更しない。将来有効化時に配送条件を再確認 |
| module本体を削除 | 実機のhotplug・driver利用・依存先に影響 | 今回は変更しない。QEMUだけで不要と判断しない |

既存imageの再packでは非圧縮938,282 bytes、SquashFS 167,936 bytes減。前後のQEMU A/Bで19 moduleが一致した。
最新設定の製品buildと実機は未確認。kernel Kconfig、kmod library、module本体の配送は変えない。

## Firmware・M5 packageの制御

Raspberry Pi GPU firmwareは`BR2_PACKAGE_RPI_FIRMWARE_VARIANT_PI_CD`と`gpu_mem=16`を対応させる。CPU/RAM、display、camera、UART、tryboot等にはboot firmware側の設定もあるが、現在のCLI用途と将来の機能追加を分けて採否を判断する。周波数を上げる案は、安定性・熱・電源・SDカード保全まで測る前に採用しない。

Wi-FiのSDIO firmwareがあるだけでは、認証、国別規制、DHCP/DNS、再接続、資格情報の保護まで完成しない。M5のLCD・BMI270初期化データ・keymapも、配布元、許諾、該当driverと機器の対応を別に確認する。

M5 packageは外部moduleをbuildし、`KCFLAGS`へ`CONFIG_CARDPUTERO_V0_5=1`を渡す。overlayはC preprocessorと`dtc -@ -I dts -O dtb`を経由する。指定を増やす前に、driverが読むproperty、共有resetや電源の責務、標準DT bindingとの違いを追う。[公式OSとの照合](../hardware/official-software.md)と[ハードウェアの資料](../hardware/hardware-spec.md)から、設定変更の機能要件を確認できる。

## CM0のSDIO firmware配送

公式CM0 datasheetはCYW43439を挙げるが、固定配送には43436sを指すCM0専用aliasがある。
実機のchip ID・revision・BT subversionが未取得なので、単一familyに絞らない。
[比較記録](../../experiments/2026-11-23-sdio-firmware.md)に一次資料・名前の規則・残件を、
[file一覧](sdio-firmware-files.csv)に全92 entryの採否・hash・symlinkの到達先を残した。

固定Buildroot `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`の
[package Config.in](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/brcmfmac_sdio-firmware-rpi/Config.in)全3 tokenを表の最初の3行と機械照合した。
固定LibreELEC `6596d332eaadd63e2413e3937715a084f61c39e2`は2026-11-23取得の最新HEADと同じで、
firmwareデータにconfigure optionや実行時の引数・環境変数はない。Buildroot masterの同Config.inも固定版と一致した。
`.mk`は広いglobで配送するため、非公開のchip選択optionを追加で渡す方法もない。
以下の残りは供給経路を区別する関連設定で、Raspberry Pi boot設定全体の再調査ではない。

| option | 意味・既定値 | 固定版の採否と理由 |
|---|---|---|
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI` | 無線firmware。既定n | yを維持。固定供給元・PROPRIETARYの許諾は変更しない |
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_BT` | brcm/synapticsのhcd一式。既定n | yを維持。個別chipの選択肢がないためexternal post-buildで絞る |
| `BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI` | brcmfmac/cyfmac一式。既定n | yを維持。CM0用alias・NVRAMを保持する。BCM43XXXと同時選択できない |
| `BR2_PACKAGE_RPI_FIRMWARE` | boot/GPU firmware。既定n | yを維持。SDIO firmwareの供給元ではない |
| `BR2_PACKAGE_RPI_FIRMWARE_VARIANT_PI_CD` | Linux bootに必要なcut-down一式。既定n | 現行yを維持。SDIO削減には使わない |
| `BR2_PACKAGE_RPI_FIRMWARE_CONFIG_FILE` | boot/config.txtの入力。既定空 | 現行board設定を維持。無線blobの選択肢ではない |
| `BR2_PACKAGE_RPI_FIRMWARE_INSTALL_DTB_OVERLAYS` | overlay install。既定y | yを維持。CM0/M5のDTを削る変更はしない |
| `BR2_PACKAGE_LINUX_FIRMWARE_BRCM_BCM43XX` | linux-firmwareのBroadcom集合。既定n。CYW43XXをselect | 不採用。供給元の切替と重複配送になる。CM0固有alias・許諾の照合を別途要する |
| `BR2_PACKAGE_LINUX_FIRMWARE_BRCM_BCM43XXX` | 同BCM43xxx集合。既定n。CYW43XXXをselect | 不採用。現行Wi-Fi optionと競合し、chip一つへの配送最小化にもならない |

runtimeの探索名はsdio.c・of.c・firmware.c・btbcm.cに従う。
`brcmfmac.alternative_fw_path`と`firmware_class.path`は既定の空文字を維持し、探索先を増やさない。
module引数・boot設定・sysctlの全体は既存の設定表を参照する。この変更で製品の表示・永続writeは増えない。

代替は、現状の全配送を維持、linux-firmwareへ供給元を変更、必要blobを自前で再配送、external post-buildの4案。
全配送は確実だが容量を減らせない。供給元変更と自前再配送はalias・NVRAM・license・更新監視を抱えるため見送る。
固定供給元・legal-infoを維持し、保持rootとsymlinkの到達先を検査するpost-buildを採用した。
新しい依存・Blob版・CVE対応・保守期間は追加していない。RAMと起動時間の差は未測定である。

再pack比較ではrootfs通常file合計1,759,026 bytes、SquashFS 1,069,056 bytes減。
前後QEMU A/Bの19 moduleは一致したが、対象SDIOもBTも実機でのfirmware読込みは未確認。
実機でchip ID・revision・BT subversionと選択file名のlogを取得してから、さらに絞れるか再検討する。

## 一次資料と既存の実測

- [固定kernelのソース](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602)、[同版のkernel引数](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/kernel-parameters.txt)、[sysctl](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/sysctl)
- [Linux 6.18のkernel引数の説明](https://docs.kernel.org/6.18/admin-guide/kernel-parameters.html)。Raspberry Pi固有の差は固定ソースを優先する。
- [M5 packageのbuildとoverlay生成](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)、[kernel fragment](../../../board/cardputerzero/linux.fragment)
- [moduleの引数](../tuning/tunables-module-params.md)、sysctl（[system](../tuning/tunables-sysctl-system.md)、[IPv4](../tuning/tunables-sysctl-ipv4.md)、[その他のnetwork](../tuning/tunables-sysctl-network.md)）、[既定値の実測](../tuning/tunables-defaults.md)。当時の測定条件を維持し、今回の設定CSVと異なる版の結果を混ぜない。
