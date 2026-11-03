# ユーザー空間・init・libcの調査

[調査の索引](../../../RESEARCH.md) / [文書案内](../../README.md)

現在の構成、候補を再評価した比較、過去の資料・測定値を分けて読みます。製品の設定は、この文書整理では変更していません。

## 現在の構成と未確認の境界

[defconfig](../../../configs/msd_cardputerzero_defconfig)はBootlinのAArch64 glibc stable外部toolchain、BusyBox init、mdevを選びます。systemd・eudev・muslへの移行を決めたという意味ではありません。M5のudev ruleとsystemd unitをそのまま実行する構成ではなく、対応する初期化・deviceの識別・権限は[公式OSとの比較](../official-software.md)で個別に確認します。全周辺機能の実機動作は未確認です。

| 読む目的 | 本文 |
|---|---|
| 現在の候補・固定Buildrootの制約・変更費用 | [基本コマンド](../alternatives/commands.md)、[initとdevice管理](../alternatives/init.md)、[libc](../alternatives/libc.md) |
| 過去のBusyBox削減、M5のdevice依存、systemdの起動分析 | [initの資料と履歴](init-history.md) |
| 過去の版・ライセンス・公表benchmark・allocator | [libcの資料と履歴](libc-history.md) |
| SquashFSの並び・圧縮・観測手段 | [rootfsの読込み順](../storage/rootfs-read-order.md) |
| Wi-Fiの接続管理・IP・DNS・未実装部分 | [接続管理の比較と計画](../alternatives/network.md) |
| 最小特権・設定の信頼・通信前の制限 | [権限設計](../security/README.md) |
| SSH・VPN・鍵保管の調査のみの範囲 | [SSH・VPN](../ssh-vpn-and-keys.md) |

driver・firmwareの選択だけでWi-Fi接続可能とは扱いません。認証、IP・DNS設定、firewall、AppArmor profile等は製品未実装です。kernel設定・生成物・runtimeの強制は別々に確かめます。

## 重複した要約と、時点の違う記録

旧本文の末尾にあったinit/libcの要約は、前半のdevice依存表・候補表・版表へ対応づけました。元の段落・表を[原文記録CSV](original-summaries.csv)へ保存し、統合理由と対応先も同じ行に残します。「未確認」の語を削って確認済みに見せる整理はしません。

特に旧libc要約では版の情報を未確認としていますが、同じ原稿の版・出典表や後の比較とは時点が異なります。古い版の値を今日の最新版に置き換えず、現在の比較へ案内します。第三者のbenchmarkはCPU、ABI、版、静的・動的リンク等の条件を保ち、CM0実機の性能や採用構成の起動時間へ読み替えません。

分割・統合の対応、全範囲の保存、CSVの同一性、改変検出、検査の限界は[保存照合の記録](../../experiments/2026-11-03-userspace-security-layout.md)に残します。
