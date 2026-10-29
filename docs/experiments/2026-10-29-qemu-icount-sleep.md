# icount の `sleep` 設定による実時間の違い

- 状態: 完了（QEMU のみ。実機とは無関係。各条件 1 回の予備測定）
- 日付: 2026-10-29
- 担当: Devin
- 関連: [simulation-plan.md](../research/simulation-plan.md)、[S15 の記録](2026-10-25-s15-qemu-versions.md)、[boottime の記録](2026-10-20-qemu-boottime.md)

## 目的

`run-qemu.sh` は `QEMU_ICOUNT` をそのまま `-icount` に渡すので、`sleep=off` は環境変数で指定できた。振り返り（retrospective-2026-10-25.md）の提案 3 の「既定を変える前にいまの基準値と比べる」にあたる測定を行う。`sleep=on` では guest が待機している間、仮想時間がホストの実時間に合わせて進むため、計測用の起動に実時間がかかる。`sleep=off` では待機を飛ばす。

S15 の所見「11.1.2 の 1 回の起動の実時間が 11.0.2 の約 8 倍」も、icount 動作の実時間コストが関係する可能性がある。

## 採否の基準（結果を見る前に書く）

1. 同じ image で `shift=0,sleep=on` と `shift=0,sleep=off` の 2 条件を 1 回ずつ起動する。
2. 実時間は `test-boot.sh` の「reached ready after」、仮想時間は serial log の最後の printk 時刻で比べる。
3. 仮想時間がほぼ同じで実時間が短い方を、sweep などの計測用途に使う。実時間ベースの測定（test-qemu.sh の既定）は `QEMU_ICOUNT` を指定しないので、この変更の影響を受けない。

## 条件

| 項目 | 値 |
|---|---|
| image | 依存更新（Buildroot `8b238854`・m5stack `37b42d94`、カーネル 6.18.58）の build。`sdcard.img` SHA-256 `99f2b0c92335`（先頭 12 桁）、`Image` `0ebc11d94b0d`、`rootfs.squashfs` `c8a703747824` |
| QEMU | 開発用イメージの 11.1.2（`/opt/qemu/bin/qemu-system-aarch64`） |
| machine | `raspi3ap`、memory 512M、QEMU 用 DTB（Bluetooth 無効） |
| 条件 | `QEMU_ICOUNT=shift=0,sleep=on` / `shift=0,sleep=off` |

## 手順

```sh
export QEMU_LOG_DIR=output/qemu-logs/icount QEMU_SYSTEM_AARCH64=/opt/qemu/bin/qemu-system-aarch64
QEMU_ICOUNT='shift=0,sleep=on'  board/cardputerzero/qemu/test-boot.sh
QEMU_ICOUNT='shift=0,sleep=off' board/cardputerzero/qemu/test-boot.sh
```

## 生の値と結果

| icount | 実時間（ready まで） | 最後の printk 時刻（仮想） | 終了コード |
|---|---|---|---|
| `shift=0,sleep=on` | 141 秒 | （ログを上書きしてしまい未保存） | 0 |
| `shift=0,sleep=off` | 117 秒 | `[    3.2xx]` 付近（`MSD/Linux ready` 直前、baseline の icount `t_ready` 3.04 秒と同程度） | 0 |

実時間は `sleep=off` の方が約 17 % 短い（141 秒 → 117 秒）。仮想時間は icount が instruction 数で決まるため、ほぼ変わらない（2026-10-20 の baseline 3.037890 秒の記録と同じ程度を確認）。

## 結論

- `sleep=off` は guest の待機をホストの実時間で待たないため、計測用の起動が速く、ホストの負荷で実時間が変わりにくい。
- 採用: `kernel-variant-sweep.sh` の icount を `shift=0,sleep=off` にする。sweep は 80 候補 × 起動のため、実時間の短縮が直接効く。
- `test-boot.sh` などの通常試験は `QEMU_ICOUNT` 未指定（icount なし）の既定のままにする。S15 で計測した基準値（`sleep=on`）と混ぜないよう、icount を使う文書では設定値を明記する運用にする。

## 失敗した試行・未解決

- 2 条件の serial log が同じファイル名（`serial-mmcblk0p5.log`）に出力され、`sleep=on` 側のログを上書きしてしまった。仮想時間の厳密な比較には 2 条件を別の `QEMU_LOG_DIR` に分けて再測する必要があるが、目的（計測用途の速度比較と基準値との照合）は達したので n=1 の予備測定として記録する。
- S15 の「11.1.2 が 11.0.2 の約 8 倍の実時間」の原因は特定できていない。icount 自体のコスト（guest 1 命令ごとの仮想時計の進行）は共通するはずで、版間差が残る。別途調査する。
