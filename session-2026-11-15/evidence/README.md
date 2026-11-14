# 2026-11-15 セッションの証拠保全

このdirectoryは同じリポジトリの`data/fs-compare-experiments` branchに置きます。mainへmergeするための変更ではありません。実験の記録本文は`devin/1794692686-measure-2026-11-15`の`docs/experiments/2026-11-15-data-first-boot-writes.md`と`2026-11-15-zram-builtin-vs-module.md`です。

## 収録物

| file | 内容 |
|---|---|
| `e1-data-first-boot.tar.zst` | /data初回起動の書き込み帰属（E1）。output-dwcauseのtext類: 15 runの`metadata.json`・`serial.log`・`raw.csv`、variant生成・driver・forensic・aggregate script、driver.log、forensicのp7 .raw・dumpe2fs出力、失敗試行のrun dir。`sdcard.img`（各1 GiB）は除外 |
| `e2-zram-boottime.tar.zst` | zram `=y`対`=m`の起動時間比較（E2）。output-e2の2 CSV・driver log・各6 bootのserial log（ログのSHA-256はCSVの`log_sha256`列）。`image-build-*`（rootfs/sdcard.img/展開済みtarget）は除外 |
| `e2-zram-m-inputs.tar.zst` | =m側Buildroot出力の`linux-zram-m.fragment`と`.config` |
| `e2-zram-swap-check.tar.zst` | =m imageをQEMU起動してserialログインで採取した`/proc/swaps`・`/run/msd-zram.log`・`/dev/zram0`の確認ログ（swap無効の証拠） |
| `../SHA256SUMS` | 上記archiveのSHA-256 |

## 範囲

基準は`733d27e66c8499aa306325cb4ce928c6ed2f1034`。QEMU 11.1.2・kernel 6.18.59-v8での計測で、実SD・実機ではありません。

E3/E4（fs-compare matrix `e34-2026-11-15`、174行）は採取時に実行中で、完了後に`fs-compare/`へ別archiveとして追加します。

SD image・O= tree・ccache等のbinaryは含みません。各runの`metadata.json`に入力fileのSHA-256があるため、同じ入力は再生成できます。
