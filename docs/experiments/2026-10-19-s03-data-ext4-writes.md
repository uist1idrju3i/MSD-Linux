# S3 `/data` ext4 書き込み量と電断試験

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin
- 関連: PR #27、[読み取り専用領域と FS 比較](../research/readonly-data-and-fs.md)、[訂正済み事項](../research/corrections.md)

## 目的と仮説

QEMU の同一 file-replacement workload で ext4 block size と mount options によるゲスト書き込み量を比べ、候補の電断後状態も確認する。4 KiB / `data=ordered` を基準とし、追加 option は測定差が基準を超えた場合だけ採用する。

## 採否の基準（結果を見る前に書く）

`inline_data` は guest write bytes を 20% 以上、`lazytime` は 10% 以上減らすことを採用条件とする。電断試験では fsck が clean で、対象ファイルが旧内容または新内容のいずれかを保つことを合格条件とする。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `cf049b51614230bfd5d327fb839185d3a121d4ae` |
| ホスト | Ubuntu 22.04 |
| QEMU | 6.2.0 |
| Buildroot / GCC / カーネル | 2026.08 / 14.3.0 / 6.18.57-v8 |
| 出力先と状態 | `OUTPUT_DIR=<Buildroot の O= ディレクトリ>`。再利用したローカル output |
| 変える条件 | ext4 1 KiB/4 KiB、`data=journal`/`data=ordered`、`inline_data`、`lazytime` |
| 変えない条件 | 同一 QEMU guest workload、100 個のファイルを一時ファイルから rename、同じ field 7 counter |
| 繰り返し | 各 V0–V5 は有効 5 回。中央値を採用。V1/V2 は電断を各 20 回 |

## 手順

同名 CSV は提供された raw CSV の全行を保持し、無効行も削除していない。追加の電断 CSV は V1/V2 の cut JSON 40 件から作成した。

ローカル再実行では bench hook を通常 overlay や CI に入れず、使い捨て rootfs にだけ追加する。

```sh
REPO=<リポジトリのルート>
OUTPUT_DIR=<Buildroot の O= ディレクトリ>
LOG_DIR=<ローカルログの保存先>
install -m 0755 "$REPO/board/cardputerzero/tools/bench/s3/S02zz-s3verify" \
  "$OUTPUT_DIR/target/etc/init.d/S02zz-s3verify"
install -m 0755 "$REPO/board/cardputerzero/tools/bench/s3/S06msd-s3bench" \
  "$OUTPUT_DIR/target/etc/init.d/S06msd-s3bench"
python3 "$REPO/board/cardputerzero/tools/bench/s3/s3-qemu.py" measure \
  --image "$OUTPUT_DIR/images/sdcard.img" \
  --kernel "$OUTPUT_DIR/images/Image" \
  --dtb "$OUTPUT_DIR/images/bcm2710-rpi-3-b.dtb" \
  --output "$LOG_DIR/V1/run1" --append msd.s3bench=1
python3 "$REPO/board/cardputerzero/tools/bench/s3/s3-qemu.py" cut \
  --image "$OUTPUT_DIR/images/sdcard.img" \
  --kernel "$OUTPUT_DIR/images/Image" \
  --dtb "$OUTPUT_DIR/images/bcm2710-rpi-3-b.dtb" \
  --output "$LOG_DIR/powercut/V1/run1" \
  --append msd.s3cut=1 --verify-append msd.s3verify=1
```

実行時に `MSD_DATA_DEVICE`、`MSD_S3_DATA_DIR`、`MSD_S3_STAT_PATH`、`MSD_S3_BENCH_DIR`、`MSD_S3_CUT_DIR` を指定すれば、guest 側の device、mount point、counter、data directory を変更できる。QEMU の binary と追加 command line は `QEMU_SYSTEM_AARCH64`、`QEMU_EXTRA_APPEND` で指定する。

## 計測器の検証

QMP `query-blockstats` は読み書き byte counter が全て 0 で、raspi SD model のこの用途では計測器として使えなかった。採用した値は guest の `/sys/class/block/mmcblk0p7/stat` field 7 の差に 512 を掛けた値である。10 秒アイドル後の delta が 0 の場合だけ workload を許可した。これは QEMU guest block layer の書き込み量であり、SD card FTL や NAND の物理書き込み量ではない。

最初の guest-stat 測定は ext4 lazy initialization の書き込みが混入した。`lazyinit-V1` 行の idle delta は 16 sectors で無効である。以降は `lazy_itable_init=0,lazy_journal_init=0` で作成し、sync、idle wait、idle-delta=0 gate を通した。

## 結果

中央値と全 run は CSV を参照する。電断試験は別 CSV に全 40 行を記録した。

| Variant | 条件 | 中央値（bytes） |
|---|---|---:|
| V0 | 1 KiB / `data=journal` | 2,580,480 |
| V1 | 4 KiB / `data=ordered` | 7,618,560 |
| V2 | V1 + `inline_data` | 7,618,560 |
| V3 | V1 + `lazytime` | 7,618,560 |
| V4 | 1 KiB / `data=ordered` | 2,269,184 |
| V5 | 4 KiB / `data=journal` | 8,855,552 |

V1 と V2 の電断試験は各 20 回中 20 回 PASS。各試行は 1–10 秒後に QEMU を SIGKILL し、再起動後に fsck clean と 100 ファイルの旧内容／新内容を確認した。

## 捨てた試行と経緯

- QMP blockstats は読み書きとも 0 のため採用せず、guest field 7 に切り替えた。
- V0 run3 は `SECTORS_AFTER` がなく無効。raw CSV に残し、`run3-valid` で置き換えた。
- `probe-remount` は mount の sanity check であり、独立した測定回として集計していない。
- V1 と V3 は raw CSV の全測定値が一致した。`lazytime` が既存 inode の時刻更新を遅らせる一方、この workload は新しい inode の作成と rename で file を置き換えるため差が出なかった可能性がある。この説明は未検証の仮説である。

## 結論

ユーザー判断により 4 KiB / `data=ordered`（V1）を採用する。V2 `inline_data` と V3 `lazytime` は採否基準を満たさず採用しない。4 KiB の各測定値は 1 KiB より大きかったが、これは QEMU guest block-layer metric の結果で、実カードの FTL 書き込み量や寿命を示さない。

## 未確認の点

対象 microSD の内部 page size、FTL write amplification、実機での書き込み量と電断耐性は未確認である。V1/V3 が一致した原因も仮説にとどまる。

## ログ

raw counter は同名 CSV、電断の delay/status は `2026-10-19-s03-data-ext4-powercut.csv` に保存した。詳細な QEMU serial log はリポジトリ外のローカルデータから再生成する。scripts は `board/cardputerzero/tools/bench/s3/` にあり、標準 rootfs と CI には含めない。
