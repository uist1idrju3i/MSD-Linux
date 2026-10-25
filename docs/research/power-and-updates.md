# 電源断耐性・A/B 更新

## 6. 電源遮断耐性

【一次】RPi Linux `rpi-6.18.y` は 2026-10-16 時点で 6.18.57 です（Makefile の SUBLEVEL=57）。参考値は mainline 7.3-rc7、stable 7.2.11 です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://www.kernel.org/releases.json

### 6.1 FS 比較

| FS/技術 | 確認済み事実 | 評価 | 出典URL |
|---|---|---|---|
| UBIFS | 生 NAND/MTD+UBI 向けで、microSD/eMMC では使えないとの情報は未確認です。 | 除外 | 未確認 |
| ext3 | `CONFIG_EXT3_FS` は 6.18 で削除され、ext4 ドライバが扱うとの情報は未確認です。 | 独立候補から除外 | 未確認 |
| ext4 | 既定は commit=5、data=ordered。data=journal は非推奨（2028-01 削除予定の記述は最新 docs と v7.3-rc7・rpi-7.3.y の ext4.rst にあり、v7.2・rpi-7.2.y・v6.18・rpi-6.18.y にはありません。版による差があります。） | 小さな RW データ領域向けの第一候補 | https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf<br>https://docs.kernel.org/admin-guide/ext4.html |
| btrfs | COW の安全性はデバイスの flush / atomic write に依存し、microSD 固有の保証は確認できていません（未確認）。 | 保留 | 未確認 |
| overlayfs | xattr と d_type が必要。workdir は upper と同じ FS に置く。bcm2711_defconfig で OVERLAY_FS=m | ro rootfs と組み合わせる | https://docs.kernel.org/filesystems/overlayfs.html<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1650<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| SquashFS | 圧縮方式 gzip/lzo/lz4/xz/zstd。bcm2711_defconfig で SQUASHFS=m(LZO/XZ/ZSTD=y) | ro rootfs の候補 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1671-L1675<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| EROFS | bcm2711_defconfig で EROFS_FS=m（ZIP_ZSTD=y）、DM_VERITY=m です。 | ro rootfs の候補です。`fsck.erofs` の有無と整合性確認の方法は未確認です。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1679-L1680<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L513<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| tmpfs | 既定サイズは RAM の 50% | overlayfs の upper 候補（RAM 512MB に注意） | https://docs.kernel.org/filesystems/tmpfs.html<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1663<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |
| Yocto read-only-rootfs | Wrynose 6.0 の LTS は 2030-04 まで、Scarthgap 5.0 は 2028-04 までとの情報があります。期間と Wrynose の資料は未確認です。 | Yocto での設定例は [ユーザー空間とセキュリティ](userspace-and-security.md) を参照してください。 | https://www.kernel.org/releases.json<br>https://docs.yoctoproject.org/releases.html |
| F2FS | bcm2711_defconfig で F2FS_FS=y。RPi 公式が電源断後の破損報告が多いと警告 | 保留 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641<br>https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf |

### 6.2 RPi 公式ホワイトペーパー
【一次】CM0 を含む Raspberry Pi の電断耐性に関する PDF は、本文に Release 2、Build date 07/08/2026 と記載され、ファイル名の `WP-3` とは版表記が異なります。https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003610-WP-3-Making%20a%20more%20resilient%20file%20system.pdf

- ext4 は `data=ordered` と `metadata_csum` を使います。
- SquashFS または EROFS の read-only rootfs と overlayfs、小さな RW 永続データ領域を分離する構成が記載されています。
- F2FS は警告対象です。
- `/boot`（FAT）を read-only にする推奨と、ファイル更新時の temp → fsync → rename は未確認です。

【推測・設計案】MBR を候補にします。BCM2837 の boot ROM が GPT を読めない可能性を考慮しますが、CM0 での GPT 対応は未確認です。overlayfs の upper と `/etc` などの可変設定は tmpfs に置き、永続設定と開発ログは p7 に保存する案です。電源断試験ログには pstore/ramoops の利用を検討します。https://docs.kernel.org/filesystems/overlayfs.html<br>https://docs.kernel.org/admin-guide/ramoops.html

