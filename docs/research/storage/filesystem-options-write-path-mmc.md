# MMCとSD hostの設定項目

[保存領域の調査へ戻る](README.md) / [filesystem option一覧](filesystem-options.md)

## 範囲と出典

Linux固定版6.18.59とmainline 7.4-rc1からMMC coreのmodule parameter、MMC sysfs ABI、`mmc-controller-common.yaml`と`mmc-controller.yaml`のpropertyを抽出しました。CardputerZeroのhost driverはDTS/overlayの最終展開を確認できていないため、候補として記録します。`CONFIG_MMC_BCM2835_MMC`、`CONFIG_MMC_BCM2835`、`CONFIG_MMC_SDHCI_IPROC`はいずれもboard fragmentで有効ですが、最終`.config`の解決結果と実機でprobeされたdriverは未確認です。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
|---|---|---|---|---|---|---|
| `perdev_minors` `card_quirks` `use_spi_crc` `fail_request` | MMC block minor、card quirk、SPI CRC、debug request fault injection | driver/kernel既定 | 可 | debug paramの差分あり | 既定のまま | fault injectionは試験専用。製品起動時に故障を起こす設定は置かない。 |
| `mmc_debug` `mmc_debug2` `debug_quirks` `debug_quirks2` | candidate host/SDHCI debug flag | driver既定 | 可 | candidate driverごと | 既定のまま | logはRAMへ置く。debug出力により無操作時のSD writeを発生させない。 |
| `sysfs/rev` | MMC device revision情報 | card報告値 | 可 | 同 | 既定のまま | read-only識別情報であり、設定対象ではない。 |
| `dt/bus-width` `dt/max-frequency` `dt/max-sd-hs-hz` `dt/sd-uhs-sdr12` `dt/sd-uhs-sdr25` `dt/sd-uhs-sdr50` `dt/sd-uhs-ddr50` `dt/sd-uhs-sdr104` `dt/cap-sd-highspeed` `dt/cap-mmc-highspeed` `dt/mmc-hs400-enhanced-strobe` | bus width・frequency・SD/MMC speed capability | board/card/driver依存 | 可 | property差分あり | 実験で比べる | SD cardとSoCの実対応を確認し、write timing、error rate、電力、温度を実機で測る。未確認のspeed modeを有効にしない。 |
| `dt/cd-gpios` `dt/cd-inverted` `dt/broken-cd` `dt/cd-debounce-delay-ms` `dt/non-removable` `dt/wp-gpios` `dt/wp-inverted` `dt/disable-wp` `dt/dsr` | card detect、write protect、removable判定 | board配線依存 | 可 | 同 | 既定のまま | CardputerZeroの配線図と実機状態を確認する。誤ったwrite-protect扱いでdataを失わないよう設定を推測しない。 |
| `dt/vmmc-supply` `dt/vqmmc-supply` `dt/mmc-pwrseq` `dt/post-power-on-delay-ms` `dt/power-off-delay-us` `dt/full-pwr-cycle` `dt/full-pwr-cycle-in-suspend` `dt/keep-power-in-suspend` `dt/wakeup-source` | power supply、起動順、suspend時の給電 | board/driver依存 | 可 | `power-off-delay-us`等を含む | 実験で比べる | suspend/resumeやpower-cycleがjournal・dm-integrityのflush中に起きない条件を測る。長い操作の電源状態も表示する。 |
| `dt/cap-mmc-hw-reset` `dt/cap-power-off-card` `dt/cap-sdio-irq` `dt/supports-cqe` `dt/disable-cqe-dcmd` `dt/no-1-8-v` `dt/no-mmc` `dt/no-mmc-hs400` `dt/no-sd` `dt/no-sdio` `dt/fixed-emmc-driver-type` | controller/card capabilityと禁止条件 | hardware/driver依存 | 可 | 同 | 既定のまま | capabilityは実機とSoC資料で確認し、未確認のhardware featureを有効化しない。 |

### host driver

board configは`bcm2710-rpi-cm0.dtb`と`cardputerzero-v5-overlay`を指定し、kernel fragmentは`MMC_BCM2835_MMC`、`MMC_BCM2835`、`MMC_SDHCI_IPROC`を有効化します。host選択はDTS include/overlayを展開した最終DTで未確認です。必要候補は`sdhci-iproc`、`bcm2835-sdhost`、`bcm2835-mmc`です。sourceのmodule parameterを列挙したことは、製品imageでmoduleとしてloadされることを意味しません。

## 出典

- [固定版 MMC sysfs ABI](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/Documentation/ABI/testing/sysfs-bus-mmc?id=b3495ea401d709af0701a85babcba5e3d788a602)、[MMC bindings](https://git.kernel.org/pub/scm/linux/kernel/git/raspberrypi/linux.git/tree/Documentation/devicetree/bindings/mmc?id=b3495ea401d709af0701a85babcba5e3d788a602)
- [Linux v7.4-rc1 MMC ABI](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/ABI/testing/sysfs-bus-mmc?h=v7.4-rc1)、[MMC bindings](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/mmc?h=v7.4-rc1)
- [CardputerZero board configuration](../../../board/cardputerzero/config.txt)、[kernel fragment](../../../board/cardputerzero/linux.fragment)
