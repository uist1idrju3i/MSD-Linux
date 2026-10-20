# サイトの minify・SVG 最適化・CSS のインライン化・content-visibility とレンダリング時間

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin
- 関連: [公式サイト調査](../research/site-html-css.md)

## 目的と仮説

GitHub Pages は HTML・CSS・SVG を gzip で送るので、minify しても転送量はほとんど減りません。そこで、低スペックの機器での表示を想定して、レンダリング時間（FCP、処理時間、レイアウト、スタイル計算）が変わるかを測ります。仮説は「minify で DOM の節点は減るが、時間は誤差の範囲でしか変わらない」です。

## 採否の基準（結果を見る前に書く）

正式な測定の前に、次の基準を決めました。

1. 主条件（320×170、CPU 6 倍の遅さ、明るい表示）で、FCP か処理時間（CDP の `TaskDuration`）の中央値が、いまの版より 10% 以上、かつ A/A の差の 3 倍以上縮む。A/A の差は、同じファイルを別のポートで配った版（`aa`）と、いまの版（`orig`）の中央値の差とする。
2. 320×170 と 1280×800、明・暗の全体のスクリーンショットが、いまの版と1画素も変わらない（ImageMagick の `compare -metric AE` が 0）。
3. ほかの条件（1280×800、CPU の遅さなし）や指標（DOMContentLoaded、load）が 10% 以上悪化しない。

1〜3 をすべて満たさない版は採用しません。CSS のインライン化は CSP にハッシュを足す必要があり、その手間も費用として数えます。`content-visibility` の版は、正式な測定のあとで追加しました。基準は同じものを、測る前に書き足しました。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `3f92638` |
| ホスト | Ubuntu 22.04.5 LTS、x86_64、Linux 6.8.0-1061-aws |
| ブラウザー | Chromium headless shell 156.0.8078.4（Playwright 1.64.0 の同梱版） |
| 使ったツールの版 | Node.js 24.21.0、`playwright-core` 1.64.0、`html-minifier-terser` 7.2.0、`clean-css` 5.3.3、`svgo` 4.1.0、ImageMagick 6.9.11-60 |
| 配信 | `python3 -m http.server`。版ごとに別のポート |
| 版 | `orig`（いまの `public_html/`）、`aa`（`orig` と同じファイル）、`min`（HTML・CSS を minify）、`svgo`（SVG を最適化）、`inlinecss`（`site.css` を `<style>` に入れ、CSP にハッシュを追加）、`cv`（`orig` に `content-visibility` を追加） |
| 画面 | 320×170、1280×800 |
| CPU | `Emulation.setCPUThrottlingRate` で 1 倍と 6 倍（`cv` の測定は 6 倍のみ） |
| キャッシュ | `Network.setCacheDisabled` で無効 |
| 繰り返し | 各条件 30 回。版の順番は回ごとにずらす |
| 生の値 | [2026-10-19-site-render.csv](2026-10-19-site-render.csv)（`cv` 以外）、[2026-10-19-site-render-cv.csv](2026-10-19-site-render-cv.csv)（`cv`） |

## 手順

1. 基準の commit の `public_html/` を `v-orig/` と `v-aa/` と `v-svgo/` に写し、`v-min/` と `v-inlinecss/` を作る。`v-cv/` は `v-orig/` を写し、`site.css` の末尾に次を足す。

   ```css
   main > section {
     content-visibility: auto;
     contain-intrinsic-size: auto 40rem;
   }
   ```

