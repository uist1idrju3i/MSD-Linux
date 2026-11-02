# カーネル版・PREEMPT と起動時間の比較

[起動・カーネルの入口](boot-and-kernel.md) / [調査の索引](../../RESEARCH.md)

以下は公開資料の調査記録です。測定条件と未確認の記述を含め、元の節を保持しています。現在の実装は [BUILD.md](../BUILD.md) で確認してください。

## 20. 6.18 以降の起動時間変更・カーネル比較・PREEMPT

### 20.1 起動時間（6.18 以降の変更）
- **結論:** BCM2837 級 arm64 で「6.18 以降に起動が速く/遅くなった」と実測した情報は見つかりませんでした。Phoronix の 7.0〜7.3 記事は性能記事が中心です。https://www.phoronix.com/search/Linux%207.3
- 起動時間に効きうる変更は少なく、多くは条件付き(RT のみ・eMMC のみ・x86/大メモリ向け)か未マージ:
  - printk スレッド化の「console_lock を record ごとに解放」は **RT 限定**(printk-for-6.19 pull 文面。一次):https://lkml.iu.edu/2512.0/00981.html → 非 RT の CM0 には**効かない可能性が高い(推測)**。
  - 7.3:`printk: Postpone kthread startup`(NBCON printer kthread を subsys_initcall へ)=安定化。https://www.phoronix.com/news/Linux-7.3-KThreads-NBCON(二次)
  - 7.1:`deferred_probe_timeout` を Kconfig 化(`56e3ee721b33`、一次):https://github.com/torvalds/linux/commit/56e3ee721b33
  - MMC: `bcm2835.c`（sdhost）は 6.18 → 7.2 で差分 0、7.2 → 7.3-rc7 で DMA device 取得の変更 36 行があります。tuning / CMD 1 polling の短縮提案（2026-09）は未 merge で eMMC / dw_mmc 向けのため、SDHCI 標準経路は対象外です。https://github.com/raspberrypi/linux/compare/rpi-6.18.y...rpi-7.2.y<br>https://github.com/raspberrypi/linux/compare/rpi-7.2.y...rpi-7.3.y<br>https://lkml.iu.edu/2609.2/00512.html
  - init_on_alloc 一括クリア(7.2。数値は **AMD 送信・16GB HugeTLB 条件**:0.445s→0.166s。CM0 に当てはめ不可):https://www.spinics.net/lists/kernel/msg6184200.html
  - 「mmc: core: Optimize boot time by detecting cards simultaneously」は 2015 年のコミットで、6.18 以降の変更ではありません。https://github.com/torvalds/linux/search?q=Optimize+boot+time+by+detecting+cards+simultaneously&type=commits
- 外部の起動時間報告(x86、CM0 に外挿不可。原因がカーネル回帰とは限らない事例):**Omarchy #6996**(Omarchy 4.0.0-1 / Linux 7.1.8-arch1-3、AMD+NVIDIA 混在機。約 266MiB の initramfs と `initramfs_async=0`。`1min 15.918s (kernel)`。2026-08-15 作成、取得時 open)https://github.com/omacom/omarchy/issues/6996 (リポジトリ移転済み。旧 URL は HTTP 404)。**CachyOS**(7.2 カーネルで graphical.target @1min 32.184s、6.18.48-1-cachyos-lts は @8.960s、x86)https://discuss.cachyos.org/t/7-2-kernel-boot-times-drastically-slower-than-6-18-lts/35306 :critical-chain に `cryptsetup.target` があり、**投稿者は後に「BIOS で TPM を無効にして解消」と報告(2026-09-10)**。7.2 カーネル自体の回帰と断定できない【二次・ユーザー報告】
- 未確認事項: kernelnewbies 7.3 は後半未読、LWN 個別記事の精読は一部のみ、全履歴の `git log` 検索は未実施、乱数サブシステムの 6.18 以降の変更は未調査です。確認先: https://kernelnewbies.org/Linux_7.3<br>https://lwn.net/Articles/

### 20.2 カーネル比較（6.18 対 7.x）
| 項目 | 内容 | 確認度 |
|---|---|---|
| RPi 公式既定 | `rpi-6.18.y`（6.18.57、リポジトリ既定ブランチ）。RPi OS Trixie 2026-10-06 イメージは 6.18.50。`rpi-7.2.y` = 7.2.11、`rpi-7.3.y` = 7.3.0-rc7（いずれも 2026-10-18 時点）。 | 一次。https://downloads.raspberrypi.com/raspios_arm64/release_notes.txt<br>https://github.com/raspberrypi/linux/tree/rpi-6.18.y<br>https://github.com/raspberrypi/linux/tree/rpi-7.2.y<br>https://github.com/raspberrypi/linux/tree/rpi-7.3.y |
| M5 ドライバ互換 | 7.1 で `drm_simple_display_pipe` 系 / `mipi_dbi_dev_init_with_formats` などが削除され、M5 の `panel-mipi-dbi-m.c` は 7.2 ではそのままでは API 不整合（header に存在しない関数 6 個）です。7.0 で `snd_soc_dapm_kcontrol_component/dapm` の別名が削除され、`es8389_m5stack.c` が影響します。ビルド可否は未確認で、API の存在確認までです。 | 一次（API 存在確認まで）。https://github.com/raspberrypi/linux/tree/rpi-7.2.y<br>https://github.com/m5stack/m5stack-linux-dtoverlays/tree/75518549a2640486f5d13ea72ca4935b198d7c20/modules |
| 起動時間(6.18 vs 7.2/7.3) | 同条件の公表実測は見つかっていません。ソース差分では SD ホスト（bcm2835 sdhost）・KASLR・圧縮展開コードは 6.18 → 7.2 で差分 0 です。 | 一次（差分の有無） / 推測（速度影響）。https://github.com/raspberrypi/linux/compare/rpi-6.18.y...rpi-7.2.y |
| 運用 | 7.0 / 7.1 は約 11 週で EOL（Wikipedia、二次）。6.18 LTS は予定 EOL 2028-12（kernel.org）。次の LTS 候補 7.4 は kernel.org が事前に公表しません。 | 一次 / 二次。https://en.wikipedia.org/wiki/Linux_kernel_version_history<br>https://www.kernel.org/category/releases.html |
| 評価 | 本番基準は 6.18.y、7.2 は同一構成での比較用とする案です。7.3 final 後または LTS 化された 7.4 を検討し、差（中央値 −300 ms 以上など）が出たら移行を検討します。閾値は仮置きです。 | 推測 |
- 7.3 final は 2026-10-18 公開予定と報じられるが、取得時点で未確認。

