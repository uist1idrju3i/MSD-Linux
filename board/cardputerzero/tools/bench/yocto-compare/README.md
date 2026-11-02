# QEMU 起動比較 runner

Buildroot 同士、または Buildroot と Yocto の入力を比較します。QEMU の値は実機の起動時間・周辺機器・firmware tryboot・電源断耐性を示しません。[2026-11-02 の比較記録](../../../../../docs/experiments/2026-11-02-buildroot-yocto-boottime.md)のコマンドは当時の版です。以後の出力は条件ごとの新しいディレクトリに分けます。

## 一つの条件を測る

固定済みの `docker/msd-dev` 内で実行します。出力先の親は先に作り、`--out` 自体は存在しない名前にします。空のディレクトリやシンボリックリンクも再利用しません。

```sh
board/cardputerzero/tools/bench/yocto-compare/run-compare.sh \
  --condition baseline --kernel output/images/Image \
  --dtb output/images/bcm2710-rpi-cm0.dtb --image output/images/sdcard.img \
  --root-dev /dev/mmcblk0p5 --root-fstype squashfs \
  --ready-marker 'MSD/Linux ready' --mode tcg --runs 5 --out results-baseline
```

別の Buildroot イメージも、条件名と新しい出力先を変えて同様に測れます。入力は変更せず、作業用イメージで初回起動を 1 回、通常起動を指定回数測ります。初回起動後の作業用イメージを通常起動で使います。`icount` と `tcg` の値は分けて比較します。icount は仮想時間であり、wall time と混ぜません。

## 出力と判定

- `results.csv`: 初回、通常起動、失敗を含む全行。条件、mode、boot の組が試行の識別子です。
- `summary.csv`: 成功した通常起動だけの中央値・最小・最大。`n` は通常起動の総数、`pass` はその成功数です。
- `*.log`、`*.provenance`: ログ、commit、追跡ファイルの変更状態、入力・スクリプト・QEMU の SHA-256 と版。ログにも実際の DTB と QEMU の情報を保存します。

タイムアウト、QEMU の終了、時刻の欠損は失敗として保存します。初回の失敗、連続しない boot 番号、指定回数未満の成功があると終了コードは 1 です。CSV の不正な列、重複、非有限値、pass の欠損値は集計時に 2 で止めます。失敗時の作業用イメージと、中断時までの証拠は残します。再試行は新しい出力先で行い、証拠を保存するまで元の出力を消しません。

```sh
python3 board/cardputerzero/tools/bench/yocto-compare/summarize.py results-baseline/results.csv
```

集計器は既定で通常起動 5 回以上の成功を要求します。機能試験で回数を減らすときだけ `--min-runs 1` などを指定し、性能比較の根拠にはしません。

## 既存の比較行列

`run-all.sh INPUT_DIR NEW_OUT_DIR [RUNS]` は従来の 4 条件と A/A を実行します。入力名はスクリプト冒頭にあります。条件と mode ごとに子ディレクトリを作り、すべて成功した場合だけ親に結合 CSV と集計を作ります。失敗した場合は、各子の証拠を確認します。

`tests/yocto-compare/run.sh` は模擬 QEMU による正常・異常系と、既存 54 行の再集計を検査します。本物の QEMU でイメージが起動することは別の試験です。