### 6.3 powerfail_suo
Buildroot の package patch で `POWERFAIL=1` uevent を発行し、`sync_filesystem()` を `/`、`/boot`、`/data` に同期的に実行してから SysRq-U を呼び出します。mdev helper は `/dev/kmsg` に記録し、ユーザー空間の `sync` をバックグラウンドで実行します。パッチは `vendor/` を変更せず、`package/m5stack-cardputerzero/` に置きます。

【一次】上流 M5 ドライバでは `handle_sysrq('u')`（read-only 再マウント）のみが実行されます。`'i'` と `'s'` はコメントアウトされています。パッチは uevent と同期的な filesystem sync を追加してから U を実行します。同期 API は Linux 6.18 の `sync_filesystem()` を使用し、`fs/sync.c` の export と宣言を確認しました。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L93<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L74-L115

GPIO6 の立下りを 500 ms デバウンスして SysRq-U を実行します。バックライトを 0 にし、`disabled-gpios = <&m5ioe1 11 1>` も駆動します。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L289-L295<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/powerfail_suo.c#L108-L115

正常停止は追加していません。hold-up 時間を実機で測定し、電源が失われる前に停止を完了できるか確認してから判断します。

【推測】`<&m5ioe1 11 1>` が M5IOE1 の PYG12 に当たるかは、index + 1 が PYGn に対応すると仮定した推論です。公式 docs は PYG12=LCD_RST と記載しますが、このドライバが同端子を操作するかは実機または回路図で確認が必要です。https://docs.m5stack.com/en/CardputerZero

【一次】DT ノードは `cardputerzero-v5-overlay.dts` にありますが、`cardputerzero-v3-overlay.dts` にはありません。https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L100<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v3-overlay.dts#L90

【推測】このドライバはスイッチ操作の検知を想定しているようです。sync も poweroff もしないため、電池の突然の抜けや枯渇には対応できません。

### 6.4 microSD の FTL リスク
- 【未確認】microSD の FTL は書込み中の電源断で無関係なデータまで壊す可能性があるとの指摘があります（2014 年のメーリングリスト上の個人意見）。LWN、Bootlin、JEDEC の公開一次資料を探しましたが、その主張を裏付ける資料は特定できていません。
- 【推測】A/B の「書き込んでいない側のスロットは無傷」という前提は保証されません。更新中以外の書込みを極力なくし、産業用 SD を評価する方法が考えられます。

### 6.5 設計案（推測）
- SquashFS(または EROFS)の **ro rootfs**+ **overlayfs**(upper は tmpfs または zram)
- **小さな ext4 データパーティション**(data=ordered、metadata_csum、fsync+rename)
- **A/B** スロット、/boot(FAT)は ro(更新時だけ書込み)

### 6.6 追加質問 Q1:完全 read-only でも zram/zswap は使えるか
- 【一次】`bcm2711_defconfig` には `CONFIG_ZRAM=m`、`ZRAM_BACKEND_ZSTD=y`、`ZRAM_BACKEND_LZO=y`、`ZRAM_DEF_COMP_ZSTD=y`、`ZRAM_WRITEBACK=y`、`ZRAM_MULTI_COMP=y`、`CONFIG_ZSWAP=y`、`PREEMPT=y` が設定されています。また `CONFIG_ZRAM_BACKEND_LZ4=y` もあります。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L467-L473<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L86<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10
- `bcm2711_defconfig` では SQUASHFS=m、EROFS_FS=m、OVERLAY_FS=m、DM_VERITY=m、F2FS_FS=y、USB_RTL8152=m です。USB ID 0fe6:9900 は `r8152.c` の ID 表にありますが、SR9900A の実 ID が 0fe6:9900 かは未確認です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L1641-L1680<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L513<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L580<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/net/usb/r8152.c
- 【**推測**】 zram は RAM 上のブロックデバイスなので rootfs が ro でも使えます。ただし =m なので initramfs か rootfs にモジュールが要ります。
- 【**推測**】 zswap は swap 先が必要で、SD 上の swap は電源断耐性に反します。**zram swap を使うなら zswap(=y で組込済み)は実行時に無効化**します。

