# legal-info補足資料の収集と残件

## 現在の範囲

[SBOMとlegal-infoの調査](sbom-coverage.md)に続く選択肢Aの実装です。collectorは[固定pin](../../../board/cardputerzero/legal-info/bootlin-2025.08-1.json)を使い、製品のrootfsではなくbuild host上で動きます。CIでは`make legal-info`成功後に[collector](../../../.github/scripts/legal-info-supplement.py)を実行し、その後のlegal-info tarへsupplementも含めます。

[実験](../../experiments/2026-11-13-legal-info-supplement.md)では、元のREADMEと全261 fileを保持し、製品側BuildrootのarchiveとBootlinの41 license fileを追加しました。元の`legal-info.sha256`は変更せず、補足内の`SHA256SUMS`で追加fileを照合します。これは元packageの警告を解決する変数定義ではありません。

## 一次資料と固定

- SDKのREADME・summary・configは、Buildrootが固定する`aarch64--glibc--stable-2025.08-1`のものです。3 fileのSHA-256をpinし、別のtoolchainを黙って収集しないようにしました。
- SDKの`summary.csv`はheaderを除いて27 recordです。`gcc-final`と`gdb`が各2回現れるため、同じcomponent/versionをまとめたcollectorの25 componentとは数え方が違います。source配布の23 archiveとも別の単位です。
- builderは[Bootlinの2025.08.1 tag](https://github.com/bootlin/buildroot-toolchains/tree/toolchains.bootlin.com-2025.08.1)に対応するcommit `83947c7bb6158072bc2f52b58e90891cd3dc04a2`です。各packageの`.hash`と、builder自身のCOPYINGからlicense SHA-256を得て、[Bootlinのlicense配布](https://toolchains.bootlin.com/downloads/releases/licenses/)の本文と照合しました。出典URLとmetadata fileのSHA-256もpinへ記録しています。
- [source配布](https://toolchains.bootlin.com/downloads/releases/sources/)の23 archiveをURL・参照hashで列挙します。20件はSHA-256、GCC・GDB・binutilsの3 archiveはbuilder metadataがSHA-512のみです。未提供のSHA-256を空欄にし、元のSHA-512を残します。本文未取得なのでsource検証済みとはしません。
- patchの参照先は配布directoryと固定builder recipeです。patch本文、series、適用順序の完全性は未確認です。Linux headers 5.4.296はSDK summaryのlicense file欄が空で、別版のLinux COPYINGを流用せず未収集としました。

製品側Buildrootのcommitは、実行時の`git ls-tree HEAD vendor/buildroot`から読みます。上記のBootlin builderとは別物で、両者を同じsource一式と扱いません。存在するgitlink objectを`git archive`するため、shallowでも対象objectがあれば動作します。

固定Buildrootの[Makefile:874](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/Makefile#L874)は`legal-info-prepare`でsource未保存の警告を無条件に追加します。補足collectorやconfigでこの元の警告を隠す方針ではありません。Linux headersのlicense不足とも別の残件です。

## 取得方式の選択

CIは既にsource downloadを使う構成で、offline-onlyではありません。license本文をrepoへvendorせず、**固定hash＋収集時download**を採用しました。HTTPSとSHA-256を検査し、本文の変更、404、通信失敗、入力欠落はcollectorの失敗にします。更新された本文へ自動追従しません。

offline用には同じpinの`path`で並べたlicense treeを別途保存し、`--license-dir`を指定します。通信せず同じhashを検査します。実測したonline/offline A/Aでは補足全50 fileのhashが一致しました。Git・Python・gzipの実装をまたぐbyte単位の同一性までは保証していません。

```sh
make -C output legal-info
python3 .github/scripts/legal-info-supplement.py --output output
# offlineの場合
python3 .github/scripts/legal-info-supplement.py --output output \
  --license-dir path/to/pinned-license-tree
```

2つは別々の新しいlegal-info出力で実行します。既存のsupplementには上書きせず、失敗途中のdirectoryを成功した収集物にしません。

## 更新時の点検

toolchainの更新ではSDKの3 file、builder commit、各componentの版・source hash・patch参照・license原文の差分を読み、許諾条件の変更を判断してからpinを更新します。sourceのSHA-512しかないことをhash欠落の隠蔽と混同せず、SHA-256が未提供である事実を残します。

[host tests](../../../tests/legal-info-supplement/run.py)で改変拒否・欠損・manifest・shallow・A/Aを検査し、新しい実legal-infoでも原fileの不変と警告保持を確認します。23 archive約335 MiB、patch、builder tree、Linux headers license、外部tree archiveの残件は、収集して照合するまで未収集です。成功は再配布・完全な対応sourceの判定ではありません。
