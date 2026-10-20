# アイデア総覧

RESEARCH.md から分割した節です。

## アイデア総覧

この表は高速化・電源断・A/B 案に、ストレージ、セキュリティ、ハードウェア機能の案を加えた一覧です。QEMU で確認できるのは仮想化された Linux・イメージ・更新処理に限られ、ファームウェアの選択、SD 性能、実物の周辺機器、電源断は実機で確認します。優先度は目安です。状態は `origin/main` のコードと設定に照合しました。「採用済み」は実装の存在を示し、実機動作の確認を意味しません。

| 分類 | アイデア | 期待効果 | コスト | リスク | 検証（QEMU / 実機） | 優先度 | 状態 |
|---|---|---|---|---|---|---|---|
| 高速化 | [`kernel8.img` gzip 再圧縮](fastboot-ideas.md#高速化のアイデア一覧) | 読込量を減らす | 再現可能なカーネル生成 | 展開時間やファームウェア互換 | QEMU: 起動 / 実機: 読込・展開時間 | P2 | 一部採用（圧縮方式・サイズ比較あり、非圧縮実測なし） |
| 高速化 | [`start_cd.elf` / `fixup_cd.dat`](fastboot-ideas.md#高速化のアイデア一覧) | 小さいファームウェアの可能性 | 低 | GPU/ファームウェア互換 | QEMU: ファームウェア不可 / 実機: 起動 | P3 | 採用済み（実機未確認） |
| 高速化 | [`boot_delay=0` / `disable_splash=1`](fastboot-ideas.md#高速化のアイデア一覧) | 不要な待機・表示を減らす | 低 | 診断情報を隠す可能性 | QEMU: Linux 部分のみ / 実機: 起動時間 | P2 | 採用済み（効果未実測） |
| 高速化 | [未使用 dtoverlay の削除](fastboot-ideas.md#高速化のアイデア一覧) | 不要初期化探索を抑える | 中 | 必須機能喪失 | QEMU: DT / 実機: 全機能 | P2 | 未着手 |
| 高速化 | [必須ドライバー組み込み、任意機能モジュール](fastboot-ideas.md#高速化のアイデア一覧) | 任意初期化探索を遅らせる | 中 | モジュール依存順・起動不能 | QEMU: 起動 / 実機: LCD・入力 | P1 | 未着手 |
| 高速化 | [`quiet` / `lpj=` / `initcall_debug`](fastboot-ideas.md#高速化のアイデア一覧) | printk 負荷・遅い initcall の評価 | 低 | `lpj` 誤設定、測定付加負荷 | QEMU: log / 実機: 時間 | P2 | 一部採用（quiet のみ） |
| 高速化 | [ST7789 DRM panel + fbcon](fastboot-ideas.md#高速化のアイデア一覧) | HDMI/GUI なしの CLI | 中 | console blank / 割当違い | QEMU: 不可 / 実機: LCD | P1 | 未着手 |
| 高速化 | [initramfs を使わず `root=` を直接指定](fastboot-ideas.md#高速化のアイデア一覧) | 読込・展開・RAM を削減 | 中 | root ドライバー不足 | QEMU: 起動 / 実機: 起動時間 | P2 | 採用済み |
| 高速化 | [`initramfs_async=`](fastboot-ideas.md#高速化のアイデア一覧) | 展開と他処理を重ねる可能性 | 低 | 効果が負荷条件依存 | QEMU: 比較 / 実機: 起動時間 | P3 | 対象外（initramfs なし） |
| 軽量化 | [SquashFS と EROFS の比較](fastboot-ideas.md#高速化のアイデア一覧) | サイズ・読込・CPU の選択 | 中 | 圧縮・起動要件の差 | QEMU: 機能 / 実機: I/O・RAM | P2 | 未着手 |
| 軽量化 | [BusyBox init + mdev](fastboot-ideas.md#高速化のアイデア一覧) | ユーザー空間/サービスを小さくする | 中 | udev ルール / systemd 依存 | QEMU: デバイス / 実機: 全機能 | P3 | 採用済み |
| 高速化 | [読み取り専用 SquashFS と preload/readahead](fastboot-ideas.md#高速化のアイデア一覧) | 不要な先読みを避ける | 低 | 必要な読込まで遅れる | QEMU: I/O 観測 / 実機: 起動時間 | P3 | 一部採用（SquashFS rootfs、先読み未実施） |
| 高速化 | [`mksquashfs -sort`](fastboot-ideas.md#高速化のアイデア一覧) | 起動ファイルの配置を最適化 | 低 | open 順と I/O 順が不一致 | QEMU: イメージ / 実機: SD 読込 | P3 | 未着手 |
| 高速化 | [fanotify / strace / blktrace](fastboot-ideas.md#高速化のアイデア一覧) | 起動 I/O の把握 | 中 | 監視付加負荷 | QEMU: trace / 実機: 比較測定 | P2 | 未着手 |
| 軽量化 | [不要カーネル機能・DTB の削減](fastboot-ideas.md#高速化のアイデア一覧) | イメージと初期化を減らす | 中 | 必須周辺機器を失う | QEMU: 起動 / 実機: 全機能 | P2 | 未着手 |
| 高速化 | [Wi-Fi/camera/display 自動検出抑制](fastboot-ideas.md#高速化のアイデア一覧) | 未使用初期化探索を減らす可能性 | 中 | 全機能維持の柱と衝突するため遅延ロードで代替 | QEMU: 一部 / 実機: 対象機能 | P3 | 対象外（遅延ロードで代替） |
| 高速化 | [`max_framebuffers` / ファームウェア KMS](fastboot-ideas.md#高速化のアイデア一覧) | HDMI 初期化を抑える可能性 | 低 | LCD/HDMI と競合 | QEMU: 限定 / 実機: 表示 | P3 | 未着手 |
| 高速化 | [`core_freq` / `initial_turbo`](fastboot-ideas.md#高速化のアイデア一覧) | 起動ファームウェア読込時間を短縮する可能性 | 低 | 発熱・電力・UART clock | QEMU: 不可 / 実機: 時間・温度 | P3 | 未着手 |
| 軽量化 | [BusyBox applet 最小化・fork削減](fastboot-ideas.md#高速化のアイデア一覧) | ユーザー空間処理を削減 | 中 | 実行時に必要コマンド不足 | QEMU: 起動 / 実機: 利用操作 | P3 | 未着手 |
| 軽量化 | [static link / LTO / UPX](fastboot-ideas.md#高速化のアイデア一覧) | 配布サイズや load を比較 | 中 | サイズ増・展開 CPU | QEMU: 起動 / 実機: 時間・RSS | P3 | 未着手 |
| 高速化 | [ネットワーク起動を終点後へ遅延](fastboot-ideas.md#高速化のアイデア一覧) | 対話可能になる前のネットワークサービスを減らす | 低 | 利用可能になるまで遅れる | QEMU: サービス / 実機: 入力時点 | P2 | 未着手 |
| 軽量化 | [systemd ユニットの削減](fastboot-ideas.md#高速化のアイデア一覧) | 不要ユニットを減らす | 中 | BusyBox init を使うため対象外 | QEMU: ユニット / 実機: 時間 | P3 | 対象外（BusyBox init 使用） |
| 軽量化 | [libc / allocator 比較](fastboot-ideas.md#高速化のアイデア一覧) | 起動・RAM・サイズ最適化 | 高 | ABI/互換性・測定条件 | QEMU: 機能 / 実機: RAM・時間 | P3 | 未着手 |
| 高速化 | [カーネル gzip / 非圧縮比較](fastboot-ideas.md#高速化のアイデア一覧) | 読込時間と展開時間を最適化 | 低 | ファームウェア対応形式 | QEMU: Linux / 実機: 起動経路 | P2 | 一部採用（gzip 方式の生成時比較、非圧縮実測なし） |
| 高速化 | [GPU ファームウェアを省くブートローダー](fastboot-ideas.md#高速化のアイデア一覧) | ファームウェア段を短縮する可能性 | 高 | 非公式・SoC 互換性 | QEMU: 不可 / 実機: 起動信頼性 | P3 | 未着手 |
| 高速化 | [PREEMPT / printk 比較](fastboot-ideas.md#高速化のアイデア一覧) | 起動ログ・init 付加負荷の評価 | 低 | 起動時間以外の影響 | QEMU: 起動 / 実機: 時間 | P3 | 未着手 |
| 信頼性 | [読み取り専用 SquashFS rootfs](power-and-updates.md) | rootfs の永続書込みをなくす | 現行構成 | 可変領域の容量・電断 | QEMU: マウント/update / 実機: 電断 | P1 | 採用済み |
| 信頼性 | [`align = 4M`](../../docs/research/storage-and-flash.md) | 全パーティション開始位置を 4 MiB 境界にする | イメージが約16 MiB増 | 実機効果・ファームウェア互換性未確認 | QEMU: レイアウト / 実機: 性能・電断 | P1 | 採用（#19。`genimage.cfg` の `align = 4M` と、`check-image-layout.sh` の 8192 sector 境界の検査）。実機での性能と電断は未確認 |
| 信頼性 | [FAT data-area offset の扱い](../../docs/research/storage-and-flash.md) | ファイルシステム内部位置を把握 | フォーマッター/レイアウト変更 | パーティション alignment だけでは変わらない | QEMU: BPB / 実機: カード性能 | P2 | 一部調査済み（offset 測定済み、性能未測定） |
| 信頼性 | [`data=ordered` 移行検討](../../docs/research/storage-and-flash.md) | `data=journal` の非推奨に備える | アプリ・FS 試験 | fsync/rename と電断時整合性 | QEMU: FS / 実機: 電源断 | P1 | 未着手 |
| 信頼性 | [barrier / `commit=` と `/data` 検証](../../docs/research/storage-and-flash.md) | マウント durability を確認 | マウント・アプリ変更の可能性 | SD FTL の保証ではない | QEMU: マウント / 実機: 電断 | P1 | 未着手 |
| 信頼性 | [discard / `fstrim`](../../docs/research/storage-and-flash.md) | 対応時の空き領域通知 | カード・カーネル対応確認 | 未対応や性能差 | QEMU: コマンド / 実機: discard | P2 | 未着手 |
| 信頼性 | [カード erase/AU/sysfs と SD 性能測定](../../docs/research/storage-and-flash.md) | alignment 判断にデータを得る | 複数カード・計測 | 値は erase ユニット / 耐久保証でない | QEMU: 不可 / 実機: fio・sysfs | P1 | 未着手 |
| 信頼性 | [A/B + tryboot + watchdog](../../docs/research/power-and-updates.md) | 起動失敗を検出し旧スロットへ戻す案 | 状態・watchdog・試験 | S01msd-watchdog は実装済み、実機動作は未確認 | QEMU: スロット / 実機: tryboot・ハング | P1 | 採用済み（実機未確認） |
| 信頼性 | [電源異常正常停止](../../docs/research/power-and-updates.md) | 電源異常を graceful 停止に接続 | ドライバー / ユーザー空間変更 | 電源保持時間不足の可能性 | QEMU: 不可 / 実機: 電源試験 | P1 | 未着手 |
| 信頼性 | [更新記録の fsync/rename 原子性](../../docs/research/power-and-updates.md) | 確定記録の破損リスク低減 | 更新処理実装・試験 | FAT 上の原子性未保証 | QEMU: 更新処理 / 実機: 電断 | P1 | 一部採用（fsync・一時ファイル rename、電断未検証） |
| 信頼性 | [p7 ext4 を `msd-data-grow` で拡張](power-and-updates.md) | 利用可能容量を増やす | first-起動 script | 中断時の FS 整合性 | QEMU: サイズ変更 / 実機: 電断 | P2 | 採用済み |
| 信頼性 | [RAUC / SWUpdate / Mender / Rugix 比較](../../docs/research/power-and-updates.md) | 更新方式を選ぶ | 導入・保守負担 | ファームウェア/bootchooser 互換性 | QEMU: package / 実機: ロールバック | P2 | 未着手 |
| セキュリティ | [署名検証・公開鍵配置と鍵運用](../../docs/research/security-hardening.md) | 更新物の真正性 | 署名鍵の運用 | 全 microSD 交換は防げない | QEMU: reject / 実機: 信頼連鎖 | P1 | 一部採用（署名検証・鍵配置あり、鍵運用未確認） |
| セキュリティ | [dm-verity と trusted root digest](../../docs/research/security-hardening.md) | root block 改ざん検知 | 起動 cmdline・digest管理 | digest が同じカードなら無効 | QEMU: corruption / 実機: 信頼起点 | P2 | 未着手 |
| セキュリティ | [`nosuid,nodev,noexec` と sysctl](../../docs/research/security-hardening.md) | `/data` からの権限昇格面を減らす | マウント・互換試験 | アプリ互換性 | QEMU: マウント / 実機: アプリ | P1 | 未着手 |
| セキュリティ | [SSP / FORTIFY / RELRO / PIE](../../docs/research/security-hardening.md) | exploit mitigation（FORTIFY_SOURCE_3 は現行設定） | binary サイズ・ビルド時間 | toolchain/package 互換 | QEMU: ビルド / 実機: アプリ | P2 | 一部採用（FORTIFY_SOURCE_3、残り未監査） |
| セキュリティ | [A/B 更新の署名・SHA-256 manifest・読込-back](../../docs/research/security-hardening.md) | 書込み破損検出・スロットイメージ確認 | 現行更新処理 | 署名鍵の配布・更新・失効手順は要確認 | QEMU: 正常/破損 bundle / 実機: 書込み復旧 | P1 | 採用済み |
| セキュリティ | [未使用 Wi-Fi/BT/USB surface の削減](../../docs/research/security-hardening.md) | attack surface を縮小 | 機能・保守判断 | 無線/USB 機能喪失 | QEMU: 設定 / 実機: peripheral | P2 | 未着手 |
| セキュリティ | [対応 secure-起動 SoC への移行](../../docs/research/security-hardening.md) | ファームウェア信頼連鎖を追加 | 高い BOM・移植費 | board/起動 migration | QEMU: 非対象 / 実機: BootROM | P3 | 未着手 |
| ハードウェア | [ドライバー / ファームウェア / overlay の実機対応表](../../docs/research/hardware-spec.md#ハードウェア機能の対応表) | 未対応・遅延可能機能を把握 | 各機能の個別試験 | 初期化探索成功だけで動作を誤認 | QEMU: 一部 / 実機: 全周辺 | P1 | 一部調査済み（実機動作未確認） |
| ハードウェア | [IR / camera / IP2315 charger の対応調査](hardware-spec.md#目標との差分) | 未実装機能との境界を明確化 | media/charger ドライバー調査 | ハードウェア revision 依存 | QEMU: 設定 / 実機: I/O | P2 | 一部調査済み（実機対応未確認） |
| 試験・保守 | [更新中を含む 200 回電源断試験案](power-and-updates.md) | 電断失敗 rate を評価 | 長時間・試験治具 | 例示合格条件で保証ではない | QEMU: 不可 / 実機: 反復試験 | P1 | 未着手 |
| 試験・保守 | [ホストテスト（msd-update／msd-data-grow／msd-hwinfo）](../../.devin/wiki.json) | 更新・拡張・機器情報処理を回帰検査 | 低 | ホスト試験は実機の周辺機器動作を保証しない | tests/ 配下3 テスト一式／実機：全機能 | P1 | 採用済み |
| 試験・保守 | [SSH / VPN 実装](../../docs/research/userspace-and-security.md) | 遠隔管理 | 鍵・更新・攻撃面 | 現方針では実装対象外 | QEMU: 不要 / 実機: 不要 | P3 | 不採用 |
| 軽量化 | GPU メモリ／CMA 量の見直し | RAM の余地を評価 |調査・測定| 削減で表示機能を損なう可能性 | 実機で必要量を測る | P2 | 未着手 |
| 軽量化 | zram／zswap の評価 | RAM 内の圧縮 swap を評価 |調査・測定| base defconfig は `ZRAM=m`／`ZSWAP=y`、実運用未確認 | QEMU・実機で評価 | P2 | 一部採用（base defconfig、実運用未確認） |
| 信頼性 | `kernel_watchdog_timeout` の OS 引継ぎ | watchdog 起動後給餌 |調査・測定| CM0 対応未確認 | QEMU・実機ハング/リセット | P1 | 一部採用（S01msd-watchdog、ファームウェア handover 未確認） |
| 信頼性 | `get_throttled` 低電圧・温度記録 | 電源・温度異常を記録 |調査・測定| bit 0／16、3／19。実機未測定 | 実機 | P1 | 未着手 |
| 信頼性 | `/data` fsck 時間 | 起動遅延を把握 |調査・測定| `fsck.ext4 -p` 実装済み、時間未測定 | QEMU・実機起動時間 | P1 | 一部採用（fsck 実装、時間未測定） |
| 信頼性 | `/data` ext4 4 KiB block／`inline_data` | 1 KiB と 4 KiB の割り当て量、inode 内保存の候補 |調査・測定| 小さい file での差はローカル測定済み。実機性能は未確認 | QEMU・実機 I/O／fsck | P2 | 候補（効果は未検証） |
| 信頼性 | [`/etc`・`/data` の通常時 RO と `lazytime`](../../docs/research/readonly-data-and-fs.md#提案する-read-only-policy) | persistent write を限定し、通常時の SD 書き込みを減らす | writer の洗い出しと RW window 実装 | journal recovery、seedrng、更新状態、設定変更を壊す可能性 | QEMU: mount/update / 実機: 電断・書き込み量 | P1 | 未着手 |
| 信頼性 | [ext4/F2FS/btrfs の `/data` 比較](../../docs/research/readonly-data-and-fs.md#mount-option-と-ext4f2fsbtrfs-の比較方針) | fsck/mount/recovery、小ファイル、write volume を比較 | image/tool build と測定 | SD FTL 依存、回復 tooling と複雑性 | QEMU: fsck/replay / 実機: 電断・I/O | P1 | 未着手 |
| 信頼性 | [OverlayFS mode と古い `/data/etc` lower の移行](../../docs/research/readonly-data-and-fs.md#overlayfs-の3案) | read-only policy と A/B image defaults を整合 | migration schema と boot logic | 古い設定が新 image を隠す、upper FS xattr 制約 | QEMU: A/B config / 実機: update 回帰 | P1 | 未着手 |
| 試験・保守 | [S17 storage fault/speed emulation](../../docs/research/readonly-data-and-fs.md#s17-ストレージの障害速度の模擬) | write/flush replay、I/O error、delay、帯域制限を検証 | device-mapper/QEMU image と test harness | QEMU/dm は実 SD FTL・物理電断を再現しない | QEMU guest: replay/error / 実機: 電断・SD 性能 | P1 | 未着手 |
| セキュリティ | カーネル Kconfig／sysctl hardening | 攻撃面を緩和 |調査・測定| RAM／CPU／保守コストあり | 設定・実機回帰 | P1 | 未着手 |
| 試験・保守 | [sysctl・I/O スケジューラーなどの既定値の一覧](../../docs/research/tunables-defaults.md) | 調整の出発点を固定する | QEMU で取得済み | QEMU の値は実機と異なる（RAM、SD、cpufreq、温度） | QEMU: 取得済み / 実機: 取り直し | P1 | 一部調査済み（QEMU のみ） |
| 信頼性 | [`kernel.sysrq` を 32 に絞る（0 は不可）](../../docs/research/cpu-irq-and-sysctl.md#vps-運用記事との照合) | 電源断時の remount だけを残す | drop-in 1 つ | 0 にすると `powerfail_suo` の remount が止まる | QEMU: 値と remount / 実機: 電源断 | P1 | 未着手（現在は 502） |
| 信頼性 | [`kernel.panic`／`panic_on_oops` と watchdog・tryboot](../../docs/research/cpu-irq-and-sysctl.md#項目ごとの判断) | ハング時の自動再起動と A/B の失敗検知 | 秒数の設計と試験 | 一時的な oops でも再起動する | QEMU: panic 経路 / 実機: tryboot | P1 | 未着手（現在は 0 / 0） |
| セキュリティ | [情報漏えい・リンク保護の sysctl](../../docs/research/cpu-irq-and-sysctl.md#sysctl-の主な値) | `kptr_restrict`、`dmesg_restrict`、`fs.protected_*`、`ldisc_autoload`、redirect と `rp_filter` | drop-in 1 つ | 開発時のデバッグがしにくくなる | QEMU: 値 / 実機: 回帰 | P1 | 未着手 |
| 高速化 | [I/O スケジューラーと `read_ahead_kb` の比較](../../docs/research/cpu-irq-and-sysctl.md#io-スケジューラーとブロックデバイス) | SquashFS の読み込みと `/data` の書き込み中の遅延 | 実機測定 | 差が小さい可能性【推測】 | QEMU: 不可 / 実機: 起動時間・遅延 | P3 | 未着手（現在は `mq-deadline`、128 KiB） |
| 高速化 | [CPU governor（`ondemand`／`schedutil`／`performance`）と `maxcpus=1`](../../docs/research/cpu-irq-and-sysctl.md#コア数周波数熱) | 起動時間・温度・電力の比較 | 実機測定 | 1 コアでも周波数の上限は上がらない | QEMU: 不可（cpufreq なし） / 実機 | P2 | 未着手 |
| 軽量化 | [irqbalance](../../docs/research/cpu-irq-and-sysctl.md#割り込みの分散と-irqbalance) | なし（カーネルが既に 4 コアへ順に分散） | - | 常駐プロセスが増える | 不要 | - | 不採用 |
| 軽量化 | [CM0 にない機能のカーネルからの削除（NVMe、PCIe、RP1、KVM、binder、NFS、`brd` など）](../../docs/research/cpu-irq-and-sysctl.md#その他のチューニング要素) | 起動時間と RAM の削減 | S1 と合わせて試験 | 必要な機能を誤って外す | QEMU: サイズ・起動 / 実機: 全周辺 | P2 | 未着手 |
| 信頼性 | [ramoops の領域予約](../../docs/research/cpu-irq-and-sysctl.md#その他のチューニング要素) | panic の記録を再起動後に読む | DT／cmdline と試験 | RAM を少し使う | QEMU: 一部 / 実機 | P2 | 未着手（`mem_size` 0） |
| 試験・保守 | [VPS 向け設定（BBR、fq、大きな TCP バッファー、Falco、Suricata、ufw）](../../docs/research/cpu-irq-and-sysctl.md#項目ごとの判断) | サーバー向けで、端末には不要 | - | RAM と保守の負担 | 不要 | - | 不採用 |
| 高速化 | [SquashFS codec／block size の実機比較](../../docs/research/soc-memory-compression.md) | rootfs size と展開・読込時間を比較 | 複数 build と実機測定 | SD rate、cache、CPU clock に依存 | QEMU: 起動 / 実機: SD・CPU | P1 | image size 実測済み、速度未測定 |
| 軽量化 | [kernel compressor / EROFS の削減比較](../../docs/research/soc-memory-compression.md) | `Image` / `vmlinux` size を比較 | kernel build と回帰試験 | rootfs 互換性・全 hardware 維持 | QEMU: mount・A/B / 実機: 起動 | P2 | 未着手 |
| 高速化 | [Buildroot `-O2` / `-Os`、LTO / PGO](../../docs/research/soc-memory-compression.md) | userland size と CPU-bound workload を比較 | build time、profile 回収、再現性 | package 対応と stale profile | QEMU: 機能 / 実機: CPU・起動 | P2 | 未着手 |
| 試験・保守 | [三段階 simulator 検証](simulation-plan.md#シミュレーターと検証基盤の比較) | QEMU 機能、TCG option 比較、実機 timing を分離 | hardware proxy と実機が必要 | QEMU / gem5 の時間を実機値と混同しない | QEMU・gem5・Zero 2 W・CM0 | P1 | 方針案 |
| 開発・CI | [開発環境と CI](../../docs/research/dev-environment-and-ci.md) | ローカルと CI の toolchain をそろえ、検査・起動確認を再現する | 開発イメージと CI の保守 | CI 成果物との比較、速度改善は未確認 | QEMU: 機能確認 / CI: build・artifact | — | 開発イメージ採用、比較結果は予備的 |
