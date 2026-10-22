# GPIO6 電源断モデルの QEMU 整合性試験

- 状態: 完了
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
| 基準の commit | 初回 smoke: `73bf3338eee25a1979c910f4165c2d171af27091`。A/A・反復試験・初回 integrity: `45bb5e8b21da3162975107e5e53178e0494b653c`。PR-A 修正後の再ビルド、smoke、追加 integrity: PR-B `110ff713acf77365a6deb7c9be08a2aded931acd`（PR-A `0b34be9c7e20a89ec003312eeada3f9931c1881e` を含む） |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| QEMU | 開発用イメージ内の `qemu-system-aarch64 --version`: QEMU emulator version 11.1.2 |
| Buildroot / GCC / カーネル | Buildroot 2026.08 (`d6061d653d7`)、AArch64 GCC 14.3.0、kernel `6.18.57-v8`。Linux source commit は `234188315037848e5b07d65b85d38edc64095caa` |
| 使ったツールの版 | Buildroot host tools: dtc/fdtoverlay 1.7.2、mksquashfs/unsquashfs 4.7.5、sfdisk 2.41.5。イメージ生成時の mke2fs 1.47.4 |
| 出力先と状態 | Buildroot 出力は `OUTPUT_DIR` で指定。基準 `origin/main` の出力とは分離した。初回は `m5stack-cardputerzero-dirclean`、`m5stack-cardputerzero-rebuild`、全体ビルドを実行。PR-A 修正後は PR-B の新しい HEAD を `/work` にして同じ `OUTPUT_DIR` で再ビルドと全体再生成を実行。いずれも `*-reconfigure` は行っていない。試験用 rootfs と SD image は `output/qemu-powerfail/` に生成 |
| 実行時の作業木 | 初回実験のソースと画像は commit `45bb5e8`。実験時に未コミットだった変更はこの記録と CSV のみで、QEMU、ドライバー、overlay、試験コードに追加の変更はない。再ビルド・再試験は commit `110ff713` のコードから実施 |
| 変える条件 | GPIO6 low から SIGKILL までの時間: 0.1、0.4、0.7、1.5、5 秒。別に GPIO event なしの 5 秒 control |
| 変えない条件 | QEMU machine `raspi3ap`、A slot (`/dev/mmcblk0p5`)、kernel、base DTB、SD image layout、100-file S3 workload、500 ms debounce |
| 繰り返し | A/A を 2 回、各遅延を 5 回、control を 5 回。中央値と最小・最大を記録 |

## 手順

```sh
docker/msd-dev build
export OUTPUT_DIR=/path/to/buildroot-output
export QEMU_LOG_DIR="$PWD/output/qemu-logs"
OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$QEMU_LOG_DIR" \
  docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --smoke
OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$QEMU_LOG_DIR" \
  docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --integrity
OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$QEMU_LOG_DIR" \
  docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --experiment
```

試験用 rootfs は既存 SquashFS を展開し、`board/cardputerzero/tools/bench/s3/` の writer と verifier のみを追加して再作成します。通常の Buildroot image や製品用 rootfs には追加しません。overlay は実行時に `output/host/bin/dtc -@` と `fdtoverlay` で base DTB に重ねます。

## 計測器の検証

GPIO6 を low にして QMP が応答した時刻と、ホストが SIGKILL を送った時刻を `time.monotonic_ns()` で計測します。1.5 秒条件の A/A 2 回で実測遅延の差が 0.05 秒以下であることを確かめてから、条件別の試行を始めます。測定値は同名 CSV の `gpio_low_to_kill_seconds` 行に記録します。A/A の実測は 1.567163 秒と 1.571227 秒で、差は 0.004064 秒でした。

## 結果

有効な試行の実測遅延は中央値と最小〜最大を示します。ext4 検査は再起動後の `fsck.ext4 -n` 終了値 0、回復は再起動ログの回復メッセージを示します。試行ごとの値は同名 CSV に記録します。

