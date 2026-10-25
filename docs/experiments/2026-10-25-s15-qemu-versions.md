# S15 QEMU のバージョン、machine、plugin による起動時間の違い

- 状態: 完了（QEMU のみ。実機とは無関係）
- 日付: 2026-10-25
- 担当: Devin
- 関連: [simulation-plan.md](../research/simulation-plan.md)、[S12 の記録](2026-10-25-s12-squashfs-codec.md)、[boottime の記録](2026-10-20-qemu-boottime.md)

## 目的と仮説

これまでの icount の測定は、開発用イメージの QEMU 11.1.2 で行ってきた。QEMU のバージョン、build、machine（`raspi3ap` と `raspi3b`）、TCG plugin の有無で、同じ image の起動時間（icount の仮想時間）が変わるかを確かめる。変わるなら、異なる QEMU で測った値どうしは比べられない。

仮説: 同じ QEMU のバージョンなら、build と plugin の有無で値は変わらない。バージョンが違うと、TCG の変更で値が変わることがある。

## 採否の基準（結果を見る前に書く）

基準は、本測定を始める前（2026-10-25T16:19Z）に作業メモに書いた。

1. 各条件で 6 回起動し、repeat 0 を warm-up として除き、repeat 1〜5 の `t_ready` の中央値を比べる。`t_init`、`t_data`、`initcall_total` も記録する。
2. 6 回すべてで終了コードが 0、全行が `valid=1` のときだけ、その条件を判定に使う。
3. 中央値の差の絶対値が、基準側の中央値の 1 % と、2 条件の範囲（最大と最小の差）の大きい方の 3 倍のどちらよりも大きいときだけ「差あり」とする。
4. q1112ci と q1112l は build の A/A とする（build の違いが効かなければ同じ値になる）。
5. plugin の命令数は記録だけとする。ログイン後、SIGTERM で止めるまでの待機中の命令も含む。

## 条件

| ID | QEMU | machine | plugin |
|---|---|---|---|
| q1102 | 11.0.2（手元で build） | `raspi3ap` | なし |
| q1112ci | 11.1.2（開発用イメージの `/opt/qemu`） | `raspi3ap` | なし |
| q1112l | 11.1.2（手元で build） | `raspi3ap` | なし |
| q1112ci3b | 11.1.2（開発用イメージ） | `raspi3b`（`bcm2710-rpi-3-b.dtb`） | なし |
| q1102insn | 11.0.2（手元で build） | `raspi3ap` | `libinsn.so` |
| q1112insn | 11.1.2（開発用イメージ） | `raspi3ap` | `libinsn.so` |

| 項目 | 値 |
|---|---|
| image | `87aadf5` の build（S12 と同じ）。カーネルは `6.18.57-v8` |
| 入力の SHA-256 | `sdcard.img` `5610e093d0d30be2c2ae110752e97119847f69b9429b44dc335165c4e8c9c654`、`rootfs.squashfs` `28164bdda81a7ca44e87c444937d01db62cee29a41b33a75e7a4231f7678434b`、`Image` `1c085405fedf067be7c8efeadd1f1a779896baa7de60d6ed139f7faf3c5eb8a3` |
| DTB | `run-qemu.sh` が Bluetooth を無効にして作る QEMU 用の DTB（#105）。CM0 由来は `b3e809de61af`、3B 由来は `7d1509333463`（SHA-256 の先頭 12 桁） |
| runner の commit | `ad8189f`（#105 のマージ後の `78eb4f0` に、この PR の runner の 2 ファイルを足した）。PR では `775cdfd` の上に移した。内容は同じ |
| runner の SHA-256 | `s15-qemu-versions.sh` `6f375daf69abe8a244f8d495f56e2e35da80c5b95211dabf08659750a6b1384d`、`s15/qemu-wrap.sh` `fb1e0b21f34ced4ed4d1c94a848c93e44a792424931429f3d3227ae53626bd60` |
| 開発用イメージ | `msd-dev:local`（image ID `2a2c70d17140`） |
| icount | `run-boottime.sh --mode icount`（`QEMU_ICOUNT=shift=0`。`sleep` は既定の on） |

