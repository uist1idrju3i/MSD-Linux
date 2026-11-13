# 製品timezoneの既定値とtzdata

[component option一覧](README.md) / [書き込みの台帳](../../design/write-policy.md)

2026-11-12の変更では、既定timezoneをAsia/Tokyoにします。時計の同期、RTCへの書き戻し、日本語localeの追加ではありません。
基準rootfsの `date` はUTCでした。既存の起動bannerにあるJSTはbuild時刻の表記で、実行時timezoneの証拠ではありません。
容量とQEMUの値は[実験記録](../../experiments/2026-11-12-write-inventory.md)に分けます。

## 方式と固定版

| 候補 | 扱いと理由 |
|---|---|
| Buildroot標準のtzdataとlocaltime symlink | 採用。glibcが使う `/etc/localtime` を構築時に設定し、daemonにも適用します。実行時のSD書き込みは追加しません |
| profileで `TZ=JST-9` をexport | 不採用。login shellの環境だけでは、既に起動したdaemonの既定値を設定できません |
| timezone fileの自前配布・独自のpost-build削除 | 不採用。標準recipeで満たせるため、独自の生成・削除手順を追加しません |
| 全世界のtimezone data | 今回は不採用。現在は日本向けの既定値が要件で、未導入だったdataを全地域分追加する必要はありません |

Buildroot固定commitは `8b238854d909c9cce32ef9671d968b03e323b55d`、recipeのtzdataは2026e、host-zicはtzcode 2026bです。
版を更新せず、既存recipeを有効にします。targetはtimezone dataで、zic executableはhostにだけ入ります。
tzdataのLICENSEは原則public domainで、列挙された一部code fileにはBSD条件があります。宣言と収集結果はlegal-infoで確かめ、SBOMの生成を配布条件の確認と扱いません。

取得した[IANAの最新版表示とrelease notes](https://www.iana.org/time-zones/releases/2026f)は2026f（2026-10-27）です。Cuba・Brazilの時刻、leap secondのExpires処理、`MIN_TRANSITION_GAP`のcompile時指定等の変更があり、Tokyoのoffset変更は記載されていません。
今回は依存版を更新せず、固定recipeのposix側Tokyoを使います。2026fのcode変更をglibcの実装に取り込んだとは扱いません。全地域dataやright側のleap second運用が必要になれば、版更新を別に審査します。

## Buildrootの全timezone設定

| option | 既定値・条件 | 今回の採否 |
|---|---|---|
| `BR2_TARGET_TZ_INFO` | 無効。glibcではtzdataをselect | `y`。標準のzoneinfo読込みを使います |
| `BR2_TARGET_TZ_ZONELIST` | `default` は主要地域のsource一式 | `asia`。これはsource file名で、`Asia/Tokyo`というzone名ではありません。Asia以外の全地域は収録しません |
| `BR2_TARGET_LOCALTIME` | `Etc/UTC` | `Asia/Tokyo`。`/etc/localtime`のsymlinkと `/etc/timezone` の文字列を構築時に作ります |
| `BR2_PACKAGE_TZDATA` | 非表示。glibc・muslのTZ_INFOからselect | glibcの現行構成で有効になります。外部overrideやvendor編集は不要です |
| `BR2_PACKAGE_TZ` | uClibc向けの別実装 | 現行のglibcでは選びません |

`asia`の全zone、posix/right両方、共通tab fileはrecipeどおりに残します。Tokyo以外のfileを個別に削る変更はしていません。
従来はtzdata自体が未導入なので、既存の他地域dataを削る変更ではありません。全地域の選択が必要になった時はzonelistと容量を見直します。

## host-zicの引数

固定binaryのhelpに出るoptionを列挙します。製品に新しい実行時commandを追加する表ではありません。

| option | recipe・今回の扱い |
|---|---|
| `--version`、`--help` | hostでの版・設定範囲の採取に使います |
| `-b` | recipeの `fat` を維持。時刻の互換性を容量だけで削りません |
| `-d` | recipeの `_output/posix` と `_output/right`。書き込み先はhostのbuild treeです |
| `-L` | right用に `leapseconds` を渡します。既定localtimeはposix側へのlinkです |
| `-v`、`-D`、`-l`、`-m`、`-p` | recipeは指定しません。診断、directory・既定link、permission等の既定を変更しません |
| `-r`、`-R` | recipeは指定しません。過去・未来の時刻範囲の削減は行いません |
| `-t`、`-u` | recipeは指定しません。独自のlocaltime linkや所有者指定を加えません |

## 実行時と書き込み

glibcは `TZ` 環境変数がなければ `/etc/localtime` を読みます。アプリがTZを明示すれば、そのアプリの選択が優先します。
etc overlayのupperは `/run`、lowerの先頭は `/data/etc` なので、利用者が保存済みのlocaltime設定で既定を隠す場合は別です。今回その設定を削除しません。
新しいdataはSquashFS上にあり、起動時に時計やSDへ保存するdaemonは追加しません。RTC・NTP・時刻の正確さは別の確認事項です。

## 一次資料

- [固定Buildrootのsystem/Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/system/Config.in#L606-L644)
- [tzdata recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/tzdata/tzdata.mk)、[tzdata Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/tzdata/Config.in)、[host-zic recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/zic/zic.mk)
- [IANA timezone database](https://www.iana.org/time-zones)、[zicのmanual](https://data.iana.org/time-zones/tzdb/zic.8.html)
- [glibcのTZ環境変数](https://www.gnu.org/software/libc/manual/html_node/TZ-Variable.html)