---

## 7. OTA / A-B

### 7.1 各ツールのバージョン
| ツール(何の版か) | 版(日付) | 確認度 | 出典URL |
|---|---|---|---|
| RAUC | v1.15.2（2026-03-27） | 一次（公式 releases API、2026-10-18 に公開資料で確認） | https://api.github.com/repos/rauc/rauc/releases/latest |
| SWUpdate | 2026.05.1（2026-06-22） | 一次（公式 releases API、2026-10-18 に公開資料で確認） | https://api.github.com/repos/sbabic/swupdate/releases/latest |
| Mender Client（製品版） | **6.1.0**。mender.io のブログで 2026-10-16 に紹介されたとの情報は未確認です。supported-releases は「Mender Client 6.1 / 2026-10 / Supported」と記載します。mender-convert の README には officially supported 構成として **`raspberrypi3_bookworm_64bit_config`（Raspberry Pi 3、Raspberry Pi OS Bookworm 64-bit）** があります。方式は U-Boot で、tryboot ではありません。CM0 の構成は一覧になく、動作は未確認です。 | 一次（supported-releases、README）、2026-10-18 に確認、ブログ日付は未確認 | https://docs.mender.io/release-information/supported-releases<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md |
| mender-convert | 5.1.0 の変更履歴（changelog 日付 2025-12-01、GitHub release 公開 2025-12-02T10:38:33Z = 2025-12-02 19:38 JST）は「Remove raspberrypi3 jobs (MEN-8947)」で、RPi 3 の CI ジョブを削除し、RPi 5 対応時に onboarding image を RPi 4 / RPi 5 に集約したものです。README の対応表には `raspberrypi3_bookworm_64bit_config` が残るため、CI ジョブの削除は同構成の削除を意味しません。最新は 5.3.0（changelog 日付 2026-09-30、GitHub release 公開 2026-10-01T12:54:27Z = 2026-10-01 21:54 JST。日付の基準が異なります）。README の Core configurations には RPi 3 の U-Boot 構成があり、CM0 構成はありません。 | 一次（公式 changelog、releases、README） | https://docs.mender.io/release-information/release-notes-changelog/mender-convert<br>https://github.com/mendersoftware/mender-convert/releases<br>https://github.com/mendersoftware/mender-convert<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md |
| Mender の Buildroot パッケージ | **3.5.3**（Buildroot 2026.08 の `package/mender/mender.mk`、2026-10-18 に公開資料で確認）。古い系列です。 | 一次 | https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7 |
| MCUboot | v2.4.0 | 未確認 | 出典URL未取得 |
| Rugix Ctrl | v1.3.0（2026-08-05） | 一次（公式 releases API、2026-10-18 に公開資料で確認。Bakery と Ctrl の区別は未確認） | https://api.github.com/repositories/642546697/releases |

### 7.2 RPi firmware の tryboot
- 【一次】公式資料には `tryboot`、`autoboot.txt`（`[all]` / `[tryboot]`）、`reboot "0 tryboot"`、`tryboot_a_b=1`、`os_prefix`、`boot_ramdisk` が記載されています。U-Boot を使わずに A/B を構成する仕組みです。https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60
- 【一次】Raspberry Pi の文書は tryboot を全モデル対応と記載しています。一方、`autoboot.txt` の注記は rpi-image-gen を案内しています。CM0（BCM2837）の SD 起動（bootcode.bin / start.elf）で実際に動作するかは未確認で、実機検証が必要です。https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc<br>https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L5-L60
- 【一次（フォーラム投稿）】2025-11-28 の RPi フォーラム投稿は、Pi 3 では `autoboot.txt` に加え空の `config.txt` も必要で、FAT12 は使えないと述べています。RPi エンジニアは Pi 3 以前の A/B では bootcode.bin がパーティション 1 のみで冗長性がないこと、OTA の注力が Pi 4 以降であることを述べています。CM0 への適用は未確認です。https://web.archive.org/web/20260218015810/https://forums.raspberrypi.com/viewtopic.php?t=394171
- 【未確認】「Pi 3 / Zero 2 は tryboot 非対応」とする検索要約には裏付けがありません。Ubuntu 25.10 以降の piboot-try が Zero 2 W 対応表にあるものの、autoboot 方式ではないとの情報も確認できていません。

