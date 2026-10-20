# CI の Buildroot ビルド：runner と開発用イメージの比較（既存の run の振り返り）

- 状態: 完了
- 日付: 2026-10-20
- 担当: Devin
- 関連: [#58](https://github.com/uist1idrju3i/MSD-Linux/pull/58)、[#60](https://github.com/uist1idrju3i/MSD-Linux/pull/60)、[開発環境と CI の調査](../research/dev-environment-and-ci.md)

## 目的と仮説

#58 で、CI の Buildroot ビルドを runner の上から開発用イメージ（`docker/msd-dev`）の中に移しました。移した後の build job が、runner のときより遅くなっていないかを確かめます。仮説は「ccache が効く状態なら、コンテナーの中でも runner と同じくらいの時間で終わる」です。

この記録は、新しく計画した実験ではありません。すでに終わった CI の run を、後から集めて比べたものです。そのため、繰り返しは 5 回に届かず、条件もそろっていません（下の「条件」）。

## 採否の基準（結果を見る前に書く）

採否は決めません。#58 はすでにマージ済みです。次の 2 点を記録するのが目的です。

1. ccache が効いた run どうしで、`Build image and legal information` の時間が runner より 20% 以上長くなっていないか
2. 遅かった run の原因が、コンテナーではなく ccache の状態で説明できるか

## 条件

| 項目 | 値 |
|---|---|
| 対象の run | workflow「Buildroot build and QEMU smoke test」の build job、9 件（CSV の `run_id`） |
| runner | GitHub-hosted `ubuntu-26.04`（標準）。runner image は 20261012.163。#60 の run だけ 20261018.168 |
| runner での実行（3 件） | main の push。dae05df、f105581、b3d7a57 |
| イメージでの実行（6 件） | #58 の 3 回（af92aeb、9f054ab、dbe83fa）、#58 のマージ後の main（017e068）、#60（de05d5e）、#60 のマージ後の main（e9b3b3f） |
| 計った区間 | build job 全体、`Ensure development image`、`Build image and legal information`（`host-ccache`、`ccache -z`、`make -j"$(nproc)"`、`legal-info`） |
| 時間の出どころ | Actions API の job と step の `started_at`／`completed_at`（秒） |
| ccache の値の出どころ | job ログの `ccache -s` の出力 |
| 変えた条件 | ビルドする場所（runner かイメージか）。ccache の状態は run ごとに違う（CSV の `cache=`） |
| 変えなかった条件 | Buildroot の defconfig とダウンロードのキャッシュ（`buildroot-dl-…` を復元） |
| 繰り返し | 条件ごとに 1〜3 件。5 件に届いていないため、中央値は出さず、各 run の値をそのまま示す |

## 手順

```sh
# job と step の時間
gh api repos/uist1idrju3i/MSD-Linux/actions/runs/<run_id>/jobs --paginate
# job のログ（ccache の統計、ensure の経路、復元したキャッシュの大きさ）
gh api repos/uist1idrju3i/MSD-Linux/actions/jobs/<job_id>/logs > log-<job_id>.txt
grep -E 'Hits:|Cacheable calls|Cache Size|Cache restored from key|was not found; building locally' log-<job_id>.txt
```

## 計測器の検証

- ccache の統計：runner での 3 件と #58 の 1 回目は、`Cacheable calls` が 43 万〜48 万回でした。1 回のビルドは 15,917 回なので、これらは統計をリセットせずに数えた累計です。この 4 件のヒット率は、CSV で `valid=false` にしています。#58 の 2 回目以降は、ビルドの前に `ccache -z` でリセットしています。値は 15,917 回で、各 run の値です。
- 時間：API の値だけを使い、別の計測器とは突き合わせていません。job の時間は、その job の step の合計より長くなっていて、矛盾はありません（例：e9b3b3f の build job は 11:26:11 から 11:52:58 で 1,607 秒、そのうち ensure と Buildroot の step が 1,459 秒）。

## 結果

生の値は [2026-10-20-ci-image-vs-runner.csv](2026-10-20-ci-image-vs-runner.csv) にあります。

| 実行場所 | commit | ccache の状態 | ヒット率 | ensure | Buildroot の step | job 全体 |
|---|---|---|---:|---:|---:|---:|
| runner | dae05df | runner のパスで作ったもの | （累計） | — | 1,267 秒 | 1,413 秒 |
| runner | f105581 | 同上 | （累計） | — | 1,297 秒 | 1,455 秒 |
| runner | b3d7a57 | 同上 | （累計） | — | 1,313 秒 | 1,479 秒 |
| イメージ | af92aeb | runner のパスで作ったもの | （累計） | 441 秒 | 4,221 秒 | 4,814 秒 |
| イメージ | 9f054ab | 空（186 B） | 16.40% | 417 秒 | 4,330 秒 | 4,878 秒 |
| イメージ | dbe83fa | `/work` のパスで作ったもの | 99.82% | 413 秒 | 1,184 秒 | 1,727 秒 |
| イメージ | 017e068 | runner のパスで作ったもの | 16.40% | 489 秒 | 3,921 秒 | 4,570 秒 |
| イメージ | de05d5e | runner のパスで作ったもの | 16.40% | 312 秒 | 2,576 秒 | 3,019 秒 |
| イメージ | e9b3b3f | `/work` のパスで作ったもの | 99.82% | 386 秒 | 1,073 秒 | 1,607 秒 |

- ccache が効いたイメージの run（dbe83fa、e9b3b3f）の Buildroot の step は 1,073〜1,184 秒でした。runner の 1,267〜1,313 秒より短く、基準 1 の「20% 以上長い」には当たりません。
- runner のパスで作った ccache を、コンテナーの中（`/work`）で復元した run は、ヒット率が 16.40% でした。Buildroot の step は 2,576〜4,221 秒かかりました。空の ccache の run（4,330 秒）と同じくらいです。
- 6 件すべてで、`ensure` は「`was not found; building locally`」を出し、イメージをローカルでビルドしていました（312〜489 秒）。PR の run では、そのタグがまだ公開されていません。main の push では、公開のワークフローが build と同時に走るので、build の時点ではまだ公開されていません。そのため、公開済みのイメージを pull する経路の時間は、CI ではまだ一度も計れていません。

## 捨てた試行と経緯

- #58 の 1 回目のヒット率 92.51% を、一度は「その run の値」として報告しました。これは累計の値で、誤りでした（`valid=false`）。
- #58 の 2 回目が復元した 186 B の ccache は、取り消された run が `if: always()` で保存した空のキャッシュでした。#58 で、ビルドが成功したときだけ保存するように直しました。
- #58 の 1 回目は、イメージに cmake がなく、host-cmake をソースからビルドしていました（約 607 秒）。2 回目からは、イメージに Debian の cmake を入れています。
- 017e068 と de05d5e は、ccache の状態もヒット率（16.40%）も同じです。それでも、Buildroot の step は 3,921 秒と 2,576 秒で、1.5 倍の差がありました。de05d5e だけ runner image が違いますが、原因は調べていません。ccache が効かない run の時間は、runner によるばらつきが大きいと見ています（推測です）。

## 結論

- 仮説は支持されました。ccache が効く状態なら、イメージの中のビルドは runner より遅くなっていません（2 件と 3 件の比較）。
- 遅かった 4 件は、ccache がほぼ効いていなかった run です（基準 2）。コンテナーそのものが遅いという証拠は見つかっていません。
- ただし、どの run も `ensure` でイメージをローカルでビルドしていて、job が 312〜489 秒延びていました。main の push でも同じです。高速化の候補として、これから行う CI/CD の高速化の実験で扱います（イメージのビルドを 1 つのジョブにまとめる、registry cache を使う、公開を待ってから pull する、など）。
- runner での 3 件のヒット率は累計の値なので、runner とイメージでヒット率は比べていません。

## 未確認の点

- 条件をそろえた、各 5 回以上の比較（同じ commit、同じ ccache、同じ runner image）
- 公開済みのイメージを pull する経路の `ensure` の時間
- ccache が効かない run の時間のばらつきの原因

## ログ

ログはコミットしていません。上の「手順」のコマンドで、GitHub の保存期間（90 日）のあいだは再取得できます。取得したログの SHA-256 です。

| job_id | SHA-256 |
|---|---|
| 118375881097 | `2e00b8ce4ee31472959f0193e1be2a79c821cbee0aa89665ed613b9f3c7acfe0` |
| 118401208559 | `81cdec39f40afeee542f7d08af040a791fd5f77aa393f5b0f1b663cdffcf5893` |
| 118440219878 | `26a1757ecbce9d0e20a47774850e9aa69774c5f3e3bbe227c3f34d53792565df` |
| 118445559970 | `9eaf853159627518ade0a8adf496ff38f0d845e7cde8e2c15f220fdfe6770f38` |
| 118470400632 | `5316ec0a2b0231c3d24545435ba2824a5772afb0aaef4bcc31084e06e7783d43` |
| 118498464358 | `d1f57c076d5164b6b65bfa5ca90bbc4b8328d30dd54a036f8ef91cca2c59a96c` |
| 118559879289 | `5efac60f0abce31badbc0e6b58cf2df04e878d86fd7dae991a3054e3ee8c8d75` |
| 118581736957 | `9a2dd9fb1b3de992c51b73686d74f43677fae5d21ac04305448221818e2a3ae7` |
| 118601507295 | `593d0d2f7ef10ec3fc001d1866b7a75304c3fe9acafa19fa1f574575c23be5b2` |
