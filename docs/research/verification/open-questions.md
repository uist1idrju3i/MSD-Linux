# 未確認事項と次の確認

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

原表に分散した問いを主題別に統合しました。「設定あり」「記録あり」「実機未確認」を分け、文書整理だけで解決済みにはしません。
実施済み試験は[S1–S17](experiment-catalog.md)、観測の条件は[観測方法](observability.md)、操作は[実機確認](../../VERIFY.md)を参照します。
原記述・出典・基準commit・行番号は[統合前の記録](research-records.csv)に保持します。Qは測定文書、Rは旧追跡表のIDです。

実装・計画・判断待ち・延期を含む作業の現在地は[残件と将来計画](../roadmap.md)、原Q/Rと残件の対応は[対応表](../roadmap-coverage.csv)で追跡します。以下の問いは、対応先があるだけでは解決済みになりません。

## 主題別の確認事項

| 主題 | 現在の根拠と留保 | 次に確かめること | 原記録 |
|---|---|---|---|
| 起動形式とSD配置 | MBR・4 MiB配置は実装済み。CM0の64-bit、gzip kernel8.img、GPTの実起動は別に確認する。 | 現行imageでfirmwareからの起動、partition境界、復旧を測る。 | Q01 Q10 Q17 Q30 R07 |
| tryboot・watchdog | QEMUのwatchdog試験はfirmwareのslot切替を確認しない。 | autoboot.txt、one-shot、試行失敗時の復帰、firmware→OSのWDT引継ぎを実機で反復する。 | Q14 Q28 R01 R02 R23 |
| 起動時間の基準 | 公式image・Buildrootの実機baselineは未測定。WP-1のLoaded 4.131 sからDevice tree loaded 6.760 sまでの2.63 sの内訳は未確認。 | T_shellとT_initを分け、同一構成のサイズ変更でGPU段との関係を測る。 | Q21 Q29 Q53 R03 |
| LCD・fbcon・overlay | 設定・overlay名と実際のLCD表示は別。UART種別・RTCアドレスも機能ごとに照合する。 | 最終.config、適用DT、fbcon、実表示とキー入力を確認する。 | Q02 Q22 Q23 Q32 R06 R08 |
| 公開OS・fork | 404やforkの名称だけで非公開理由・内容の同一性を断定しない。 | 公式OS/BSPの取得記録と固定refを照合し、到達不可は取得失敗として残す。 | Q04 Q18 Q27 Q36 |
| 公式OSのkernel版 | Trixie 2026-10-06の6.18.50はrelease notesの記載。image内部のpackage版は未確認。 | imageの展開とpackage情報で照合する。 | Q55 |
| kernel系列とAPI | 現行の固定値と7.xの比較資料を分ける。alias unmap、KVM、M5 module、rpi-6.12〜6.17のヘッダー有無には追加確認が残る。 | 固定commitでbuild・boot・PREEMPT実効値を比較し、あるpathの404を系列全体へ一般化しない。 | Q06 Q41 Q46 Q49 |
| microSDのFTL・電断 | 実カードの内部FTLと電断耐性はQEMUで確定しない。 | カード別の一次情報と実電断・fsck・復旧を記録する。 | Q07 Q19 Q37 R04 |
| カードの特性と配置効果 | erase/AUと最適化効果はカード固有。4 MiB alignmentの指定だけで高速化とは言わない。 | sysfs、FAT data-area absolute offset、現行/1 MiB/4 MiB配置と実転送速度を測る。 | Q09 R18 |
| data filesystem | ext4は実装済みで「移行前」ではない。data=journal/orderedの比較と電断時整合性は別課題。 | fsync/rename、barrier、commit=、実SDの電断と復旧を比較する。 | Q11 R19 |
| discard・fstrim | target cardのcapabilityと実行結果は未確認。 | discardの単位・可否、fstrimの結果と通常I/Oへの影響を確認する。 | R20 |
| 更新の信頼連鎖 | 既存Ed25519検証、実行時dm-verity、鍵更新、全SD交換の防御境界は別。 | 公開鍵・root digestの信頼元、key rotation、rollback、電源断・復旧を設計して試験する。 | Q12 R21 |
| RAUC連携 | 現行updaterはmsd-update。RAUC #1599やcustom backendの説明はCM0対応済みの証拠ではない。 | 署名・boot連携・health・復旧の統合費用を代替比較から評価する。 | Q03 |
| MCUboot | arm64やCM0で必要なboot flowの実績は未確認。 | 実績・信頼の起点・firmware制約を一次資料と実機で確認する。 | Q08 Q20 Q38 |
| 全周辺機能 | driver/firmwareを収録しただけではIR・camera・charger等の利用可能性を保証しない。 | Standard/Liteでprobe、競合、実I/O、復旧を機能別に記録する。 | Q13 Q31 R24 |
| Wi-Fi・Ethernet | 無線搭載版の資料はCYW43439。複数blobの収録だけでは実chip ID・選択firmwareを確定しない。SR9900AのUSB IDとdriverは未確認。 | chip ID、firmware、USB ID、bind先を採取し、認証・IP・DNS・通信開始前の防御を別途実装する。 | Q15 Q45 R05 |
| HDMI・UART | 19-pinの記載だけではconnector形状・実出力を確定しない。enable_uart、GPIO14/15のmini-UART/PL011の最終pinmuxも未確認。 | コネクタ・最終config.txt・適用DT・実信号を照合し、pi-genの文書と実装の差を調べる。 | Q16 Q44 |
| 別OS・構築基盤 | image-rota、Canonical Zephyr、Ubuntu CoreはBuildrootの置換済み機能ではない。 | Zero 2 W/Pi 3、A/B相当機構、依存・移行・復旧条件を比較する。 | Q05 Q24 Q25 Q33 Q34 R09 |
| CPU・toolchain・sysctl | QEMUの既定値や仮想時間は実温度・RAM・SD・cpufreqを反映しない。 | mcpu/mtune、LTO、sysctlとI/O値を実機で再採取し、全機能と同条件比較を行う。 | Q26 Q35 R14 |
| 暗号命令とPQ | BCM2837のAES/SHA非搭載を示すメーカー一次仕様、ML-KEM実接続とCM0所要時間は未確認。SSH/VPNは製品実装しない方針。 | A53でCrypto Extensionが任意であることとSoCの実装を分け、将来方針変更時だけ実接続・旧client互換を測る。 | Q39 Q40 Q52 R13 |
| 出典・名称利用 | brandページの404、Kickstarter・forumの403等は規約不存在・本文確認の証拠にはならない。 | 取得記録を残し、公式の代替経路で原文を確認する。 | Q42 Q43 |
| 他機種の高速化記事 | KittenLabsのcore_freq=550が最終3.5秒に含まれるか未確認。 | 構成・測定区間を照合し、CM0の性能値へ転用しない。 | Q47 |
| 電断時の観測 | ログ方式・給電が電断条件を変え得る。 | 観測方法と切替を実装し、SDログ・USB/UART給電の影響を分ける。 | Q48 |
| M5共有resetとGPIO | disabled-gpiosのindex 11とPYG12の対応は推論のまま。GPIO6=SW_DETとPYG6=MIC_SWを区別する。 | v3/v5と実回路、GL852G・keyboardの共有GPIOの制御責務を照合する。 | Q50 R12 |
| RTCアドレス | CardputerZero overlayは0x32、単体rx8130は0x68。実機未確認。 | 基板revと適用DT、実デバイスのアドレス・時刻・retentionを確認する。 | Q51 |
| Newlib | sourcewareの取得失敗だけでLinux用sysディレクトリ不存在とは言わない。 | 取得可能な一次ソースでLinux対応範囲を確認する。 | Q54 |
| 配布物・license | SBOMの照合と各配布物のlicense/source archiveの完全性は別。 | 最終構成のlegal-info、外部toolchain・M5配布物を確認する。 | R10 |
| 開発環境・CI実験 | 予備的artifact比較を正式な性能実験と混同しない。 | 未測定のbuild最適化候補を同条件・反復・負の対照で記録する。 | R11 |
| 割り込み・周波数 | IRQの4コア分散とarm_boost=1のCM0での実効値は未確認。 | proc/interrupts、vcgencmd、温度・clockを測り、config.txtの旧コメントと公式仕様を照合する。 | R15 R16 |
| SysRq-U | GPIO6経路のmarkerだけでは実remountの証拠にならない。 | kernel.sysrq=32でkernel actionと実remountを確認する。 | R17 |
| hardeningの実効値 | SSP・FORTIFY・RELRO・PIEやmount/sysctlの指定と実効値・機能影響を分ける。 | 最終config・binary・runtimeと拒否試験を照合する。 | R22 |

## 判断に使う記録

現行設定と過去の仮説を分けます。[ハードウェア・BSP](../hardware/hardware-spec.md)、[生成物照合](../../experiments/2026-11-02-hardware-artifact-audit.md)、[依存とSBOM](../operations/sbom-coverage.md)、[代替比較](../alternatives/README.md)、[権限設計](../security/README.md)を主題ごとの根拠にします。
ログイン方式の確認待ちを、この整理で確定しません。公開版SemVerと内部番号の対応は承認済みです（内部番号はtag commitのcommit時刻。対応表は[Release対応表](../../releases/README.md)）。
