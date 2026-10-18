# 電源断耐性・A/B 更新

## 6. 電源遮断耐性

基準:【**確認済み**】 rpi-6.18.y 6.18.57(2026-10-16、Makefile の SUBLEVEL=57)。参考として mainline 7.3-rc7(【**報告**】)/stable 7.2.11。

### 6.1 FS 比較

| FS/技術 | 確認済み事実 | 評価 | 出典URL |
|---|---|---|---|
| UBIFS | 生 NAND/MTD+UBI 専用で microSD/eMMC では使えない | 除外 | URL未取得 |
| ext3 | CONFIG_EXT3_FS は 6.18 で削除され、ext4 ドライバが扱う | 独立候補から除外 | URL未取得(6.18 での削除は v2 の旧確認。今回 URL 未取得) |
| ext4 | 既定は commit=5、data=ordered。data=journal は非推奨(2028-01 削除予定の記述は**最新 docs と v7.3-rc7・rpi-7.3.y の ext4.rst にあり、v7.2・rpi-7.2.y・v6.18・rpi-6.18.y には無い**=6.1 の注) | 小さな RW データ領域向けの第一候補 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf<br>https://docs.kernel.org/admin-guide/ext4.html |
| btrfs | COW の安全性はデバイスの flush/atomic write に依存。microSD 固有の保証は見つからない | 保留 | URL未取得 |
| overlayfs | xattr と d_type が必要。workdir は upper と同じ FS に置く。bcm2711_defconfig で OVERLAY_FS=m | ro rootfs と組み合わせる | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1650<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| SquashFS | 圧縮方式 gzip/lzo/lz4/xz/zstd。bcm2711_defconfig で SQUASHFS=m(LZO/XZ/ZSTD=y) | ro rootfs の候補 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1671-L1675<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| EROFS | bcm2711_defconfig で EROFS_FS=m(ZIP_ZSTD=y)、DM_VERITY=m | ro rootfs の候補。fsck.erofs 無し(整合性は dm-verity 等、報告) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1679-L1680<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L513<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| tmpfs | 既定サイズは RAM の 50% | overlayfs の upper 候補(RAM 512MB に注意) | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1663<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| Yocto read-only-rootfs | Yocto の LTS は Wrynose 6.0(2030-04 まで、報告)と Scarthgap 5.0(2028-04 まで)。Wrynose 版の docs は docs.yoctoproject.org で取得可能と監査報告(私は未再確認) | 3 章参照 | https://www.kernel.org/releases.json<br>Yocto LTS 期間・docs: URL未取得 |
| F2FS | bcm2711_defconfig で F2FS_FS=y。RPi 公式が電源断後の破損報告が多いと警告 | 保留 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |

### 6.2 RPi 公式ホワイトペーパー RP-003610-WP-3(2026-08、CM0 を含む。v3 注:取得した PDF の本文は『Release 2、Build date 07/08/2026』で、ファイル名の WP-3 と版表記が一致しない)
- 【**確認済み(一部)**】(v3:PDF 本文を再確認。『temp→fsync→rename』の記述は未再確認)推奨内容(出典: https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf(今回 PDF 本文を確認:data=ordered/metadata_csum/SquashFS・EROFS+overlayfs/F2FS。『/boot(FAT)は ro 推奨』『temp→fsync→rename』は未再確認))
  - ext4 は data=ordered と metadata_csum
  - ファイル更新は temp → fsync → rename
  - SquashFS または EROFS の ro rootfs+overlayfs
  - 永続データは小さな RW パーティションに分離
  - F2FS は警告対象、/boot(FAT)は ro 推奨

