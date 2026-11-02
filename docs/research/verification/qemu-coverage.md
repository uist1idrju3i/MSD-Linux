# QEMU・生成物で確認した範囲と実機の境界

[調査の索引](../../../RESEARCH.md) / [検証の入口](README.md)

S1–S17は[試験台帳](experiment-catalog.md)だけで更新します。以下はそれ以外の項目の記録です。
旧表の「検証済み」「未実施」という二分はやめ、実際の記録と未確認範囲を同じ行で読みます。この整理ではQEMUを再実行していません。
実firmware、tryboot、LCD・M5 I2C機器、電源回路、実SDのFTL・速度はQEMUの対象外です。

## 項目別の記録

| 項目 | 確認された内容・残る条件 | 記録・当時の費用見積り |
|---|---|---|
| 起動時間の内訳と K1・K2・U1 | initcall と init script ごとの時間。K2（ftrace の無効化）だけが基準を満たした | [2026-10-20-qemu-boottime](../../experiments/2026-10-20-qemu-boottime.md) |
| 調整項目の既定値 | sysctl、ブロックデバイス、モジュールパラメーター | [2026-10-19-tunables-dump](../../experiments/2026-10-19-tunables-dump.md) |
| `kernel8.img` の gzip 再圧縮 | 実装済み。`post-image.sh` が `pigz -11 -n` で圧縮し、展開結果を `cmp` で比べる。読み込み時間は実機で測る | #8（[BUILD.md](../../BUILD.md)） |
| `align = 4M` | 実装済み。CI の `check-image-layout.sh` が全開始位置の 8192 sector 境界を検査する。性能は実機で測る | #19（[ストレージ](../storage/README.md)） |
| Lynis による監査（QEMU のみ） | 製品イメージの監査を 3 回行い、結果が同じこと。指摘の分類。対応は sysctl 候補と S1・S14 で行う | [2026-10-21-qemu-lynis](../../experiments/2026-10-21-qemu-lynis.md) |
| 温度 | bcm2835_thermal に `temp` プロパティを追加し任意温度を注入して読み出し経路を確認 | [2026-10-29-qemu-thermal-temp](../../experiments/2026-10-29-qemu-thermal-temp.md) |
| `quiet`・`lpj=` | icount での起動時間の差。`quiet` は実時間 −20%、`lpj=` は効果なし | [2026-10-29-quiet-lpj](../../experiments/2026-10-29-quiet-lpj.md) |
| PREEMPT モデル | `PREEMPT_NONE`・`PREEMPT`・`PREEMPT_RT` の Image と起動時間の比較 | [2026-10-30-preempt-models](../../experiments/2026-10-30-preempt-models.md) |
| 任意機能ドライバーのモジュール化 | `=m` 化で Image −3.6%。modalias 自動ロードを確認。現状は見送り | [2026-10-30-modularize-drivers](../../experiments/2026-10-30-modularize-drivers.md) |
| EROFS rootfs | lz4hc では SquashFS+zstd より約 29% 増大・起動時間差なし → SquashFS 維持 | [2026-10-29-erofs-rootfs](../../experiments/2026-10-29-erofs-rootfs.md) |
| `/data` の `noexec`（QEMU のみ） | 起動・`/data` の準備・serial 検査が変わらないこと。直接実行は拒否されるが、`sh` 経由と `/etc` overlay 経由は防げないこと。アプリの互換性は実機で確認する | [2026-10-21-qemu-data-noexec](../../experiments/2026-10-21-qemu-data-noexec.md) |
| zram（QEMU のみ） | zstd・lz4 とも `modprobe` から `swapon -p 100` まで動き、zswap は無効のまま。圧縮できないデータでは OOM になる。CPU の負荷は実機で確認する | [2026-10-21-qemu-zram](../../experiments/2026-10-21-qemu-zram.md) |
| S21 sysctl・powerfail・panic・ramoops（QEMU のみ） | 修正計測器で Y1 は実 remount 5/5、Y2 は 0/5。QEMUでは `kernel.sysrq=0` がremountを止め、32は保つ。実機 ramoops retention 等と製品採否は未確認 | [2026-10-21-s21-qemu-sysctl-ramoops](../../experiments/2026-10-21-s21-qemu-sysctl-ramoops.md) |
| init script の stop 処理 | 再起動のときに起動時の処理をやり直さないこと（S11 のログで見つけた不具合） | PR #77 で修正済み |
| 起動時のファイルアクセスの観測と `mksquashfs -sort` | 起動時に読むファイルとその順番 | 観測は QEMU で完了（[記録](../../experiments/2026-10-25-qemu-boot-read-order.md)）。rootfs の 16.5 % を読み、順番は 5 回とも同じ。`-sort` の効果は実機で測る |
| dm-verity | QEMU で改ざん拒否を確認した。実機性能、A/B 復旧、信頼できる root digest、製品統合は未実施（[記録](../../experiments/2026-10-21-qemu-dm-verity.md)）。 | 中 |
| BusyBox の applet を減らす、静的リンク | QEMU で静的リンクと 63 applet を比較した。製品用 applet の範囲は未決である（[記録](../../experiments/2026-10-21-qemu-busybox.md)）。 | 中 |

## 実機と設計へ引き継ぐこと

実機での指標・動作は[実機測定](hardware-measurements.md)、SSH/VPNなどの現行方針と将来候補は[未確認事項](open-questions.md)と[代替比較](../alternatives/README.md)で扱います。
hostの生成物検査、QEMUの仮想時刻、実機の秒数を同じ種類の検証とは扱いません。