| 条件 | 回数 | GPIO low から SIGKILL までの秒数（中央値、最小〜最大） | userspace event | SysRq-U / remount | marker | fsck 0 | 回復メッセージ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.1 秒 | 5 | 0.167931（0.164525〜0.169379） | 0/5 | 0/5 | 5/5 | 5/5 | 5/5（観察のみ） |
| 0.4 秒 | 5 | 0.469368（0.464688〜0.474549） | 0/5 | 0/5 | 5/5 | 5/5 | 5/5（観察のみ） |
| 0.7 秒 | 5 | 0.768110（0.764297〜0.771734） | 0/5 | 5/5 | 5/5 | 5/5 | 0/5 |
| 1.5 秒 | 5 | 1.567993（1.566480〜1.573337） | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 |
| 5 秒 | 5 | 5.068238（5.065245〜5.069020） | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 |
| GPIO event なし、5 秒 | 5 | 5.027217（5.026886〜5.028788） | 0/5 | 0/5 | 5/5 | 5/5 | 5/5 |

0.1 秒と 0.4 秒の回復メッセージは観察値であり、採否の判定には使いません。0.7 秒も採否判定の対象外のため合否を付けません。`userspace_log_to_sysrq_seconds` は非同期 userspace ログ時刻から SysRq-U の時刻を引くため、負値になることがあります。これは remount の因果的な所要時間ではありません。CSV にはカーネルの検出ログから ext4 の read-only remount ログまでの `kernel_detect_to_ext4_remount_seconds` も記録しました。

| 条件 | kernel detection から ext4 read-only remount まで（中央値、最小〜最大） |
|---|---:|
| 0.7 秒、5 回 | 0.189953 秒（0.179104〜0.192518） |
| 1.5 秒、5 回 | 0.175310 秒（0.080021〜0.208101） |
| 5 秒、5 回 | 0.184238 秒（0.100347〜0.190180） |
| post-rebase integrity、1 回 | 0.167386 秒 |

| リビジョン別の追加確認 | 結果 |
|---|---|
| PR-B `45bb5e8` の integrity 1.5 秒 | 1/1: 実測 1.565330 秒、event/remount/marker あり、fsck 0、回復なし |
| PR-B `110ff713` の再ビルド後 smoke | PASS。event と emergency remount を確認、約 32.6 秒 |
| PR-B `110ff713` の再ビルド後 integrity 1.5 秒 | 1/1: 実測 1.566716 秒、event/remount/marker あり、fsck 0、回復なし |

再ビルドでは `.applied_patches_list` が 1 行で、`powerfail_suo.ko` に `POWERFAIL=1` が含まれ、Buildroot の全体イメージ生成も成功しました。

## 捨てた試行と経緯

- `smoke-20261020T142103Z`: `failed-run`。QOM path を `/machine/soc/gpio` と誤指定し、QMP `DeviceNotFound` で GPIO6 を操作できなかった。ログ: `output/qemu-logs/powerfail/smoke-20261020T142103Z/`。
- `smoke-20261020T142253Z`: `failed-run`。GPIO6 の QMP 操作、driver probe、SysRq-U と緊急 remount は成功したが、`msd-powerfail: power-fail event received` が出なかった。Buildroot の `SITE_METHOD=local` が override source として rsync され、通常の patch step が省略されていたため。PR-A の `POST_RSYNC_HOOKS` 修正後に再試験する。ログ: `output/qemu-logs/powerfail/smoke-20261020T142253Z/`。
- `integrity-20261020T144637Z`: `failed-run`。rootless container 内の `unsquashfs` がファイル所有者の変更を拒否され終了値 2 となり、QEMU 起動前に停止した。試験用ハーネスを修正し、この既知の uid/gid 警告だけを許容する。ログ: `output/qemu-powerfail/integrity-20261020T144637Z/unsquashfs.log`。
- `integrity-20261020T144832Z`: `failed-run`。rootfs の再作成後、A/B partition のサイズ検査が失敗した。partition metadata を 2 行で出力していたのに、shell `read` は先頭行しか読まず、B 側のサイズが空になっていた。rootfs は 23,891,968 bytes、A/B 各 partition は 524,288 sectors (268,435,456 bytes) で、実際には収まる。修正後に再試験する。ログ: `output/qemu-powerfail/integrity-20261020T144832Z/mksquashfs.log` と `output/qemu-logs/powerfail/pr-b-integrity-retry.log`。
- `integrity-20261020T144939Z` (commit `40f26ba1e6ffd518b18f6aaebe24db6654162d96`): `failed-run`。QEMU は起動し driver probe まで進んだが、test-only `S06msd-s3bench` は `msd.s3bench=1` がないため開始せず、marker を出力しなかった。ハーネスの kernel command line に `msd.s3bench=1` を追加する。ログ: `output/qemu-logs/powerfail/integrity-20261020T144939Z/firstboot.log` と `output/qemu-logs/powerfail/pr-b-integrity-final.log`。
- PR-B `110ff713` の初回 post-rebase smoke: `failed-run`。QEMU の UNIX socket path が 108 bytes を超え、QEMU 起動前に終了した。`QEMU_LOG_DIR` を短いリポジトリ内パスに変更して再実行し、smoke は通過した。ログ: `output/qemu-logs/post-rebase-smoke/powerfail/smoke-20261020T162343Z/serial.log`。

