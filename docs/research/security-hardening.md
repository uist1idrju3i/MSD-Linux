# セキュリティ対策と費用対効果

## 脅威モデル

この製品は取り外し可能な microSD から起動します。カードを入手した攻撃者は、Linux が起動する前にブートファイル、カーネル、rootfs を置き換えられます。同じカード内にあるハッシュ、署名鍵、dm-verity の root digest だけでは、カード全体を交換する攻撃に対する信頼の起点になりません。【推測】[BCM2837 の legacy boot 文書](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc)／[Raspberry Pi secure-boot ガイド](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md)

Raspberry Pi の secure-boot ガイドは Pi 4 以降の手順を説明しています。BCM2837 には同ガイドに基づく Raspberry Pi の secure-boot 経路が文書化されていないため、この製品では「未対応」として扱います。物理的に不可能とまでは断定しません。【一次】【未確認】[Raspberry Pi secure-boot ガイド](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md)

この文書で優先する脅威は、更新ファイルの置換、実行中のサービスやネットワーク経由の侵入、USB 周辺機器を入口とする攻撃、カードの物理的な改ざんです。ケースへの物理アクセス、デバッグ端子、製造時の鍵管理をどこまで攻撃者に許すかは製品要件として未決です。【未確認】[脅威モデルの未確定項目](measurement-and-planning.md)

## 現行の対策と不足

更新処理は `manifest.sig` を公開鍵で検証し、SHA-256 マニフェスト検査と書込み後の read-back を行います。公開鍵は post-build で `/etc/msd-update/update-key.pem` に配置されます。ただしカード全体を交換できる攻撃者への信頼の起点にはならず、署名鍵のリリース運用・更新・失効は別途管理が必要です。【一次】[更新処理](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)／[post-build](../../board/cardputerzero/post-build.sh)

rootfs は読み取り専用の SquashFS として構成されています。`/data` の ext4 マウントには `nodev` と `nosuid` が指定済みで、`noexec` は未指定です。`noexec` は更新処理や利用者が意図する実行ファイルを妨げる可能性があるため、利用方法を確認してから採否を決めます。QEMU では、`noexec` を足しても起動と `/data` の準備は変わらず、`/data` 上のファイルの直接実行だけが拒否されました。`sh` に渡す実行と、`/data/etc` を lowerdir にした `/etc` の overlay 経由の実行は防げません（[2026-10-21-qemu-data-noexec](../experiments/2026-10-21-qemu-data-noexec.md)）。【一次】[現行 fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab)／[イメージ構成](../../board/cardputerzero/genimage.cfg)

Buildroot defconfig は `BR2_FORTIFY_SOURCE_3=y` を選んでいます。SSP、RELRO、PIE と最終的なカーネル設定は、Buildroot の選択値だけでなく生成物のリンク設定と最終 `.config` で確認します。【一次】【未確認】[Buildroot defconfig](../../configs/msd_cardputerzero_defconfig)／[カーネル fragment](../../board/cardputerzero/linux.fragment)

Wi-Fi、Bluetooth のカーネルドライバーとファームウェアは構成に含まれますが、起動時の無線デーモン、ペアリング方針、USB gadget の最終構成は確認できていません。カーネルモジュールの存在だけでは、ユーザー向け通信機能が稼働しているとは判断しません。【一次】【未確認】[無線の構成](../../board/cardputerzero/linux.fragment)／[Buildroot defconfig](../../configs/msd_cardputerzero_defconfig)

## 対策の優先度


