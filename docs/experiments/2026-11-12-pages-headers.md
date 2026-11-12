# Cloudflare Pages のヘッダー確認

## 目的と条件

基準は`d7d9d622eae2f5f78dc0b891203f3641f334123b`です。HTML本文・CSS・画像は変えず、`_headers`とHTMLのmeta CSPだけを変えます。性能測定ではなく、各条件1回を1組とする静的・描画比較です。採用条件は、既存の本文・ローカル資源の描画が変わらないこと、承認したbeacon以外のCSP許可を増やさないこと、preview以外へnoindexを足さないことです。

`site-review`の手順でindex・404を、w3mの40・80桁とlynxの80桁で比較します。Chromiumでは320×170の明暗（先頭・全体）、800×360の明暗（先頭）、1280×800の明暗（全体）、320×170の強制カラー（先頭）を比較します。画素差は0を条件とし、目でも確認します。比較器は同じ画像のA/Aと、既知の1画素変更で検査します。

## 公開応答と一次資料

2026-11-12の`curl -sI https://muromi.moe/`では、`X-Content-Type-Options: nosniff`、`Referrer-Policy: strict-origin-when-cross-origin`、HSTSがありました。今回追加するCSP、Permissions-Policy、X-Frame-Options、COOPはありませんでした。既存の3ヘッダーは重ねて指定しません。

通常UA・Chrome形式UA・query付きのcurlと既存previewでは、HTMLにscript要素がありませんでした。取得先edgeはCDGですが、地域・設定・UAなどのどれが原因かは未確認です。依頼時に観測された注入snippet、nonce/hash、実際の送信は、この取得では再現できていません。

取得した4応答のHTMLは、基準commitの`index.html`と同じSHA-256でした。script要素がない応答を、beacon動作の証拠とは扱いません。各入力と取得資料のhashはCSVに残します。

[公式FAQ](https://developers.cloudflare.com/web-analytics/faq/)は、自動注入のconnect先を同一origin、手動埋め込みを`cloudflareinsights.com`と説明しています。取得した[beacon](https://static.cloudflareinsights.com/beacon.min.js)にも、同一originの`/cdn-cgi/rum`と、`https://cloudflareinsights.com/cdn-cgi/rum`の分岐がありました。稼働中の分岐を推測せず、利用者が承認した外部endpointだけをCSPに許可します。

公式の注入方式は[Web Analyticsの設定](https://developers.cloudflare.com/web-analytics/get-started/)も参照します。FAQの埋め込み例は、外部の`script type="module"`と`data-cf-beacon`のJSON属性です。この属性はそれ自体がinline scriptではありません。FAQは自動注入にSRIの`integrity`属性を加えるとも説明しますが、これはCSPのnonce/hashとは別です。現在の実snippetを取得できていないため、その属性やSRIが実サイトにあるとは断定しません。`unsafe-inline`・nonce・CSP hashは追加しません。

[Pages公式資料](https://developers.cloudflare.com/pages/configuration/headers/)に従い、project domainとversion・branch previewの2種類を別ruleにします。custom domainへ`X-Robots-Tag`を加える全体ruleは置きません。

資源は2 HTML、1 CSS、8画像（SVG 7・WebP 1）です。inline style・script・外部font・`data:` URIはなく、CSSの画像参照はローカルです。全SVGも調べ、外部参照・style属性・script要素がないことを確認しました。`url(#...)`はSVG内の参照で、外部通信ではありません。

## 再現方法と結果

`python3 .github/scripts/check-site.py`と`tests/check-site/run.sh`で、metaと応答CSPの両方、Pagesのrule、script要素の禁止を確認します。描画はPythonの静的HTTP serverで変更前後を配信し、ChromeをPlaywrightから起動します。ローカルserverは`_headers`を解釈しないため、描画が同じでもHTTPの制約が配信された証拠にはなりません。

再現にはw3m、lynx、Chromeと、Playwright 1.65.1・Pillow 13.0.0を入れたPythonが必要です。そのPythonを`SITE_PYTHON`へ指定し、リポジトリのrootで実行します。変更後の入力は、この記録と同じcommitの`public_html/`です。出力先は存在しない名前にします。

```sh
mkdir -p output-pages-headers
"$SITE_PYTHON" docs/experiments/2026-11-12-pages-headers.py \
  --baseline d7d9d622eae2f5f78dc0b891203f3641f334123b \
  --browser google-chrome --output output-pages-headers/replay
```

検査環境はLinux 7.0.0-43-generic、Python 3.14.4、Chrome 157.0.8103.78です。w3mとlynxを含む版と生の比較値は[CSV](2026-11-12-pages-headers.csv)へ記録しました。scriptはテキスト出力、全スクリーンショット、CSV、SHA256SUMSを出力します。

追跡するCSVは改行をLFへ揃え、変更前の元CSVのSHA-256も併記しました。公開応答と一次資料は次の方法で再取得できますが、将来も同じ内容が返るとは限りません。

```sh
curl -fsSI https://muromi.moe/
curl -fsSL https://muromi.moe/ -o output-pages-headers/live-index.html
curl -fsSL https://developers.cloudflare.com/web-analytics/faq/index.md \
  -o output-pages-headers/analytics-faq.md
curl -fsSL https://developers.cloudflare.com/pages/configuration/headers/index.md \
  -o output-pages-headers/headers-doc.md
curl -fsSL https://static.cloudflareinsights.com/beacon.min.js \
  -o output-pages-headers/beacon.min.js
```

| 検査 | 結果 |
|---|---|
| w3m 40・80桁、lynx 80桁の変更前後6対 | 出力差0。見出し・本文・リンクの読み順を確認 |
| 2ページの変更前後18対、計36画像 | 全条件で画素差0。先頭・全体を明暗で目視し、文字の重なりや画像の欠落なし |
| 320×170の強制カラー | 文字とロゴを判読でき、変更前後の画素差0 |
| 比較器の対照 | A/Aの差0、既知の1画素変更の差1 |
| check-siteと回帰suite | 成功。両metaと応答CSPの拡張、欠落・空・不正なPages rule、重複を拒否 |
| 実配信のヘッダー・Analyticsの実送信 | push後のpreview確認が必要。ローカル比較では未確認 |

初回の描画scriptは、Playwrightの停止後にbrowserを閉じる順序になり、`Event loop is closed! Is Playwright already stopped?`で失敗しました。終了順を直し、HTML・CSS・画像を変えずに全条件を取り直しました。回帰suiteの初回もfixture補助関数のshell変数が対象pathを上書きして失敗したため、試験側の変数名を分けて再実行しました。失敗した試行を成功の比較値に含めていません。

Cloudflareへの実配信、注入されたbeaconの動作、実機は未確認です。同一originへ送る自動注入だった場合は、このCSPで通信が止まる可能性が残ります。承認済みの外部endpoint以外を推測で許可せず、実snippetの再取得とtest環境での確認を必要な作業として残します。
