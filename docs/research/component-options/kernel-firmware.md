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

## Firmware・M5 packageの制御

Raspberry Pi GPU firmwareは`BR2_PACKAGE_RPI_FIRMWARE_VARIANT_PI_CD`と`gpu_mem=16`を対応させる。CPU/RAM、display、camera、UART、tryboot等にはboot firmware側の設定もあるが、現在のCLI用途と将来の機能追加を分けて採否を判断する。周波数を上げる案は、安定性・熱・電源・SDカード保全まで測る前に採用しない。

Wi-FiのSDIO firmwareがあるだけでは、認証、国別規制、DHCP/DNS、再接続、資格情報の保護まで完成しない。M5のLCD・BMI270初期化データ・keymapも、配布元、許諾、該当driverと機器の対応を別に確認する。

M5 packageは外部moduleをbuildし、`KCFLAGS`へ`CONFIG_CARDPUTERO_V0_5=1`を渡す。overlayはC preprocessorと`dtc -@ -I dts -O dtb`を経由する。指定を増やす前に、driverが読むproperty、共有resetや電源の責務、標準DT bindingとの違いを追う。[公式OSとの照合](../official-software.md)と[ハードウェアの資料](../hardware-spec.md)から、設定変更の機能要件を確認できる。

## 一次資料と既存の実測

- [固定kernelのソース](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602)、[同版のkernel引数](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/kernel-parameters.txt)、[sysctl](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/sysctl)
- [Linux 6.18のkernel引数の説明](https://docs.kernel.org/6.18/admin-guide/kernel-parameters.html)。Raspberry Pi固有の差は固定ソースを優先する。
- [M5 packageのbuildとoverlay生成](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.mk)、[kernel fragment](../../../board/cardputerzero/linux.fragment)
- [moduleの引数](../tunables-module-params.md)、[sysctl](../tunables-sysctl.md)、[既定値の実測](../tunables-defaults.md)。当時の測定条件を維持し、今回の設定CSVと異なる版の結果を混ぜない。