### 7.3 RAUC（custom bootloader backend）
- 【未確認】custom backend は get-primary / set-primary / get-state / set-state を実装するとの情報があります。出典URLは特定できていません。
- 【未確認】Rtone の raspberrypi-firmware-rauc-bootloader-backend は tryboot 用ですが、試行回数カウンターがなく、primary が起動できない場合に他スロットへフォールバックしないとの情報があります。HAOS の `rpi-tryboot.sh` は RPi 5 向けとの情報もあります。出典URLは特定できていません。
- 【一次】RAUC の PR #1599「bootchooser: add Raspberry Pi firmware initial support」は、2026-10-18 に open（未マージ、merged=false）と確認されています。https://api.github.com/repos/rauc/rauc/pulls/1599<br>https://github.com/rauc/rauc/pull/1599
- 【一次】`meta-rauc-community` の公開ツリーには RPi 向けの U-Boot 方式があります。tryboot の実装がないとの検索結果は未確認です。https://github.com/rauc/meta-rauc-community/tree/4d666ae4956f1cfacbd1a844f2e1794cb7784e2a
- 【推測】自前の custom backend で試行カウンターとフォールバックを補う案があります。

### 7.4 SWUpdate / Mender / MCUboot / boot-mbr-switch
- 【未確認】SWUpdate に Raspberry Pi firmware（tryboot）用の bootloader 連携がなく、利用できるのは fake / EFI Boot Guard / U-Boot / GRUB との情報があります。`diskpart` は GPT / DOS を扱えるとの情報もあります。出典URLは特定できていません。
- 【一次】Buildroot の `package/mender` は Mender 3.5.3 です。Mender Client 6.1 は supported-releases で Supported（2026-10）とされ、mender-convert の公式構成には RPi 3（64-bit）の U-Boot 方式が含まれますが、CM0 自体の構成はありません。`meta-mender` の Yocto Wrynose 対応と `mender-mcu`（Zephyr 向け）の存在は未確認です。https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/mender/mender.mk#L7<br>https://docs.mender.io/release-information/supported-releases<br>https://raw.githubusercontent.com/mendersoftware/mender-convert/4b3f04a2afc0518d154b58d72febb0c6969cbabc/README.md
- 【推測】MCUboot は VideoCore 起動の最初段にはなれず、tryboot での切替が必要と考えられます。arm64 での実績は未確認です。
- 【未確認】boot-mbr-switch はブートローダー領域の A/B 用で、rootfs 用ではないとの情報があります。

### 7.5 Zephyr 案での OTA
- 【未確認】CM0 上で Zephyr を動かせるかは確認できていません。このため Zephyr 案の OTA が CM0 で成立するかも未確認です。MCUboot と Mender-MCU の組合せが存在するとの情報も未確認です。

### 7.6 rpi-image-gen の A/B レイアウト
【一次】rpi-image-gen の公開コード（commit d7616a2、2026-10-16）を Devin が 2026-10-18 に確認しました。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L42<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml

