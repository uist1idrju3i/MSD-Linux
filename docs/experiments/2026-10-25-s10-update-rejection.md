# S10 更新の bundle の拒否

- 状態: 完了（QEMU とホスト。実機未確認）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [simulation-plan.md の S10](../research/simulation-plan.md)、[power-and-updates.md の 7.8](../research/power-and-updates.md#78-bundle-の検証と巻き戻しs10)、[tests/msd-update/run.sh](../../tests/msd-update/run.sh)

## 目的と仮説

`msd-update install` に、署名なし、別の鍵で署名、中身の改ざん、途中で切れた bundle を与え、非 active スロットと状態ファイル（`/data/msd-update/installed`）が変わらないことを確かめる。ホストテスト（`tests/msd-update/run.sh`）は合成した小さなファイルで同じ経路を試しているが、ゲストの BusyBox と OpenSSL、実際のブロックデバイスでは試していなかった。

仮説: 署名と SHA-256 の検査は書き込みの前にあるので、不正な bundle はすべて拒否され、スロットは変わらない。`manifest` にはバージョンの欄がなく、`msd-update` はバージョンを比べないので、同じ鍵で署名した古い bundle は受け入れられる。

## 採否の基準（結果を見る前に書く）

基準は、実行前にチャットで共有した計画に書いた。

1. T1〜T5 と T6b（下の表）は、5 回すべてで終了コードが 0 以外、非 active の root と boot が変わらず、状態ファイルがない。1 回でも外れたら不具合とする。
2. T0（正しい bundle）は 5 回すべてで受け入れられ、root と boot が変わり、状態ファイルが `3` になる。これは計測器の検証を兼ねる（変化を検出できることを示す）。
3. T7（同じ鍵で署名した別の内容）は、受け入れられる見込みとする。受け入れられた場合は不具合ではなく、設計上の事実として記録し、対策の採否を利用者に委ねる。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `87aadf5c27846838d2eb16f2f81bb62675569b16`（作業ツリーに変更なし。試験用スクリプトだけを足した） |
| ホスト | Ubuntu 26.04.1 LTS。QEMU 試験は開発用イメージ `ghcr.io/uist1idrju3i/msd-dev:inputs-36d7c1601eab8fc5`（image ID `2a2c70d17140`）の中 |
| QEMU | 11.1.2（開発用イメージの `qemu-system-aarch64 --version`）、`raspi3ap`、CM0 の DTB |
| Buildroot / カーネル | `vendor/buildroot` `d6061d653d`、rpi-6.18.y `234188315037848e5b07d65b85d38edc64095caa`、BusyBox 1.38.0 |
| 使ったツールのバージョン | ゲストの OpenSSL 3.6.5（ゲストの `openssl version`）。署名に使った開発用イメージの OpenSSL 3.5.7。ホスト試験の `/bin/sh` は dash、OpenSSL 3.5.5。`mksquashfs` 4.7.5 |
| 出力先と状態 | `git worktree` で作った checkout の `output/`。新しい `output/` で `make` を通した直後で、`*-reconfigure` はしていない |
| 入力の SHA-256 | `sdcard.img` `5610e093…c9c654`、`rootfs.squashfs` `28164bdd…434b`、`Image` `1c085405…8eb3`、試験用 rootfs `cce286f8…eda2c6` |
| 変える条件 | bundle の種類（下の表） |
| 変えない条件 | 起動スロット A（`/dev/mmcblk0p5`）、非 active は root `p6`・boot `p3` |
| 繰り返し | QEMU は 5 回起動し、1 回の起動で 9 種類を順に与えた。ホストは 5 回 |

| ID | bundle |
|---|---|
| T0-valid | 正しい bundle |
| T1-unsigned | `manifest.sig` を空にした |
| T2-wrongkey | 試験のたびに作った別の Ed25519 鍵で署名した |
| T3-tampered-rootfs | `rootfs.squashfs` の 4096 byte 目を 1 byte 変えた（署名と `manifest` はそのまま） |
| T4-tampered-manifest | `manifest` の先頭の 1 文字を変えた（署名はそのまま） |
| T5-truncated-half | tar を半分で切った |
| T6-truncated-tail | tar の末尾 1024 byte（終端の空ブロック）を切った |
| T6b-truncated-member | tar の末尾から 1024 + 262,144 byte を切り、`boot.vfat` の途中で切れるようにした |
| T7-other-signed | 内容の違う bundle を、正しい開発用の鍵で署名した（古い bundle の代わり） |

QEMU の試験の bundle は、1 MiB の乱数の `rootfs.squashfs` と `boot.vfat` で作った。実際の bundle（約 91 MB）は `/data`（64 MiB）に入らず、試験用の rootfs に入れると起動のたびに読み込みが重くなるためである。実際の bundle は、ホストの試験で使った。

## 手順

```sh
git submodule update --init
docker/msd-dev bash -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig'
docker/msd-dev bash -c 'make -C output -j"$(nproc)" M5STACK_CARDPUTERZERO_VERSION=75518549a2640486f5d13ea72ca4935b198d7c20'
# QEMU のゲストで 5 回（環境変数は docker/msd-dev を通らないので env で渡す）
docker/msd-dev env S10_RUNS=5 board/cardputerzero/tools/bench/s10-update-rejection.sh
# ホストで、ビルドした実際の bundle を使って 5 回
board/cardputerzero/tools/bench/s10-host-real-bundle.sh "$PWD" output/images output/msd-update-dev-key.pem 5 host.csv
```

`M5STACK_CARDPUTERZERO_VERSION` は、`git worktree` の checkout で必要になった。submodule の `.git` が checkout の外（コンテナーに mount されていない場所）を指すので、コンテナーの中の `git rev-parse HEAD` が失敗し、版が空になる。通常の clone では要らない。

`s10-update-rejection.sh` は、rootfs を展開して試験用の init script `S97zz-s10test` と bundle を `/usr/share/msd-s10/` に入れ、SquashFS を作り直してスロット A に書く。カーネルの引数に `msd.s10test=1` があるときだけ、init script が各 bundle で `msd-update install` を実行し、前後の root と boot の先頭 2 MiB の SHA-256 と状態ファイルを serial に出す。既存の CSV があると上書きせずに止まる。

`s10-host-real-bundle.sh` は、partition と device tree をファイルで置き換え（`tests/msd-update/run.sh` と同じ `MSD_UPDATE_*` の環境変数）、`fsync` を何もしない stub にして実行する。

## 計測器の検証

T0 は 5 回とも root と boot の変化を検出した（`root_changed=1`、`boot_changed=1`）。T7 も同じく変化を検出した。変化の検出が常に 0 になっていないことを、この 2 種類で確かめた。

QEMU には Raspberry Pi の firmware が作る `/proc/device-tree/chosen/bootloader` がない。init script は 5 回とも `dt=substitute partition=2 tryboot=0` を出し、`/tmp` に置いた値（スロット A から起動、tryboot ではない）を `MSD_UPDATE_DT_DIR` で渡した。tryboot 中の拒否は、この試験では確かめていない。

## 結果

生の値は [2026-10-25-s10-update-rejection.csv](2026-10-25-s10-update-rejection.csv) にある（360 行。`valid` はすべて 1）。

| ID | QEMU（5 回） | ホスト（5 回） | QEMU のメッセージ |
|---|---|---|---|
| T0-valid | 受理 5/5。root・boot が変化、状態 `3` | 受理 5/5。同じ | なし |
| T1-unsigned | 拒否 5/5。変化なし、状態なし | 拒否 5/5。同じ | `bundle signature verification failed` |
| T2-wrongkey | 拒否 5/5 | 拒否 5/5 | `bundle signature verification failed` |
| T3-tampered-rootfs | 拒否 5/5 | 拒否 5/5 | `bundle SHA-256 verification failed` |
| T4-tampered-manifest | 拒否 5/5 | 拒否 5/5 | `bundle signature verification failed` |
| T5-truncated-half | 拒否 5/5 | 拒否 5/5 | `bundle must contain exactly four files`（ホストは `cannot list bundle`） |
| T6-truncated-tail | 受理 5/5。状態 `3`。T0 と同じ内容なので root・boot の hash は変わらない | 受理 5/5 | なし |
| T6b-truncated-member | 拒否 5/5 | 拒否 5/5 | `bundle must contain exactly four files`（ホストは `cannot list bundle`） |
| T7-other-signed | 受理 5/5。root・boot が変化、状態 `3` | 受理 5/5 | なし |

- 基準 1: 満たした。T1〜T5 と T6b は 10 回（QEMU 5、ホスト 5）とも拒否され、非 active スロットと状態ファイルは変わらなかった。
- 基準 2: 満たした。
- 基準 3: 見込みどおり T7 は受け入れられた。
- T6 は tar の終端の空ブロックだけを切ったもので、4 ファイルの中身はそろっている。受け入れて問題はない。
- 途中で切れた tar の扱いは、ゲストの tar（BusyBox）とホストの GNU tar で違った。ゲストでは、`tar -t` が途中までの一覧を出して止まり、ファイル数の検査で拒否された。どちらも書き込みの前に止まった。
- QEMU の 5 回の serial log に `bcm2835-aux-uart 3f215040.serial: error -EINVAL: unable to register 8250 port` が 1 回ずつ出た。`check-serial-log.sh` の検出の対象ではない。試験用の init script を入れない通常の起動でも出るかは、この記録では確かめていない。

## 捨てた試行と経緯

1. ホストの試行の 1 回目（予備）: `fsync` コマンドがホストになく、T0・T6・T7 が書き込みの後に終了コード 127 で止まった。`tests/msd-update/run.sh` と同じく `fsync` の stub を `PATH` に置いて直した。このとき T6 の切り方は終端の空ブロックだけだったので、中身を切る T6b を足した。
2. QEMU の試行の 1 回目: serial log に制御文字が入っていて、`grep` が「binary file matches」と出し、CSV の 9 行すべてが `missing` になった。serial log 自体には 9 種類の結果があり、上の表と同じだった。`grep -a` に直して取り直した。また、`S10_RUNS=1` を `docker/msd-dev` の前に置いたが、コンテナーに渡らず、5 回の既定で動いていた。途中で止め、`docker/msd-dev env S10_RUNS=5 …` の形に改めた。この試行の CSV は使っていない。

## 結論

- 署名なし、別の鍵、改ざん、途中で切れた bundle は、ゲストの `msd-update` が書き込みの前に拒否する。非 active スロットと状態ファイルは変わらない（QEMU とホストで各 5 回）。
- 同じ鍵で署名した bundle は、中身が古くても受け入れる。`manifest` にバージョンがなく、バージョンを比べる処理もないためである。署名済みの古い bundle を使えば、既知の不具合があるバージョンへ戻せる。対策（`manifest` に単調に増える番号を入れ、`/data` などに記録した番号と比べる）の採否は利用者が判断する。案は [power-and-updates.md の 7.8](../research/power-and-updates.md#78-bundle-の検証と巻き戻しs10) にある。
- QEMU での結果であり、実機の microSD と firmware での結果ではない。
- その後、#103 で番号の比較を入れた。同じ runner で取り直した結果は [S10 v2](2026-10-25-s10-version-check.md) にある。

## 未確認の点

- 実機の `/proc/device-tree/chosen/bootloader` を使った判定と、tryboot 中の拒否。
- 約 91 MB の実際の bundle をゲストの中で与えること（ホストでは試した）。
- 書き込みの途中での電源断。非 active スロットだけが壊れ、状態ファイルは書かれない設計だが、この試験では試していない。

## ログ

serial log はコミットしていない。上の手順で作り直せる。今回の SHA-256 は次のとおり。

```text
ea9dbfd39cba6fb55892118d8584bffcec5f27eb48fe41b4deaf10027a422898  run1.log
edd29b47fac3d3452e75a2f2523658325e35a72edc1ee216a8340c76ebc77c3c  run2.log
571052f3906f93c178aa338af93781aac2bc4bfb44762d1d0adb8224cad0cfe0  run3.log
26e3aaf1cb4cac32110a8c5e93840c5678321eab4868fdd017ab2f5a32311117  run4.log
c4e006cdb40a31c71b7d1164177aa5392ec6b859ceabe3ba3c1d7cdbf752b7bd  run5.log
a9a1f823dffd0b431b52ac33bb1e8a611b6363d1c73f16c558755143074d263e  s10-update-rejection.sh
7b95a294bcdcc643cb2e520d8bf24cde744aa0092949caf969ec9e0f5b1acdac  S97zz-s10test
5c686d541712c085fbf66085438581390e6cc5c8f8ff608ef9749bbede3613bd  s10-host-real-bundle.sh
```

bundle は試験のたびに乱数で作るので、SHA-256 は実行ごとに変わる。
