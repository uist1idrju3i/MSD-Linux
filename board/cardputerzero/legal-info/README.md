# legal-infoの補足資料（選択肢A）

これはBuildrootのlegal-infoに追加する補足資料です。元のREADME・manifest・警告を変更・削除しません。警告ゼロ、完全な対応source、配布許諾の確認を意味しません。

## 収集したもの

- `buildroot-<gitlink commit>.tar.gz`: 実行時のproject HEADの`vendor/buildroot` gitlinkを読み、存在するcommit objectから`git archive`しました。作業treeのcopyではなく、submoduleの履歴全体も含みません。
- `licenses/`: Bootlinのlicense原文です。固定builder commitのhash metadataと照合してrepoへ固定したSHA-256で、取得のたびに検査しました。
- `metadata/`: 固定したpin、SDKの`summary.csv`・`README.txt`・`buildroot.config`。Bootlin builderと製品側Buildrootは別のtreeです。
- `manifest.json`・`manifest.csv`: componentの版、source URLと参照hash、patchの場所、licenseの収集状態。空のsource SHA-256欄は未提供で、SHA-512があれば別欄に残します。archive本文の検証済みhashと読み替えません。
- `SHA256SUMS`: このfile自身を除く補足資料のSHA-256です。

## 未収集

Bootlinの23 source archive、約335 MiBは収集していません。各URL・参照hash・当時のbyte数をmanifestへ列挙しました。GCC初期段と最終段は同じsourceを参照します。数値は独立archiveを数えたもので、component数ではありません。

patch本文・seriesと適用順序、Bootlin builder tree全体、Linux headers 5.4.296のlicense原文も未収集です。directoryとbuilder recipeの参照を、必要なpatchを全部保存した証拠とはしません。製品の外部tree全体のarchiveも含まず、project commitとcollectorのhashだけを記録しています。

Buildroot archiveの追加で元の「Buildroot source未保存」のREADMEが消えたように扱いません。Bootlin licenseの補足も、元packageのLICENSE_FILES定義を変更したものではありません。対応sourceの充足、toolchain再構築、全配布物の許諾条件は別に点検してください。

## 再実行

CIでは`make legal-info`成功後にcollectorを実行し、license原文をHTTPSで取得します。hash不一致・入力欠落・通信失敗は失敗にします。途中の収集物を成功したsupplementとして残しません。

offlineでは固定pinの`path`どおりにlicense treeを事前配置し、`--license-dir`を指定します。その場合は通信せず、同じSHA-256を検査します。既にsupplementがある出力へは上書きしません。再実行時は元の証拠を保存し、新しいlegal-info出力を使ってください。
