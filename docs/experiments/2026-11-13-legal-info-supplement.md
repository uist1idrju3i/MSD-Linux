# legal-infoの補足資料collector

- 日付: 2026-11-13
- 状態: 実legal-infoで収集・照合済み。完全な対応sourceではない
- 基準commit: `c6ef65c60e8f2b13b20ceb4116f37aa285718c78`

## 目的と採否の基準（実行前）

選択肢Aを実装し、元の警告・READMEを残したまま、固定Buildrootのsource archiveとBootlinのlicense原文を補足します。完全な対応sourceや再配布許諾の確認とは区別します。

1. 現行gitlinkからBuildroot commitを読み、`git archive`したarchiveのSHA-256を記録します。shallowでも対象objectがあれば動作することをhost fixtureで試します。
2. Bootlin SDKのsummary・README・configと固定metadataを照合し、各license原文を固定SHA-256で検査します。不一致・入力欠落は終了値が0以外で、成功したsupplement directoryを残さないことを基準にします。
3. 実際の`make legal-info`後に1回収集し、元の全fileのhashが変わらず、READMEの警告2件が残ることを照合します。機能試験なので5回の性能反復にはせず、速度の結論は出しません。
4. 同じ入力で2回収集したarchive・manifestのhashが同じことをA/Aの対照とします。23 source archive（約335 MiB）・patch・Bootlin builder tree・Linux headers 5.4.296のlicenseを未収集として列挙します。

## 条件

既存warmな`output-openssl-lts`でlegal-infoを再生成しました。新規full build、packageのreconfigure、ccache比較、kernel・rootfsの再測定はしていません。QEMUも使いません。元の出力は[OpenSSL LTS実験](2026-11-12-openssl-3.5-lts.md)由来です。今回のcollectorは基準commit上のdirty差分で実行し、clean commitからの再buildとは区別します。

hostはUbuntu 26.04.1 LTS、Linux `7.0.0-43-generic` x86_64です。実行した開発imageはDebian 13.7、Python 3.13.5、Git 2.47.3でした。image IDは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`です。

collectorのSHA-256は`3713a892e6c8c1ce20bc68673c29a15a610ea83f7058055dca1b785fab3ce98e`、固定metadataは`2801ae0d6bf688586039e310ead13eebbf3cd015e12988153737887b8fed387c`です。SDKの3 file、全入力・出力・原fileのhashは[CSV](2026-11-13-legal-info-supplement.csv)へ443行で保存しました。CSVは性能分布ではなくhash・件数・終了状態の記録です。

## 実行手順

```sh
docker/msd-dev make -C output-openssl-lts legal-info
docker/msd-dev python3 .github/scripts/legal-info-supplement.py --output output-openssl-lts
tests/legal-info-supplement/run.sh
```

`make legal-info`後、収集前に原directoryを`output-legal-supplement/aa/legal-info`へcopyしました。A/A側の`host/opt/ext-toolchain`は同じSDKへの相対symlinkです。online収集後は次のoffline収集と比較しました。

```sh
docker/msd-dev python3 .github/scripts/legal-info-supplement.py \
  --output output-legal-supplement/aa \
  --license-dir output-openssl-lts/legal-info/supplement/licenses
```

Pythonの`hashlib`で、manifestに記録した原file一覧と再採取した全原fileを比較し、両supplementの全fileも比較しました。収集の成功表示だけを合格の根拠にはしていません。

## 結果

| 項目 | 実測・照合結果 |
|---|---|
| Buildroot gitlink | `git ls-tree HEAD vendor/buildroot`から`8b238854d909c9cce32ef9671d968b03e323b55d`を取得。指定文の誤記は使用しない |
| Buildroot archive | 7,166,761 bytes、SHA-256 `3c39d8ce82ddcf59c1c2b30a302a27205a24dba265bd940ae1811fd778e66591` |
| manifest JSON | 87,910 bytes、SHA-256 `b1de6437193b9a43a6ec04f9c1ffedec0df83a82f521fac27c8fd4c131de6a87` |
| manifest CSV | 18,167 bytes、SHA-256 `0def466e11eefab8c2f3352c22e1ad08c98f819fce97222ffc90a634ca9a614d` |
| Bootlin | 25 component、41 license fileの固定SHA-256が一致 |
| 原file | 261 fileの内容hash・一覧が収集前後で一致 |
| 原README | SHA-256 `34733abfe1a06f8c76ab07ba74a263db922f81ed7dbb19cd7a44a00325741e63`が不変、警告2件を保持 |
| A/A | archive・manifestを含むsupplement全50 fileのhashが同じ |
| host回帰 | 最終12 testsが成功。改変license、欠損、空metadata、通信失敗、欠損commit、shallow object、相対出力を含む |

原READMEの警告は次の2件です。補足成功でwarningを消したとは扱いません。

```text
WARNING: the Buildroot source code has not been saved
WARNING: toolchain-external-bootlin-2025.08-1: cannot save license (TOOLCHAIN_EXTERNAL_BOOTLIN_LICENSE_FILES not defined)
```

## 失敗した試行

最初のoffline A/Aは終了値1でした。SDK symlinkがhostの絶対パスを指し、container内ではsummary.csvが見つかりませんでした。`output-legal-supplement/collect-aa-first.log`を保存し、相対symlinkへ直したretryは終了値0でした。collector自体を変更して失敗を隠していません。原fileと成功したsupplementを消さず、初回ログとretryログのhashをCSVに残しました。

host試験は最初11件、相対出力の回帰を追加した最終稿で12件成功しました。実収集は最終collectorの固定hashで行っています。実行中のcollectorは編集していません。

## 残る範囲

23 source archive、351,536,922 bytes（335.252 MiB）、patch本文・series・適用順、Bootlin builder tree全体、Linux headers 5.4.296のlicenseは未収集です。byte数は先行調査のHTTP metadataで、今回archive本文を取得して再計測した値ではありません。

source archiveの参照hashは20件がSHA-256、残る3件はSHA-512のみです。GCC initial/finalは同じarchiveを参照するため、manifestでは4 componentのSHA-256欄が空です。SHA-512からSHA-256を作ったり、licenseのSHA-256をsourceのhashへ流用したりしません。

Buildroot archiveは製品側gitlink、Bootlinのbuilderは別commitです。外部tree全体のarchiveは未収集で、project commitとcollectorのhashを記録するにとどまります。完全な対応source、toolchain再構築、全配布物のlicense compliance、実機動作は未確認です。push後CIの実行結果もこのローカル記録には含みません。