- `image/gpt/ab_userdata/image.yaml` は immutable GPT A/B レイアウトの `image-rota` layer（層バージョン 6.1.0）です。`X-Env-VarRequires-Valid: regex:^(cm4|pi4|cm5|pi5)$` は cm4 / pi4 / cm5 / pi5 のみを許可します。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L2-L11
- `preimage05-templates` は `tryboot_a_b=1` と `[tryboot]` を含む `autoboot.txt` を生成します。rootfs の既定は EROFS（`rootfs_type: erofs`、`-z zstd,3`）で、ext4 も選択でき、永続データ領域があります。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.d/hooks/preimage05-templates#L40-L44<br>https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/gpt/ab_userdata/image.yaml#L34-L41
- `device/` 層には Pi 3 と Zero 2 W が含まれますが、`image-rota` の許可クラスには含まれません。MBR の `image/mbr/simple_dual`（layer 名 `image-rpios`、ext4 / btrfs）は A/B 構成ではありません。https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/device<br>https://github.com/raspberrypi/rpi-image-gen/tree/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/image/mbr/simple_dual
- `config/trixie-minbase-ab.yaml` の例は `device: rpi5` です。https://github.com/raspberrypi/rpi-image-gen/blob/d7616a28bbb552db77cfd7bf90888f7a9ef22f33/config/trixie-minbase-ab.yaml
- 【一次】Issue #153 は BCM2837 に MBR が必要で `image-rota` は GPT と述べ、2026-02-18 に closed となっています。現行コードでは device class の制約を確認できます。https://api.github.com/repos/raspberrypi/rpi-image-gen/issues/153
- 【未確認】CM0（BCM2837）向けの公式 A/B 構成は確認できていません。同 layer の対応 device class は EEPROM 機種（Pi 4 / Pi 5 系）のみです。MBR + tryboot + RAUC custom は公式コードに裏付けられていない自前構成案です。
- 【未確認】Zero 2 W / Pi 3 で `image-rota` 相当を使った場合の挙動は未確認です。
- 【一次】rpi-image-gen の最新リリースは v2.8.0（2026-08-13）です。Devin が 2026-10-18 に公開資料で確認しました。https://api.github.com/repos/raspberrypi/rpi-image-gen/releases
- 【未確認】firmware の GPT 対応は 2020 年頃に追加されたとの情報がありますが、GPT + hybrid MBR の不具合とともに出典を特定できていません。
- 【未確認】CM0 での GPT の挙動は確認できていません。公式 A/B の GPT 例は EEPROM 機種のもので、BCM2837 の根拠にはなりません。
- 【推測】BCM2837 は ROM 由来の MBR を前提とする方が安全側と考えられます。ただし 6 パーティション構成は MBR のプライマリパーティション 4 つの上限を超えます。回避案として拡張パーティション、`os_prefix` でのスロット分離、スロットごとの `boot.img` への集約がありますが、いずれも未検証です。

### 7.7 関連する最新リリース
Devin が 2026-10-18 に公開資料で確認しました。

- 【一次】rpi-6.18.y は 6.18.57（2026-10-16、Makefile、HEAD 234188315）です。https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/Makefile#L2-L4<br>https://github.com/raspberrypi/linux/commit/234188315037848e5b07d65b85d38edc64095caa<br>https://www.kernel.org/releases.json
- 【一次】Buildroot 2026.08（2026-09-04、commit d5180309）の GCC 既定は 15.3.0 です。16.2.0 は選択可能な候補です。https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1<br>https://github.com/buildroot/buildroot/blob/d5180309b1b66ef3b8eaccca70ad69be8e0729a1/package/gcc/Config.in.host#L6
- 【一次】raspberrypi/linux の既定ブランチは rpi-6.18.y です。https://github.com/raspberrypi/linux/tree/rpi-6.18.y
- 【未確認】rpi-eeprom の 2026-05-13 の項目には A/B bootloader update の記載があり、2712（Pi 5 系）向けとの情報があります。「Pi 5 stable 2026-09-25」とする日付は確認できていません。2026-10-15 の更新と firmware 1.20260915 も CM0 とは無関係との情報です。2026-10-18 に API と release notes の HTTP 200 のみを確認し、内容は未確認です。https://api.github.com/repos/raspberrypi/rpi-eeprom/releases<br>https://raw.githubusercontent.com/raspberrypi/rpi-eeprom/master/firmware-2712/release-notes.md
- 【一次】Pi OS 2026-10-06 版は Debian 13、kernel 6.18.50 です。公式 release notes の 2026-10-06 項には `Linux kernel 6.18.50 - cff533aec2fa601846766b32ff57204e0a61bed7` とあり、Imager 一覧にも同日版があります。https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://downloads.raspberrypi.com/os_list_imagingutility_v4.json
- 【一次】kernel.org の LTS は 6.18.57（EOL 予定 2028-12）、stable は 7.2.11（2026-10-15）、mainline は 7.3-rc7 です。https://www.kernel.org/releases.json
- 【一次・一部未確認】raspberrypi/linux の `rpi-6.12.y` は 6.12.113、`rpi-7.2.y` は 7.2.11 との情報があります。`rpi-6.12.y` の HEAD SHA は branches API で確認でき、6.12.113 は kernel.org の longterm 値です。https://www.kernel.org/releases.json<br>https://api.github.com/repos/raspberrypi/linux/branches/rpi-6.12.y
- 【一次】Mender Client 6.1.0 は supported-releases で 2026-10 時点の Supported です。https://docs.mender.io/release-information/supported-releases

