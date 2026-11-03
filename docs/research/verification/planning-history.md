# 過去の実施順と分類の記録

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

以下は日付付きの作業履歴です。「完了」「実行中」、カーネル版、当時の優先順位を現在の作業指示にはしません。
試験の現在の更新先は[S1–S17](experiment-catalog.md)、未解決の確認は[未確認事項](open-questions.md)です。
S6の`BLK_DEV_WRITE_MOUNTED=n`は後の実験で`/data`自動拡張と衝突しました。[実験記録](../../experiments/2026-10-30-s6-tierb-hardening.md)を優先します。
「上の実機測定項目」は[実機測定](hardware-measurements.md)へ分けています。

#### 実施順（2026-10-20 時点）

2026-10-22 時点の残りのタスクは、[作業の振り返りと残タスク](../retrospective-2026-10.md) の 4 節にまとめています。

下の「次の作業計画（2026-10-19 時点）」を次の順に置き換えます。

1. S11 watchdog と init script の stop 処理
2. 小さい項目: S10、温度、S15
3. S12 と EROFS
4. S1・S14 の本番（S6 tier B、`quiet`・`lpj=`・PREEMPT、カーネルの圧縮方式を含む）と、任意機能のドライバーのモジュール化
5. S13
6. S16 → S4・S5・S17
7. 起動時のファイルアクセスを観測し、`mksquashfs -sort` と小項目（zram、dm-verity、BusyBox、Lynis）の記録を進める

### 次の作業計画（2026-11-01 時点）

2026-10-29/30 のラウンドで済んだもの: 依存更新（Buildroot 2026.08.1、m5stack-dtoverlays、Trivy 0.76.1、Debian digest、fonttools 4.68.0）、cryptsetup（veritysetup）の dev イメージへの追加と QEMU の SHA-256 ラベル化（#116）、sweep ツール修正と icount `sleep=off`（#118 に同梱）、Lite 判定の QEMU 確認（#118）、QEMU 11.1.2 の icount 実時間 8 倍問題の原因絞り込み（#119）、温度模擬（#120）、quiet/lpj（#123）、S5（#124）、S16（#122）、S17 速度模擬（#125）、EROFS（#126）、PREEMPT モデル比較（#127）、S4・S17 エラー注入（#128）、ドライバー・モジュール化（#129）。カーネルは 6.18.58 のまま（依存側の新バージョン対応を確認してから別 PR で上げる方針）。

2026-10-31/11-01 のラウンドで済んだもの: v4l-utils 削減と実機カメラ確認手順（#156）、kernel rpi-6.18.y の b3495ea への更新（#157）、msd-dev の golang digest 更新（#158）、QEMU 11.1.3 の icount 比較（11.0.2 の 20 s に対し 150 s と 7.5 倍遅く、bisect 済みの WFE sleeping 修正でも解消しなかったため bump 見送り）、S17 blkdebug 障害注入（発火はホスト側で確認、QEMU SD モデルがエラーをゲストに伝播しないことを確定）。セキュリティ強化項目の調査を [security-2026-11-hardening-list](../security/history/README.md) にまとめた（実装は未着手、調査のみ）。

| 順 | 作業 | 内容と完了の条件 |
|---|---|---|
| 1 | S1・S14 本番 | 完了: 80 候補の記録 #137、採用 16 件は #138・#139。 |
| 2 | S6 tier B | 完了: 24 候補の記録 #140、15 件採用は #141。`quiet`・`lpj=`・PREEMPT・モジュール化は完了（#123、#127、#129）。 |
| 3 | S13 | 完了: #136 の記録、-Os+LTO 採用は #141。 |
| 4 | PREEMPT_RT の製品化 | 完了: #133。実機でのレイテンシー評価は実機チェックリストへ。 |
| 5 | QEMU の icount 実時間問題 | 完了: bisect で `01b223f895`（A-profile WFE sleeping）と特定（#143）。11.1.3 でも 7.5 倍遅いままのため QEMU は 11.0.2 を継続使用（`tools/qemu-bisect/build-qemu.sh` でビルド、pins-check で新版を検出したら遅延が解消したかを比較してから bump）。 |
| 6 | S2 の続き | 完了: v4l-utils を `v4l2-ctl`・`media-ctl`・`ir-keytable`・`ir-ctl` の 4 本に削減し RC keymap を削除（#156）。実機カメラ確認は `tools/hw/camera-check.sh` と `docs/VERIFY.md` の手順で実機待ち。 |
| 7 | 実機依存の項目 | S7 IR、S9 powerfail の実電源試験、S8 IP2315、実機が届いたら最初に測る項目、周辺機器のモジュール自動ロード、ゲスト観測型のストレージ障害注入（QEMU の SD モデルはエラーをゲストに伝播しないため実機のみ）。 |
| 8 | セキュリティ強化の実装（調査済み・未実装） | [security-2026-11-hardening-list](../security/history/README.md) の優先順位案に沿って、fstab の noexec/nosuid 追加、sysctl ファイル整備、cmdline 追加、nftables、DoT（unbound）、chrony+NTS、AppArmor プロファイルを段階導入。実装するか・順番はユーザー確認後。 |
| 9 | 監査 | 各段階で、チャット・計画書・この表を origin/main と照らし合わせ、済んだものと済んでいないものを報告する。 |