2. 次のスクリプトで `min`、`svgo`、`inlinecss` を作る。

   ```js
   import fs from 'node:fs'; import crypto from 'node:crypto';
   import { minify } from 'html-minifier-terser'; import CleanCSS from 'clean-css'; import { optimize } from 'svgo';
   const htmlOpts = { collapseWhitespace: true, removeComments: true, collapseBooleanAttributes: true, decodeEntities: false, removeAttributeQuotes: false };
   for (const f of ['index.html','404.html']) fs.writeFileSync(`v-min/${f}`, await minify(fs.readFileSync(`v-orig/${f}`,'utf8'), htmlOpts));
   const css = new CleanCSS({ level: 1 }).minify(fs.readFileSync('v-orig/site.css','utf8'));
   if (css.errors.length) throw new Error(css.errors.join());
   fs.writeFileSync('v-min/site.css', css.styles);
   for (const f of fs.readdirSync('v-svgo/images').filter(f=>f.endsWith('.svg'))) {
     const p=`v-svgo/images/${f}`; fs.writeFileSync(p, optimize(fs.readFileSync(p,'utf8'), { path: p, multipass: true }).data);
   }
   const raw = fs.readFileSync('v-orig/site.css','utf8');
   const hash = crypto.createHash('sha256').update(raw).digest('base64');
   let html = fs.readFileSync('v-orig/index.html','utf8');
   const link = '<link rel="stylesheet" href="site.css">'; const csp = "style-src 'self'";
   if (!html.includes(link) || !html.includes(csp)) throw new Error('needle missing');
   html = html.replace(link, `<style>${raw}</style>`).replace(csp, `style-src 'self' 'sha256-${hash}'`);
   fs.writeFileSync('v-inlinecss/index.html', html);
   ```

3. 版ごとに `python3 -m http.server -d v-<版> <ポート>` を動かす（`orig` 8811、`aa` 8812、`min` 8813、`svgo` 8814、`inlinecss` 8815、`cv` 8816）。
4. 次のスクリプトを `N=30` で動かす。`cv` の測定では、`variants` を `orig`・`aa`・`cv` に、`throttles` を `[6]` にする。

   ```js
   import { chromium } from 'playwright-core';
   import fs from 'node:fs';
   const variants = { orig: 'http://127.0.0.1:8811/', aa: 'http://127.0.0.1:8812/', min: 'http://127.0.0.1:8813/', svgo: 'http://127.0.0.1:8814/', inlinecss: 'http://127.0.0.1:8815/' };
   const viewports = [[320,170],[1280,800]];
   const throttles = [1,6];
   const N = +(process.env.N || 20);
   const out = ['variant,viewport,throttle,run,fcp_ms,dcl_ms,load_ms,task_ms,layout_ms,recalc_style_ms,script_ms,nodes,layout_count,recalc_count'];
   const browser = await chromium.launch({ executablePath: process.env.CHROME });
   for (const [w,h] of viewports) for (const t of throttles) for (let r=0; r<N; r++) {
     const base = Object.keys(variants); const order = base.map((_,i)=>base[(i+r)%base.length]);
     for (const v of order) {
       const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: 'light' });
       const page = await ctx.newPage();
       const cdp = await ctx.newCDPSession(page);
       await cdp.send('Network.enable'); await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
       await cdp.send('Performance.enable');
       await cdp.send('Emulation.setCPUThrottlingRate', { rate: t });
       await page.goto(variants[v], { waitUntil: 'load' });
       await page.waitForTimeout(300);
       const nav = await page.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; const p = performance.getEntriesByName('first-contentful-paint')[0]; return { fcp: p ? p.startTime : -1, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd }; });
       const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x => [x.name, x.value]));
       out.push([v, `${w}x${h}`, t, r, nav.fcp.toFixed(2), nav.dcl.toFixed(2), nav.load.toFixed(2), (m.TaskDuration*1000).toFixed(2), (m.LayoutDuration*1000).toFixed(2), (m.RecalcStyleDuration*1000).toFixed(2), (m.ScriptDuration*1000).toFixed(2), m.Nodes, m.LayoutCount, m.RecalcStyleCount].join(','));
       await ctx.close();
     }
   }
   console.log(`browser=${browser.version()}`);
   await browser.close();
   fs.writeFileSync(process.env.OUT || 'raw.csv', out.join('\n') + '\n');
   ```