| 区分 | 対策 | 期待する効果 | 費用（起動時間・RAM・保守） | ハードウェア機能へのリスク | 検証方法 |
|---|---|---|---|---|---|
| A：先に実施、低コスト | 更新マニフェストを秘密鍵で署名し、読み取り専用 rootfs に公開鍵を置いて検証する。既存の A/B、read-back、健全性確認は維持する。 | 配布中の更新物やネットワーク経路での置換を検出する。【推測】 | 起動時に小さな検証処理を追加し、鍵保管・ローテーション・復旧手順を保守する。 | 署名鍵や形式の誤りで更新が止まる可能性がある。 | QEMU／ホスト試験で正常署名、改ざん、鍵不一致、旧版への復帰を確認。実機で更新時間と電断復旧を確認。 |
| A：先に実施、低コスト | `/data` に `nodev,nosuid` を追加し、実行ファイルを必要としない場合だけ `noexec` を評価する。未使用サービス、無線の役割、USB gadget 機能を無効化する。 | root 権限昇格や不要なネットワーク／USB 経路の影響範囲を抑える。【推測】 | 起動時間・RAM の増加は小さい見込み。設定と機能要件の保守、互換性試験が必要。 | 更新ツール、無線、USB device mode、周辺機器の利用を壊す可能性がある。 | QEMU で mount option・サービス・カーネル設定を確認し、実機で LCD、keyboard、Wi-Fi、Bluetooth、USB host／device、update を回帰試験。 |
| A：先に実施、低コスト | SSP、FORTIFY、RELRO、PIE を Buildroot の toolchain／package 設定で監査し、実際に適用できる保護を有効化する。sysctl は `dmesg_restrict`、`kptr_restrict`、`unprivileged_bpf_disabled` 等を対象に、既存機能との整合を確認する。 | メモリー破壊の悪用や情報露出を抑える多層防御になる。【推測】 | ビルド時間、RAM、バイナリーサイズへの影響を測り、ツールチェーンと全パッケージの保守が必要。 | 古いドライバー、デバッグ、必要なモジュールの遅延ロードに影響し得る。`modules_disabled=1` は再起動まで解除できず、後から必要な機能をロードできなくなるため無条件に設定しない。 | QEMU で最終 `.config`、ELF 属性、sysctl 値、必要なモジュールロードを確認。実機で全ハードウェア機能を回帰試験。 |
| B：後で評価、中コスト | dm-verity で読み取り専用 rootfs のブロックを検証し、root digest を署名済み更新メタデータに結び付ける。 | QEMUでのrootfs破損拒否は確認済み。信頼できるdigestがある場合の改ざん検知を目指す。【推測】 | device-mapper、起動時検証、A/B 更新・復旧、ハッシュ管理が複雑になる。RAM と起動時間は実機で未測定。 | 検証エラーで起動不能になる可能性があり、復旧スロットの検証も必要。 | [QEMU記録](../experiments/2026-10-21-qemu-dm-verity.md)。A/B復旧、root digestの信頼、実機起動時間・RAM・読み込み遅延は未実施。 |
| C：この機器では優先しない、高コスト | 文書化された OTP secure boot を持つ SoC への移行、または外部の信頼できる root of trust を追加する。 | カード交換だけでは置換できない起動時の信頼点を設ける。【推測】 | 基板変更、不可逆の鍵登録、製造時の鍵管理、復旧・在庫運用が必要。 | 起動鍵や署名済みイメージを失うと復旧できない危険がある。 | QEMU では OTP／BootROM 強制を検証できない。量産相当の実機で未署名・改変イメージと復旧手順を試験する。 |

## カーネル・起動時ハードニング候補

