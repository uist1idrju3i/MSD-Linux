# GPIO6 電源断モデルの QEMU 整合性試験

- 状態: 計画
- 日付: 2026-10-20
- 担当: Devin
- 関連: QEMU BCM2835 GPIO6 power-fail model

## 目的と仮説

QEMU の GPIO6 入力を low にしたとき、`powerfail_suo` の割り込み、500 ms debounce、userspace 通知、SysRq-U による read-only 再マウントが順に動作するかを確かめます。`/data` の試験用 workload を実行中に QEMU を SIGKILL し、再起動後の marker と ext4 の状態も記録します。1.5 秒以上の遅延では、イベントと再マウントが記録され、marker が残り、ext4 の回復メッセージが出ないと予想します。

## 採否の基準（結果を見る前に書く）

- GPIO6 を low にしてから SIGKILL するまでの時間を 0.1、0.4、0.7、1.5、5 秒とし、各条件を 5 回行います。GPIO イベントを発生させず、5 秒後に SIGKILL する control も 5 回行います。
- A/A 試行を同じ 1.5 秒条件で 2 回先に行います。QMP の応答から SIGKILL までの実測時間差が 0.05 秒以下であることを計測器の確認基準とします。基準を超えた場合は本試験を開始せず、失敗として記録します。
- 1.5 秒と 5 秒の有効な試行は、すべてで通知と SysRq-U の記録、再起動後の marker、`fsck.ext4 -n` の終了値 0 を確認し、ext4 の回復メッセージがないことを採用基準とします。
- 0.1 秒と 0.4 秒は debounce より短いため、結果を記録しますが合否は判定しません。0.7 秒も観測値として記録し、採否の判定には使いません。
- control では GPIO イベントと SysRq-U が記録されないことを確認します。全条件で試行状態、イベント、再マウントと経過時間、marker、ext4 の検査・回復メッセージ、起動・再起動・全体の所要時間を記録します。
- 起動、QMP 操作、または再起動検証を完了できない試行は `failed-run` とし、集計から除き、理由とログを残します。観測したファイルシステム異常は有効な結果として記録し、除外しません。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | 実行前に記録 |
| ホスト | 実行前に記録 |
| QEMU | 開発用イメージ内の `qemu-system-aarch64 --version` を実行して記録 |
| Buildroot / GCC / カーネル | 実行した出力の版を記録。Linux source commit は `234188315037848e5b07d65b85d38edc64095caa` |
| 使ったツールの版 | `output/host/bin/dtc`、`fdtoverlay`、`mksquashfs`、`unsquashfs`、`output/host/sbin/sfdisk` の版を記録 |
| 出力先と状態 | 既存 `msd-main` 作業木の `output/` を Buildroot 出力として使い、`*-reconfigure` は行わない。測定専用 rootfs と SD image はリポジトリーの `output/qemu-powerfail/` に作る |
| 変える条件 | GPIO6 low から SIGKILL までの時間: 0.1、0.4、0.7、1.5、5 秒。別に GPIO event なしの 5 秒 control |
| 変えない条件 | QEMU machine `raspi3ap`、A slot (`/dev/mmcblk0p5`)、kernel、base DTB、SD image layout、100-file S3 workload、500 ms debounce |
| 繰り返し | A/A を 2 回、各遅延を 5 回、control を 5 回。中央値と最小・最大を記録 |

## 手順

```sh
docker/msd-dev build
OUTPUT_DIR="$BUILD_OUTPUT_DIR" QEMU_LOG_DIR="$PWD/output/qemu-logs" \
  docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --experiment
```

試験用 rootfs は既存 SquashFS を展開し、`board/cardputerzero/tools/bench/s3/` の writer と verifier のみを追加して再作成します。通常の Buildroot image や製品用 rootfs には追加しません。overlay は実行時に `output/host/bin/dtc -@` と `fdtoverlay` で base DTB に重ねます。

## 計測器の検証

GPIO6 を low にして QMP が応答した時刻と、ホストが SIGKILL を送った時刻を `time.monotonic_ns()` で計測します。1.5 秒条件の A/A 2 回で実測遅延の差が 0.05 秒以下であることを確かめてから、条件別の試行を始めます。測定値は同名 CSV の `gpio_low_to_kill_seconds` 行に記録します。

## 結果

実行前のため未記入です。試行ごとの生値は同名 CSV に記録します。

| 条件 | 回数 | 通知・再マウント | marker | ext4 検査・回復 | 所要時間 |
|---|---:|---|---|---|---|
| A/A 1.5 秒 | 2 | 未実施 | 未実施 | 未実施 | 未実施 |
| 0.1 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |
| 0.4 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |
| 0.7 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |
| 1.5 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |
| 5 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |
| GPIO event なし、5 秒 | 5 | 未実施 | 未実施 | 未実施 | 未実施 |

## 捨てた試行と経緯

現時点で試行はありません。`failed-run` が生じた場合は、理由、CSV の run ID、ログの保存先をここに列挙します。

## 結論

未実施です。QEMU の SIGKILL は実際の電源断ではありません。ホストの page cache に、ゲストから送信済みの書き込みが残ることがあります。この試験から SD card の FTL や実機の電源保持時間は判断できません。

## 未確認の点

実機の GPIO6、電源保持時間、SD card の内部 FTL と実電源断時の挙動は未確認です。実機では試していない。

## ログ

大きなログは commit せず、`output/qemu-logs/powerfail/<run-id>/` に残します。完了後に各 log の SHA-256 をここへ記録します。再生成コマンドは上記の手順を使います。
