# 実験記録

実験・測定・比較の記録を 1 件 1 ファイルで置きます。書き方は `.agents/skills/experiment-record/SKILL.md` に従います。ファイル名は `YYYY-MM-DD-sNN-<short>.md` とし、生の値は同じ名前の `.csv` にします。S1〜S17 のどれにも属さない実験の記録名は `YYYY-MM-DD-<short>.md`（sNN なし）です。これらもこの一覧に載せます。覆った結論も消さず、状態を「置換」にして新しい記録へリンクします。

| ID | S 番号 | 日付 | 状態 | 結論 |
|---|---|---|---|---|
| [2026-10-19-s01-kernel-sweep-trial](2026-10-19-s01-kernel-sweep-trial.md) | S1 | 2026-10-19 | 完了 | ツールのみ。本番構成の採否は未実施。NUMA=n は QEMU_FAILED のため未判定。 |
| [2026-10-19-s02-camera](2026-10-19-s02-camera.md) | S2 | 2026-10-19 | 完了 | tier A 採用（Image +0 B、QEMU 相対 +0.0510%、署名 1,051/1,051）。rootfs +1,499,136 B、実機 capture は未確認。 |
| [2026-10-19-s03-data-ext4-writes](2026-10-19-s03-data-ext4-writes.md) | S3 | 2026-10-19 | 完了 | 4 KiB / `data=ordered` を採用。`inline_data` と `lazytime` は不採用。 |
| [2026-10-19-s06-kernel-hardening](2026-10-19-s06-kernel-hardening.md) | S6 | 2026-10-19 | 完了 | tier A 採用（Image +131,072 B、QEMU 相対 +2.63%、checker FAIL 125→111） |
| [2026-10-19-s06-modules-dep-xz](2026-10-19-s06-modules-dep-xz.md) | S6 | 2026-10-19 | 完了 | host kmod の XZ 対応と kernel decompressor を有効化し、A/B QEMU で module load を確認。 |
| [2026-10-19-tunables-dump](2026-10-19-tunables-dump.md) | なし | 2026-10-19 | 完了 | QEMU で sysctl 606 項目、ブロックデバイス 1,385 項目などの既定値を取得。rootfs に sysctl の設定はなく、`kernel.sysrq` は 502、I/O は `mq-deadline`。実機の値は未取得。 |
| [2026-10-19-social-webp](2026-10-19-social-webp.md) | なし | 2026-10-19 | 完了 | `cwebp -z 9 -metadata none` を可逆 Social preview 用に採用（19,262 B）。 |
| [2026-10-19-site-render](2026-10-19-site-render.md) | なし | 2026-10-19 | 完了 | minify、svgo、CSS のインライン化、`content-visibility` はどれも不採用（基準の 10% 短縮か画素の一致を満たさない）。 |
| [2026-10-20-ci-image-vs-runner](2026-10-20-ci-image-vs-runner.md) | なし | 2026-10-20 | 完了 | 既存の CI の run 9 件の振り返り。ccache が効けば、イメージ内の Buildroot の step（1,073〜1,184 秒）は runner（1,267〜1,313 秒）より遅くない。遅い run は ccache が効いていなかった。`ensure` は毎回ローカルでビルドしていた（312〜489 秒）。 |
| [2026-10-20-qemu-boottime](2026-10-20-qemu-boottime.md) | なし | 2026-10-20 | 完了 | QEMU の値で、実機では未確認。K2（`CONFIG_FTRACE` 無効）は icount で `t_ready` −37.88 %、TCG で −5.68 % となり、基準を満たした（製品の設定は未変更）。U1（mdev の走査を `/sys/devices` に限る）は約 −3 % で基準未達。K1（`CONFIG_KPROBE_EVENTS` 無効）は不採用。 |
| [2026-10-20-qemu-powerfail-gpio6](2026-10-20-qemu-powerfail-gpio6.md) | なし | 2026-10-20 | 完了 | 1.5 秒・5 秒の各 5 試行と post-rebase integrity は基準を満たした。SIGKILL による試験であり、実機では未確認。 |
| [2026-10-21-qemu-data-noexec](2026-10-21-qemu-data-noexec.md) | なし | 2026-10-21 | 完了 | QEMU のみ。`/data` に `noexec` を足しても起動と `/data` の準備は 5/5 で変わらず、直接実行だけが拒否された。`sh` 経由と `/etc` overlay 経由の実行は防げない。製品の設定は未変更。 |
| [2026-10-21-qemu-lynis](2026-10-21-qemu-lynis.md) | なし | 2026-10-21 | 完了 | QEMU のみ。製品イメージを Lynis 3.1.7 で 3 回監査し、3 回とも同じ結果（hardening index 60、warning 1、suggestion 24）。指摘を当てはまる・当てはまらない・実機に分けた |
| [2026-10-21-ci8-ppd-control](2026-10-21-ci8-ppd-control.md) | なし | 2026-10-21 | 完了（予備） | 同じ commit のローカル build を PPD あり・なしで 1 回ずつ比べた。PPD の top-level make は約 23.5 % 短かった。target の差は署名・時刻・生成鍵・埋め込み path・libv4l の locale のほか、原因未特定の gconv 2 ファイル。採否は未決定。 |
| [2026-10-21-ci8-ppd-ci](2026-10-21-ci8-ppd-ci.md) | なし | 2026-10-21 | 実施中 | CI の標準 runner で C0 と C1（PPD）を warm-up 1 回と本番 5 回ずつ比べる。計画と採否の基準は事前登録済み。 |
