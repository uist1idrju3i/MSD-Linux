# 公式サイトの HTML・CSS

RESEARCH.md から分割した節です。

## 公式サイトの HTML・CSS

公式サイト（https://muromi.moe/ 、ソースは `public_html/`）について、使える HTML・CSS の技術を採否つきで検討しました（2026-10-19）。読む人として、パソコンとスマートフォンに加えて、低スペックの機器（CardputerZero のような 320×170 の画面と遅い CPU）、テキストブラウザー（w3m、lynx）、スクリーンリーダーを想定します。

### 測った結果

測定の条件と生の値は [docs/experiments/2026-10-19-site-render.md](../../docs/experiments/2026-10-19-site-render.md) にあります。GitHub Pages は HTML・CSS・SVG を gzip で送り、Brotli には対応しません。HTML・CSS を minify しても、gzip 後の転送量は数十バイトしか減りません。レンダリング時間も、320×170・CPU 6 倍の条件で誤差（2〜3 ms）を超えて縮みませんでした。時間の大半はレイアウトです。SVG の最適化（svgo）は画素が変わり、CSS のインライン化は CSP にハッシュを足す手間に見合う短縮がありませんでした。`content-visibility: auto` は FCP が 28% 縮みましたが、全体のスクリーンショットが変わり、スクロール中にページの高さも変わるため、採用しません。

### 採用したもの

| 項目 | 内容 |
|---|---|
| カードの見出しと説明を `<h3>`・`<p>` にする | `<strong>`・`<span>` を CSS の `display: block` で分けていたため、w3m と lynx で見出しと説明が1行につながっていました。スクリーンリーダーで見出しを飛び移るときにも使えます。1280×800 の見た目は1画素も変わりません |
| 縦の短い画面で余白を詰める | `@media (max-height: 30em)` で、ロゴのまわりの余白とロゴの幅を小さくします。320×170 の最初の画面に、ロゴと説明文の3行が入ります |

### 以前から入っているもの

`color-scheme` と明暗の `theme-color`、システムフォント、画像の `width`・`height` と `alt`、スキップリンク、`:focus-visible`、ランドマーク（`header`・`main`・`footer`）、`default-src 'none'` から始める CSP、`referrer`。色のコントラストは、明・暗とも WCAG AA（4.5:1）を超えます（最も低いのは暗い表示のカードの上のリンク色で 6.04:1）。強制カラー（Windows のハイコントラスト）でも、文字とロゴが読めます。

### 採用しないもの

| 項目 | 理由 |
|---|---|
| HTML・CSS の minify、svgo、CSS のインライン化、`content-visibility` | 上の測定のとおり |
| `preload`、`fetchpriority`、`loading="lazy"`、`decoding` | 画像はロゴ1枚だけで、最初の画面にあります。先に読ませる対象も、遅らせる対象もありません |
| `prefers-reduced-motion` | 動きのある表現がありません |
| `prefers-reduced-data` | 既定で対応しているブラウザーがありません |
| `manifest` | アプリ（PWA）ではありません |
| SRI | 外部のオリジンから読むものがありません |
| `apple-touch-icon`、`favicon.ico` | PNG・ICO の派生ファイルが増え、二重管理になります |
| 構造化データ（JSON-LD） | 1ページのサイトでは得るものが小さいためです |
| `robots.txt`、`sitemap.xml` | 1ページで、全部を公開してよいため、置かなくても同じ扱いになります |
| `security.txt`（RFC 9116） | `Expires` を1年以内ごとに更新する手間がかかります。連絡先は GitHub のリポジトリから辿れます |
| HTML・CSS の lint を CI に入れる | W3C の Nu Html Checker（26.10.12）ではエラーが 0 件でした。html-validate（11.16.4）は doctype の小文字、Stylelint（17.16.0、標準の設定）は書き方の好み3件を指摘しただけです。CI に入れると Java や npm の依存と、その監視が増えます |
| CSP の `frame-ancestors`、HSTS、キャッシュの調整 | meta の CSP では `frame-ancestors` が効かず、GitHub Pages では応答ヘッダーを付けられません。ほかのサイトへの埋め込みは防げないことを、制約として残します |

### テキストブラウザーの限界

lynx 2.9.0 では、長い段落の行の右端が切れます。w3m 0.5.3 では切れません。lynx 2.9.0dev.10 の `-dump -width=80` の出力で全角文字を2桁と数えると、1行が最大 145 桁になります。lynx が全角文字を1桁と数えて折り返しているためです。サイトの側では直せないため、記録だけにします。
