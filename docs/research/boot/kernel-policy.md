# カーネルの生成と比較の方針

[調査の索引](../../../RESEARCH.md) / [カーネル比較](kernel-comparison.md)

## 現行の生成処理

[post-image.sh](../../../board/cardputerzero/post-image.sh)は、`Image`を`pigz -11 -n`で`kernel8.img`に圧縮し、`gunzip`後に元の`Image`と`cmp`で照合します。実サイズはbuild logの`Kernel compression sizes`行に記録します。firmwareによる展開と実機の起動時間を検証したという意味ではありません。

カーネルの固定値は[defconfig](../../../configs/msd_cardputerzero_defconfig)を参照します。[製品fragment](../../../board/cardputerzero/linux.fragment)は`CONFIG_PREEMPT=y`と`CONFIG_PREEMPT_RT=y`を指定します。生成後の有効値は最終`.config`とbuild logで確認します。

## 過去の方針メモ

以下は、2026年10月の公開資料と当時の方針を記録した本文です。「PREEMPT_RTは対象外」などの記述は現行の製品設定ではありません。版別のAPI・PREEMPT・alias unmapの出典と確認範囲は[比較の詳細](kernel-comparison.md)を、採用方針の訂正は[訂正記録](../history/corrections.md)を参照してください。

- `kernel8.img` は `pigz -11 -n` で作成し、gunzip 後に `Image` と一致することを検査する。実サイズはビルドログの `Kernel compression sizes` 行に記録する。この文書では未測定値を記載しない。
- 基準は `rpi-6.18.y` とします。RPi kernel 6.18.57（2026-10-25 に 6.18.58 へ更新）、Buildroot 2026.08 の 2026-09-04 版を公開情報で確認しました。カーネルと M5 driver は commit 固定します。
- M5 DRM panel API が 7.1 で削除され、7.0 で ASoC API が変更されたとの情報は未確認です。確認には M5 driver と Raspberry Pi kernel の公開 tree をバージョンごとに比較する必要があります。M5 driver をそのまま build できるかは未確認です。6.18 を基準、7.2 は同一構成での比較候補とします。
- 6.18 から 7.2 で BCM2835 SD host / KASLR / 圧縮展開コードの変更がないとの調査。ただし BCM2837 の実測差はない。6.18 以降の起動時間に関係しそうな公開変更は条件付き、未マージ、または x86 / 大容量向けで、CM0 に適用できる証拠は乏しい。
- 6.18 arm64 は PREEMPT_NONE が既定で VOLUNTARY 選択可能との調査。7.2 では arm64 の PREEMPT_LAZY 機能により NONE / VOLUNTARY を選べないとの調査。起動時間への影響は未測定。PREEMPT_RT は対象外。
- 7.3 系で arm64 linear alias unmap の変更が再適用されたとの情報は、公開 commit history を確認できていないため未確認です。再適用後の Raspberry Pi 3 / CM0 起動も未確認です。確認先は [Raspberry Pi Linux 7.3.y source tree](https://github.com/raspberrypi/linux/tree/rpi-7.3.y/arch/arm64/mm) です。7.x 比較時は起動可否を先に確認します。
- M5 の v5 overlay 依存では I2C1 → M5IOE1 → LCD backlight / SPI0 panel、および keyboard / input の鎖を考慮する。optional driver は終点後に modprobe する案。
- arm64 kernel は firmware 起動で gzip または非圧縮を前提に評価する。LZ4 / ZSTD / LZO kernel 形式を標準起動で使う根拠は見つかっていない。カスタム ARM stub / TF-A は未確認。

出典: [RPi kernel rpi-6.18.y](https://github.com/raspberrypi/linux/tree/rpi-6.18.y)、[6.18 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt)、[7.2 Kconfig.preempt](https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt)、[deferred probe change](https://github.com/torvalds/linux/commit/56e3ee721b33)、[Raspberry Pi boot docs](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/config_txt/boot.adoc#L26-L52)。
