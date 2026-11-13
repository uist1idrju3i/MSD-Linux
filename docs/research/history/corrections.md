# 訂正済み事項

## 2026-11-12の書き込み経路

| 原記述・推測 | 訂正と理由 | 根拠 |
|---|---|---|
| 台帳の「mkfsに指定がないので通常imageでもlazy初期化」、syslogの起動は未確認 | 通常imageはgenimageが `lazy_itable_init=0,lazy_journal_init=0` を付けます。空partitionのfallback format・起動時のonline resizeは別経路です。生成rootfsとQEMUではsyslogd・klogdが起動していますが、log先はRAMです | [台帳](../../design/write-policy.md)、[測定条件とraw値](../../experiments/2026-11-12-write-inventory.md) |

## 2026-11-12のBuildroot LTS判定

固定版監視がすべての`.02.x`をLTS候補とし、`pinned-versions.md`に2026.02.xを表示していました。[公式方針](https://buildroot.org/lts.html)は2025.02以降、奇数年の最初のreleaseを3年間保守します。現行は2025.02.x（2028年3月まで）、次は2027.02です。生成側とfixtureも修正し、[固定版表](../dependencies/pinned-versions.md)の他行の取得日とは区別しました。

## 2026-11-03 の高速起動候補の状態訂正

| 原記述・混在 | 訂正と理由 | 根拠 |
|---|---|---|
| `fastboot-ideas.md` の `start_cd.elf` / `fixup_cd.dat` 行: 【案・未検証】 | 現行 `config.txt` の `gpu_mem=16` が cut-down firmware を選び、生成処理と image 定義が両ファイルを収録する。設定と収録は確認済みだが、実機での起動は未確認 | [config.txt](../../../board/cardputerzero/config.txt)、[post-image.sh](../../../board/cardputerzero/post-image.sh)、[genimage.cfg](../../../board/cardputerzero/genimage.cfg)、[ファームウェア調査](../boot/firmware.md) |
| `fastboot-ideas.md` の boot 設定行: 【案・未検証】 | `boot_delay=0` と `disable_splash=1` は現行 `config.txt` にある一方、`avoid_warnings` は設定されていない。実機での効果は未確認 | [config.txt](../../../board/cardputerzero/config.txt) |
| `fastboot-ideas.md` の built-in / module 行: QEMU 実測済み（#129: Image -3.6%、modalias 自動ロード正常）。採否は積み上げ方針で再検討中 | PR #129 の QEMU 実験は製品設定を変更せず、Image の縮小に対してフラッシュ節約が小さく署名鍵ペアの管理が複雑になるため、追加のモジュール化は見送りが妥当と結論した | [linux.fragment](../../../board/cardputerzero/linux.fragment)、[PR #129](https://github.com/uist1idrju3i/MSD-Linux/pull/129)、[実験記録](../../experiments/2026-10-30-modularize-drivers.md) |

## 2026-11-03 のユーザー空間・強化項目の整理

| 原記述・混在 | 訂正と理由 | 根拠 |
|---|---|---|
| BusyBoxの`sysctl -p`は`sysctl.d`も読む | 固定BusyBox 1.38.0は既定で`/etc/sysctl.conf`、引数があればそのファイルを順に読む。directoryを自動で列挙しない。起動scriptが明示して複数ファイルを渡す処理とは別 | [固定sourceの追跡](../security/history/kernel-and-mounts.md#busyboxのsysctl読込み) |
| libcの詳細表と後半の未確認の要約 | 同じ原稿内でも確認状態が違う。版・数値・URLを後の知識で置換せず、重複要約の原文とhashはCSV、詳細はlibc履歴、現在の候補比較は代替比較へ分ける | [原文要約](../userspace/original-summaries.csv)、[libc履歴](../userspace/libc-history.md)、[現在の比較](../alternatives/libc.md) |
| systemdのunit例とBusyBox製品構成が同じ段落にある | 当時の条件付きの例として保持し、現行のPID1・mdev・mount実装の説明とは分ける。kernel設定や候補表をruntimeの強制済みと読まない | [強化項目の読取り方](../security/history/README.md)、[ユーザー空間](../userspace/README.md) |

## 2026-11-02 の権限設計と強化項目

[日付付き強化項目](../security/history/README.md)の採用方向と現行実装を分け、設定から実行時の強制を推定していた箇所を訂正しました。数値・過去の実験結果を新しい製品の試験結果へ置き換えてはいません。

| 原記述 | 訂正と理由 | 根拠 |
|---|---|---|
| firewallにはnft userlandだけが不足、listenerなし、nftablesが最小 | 必要module・ruleset・起動順・hotplug・正負の試験も未実装。runtime socketとsize比較は未試験。output acceptは侵害済みserviceの外向き通信を止めない | [通信開始と検証](../security/network.md) |
| AppArmor以外のLSMは未compile、Landlock等は有効 | Yama/Landlockの設定もある。kernel設定・LSM名の一覧・実行時policyと強制を区別。AppArmorのprofile load・enforce、LandlockのABIとprocess側の適用が必要 | [固定CI設定の照合範囲](../security/README.md)／[Linux機構](../security/principles.md) |
| SELinuxは一律不採用、AppArmor profileは自作 | 固定構成と保守費用を理由にAppArmorを第一候補とする比較に限定。上流のprofileやdaemonの既存privsepを先に評価し、major LSMの無条件併用も前提にしない | [原則と適用条件](../security/principles.md) |
| do-udp設定だけで平文fallbackを防ぐ、時刻の乱れが署名検証自体を崩す | 全平文通信の停止保証を撤回し、UDP/TCP・上流TLS・fallbackの確認を要件化。raw Ed25519の数学的検証は壁時計不要で、TLS・metadata期限・運用は別 | [DNS・時刻・更新](../security/network.md) |
| NoNewPrivilegesをnosuid/LSMで代替 | no_new_privsはexec時の昇格等に関する別のkernel機構。保有権限のdropやFD移譲制限の代用ではなく、LSM遷移との順序も試験する | [Linuxの仕組み](../security/principles.md) |
| Quad9でDNS層は対応済み、noexecならdataは実行されずhost AVと同じ効果 | DNS設定は未稼働。noexecはinterpreterやetc overlayを一般には防がず、dm-verityも製品未導入。hostでのscanとdevice実行時の検知は対象・限界が異なる | [通信設計](../security/network.md)／[可変設定](../security/privileges.md)／[既存noexec試験](../../experiments/2026-10-21-qemu-data-noexec.md) |
| A/Bと署名検証を含む設計・試験が未実施 | raw Ed25519の現行実装と既存host試験を区別。鍵の配布・更新・失効、復旧、可変etcが正本を隠す境界が未解決 | [現行対策と不足](../security/threat-model.md)／[処理別設計](../security/privileges.md) |

## 2026-11-02 の圧縮library比較

| 原記述 | 訂正と理由 | 根拠 |
|---|---|---|
| libdeflateを「EB Wise」「zlib API一部互換」と記載 | Eric Biggersらの実装で、DEFLATE/zlib/gzip形式のwhole-buffer処理を行う専用API。zlib APIと互換の差し替えではなく、streamingにも非対応。性能とRAMはcallerを移植して測る必要がある | [固定README・headerと置換条件](../alternatives/build-support.md) |
| libdeflate/zlib-ngを更新データの高速化候補として一括記載 | zlib-ngの互換modeと、callerの移植が必要なlibdeflateを分ける。現行rootfsはzstdのSquashFSであり、zlib系の処理が律速かも未確認 | [圧縮・image生成の比較](../alternatives/build-support.md) |

## 2026-11-02 のSBOM生成経路

通常buildと週次securityにはLinux版の補正処理の有無に差があった。固定生成物の通常build SBOMは `custom` のままであり、生成成功だけでは正しいkernel版の確認にならない。両経路で同じ補正・内容照合を行い、入力のshow-infoも保存する。[検証条件と失敗試行](../../experiments/2026-11-02-sbom-generation.md)を参照。

## 2026-11-02 のハードウェア・公式OS照合

| 原記述・混同 | 訂正 | 根拠 |
|---|---|---|
| CM0Liteの無線やCM0のCSI能力をLinuxの既定設定と混同 | CM0Liteにも無線ありの型番がある。CM0と基板は4 lane対応だが、固定Linuxのcamera endpointは既定2 lane | [資料と全U1〜U37](../hardware/hardware-wiring-audit.md)、[生成物](../../experiments/2026-11-02-hardware-artifact-audit.md) |
| BMM150を主I2Cのdeviceとして扱う | BMI270のAUX経由。主I2C上で同じ0x10のES8389と衝突すると判断しない | [回路接続監査](../hardware/hardware-wiring-audit.md) |
| M5 `7551854`、Linux `2341883`を現行値として引用 | 現行固定値はM5 `37b42d9`、Linux `b3495ea`。公式pi-genのkernel固定とM5可変main取得も区別 | [公式OS比較と資料hash](../hardware/official-software.md) |
| SysRq-Uだけを製品の電源異常処理として記載 | MSD/Linuxはlocal patchでsyncと通知を加えている。QEMUの通知・RO化と実電断耐性は別 | [生成物とログの確認](../../experiments/2026-11-02-hardware-artifact-audit.md) |
| 公式APPLaunchのLVGL版や全配布imageを検証したかのような表現 | 公開build scriptと取得条件の照合に限定。配布binaryのLVGL版・全サービスは本照合では未確認 | [公式OS比較](../hardware/official-software.md) |

## 2026-11-02 の文書整理で補った条件

| 原記述 | 訂正・補足 | 根拠 |
|---|---|---|
| Yocto 総まとめの「同じカーネルなら変わらない。移っても速くはならない」 | C3/C4 の差が事前の閾値を超えなかったことだけを示す。同等性、完成品同士、実機への一般化はできない。実験本文と CSV は保持し、読み方の注記を加えた | [起動時間の比較](../../experiments/2026-11-02-buildroot-yocto-boottime.md)、[CSV](../../experiments/2026-11-02-buildroot-yocto-boottime.csv) |
| cold build 約 2.3 倍、作業領域約 6 倍 | 同じホストの各 1 回の参考値。完成イメージと最小イメージ、外部ツールチェーン利用と内部構築の違いがあるため、一般的なビルドシステムの倍率としない | [成果物の比較](../../experiments/2026-11-02-buildroot-yocto-artifacts.md) |
| RESEARCH の「現行 `/data` は 1,024 B ブロック」と変更案 | 1,024 B は当時の値。現行 CI は 4,096 B を検査する。旧測定値は保存し、入口は現在のコードを案内する | [S3](../../experiments/2026-10-19-s03-data-ext4-writes.md)、[build workflow](../../../.github/workflows/build.yml) |

以下は従来の訂正記録です。版数と確認時点は各出典の条件を保持します。

### よくある誤解と正しい内容
| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| `/data` の自動拡張 | UPDATE.mdに「初回起動時の自動拡張は未実装」と記載 | `S02msd-data` が `msd-data-grow` を呼び、MBRのp4・p7とext4を拡張する実装が既にあります。拡張の失敗時はログを出し、マウントを維持します。実装・ホスト試験・過去のQEMU・実機未確認を区別します | [導入と更新の照合](../release-client/install-update-status.md) |
| Kickstarter の販売数 | 3,000/12,000 台の情報を未検証の SNS 情報と扱う | **Update 13 は公式更新**の引用（X のリンクカード由来。本文は取得できていない=403） | https://x.com/saitotetsuya/status/2111008950107910198<br>URL未取得（Kickstarter 本文） |
| pi-gen は rpi-v8 カーネルを apt から導入 | pi-gen は rpi-v8 カーネルを apt から導入(版の固定なし) | **6.18.39-1+rpt1 を sha256 検証+apt pin 1001+hold で固定**。M5 dtoverlays は `--depth=1` で最新追従 | https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/files/kernel.pref#L3<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage0/02-firmware/01-run.sh#L32<br>https://github.com/CardputerZero/pi-gen/blob/791a985d4efca7327ae1fdb6c48230ac0d1ee1bc/stage2/05-cardputerzero/01-run.sh#L20 |
| 起動時間の数値 | 起動時間の数値(2.1s、5〜6s、3.5s 未満)を同列に並べた | 数値は SoC・条件・終点が異なり**合成不可**。2112ms は 227KB の小型カーネル構成、Linux 可用 7〜9s は自己申告、Pi 3B+ は ARM 開始 6.79s です。各値の条件を併記します | https://github.com/CardputerZero/circle-boot-splash/blob/b80d7c6a537c09c1ca233aeffa9c2e8601b113df/app/cardputerzero-splash/BENCHMARK.md#L14-L21<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf<br>https://github.com/johschmitz/buildroot-quickpi/blob/2f62ac8b7a1d2edb29aad7008f2c5f38aa5195a5/README.md#L15-L16 |
| rpi-eeprom の Pi5 stable | rpi-eeprom の Pi5 stable(2026-09-25)で A/B 更新 | A/B 更新の記載は 2026-05-13 の Pi5 系エントリ。**CM0 には無関係** | https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md (HTTP 200 のみ確認。内容は未読) |
| Mender Client 6.1.0 は二次情報/CM0 向け統合は不明 | Mender Client 6.1.0 は二次情報/CM0 向け統合は不明 | **6.1 は Supported(docs.mender.io)、mender-convert に RPi3(64bit)の U-Boot 構成あり。CM0 の構成・動作は未確認**。Buildroot の mender は 3.5.3(古い系列) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://docs.mender.io |
| zram は defconfig 未確認 | zram は defconfig 未確認 | **ZRAM=m、ZSWAP=y**(rpi-6.18.y bcm2711_defconfig) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86 |
| Buildroot 2026.08 は GCC 16.2.0 が既定 | Buildroot 2026.08 は GCC 16.2.0 が既定(旧記述) | **GCC 既定は 15.3.0**(14.x/16.x は選択式) | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6 |
| powerfail_suo は S→U→O | powerfail_suo は S→U→O(sync/ro/poweroff)を実行 | SysRq-U(読み取り専用で再マウント)に加え、バックライトと GPIO を操作します。's'、'i'、`kernel_power_off()` はコメントアウトされています | https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93 |
| rpi-image-gen の最新は v2.3.0 | rpi-image-gen の最新は v2.3.0(cm4/pi4/cm5/pi5 のみ)、issue #153 で image-rota は GPT・BCM2837 は MBR 要 | **最新 v2.8.0(2026-08-13)/master d7616a2**。device 層に pi3/zero2w はあるが、**image-rota は現行 master でも cm4/pi4/cm5/pi5 のみ**(コードで確認)。issue #153 は closed(2026-02-18)のため根拠をコードに変更 | https://api.github.com/repos/raspberrypi/rpi-image-gen/releases<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153 |
| 「検証ボードに RPi が無いから Zephyr 26.04 LTS は非対応」 | 「検証ボードに RPi が無いから Zephyr 26.04 LTS は非対応」 | 根拠は「v4.4.0 に BCM2710/rpi_zero_2w が無い」。Canonical フォークの中身は未確認 | https://github.com/zephyrproject-rtos/zephyr/tree/684c9e8f32e4373a21098559f748f06915f950c9/boards/raspberrypi |
| CM5 で display_auto_detect=0 の差は 9ms | CM5 で display_auto_detect=0 の差は 9ms(旧版は確認済み扱い) | 出典を特定できず【未確認】に降格 | URL なし |
| 「GL852G のリセットは PYG3 経由」 | 「GL852G のリセットは PYG3 経由」(推測) | docs に明記:PYG3 は**キーボードとハブの共用リセット** | https://docs.m5stack.com/en/CardputerZero |
| RAUC PR #1599 の状態は未確認 | RAUC PR #1599 の状態は未確認 | open・未マージ(2026-10-18) | https://api.github.com/repos/rauc/rauc/pulls/1599 |
| arm_64bit の CM0 対応は未確認 | arm_64bit の CM0 対応は未確認 | 対応表に CM0 なし。`[cm0]` フィルタはある | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/conditional.adoc#L43 |
| PREEMPT_RT の方針 | PREEMPT_RT は採用しない方針（boot-and-kernel.md の旧記述） | 2026-10-30 に製品構成に採用済みで、`linux.fragment` に `CONFIG_PREEMPT_RT=y` があります。Yocto の B2 でも vermagic に `preempt_rt` が出ました | [実験記録](../../experiments/2026-10-30-preempt-models.md)<br>[構築試験](../../experiments/2026-11-02-yocto-wrynose-probe.md) |
| Yocto への移行の結論 | Buildroot を維持し、Yocto には移行しない（pros-cons-2026-10.md） | 2026-11-02 に利用者が Wrynose 6.0 LTS への移行を方針として決めました。移行作業は未着手です | [再評価](../yocto-migration/reevaluation.md)<br>[移行計画（案）](../yocto-migration/migration-plan.md) |
| Yocto への移行（2026-11-02 の再決定） | Wrynose 6.0 LTS へ移行する方針 | 検証の結果、移行せず Buildroot を維持すると決めました | [総まとめ](../yocto-migration/summary-2026-11.md) |
| M5 kernel compatibility | kernel 版の前提に関する旧記述 | **panel-mipi-dbi-m.c の include は 6.12 で解決せず 6.18 で解決する（一次）。M5 code 全般が 6.18 以上必須とは言えません**。mainline panel-mipi-dbi 経路もありますが、実機確認は未確認 | https://raw.githubusercontent.com/m5stack/m5stack-linux-dtoverlays/75518549a2640486f5d13ea72ca4935b198d7c20/modules/st7789v-1.0/panel-mipi-dbi-m.c |


## 訂正済み事項

この表には公開資料から確認できる訂正をまとめています。

| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| LLVM libcの適用範囲 | 公式の重要関数不足の警告だけで、本機では一律に未成熟とした | 現行の公式トップと固定sourceは、静的Linux等の限定した本番利用と、regex・locale・wide-character I/O等の不足を併記します。限定した実験候補に戻しますが、MSD/Linux全体を置換できる根拠や本機の動作確認ではありません | [再評価・確認したcommit・一次資料](../alternatives/libc.md#llvm-libcの旧評価を変える根拠) |
| Mender を RPi3 の対象外 | Mender は RPi3 をサポートしない | mender-convert の README(HEAD 4b3f04a、2026-10-12 コミット)が `raspberrypi/uboot/debian/raspberrypi3_bookworm_64bit_config`(Raspberry Pi 3、Raspberry Pi OS bookworm 64bit)を「officially supported」の Core 構成に載せ、Mender Client 6.1 は 2026-10 にサポート対象(docs.mender.io supported-releases)。Mender Client 6.1.0 は mender.io のブログ(2026-10-16)に記載。CM0 自体の記載と動作は未確認 | [公開出典一覧](../sources/sources.md) |
| `/data` のマウントオプション | `/data` に `nosuid`、`nodev`、`noexec` が指定されていない（security-hardening.md の旧記述） | `fstab` は `noatime,nodev,nosuid,data=ordered,errors=remount-ro`。未指定なのは `noexec` だけです（2026-10-19 に main の `fstab` で確認） | [現行 fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| powerfail_suo の動作 | S→U→O を実行する | SysRq-U に加えてバックライトと GPIO を操作します。`'i'`・`'s'`・`kernel_power_off()` はコメントアウトされています（powerfail_suo.c @7551854 の L74/L83/L93/L106） | [公開出典一覧](../sources/sources.md) |
| UART0 の種別を PL011 と断定 | UART0 が PL011 である | 公式 DT は `serial0 = &uart1`(mini-UART、`uart1_pins` は空)、`serial1 = &uart0`(PL011、GPIO30〜33=BT)。公式 pi-gen は cmdline の `console=serial0,115200` を除去。「公式 pi-gen に enable_uart が無い」という記述は不正確でした。一部訂正として、pi-gen は M5 の Makefile(`config_setup`)経由で `enable_uart 1` を [all] に設定する(最終 config.txt は未検査) | [公開出典一覧](../sources/sources.md) |
| 「OpenSSH の既定は AES-GCM 候補」 | 「OpenSSH の既定は AES-GCM 候補」 | `chacha20-poly1305@openssh.com` が先頭(myproposal.h、V_10_5_P1)。OpenVPN は暗号の設定が要る(`--data-ciphers` 既定は AES-GCM 先頭) | [公開出典一覧](../sources/sources.md) |
| arm64 linear alias unmap の記述 | 修正が v7.2 に適用され、revert 後も残る | 導入(63e0b6a5b693)と revert(f102131c842d)はともに v7.2-rc1、再適用(fb0f3ef5601a)は v7.3-rc1 に入る(v7.2 には入らない)。`rpi-7.2.y` の mmu.c は data/bss を「read-only で map」する旧コードで影響なし、`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid`)を含む。compare API と各ブランチの raw で確認(再適用で RPi3/4 の問題が解消したかはコミットメッセージから読み取れず未確認のまま) | [公開出典一覧](../sources/sources.md) |
| CachyOS の遅延と kernel 回帰 | CachyOS の遅延を kernel 7.2 の回帰とする | 投稿者は BIOS で TPM を無効にして解消(2026-09-10)。Omarchy #6996 は Omarchy 4.0.0-1 / Linux 7.1.8、約 266MiB の initramfs と `initramfs_async=0` の x86 事例です。Omarchy の URL は移転前の組織配下で 404、現行は `omacom/omarchy` です | [公開出典一覧](../sources/sources.md) |
| KittenLabs の数値を条件なしで書いたのは不備 | 測定条件を示さず <3.5 秒とする | <3.5 秒は Zero 2 W+Buildroot 2024.02.1(フル glibc)、カーネル 8.5MiB(非圧縮。Raspbian 標準は 25MiB)、KASLR 無効、Spectre 等の緩和無効、sound/USB/HID/DVB/video・fb/RAID/高度なネットワーク機能無効、モジュール非圧縮、測定は電源投入から userspace が GPIO をトグルするまで(カーネル実行約 400ms)。「5.38→4.75→4.47 秒」と「9,276,375 B を 1.54 秒」は同じブログの Raspbian ベースの段階(HQ camera/display の自動検出無効、initramfs 削除)。「第三者・URL 未取得」とするのは誤りで、出典は同ブログ | [公開出典一覧](../sources/sources.md) |
| 起動終点を LCD+キーとする案 | 起動終点は LCD+キーと確定している | ユーザー要件に終点の定義はなく、LCD+キーは暫定案です。設計判断が確定するまでは選択肢を併記します | [公開出典一覧](../sources/sources.md) |
| GPIO6 の割り当て | SW_DET と keypad IRQ は GPIO6 を異なる用途で使う | 公式 docs の SW_DET=G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`(L292-293)は同じ GPIO6 で食い違いなし | [公開出典一覧](../sources/sources.md) |
| libc 比較の記述 | libc 比較の有無について異なる記述があった | libc 比較は取り込み済みで、未完成とする記述が古いものでした | [公開出典一覧](../sources/sources.md) |
| UART 物理ピン番号 | EXT 2.54-14P の UART 物理ピン番号を 13・14 番とした記述 | 12 番と 14 番(右列)。G15(UART_RXD)が 12 番、G14(UART_TXD)が 14 番で、13 番ピンは G7(SPI0_CS1)。物理ピンと GPIO を別列で示し、13 番ピンは G7(SPI0_CS1)と区別します。他の箇所に同じ誤記はありません | [公開出典一覧](../sources/sources.md) |
| M5 の `modules/rx8130` を RTC に必須とした記述 | RX8130 専用 driver が必要 | RX8130 は rpi-6.18.y(@2341883)の `rtc-ds1307.c` L1164 の `epson,rx8130` で扱われ(`RTC_DRV_DS1307=m`)、`modules/rx8130` は Makefile とオーバーレイ DTS だけで C ソースはありません。必要なのはドライバではなくオーバーレイです。単体オーバーレイの reg=0x68 と CardputerZero overlay の 0x32 の違いは未解決です | [公開出典一覧](../sources/sources.md) |
| 失敗検知・確定条件の扱い | 起動終点が未定なのに、失敗検知・確定条件を確定事項として扱う | 起動終点と設計案が決まるまで、失敗検知・確定条件を保留します | [公開出典一覧](../sources/sources.md) |
| M5 の既定 DT における UART | GPIO14/15 に出る UART の種別まで確定している | M5 の既定 DT では serial0 は mini-UART を指しますが、GPIO14/15 に出る UART の種別は未確認です | [公開出典一覧](../sources/sources.md) |
| `PYG12(LCD_RST)` の操作 | `disabled-gpios` の index から PYG12 であることまで確認済み | 確認できるのは `disabled-gpios = <&m5ioe1 11 1>` を駆動することで、それが PYG12 に当たるのは index+1 の推論(【推測】)。PYG6(MIC_SW)と GPIO6(SW_DET)は別の信号です | [公開出典一覧](../sources/sources.md) |
| mender-convert の公開日と状態 | changelog の日付を公開日とし、compare status を見誤った | mender-convert 5.1.0 の日付 2025-12-01 は changelog の日付で、GitHub release の公開は 2025-12-02T10:38:33Z(= 19:38 JST)です。compare API の status は ahead(ahead_by 17683)で、docs ページの本文も取得して確認しました | [公開出典一覧](../sources/sources.md) |
| RX8130 の driver に関する記述 | どの driver を使うか未確認 | `rtc-ds1307.c`(`epson,rx8130`)で扱え、別ドライバは不要です。rtc-ds1307.c の L1470 で確認しました | [公開出典一覧](../sources/sources.md) |
| Newlib の Linux 対応 | Newlib を Linux 非対応とする | sourceware のページは bot 防御により取得できず、Linux 対応は【未確認】です | [公開出典一覧](../sources/sources.md) |
| `kernel_power_off()` の行番号 | `kernel_power_off()` は L102 | L106(L102 はコメント行)。先頭コメントは L3-L9(S L7、U L8、O L9) | [公開出典一覧](../sources/sources.md) |
| ext4 の `data=journal` 削除予告 | v7.2 で削除予定とする | docs.kernel.org の最新版と v7.3-rc7・rpi-7.3.y にあり、v7.2・rpi-7.2.y・v6.18・rpi-6.18.y には記載がありません | [公開出典一覧](../sources/sources.md) |
| OpenVPN の ML-KEM の実効既定 | マニュアルの記載がそのまま実効既定になる | ソース(v2.7.6 `ssl.c` L552)は指定時のみグループを設定し、OpenSSL 3.6.4(Buildroot 2026.08 同梱)の既定グループは先頭が `X25519MLKEM768`(`ssl/t1_lib.c` L209)。実接続での使用は未確認 | [公開出典一覧](../sources/sources.md) |
| カーネルサイズの数値 | WP-1 の kernel size は 9.8MB | WP-1 のログの `size 0x9af973` = 10,156,403 B(約 10.2MB、9.69MiB)。initramfs 11.7MB(0xb2483c)は正しい | [公開出典一覧](../sources/sources.md) |
| GPU 段と kernel サイズの関係 | GPU 段の時間が kernel サイズに連動する | 【推測】サイズ比 1.09 に対し時間比は約 1.7 です。機材と測定区間が異なるため、両者の関係は推測です | [公開出典一覧](../sources/sources.md) |
| RPi OS kernel 6.18.50 の確認度 | RPi OS kernel 6.18.50 を一次資料で確認済みとする | 【未確認】（Imager 一覧では版の存在のみ確認できます） | [公開出典一覧](../sources/sources.md) |
| OpenVPN の PQ 鍵交換 | OpenVPN に PQ 鍵交換はないと言い切る | マニュアル上の記載はなく、実効既定は OpenSSL 版に依存します。実接続は未確認です | [公開出典一覧](../sources/sources.md) |
| `powerfail_suo` の先頭コメント範囲 | URL が O の行(L9)を含まない | URL 範囲を L3-L9 に修正し、O の行を含めます | [公開出典一覧](../sources/sources.md) |
| Compute Module Zero のデータシート | RP-009251-DS を CYW43439 のデータシートとし、URL を未確認とする | データシート Release 3 で BCM2837、無線はオプション(CYW43439)、CM0Lite は eMMC なしで SDIO と確認できます。「CM0 内蔵」ではなく「無線搭載版に搭載」と表現します。CM0Lite に無線があるかはデータシートに明記がなく【未確認】です | [公開出典一覧](../sources/sources.md) |
| Celeron benchmark の条件 | benchmark の測定条件が不明確 | ChromeOS の Crostini VM 上で測定された値です(gist 本文で確認)。blame には Type=simple の service は測定不能という注意が欠けていたことを man で確認しました | [公開出典一覧](../sources/sources.md) |
| `/var` の filesystem | `/var` を tmpfs として扱う | この image では `/tmp`、`/run`、`/dev/shm` が tmpfs mount で、`/var` は tmpfs ではありません | [fstab](../../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| SD の page size | 多くの SD card の page size は 16 KiB 以上 | 取得した公開資料が示すのは 2 KiB または 4 KiB の例であり、「多くは 16 KiB 以上」とする根拠はありません。個別カードの値は未確認です | [S3 記録](../../experiments/2026-10-19-s03-data-ext4-writes.md)、[読み取り専用領域と FS 比較](../storage/write-policy-and-s3.md) |
| CI の `mke2fs` version | PATH の `mke2fs 1.47.2` が image 作成にも使われた | image 作成に使われたのは Buildroot host `output/host/sbin/mke2fs` 1.47.4。PATH 上の version log は誤った binary を示していました | [storage-and-flash.md](../storage/README.md)、[Build run](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39204900529) |
| module dependency index より前の状態 | boot smoke test が通るので module autoload も正常 | host depmod に XZ support がなく `.ko.xz` を飛ばし、`modules.dep` が空で `modprobe` できませんでした。実機 autoload への影響は未確認です | [S6 modules.dep 記録](../../experiments/2026-10-19-s06-modules-dep-xz.md) |
| NUMA=n の結果 | gzip size が 64,784 B 減った候補は成功 | raw CSV の状態は `QEMU_FAILED`。保持した QEMU log がなく、サイズ差だけで判定できません | [S1 記録](../../experiments/2026-10-19-s01-kernel-sweep-trial.md) |
| カメラ電源の GPIO 割当て | 「カメラの power-enable GPIO は回路図から特定できない」 | 以前の記述は PDF の文字列だけを抽出し、回路図を読まずに結論づけていました。C154 V0.6.1 p.10 は `CAM_3V3`、`SSP7615-33DFR`、`R190 100K`、`R192 NC` を示し、LDO の EN は VSYS_5V に pull-up されています。p.5 は CM0 pin 44 と JP5 pin 17 を `CAM_GPIO` と表示します。CM0 DTS は GPIO40 を `CAM_GPIO` と名付け、`&cam1_reg` に `gpio = <&gpio 40 GPIO_ACTIVE_HIGH>` を設定するため、既定の cam1 IMX219 overlay が正しい pin を使います。v5 の GPIO16 は `G16_PY32_RST` で、M5 Makefile の GPIO16-high camera overlay は非 V0_5 側だけで追加されます。v5 に追加 GPIO hog は不要です。【一次】 | [C154 V0.6.1 schematic](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1243/C154-CardputerZERO_SCH_V0.6.1_20260702.pdf)<br>[CM0 DTS](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm/boot/dts/broadcom/bcm2710-rpi-cm0.dts)<br>[M5 CardputerZero Makefile](https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/Makefile) 【一次】 |
| S11 v2 QEMU の patch provenance | v2 の結果を commit 済み QEMU patch の結果として扱った | v2 image は prebuilt layer の QEMU を含み、commit 済み patch から build されたものと確認できません。v2 の測定値は invalid とはせず、別 build の参考値として保持し、patch 適用可能な `c01f6e7` の QEMU で v3 を再測定しました | [S11 記録](../../experiments/2026-10-20-s11-qemu-watchdog.md) |

| S21 SysRq-U marker と remount | driver marker は実 remount の証拠 | `dev_emerg()` marker は `handle_sysrq('u')` より前に出ます。kernel action line で判定した再測定では `kernel.sysrq=0` は remount なし 5/5、32 は remount 5/5 でした。製品採否は未決定 | [S21 記録](../../experiments/2026-10-21-s21-qemu-sysctl-ramoops.md) |

## 測定・検証文書の状態訂正（2026-11-02）

旧表と訂正する状態の原文は[原記録CSV](../verification/research-records.csv)、現在の試験状況は[試験台帳](../verification/experiment-catalog.md)へ保存しました。今回、実験を再実行したものではありません。

| 項目 | 旧記述の問題 | 訂正と根拠 |
|---|---|---|
| S1/S14 | 80候補の完了や失敗12件の全件誤検出と読める | [本番記録](../../experiments/2026-10-30-kernel-sweep-s1-s14.md)の集計はPASS 61、QEMU_FAILED 12、TARGET_MISMATCH 5、KEEP_CHANGED 1の79行。全12件を成功へ再分類できる証拠は確認できず、不一致を保持する |
| S10 | 初回記録の番号比較前の状態を現行の「未実装」とした | [番号比較v2](../../experiments/2026-10-25-s10-version-check.md)は古い番号・番号なしを既定で拒否し、明示した`--allow-downgrade`で許可。不正形式は常に拒否。可変な最大番号の保護・実機全体のanti-rollbackとは別 |
| S13 | 未着手と完了が併存し、最適化の単独効果と読めた | [元の結果表](../../experiments/2026-10-30-s13-optimize.md)は3構成、n=1、output4だけFTRACE=y。`-Os + LTO`の同時適用や統計的な同等性の確認ではない |
| S17 | SDモデルのblkdebugの限界を全ゲスト障害試験へ広げた | [SDモデルの記録](../../experiments/2026-11-01-s17-dmlw-blkdebug.md)ではホスト側発火・ゲスト非伝播。[dm-flakey記録](../../experiments/2026-10-30-s17-error-injection.md)にはゲストのreadエラーがある。試した経路を区別し、実カードのFTL・電断は未確認とする |

## 個別訂正の補足

| 項目 | 誤解されやすい記述 | 正しい内容 | 出典 |
|---|---|---|---|
| Lite 版の microSD | Lite 版には microSD がない | スロットはあるが、カードは付属しない | [公開出典一覧](../sources/sources.md) |
| `PARTITION_WALK` | 適用範囲の明記なし | EEPROM ブートローダー搭載機の機能で、Pi 4 以降が対象。CM0 では使えない | [公開出典一覧](../sources/sources.md) |
| tryboot | Raspberry Pi 文書は Pi 4 / 5 を主に扱うとし、CM0 では未検証 | 文書では全モデル対応と記載。CM0 実機での動作は未確認 | [公開出典一覧](../sources/sources.md) |
| `powerfail_suo` | 要約は SysRq-U のみと記載 | SysRq-U に加えてバックライト制御と GPIO 操作を行う | [公開出典一覧](../sources/sources.md) |
| ES8389 | compatible 値の記載なし | compatible は `everest,es8390` | [公開出典一覧](../sources/sources.md) |
| Rugix の Pi 3 対応 | 対応表では Pi 3 が `rpi-tryboot` とする | 【一次】（2026-10-19 確認）Pi 3 は Rugix では `rpi-uboot`（Tier 2）です。これは Rugix の target 制約であり、Raspberry Pi firmware 自体は全モデルで tryboot に対応します。CM0 で Rugix を使う場合は実験的な U-Boot flow が必要ですが、firmware 更新不可のため U-Boot 非採用の MSD 方針とは合いません。MSD 自身の tryboot 設計は影響を受けず、CM0 実機確認は継続します。 | https://rugix.org/docs/bakery/devices/<br>https://rugix.org/docs/bakery/devices/raspberry-pi<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91 |
| `align = 4M` と `kernel8.img` の gzip 再圧縮の状態 | ideas-overview.md に `align = 4M` は「未着手（origin/main 未反映）」、fastboot-ideas.md に gzip 再圧縮は「案・未検証」とあった | どちらも main に実装済みです。`align = 4M` は #19 で `genimage.cfg` に入り、CI が検査しています。gzip 再圧縮は #8 で `post-image.sh` に入り、展開結果を `cmp` で比べています。実機での効果は未確認です（2026-10-20 に main のコードで確認） | [genimage.cfg](../../../board/cardputerzero/genimage.cfg)、[post-image.sh](../../../board/cardputerzero/post-image.sh) |

## 2026-11-11 phase1-r2のT2/T1結果訂正

phase1-r2でT2 `manifest_ok`が不足した原因は、W2のack markerとrename/fsyncの順序差、fscrypt keyfileの非永続化、最後のW3 marker後に残る有効tailを扱わない判定にあった。raw値は[phase1-r2記録](../../experiments/2026-11-10-phase1-matrix-r2.md)に保持し、修正後の[phase1-r3再測定](../../experiments/2026-11-11-phase1-t2-rerun.md)ではT2全20構成がrecovered/manifest_okとも20/20となった。I2 T1の未完了結果もtimeout延長後の再試行で完了した。いずれもQEMUの結果であり、実SDのFTL・物理電源断は未確認である。