---

## 18. 失敗検知と自動復旧（A/B）

| 要素 | 事実(一次) | 出典URL | CM0 適合 |
|---|---|---|---|
| `autoboot.txt` + `tryboot` | `[tryboot]` フィルターと `tryboot_a_b=1` により、通常の config.txt / boot.img を使いながらパーティション単位で切り替えます。`reboot "0 tryboot"` で 1 回試行し、成功時は autoboot.txt を更新して確定します。再起動した場合は tryboot フラグが自動クリアされ、元のパーティションに戻るとの記載があります。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc#L36-L83 | BCM2837 / CM0 での動作は未確認です。CM0 は EEPROM を持たず SD の bootcode / start.elf で起動します。 |
| カーネルウォッチドッグのハンドオーバー | `kernel_watchdog_timeout` はブート時にハードウェアウォッチドッグを OS に引き渡し、OS が給餌しない場合にリセットします。`systemd` の `watchdog.open_timeout` を cmdline で設定します。`BOOT_WATCHDOG_TIMEOUT`（EEPROM）は Pi 4 / Pi 5 のみです。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L255 | EEPROM 設定は CM0 対象外です。`kernel_watchdog_*` が BCM2837 firmware で有効かは未確認です。 |
| `kernel_watchdog_partition` | カーネルウォッチドッグが発火した場合、リセット後に指定パーティションから起動します（自動フェイルオーバー）。 | https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L262-L271 | BCM2837 / CM0 での動作は未確認です。 |
| bcm2835 内蔵 WDT ドライバ | RPi Linux ツリーに `drivers/watchdog/bcm2835_wdt.c` があります。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c | ファイルの存在を確認しています。 |
| WDT ユーザー空間 API | `CONFIG_WATCHDOG_NOWAYOUT` / magic close により、ウォッチドッグデバイスを close しても停止しない設計が可能です。 | https://docs.kernel.org/watchdog/watchdog-api.html | 一次 |
| systemd との連携 | `RuntimeWatchdogSec` と `sd_notify` の WATCHDOG 通知が利用できます。 | https://www.freedesktop.org/software/systemd/man/latest/systemd-system.conf.html#RuntimeWatchdogSec=<br>https://man7.org/linux/man-pages/man3/sd_notify.3.html | 一次 |

### 18.1 人手の回復モードを設けない設計案（推測、未実装・未測定）
起動完了条件は未決です。LCD にプロンプトを表示してキー入力を受け付ける時点、PID 1 が完了マーカーを書く時点、または両方を使う案では判定条件が異なります。[起動時間の終点](boot-and-kernel.md)も参照してください。