## 結論

事前基準に定めた 1.5 秒と 5 秒の各 5 試行はすべて event、SysRq-U/remount、marker、fsck 終了値 0、回復メッセージなしを満たしました。追加の post-rebase integrity も通過しました。0.1 秒と 0.4 秒は合否判定をせず観察値のみを記録しました。0.7 秒ではカーネルの検出と remount は 5/5 でしたが、userspace の event ログは 0/5 でした。

0.7 秒の 5 件すべてで、シリアルログには `Power fail detected; notifying userspace`、SysRq-U、ext4 の read-only remount があり、`msd-powerfail: power-fail event received` はありません。CSV と 5 件のログも 0/5 を示します。途中の報告にあった 1/5 は保存済みログで裏付けられず、ここでは 0/5 に訂正しました。通知文を出すのはカーネルではなく、`board/cardputerzero/post-build.sh` が登録する mdev ルールから起動する `/usr/libexec/msd/powerfail-notify` です。このスクリプトは `/dev/kmsg` への書き込みと `sync` をバックグラウンドで実行します。短い猶予時間内に userspace handler またはシリアル出力が完了しなかった可能性はありますが、試験ログから原因を確定できないため仮説として扱います。

CSV の `remount_seen=yes` 19 試行を事後確認し、全 run の log に `sysrq: Emergency Remount R/O` と `Emergency Remount complete` があった。旧 metric は実 remount と一致していた。

QEMU の SIGKILL は実際の電源断ではありません。ホストの page cache に、ゲストから送信済みの書き込みが残ることがあります。この試験から SD card の FTL や実機の電源保持時間は判断できません。

## 未確認の点

実機の GPIO6、電源保持時間、SD card の内部 FTL と実電源断時の挙動は未確認です。実機では試していない。

## ログ

ログは commit せず、`output/qemu-logs/` に残します。主要ログの SHA-256 は次のとおりです。

| ログ | SHA-256 |
|---|---|
| `output/qemu-logs/powerfail/pr-b-experiment.log` | `5424d4aaa350981ef981c8bdc01fc247198cdacf94372397835e77f8f6c1cf76` |
| `output/qemu-logs/test-powerfail-smoke-post-rebase-short.log` | `3daba659ebf97cfef8331d7a218690029fac03cea15f278628630df55b10cb01` |
| `output/qemu-logs/post-rebase-smoke-short/powerfail/smoke-20261020T162406Z/serial.log` | `c6f7632c9f7a4f0e9a1fdd4e789555d963099223195c94212088f9ff43b06de9` |
| `output/qemu-logs/test-powerfail-integrity-post-rebase.log` | `da1e4a93087bda717ea5cac0793c31a2ce3c4a4f502a84868a46324d27737099` |
| `output/qemu-logs/post-rebase-integrity/powerfail/integrity-20261020T162446Z/firstboot.log` | `536deae2656eb34b59377cea71b44e84380e69bb03f5ff837f2d06178b56d80c` |
| `output/qemu-logs/post-rebase-integrity/powerfail/integrity-20261020T162446Z/reboot.log` | `5f0660ddf1e987925cabcedabd6d4d0f5cd89f3f28c1263c404ddfa382bced56` |

失敗試行と全反復試験の個別ログも同じ `output/qemu-logs/` 以下に保存しました。再生成コマンドは上記の手順を使います。