KSPP の推奨設定を出発点に、CM0 の機能・起動時間・RAM との両立を確認します。tier は導入順の案であり、最終 kernel `.config` や性能を測定した結果ではありません。【一次】[KSPP Recommended Settings](https://kspp.github.io/Recommended_Settings)。コスト欄の見込みは設計上の推測で、実測値ではありません。

| tier | 設定 | ねらい | 起動・RAM コスト／条件 | 採否・検証 |
|---|---|---|---|---|
| A | `CONFIG_STACKPROTECTOR_STRONG`、`CONFIG_STRICT_KERNEL_RWX`、`CONFIG_HARDENED_USERCOPY` | kernel memory の保護を強化 | driver 回帰を確認 | 採用。S6 の `Image` は 131,072 B、`gzip -9n` は 25,740 B 増加。QEMU ready-marker の中央値は 3.142595 s から 3.225268 s（+82.673 ms、+2.63%）。[実験記録](../experiments/2026-10-19-s06-kernel-hardening.md) |
| A | `CONFIG_RANDOMIZE_BASE` | kernel ASLR | Pi firmware が `kaslr-seed`／`rng-seed` を CM0 に渡すか未確認 | 採用。seed の供給有無と実効性は実機で確認する。 |
| A | `CONFIG_SECURITY_YAMA`、`CONFIG_BPF_UNPRIV_DEFAULT_OFF` | ptrace と unprivileged BPF を制限 | 診断・BPF 利用を確認 | 採用。`CONFIG_LSM` は既定の LSM 一覧を維持して Yama を含めた。QEMU の起動ログで Yama が有効になり、`ptrace_scope=1` を確認。 |
| A | `CONFIG_MODULE_SIG`、`CONFIG_MODULE_SIG_FORCE`、`CONFIG_MODULE_SIG_ALL`、`CONFIG_MODULE_SIG_SHA256` | module の署名を必須化 | per-build 鍵を使う。kernel と modules は同じ build の組で配布する。 | 採用。1,039/1,039 modules に署名があり、未署名 `usbnet` は QEMU で拒否された。`modules_disabled=1` は USB／Wi-Fi／Bluetooth の hotplug autoload を妨げるため不採用。署名強制時は、信頼鍵で署名されていない第三者製 out-of-tree module をロードできない。 |
| B | `CONFIG_INIT_STACK_ALL_ZERO`、`init_on_alloc=1`、`init_on_free=1` | 初期化されていない memory の利用を抑える | memory clear の CPU 帯域・起動時間コストを実測 |
| B | `CONFIG_SLAB_FREELIST_HARDENED`、`CONFIG_SECURITY_LOCKDOWN_LSM` | heap exploit 緩和、kernel interface 制限 | RAM／CPU 増は未測定。Lockdown と firmware・debug 経路の互換性を確認 |
| C | ARM64 PAC／BTI | return address・間接分岐の保護 | Cortex-A53 は Armv8.0 世代で PAC／BTI を実装しないため対象外【一次】[Arm Cortex-A53](https://developer.arm.com/documentation/100095/0001/)、[Arm PAC/BTI](https://developer.arm.com/documentation/102433/latest/) |

採用前に最終 `.config`、起動ログ、全周辺機能、更新・復旧試験を確認します。

署名鍵を read-only rootfs に置く設計は、更新バンドルの真正性を検査する用途です。CM0 の起動時に rootfs 自体を認証する独立した信頼点がないため、攻撃者がカード全体を交換できる場合は、鍵と検証処理も差し替えられます。したがって署名更新を「secure boot」と呼ばず、A/B の read-back と健全性確認も残します。【推測】[Raspberry Pi secure-boot ガイド](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md)／[更新処理](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)

## dm-verity と BCM2837 の暗号機能

dm-verity が保証するのは、検証に使う root digest を信頼できる場合の読み取りブロック整合性です。digest を同じ microSD にだけ置く構成では、カード全体を交換する攻撃者に対する信頼点になりません。【推測】[dm-verity 文書](https://docs.kernel.org/admin-guide/device-mapper/verity.html)

Raspberry Pi の暗号化ガイダンスは BCM2837 に Adiantum、BCM2711 に AES を推奨していますが、これは BCM2837 で AES、PMULL、SHA、CRC の各命令が実装されることを証明しません。BCM2837 の HWCAP／CPU feature は未確認です。実機で `/proc/cpuinfo`、`getauxval(AT_HWCAP)` と実際の dm-verity／暗号ワークロードを測り、起動時間と CPU 負荷を比較します。【一次】【未確認】[Arm Cortex-A53 TRM](https://developer.arm.com/documentation/ddi0501/latest/)

## 無線・USB の攻撃面

Wi-Fi／Bluetooth のドライバーとファームウェアは選択されていますが、アソシエーション、ペアリング、常時 discoverable の有無は未確認です。必要な無線機能が確定するまでは、起動時サービス、権限、ペアリング可否を検査し、不要な無線を無効化します。【未確認】[無線カーネル設定](../../board/cardputerzero/linux.fragment)／[Buildroot defconfig](../../configs/msd_cardputerzero_defconfig)

USB hub、USB-A、host／device 切替、SR9900A Ethernet の実際の USB ID と対応ドライバーは実機で確認します。USB gadget 機能は一部が kernel fragment で無効化されていますが、それだけで最終 `.config` や runtime の全 gadget 経路が無効だとは断定できません。【一次】【未確認】[USB／Ethernet の調査](scope-and-hardware.md)

## 未確認事項

| 項目 | 確認方法 |
|---|---|
| CM0 の secure-boot／鍵登録経路 | Raspberry Pi の公開ガイドは Pi 4 以降を対象としています。BCM2837 の別経路があると推測せず、対象SoC・ファームウェアの公開仕様を確認します。【未確認】[secure-boot ガイド](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md) |
| 署名形式、鍵更新・失効、緊急復旧 | A/B と署名検証を含む設計・試験が未実施です。【未確認】[更新処理](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) |
| `/data` の `noexec`、USB gadget、無線の実効設定 | 最終 Buildroot 設定、マウント一覧、起動サービス、稼働中モジュールを確認し、機能回帰試験を行います。【未確認】 |
| SSP／RELRO／PIE と BCM2837 の crypto HWCAP | 最終 ELF／kernel config と実機の CPU feature を確認します。【未確認】[Arm Cortex-A53 TRM](https://developer.arm.com/documentation/ddi0501/latest/) |
| 攻撃者が持つ物理アクセスと復旧要件 | 製品要件として脅威境界を決めます。【未確認】 |


- 【一次】[Raspberry Pi secure-boot ガイド](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md) — “how secure-boot works on a Raspberry Pi 4 (or newer)”
- 【一次】[dm-verity 文書](https://docs.kernel.org/admin-guide/device-mapper/verity.html) — dm-verity の設定、root digest、検証動作。
- 【一次】[Arm Cortex-A53 TRM](https://developer.arm.com/documentation/ddi0501/latest/) — 暗号拡張の構成は SoC 依存であり、対象 CM0 の実装確認は別途必要。
- 【一次】[現行更新処理](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)、[fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab)、[Buildroot defconfig](../../configs/msd_cardputerzero_defconfig)、[kernel fragment](../../board/cardputerzero/linux.fragment)。

## 出典と短い抜粋

| 主張 | URL | 原文の短い抜粋 | 確度 |
|---|---|---|---|
| Raspberry Pi の secure-boot 手順対象 | [Raspberry Pi secure-boot guide](https://github.com/raspberrypi/usbboot/blob/0fd2663f869b7f325f4481049c60d6394855260e/docs/secure-boot.md) | “how secure-boot works on a Raspberry Pi 4 (or newer)” | 【一次】 |
| BCM2837 legacy boot が SD の bootcode から始まる | [Raspberry Pi legacy boot flow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-legacy.adoc) | “check primary SD for `bootcode.bin`” | 【一次】 |
| 更新処理の署名検証と SHA-256 | [現在の updater](https://github.com/uist1idrju3i/MSD-Linux/blob/main/board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) | `openssl pkeyutl -verify` / `sha256sum -c manifest` | 【一次】 |
| `/data` mount options | [現行 fstab](https://github.com/uist1idrju3i/MSD-Linux/blob/main/board/cardputerzero/rootfs-overlay/etc/fstab) | `/dev/mmcblk0p7 /data ext4 noauto,noatime,data=journal,errors=remount-ro 0 2` | 【一次】 |
| dm-verity root digest の trust 要件 | [Linux dm-verity documentation](https://docs.kernel.org/admin-guide/device-mapper/verity.html) | “This hash should be trusted as there is no other authenticity beyond this point.” | 【一次】 |
| Buildroot FORTIFY 設定 | [board defconfig](https://github.com/uist1idrju3i/MSD-Linux/blob/main/configs/msd_cardputerzero_defconfig) | `BR2_FORTIFY_SOURCE_3=y` | 【一次】 |
| kernel の media support と watchdog 設定 | [kernel fragment](https://github.com/uist1idrju3i/MSD-Linux/blob/main/board/cardputerzero/linux.fragment) | `CONFIG_BCM2835_WDT=y` / `# CONFIG_MEDIA_SUPPORT is not set` | 【一次】 |
| Cortex-A53 crypto extension は option | [Arm Cortex-A53 TRM](https://documentation-service.arm.com/static/5e9077ee8259fe2368e2acf7?token=) | “The optional Cryptography Extension is not included in the base product.” | 【一次】 |
| kernel hardening sysctl の存在 | [Linux kernel sysctl documentation](https://docs.kernel.org/admin-guide/sysctl/kernel.html) | `dmesg_restrict` / `kptr_restrict` / `unprivileged_bpf_disabled` | 【一次】 |
| module の自動署名と制限モード | [Linux kernel module signing](https://docs.kernel.org/admin-guide/module-signing.html) | “modules will be automatically signed during the modules_install phase of a build”; “only modules that have a valid signature that can be verified by a public key in the kernel’s possession will be loaded.” | 【一次】 |
| 既定の module signing key の自動生成 | [Linux kernel module signing](https://docs.kernel.org/admin-guide/module-signing.html) | “the kernel build will automatically generate a new keypair using openssl if one does not exist” | 【一次】 |

A/B/C の費用・効果・リスクと実装案は、これらの資料および現在のリポジトリ構成に基づく設計上の推論です。実機での性能・攻撃耐性を示す測定結果ではありません。【推測】
