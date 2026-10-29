# QEMU のローカルパッチ

| ファイル | 内容 | 上流への提出状況 |
|---|---|---|
| `0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch` | BCM2835 の ASB 領域に未実装デバイスを追加します。 | 未提出 |
| `0002-hw-gpio-bcm2835_gpio-add-input-irq.patch` | BCM2835 GPIO の入力、エッジ・レベル検出、イベント状態、割り込み出力を追加します。 | 未提出 |
| `0003-hw-misc-bcm2835_powermgt-add-watchdog-timer.patch` | BCM2835 watchdog のカウントダウン、給餌、リセット、電源オフを追加します。 | 未提出 |
| `0004-hw-misc-bcm2835_thermal-make-temperature-settable.patch` | BCM2835 thermal のダミー温度を `temp` プロパティ（摂氏、既定 25）で設定可能にします。 | 未提出 |

Linux の `bcm2835-power` ドライバーは `BRDG_OFFSET`（`0xa000`）の ASB 領域を読みます。未割り当てのままだと、512 MiB の `raspi3ap` は `bcm2835_power_probe` で同期外部 abort になります。一方、`raspi3b` は RAM のエイリアスがこの穴を覆うため、起動に支障はありません。
