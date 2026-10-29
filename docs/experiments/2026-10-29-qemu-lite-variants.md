# QEMU での Lite 版相当の動作（BMI270 不在の probe 失敗）

- 状態: 完了（QEMU のみ。実機の Lite 版は未確認）
- 日付: 2026-10-29
- 担当: Devin
- 関連: [simulation-plan.md](../research/simulation-plan.md)「QEMU で検証できる項目」、 [S2 の記録](2026-10-19-s02-camera.md)

## 目的

`config.txt` は `bmi270_bmm150_overlay` を無条件で読む。Lite 版（C155）には BMI270+BMM150 が無いため、センサーが無いときの挙動を確かめる。QEMU には I2C センサーの模擬が無いので、製品の DTB に overlay を合成すると「センサーが宣言されているが応答しない」＝Lite 版と同じ状況を再現できる。ついでに `msd-hwinfo` の model 判定の出力も記録する。

## 採否の基準（結果を見る前に書く）

1. 合成した DTB で起動が `MSD/Linux ready` とログイン画面まで進む（probe 失敗で boot が止まらない）こと。
2. kernel の probe 失敗メッセージを実際に採取し、エラーの種類を記録する。
3. `msd-hwinfo` の model / imu 出力を記録する。QEMU では v5 拡張チップ（M5IOE1、I2C 0x4f）も模擬されないため、実機 Lite の `model=lite` ではなく `unknown` 系を予想する。

## 条件

| 項目 | 値 |
|---|---|
| image | 依存更新後の build（`sdcard.img` SHA-256 `99f2b0c92335` 先頭 12 桁、`Image` `0ebc11d94b0d`） |
| DTB | `bcm2710-rpi-cm0.dtb` に `bmi270_bmm150_overlay.dtbo` を `fdtoverlay` で合成（`output/qemu-dtb/cm0-imu.dtb`）。`imu@68`（bmi270）と `magnetometer@10`（bmm150）が追加される |
| QEMU | 開発用イメージの 11.1.2、machine `raspi3ap`、512M |

## 手順

```sh
fdtoverlay -i output/images/bcm2710-rpi-cm0.dtb \
    -o output/qemu-dtb/cm0-imu.dtb \
    output/images/overlays/bmi270_bmm150_overlay.dtbo
QEMU_LOG_DIR=output/qemu-logs/lite DTB_IMAGE=output/qemu-dtb/cm0-imu.dtb \
    board/cardputerzero/qemu/test-boot.sh
```

## 生の値と結果

serial log（`QEMU_LOG_DIR=output/qemu-logs/lite` で生成）から採取した実際のメッセージ:

```
bmi270_core: loading out-of-tree module taints kernel.
bmi270_i2c 1-0068: Unexpected chip id 0xff
bmi270_i2c 1-0068: error -EREMOTEIO: Failed to write power configuration
bmi270_i2c 1-0068: probe with driver bmi270_i2c failed with error -121
```

- 起動は `MSD/Linux ready` とログイン画面まで進んだ（基準 1 を満たす）。probe の失敗は boot を止めない。
- `msd-hwinfo` の出力は `model=unknown imu=unknown`。QEMU では M5IOE1（0x4f）も無いので `imu=absent`（model=lite）にはならない。実機の Lite での判定は未確認。

## 結論

- Lite 版で想定される probe 失敗は `Unexpected chip id` + `-EREMOTEIO` + `-121` の 3 行で、起動は続行する。imx219 と同様、無害であることを QEMU で確認した。
- `config.txt` に「Lite では probe failure は無害」のコメントを追加した（imx219 と同じ扱い）。
- `msd-hwinfo` の model 判定（standard/lite）は実機でしか確かめられない。QEMU では `unknown` を返すことを確認した。

## 失敗した試行・未解決

- QEMU の I2C は応答そのものを模擬しない（転送は失敗して `0xff` が返る）。実機 Lite の probe 失敗は応答しないセンサーによる NACK で、メッセージは別物になる可能性がある。実機での採取は残課題。
