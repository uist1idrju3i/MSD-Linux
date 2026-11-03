# OS ベース比較

RESEARCH.md から分けた節です。


以下は公開資料で確認した OS 候補の比較です。値や互換性は出典に記載された条件とともに示し、本リポジトリでは試していません。

| 候補 | 調査結果 | 起動 / 要件への評価 |
|---|---|---|
| Buildroot 2026.08 | `raspberrypizero2w_64_defconfig` と `raspberrypi3_64_defconfig` があります。CM0 専用 defconfig の有無は未確認です。GCC 既定は 15.3.0 | 最小化・独自 A/B に適しそうとの推測です。Zero 2 W で <3.5 s の第三者値は条件が大きく異なります |
| 公式 CardputerZero pi-gen | Debian trixie / systemd / labwc、kernel 6.18.39 固定。追跡対象の公開ファイルでは A/B / RO 設定を確認できていません | M5 の現行ベースラインとして有用です。Linux 可用 7〜9 s は終点定義がありません |
| Yocto / meta-raspberrypi | `raspberrypi0-2w-64.conf` と `linux-raspberrypi_6.18.bb` があります。CM0 専用 machine の有無は未確認です。read-only-rootfs は利用可能です | Buildroot の代替です。ビルド・学習負担が大きく、起動時間の比較値はありません |
| Ubuntu Server / Minimal Ubuntu 26.04.1 | Imager 一覧に Pi 3 向け Server がある | 起動時間・A/B の根拠なし。systemd 標準 |
| Ubuntu Core 26 | Imager 一覧で pi3-64bit 向けを確認。最小 RAM / ストレージや起動高速化資料は未確認 | snap の recovery / seed が A/B 相当か未確認、秒数もなし |
| rpi-image-gen | Pi 3 / Zero 2 W の device 定義あり。`image-rota` は Pi 4 / 5 クラスのみ | CM0 の公式 A/B 構成には使えない |
| Zephyr v4.5 / Canonical Zephyr 26.04 | v4.5.0（2026-10-28 公開、サポートは 2027-10-28 まで）に `boards/raspberrypi/rpi_zero_2w` が入りました（PR #110189、2026-08-17 マージ）。単コア・mini-UART 向けで SDHCI 対応は未確認です。Canonical fork の内容も未確認です | SD ストレージを使えない可能性が高く、CM0 対応は依然として評価できません |
| Alpine 3.24.2 / piCore64 17.0 | CM0 対応、kernel 6.18 系との情報がありますが、公開資料の確認が未完了です | A/B と起動時間の根拠はありません。RAM 展開型は 512 MB で厳しい可能性があります |
| BusyBox 単独 | OS ではなく userland。Buildroot の最小構成で利用できる | kernel / firmware は Buildroot と共通。独立した起動時間根拠なし |
| Rugix Bakery / Ctrl | 【一次】（2026-10-19 確認）対応表では Pi 5/Pi 4（Tier 1）/CM4（Tier 2）が `rpi-tryboot`、Pi 3/Zero 2 W（Tier 2）と Pi 2 v1.2/Pi 2/Pi 1/Zero（Tier 3）が `rpi-uboot`。Pi 3 の制約は Rugix の target による | Raspberry Pi firmware は全モデルで tryboot に対応します。CM0 で Rugix を使うには実験的な U-Boot flow が必要で、firmware 更新不可のため U-Boot 非採用の MSD 方針とは合いません。MSD 自身の tryboot 設計は影響を受けず、CM0 実機確認は継続します |
| Android / BSD / RTOS / OpenWrt | 512 MB / CLI、M5 Linux ドライバ非対応、または kernel 6.12 系という理由で優先外 | FreeBSD 15.1 の Zero 2 W 対応は未確認です。LCD / keyboard / M5IOE1 も未確認です |

出典: [Buildroot 2026.08](https://github.com/buildroot/buildroot/commit/d5180309b1b66ef3b8eaccca70ad69be8e0729a1)、[Yocto meta-raspberrypi](https://github.com/agherzan/meta-raspberrypi/blob/919588393f41b48cb6c5d832aa35e58a19b6762d/conf/machine/raspberrypi0-2w-64.conf)、[Raspberry Pi Imager OS list](https://downloads.raspberrypi.com/os_list_imagingutility_v4.json)、[Zephyr Pi Zero 2 W board](https://github.com/zephyrproject-rtos/zephyr/tree/a915b2f12675b48b16d56653ea145dcd8f20cbbf/boards/raspberrypi/rpi_zero_2w)、[Rugix devices](https://rugix.org/docs/bakery/devices/)、[Rugix Raspberry Pi flow](https://rugix.org/docs/bakery/devices/raspberry-pi)、[Raspberry Pi bootflow](https://github.com/raspberrypi/documentation/blob/ddea98e98dafe9419feb4fd82710c2fbdef7dc44/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L91)。
