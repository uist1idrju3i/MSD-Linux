# 強化項目の調査履歴と現在の読み方

[権限設計へ戻る](../README.md) / [調査の索引](../../../../RESEARCH.md) / [保存照合](../../../experiments/2026-11-03-userspace-security-layout.md)

元の「セキュリティ強化項目の調査（2026-11-01）」を、主題ごとに移しました。下段の前提・優先順位・検証方法も当時の記録です。「採用方向」「導入しない」「最新」という語を現在の実装状態や永久の採否へ読み替えません。本文の数値・条件・出典は保存し、現在の注記はこの案内と各本文の冒頭に分けています。

| 調べたいこと | 履歴 | 現在の比較・設計 |
|---|---|---|
| firewall、DNS、DoT、NTS | [通信](network.md) | [接続管理](../../alternatives/network.md)、[通信開始前の制限](../network.md) |
| cmdline、LSM、IRQ、I/O、mount、sysctl | [kernelとmount](kernel-and-mounts.md) | [権限と可変設定](../privileges.md)、[試験の未解決事項](../../verification/open-questions.md) |
| IDS・監査・AV等の見送り案 | [監視](monitoring.md) | [段階導入と拒否試験](../verification.md) |
| systemd sandbox、compiler hardening、Rust | [softwareとsandbox](software-and-sandbox.md) | [init](../../alternatives/init.md)、[compiler](../../alternatives/toolchains.md)、[Linuxの制限機構](../principles.md) |

## 現在の状態と訂正

製品はBusyBox initとmdevです。firewall・AppArmor userspace/profile・専用user・分離した更新helperの実装や、Wi-Fi実機接続の確認はまだありません。現在の順序は、[権限設計](../README.md#優先順位と未決定事項)のとおり、通信を始める前に必要な制限を強制して正負の試験を行う案です。下の履歴にある「まずnftables、後でAppArmor」をそのまま実装指示にはしません。

| 履歴で注意する記述 | 今の読み方・根拠 |
|---|---|
| ARM組込みはACPIではない、irqbalanceは不要 | CM0のDeviceTree構成とARM全般を区別する。irqbalanceの費用・効果は推測で、同条件の実機測定なしに優劣を確定しない。[CPU/IRQの調査](../../cpu-irq-and-sysctl.md) |
| unboundが唯一実用的 | 固定Buildrootにstubby packageがないことと、全候補の実用性は別。[接続管理の候補](../../alternatives/network.md)を先に比較する |
| `sysctl -p`は`sysctl.d`も読む | 固定BusyBox 1.38.0は引数なしの`-p`で`/etc/sysctl.conf`を読み、引数はファイルとして順に開く。directory自動走査はしない。起動時に何を呼ぶかは別に定める。[固定sourceと確認方法](kernel-and-mounts.md#busyboxのsysctl読込み) |
| PIE等の選択は全packageに同じcompiler引数を与える | 共通設定、外部toolchain、package固有の処理、生成ELFを分けて確認する。[compiler比較](../../alternatives/toolchains.md) |
| Rust表の「最新情報」 | 元の表見出しは2025-11-01、原稿名は2026-11-01。誤記と推定して日付を直さず、現在の最新情報として使わない |

既存のAppArmor、時刻、noexec等の訂正は[訂正記録](../../corrections.md)と[Linuxの機構](../principles.md)を参照します。原稿の前提・候補を保存したことは、profile・ruleの稼働や実機性能の確認とは異なります。

## 原稿の前提と導入順の記録

2026-11-02に、設定と実行時の強制を混同する箇所、署名と時刻、noexec等の記述を[訂正記録](../../corrections.md)に根拠を残して更新しました。採用方向という表現は導入方針であり、firewall・AppArmor profile等が製品で稼働しているという意味ではありません。具体的な権限・起動順・拒否試験は[権限設計](../README.md)を参照してください。

ユーザーから提示された強化項目を、MSD/Linux（Buildroot + BusyBox、systemd・deb 系なし、ターゲットは BCM2837 / 512 MiB RAM / microSD 起動 / RO SquashFS + A/B 更新）へ適用する観点で調査した。各項目について、現行構成との照合、適用可否、推奨、検証方法を示す。なお現在この機器には**ネットワーク設定自体が未導入**（`udhcpc` は busybox に入っているが interfaces・resolv.conf 系の設定がなく、起動時に net を上げる init もない）ため、ネットワーク前提の項目は「ネットワーク導入時の設計」として整理する。

【一次】現行構成の一次情報は `configs/msd_cardputerzero_defconfig`、`board/cardputerzero/linux.fragment`、`board/cardputerzero/busybox.fragment`、`board/cardputerzero/rootfs-overlay/etc/fstab`、`cmdline_rootfs_{a,b}.txt`、およびビルド済み `output/build/{linux-custom,busybox-1.38.0}/.config` に基づく。

## 実装の優先順位案

1. **先にやる（低コスト）**: `fstab` の `/tmp`・`/run`・`/dev/shm` への `noexec`/`nosuid`/`nodev` 追加、`/data` `noexec` の採否結論、sysctl ファイルの整備、`mitigations=auto` 等の cmdline 追加。
2. **中**: `nftables`（`BR2_PACKAGE_NFTABLES` + 静的ルール）、`BR2_PACKAGE_CA_CERTIFICATES`、DoT 用 unbound/stubby、chrony + NTS。
3. **後で評価**: AppArmor プロファイル整備（complain 観測 → enforce）、io scheduler 実測、qdisc/BBR、hidepid。
4. **対象外**: acpid、irqbalance、SELinux（本機では AppArmor）、debsums（deb なし）、systemd 系（なし）、Suricata/Falco（調査のみ）。

## 検証方法

- カーネル・sysctl・マウント・nftables は QEMU で回帰確認（起動時間差分は S1/S14 方式で測る）。
- DoT/NTS は実 DNS/時刻サーバへの到達性が要るため QEMU ネットワーク構成での確認が必要。実機での時間確立と TLS 失敗時の挙動も要確認。
- 実験は experiment-record スキルに従い、`docs/experiments/` に記録する。
