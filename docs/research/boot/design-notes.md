# 起動に関連する設計論点

[調査の索引](../../../RESEARCH.md) / [起動経路](sequence.md)

旧調査の分野横断の論点をまとめた記録です。採用済みの設定一覧ではありません。現在の回路・GPIO・BSPの確認範囲は[ハードウェア監査](../hardware-wiring-audit.md)、権限の具体設計は[セキュリティ設計](../security/README.md)、現行の更新操作は[更新手順](../../UPDATE.md)を参照してください。

以下は起動時間や電断耐性の検討項目です。公開根拠が不足している主張は未確認または推測として示します。

| 話題 | 内容・条件 |
|---|---|
| `config.txt` 最適化 | `boot_delay`、`disable_splash` などの候補があります。`disable_fw_kms_setup` 等が BCM2837 で有効かは未確認です。確認先: [Raspberry Pi 起動資料](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010196-WP-1-Optimising%20boot%20time%20on%20Raspberry%20Pi%20single-board%20computers.pdf) |
| DTB 最小化 | Pi 3 の単一ブログに実測例があるとの情報ですが、条件固有で、別機種の値とは合成できません。記事 URL を特定できていないため未確認です。確認先: https://furkantokac.com/ |
| initcall 非同期化・モジュール化 | カーネル初期化とモジュールのロードを分け、遅延ロードする案があります。`initcall_debug` で実機の時間を計測する必要があります。https://docs.kernel.org/admin-guide/kernel-parameters.html |
| initramfs 非同期展開 | `initramfs_async` は kernel parameter として文書化されています。mainline 化は 2021 年の `e7cb072eb988` です。Victron 由来とされる説明は古い可能性があります。https://docs.kernel.org/admin-guide/kernel-parameters.html<br>https://github.com/torvalds/linux/commit/e7cb072eb988 |
| GPU 読込とカーネルサイズ | サイズが読込時間に影響するとの見立ては推測で、比例関係は未確認です。KittenLabs は Zero 2 W の Raspbian 標準 kernel8.img（9,276,375 B）について、ログ時刻の差 1.54 s（計算値約 5.74 MiB/s、ブログ記載は約 6 MiB/s）を掲載しています。単一ブログの条件固有値です。https://kittenlabs.de/blog/2024/09/01/extreme-pi-boot-optimization/ |
| firmware の代替 | rpi-open-firmware、U-Boot Falcon などは候補ですが、CardputerZero での対応状況は未確認です。https://github.com/search?q=rpi-open-firmware&type=repositories<br>https://github.com/CardputerZero/u-boot |
| LCD の先行点灯 | 起動完了条件に画面表示を含める場合は早期ロードが必要です。含めない場合は M5IOE1 → backlight → LCD の依存を保ったまま遅延ロードする案があります（推測）。 |
| init・rootfs・ユーザー空間 | init 直起動、s6 / runit、EROFS（LZ4）と配置最適化、静的リンク / LTO / UPX、network の遅延起動や readahead は個別に検討します。[ユーザー空間とセキュリティ](../userspace-and-security.md) |
| 電断検知 | 公式 docs の SW_DET = G6 と M5 overlay の `irq-gpios = <&gpio 6 0>`（falling）は、同じ GPIO6 で矛盾しません。GPIO6 は CM0 側の SW_DET です。M5IOE1 側の PYG6 は MIC_SW で別信号です。`disabled-gpios = <&m5ioe1 11 1>` が PYG12（LCD_RST）に当たるかは index + 1 の推論で未確認です。https://docs.m5stack.com/en/CardputerZero<br>https://github.com/m5stack/m5stack-linux-dtoverlays/blob/75518549a2640486f5d13ea72ca4935b198d7c20/modules/CardputerZero/cardputerzero-v5-overlay.dts#L289-L295 |
| 書込み量と原子性 | rootfs を read-only にして書込みを最小化する案、ext4 `data=ordered`、更新時の atomic write が検討対象です。[電源と更新](../power-and-updates.md) |
| 電源喪失保護付き SD | UCSD の DAC 2011 論文などに PLP 付きストレージの記述があります。pSLC は eMMC 向けで microSD には適用できないとの情報があり、ベンダー主張は未検証です。[公開出典一覧](../sources.md) |
| dm-verity | QEMU で rootfs の改ざん拒否を確認した。CM0 の SHA 命令、実機性能、A/B 切替時だけ全検証する案は未確認である（[QEMU 記録](../../experiments/2026-10-21-qemu-dm-verity.md)）。確認先: https://developer.arm.com/documentation/ddi0500/latest/ |
| watchdog と復旧 | WDT、boot counter、最小復旧イメージは候補です。復旧方式は未決です。[電源と更新](../power-and-updates.md) |
| 電断試験 | `dm-flakey`、`dm-log-writes`、CrashMonkey などの障害注入が候補です。これらは実カードの FTL や実際の電源遮断を再現しません。[公開出典一覧](../sources.md) |
| スーパーキャパシタ | 筐体内に搭載するのは難しいとの見立てですが、寸法・電力条件の確認は未実施です（推測）。 |
