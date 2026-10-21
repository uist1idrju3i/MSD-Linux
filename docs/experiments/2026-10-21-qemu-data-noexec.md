# `/data` の `noexec` の QEMU 試験

- 状態: 完了（QEMU のみ。実機とアプリの互換性は未確認）
- 日付: 2026-10-21
- 担当: Devin
- 関連: docs/research/simulation-plan.md の小項目「`/data` の `noexec`」、docs/research/security-hardening.md

## 目的と仮説

`/data` の ext4 に `noexec` を足したとき、起動と `/data` の準備が壊れないか、何を防げて何を防げないかを確かめます。

仮説: `/data` 上のファイルを直接実行することは防げます。一方で、`sh <file>` のようにインタープリターに渡す実行は防げません。`/data/etc` を lowerdir にした `/etc` の overlay は、overlay の mount が `noexec` でないため、`/etc` 経由なら実行できると予想します。

## 採否の基準（結果を見る前に書く）

各 variant を 5 回行います。1 回は 2 起動です。1 回目の起動で試験用のファイルを作り、同じイメージで 2 回目を起動して検査します。

- P1: 2 回目の起動で、`/proc/mounts` の `/data` に `noexec` がある（`noexec` だけ）。base にはない。
- P2: `/data/probe-bin/busybox`（`/bin/busybox` のコピー、0755）を直接実行する。`noexec` では拒否（終了値 126）、base では成功。
- P3: `/data/probe.sh`（`#!/bin/sh` のスクリプト、0755）を直接実行する。`noexec` では拒否、base では成功。
- P4: `sh /data/probe.sh` は、両方で成功する。
- P5: `/data/etc/msd-probe.sh` を `/etc/msd-probe.sh` として直接実行する。合否には使わず、結果を記録する。実行できた場合は「`/etc` の overlay 経由では防げない」と明記する。
- P6: 両方の起動で `MSD/Linux ready` に届き、`check-serial-log.sh` が通る。

5 回とも P1〜P4 と P6 が期待どおりなら、`noexec` を採用の候補とします。1 回でも P6 が失敗したら不合格とします。最終的な採否は、実機と利用するアプリを確かめてから決めます。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `39ccd234761a76f818c128a19b97fe8af1cf207b`（この commit から新しく全体をビルド） |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| QEMU | 開発用イメージ内の `qemu-system-aarch64 --version`: QEMU emulator version 11.1.2。machine `raspi3ap`、RAM 512 MiB、TCG |
| 使ったツールの版 | Buildroot の host tools: mksquashfs/unsquashfs 4.7.5、sfdisk 2.41.5 |
| 入力の SHA-256 | `Image`: `4bad7a2ed1d31272dbca4c716fc96cff3211ce16266f6713920a4275e98a2505`、`rootfs.squashfs`: `7bc7c5174ae81674ae130edc7583a435aad3e432166642ad948deddbb7b6ab57`、`sdcard.img`: `6cc795a97b2a4133717351b88b5f5006e24ee74e88a9ec5f5fb777b2b5700713`、DTB `bcm2710-rpi-cm0.dtb`: `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` |
| 変える条件 | `noexec` variant だけ、`etc/fstab` の `/data` 行と `S02msd-data` の `mount -o` に `noexec` を足す |
| 変えない条件 | kernel、DTB、cmdline、SquashFS の圧縮方式と block size、data.ext4 の初期内容、A スロット |
| 試験用 hook | 両 variant に `S99zz-noexec-probe` を足す。通常のイメージには入れない |
| 繰り返し | 各 variant 5 回（1 回 = 2 起動）。この前に予備試行を 1 回ずつ行った（集計に入れない） |

## 手順

```sh
docker/msd-dev make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig
docker/msd-dev make -C output -j"$(nproc)"
d=board/cardputerzero/tools/bench/data-noexec
docker/msd-dev "$d/make-variant.sh" base output/s27/noexec-base "$d/S99zz-noexec-probe"
docker/msd-dev "$d/make-variant.sh" noexec output/s27/noexec-noexec "$d/S99zz-noexec-probe" noexec
for i in 1 2 3 4 5; do
  docker/msd-dev "$d/run-probe.sh" output/s27/noexec-base "/work/output/s27/base-r$i"
  docker/msd-dev "$d/run-probe.sh" output/s27/noexec-noexec "/work/output/s27/noexec-r$i"
done
docker/msd-dev "$d/summarize-noexec.sh" /work/output/s27 > noexec.csv
```

