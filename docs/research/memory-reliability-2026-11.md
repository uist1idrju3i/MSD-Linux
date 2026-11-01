# メモリ信頼性（EDAC / MCE / DRAM リフレッシュ）の調査（2026-11）

放射線・ソフトエラー対策としての EDAC、MCE（Machine Check Exception）、DRAM リフレッシュ周期についての調査です。調査のみで、実装の決定は行いません。

## 1. 前提（本機のハードウェア）

- CM0 = RP3A0 SiP（BCM2710 + 512MB LPDDR2）。**ECC DRAM はない**（LPDDR2 は in-band ECC 非対応）【一次: RP3A0 / CM0 製品情報】
- カーネルは `linux.fragment` ベースで、EDAC・RAS・MEMORY_FAILURE 系の設定は含まれていない【一次: board/cardputerzero/linux.fragment】
- upstream `bcm2711_defconfig`（rpi-6.18.y）にも `CONFIG_EDAC_*`、`ACPI_APEI`、`MEMORY_FAILURE`、`GHES` は入っていない【一次: raspberrypi/linux bcm2711_defconfig】

## 2. EDAC（Error Detection And Correction）

カーネルの EDAC サブシステムは、ECC メモリコントローラ・キャッシュパリティ・PCIe AER などからのエラーを収集・報告する枠組みです。

| 観点 | 状況 |
|---|---|
| RPi 向けの EDAC ドライバ | `drivers/edac/` に BCM283x/BCM2710 用のメモリコントローラ EDAC ドライバは**存在しない**【一次: rpi-6.18.y drivers/edac/ 一覧】 |
| `a72_edac` | Cortex-A72 の L1/L2 キャッシュパリティ検出用。CM0 の Cortex-A53 には適用外（A53 のキャッシュには parity 検出の公開インタフェースがない前提）【一次: drivers/edac/a72_edac.c】 |
| `versal_edac` `dmc520_edac` など | Xilinx / サーバー向け SoC の専用ドライバで、BCM2710 には使えない |
| ユーザーランド | Buildroot に `BR2_PACKAGE_RASDAEMON` があるが、rasdaemon は EDAC/RAS イベントの収集デーモンであり、**報告元となるハードウェア EDAC がない環境では収集対象がない** |
| 結論 | **ハードウェアが ECC/parity 報告を持たないため、EDAC は本機では実質的に使えない**。有効化しても監視対象が存在しない |

## 3. MCE（Machine Check Exception）

MCE は x86 の用語です。arm64 ではハードウェアエラーの通知は以下の機構になります。

| 機構 | arm64 での対応 | 本機での現実性 |
|---|---|---|
| Synchronous External Abort（同期外部アボート） | 命令・データアクセス中のバスエラー → CPU 例外 | ハードがある（bcm2710 でバスエラーが発生すれば例外は出る）。EDAC 的な回収経路はない |
| SError Interrupt（非同期エラー） | 遅れたバスエラーや内部エラーの割り込み | 同上 |
| RAS（Reliability, Availability, Serviceability）拡張 | `CONFIG_ARM64_RAS_EXTN` など。CPU 内部のエラーレコードを ERRC*/ERR* レジスタで報告し、APEI/GHES 経由で OS が拾う | BCM2710 は RAS 拡張を持たない前提【未確認：アーキテクチャマニュアルの機能対応表】 |
| APEI / GHES | ACPI 経由でファームウェアがエラーを OS に渡す仕組み（サーバー向け） | **RPi は ACPI で起動しない（DT ブート）ため使えない** |
| `CONFIG_MEMORY_FAILURE`（hwpoison） | 壊れた物理ページを退避する機構 | **現在有効化していない**。ECC がなくても、ファームウェア/ドライバがエラーを検出して `memory_failure()` を呼べる設計なら有効だが、RPi の SDRAM 側にその報告経路がない |

**実質的な結論**: ハードウェア検出（ECC/parity）がない環境では、MCE 系の枠組みを有効化しても「拾うべきエラーが発生しない」ため効果が薄い。本機のソフトエラー対策は **EDAC ではなく検出できない事を前提にした設計**（ウォッチドッグ・A/B ロールバック・署名検証）で担う形になる。

## 4. DRAM リフレッシュ周期

DRAM のリフレッシュ間隔を短くする（例: 64ms → 32ms）と、リフレッシュ漏れによるデータ保持エラーの窓が狭まる一方、電力と帯域の消費が増えます。

| 観点 | 状況 |
|---|---|
| 設定箇所 | DRAM タイミングは **Raspberry Pi の閉鎖ファームウェア（start.elf / EEPROM ブートローダ）がメモリコントローラに設定**しており、ARM 側の Linux や config.txt からは調整できない【一次: raspberrypi/documentation config_txt に `sdram`/`refresh` 系の設定項目なし】 |
| `sdram_freq` 関連 | config.txt には `sdram_freq` などの周波数系はあるが、リフレッシュ周期そのものを変更する公開設定は確認できていない【未確認：公開 config_txt 一覧の grep 結果】 |
| Linux 側 | Linux は DRAM のリフレッシュを制御しない（PHY/メモリコントローラの動作） |
| 結論 | **本機ではリフレッシュ周期の変更は実質不可**（ファームウェア内部の話）。効果を求めるなら Raspberry Pi ファームウェアの設定可能性を問い合わせる経路になる |

## 5. 本機で現実的な放射線・ソフトエラー対策

ハードウェア EDAC がないため、設計側で担います。

| 層 | 対策 | 現状 |
|---|---|---|
| ウォッチドッグ | `CONFIG_BCM2835_WDT=y` + ユーザーランド watchdog | 有効済み |
| ストレージ健全性 | SquashFS RO + 署名検証 + A/B | 済み |
| ランタイム | 定期的な再起動・ヘルスチェック・panic 自動再起動（sysctl `kernel.panic`） | [セキュリティ強化項目の調査](security-2026-11-hardening-list.md) の sysctl 案を参照 |
| アプリケーション | 重要データの冗長保持・CRC・チェックポイント | 設計上の話題 |
| ハードウェア | ECC 付きモジュール（CM4 等）への移行 | 本機では対象外 |

## 6. まとめ

1. **EDAC / MCE / RAS 枠組みは本機では実用不可**: ECC/parity を持たない LPDDR2 + A53 + DT ブート + ACPI なしという構成では、カーネル側にエラー報告元がない。
2. **DRAM リフレッシュ周期は config.txt/Linux から変更不可**: ファームウェア内部の設定で、公開された調整経路はない。
3. **現実的な対策は設計側**: ウォッチドッグ・A/B 復旧・署名・定期的健全性チェックでカバーするのが本機の実装方針として妥当。

## 出典

- `raspberrypi/linux` `rpi-6.18.y` `drivers/edac/` 一覧と `a72_edac.c` 【一次】
- `raspberrypi/linux` `rpi-6.18.y` `arch/arm64/configs/bcm2711_defconfig`（EDAC/APEI/MEMORY_FAILURE が無いことを grep で確認）【一次】
- `board/cardputerzero/linux.fragment`（EDAC/RAS 系設定なし）【一次】
- raspberrypi/documentation `config_txt`（`sdram`/`refresh` 設定項目なしを確認）【一次】
- Buildroot 2026.08 `vendor/buildroot/package/rasdaemon`（パッケージは存在するが報告元がない）【一次】