### 20.3 PREEMPT の確認結果
| カーネル | 事実 | 出典URL(コミット固定) |
|---|---|---|
| **6.18** | `Kconfig.preempt` の選択肢 `default PREEMPT_NONE`。`PREEMPT_VOLUNTARY` は `depends on !ARCH_NO_PREEMPT` と `!PREEMPT_RT` のみです。arm64 の Kconfig は `ARCH_NO_PREEMPT` を select していないため、VOLUNTARY は選択可能です。RPi の `bcm2711_defconfig` は `CONFIG_PREEMPT=y`（VOLUNTARY ではない）です。 | https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/kernel/Kconfig.preempt#L17-L52<br>https://github.com/raspberrypi/linux/blob/234188315037848e5b07d65b85d38edc64095caa/arch/arm64/configs/bcm2711_defconfig#L10 |
| **7.2** | 既定は `default PREEMPT_LAZY if ARCH_HAS_PREEMPT_LAZY`（arm64 は `select ARCH_HAS_PREEMPT_LAZY`、arch/arm64/Kconfig L44）です。`PREEMPT_NONE` は `depends on ARCH_NO_PREEMPT`、`PREEMPT_VOLUNTARY` は `depends on !ARCH_HAS_PREEMPT_LAZY` です。arm64 は LAZY を持つため、NONE も VOLUNTARY も選べず、FULL / LAZY のみです。 | https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/kernel/Kconfig.preempt#L17-L45<br>https://github.com/raspberrypi/linux/blob/61d337138d273f134f41ef06eb0dd97c90123934/arch/arm64/Kconfig#L44 |
- 【推測】起動時間のために VOLUNTARY / NONE を使う場合は 6.18 系に留まる必要があります。7.2 以降は PREEMPT_LAZY（または FULL）固定です。VOLUNTARY が起動時間に有利かは未測定です。PREEMPT_RT は採用済みです（2026-10-30）。
- 注意: 7.2 の RPi defconfig は確認できていません。6.18 では `CONFIG_PREEMPT=y` です。
- 7.0 の preempt モデル制限(コミット `7dadeaa6e851`)の外部報告:Graviton4(96vCPU)で pgbench 0.51x(スループット。**起動時間ではない・CM0 に不適用**)、LWN は「実は回帰ではない」と整理 https://lwn.net/Articles/1067029/ (二次)。

### 20.4 printk 方針
- **測定ビルドは PRINTK=y（`initcall_debug`・`printk.time=1`）、量産ビルドは `quiet` + 低 loglevel とし、PRINTK=n は別バイナリで試すのみ**とする案です（推測）。
- 6.19 の printk 改善は RT 限定の記述であり、非 RT の CM0 には効果が見込みにくい。7.3 の NBCON kthread 起動遅延は安定化目的で、コンソール出力開始が遅れる可能性は**推測**(測定なし)。

### 20.5 リスク: arm64 linear alias unmap 変更
一次（GitHub commit、2026-10-18 に確認）:
- **63e0b6a5b693**（2026-06-02、「kernel data/bss の線形エイリアス unmap」）と、その **revert f102131c842d**（2026-06-10）は、ともに v7.2-rc1、v7.2、v7.3-rc1 に含まれます。v7.2 では導入と revert が相殺されます。revert のメッセージ:「Unmapping the kernel '.bss' appears to break KVM initialisation on some devices, breaking the boot on popular platforms such as RaspberryPi3 and 4」。https://github.com/torvalds/linux/commit/63e0b6a5b693<br>https://github.com/torvalds/linux/commit/f102131c842d
- **再適用 fb0f3ef5601a**（2026-08-07）は v7.3-rc1 にのみ入り、v7.2-rc1 より後、v7.2 とは分岐し、v7.3-rc1 より前です。メッセージはハイバネーション時の map/unmap 処理を追加する内容で、KVM の問題が解消したとは記していません。https://github.com/torvalds/linux/commit/fb0f3ef5601a
- RPi ツリー:`rpi-7.2.y` の mmu.c は「Map the kernel data/bss read-only」の旧コード(影響なし)。`rpi-7.3.y` は再適用後のコード(`mark_linear_data_alias_valid` と PM notifier)を含む。
- **CM0(BCM2837、Cortex-A53)で 7.3 系(再適用後)が起動するかは未確認**。revert メッセージは RPi 3/4 を挙げている(BCM2837 は RPi 3)ので、7.3 採用時は「起動確認を最初の実機試験に置く」(推測)。7.2 系は上記の理由で当該リスクを持たない(7.2 にその他の CM0 固有の問題が無いことは別途未確認)。
