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
