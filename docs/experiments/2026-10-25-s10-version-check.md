# S10 v2 更新の bundle の番号の比較

- 状態: 完了（QEMU とホスト。実機未確認）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [S10 の最初の記録](2026-10-25-s10-update-rejection.md)、[power-and-updates.md の 7.8](../research/power-and-updates.md#78-bundle-の検証と巻き戻しs10)、[tests/msd-update/run.sh](../../tests/msd-update/run.sh)

## 目的と仮説

#103 で、`manifest` の 1 行目に `version <番号>` を入れて署名し、`msd-update` が実行中の rootfs の番号（`/etc/msd-update/version`）と比べるようにした。古い番号の bundle と番号のない bundle は既定で拒否し、`--allow-downgrade` を付けたときだけ受け入れる。形式の誤った番号は、`--allow-downgrade` を付けても拒否する。

この動作を、ゲストの BusyBox と OpenSSL、実際のブロックデバイスで確かめる。最初の S10 の 9 種類（T0〜T7）も、同じ runner で取り直す。

仮説: T8〜T13 は上の方針のとおりに受理と拒否が分かれる。拒否したときは、非 active スロットと状態ファイルが変わらない。T0〜T7 は最初の記録と同じ結果になる。

## 採否の基準（結果を見る前に書く）

基準は、本測定の前に作業メモに書いた。

1. T8-older、T10-unversioned、T13-malformed-allow は、10 回（QEMU 5、ホスト 5）すべてで終了コードが 0 以外、非 active の root と boot が変わらず、状態ファイルがない。
2. T9-older-allow、T11-unversioned-allow、T12-newer は、10 回すべてで受け入れられ、root と boot が変わり、状態ファイルが `3` になる。
3. T0〜T7 は、最初の記録の表と同じ結果になる（T0、T6-truncated-tail、T7-other-signed は受理。ほかは拒否）。
4. 1 回でも外れたら、取り直さずに所見として記録する。

基準 3 は、作業メモでは最初「T1〜T7 は拒否」と書いていた。T6-truncated-tail と T7-other-signed は最初の記録でも受理なので、書き誤りである。ホストの結果を見た後、ゲストの結果が出る前に、最初の記録の表に合わせて直した。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `b4b1745`（#103 のマージ後の main）。image はこの commit の新しい clone で `make` した |
| runner の commit | `54edc37`（`b4b1745` に S10 の runner の変更だけを足した） |
| ホスト | Ubuntu、x86_64。どちらの試験も開発用イメージ `msd-dev:local` の中（OpenSSL 3.5.7、`/bin/sh` は dash） |
| QEMU | 11.1.2（開発用イメージ）、`raspi3ap`。DTB は CM0 のまま（Bluetooth を無効にする #105 より前） |
| カーネル | `6.18.57-v8`（serial log の `Linux version` の行から） |
| ゲストの OpenSSL | 3.6.5（ゲストの `openssl version`） |
| 実行中の番号 | `1792942296`（rootfs の `/etc/msd-update/version`） |
| 入力の SHA-256 | `sdcard.img` `969d703dbfe0`、`rootfs.squashfs` `3bc11e3e6b50`、`Image` `84c2d12111ce`、試験用 rootfs `0933249f63bb` |
| 繰り返し | QEMU は 5 回起動し、1 回の起動で 15 種類を与えた。ホストは 5 回 |

| ID | bundle | `--allow-downgrade` |
|---|---|---|
| T8-older | 実行中より 1 小さい番号で、正しい鍵で署名した | なし |
| T9-older-allow | T8 と同じ | あり |
| T10-unversioned | `version` の行がない | なし |
| T11-unversioned-allow | T10 と同じ | あり |
| T12-newer | 実行中より 1 大きい番号 | なし |
| T13-malformed-allow | 番号の先頭に `0` を付けた（`01792942296`） | あり |

T0〜T7 の作り方は最初の記録と同じである。ただし、どの bundle も 1 行目に実行中と同じ番号を入れて署名した。ホストの試験では、実際の bundle の番号を実行中の番号とした。

## 手順

```sh
git submodule update --init
docker/msd-dev bash -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
docker/msd-dev env S10_RUNS=5 board/cardputerzero/tools/bench/s10-update-rejection.sh
docker/msd-dev board/cardputerzero/tools/bench/s10-host-real-bundle.sh /work output/images output/msd-update-dev-key.pem 5 host.csv
```

実際には、runner の checkout と image の出力先が別のディレクトリだったので、開発用イメージを `docker run` で直接起動した。`docker/msd-dev` と同じく、runner の checkout を `/work` に mount し、出力先を読み取り専用で mount して `OUTPUT_DIR` と `S10_LOG_DIR` を渡した。

## 計測器の検証

受理されるはずの T0、T9、T11、T12 は、20 回とも root と boot の変化を検出した（`root_changed=1`、`boot_changed=1`）。拒否されるはずの番号のケースでは 0 だった。

ゲストの init script は、bundle を名前の順（`T0`、`T1`、`T10`、`T11`、`T12`、`T13`、`T2`…）に与える。そのため T6-truncated-tail の前に受け入れられるのは T12-newer で、T6 で中身が T0 に戻る。最初の記録では T6 の root と boot が変わらなかったが、今回は変わったのはこのためである。

## 結果

生の値は [ゲスト](2026-10-25-s10-version-check-guest.csv)（75 行。`valid` はすべて 1）と [ホスト](2026-10-25-s10-version-check-host.csv)（75 行）にある。

| ID | QEMU（5 回） | ホスト（5 回） | メッセージ |
|---|---|---|---|
| T8-older | 拒否 5/5。変化なし、状態なし | 拒否 5/5。同じ | `bundle version 1792942295 is older than running version 1792942296; use --allow-downgrade to install it` |
| T9-older-allow | 受理 5/5。root・boot が変化、状態 `3` | 受理 5/5。同じ | `downgrading from version 1792942296 to 1792942295 (--allow-downgrade)` |
| T10-unversioned | 拒否 5/5 | 拒否 5/5 | `bundle has no version; use --allow-downgrade to install it` |
| T11-unversioned-allow | 受理 5/5 | 受理 5/5 | `installing a bundle without a version (--allow-downgrade)` |
| T12-newer | 受理 5/5 | 受理 5/5 | なし |
| T13-malformed-allow | 拒否 5/5 | 拒否 5/5 | `invalid version in manifest` |
| T0〜T7 | 最初の記録と同じ | 最初の記録と同じ | 最初の記録と同じ |

- 基準 1〜3: 満たした。外れた回はなかった。
- T5 と T6b のメッセージは、最初の記録と同じく、ゲストでは `bundle must contain exactly four files`、ホストでは `cannot list bundle` だった。

## 捨てた試行と経緯

なし。runner の shellcheck の指摘（`cmp` の結果の扱いと、`--allow-downgrade` の引数の引用符）は、本測定の前に直した（`54edc37`）。

## 結論

- #103 の番号の比較は、QEMU のゲストとホストで方針のとおりに動いた。古い番号と番号のない bundle は既定で拒否され、`--allow-downgrade` を付けたときだけ受け入れられた。形式の誤った番号は、`--allow-downgrade` を付けても拒否された。拒否したときは、非 active スロットと状態ファイルは変わらなかった。
- 最初の S10 の 9 種類の結果は、番号を入れた後も変わらなかった。
- QEMU での結果であり、実機の microSD と firmware での結果ではない。

## 未確認の点

- 実機の `/proc/device-tree/chosen/bootloader` を使った判定と、tryboot 中の拒否。
- 番号が 18 桁を超えるときと、実行中の rootfs に番号がないとき。どちらもホストテスト（`tests/msd-update/run.sh`）では試しているが、この記録では試していない。
- カーネル 6.18.58 の image と、Bluetooth を無効にした QEMU の DTB では試していない。

## ログ

serial log はコミットしていない。上の手順で作り直せる。今回の SHA-256 は次のとおり。

```text
807018a92872633d4f46722f7d0b0b0a1be116bb17cbfa29e453037770b5c48b  run1.log
5a2c99a79bc7ae3757282b87bee0c9b5005480f18726d25c4b031d1f6e6ccfd8  run2.log
ce990e3e554c001213bb03a4df3c72f0721f51f10759a91820d04c5f533e2ccd  run3.log
ae1773ce0d3ce0ae0fb9d75b82f37863d678da55d0073d700b2e9b29c780f169  run4.log
97e896d2d330a7b11704e4983c73a980e99f5e0718460a636f369204bf703893  run5.log
fab976ec9e3b413b684d55262932722a5afee395e6489d667842d5355ee9eb36  s10-update-rejection.sh
485678c2dd2e9e93b292490d779dbb24d202e7962adeae01647d12eb15b588e0  S97zz-s10test
2b48d6b67ea11e214b2628a80c247a5331872f37ca34d1cf32f9e438943d802e  s10-host-real-bundle.sh
```

bundle は試験のたびに乱数で作るので、SHA-256 は実行ごとに変わる。
