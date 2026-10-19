# 実験記録

実験・測定・比較の記録を 1 件 1 ファイルで置きます。書き方は `.agents/skills/experiment-record/SKILL.md` に従います。ファイル名は `YYYY-MM-DD-sNN-<short>.md` とし、生の値は同じ名前の `.csv` にします。覆った結論も消さず、状態を「置換」にして新しい記録へリンクします。

| ID | S 番号 | 日付 | 状態 | 結論 |
|---|---|---|---|---|
| [2026-10-19-s01-kernel-sweep-trial](2026-10-19-s01-kernel-sweep-trial.md) | S1 | 2026-10-19 | 完了 | ツールのみ。本番構成の採否は未実施。NUMA=n は QEMU_FAILED のため未判定。 |
| [2026-10-19-s02-camera](2026-10-19-s02-camera.md) | S2 | 2026-10-19 | 完了 | Image 0 B、署名 1,051/1,051。QEMU 相対 +4.66% は +1.0% 基準未達。実機 capture は未確認。 |
| [2026-10-19-s03-data-ext4-writes](2026-10-19-s03-data-ext4-writes.md) | S3 | 2026-10-19 | 完了 | 4 KiB / `data=ordered` を採用。`inline_data` と `lazytime` は不採用。 |
| [2026-10-19-s06-kernel-hardening](2026-10-19-s06-kernel-hardening.md) | S6 | 2026-10-19 | 完了 | tier A 採用（Image +131,072 B、QEMU 相対 +2.63%、checker FAIL 125→111） |
| [2026-10-19-s06-modules-dep-xz](2026-10-19-s06-modules-dep-xz.md) | S6 | 2026-10-19 | 完了 | host kmod の XZ 対応と kernel decompressor を有効化し、A/B QEMU で module load を確認。 |
