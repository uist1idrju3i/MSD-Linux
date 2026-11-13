# productionのCloudflare Web AnalyticsとCSP

- 状態: production応答・ローカル描画とCSP検査を実施。実送信は未観測
- 日付: 2026-11-13
- 関連: [サイト調査](../research/presentation/site-html-css.md)

## 目的と採否の基準

利用者は2026-11-13にAnalyticsを継続すると決めました。productionのrootと存在しないpathのHTML・headerを1回ずつ取得し、注入script・`data-cf-beacon`・送信先を記録します。これは性能測定ではなく、取得時点の状態の確認なので5反復は行いません。

結果を見る前の基準は、Cloudflareの一次資料またはproductionの観測で同一origin送信が可能なら、既存の明示RUM URLに`connect-src 'self'`だけを追加することです。注入が見つからない場合は不在の観測として残し、設定OFFとは断定しません。scriptの記述とbrowserが実際に送ったrequestは区別します。ビルド・QEMU・実機性能は対象外です。

## 条件

| 項目 | 値 |
|---|---|
| 基準commit | `e4f3e6e4f7e80dc31508afe73cf28624adeb3f73`と本branchのCSP差分 |
| ホスト | Ubuntu 26.04.1 LTS、x86_64、Python 3.14.4 |
| ツール | curl 8.18.0、Google Chrome 157.0.8103.78、Playwright 1.64.1、w3m 0.5.3+git20230121、Lynx 2.9.2 |
| 取得時刻 | curlは2026-11-13 11:14 UTCから。各応答とbrowserの時刻は`production/fetch.json`と`browser.json` |
| 変える条件 | productionのrootと不存在path、curlとheadless browser。ローカルは変更前後のCSP |
| 固定条件 | 同じVM・browser版。ローカルのHTMLはmetaのconnect-srcだけを変更し、CSS・画像は不変 |
| 反復と集計 | 各clientで各URL 1回。描画は後述の条件各1回。性能の中央値・最小最大は算出しない |
| build・cache | buildなし。既存build出力やccacheを比較しない。HTTP cacheやedgeは固定せず、headerを保存 |
| 入力とbinary | siteの前後の写し、script、ツール実体のSHA-256はarchiveと`production/tools.json`。全memberのhashは同名CSV |

## 一次資料

