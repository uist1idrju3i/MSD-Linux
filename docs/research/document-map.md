# 文書の配置と整理の判断

[文書案内](../README.md) / [調査の索引](../../RESEARCH.md)

利用・構築・検証は `docs/` の操作文書、採否と公開資料の調査は `docs/research/`、特定の入力に対する測定は `docs/experiments/` に置きます。操作手順はコードと照合して更新します。実験は基準 commit の記録として残し、結論が変われば注記と新しい根拠を足します。

## 主題の本文と重複候補

[導入手順](../INSTALL.md)はPCから全SD imageを書く操作、[更新手順](../UPDATE.md)は端末で既存のA/Bを更新する操作です。[照合記録](install-update-status.md)には、成果物の取得範囲、自動拡張、自動commitとDTの状態についてコードと照合した根拠を置きます。READMEには利用者の最初の手順を残し、管理者の鍵操作や実験の詳細は複製しません。

[署名鍵の設定](../RELEASE-SIGNING.md)は管理者が行う操作、[Releaseの調査](release-security.md)は防御の役割と未実装部分、[更新操作](../UPDATE.md)は現行のA/B処理を説明します。鍵の内容や設定手順を調査本文へ重ねず、相互参照します。

[権限設計](security/README.md)は、OpenBSDの原則をLinuxのservice・UID・device・IPC・通信開始・拒否試験へ対応づける本文です。既存のsecurity-hardeningは物理アクセスと費用、日付付き強化項目は当時の候補として区別し、現行の強制状態と誤読される記述は根拠付きで訂正します。新しい本文は原則・処理・通信・検証に分け、未実装を明記します。

日付付き強化項目とcorrectionsは20,000 bytesを超えています。前者は同じ入力リストの採否を通覧する記録、後者は訂正前・理由・根拠を日時順に追う記録なので、この改訂では条件や訂正表を途中で分割しません。新しい具体設計を別本文へ置き、これらの記録へ設計の詳細を重ねない方針です。

2026-11-02 の整理では、同名に近い節も条件・出典・否定を照合しました。見出しや話題が同じだけでは本文を削りません。

| 重複候補 | 違いと本文の置き場 |
|---|---|
| [前提・ハードウェア](scope-and-hardware.md) / [仕様](hardware-spec.md) / [公式構成](official-software.md) | 前提には設計条件、除外理由、候補別の条件がある。仕様は機能依存と回路の表、公式構成は pi-gen の版・pin・UI の要約。既存の仕様節はリンクになっているため、数値や出典を再コピーしない |
| [前提の OS 比較](scope-and-hardware.md) / [OS 候補](os-candidates.md) | 前者には起動時間の異なる終点と除外理由、後者には公開資料の候補比較がある。第三者の数値は MSD の測定値ではない。現行の Buildroot 維持判断は [RESEARCH](../../RESEARCH.md)、Yocto の実測は[検討記録](yocto-migration/README.md)を正本とし、候補表を製品実装の表と読まない |
| [起動の入口](boot-and-kernel.md) / [起動時間](boot-time-measurements.md) / [カーネル方針](kernel-policy.md) / [縮小](kernel-size.md) | M5 の 2,112 ms は bare-metal splash、終点定義は測り方、カーネル方針は生成・検査の要約、縮小は構成候補。2,112 ms を Linux 全体と読み替えず、PREEMPT の版別条件と実測なしの否定も残す。入口の独立した 3 節だけを下表へ移す |
| [測定・限界](measurement-and-planning.md) / [未確認](open-questions.md) / [検証計画](simulation-plan.md) | 前者は UART などの観測と当時の判断根拠、未確認表は項目の追加・解消、検証計画は S1–S17 の状況と根拠の正本。既存の S1–S17 節はリンクであり、表を複製しない |
| [read-only と FS](readonly-data-and-fs.md) / [FS 候補](fs-candidates.md) | 前者は mount・書き込み経路・S17 の条件、候補表は圧縮・電断・費用の定性的比較。候補表の K12 などの出典は親文書にあり、切り離せない。未測定の性能を測定済みへ変えない |
| [電源・更新](power-and-updates.md) / [更新操作](../UPDATE.md) | 前者は FS、tryboot、更新フレームワークの候補と制約、後者は現在の `msd-update` の操作。現行操作は UPDATE を更新し、U-Boot 前提の先例や実機未確認の制約は調査側へ残す |
| [userspace](userspace-and-security.md) / [セキュリティ](security-hardening.md) / [ハードニング案](security-2026-11-hardening-list.md) | init/libc/allocator の候補、物理交換を含む脅威モデル、個別対策の採否は目的が異なる。systemd の設定例は BusyBox の製品設定ではない。採用根拠を増やさず統合しない |
| [代替比較](alternatives/README.md) / [userspace](userspace-and-security.md) / [再実装](reimplemented-libraries.md) | 代替比較は現行の固定設定と取得した一次資料を対応付ける採否の本文。[67構成要素](alternatives/coverage.csv)と、周辺・開発・CIまで役割を対応づける。既存の第三者の測定・当時の仮説は条件を保つ。LLVM libc、libdeflateのAPI互換性等の評価は根拠とともに訂正し、全候補のbuild・runtime・license監査の完了とはしない |

候補比較の古い版数や未確認事項は、その調査時点の記述です。最新の採否は RESEARCH、現行設定は BUILD とコード、個々の測定条件は実験を確認します。文書整理だけで、未確認項目を解消済みにしません。

## 起動・カーネル文書の移動対応

