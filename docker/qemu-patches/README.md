# QEMU のローカルパッチ

| ファイル | 内容 | 上流への提出状況 |
|---|---|---|
| `0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch` | BCM2835 の ASB 領域に未実装デバイスを追加します。 | 未提出 |

Linux の `bcm2835-power` ドライバーは `BRDG_OFFSET`（`0xa000`）の ASB 領域を読みます。未割り当てのままだと、512 MiB の `raspi3ap` は `bcm2835_power_probe` で同期外部 abort になります。一方、`raspi3b` は RAM のエイリアスがこの穴を覆うため、起動に支障はありません。