QEMU の binary を次の表に示す。

| QEMU | 出どころ | binary の SHA-256 | `libinsn.so` の SHA-256 |
|---|---|---|---|
| 11.0.2 | 手元で build | `f0f2066f3b5f2aa89a660f1a91e2347ac4ce372e3d312b1755f9c65df7c4d356` | `be1bbdda38d6c32077d230b95c7056a4dfb7c1a3262ecd480ef213ac1b645729` |
| 11.1.2 | 開発用イメージ（CI で作ったもの） | `a1dfa3b632e3864fe887c90198947c470dc9f47c4e7c0cce8ba952fefe2f0d59` | `b349c328b0bde4a6fb1664995170523a9583769a1f278fe8901dc684f84a0d16` |
| 11.1.2 | 手元で build | `914b3bae533bdf3b8ffe89359006c4a1b230e4e226d9f3bafd566a74cc0307b3` | 使っていない |

手元の build は、`b4b1745` の `docker/msd-dev.Dockerfile` の `qemu` stage を、`QEMU_VERSION` と `QEMU_SHA256` だけ変えて作った。tarball の SHA-256 は 11.0.2 が `3745f6ea88e2e87fe0dc838b2b1d4e0a770bf48e01a1d5a186842a1fff76ccf5`、11.1.2 が `731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016` である。

## 手順

```sh
docker build -f docker/msd-dev.Dockerfile --target qemu \
    --build-arg QEMU_VERSION=11.0.2 --build-arg QEMU_SHA256=<tarball の SHA-256> -t msd-s15-qemu:11.0.2 .
# 11.1.2 も同じ。build した image から /opt/qemu を取り出す
docker/msd-dev env S15_LOG_DIR=<出力先> S15_RUNS=5 \
    S15_CONDITIONS='q1102:<11.0.2 の qemu-system-aarch64>:raspi3ap: q1112ci:/opt/qemu/bin/qemu-system-aarch64:raspi3ap: ...' \
    board/cardputerzero/tools/bench/s15-qemu-versions.sh
```

`S15_CONDITIONS` の各項目は `名前:QEMU の binary:machine:plugin` で、plugin がないときは空にする。runner は条件ごとに QEMU と plugin の SHA-256 を `conditions.log` に書き、`run-boottime.sh` で 6 回起動する。plugin の命令数は各起動の `plugin.log` の `total insns:` から取る。runner は既存の CSV を上書きしない。

## 結果

36 回の起動はすべて終了コード 0 で、valid でない行は 0 行だった。plugin の 12 行もすべて valid だった。

`t_ready`（icount、秒。repeat 1〜5）を次の表に示す。

| ID | 中央値 | 範囲 | repeat 0 |
|---|---:|---:|---:|
| q1102 | 2.538723 | 0.005621 | 3.050956 |
| q1112ci | 2.643888 | 0.033001 | 3.149611 |
| q1112l | 2.647694 | 0.086120 | 3.155132 |
| q1112ci3b | 2.667808 | 0.007461 | 3.237467 |
| q1102insn | 2.540741 | 0.008195 | 3.050485 |
| q1112insn | 2.655349 | 0.028046 | 3.154755 |

判定を次の表に示す。

| 比べたもの | 差 | 閾値 | 判定 |
|---|---:|---:|---|
| バージョン: q1102 → q1112ci | +0.105165（+4.14 %） | 0.099003 | 差あり |
| build の A/A: q1112ci → q1112l | +0.003806（+0.14 %） | 0.258360 | 差なし |
| machine: q1112ci → q1112ci3b | +0.023920（+0.90 %） | 0.099003 | 差なし |
| plugin（11.0.2）: q1102 → q1102insn | +0.002018（+0.08 %） | 0.025387 | 差なし |
| plugin（11.1.2）: q1112ci → q1112insn | +0.011461（+0.43 %） | 0.099003 | 差なし |
| バージョン（plugin あり）: q1102insn → q1112insn | +0.114608（+4.51 %） | 0.084138 | 差あり |