元の約 40 KB の文書は、探す目的が異なる節を分けました。節番号・条件・表・数値・出典はそのまま移し、元の全見出しには短い案内を残します。

| 元の節 | 本文の移動先 | 読む目的 |
|---|---|---|
| `boot-and-kernel.md` §5 | [boot-sequence.md](boot-sequence.md) | ROM から userspace までの起動経路と高速化候補 |
| 同 §15 | [boot-time-methods.md](boot-time-methods.md) | T_shell / T_init、観測方法、終点の定義 |
| 同 §20 | [kernel-boot-comparison.md](kernel-boot-comparison.md) | 6.18 以降の公開変更、PREEMPT、7.x 比較の条件 |
| 同 §14 / §22 | [boot-and-kernel.md](boot-and-kernel.md) | §14 は既存の縮小文書への案内。§22 の関連する設計事項は保持 |

## 長い文書を保持した理由

20,000 バイト超は分割を検討する目安で、検査を通すために記録を切りません。以下は今回確認した各文書の判断です。40,000 バイト超はなく、サイズの例外は追加していません。追加の改訂時には主題とサイズを再検討します。

| 文書 | 判断と理由 |
|---|---|
| [boot-sequence.md](boot-sequence.md) | 分割後も約 21 KB。起動順と候補・制約・同じ出典の表を一体で保持 |
| [corrections.md](corrections.md) | 原記述・訂正理由・出典を並べる記録。誤記だけを独立させない |
| [cpu-irq-and-sysctl.md](cpu-irq-and-sysctl.md) | CPU/thermal/IRQ の相互作用と QEMU の既定値・未測定の条件を保持 |
| [fastboot-and-cpu-tuning.md](fastboot-and-cpu-tuning.md) | 外部記事、CM0 の条件、compiler/crypto 候補の適用可否と出典が対になる |
| [hardware-spec.md](hardware-spec.md) | 対応表の「ビルド済みは実機動作ではない」という条件と、回路・機能依存を保持 |
| [ideas-overview.md](ideas-overview.md) | 案・採否・費用・根拠を同じ表で比較する入口。行途中で分断しない |
| [kernel-size.md](kernel-size.md) | 構成候補、依存、できない縮小、検査の基準を一体で読む |
| [measurement-and-planning.md](measurement-and-planning.md) | 観測手段と限界を残す調査記録。未確認と S1–S17 の更新先は上表で区別 |
| [power-and-updates.md](power-and-updates.md) | FS の電断特性と A/B の障害・復帰条件をつなげて読む。操作は UPDATE に分離済み |
| [readonly-data-and-fs.md](readonly-data-and-fs.md) | mount、書き込み先、read-only 案、S17 の出典 ID を保持。FS 候補は分離済み |
| [scope-and-hardware.md](scope-and-hardware.md) | 設計条件・除外理由・異なる条件の値を保存。仕様と公式構成の要約は別文書を使う |
| [security-2026-11-hardening-list.md](security-2026-11-hardening-list.md) | 各対策の費用と非採用条件、検証方法を一体で比較する調査 |
| [simulation-plan.md](simulation-plan.md) | S1–S17 の正本。試験 ID、状態、根拠の対応を分断しない |
| [soc-memory-compression.md](soc-memory-compression.md) | kernel と rootfs の圧縮条件・RAM・費用と実機測定の不足を保持 |
| [sources-url-reachability.md](sources-url-reachability.md) | 取得した URL と結果・信頼度の記録。到達だけでは本文確認ではない |
| [sources-url-reachability-more.md](sources-url-reachability-more.md) | もう一組の URL 取得記録。前の表と単純に重複とみなさない |
| [sources.md](sources.md) | 分割済み出典への入口と追加調査の取得記録。原文・URL の対応を保持 |
| [storage-and-flash.md](storage-and-flash.md) | パーティション・FS 内部の整列、測定条件と未確認の効果を一体で読む |
| [tunables-module-params.md](tunables-module-params.md) | `/sys/module` の既定値・候補・適用条件の表。sysctl の表とは別に保持 |
| [tunables-sysctl.md](tunables-sysctl.md) | `/proc/sys` の既定値・候補・条件の比較表を保持 |
| [userspace-and-security.md](userspace-and-security.md) | init/libc/allocator の機能依存と非採用条件をそろえて比較 |
| [S2 カメラ](../experiments/2026-10-19-s02-camera.md) | 条件、署名検査、失敗と実機未確認の結論が 1 実験を構成する |
| [実験一覧](../experiments/README.md) | 状態・条件・結論を実験ごとに 1 行で引ける一覧。個別の本文と CSV は既に分離してあり、表の行を機械的に別ページへ分けない |
| [S11 watchdog](../experiments/2026-10-20-s11-qemu-watchdog.md) | 事前 amendment、停止処理、失敗試行を含む一連の証拠を保持 |
| [CI8 PPD path](../experiments/2026-10-21-ci8-ppd-pathmap.md) | 比較条件、失敗、副次発見、復元を含む記録の完全性を保持 |
| [S21 sysctl/ramoops](../experiments/2026-10-21-s21-qemu-sysctl-ramoops.md) | 事前 amendment、計測器検証、失敗と未確認を分離しない |

## 照合の限界

本文の配置・リンク・文字・サイズの検査は、過去の実験を再実行した証拠ではありません。Yocto の生ログを読めた範囲は [還元の評価](yocto-migration/buildroot-lessons.md#証拠を読み直した範囲)に記載します。測定値の原本である CSV は整理のために変更しません。