`make-variant.sh` は既存の SquashFS を展開し、hook を足して（`noexec` variant では mount の設定も変えて）作り直し、A と B の rootfs パーティションに書き込みます。`noexec` を足す置換は、対象の行がそれぞれ 1 か所だけであることを確かめてから行います。`run-probe.sh` は同じイメージで QEMU を 2 回起動し、1 回目は `=noexec= stage1-done`、2 回目は `=noexec= finished` が出たら QEMU を止めます。

## 計測器の検証

base は P2〜P5 がすべて成功し、`noexec` は P2・P3 が拒否されました。2 つの variant で結果が分かれるので、hook は mount の違いに反応しています。`/proc/mounts` の値も、それぞれの variant で期待どおりでした（P1）。

## 結果

| variant | 回数 | P1 `noexec` | P2 ELF を直接実行 | P3 スクリプトを直接実行 | P4 `sh` で実行 | P5 `/etc` overlay 経由 | P6 ready・serial 検査 |
|---|---|---|---|---|---|---|---|
| base | 5 | なし 5/5 | 成功 5/5 | 成功 5/5 | 成功 5/5 | 成功 5/5 | 10 起動すべて通過 |
| noexec | 5 | あり 5/5 | 拒否（126）5/5 | 拒否（126）5/5 | 成功 5/5 | 成功 5/5 | 10 起動すべて通過 |

`noexec` の mount オプションは `rw,nosuid,nodev,noexec,noatime,errors=remount-ro,data=ordered` でした。P2・P3 の拒否は `Permission denied` です。値は同名の CSV にあります。

## 結論

- QEMU では採否の基準を満たしました。`noexec` を足しても起動、`/data` の準備（fsck、拡張、`/data/etc` などの作成）、serial の検査は変わりません。
- 防げるのは `/data` 上のファイルの直接実行だけです。`sh /data/x` のようにインタープリターへ渡す実行は防げません。
- `/data/etc` に置いたファイルは、`/etc` の overlay 経由なら実行できます（P5、5/5）。`/data/etc` から実行ファイルを持ち込めなくするには、overlay の mount 側にも `noexec` が要ります。ただし `/etc/init.d` などを実行できなくなるので、別の検討が必要です。
- 製品の設定はまだ変えていません。採用の前に、実機で使うアプリと更新処理（`msd-update` は `/data/msd-update` を状態の保存にだけ使い、そこから実行はしません）を確かめます。

## 失敗・中止した試行

- 最初の hook は 1 回目の起動の最後に `reboot` を呼び、QEMU の中で 2 回目の起動をする設計でした。`run-qemu.sh` は QEMU で `bcm2835_wdt` を blacklist しているため、guest の reboot で QEMU が再起動せず止まりました（予備試行の base と noexec の各 1 回）。同じイメージで QEMU を 2 回起動する方式に変えました。
- 集計の初版は `MSD/Linux ready` を行頭で数えていました。noexec の 3 回目の 2 回目の起動で 0 と数えましたが、ログでは行の前に制御文字（`\001\003\f`）が入っていただけでした。ready の行はありました。行頭の条件を外して数え直し、結果は上の表のとおりです。
- 本番後に、スクリプトのパスを `/work` 固定からリポジトリ相対に直しました。直したあとに noexec の variant を作り直して 1 回試し、P1〜P5 が本番と同じ結果になることを確かめました。作り直した SquashFS の SHA-256 は本番のものと一致しません。`unsquashfs -lln` の一覧を比べると、違うのは `etc`、`etc/init.d`、`etc/fstab`、`S02msd-data`、hook の更新時刻だけで、hook の中身の SHA-256 は一致しました。

## ログ

大きな serial log はコミットしていません。各起動のログの SHA-256 は CSV の `note` 列にあります。上の手順で作り直せます。