保留: libcamera と VideoCore の ISP（カメラの tier B）は、VCHIQ と firmware の変更が必要で、起動時間と RAM への影響が大きいため、使う場面が決まるまで入れません。Raspberry Pi Zero 2 W は用意しません。CardputerZero が手に入らない場合に限り、代わりの実機として検討します。

実機が届いたら、上の「実機が届いたら最初に測る項目」に加えて、実際の周辺機器（Wi-Fi、Bluetooth、音声、USB ネットワーク）でモジュールが自動でロードされることを確かめます。

#### S6 tier B の分類

S6（#31）のあとの kernel-hardening-checker v0.6.17.1 の FAIL は 111 件です（cmdline・sysctl の項目と、同じ項目の重複判定を含みます）。分類は次のとおりで、【要確認】は実装の前にビルドで確かめます。

1. **A53（ARMv8.0）では使えないため対処しない:** `ARM64_BTI_KERNEL`（ARMv8.5）、`KASAN_HW_TAGS`（MTE、ARMv8.5）、`ARM_SMMU` 系（BCM2837 に SMMU はない）、`EFI_DISABLE_PCI_DMA`・`RESET_ATTACK_MITIGATION`・cmdline の `efi`（EFI 起動ではない）、`SCHED_CORE`・`nosmt`（SMT はない）、`CFI_CLANG`・`CFI_PERMISSIVE`（Clang が必要）。
2. **ツールチェーンしだい【要確認】:** `SHADOW_CALL_STACK`（GCC の aarch64 対応）、`RANDSTRUCT_FULL`・`GCC_PLUGIN_LATENT_ENTROPY`（GCC plugin を作れるか）、`ARM64_SW_TTBR0_PAN`（A53 に PAN がなくソフトウェアで模擬するため、システムコールのコストを測る）。
3. **低コストの候補（tier B として測る）:** `SLAB_FREELIST_HARDENED`、`SLAB_FREELIST_RANDOM`、`SLAB_MERGE_DEFAULT=n`、`RANDOM_KMALLOC_CACHES`、`LIST_HARDENED`、`BUG_ON_DATA_CORRUPTION`、`SHUFFLE_PAGE_ALLOCATOR`、`FORTIFY_SOURCE`、`ZERO_CALL_USED_REGS`、`RANDOMIZE_KSTACK_OFFSET_DEFAULT`、`RODATA_FULL_DEFAULT_ENABLED`、`DEBUG_WX`、`DEFAULT_MMAP_MIN_ADDR=65536`、`ARCH_MMAP_RND_BITS` の最大化、`SECURITY_DMESG_RESTRICT`、`LEGACY_TIOCSTI=n`、`LDISC_AUTOLOAD=n`、`PROC_MEM_NO_FORCE`、`STRICT_DEVMEM`・`IO_STRICT_DEVMEM`・`DEVPORT=n`、`SECURITY_LANDLOCK`、`SECURITY_LOCKDOWN_LSM`（integrity モード）、`MODULE_SIG_SHA512`、`BLK_DEV_WRITE_MOUNTED=n`（msd-update と両立するかを試験で確かめる）。
4. **コストが大きいため既定では入れず、開発用イメージの選択肢にする:** `INIT_ON_ALLOC_DEFAULT_ON`、`INIT_ON_FREE_DEFAULT_ON`、`KSTACK_ERASE` 系、`UBSAN` 系、`KFENCE` 系、`PAGE_TABLE_CHECK` 系、`DEBUG_VIRTUAL`・`DEBUG_SG`・`DEBUG_NOTIFIERS`、`WERROR`。
5. **機能を削るもの:** `MODULES`、`VT`、`FB` は CardputerZero の機能（後から挿す USB 機器、コンソール、LCD）に使うので残します。`STATIC_USERMODEHELPER` と `RSEQ` は、mdev と glibc への影響を確かめてから決めます。`DEBUG_FS`、`FTRACE`・`KPROBES` 系、`KALLSYMS`、`BPF_SYSCALL`、`USER_NS`、`IO_URING`、`AIO`、`MAGIC_SYSRQ`、`COREDUMP`、`CHECKPOINT_RESTORE`、`COMPAT` などは S1 の削減候補と重なるため、S1 の本番で影響を測ってから決めます。
