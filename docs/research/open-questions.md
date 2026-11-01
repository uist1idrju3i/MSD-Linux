# 未確認事項

RESEARCH.md から分けた節です。項目の追加・解消はこの表を更新します。


| 項目 | 次に確認すること |
|---|---|
| BCM2837 / CM0 の tryboot | 実機で `autoboot.txt` / `tryboot_a_b=1`、再起動時復帰を確認 |
| watchdog | `kernel_watchdog_*` と BCM2835 WDT が firmware / CM0 で有効か実機試験 |
| 起動速度 | 公式 image baseline、Buildroot baseline、LCD + keyboard の終点と PID 1 marker を測定 |
| rootfs / SD | microSD FTL の電断に関する一次資料と、複数カードでの実電断試験 |
| Wi-Fi / Ethernet | Wi-Fi chip ID、firmware blob、SR9900A の USB ID / driver |
| HDMI / UART / framebuffer | HDMI connector type、UART pinmux / console、FRAMEBUFFER_CONSOLE の最終 `.config` と LCD fbcon |
| GPT / MBR | BCM2837 での GPT boot、パーティションレイアウト制約 |
| M5 overlay | `cardputerzero-overlay` と `cardputerzero-v3/v5-overlay` の名称不整合、RTC overlay の I2C address |
| image-rota / Zephyr | zero2w / pi3 での image-rota 挙動、Canonical Zephyr fork の内容 |
| Buildroot packages | 最終構成で `make legal-info` を生成し、各配布物のバージョン・ライセンス・source archive を確認 |
| 開発環境・CI の比較 | [記録](dev-environment-and-ci.md)の artifact 比較は予備的です。第3段階の PR で正式な実験記録を作成し、未測定の build 最適化候補を評価 |
| M5 hardware revision | v3 / v5 overlay と製品回路の整合、GL852G reset と keyboard shared GPIO |
| SSH / VPN | 実装しない方針。将来方針が変わる場合に限り暗号性能・鍵管理を再調査 |
| sysctl・I/O の実機値 | QEMU で取った既定値（[一覧](tunables-defaults.md)）を CM0 実機で取り直し、RAM、SD、cpufreq、温度に依存する値の差を記録 |
| IRQ の分散 | 実機の `/proc/interrupts` で、周辺機器の割り込みが 4 コアへ回っているかを確認 |
| `arm_boost=1` | CM0 で `arm_freq` が変わるかを `vcgencmd` で確認。`config.txt` のコメント（Pi 3 のブーストモード）は公式資料と一致しない |
| `kernel.sysrq=32` | GPIO6 の電源断で remount が実行されることを、値を変えたイメージで実機確認 |
| SD の配置・性能 | 現行／1 MiB／4 MiB の image layout、FAT data-area absolute offset、target card の sysfs erase/AU 値と実性能を実機で確認 |
| `/data` の ext4 | `data=journal` から `data=ordered` へ移す場合の `fsync`/rename、barrier、`commit=` と電源断の整合性を確認 |
| discard / fstrim | target card の discard capability と処理結果を実機で確認 |
| update trust chain | 署名検証、鍵ローテーション、dm-verity root digest の保管場所を設計し、全カード交換の脅威境界を確認 |
| kernel / userspace hardening | SSP、FORTIFY、RELRO、PIE、mount options、sysctl の Buildroot 実効値と機能影響を確認 |
| watchdog / tryboot | BCM2837 での one-shot tryboot、`kernel_watchdog_timeout`、S01msd-watchdog の実 reset 動作を実機で確認 |
| hardware functions | IR、camera、IP2315 charger、SR9900A、各 M5 driver の probe と実機動作を確認 |
