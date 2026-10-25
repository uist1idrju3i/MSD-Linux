# 起動時の rootfs の `remount,rw` をやめる前後の比較

- 状態: 完了（QEMU のみ。実機未確認）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [retrospective-2026-10.md の 6.1](../research/retrospective-2026-10.md#61-inittab-の-remountrw)、[dm-verity の記録](2026-10-21-qemu-dm-verity.md)

## 目的と仮説

Buildroot の既定 `BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW=y` は、`/etc/inittab` に `::sysinit:/bin/mount -o remount,rw /` を入れる。root は read-only の SquashFS なので、この行は何も変えない。read-only の dm device では `-EACCES` で失敗する（dm-verity の記録）。defconfig に `# BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW is not set` を足し、この行をやめる。

仮説: inittab の行がなくなる以外、起動、A/B の切り替え、電源断からの回復、起動時間は変わらない。

## 採否の基準（結果を見る前に書く）

基準は、変更後の側のビルドが終わる前に作業メモに書いた。

1. `target/etc/inittab` の有効な行 `::sysinit:/bin/mount -o remount,rw /` が、変更前は 1 行、変更後は 0 行になる。ほかの行は変わらない。
2. rootfs のファイルの一覧（`unsquashfs -lls`）は、inittab 以外で同じになる。
3. 両方で `test-boot.sh` と `test-ab.sh` が通る。
4. 両方で `test-powerfail.sh --smoke` と `--integrity` が通る（`status=ok`、`fsck=0`）。
5. root が read-only で mount されていることを serial log で見る（記録だけ）。
6. 起動時間: `run-boottime.sh` の icount で 6 回起動し、repeat 0 を除いた 5 回の `t_ready` の中央値を比べる。中央値の差の絶対値が、1 % と、範囲（最大と最小の差）の大きい方の 3 倍のどちらよりも大きいときだけ「差あり」とする。
7. dm-verity: 変更後の側で `dm-verity/make-case.sh T0-A2` が `before_count=0` で通る。
8. 外れても取り直さず、所見として記録する。電源断の `--experiment` は時間があれば行い、行わなければ未実施と書く。

## 条件

| 項目 | 値 |
|---|---|
| 変更前 | `b4b1745`（#103 のマージ後の main）を新しく clone して `make` した |
| 変更後 | `0b197bd`（`b4b1745` に defconfig の 1 行と、`make-case.sh` の 0 行を許す変更を足した）を `make` した |
| PR の commit | 測定の後で `775cdfd`（カーネル 6.18.58）の上に rebase した。rebase の後の commit ではビルドも QEMU の試験もしていない |
| 開発用イメージ | `msd-dev:local`（image ID `2a2c70d17140`）。QEMU 11.1.2、`raspi3ap` |
| カーネル | `6.18.57-v8`（両方とも） |
| DTB | `run-qemu.sh` の既定（Bluetooth を無効にした QEMU 用の DTB。#105） |

| 成果物 | 変更前の SHA-256 | 変更後の SHA-256 |
|---|---|---|
| `sdcard.img` | `969d703dbfe0f5650c139954d4c2f512ff9d0fa3915a1c6f5e0e0200636a6c12` | `dcbd5553497de29a50bc4600fb743c54ad5a3b79fee3de9d1aad4d7fb250b9ec` |
| `rootfs.squashfs` | `3bc11e3e6b50556c6c94fc4ceaec15d7a29f339eeb548bcc4039087b61981800` | `2938ef48052a3a7fded11ceb27a754086810979dd2afb7ee6ee5c917d3b76491` |
| `Image` | `84c2d12111ce35c8d8fb7e3f309949fd2151455e18b93675763b750ff3464079` | `22df93ceb3ecb24d4dce12e033db5e903b9af5c3d2ec3a59189887d731662ec1` |
| `target/etc/inittab` | `d881fa9fc769ea0bd00b007abdc26b4e2185be8da38e33f1eb0398eda90540fa` | `18400d8b3247d23c856e5103b45c05cb8c320299a1f2f6e45a66a6e4b15dc86c` |

`rootfs.squashfs` の大きさは、どちらも 23,891,968 byte だった。

## 手順

各 checkout で次を順に実行した。

```sh
git submodule update --init
docker/msd-dev bash -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
docker/msd-dev board/cardputerzero/qemu/test-ab.sh
docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --smoke
docker/msd-dev board/cardputerzero/qemu/test-powerfail.sh --integrity
docker/msd-dev board/cardputerzero/tools/bench/boottime/run-boottime.sh --variant <before|after> --runs 5 \
    --csv output/boottime-remount/<before|after>.csv --log-dir output/boottime-remount/logs
```

起動時間は、変更前の 6 回の後に変更後の 6 回を続けて測った。ほかの QEMU の測定（S15）と同じ時間帯に走った。icount の値は判定に使い、実時間（`wall`）は使わない。

ファイルの一覧は、両方の `rootfs.squashfs` を `unsquashfs -lls` で出して `diff` で比べた。

dm-verity は、変更後の側で `output/images` の `Image`、`rootfs.squashfs`、`sdcard.img` を `V0` に写し、`make-case.sh T0-A2 output <base> <base>/T0-A2` を実行した。

## 結果

| 基準 | 結果 |
|---|---|
| 1. inittab | 満たした。変更前は有効な行が 1 行。変更後は `#::sysinit:/bin/mount -o remount,rw /` とコメントになり、有効な行は 0 行。`diff` の差はこの 1 行だけ |
| 2. ファイルの一覧 | 満たさなかった（所見 1）。ファイルの名前と数は同じ。差は inittab（1,286 → 1,287 byte）と、`.ko.xz` 532 個の大きさ |
| 3. test-boot、test-ab | 満たした。両方とも終了コード 0 |
| 4. 電源断の smoke、integrity | 満たした。両方とも終了コード 0、`status=ok`、`fsck_exit_status=0`、`fs_recovery_messages=no` |
| 5. root の mount | 両方の serial log に `VFS: Mounted root (squashfs filesystem) readonly` が出た。kernel の command line は両方とも `ro`。ゲストの `/proc/mounts` は見ていない |
| 6. 起動時間 | 差なし（下の表） |
| 7. dm-verity | 一部だけ満たした（所見 2）。inittab の検査は `before_count=0`、`after_count=0` で通った。その後の `veritysetup format` は、製品の build に `veritysetup` がないため終了コード 127 で止まった |
| 電源断の `--experiment` | 未実施 |

起動時間（icount、秒。repeat 1〜5）を次の表に示す。

| 側 | `t_ready` の中央値 | 範囲 | repeat 0 | valid でない行 |
|---|---:|---:|---:|---:|
| 変更前 | 3.063319 | 0.055697 | 3.548617 | 0 / 259 |
| 変更後 | 3.045318 | 0.080848 | 3.557815 | 0 / 258 |

差は −0.018001 秒（−0.59 %）で、閾値の 0.242544 秒（範囲 0.080848 の 3 倍）より小さい。12 回の起動はすべて終了コード 0 だった。

生の値は次の CSV にある。

- [2026-10-25-rootfs-stay-ro-boottime.csv](2026-10-25-rootfs-stay-ro-boottime.csv): 起動時間の全行（`variant` が `before` か `after`）
- [2026-10-25-rootfs-stay-ro-powerfail.csv](2026-10-25-rootfs-stay-ro-powerfail.csv): 電源断の integrity の全行（`side` で区別）

## 所見

1. `.ko.xz` の大きさの差は、絶対値で 4〜12 byte だった（増えたものと減ったものがある）。カーネルの設定は `CONFIG_MODULE_SIG_ALL=y` で、署名の鍵（`certs/signing_key.pem`）は build ごとに作られる。`Image` の SHA-256 も変わっている。そのため、module の署名が変わって xz の圧縮後の大きさが変わったものと考えている。module を比べて確かめてはいない（推測）。inittab の変更とは関係しない見込みだが、基準 2 は書いたとおりには満たしていない。
2. dm-verity の case を最後まで作るには、`host-cryptsetup` を入れた dm-verity の実験用の build が要る。今回は inittab の検査が 0 行を受け入れることだけを確かめた。read-only の dm device で起動エラーが消えることは、本リポジトリでは試していない。
3. `test-powerfail.sh --integrity` は、結果を追跡している `docs/experiments/2026-10-20-qemu-powerfail-gpio6.csv` に追記する。今回の行はこの記録の CSV に移し、元の CSV は戻した。

## 結論

QEMU では、`remount,rw` をやめても、起動、A/B の切り替え、電源断の smoke と integrity、icount の起動時間に差は見られなかった。root は変更前も変更後も read-only で mount されていた。defconfig の変更を採る。

## 限界

- 実機では試していない。
- 測ったのは `b4b1745` の上の変更で、カーネルは 6.18.57 である。PR の commit（6.18.58 の上に rebase したもの）では、QEMU の試験をしていない。
- 電源断の `--experiment` と、dm-verity の起動（所見 2）は行っていない。
- 開発用に ext4 の root で build した場合は、root が書き込み可能にならない。必要なら手で `mount -o remount,rw /` を実行する。