### 6.3 powerfail_suo(M5 ドライバ)
- 【**確認済み**】(`modules/CardputerZero/powerfail_suo.c`、m5stack-linux-dtoverlays HEAD 7551854、2026-09-23、grep 2026-10-18)(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93)
  - **実行されるのは `handle_sysrq('u')`(ro 再マウント)のみ**(93 行)。`'i'`(74 行)と `'s'`(83 行)はコメントアウト。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93)
  - ファイル冒頭コメントと MODULE_DESCRIPTION は「S→U→O」だが、実装は U のみ(コメントと実装が不一致)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93)
  - 流れ:GPIO6 の立下り(overlay L292-293)→ 500ms デバウンス(overlay L290)→ 'u'。あわせてバックライトを 0 にし(powerfail_suo.c L108-110)、`disabled-gpios = <&m5ioe1 11 1>` を駆動する(同 L113-115、overlay L295)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L108-L115)
  - 【**推測**】 `<&m5ioe1 11 1>` が M5IOE1 の PYG12 に当たる(index+1=PYGn と仮定した推論)。「PYG12=LCD_RST」自体は公式 docs の記載(https://docs.m5stack.com/en/CardputerZero、v6 で本文再取得)だが、powerfail_suo がその端子を操作するかは index の対応を実機・回路図で確認していない。
- 【**報告による・未確認**】 この DT ノードは v5 overlay のみ(v3 には無い)。(出典: https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100(v3 に無いことは https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90 の grep で確認))
- 【**推測**】 スイッチ操作の検知を想定した設計と読めます。**sync も poweroff もしないため、電池の突然の抜けや枯渇は救えません。**

### 6.4 microSD の FTL リスク
- 【**報告による**】 microSD の FTL は書込み中の電源断で無関係なデータまで壊す可能性がある(2014 年のメーリングリストでの個人意見)。LWN/Bootlin/JEDEC の一次資料は**今回も取得していません(【未確認】)**。(出典なし)
- 【**推測**】 そのため A/B の「書き込んでいない側のスロットは無傷」という前提は**保証されません**。更新中以外の書込みを極力なくす、産業用 SD を評価する、などが考えられます。

### 6.5 推奨構成(**【作成者の見立て】設計案**)
- SquashFS(または EROFS)の **ro rootfs**+ **overlayfs**(upper は tmpfs または zram)
- **小さな ext4 データパーティション**(data=ordered、metadata_csum、fsync+rename)
- **A/B** スロット、/boot(FAT)は ro(更新時だけ書込み)

### 6.6 追加質問 Q1:完全 read-only でも zram/zswap は使えるか
- 【**確認済み**】(rpi-6.18.y 234188315、2026-10-16、`bcm2711_defconfig`)`CONFIG_ZRAM=m`、`ZRAM_BACKEND_ZSTD=y`、`ZRAM_BACKEND_LZO=y`、`ZRAM_DEF_COMP_ZSTD=y`、`ZRAM_WRITEBACK=y`、`ZRAM_MULTI_COMP=y`、**`CONFIG_ZSWAP=y`**、`PREEMPT=y`。**v3 訂正:`CONFIG_ZRAM_BACKEND_LZ4=y` も存在します(bcm2711_defconfig L468)。** v2 の『LZ4 の行は見つからなかった』は、grep の正規表現が数字を含まず取りこぼしたための誤りでした(監査報告が正しい)。(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10)
- 同 defconfig で SQUASHFS=m、EROFS_FS=m、OVERLAY_FS=m、DM_VERITY=m、F2FS_FS=y。【**一次**】 USB ID 0fe6:9900 は `r8152.c` の表にある(14.3)。USB_RTL8152=m。SR9900A の実 ID が 0fe6:9900 かは**未確認**。(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641-L1680<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L513<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L580)
- 【**推測**】 zram は RAM 上のブロックデバイスなので rootfs が ro でも使えます。ただし =m なので initramfs か rootfs にモジュールが要ります。
- 【**推測**】 zswap は swap 先が必要で、SD 上の swap は電源断耐性に反します。**zram swap を使うなら zswap(=y で組込済み)は実行時に無効化**します。

---

## 7. OTA / A-B

### 7.1 各ツールの版
| ツール(何の版か) | 版(日付) | 確認度 | 出典URL |
|---|---|---|---|
| RAUC | v1.15.2(2026-03-27) | 確認済み(API GET、2026-10-18。v3 で格上げ) | https://api.github.com/repos/rauc/rauc/releases/latest |
| SWUpdate | 2026.05.1(2026-06-22) | 確認済み(API GET、2026-10-18。v3 で格上げ) | https://api.github.com/repos/sbabic/swupdate/releases/latest |
| Mender Client(製品版) | **6.1.0**(mender.io ブログ 2026-10-16)。docs.mender.io の supported-releases は「Mender Client 6.1 / 2026-10 / Supported」。mender-convert の README(4b3f04a)は officially supported 構成に **`raspberrypi3_bookworm_64bit_config`(RaspberryPi 3, Raspberry Pi OS bookworm 64bit)** を載せる。**方式は U-Boot(tryboot ではない)。CM0 そのものの構成は一覧に無く、動作は未確認** | 一次(supported-releases・README。ブログは v5 で到達のみ確認) | https://docs.mender.io/release-information/supported-releases<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md |
| mender-convert | **v4 訂正**:5.1.0(changelog 日付 2025-12-01、GitHub release 公開 2025-12-02T10:38:33Z = 2025-12-02 19:38 JST)の変更履歴は「Remove raspberrypi3 jobs (MEN-8947)」=**RPi3 の CI ジョブを削除**(RPi5 対応で onboarding image を RPi4/RPi5 に集約)。設定は README の対応表(raspberrypi3_bookworm_64bit_config)に残る。「RPi3 を削除/完全に対象外」は誤り。最新は 5.3.0(changelog 日付 2026-09-30、GitHub release の公開 2026-10-01T12:54:27Z = 2026-10-01 21:54 JST。日付の基準が異なる)。v5 で README(4b3f04a)の Core configurations に RPi3 の U-Boot 構成を確認(CM0 の構成は無い) | 確認済み・一次(公式 changelog。libc 調査資料より) | https://docs.mender.io/release-information/release-notes-changelog/mender-convert / https://github.com/mendersoftware/mender-convert/releases / https://github.com/mendersoftware/mender-convert |
| Mender の Buildroot パッケージ | **3.5.3**(Buildroot 2026.08 の `package/mender/mender.mk`、2026-10-18 確認)。古い系列 | 確認済み | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 |
| MCUboot | v2.4.0 | 報告による・未確認 | URL未取得 |
| Rugix Ctrl | v1.3.0(2026-08-05) | 確認済み(リリース一覧 API、2026-10-18。v3 で格上げ。Bakery/Ctrl の別を区別していない) | https://api.github.com/repositories/642546697/releases |

### 7.2 RPi firmware の tryboot
- 【**確認済み**】 公式 docs(raspberrypi/documentation)に tryboot と autoboot.txt([all]/[tryboot]、reboot '0 tryboot'、tryboot_a_b=1、os_prefix、boot_ramdisk)の記載があります。U-Boot 無しで A/B を構成できる仕組みです。(出典: https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60)
- 【**確認済み・注意**】 「全モデル対応」の記述は **EEPROM 起動の文書(bootflow-eeprom.adoc)にあり**、autoboot.txt の注記は rpi-image-gen を指します(監査報告)。BCM2837 の SD 起動(bootcode.bin/start.elf)で動く根拠にはなりません。(出典: https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60)
- 【**未確認**】 **BCM2837(CM0)での tryboot 動作**は一次資料で確認できません。実機検証が必須です。「Pi 3/Zero 2 は非対応」という検索要約の主張にも裏付けはありません。**v4 追記**:RPi フォーラム t=394171「tryboot on Pi3: Some observations」(Wayback 20260218015810 経由で取得)では、Pi 3 は autoboot.txt に加え空の config.txt も必要、FAT12 不可、RPi エンジニアは「Pi3 以前の A/B では bootcode.bin はパーティション 1 にのみ存在し冗長性は無い」「OTA の注力は Pi4 以降」と発言(2025-11-28)。**CM0 への適用は推測**(https://web.archive.org/web/20260218015810/https://forums.raspberrypi.com/viewtopic.php?t=394171)。
- 【**報告による**】 Pi 3 以前は bootcode.bin を冗長化できない(RPi フォーラム t=394171 のスニペットのみ。フォーラムは接続不可で本文を読めていない)。(出典なし。13.2 N6 に Wayback の URL があるが、CM0 への適用は推測)
- 【**報告による**】 Ubuntu 25.10+ の piboot-try は Zero 2 W 対応表にあるが autoboot 方式ではない(検索要約)。(出典なし)

### 7.3 RAUC(bootloader=custom)
- 【**報告による・未確認**】 custom バックエンドは get-primary/set-primary/get-state/set-state を実装する。(出典: URL未取得(RAUC docs/ローカル clone /workspace/r/rauc を grep していない))
- 【**報告による・未確認**】 Rtone の raspberrypi-firmware-rauc-bootloader-backend は tryboot 用だが、試行回数カウンタが無く、primary が起動できないとき他スロットへフォールバックしない。HAOS の rpi-tryboot.sh は RPi5 向け。(出典: URL未取得)
- 【**確認済み**】(GitHub API GET、2026-10-18)RAUC の **PR #1599「bootchooser: add Raspberry Pi firmware initial support」は open(未マージ)** です(merged=false)。旧 U7 は解消。(出典: https://api.github.com/repos/rauc/rauc/pulls/1599<br>https://github.com/rauc/rauc/pull/1599)
- 【**報告による・未確認**】 meta-rauc-community の RPi 対応は U-Boot 方式で、tryboot の grep は 0 件。(出典: https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a)
- 【**推測**】 自前の custom バックエンドで試行カウンタとフォールバックを補う必要があります。

### 7.4 SWUpdate / Mender / MCUboot / boot-mbr-switch
- 【**報告による・未確認**】 SWUpdate には RPi firmware(tryboot)用の bootloader 連携が無い(fake/EFI Boot Guard/U-Boot/GRUB)。diskpart で gpt/dos を扱える。(出典: URL未取得)
- 【**確認済み**】 Mender の Buildroot 統合(`package/mender`)は 3.5.3 の古い系列(7.1 節)。【**一次**】 Mender Client 6.1 は supported-releases で Supported(2026-10)、mender-convert は RPi3(64bit)を U-Boot 方式の公式構成に含む(CM0 自体の構成は無い=未確認)。meta-mender の Yocto Wrynose 対応と mender-mcu(Zephyr 向け)は存在する(監査報告)。(出典: https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 / https://docs.mender.io/release-information/supported-releases)
- 【**推測**】 MCUboot は VideoCore 起動では最初段になれず、tryboot での切替が結局必要。arm64 での実績は【**未確認**】。
- 【**報告による・未確認**】 boot-mbr-switch はブートローダ領域の A/B 用で rootfs 用ではない。

### 7.5 Zephyr 案での OTA
- 【**推測**】 Zephyr は CM0 で動かない(3 章)ため、Zephyr 案の OTA は CM0 上では成立しません。なお MCUboot+Mender-MCU の組合せ自体は存在します(監査報告)が、CM0 では前提の Zephyr が動きません。

### 7.6 公式 A/B(rpi-image-gen の image-rota)と MBR/GPT
- 【**確認済み**】(raspberrypi/rpi-image-gen master d7616a2、2026-10-16。`/tmp/rig` の clone を 2026-10-18 に grep/読取り)(出典: https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L42<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml)
  - `image/gpt/ab_userdata/image.yaml`:レイヤ名 **image-rota**(Immutable **GPT** A/B レイアウト、層バージョン 6.1.0)。`X-Env-VarRequires-Valid: regex:^(cm4|pi4|cm5|pi5)$` で **デバイスクラスは cm4/pi4/cm5/pi5 のみ**。(出典: https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11)
  - 同 `image.d/hooks/preimage05-templates` が autoboot.txt を生成(`tryboot_a_b=1`、[tryboot] あり)。rootfs は既定 EROFS(image.yaml L34 `rootfs_type: erofs`、`-z zstd,3` は image.yaml L41。autoboot.txt 生成は hook の L40・`tryboot_a_b=1` は L42・`[tryboot]` は L44)、ext4 も選択可、persistent データ領域あり。(出典: https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L44<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L34-L41)
  - device 層(`device/`)に **pi3 と zero2w があるが、image-rota はこれらを受け付けない**。MBR レイアウトは `image/mbr/simple_dual`(layer 名 image-rpios、ext4/btrfs)で、これは A/B ではない。(出典: https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual)
  - 例設定 `config/trixie-minbase-ab.yaml` は `device: rpi5`。(出典: https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml)
  - 旧版が参照した「issue #153: BCM2837 は MBR 要で image-rota は GPT」は issue が closed(2026-02-18)で古い可能性があったが、**現行 master で上記の制約が直接確認できた**ため、issue ではなくコードを根拠にします。(出典: https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153)
- 【**結論(確認済み事実に基づく)**】 **CM0(BCM2837)向けの公式 A/B 構成は存在しません**。image-rota は EEPROM 機種(Pi4/5 系)専用です。したがって本レポートの推奨(MBR+tryboot+RAUC custom)は**公式の裏付けがない自前構成** です。
- 【**未確認**】 zero2w/pi3 で image-rota 相当を無理に通した場合の挙動(ビルド禁止のため未実施)。
- 【**確認済み**】(API GET、2026-10-18。v3 で格上げ)rpi-image-gen 最新リリース **v2.8.0(2026-08-13)**。ローカル clone は浅くタグを持たない。(出典: https://api.github.com/repos/raspberrypi/rpi-image-gen/releases(今回 API で確認済みに格上げ))
- 【**報告による**】 GPT と MBR:firmware の GPT 対応は 2020 年頃に追加された。ただし GPT+hybrid MBR で不具合の報告あり(旧版の記述)。(出典なし。ユーザーの GPT/MBR の問いは R26)
- 【**未確認**】 CM0 での GPT の挙動(公式 A/B の GPT 例は EEPROM 機種限定のため、BCM2837 の根拠にならない)。
- 【**作成者の見立て**】 BCM2837 は ROM 由来の MBR 前提が安全側。ただし 6 パーティション構成の公式 A/B 例は MBR のプライマリ 4 つの上限を超える。回避案(未検証):拡張パーティション、os_prefix でスロットを分ける、スロットごとの boot.img にまとめる、など。

### 7.7 関連する最新リリース
- 【**確認済み**】
  - rpi-6.18.y:**6.18.57**(2026-10-16、`Makefile` と HEAD 234188315)(出典: https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://www.kernel.org/releases.json)
  - Buildroot 2026.08(2026-09-04、d5180309):**GCC 既定は 15.3.0**(旧版の「GCC 16.2.0」は誤り。16.2.0 は選択式)(出典: https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6)
  - raspberrypi/linux ブランチ rpi-6.18.y(default)(出典: https://github.com/raspberrypi/linux/tree/rpi-6.18.y)
- 【**報告による・未確認**】
  - rpi-eeprom:**A/B ブートローダ更新の記載は 2026-05-13 のエントリ(2712=Pi5 系)** で、CM0 には無関係(旧版の「Pi5 stable 2026-09-25」は誤り)。2026-10-15 の更新とファーム 1.20260915 も CM0 無関係(出典: https://api.github.com/repos/raspberrypi/rpi-eeprom/releases (HTTP 200 のみ確認。内容は未読。raw: https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md も HTTP 200 のみ))
  - 【**確認済み**】 Pi OS 2026-10-06 版:Debian 13、kernel 6.18.50(公式 `release_notes.txt` の 2026-10-06 の項 L38「Linux kernel 6.18.50 - cff533aec2fa601846766b32ff57204e0a61bed7」。v9 で取得)(出典: https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json(Imager 一覧に 2026-10-06 版あり))
  - kernel.org:LTS 6.18.57(EOL 予定 2028-12)、stable **7.2.11(2026-10-15)**、mainline 7.3-rc7(出典: https://www.kernel.org/releases.json)
  - raspberrypi/linux:rpi-6.12.y(6.12.113)、rpi-7.2.y(7.2.11)(出典: https://www.kernel.org/releases.json(rpi-6.12.y の HEAD sha は API で確認可能: https://api.github.com/repos/raspberrypi/linux/branches/rpi-6.12.y 。6.12.113 は kernel.org の longterm 値))
  - Mender Client 6.1.0(7.1 節)

---

## 18. 失敗検知と自動復旧(A/B)(提案 5)

> 11 章との対応: 11.1(A/B)、11.3 D4(11.5 に対応表)

| 要素 | 事実(一次) | 出典URL | CM0 適合 |
|---|---|---|---|
| `autoboot.txt` + `tryboot` | `[tryboot]` フィルタ、`tryboot_a_b=1` で通常の config.txt/boot.img を使いつつパーティション単位で切替。`reboot "0 tryboot"` で 1 回だけ試行し、成功なら autoboot.txt を更新して確定、失敗(再起動)なら tryboot フラグが自動クリアされ元のパーティションに戻る(RPi 文書の記述。CM0 で成り立つかは未検証) | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83 | **BCM2837 で動くかは未確認**(v3 7.2 節と同じ。CM0 は EEPROM を持たず SD の bootcode/start.elf で起動) |
| カーネルウォッチドッグのハンドオーバー | `kernel_watchdog_timeout`:ブート時にハードウェアウォッチドッグを OS に引き渡し、OS が給餌しないとリセット。`systemd` の `watchdog.open_timeout` を cmdline で設定。`BOOT_WATCHDOG_TIMEOUT`(EEPROM)は **Pi 4/5 のみ** | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L255 | EEPROM 設定は CM0 対象外。`kernel_watchdog_*` が BCM2837 ファームで有効かは**未確認** |
| `kernel_watchdog_partition` | カーネルウォッチドッグが発火したら、リセット後に指定パーティションから起動(自動フェイルオーバー) | 同 boot.adoc#L262-L271 | 同上(未確認) |
| bcm2835 内蔵 WDT ドライバ | `drivers/watchdog/bcm2835_wdt.c` が RPi ツリーに存在 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c | 存在のみ確認 |
| WDT ユーザー空間 API | `CONFIG_WATCHDOG_NOWAYOUT` / magic close:ウォッチドッグデバイスを close しても止めない設計が可能 | https://docs.kernel.org/watchdog/watchdog-api.html | 一次 |
| systemd との連携 | `RuntimeWatchdogSec`(RPi doc が参照)、`sd_notify` の WATCHDOG | https://man7.org/linux/man-pages/man3/sd_notify.3.html | 一次 |

### 18.1 「人手の回復モードなし」の設計案(【作成者の見立て=推測、未実装・未測定】)
> **D1(15.1 の終点の定義)が未決**のため、以下で「終点」を使う判定は全て **D1 が決まるまで保留** です(終点の判定条件は案 A/B/C で異なる。11.3 D1)。
1. **スロット**:A/B(+必要なら C=工場イメージ)。回復モード・ブートメニューは作らない(ユーザー要件)。復旧は「自動で前のスロットへ戻る」のみ。
2. **試行**:新スロットは tryboot(または自前の試行フラグ+カウンタ)で 1〜N 回だけ起動。「選択された終点に到達+アプリの健全性確認」で初めて「確定」(autoboot.txt 更新)。**終点の判定は D1 が決まるまで保留**(15.1 の案 A なら E1、案 B なら終点マーカー、案 C なら両方。E1 は案 A 専用の判定)。
3. **失敗検知は 3 段**:(a) カーネル panic → `panic=` で再起動(`panic=N` は kernel-parameters に記載)、(b) hung → ウォッチドッグ(`kernel_watchdog_timeout` が CM0 で効かない場合に備え、カーネル側 `bcm2835_wdt` を init が直接 open して給餌する自前経路を用意)、(c) 起動はしたが機能不全 → 確定前の自己診断(**判定基準は D1 が決まるまで保留**。案 A なら LCD/キー入力が来るか、案 B なら PID1 が一定時間内に終点マーカーを書いたか。ヘッドレス判定は困難)。
4. **boot counter**:RW の小領域(別パーティション)に連番+CRC の 2 面書き(P-4 のアイデア)。N 回連続で(D1 が決まるまで保留の)終点判定に未達なら旧スロットを既定へ戻す。**SD 書込み回数を最小化**(確定時のみ)。
5. **電源断との整合**:試行中の電断は「未確定のまま再起動」=最大 N 回で旧スロット復帰となる(要試験。tryboot と再起動での復帰が BCM2837 で効くかは未検証のため、「必ず前の面に戻せる」とは言えない)。確定の書込み(autoboot.txt 等 FAT)が電断で壊れうるリスクは v3 6 章の FAT 警告参照。
6. **弱点**:A/B を実現する boot パーティション(FAT)自体が単一障害点。ファームウェア(start.elf/bootcode.bin)は A/B 化されない(RPi 側の仕様。**A/B 化の公式手段は CM0 では未確認**)。
7. 【報告による】CM0 向けの公式 A/B は見つかっておらず(否定。範囲は 7.1・7.6 の調査)、tryboot は BCM2837 で未検証(v3 7.6)。よって**最初の実機試験は「tryboot が効くか」と「`kernel_watchdog_*` が効くか」**。効かない場合のフォールバック:U-Boot(段が増える)または RAUC custom(v3 7.3)。