plugin の命令数（repeat 1〜5 の中央値）は、q1102insn が 2,571,567,337、q1112insn が 2,694,697,012 で、11.1.2 の方が 4.79 % 多かった。待機中の命令も含むので、起動の処理の量の差とは言えない。

生の値は次の CSV にある。

- [2026-10-25-s15-qemu-versions-boot.csv](2026-10-25-s15-qemu-versions-boot.csv): 起動時間の全行
- [2026-10-25-s15-qemu-versions-plugin.csv](2026-10-25-s15-qemu-versions-plugin.csv): plugin の命令数の全行

### 事後の追加測定（判定には使わない）

本測定の結果を見た後で、所見 1 を確かめるために、ほかの QEMU や build を動かしていない時間帯に q1102 と q1112ci を同じ手順で 6 回ずつ測り直した（ID は phq1102 と phq1112ci）。基準は本測定と同じものを使ったが、結果を見た後に決めた測定なので、採否には使わない。12 回とも終了コード 0 で、全行が valid だった。

| ID | `t_ready` の中央値 | 範囲 | `wall` の範囲（秒） |
|---|---:|---:|---|
| phq1102 | 2.542518 | 0.013935 | 36.06〜37.13 |
| phq1112ci | 2.649759 | 0.011919 | 286.09〜338.55 |

差は +0.107241 秒（+4.22 %）で、閾値 0.041805 秒を超えた。11.1.2 の範囲は、本測定（0.033 秒）より小さくなった。生の値は [2026-10-25-s15-qemu-versions-posthoc.csv](2026-10-25-s15-qemu-versions-posthoc.csv) にある。

負荷の少ない時間帯でも、11.1.2 の 1 回の起動の実時間は 11.0.2 の約 8 倍だった。原因（QEMU の変更か、build の設定か）は調べていない。

## 所見

1. 本測定では、11.1.2 の範囲（0.028〜0.086 秒）が 11.0.2（0.006〜0.008 秒）より大きかった。11.1.2 の条件のほとんどは、ほかの build と同じ時間帯に走っている。icount の `sleep` が on なので、guest が待っている間の仮想時間は、ホストの実時間に合わせて進む。負荷の少ない時間帯の事後の測定では、11.1.2 の範囲は 0.012 秒になり、差の大きさ（+4.2 %）は変わらなかった。ホストの負荷は範囲を広げたが、バージョンの差は負荷によるものではないと考える。
2. 実時間（`wall`）は判定に使っていない。本測定ではホストの負荷が条件ごとに違ったので、比べられない。事後の測定の値は上の表のとおりである。
3. QEMU の patch（`docker/qemu-patches/`）は、手元の 11.0.2 にも 11.1.2 にも fuzz 付きで当たった（`bcm2835_gpio.h` の hunk 1 が fuzz 2 など）。fuzz が出た hunk は両方で同じだった。11.0.2 では、`bcm2835_peripherals` の hunk の行のずれ（offset）も出た。CI の開発用イメージも同じ Dockerfile で patch を当てるが、CI の build log の fuzz は見ていない。patch はどれも失敗せずに当たった。patch が変える GPIO と電源管理の動作は、S15 では確かめていない。
4. 手元で build した 11.1.2 の binary は、CI の binary と SHA-256 が一致しない（S12 の記録と同じ）。それでも `t_ready` は差なしだった。

## 結論

QEMU 11.0.2 と 11.1.2 では、`t_ready` が約 4 % 違った（11.1.2 が長い）。これは、S12 の閾値（5 %）に近い大きさである。QEMU のバージョンが違う測定どうしは比べず、同じ QEMU の binary で取った基準と比べる。同じ 11.1.2 なら、build（CI と手元）、machine（`raspi3ap` と `raspi3b`）、plugin の有無で差はなかった。

## 限界

- QEMU の仮想時間だけを比べた。実機の起動時間とは関係しない。
- QEMU の 2 つのバージョンしか比べていない。どの変更が差を生んだかは調べていない。
- image のカーネルは 6.18.57 で、6.18.58 では試していない。
