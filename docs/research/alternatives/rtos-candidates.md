# RTOS 候補の調査（RTEMS・NuttX・Zephyr・Canonical Zephyr LTS・FreeRTOS）

Linux ディストリビューションである MSD/Linux と同じ土俵で比較できるかを確認するため、組込み RTOS 5 系統を調査した。先に結論をまとめる。

**総合判定: CardputerZero（BCM2837・armv8-A・512MB）で「安定性＋起動最速＋PREEMPT_RT」のコンセプトを維持する限り、いずれの RTOS も現行 Linux の置き換えにはならない。** RTOS は MMU なしの MCU クラスを主戦場とし、Linux 側で実現済みの機能（SquashFS rootfs・dm-verity・ext4 /data・BusyBox ユーザランド・raspi firmware/tryboot 連携）の移植経路がない。PREEMPT_RT 採用後も Linux 内で改善を積み上げる方針が合理的である。

| RTOS | armv8-A(64bit) 対応 | BCM2837/CM0 適合 | 判定 |
|---|---|---|---|
| RTEMS | AArch64 BSP・SMP あり | raspi4 系 BSP 相当なら近いが CM0 実績なし | 技術的には動く可能性があるが Linux 機能の代替がないため不適 |
| Apache NuttX | armv8-a 対応（BCM2711/RPi4 実績） | BCM2837 ボード定義なし（port 必要） | 同上。POSIX 準拠は高いがコンセプト置換にならない |
| Zephyr | armv8-A サポート（qemu/fvp・一部ボード） | CM0 向け board 定義なし | MCU 向け。Linux 置換不適 |
| Canonical Zephyr 26.04 LTS | Zephyr と同じ | 同左 | 商用 LTS（Ubuntu Pro）のため性質が違う。CM0 不適は同じ |
| FreeRTOS | Cortex-R82(AArch64)ポートはあるが **Cortex-A プロファイルのポートがない** | BCM2837 の Cortex-A53 では動かない | **除外**（アーキテクチャ不適合） |

## RTEMS

Real-Time Executive for Multiprocessor Systems。単一アドレス空間・スレッド型 RTOS（カーネル/ユーザー空間の分離なし）。宇宙・医療・ネットワーク機器での実績が長い。

- API: POSIX 1003.1b（pthread 等）と Classic API。C/C++/Ada(GNAT)。
- SMP: AArch64 を含む対象 arch で Clustered Scheduling による SMP を提供。
- ライセンス: 修正版 GPL 2.0+（静的リンク例外付き）でアプリ側のライセンス義務なし。
- ネットワーク: FreeBSD 由来 TCP/IP。FS は IMFS・FAT12/16/32・RFS・TFTP/NFS クライアント。
- CardputerZero との関係: 64bit ARM を対象とする少数派 RTOS で、raspi4 系 BSP なら BCM2837 に近い。ただし Linux の rootfs・verity・A/B 更新・BusyBox 資産をそのまま使う経路がなく、コンセプト（ディストリビューション）自体の再設計になる。

## Apache NuttX

POSIX を開発指針とする RTOS（Apache 2.0）。PSE51 相当の機能群を持ち、組込みでは最も Linux 的な設計（VFS・/proc・flat/protected/kernel ビルドモード）。

- POSIX 対応表で `POSIX_C_LANG_SUPPORT 94/105` など細かく開示している（POSIX 商標の使用許諾はない）。
- armv8-a 対応があり BCM2711（RPi4）の board 実績があるが、**BCM2837/CM0 の board 定義は upstream にない**（port 作業が必要）。
- BCM2708（Pi Zero/1 世代）は過去に対応したが削除済み。
- Linux の資産は使えず（独自ドライバモデル）、SquashFS/verity/A/B の移植経路もない。

## Zephyr

Linux Foundation の RTOS（Apache 2.0）。MCU クラス中心、Kconfig+Devicetree 構成、west ツール。

- リリース: 最新安定 4.5.0（2026-10-28）、現行 LTS は 3.7.0（EOL 2029-07-27）。LTS は 2.5〜3 年ごとで約 5 年保守。
- armv8-A（64bit）のサポートは qemu/fvp と一部ボードまで。確認した範囲では CM0/BCM2837 の board 定義はなく、SD 起動・raspi firmware 連携の経路もない。
- POSIX サポートは拡大中だが（PSE51/52/53 の Options 相当）、完全互換ではない。

## Canonical Zephyr 26.04 LTS

2026-09-21 発表の Canonical 製 Zephyr ディストリビューション（Ubuntu Pro for Devices）。

- upstream Zephyr の約 5 年保守を超える**最大 15 年のセキュリティ保守**（EU CRA の 5 年要件を上回る）。
- Ubuntu と同じリリースサイクル（LTS は 2 年ごと、中間 6 か月）。West 等のツールチェーンも保守対象。
- Golioth Cloud による OTA/デバイス管理をネイティブ統合。
- 判定: 対象は MCU グレードの製品で、BCM2837 の Linux クラス用途とは層が違う。商用サブスクリプション前提のため、本プロジェクトの「再現可能な OSS 配布」方針とも合わない。

## FreeRTOS

Amazon 主導の RTOS（MIT）。カーネル単体が小さい最小構成。

- LTS: FreeRTOS Kernel 11.3.0、LTS 保守は 2028-04-30 まで。
- armv8 対応は **Cortex-R82（ARMv8-R・AArch64）の SMP ポート**。アプリケーションプロセッサの **Cortex-A プロファイル（v8-A）用ポートは提供されていない**。
- BCM2837 の Cortex-A53 では動作しないため、SD 起動の本機では**除外確定**。

## MSD/Linux への意味

RTOS 化は「より速い起動」と引き換えに、ドライバ（LCD・キーボード・SD・USB）・ファイルシステム・更新機構・検証基盤（QEMU ゲート・sweep）のすべてを再設計する変更であり、コンセプトの「安定性」と「積み上げによる最速化」のどちらにも反する。RTOS の価値が出るのは MCU クラスや例外遅延が主眼の製品であり、CardputerZero の 512MB/SD/Linux 資産では Linux+PREEMPT_RT が上位互換である。

## 出典

- [RTEMS 公式](https://www.rtems.org/)・[RTEMS SMP guide](https://docs.rtems.org/docs/main/c-user/symmetric_multiprocessing_services.html)【一次】API・SMP・ライセンス
- [Apache NuttX platforms](https://nuttx.apache.org/docs/latest/platforms/)・[POSIX 対応表](https://nuttx.apache.org/docs/latest/standards/posix.html)【一次】armv8/BCM 対応状況
- [Zephyr releases](https://docs.zephyrproject.org/latest/releases/index.html)【一次】LTS 3.7・最新 4.5
- [Canonical「Zephyr 26.04 LTS」](https://canonical.com/blog/zephyr-lts-announcement)【一次】15 年保守・Ubuntu Pro・Golioth
- [FreeRTOS-LTS](https://github.com/FreeRTOS/FreeRTOS-LTS)・[FreeRTOS Kernel v11.3.0](https://github.com/FreeRTOS/FreeRTOS-Kernel/releases/tag/V11.3.0)【一次】LTS・Cortex-R82 ポート（v8-A は未提供）
