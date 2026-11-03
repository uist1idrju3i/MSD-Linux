# 電源遮断耐性とFTL・filesystemの調査

[保存領域の入口へ戻る](README.md) / [調査の索引](../../../RESEARCH.md)

以下は電源遮断・filesystem・FTL・powerfailの公開資料と、当時の案をまとめた本文です。実microSDの電源断試験を行った結果ではありません。A/B方式の当時の比較は[設計履歴](ab-design-history.md)、回復の案とS11は[復旧とwatchdog](recovery-and-watchdog.md)、現行コードは[保存領域の入口](README.md#現在の実装とまだ確かめていないこと)へ分けます。

現在のfilesystem・更新方式の比較は[保存領域](../alternatives/filesystems.md)、[更新framework](../alternatives/updates.md)、[TUF・Uptane](../alternatives/update-metadata.md)にまとめています。以下の版情報・未確認事項は主に2026-10-18の調査記録であり、現行採用版・最新状態と混同しません。firmwareと電源断、S10の経緯はこの文書に残します。

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
| Yocto read-only-rootfs | Wrynose 6.0 の LTS は 2030-04 まで、Scarthgap 5.0 は 2028-04 までとの情報があります。期間と Wrynose の資料は未確認です。 | Yocto での設定例は [ユーザー空間とセキュリティ](../userspace/README.md) を参照してください。 | https://www.kernel.org/releases.json<br>https://docs.yoctoproject.org/releases.html |
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
