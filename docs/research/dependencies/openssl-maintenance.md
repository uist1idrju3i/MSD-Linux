# OpenSSLの版と保守期限の監視

## 現在の判断（2026-11-12）

利用者の決定により、Buildroot 2026.08.xの固定commitは動かさず、target `libopenssl` と `host-libopenssl` を外部treeで**3.5.9 LTS**に固定します。保守期限は2030-04-08です。[機能・option・既定値の比較](../component-options/openssl-series.md)と[build・QEMUの記録](../../experiments/2026-11-12-openssl-3.5-lts.md)を分けます。同一majorのAPI/ABI方針だけで、CLIやproviderの動作まで同じとは判断しません。

**3.5.9は11月10日のadvisory修正を収録していません。** 12月1日予定の3.5.10は別作業です。今回、自前backportは行いません。次の基盤更新は2026.11.x、その後2027.02 LTSを計画します。今回はsubmodule更新、4系移行、暗号機能の削減を行いません。

### 上流の保守とrelease

2026-11-12 UTC取得の[公式配布表](https://openssl-library.org/source/)、[Release Strategy](https://openssl-library.org/policies/releasestrat/)、[GitHub Releases](https://api.github.com/repos/openssl/openssl/releases?per_page=50)によります。3.6の明示的な期限は11月3日の本記録を引き継ぎ、現在の表からの除外とも区別します。

| 系列 | 最新公開版 | release日 | 通常保守期限 | 判断 |
|---|---|---|---|---|
| 3.5 LTS | 3.5.9 | 2026-09-29 | 2030-04-08 | 今回採用 |
| 3.6 | 3.6.5 | 2026-09-29 | 2026-11-01 | 保守終了。配布表から除外 |
| 4.0 | 4.0.3 | 2026-09-29 | 2027-05-14 | 非LTS。今回は移行しない |
| 4.1 | 4.1.0 | 2026-10-23 | 2027-11-23 | 非LTS。今回は移行しない |

[11月10日のadvisory](https://openssl-library.org/news/secadv/20261110.txt)はLow 5件の修正が公開repositoryに入り、収録releaseは12月1日予定としています。対象はQUIC、AES-GCM-SIV、CMS暗号化です。予定版3.5.10 / 4.0.4 / 4.1.1は取得時の公式配布表になく、各GitHub release APIも404でした。3.6を含む保守終了系列は解析していないと明記されており、対象欄にないことを影響なしとは読みません。製品構成で各問題に到達するかは未判定です。

3.6.5以後の[branch差分](https://api.github.com/repos/openssl/openssl/compare/openssl-3.6.5...openssl-3.6)にはPBKDF1の派生鍵buffer消去修正（11月1日）などがありますが、新しい3.6 security releaseは見つかりませんでした。branchのCHANGESは3.6.6の日付未定・変更欄`none yet`です。branch commitを公開済みreleaseとして扱いません。

### Buildrootの状況と選択肢

取得時の[2026.08.x HEAD](https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/libopenssl/libopenssl.mk)は`75f325ad8425`、[master HEAD](https://github.com/buildroot/buildroot/blob/dc10246725957f68dfea7a47a2d3b1726567452f/package/libopenssl/libopenssl.mk)は`dc1024672595`で、どちらも3.6.5です。現在の固定版`8b238854d909`も3.6.5です。

[4.0.3 bump v9](https://lore.kernel.org/buildroot/20261011130058.3443432-1-bernd@kuhls.net/)は[Patchwork](https://patchwork.buildroot.org/api/1.2/patches/?q=libopenssl&since=2026-09-01&order=-date&per_page=100)で`deferred`でした。Python等の移行を含む案で、取得した両HEADには未反映です。4.1 bump案は今回の検索では見つかりませんでした。

[Buildroot LTS方針](https://buildroot.org/lts.html)は2025.02から奇数年の最初のreleaseを3年間保守します。現行LTSは2025.02.x、期限は2028年3月、次は2027.02です。2026.08.xは通常stableで、[保守期限](https://buildroot.org/download.html)は2026年12月です。OpenSSLだけの一律な追従保証は確認できませんでした。一方、[2025.02.xの3.5 LTS移行議論](https://lore.kernel.org/buildroot/20260413122702.58499-1-thomas.perale@mind.be/)は、OpenSSLのEOLがBuildroot LTSより早いことを系列更新の理由としています。そのrecipeは現在3.5.9です。

| 案 | 工数・利点 | リスクと採否 |
|---|---|---|
| stableの更新待ち | 導入変更は小。上流の統合修正を利用できる | 4.0案はdeferredで時期不明。3.6の保守終了を解消できないため不採用 |
| 外部treeの版・hash override | 変更を限定し、既存recipeの依存・引数・host処理を保つ | 自前の版・hash・patch適合確認と廃止監視を負う。今回採用 |
| Buildroot submodule更新 | 将来は標準recipeへ戻せる | 現HEADへ進めるだけでは3.6.5のまま。ほかのpackageの回帰も増える。2026.11.x、2027.02 LTSへ段階的に計画 |

### 外部overrideの仕組みと廃止条件

[defconfig](../../../configs/msd_cardputerzero_defconfig)の`BR2_PACKAGE_OVERRIDE_FILE`から[package-overrides.mk](../../../board/cardputerzero/package-overrides.mk)を読み、`override LIBOPENSSL_VERSION = 3.5.9`を指定します。BuildrootのMakefileはこのfileを組込みrecipeより前に読みます。通常の代入では後のrecipeに上書きされるため`override`を使います。hostの版はtargetを継承します。

`external.mk`でrecipe評価後に版だけを変えたり、`*_OVERRIDE_SRCDIR`でdownload/hash処理を迂回したりしません。独自のOpenSSL providerやrecipe全体の複製も不要です。`vendor/`は変更しません。

既存`BR2_GLOBAL_PATCH_DIR`を使い、[追加hash](../../../board/cardputerzero/patches/libopenssl/libopenssl.hash)に[公式sha256](https://github.com/openssl/openssl/releases/download/openssl-3.5.9/openssl-3.5.9.tar.gz.sha256)と照合したtarballの値を記録します。

```text
openssl-3.5.9.tar.gz  603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a
LICENSE.txt          7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a
```

licenseはApache-2.0で、LICENSE.txtのhashは既存Buildrootと同じです。既存2 patchを3.5.9に`patch -p1 --fuzz=0`で適用できました（2番目は行offsetあり、fuzzなし）。2025.02.xの同名patchとの差はindex・hunkの位置と周辺表示で、変更する行は同じです。configure引数とpatchは固定Buildrootのものを使います。全legal-infoの状態と配布上の不足は実験記録を参照してください。

[週次チェッカー](../../../.github/scripts/check-pins.py)は次を別行で報告します。[既存workflow](../../../.github/workflows/pins-check.yml)のIssue通知を使い、手動のIssue編集・workflow起動はしていません。

| 行 | 比較と通知 |
|---|---|
| `OpenSSL (Buildroot target/host)` | overrideを読み、3.5系列の公式最新版と比較。4系が新しいだけでは更新要求にしない |
| `OpenSSL upstream support` | 公式の保守期限を独立に判定。期限当日は超過とせず、翌日から通知 |
| `OpenSSL override retirement (pinned)` | 親repositoryのHEADに記録したgitlinkのrecipeと比較。dirtyなローカルsubmoduleを固定値にしない |
| `OpenSSL override retirement (2026.08.x)` | `.gitmodules`の追跡branchのrecipeと比較 |

recipeがoverride以上で、かつ公式配布表でその系列が保守中のときだけ`廃止検討`を通知します。数値が大きくても保守終了の3.6.5では廃止を勧めません。取得失敗、不正なoverride、解析不能は`確認できず`で通知し、「最新」に変えません。

通知は自動削除ではありません。同版の3.5 recipeへ戻す場合もhash・patch・legal-info・host/target・回帰を確認します。4系以上の場合は下記の移行条件も必要です。廃止時はdefconfigの指定、override file、追加hash、専用監視を一緒に見直します。

### 4系へ移行するときの条件

一次資料は[4.0 CHANGES](https://github.com/openssl/openssl/blob/openssl-4.0.3/CHANGES.md)、[4.1 CHANGES](https://github.com/openssl/openssl/blob/openssl-4.1.0/CHANGES.md)、[migration guide](https://github.com/openssl/openssl/blob/openssl-4.1.0/doc/man7/ossl-guide-migration.pod)、[removed APIs](https://github.com/openssl/openssl/blob/openssl-4.1.0/doc/man7/ossl-removed-api.pod)です。

| 変更 | 移行時の対応 |
|---|---|
| major ABI、ENGINE削除 | 全利用者をrebuild。ENGINEが必要ならproviderへ移行。現在の`no-engine`だけで将来のPKCS#11も対応済みとはしない |
| ASN1_STRINGのopaque化、X509 APIのconst化 | 構造体直接参照と型を修正。deprecated APIすべての一律削除ではない |
| 固定TLS/DTLS method、custom EVP method、旧ERR state API削除 | 汎用method/provider APIへ移行 |
| SSLv3、SSLv2 ClientHello、`c_rehash`削除 | 旧protocolを前提にしない。toolは`openssl rehash`へ |
| 古いTLS EC group、未知の明示EC parameterの既定無効化 | 必要な互換optionと相手を個別に確認 |
| FIPS、PBKDF2、CRL、AKIDの変更 | 入力・証明書・providerごとに成功と拒否を確認。FIPS認証済みとは主張しない |
| 4.1のSANなし証明書 | hostname検証でsubject CN/emailを既定参照しない。必要なら`X509_CHECK_FLAG_ALWAYS_CHECK_SUBJECT`を明示。client独自の検証は別確認 |
| 4.1の追加変更 | `SSL_OP_TLSEXT_PADDING`はno-op、`no-ecdsa`/`no-ecdh`削除、`tsget`のPerl依存変更、DTLS 1.3/GREASE、追加deprecationを確認 |

現行defconfigのtarget利用者はOpenSSL CLIとkmod 34.2で、`msd-update`がCLIの`pkeyutl`を呼びます。kernel buildはhost版を使います。以下の計画packageは現在未選択です。静的なsource確認と製品構成での実行を分けます。

| 利用者 | 取得資料で確認した範囲／未確認 |
|---|---|
| 現行CLI・kmod | kmodの署名表示はASN1 accessorを使用。3.5のbuild・署名回帰と4系互換性は別で、後者は未試験 |
| wpa_supplicant 2.12 | ENGINE処理には`OPENSSL_NO_ENGINE`のguardがあり、ASN1 accessorも使う。ENGINE削除だけで無条件のbuild失敗とはしない。SAE/EAP、provider・legacy algorithmの組合せは未試験 |
| curl 8.23.0 | upstreamに4.0.3のCI更新あり。確定的なsource非互換は今回見つからず、当該Buildroot構成の保証ではない |
| RAUC 1.15.2 | ASN1構造体直接参照で4.0のbuild失敗が既知。[issue #1913](https://github.com/rauc/rauc/issues/1913)、[修正 #1914](https://github.com/rauc/rauc/pull/1914)、[Buildroot masterの修正](https://github.com/buildroot/buildroot/commit/aac023e8eab14f72df75a4b5513927e76040b182)。[PKCS#11 provider案 #1779](https://github.com/rauc/rauc/pull/1779)は別件で未merge |
| SWUpdate 2026.05.1 | 確認した署名・復号sourceはEVP/CMS APIを使用。全optionのbuildと署名済みimageの検証は未実施 |
| OpenSSH 10.6p1 | Buildrootはcryptodev選択時だけ`--with-ssl-engine`を渡す。現行defconfigではその選択を確認していないため、ENGINEを一律の障害としない |
| Python 3.14.8 ssl | Buildrootの移行案では大規模patchまたは3.15更新が必要。さらに[TLS 1.2の誤検出 #159387](https://github.com/python/cpython/issues/159387)にupstream修正あり。固定版への収録・backport状態は未確認 |

これらは4系を今回避ける理由であり、3.5.9で計画packageをすべて検証した意味ではありません。3.6から失う機能と利用状況は[系列比較](../component-options/openssl-series.md)に記録します。

### 出典と残件

取得URL、UTC取得時刻、HTTP結果、raw responseのhashは[sources.json](sources.json)に保存しました。失敗した404等も成功と分けています。取得成功を全文review、互換性、licenseの完結の証拠にはしません。

実機の暗号性能、Wi-Fi SAE/EAP・TLS、LCD・keyboard・I2C、firmware tryboot、電源断は未確認です。3.5.10の公開確認と別更新、基盤の段階更新、計画packageのbuildと拒否試験を残します。R24全体の不足とBrotliの延期・公開ゲートは変更しません。

## 2026-11-03時点の判断（旧）

以下は系列変更を決める前の記録です。「依存版を変更していない」という状態と全major比較の監視は当時のもので、上の決定・監視に置き換わります。元の取得結果や未確認の範囲は新しいbuild結果へ読み替えません。

Buildrootのtarget `libopenssl` と `host-libopenssl` は同じrecipeの3.6.5です。上流の[Release Strategy](https://openssl-library.org/policies/releasestrat/)は3.6系列の通常保守期限を2026-11-01としています。2026-11-03の確認では期限超過です。下流が継続保守する根拠は未確認であり、新たなCVEがあると確認した意味でもありません。

公式[Downloads](https://openssl-library.org/source/)では、保守対象の候補は次のとおりです。公開順の先頭だけで最新版を決めません。

| 系列 | 配布版 | 上流の保守期限 | MSD/Linuxでの扱い |
|---|---|---|---|
| 4.1 | 4.1.0 | 2027-11-23 | 最大の安定版候補。major移行としてAPI/ABI・廃止機能・Buildroot統合を調べる |
| 4.0 | 4.0.3 | 2027-05-14 | 4系の別候補。4.1より保守期限が短い |
| 3.5 LTS | 3.5.9 | 2030-04-08 | 長期保守候補。3.6からの機能後退と既存利用を調べる |

現時点では依存版を変更していません。最新版への追従を優先するなら4.1、保守期間を優先するなら3.5 LTSを比較します。API/ABI互換は同一major内という上流方針であり、CLIやproviderの既定動作まで同一とは断定しません。採用前に全変更履歴、target/hostの利用箇所、署名CLI、更新検証、TLS、license、SBOM、legal-info、生成物、QEMUを確認します。実機での暗号性能・更新確認も別に残します。

### 当時の自動監視へ追加した境界

[固定版チェッカー](../../../.github/scripts/check-pins.py)は、親repositoryのHEADに記録されたBuildroot gitlinkのrecipeを取得します。未初期化・別revision・dirtyなローカルsubmoduleの内容を固定版として読みません。取得先は[.gitmodules](../../../.gitmodules)のBuildroot mirrorの固定SHAです。

- `OpenSSL (Buildroot target/host)` は公式配布表の安定版候補と固定版を比較します。全majorの保守対象系列を数値で比較し、pre-releaseや不正な版・系列は受理しません。
- `OpenSSL upstream support` は版比較と別行です。現行配布表の期限を優先し、表にない旧系列はRelease Strategyの明示的な期限を調べます。期限当日は超過とせず、翌日から `保守期限超過` とします。
- 表の形式変更、欠測、重複、日付不正、期限がreleaseより早い表、保守対象なのに配布表にない系列を `確認できず` とします。取得失敗を「最新」に変えません。
- 期限超過・確認不能は[既存の週次workflow](../../../.github/workflows/pins-check.yml)で[Issue #112](https://github.com/uist1idrju3i/MSD-Linux/issues/112)へ通知する条件です。今回はIssueの手動編集・週次workflowの手動起動はしていません。PRではネットワークを使わないfixtureを試します。

開発OCIのDebian配布版とBuildrootの版を混ぜません。既存の[APT台帳](development-apt.csv)ではOpenSSL 3.5.7-1~deb13u3です。今回の追加はDebianのbackport判定や全APTの最新版監視ではありません。署名CLIのhost試験も製品target版の実行証拠にはなりません。

### 当時の残件

R24全体は未完了です。外部toolchainの内包物、全recipeの独立した最新版・保守期限、OCI全stage/arm64、Actions実bundleとrunner、CVE通知・未照合の扱いは[監視差分](README.md#監視の差分)に残ります。今回の修正で全依存が安全、保守中、最新版と認定したわけではありません。Brotliの延期と公開ゲートも変更しません。

再実行・負の対照・実際の入力hashは[検証記録](../../experiments/2026-11-03-maintenance-followup.md)を参照してください。

[依存監査へ戻る](README.md)