5. 320×170 と 1280×800、明・暗で、各版の `index.html` と `404.html` の全体のスクリーンショット（Playwright の `fullPage: true`、読み込み後 300 ms 待つ）を撮り、`compare -metric AE` で `orig` と比べる。

## 計測器の検証

- A/A（`orig` と `aa`）の中央値の差は、主条件で FCP 2 ms、処理時間 3.0 ms でした。`cv` の測定では 2 ms と 1.8 ms です。
- load の中央値は、主条件の A/A でも 89.4 ms と 228.8 ms に分かれました。load は回によって 70 ms 前後と 230 ms 前後の二つの山に分かれるため、load の差は採否に使える精度がありません。
- `svgo` の 1280×800・6 倍の 15 回目は、FCP が記録されませんでした（CSV では `-1.00`）。中央値はこの行を含めた値です。

## 結果

30 回の中央値（ms）。DOM の節点の数は1回目の値です。括弧内は最小〜最大です。

| 画面 | CPU | 版 | FCP | 処理時間 | レイアウト | スタイル計算 | DCL | load | 節点 |
|---|---|---|---|---|---|---|---|---|---|
| 320×170 | 6 倍 | orig | 258.0（160〜324） | 247.7（222.8〜295.7） | 149.7 | 7.6 | 63.0 | 89.4 | 451 |
| 320×170 | 6 倍 | aa | 260.0 | 250.7 | 146.1 | 8.4 | 64.7 | 228.8 | 451 |
| 320×170 | 6 倍 | min | 258.0 | 253.7 | 147.3 | 6.9 | 62.0 | 87.4 | 355 |
| 320×170 | 6 倍 | svgo | 268.0 | 253.4 | 144.7 | 8.6 | 69.9 | 92.3 | 440 |
| 320×170 | 6 倍 | inlinecss | 256.0 | 249.0 | 153.1 | 7.4 | 61.6 | 236.4 | 452 |
| 1280×800 | 6 倍 | orig | 260.0 | 245.2 | 146.1 | 7.1 | 62.4 | 87.8 | 451 |
| 1280×800 | 6 倍 | aa | 258.0 | 248.7 | 146.1 | 7.5 | 63.4 | 90.2 | 451 |
| 1280×800 | 6 倍 | min | 264.0 | 248.8 | 149.0 | 6.3 | 64.1 | 85.5 | 355 |
| 1280×800 | 6 倍 | svgo | 264.0 | 249.0 | 150.2 | 8.3 | 63.6 | 89.7 | 440 |
| 1280×800 | 6 倍 | inlinecss | 256.0 | 242.5 | 147.0 | 6.5 | 63.6 | 153.2 | 452 |
| 320×170 | 1 倍 | orig | 52.0 | 47.7 | 26.0 | 1.0 | 15.0 | 47.9 | 451 |
| 320×170 | 1 倍 | aa | 48.0 | 42.2 | 22.7 | 1.0 | 13.1 | 45.7 | 451 |
| 320×170 | 1 倍 | min | 46.0 | 41.4 | 23.1 | 1.1 | 11.3 | 44.0 | 355 |
| 320×170 | 1 倍 | svgo | 46.0 | 41.1 | 23.0 | 1.0 | 11.6 | 40.6 | 440 |
| 320×170 | 1 倍 | inlinecss | 46.0 | 39.6 | 21.8 | 1.0 | 11.4 | 40.2 | 452 |
| 1280×800 | 1 倍 | orig | 48.0 | 38.3 | 20.9 | 1.2 | 10.1 | 39.9 | 451 |
| 1280×800 | 1 倍 | aa | 48.0 | 39.8 | 21.3 | 1.0 | 10.1 | 39.6 | 457 |
| 1280×800 | 1 倍 | min | 48.0 | 39.2 | 21.7 | 1.0 | 10.2 | 38.8 | 361 |
| 1280×800 | 1 倍 | svgo | 48.0 | 39.2 | 21.6 | 0.9 | 9.4 | 39.1 | 440 |
| 1280×800 | 1 倍 | inlinecss | 48.0 | 37.1 | 20.6 | 1.1 | 9.6 | 37.2 | 452 |