Cloudflareの[FAQ・proxy時の送信先](https://developers.cloudflare.com/web-analytics/faq/#i-am-proxying-my-site-through-cloudflare-should-i-manually-add-the-js-beacon)は、自動setupなら自domainの`/cdn-cgi/rum`、手動snippetなら`cloudflareinsights.com/cdn-cgi/rum`と説明しています。[CSPの節](https://developers.cloudflare.com/web-analytics/faq/#what-do-i-need-to-add-to-my-content-security-policy-csp)は自動注入で`connect-src 'self'`が必要と明記しています。[導入手順](https://developers.cloudflare.com/web-analytics/get-started/)も取得しました。

FAQのscript例は`https://static.cloudflareinsights.com/beacon.min.js`、属性は`data-cf-beacon='{"token": "$SITE_TOKEN"}'`です。これは一次資料の例であって、このsiteで観測したsrcやtokenではありません。公式のendpointはPOST用ですが、今回は人工の測定payloadをproductionへ送っていません。

## 手順と計測器の照合

取得は次のURLごとに別名で実行しました。`--fail`は付けず、意図した404も本文とheaderを保存します。

```sh
curl --silent --show-error --location --max-time 60 \
  --dump-header index.headers --output index.html \
  --write-out '%{http_code} %{url_effective}' https://muromi.moe/
curl --silent --show-error --location --max-time 60 \
  --dump-header 404.headers --output 404.html \
  --write-out '%{http_code} %{url_effective}' \
  https://muromi.moe/__msd-analytics-probe-20261113-not-found
```

archiveの`observe-production.py`はPlaywrightで両URLをloadし、network idle後のscript属性、応答本文とheader、request・consoleを保存します。最後に`about:blank`へ離脱しました。既存の出力は上書きせず、再試行ではscriptと`production/`の保存先を新しいrun directoryへコピーして実行します。

`review-site.py`はローカルの前後を別portで配信し、次を照合しました。

- index・404それぞれでw3m 40／80桁、lynx 80桁を出力。6組の前後byte列が一致しました。見出しと本文は別行で、indexの先頭は「本文へ移動」です。404は単純な見出しと戻るlinkで、skip linkは元からありません。
- 320×170の明暗は最初と全体、800×360の明暗は最初、1280×800の明暗は全体、320×170の強制カラーは最初を撮影。両page合計18組がbyte一致し、画素差は0です。
- 変更後18枚を目視し、320幅の全体画像は6枚の等倍cropでも読みました。文字の重なりや横方向の欠けは見つかりませんでした。170高さでは見出しや本文が下へ続くため、縦scrollが必要です。変更前18枚はbyte一致で照合し、別途の目視はしていません。
- 同じbrowserで`fetch('site.css')`を実行。変更前の両pageはTypeError、変更後はHTTP 200で、同一origin接続の許可が実際に変わることを確認しました。通常のCSS表示はstyle-srcで許可されるため、connect-srcによるfetchとは区別します。

色・CSS・速度を変更する試験ではないため、contrast比やCPU抑制下の速度は再測定していません。ローカル配信はmeta CSPの検査です。HTTP CSPとの一致は`check-site.py`とその回帰testで調べ、ローカル配信をCloudflareの配信成功とは扱いません。

## 結果

| client・page | HTTP | script要素 | data-cf-beacon | RUM送信 |
|---|---:|---:|---|---|
| curl・root | 200 | 0 | なし | curlでは実行しない |
| curl・不存在path | 404 | 0 | なし | curlでは実行しない |
| headless Chrome・root | 200 | 0 | なし | 観測なし |
| headless Chrome・不存在path | 404 | 0 | なし | 観測なし |

curlのroot HTMLはSHA-256 `51ee6747e7d757a48aeaff7fa34c9f76c27a4f2b43da6aaa8f2cf3767070620d`、404 HTMLは`66e5c5a3a1968698619b459a0b568c6abcd1422d1ff9f61c6f16dfcab0557e4d`です。headerとbrowser本文のhashも[CSV](2026-11-13-cloudflare-analytics.csv)へ保存しました。取得時のHTTPとmetaのCSPには同一originの接続許可がありませんでした。

**実際の注入script src・設定属性・送信先は、今回の観測では特定できません。** Web Analyticsの有効設定、全訪問者への注入、Analytics dashboardへの到達も、この不在の観測だけでは判定しません。公式資料上の自動注入が同一originへ送るため、利用者の条件に従ってCSPへselfを追加しました。selfは同一origin全体の許可で、特定pathだけの許可ではありません。新CSPのproduction配信は未確認です。

## 失敗・制限

推測した公式URL`/web-analytics/data-metrics/beacon/`は404でした。この応答を一次資料の説明には使わず、取得成功したFAQと導入手順を使いました。失敗した応答もarchiveとCSVへ残しています。

hostの標準PythonにはPlaywrightがなかったため、blueprintの指定版1.64.1を専用venvへ入れ、既存のChromeを使いました。ImageMagickはなかったため、比較はPNGのbyte一致、等倍cropはbrowser canvasのpixel copyを使いました。計測中のscriptの書き換えや失敗行の削除はしていません。

初回metadataではw3mの版をstderrから取って空欄になったため、stdoutの実値を追記しました。描画やbyte比較の結果は変更していません。

実機CardputerZero、他のbrowser・UA・国・edge・cache条件、注入不在の原因、実際のRUM ingestion、公開後の新CSP、DNSSEC・CAA・DMARC・`pages.dev` redirectは未確認です。新しいbuild・QEMU試験もしていません。

## 生データと保存照合

[data枝の固定commit](https://github.com/uist1idrju3i/MSD-Linux/tree/d0024e3b7e5b4a0afff559fe41ab3fa3688fedf2/session-2026-11-13/evidence)へ通常pushし、remote SHAを照合しました。`decisions-analytics.tar.gz`は7,255,033 bytes、SHA-256は`9edbd1536dc2033f3b9edf61578e0ff488c8aabf6d95004953c4bf369ceaf3db`です。

全101 memberを原本のbyte列と照合しました。`production/`にはHTML・header・Cloudflare資料・browser JSONと版情報、`site/`には前後のsite写し・text・画像・crop・結果JSONがあります。観測・描画scriptとlog、251 binaryの削除前採取・限定削除の補助scriptも監査用に含めました。削除したbinary本文を含むものではなく、削除を再実行する指示でもありません。

```sh
git fetch origin data/fs-compare-experiments
git show d0024e3b7e5b4a0afff559fe41ab3fa3688fedf2:session-2026-11-13/evidence/decisions-analytics.tar.gz > decisions-analytics.tar.gz
sha256sum decisions-analytics.tar.gz
tar -tzf decisions-analytics.tar.gz
tar -xOf decisions-analytics.tar.gz production/index.headers
```