1. **スロット:** A / B に加え、必要なら C を工場イメージとして設けます。回復モードとブートメニューは設けず、自動で前のスロットへ戻す案です。
2. **試行:** 新スロットを tryboot（または自前の試行フラグとカウンター）で 1〜N 回だけ起動します。選択した完了条件への到達とアプリの健全性確認を満たした場合に確定し、autoboot.txt を更新します。完了条件は未決です。
3. **失敗検知は 3 段です。** (a) カーネル panic は `panic=N` で再起動します（kernel-parameters に記載）。(b) hung にはウォッチドッグを使います。`kernel_watchdog_timeout` が CM0 で使えない場合に備え、init が `bcm2835_wdt` を直接 open して給餌する経路を用意する案です。(c) 起動後の機能不全は確定前の自己診断で検知します。判定条件が未決で、LCD / キー入力または PID 1 の完了マーカーを使う案があります。ヘッドレスでの判定は困難です。https://docs.kernel.org/admin-guide/kernel-parameters.html
4. **boot counter:** RW の小領域（別パーティション）に連番と CRC を 2 面書きします。N 回連続で完了条件に到達しなければ旧スロットを既定に戻します。確定時だけ書き込み、SD への書き込み回数を最小化する案です。
5. **電源断との整合:** 試行中の電断は未確定状態での再起動となり、最大 N 回の試行後に旧スロットへ戻す想定です。tryboot と再起動による復帰が BCM2837 で動くかは未確認で、必ず戻せるとは言えません。確定時に更新する FAT 上の autoboot.txt も電断で破損する可能性があります。
6. **弱点:** A/B 用 boot パーティション（FAT）は単一障害点です。更新を 1 セクター内に収める方法や検証用コピーを持つ方法は軽減案ですが、FAT 上での有効性は未検証です。firmware（start.elf / bootcode.bin）は A/B 化されないとの情報がありますが、裏付ける公開資料は未確認です。CM0 で firmware を A/B 化する公式手段も未確認です。
7. CM0 向けの公式 A/B 構成は確認できておらず、tryboot は BCM2837 で未検証です。最初の実機試験では tryboot と `kernel_watchdog_*` の動作を確認します。動作しない場合は、段数が増える U-Boot または RAUC custom backend を代替案として検討します。
8. **更新記録の原子性:** 更新物を一時ファイルへ書いて fsync し、rename 後に親ディレクトリも fsync する案です。tryboot=1、選択中のパーティション一致、インストール記録の検証がそろってから更新を確定します。FAT 上の更新動作と実装は未検証・未着手です。

### 現行 watchdog init script の動作

Raspberry Pi の文書は全モデルが `tryboot` を使えると説明しています。これは一度だけ alternate boot を選ぶ再起動ベースの仕組みで、OS が停止したことを自ら検知する機能ではありません。hang から戻すには watchdog による reset か人手の再起動が別に必要です。BCM2837/CM0 の実機での動作は未確認です。【一次】【未確認】[tryboot 文書](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)／[autoboot.txt の one-shot 手順](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/autoboot.adoc)

Raspberry Pi は `kernel_watchdog_timeout` を、ハードウェア watchdog を OS に引き渡す設定として説明しています。OS 側で watchdog を開いて給餌するサービスが必要であり、設定名やドライバーがあることだけでは CM0 でのリセットを証明しません。【一次】【未確認】[watchdog boot option](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271)

現在の [`S01msd-watchdog`](../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog) は `watchdog -T 15 -t 5 /dev/watchdog` を実行します。スクリプトにはアプリケーションの健全性判定やログ記録はありません。タイムアウト・給餌周期を含む実際のリセット動作、init script が起動時に実行されること、CM0 watchdog の挙動は実機で確認します。【一次】【未確認】[現行 init script](../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog)／[BCM2835 watchdog driver](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/drivers/watchdog/bcm2835_wdt.c)

QEMU 11.1.2 TCG の v3 では、commit `c01f6e7` の patch から build した QEMU で 6 mode × 5 回を実施しました。stop / kill9 の marker→reset 中央値は 14.528 秒、17.064 秒であり、reset 後 120 秒以内の second boot ready は各 5/5 回でした。reboot も restart message、reset、ready が各 5/5 回そろい、poweroff は QEMU が status 0 で 5/5 回終了しました。`TERM` は 5 試行とも 60 秒以内に reset せず、BusyBox が magic close `V` を使うという仮説と整合しますが、close の方式自体は確認できていません。v1 は観測窓が不足して基準未達でした。v2 の結果は commit されていない source から build した別 QEMU の参考値として残し、invalid とはしていません。これらは QEMU の結果であり、実機 watchdog の動作は未確認です。QEMU では GPU firmware / tryboot を使えず、watchdog reset 後の slot selection も検証できません。【実験】[S11 QEMU watchdog 実験](../experiments/2026-10-20-s11-qemu-watchdog.md)