次の表は `content-visibility` の測定です（CPU 6 倍、30 回の中央値、ms）。

| 画面 | 版 | FCP | 処理時間 | レイアウト | スタイル計算 | DCL | load |
|---|---|---|---|---|---|---|---|
| 320×170 | orig | 254.0 | 243.6 | 150.7 | 5.9 | 60.8 | 83.3 |
| 320×170 | aa | 252.0 | 245.4 | 149.4 | 6.2 | 60.3 | 87.6 |
| 320×170 | cv | 182.0 | 186.2 | 89.7 | 6.4 | 63.0 | 86.6 |
| 1280×800 | orig | 258.0 | 241.6 | 148.0 | 5.9 | 65.8 | 89.7 |
| 1280×800 | aa | 256.0 | 243.2 | 148.7 | 6.6 | 62.7 | 84.2 |
| 1280×800 | cv | 206.0 | 244.1 | 141.7 | 6.6 | 60.2 | 141.0 |

次の表は、スクリーンショットの `orig` との差（画素の数）です。

| 版 | 320×170 明 | 320×170 暗 | 1280×800 明 | 1280×800 暗 | 404 |
|---|---|---|---|---|---|
| min | 0 | 0 | 0 | 0 | 0 |
| inlinecss | 0 | 0 | 0 | 0 | 0 |
| svgo | 314 | 304 | 511 | 501 | 未記録 |
| cv | 151,349 | 151,040 | 301,878 | 301,295 | 0 |

`cv` の全体のスクリーンショットは、ページの高さが変わりました（320×170 で 5,472 px から 4,484 px、1280×800 で 3,338 px から 3,663 px）。320×170 では「開発の状況」から「文書とリンク」までの節が描かれず、1280×800 では「文書とリンク」が描かれませんでした。

## 結論

- **minify は採用しません。** 節点は 451 から 355 に減りましたが、主条件の FCP は 258 ms のまま、処理時間は 247.7 ms から 253.7 ms で、A/A の差の範囲です。時間の大半はレイアウト（約 147 ms）で、空白の文字は効いていません。
- **svgo は採用しません。** 時間は縮まず、画素が 304〜511 個変わります。
- **CSS のインライン化は採用しません。** 主条件の FCP は 2 ms、処理時間は 1.3 ms 縮んだだけで、基準の 10% に届きません。CSP のハッシュを CSS の変更ごとに直す手間が増えます。
- **`content-visibility: auto` は採用しません。** 320×170 では FCP が 28%、処理時間が 24% 縮み、基準 1 は満たします。しかし、全体のスクリーンショットが変わり（基準 2）、1280×800 の load が 89.7 ms から 141.0 ms に悪化しました（基準 3）。

## 捨てた試行と経緯

- `lightningcss-cli` は、最初は実行ファイルが壊れていて動きませんでした（`This: not found`）。`npm rebuild` のあとは動きましたが、版の表示が想定と違う `1.0.0-alpha.72` だったため、CSS の minify には `clean-css` を使いました。
- 正式な測定の前に、試しに測った回があります。その値は見ないまま捨て、採否の基準を書いてから正式に測りました。

## 未確認の点

- CPU の遅さはエミュレーションです。CardputerZero の実機と、実機で動くブラウザーでは試していません。
- `cv` のスクリーンショットで節が描かれなかったのは、全体を1枚に撮るときの描き方による可能性があります。利用者がスクロールしたときに節が欠けるかは確かめていません。ただし、`contain-intrinsic-size` の見積もりと実際の高さが違うので、スクロール中にページの高さが変わることは避けられません。
- 1280×800・6 倍の load の悪化は、上の「計測器の検証」のとおり load の精度が低いため、確かな差とは言えません。基準 2 だけでも不採用は変わりません。
