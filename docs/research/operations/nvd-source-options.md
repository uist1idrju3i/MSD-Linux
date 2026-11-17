# NVD取得元と取得方式の比較

[調査の索引](../../../RESEARCH.md) / [CIの現行手順](../../CI.md)

2026-11-17の先行調査と、同日の利用者承認に基づく採否です。製品上ではなくCIで使います。既存のBuildroot consumerと同じCPE照合・NVD評価を保つこと、匿名で取得できること、base/headを同じ入力で比較できることを条件にしました。

## 観測した事実

先行調査の16:40〜16:45 UTCごろ、fkie default branchは`2ea002cc3b166ddbd3dfaf54371d7e6729fac92a`、committer時刻は11/13 03:23:31 UTCでした。一方、NVD APIの直近6時間検索は494件で、取得範囲の最大`lastModified`は11/17 16:37:19.907でした。NVD全体の最大値を証明したものではありません。

公式`modified`は10,976件で、gzip 6,134,172 byte、展開後73,428,153 byteでした。展開後SHA-256はmetaと一致しました。2002年feedも取得・hash照合し、6,771件に1999〜2002年のIDがあることを確認しました。1999年feedのmetaは404でした。後の[全bootstrap](../../experiments/2026-11-17-nvd-official-feed.md)は別時刻の入力であり、値を混ぜません。

同じ調査ではcvelistV5、CISA vulnrichment、GitHub Advisory Databaseのdefault branch更新と、直近GHSAのOSV公開を観測しました。完全性・NVDとの同等性を検証したという意味ではありません。

## source optionと採否

費用・適合性の評価は、観測と一次資料に基づく推論です。

| option | schema・評価範囲 | 認証・整合性・固定方法 | 費用と失敗時の性質 | MSD/Linuxの採否 |
|---|---|---|---|---|
| NVD API 2.0 | 現行が読むCVE objectと互換。CPE、NVD metricsを保持 | 匿名5回/30秒、keyあり50回/30秒。TLS。応答を保存してhash化する必要あり | 最大2,000件/page、日付窓120日。約42.5万件なら約213 page、6秒間隔だけで約21分。page途中の更新と中断への対策が必要 | 不採用。API keyを追加せず、fallbackにも使わない |
| NVD公式JSON 2.0年別＋modified | `vulnerabilities[].cve`を取り出せば現行と互換 | key不要。TLSと同じ配信元のmetaによるサイズ・SHA-256照合。独立した署名ではない | 年別bootstrapは重いが、通常は差分feed一つ。metaと本体の更新競合・長期停止では失敗または再構築が必要 | 採用。内容hashでsnapshotを固定し、7日以上のcacheを再構築 |
| fkie mirror | 既存配置と互換 | Git commitを固定できるが、今回停止を観測 | clone時刻はデータの新しさを示さない。mirror側の更新にも依存 | 依存を除去 |
| CVEProject/cvelistV5 | CVE Record Format 5.x。CNA/ADP由来でNVDのCPE・CVSSと同等ではない | 公開Git、commit固定。GitHub REST利用時は匿名60回/時 | schema変換だけでなく判定方式・coverageの見直しが必要 | 代替しない。自動切替なし |
| OSV.dev / GitHub Advisory DB | ecosystem、package、version range中心。NVD CPE照合と非互換 | 公開API・Git。OSV公式APIは調査時点でrate limitなし、HTTP/1.1応答上限32 MiB | Buildroot全体とのcoverage同等性は未確認。OSVにはNVD由来の変換情報もある | 代替しない。別の監視方式を設計する場合の候補 |
| CISA vulnrichment等 | CVE 5.xのADP補完。NVD全件mirrorではない | 公開Git、commit固定 | SSVCや一部CVSS等の補完には有用。NVD全件・CPEの代用ではない | 補完候補にとどめる。他mirrorの網羅比較は未実施 |

NVD公式説明では、年別feedは日次、recent/modifiedは約2時間ごと、差分窓は過去8日です。`recent`だけでは古いCVEの修正を拾えないため使いません。年別の古いmetaを一律24時間で拒否せず、modifiedと検証済み同期の鮮度を分けます。時刻だけでデータの完全性を証明したことにはしません。

## 実装の設定

取得器はPython標準ライブラリだけで動き、build時optionや追加依存はありません。API・別sourceを選ぶoptionは公開しません。

| option・設定 | 意味・既定値 | 採用理由 |
|---|---|---|
| `--nvd-path` | 必須。atomicに差し替えるsnapshot symlinkの場所 | `git/`以下を変えずにBuildrootへ渡す |
| `--github-output` | 任意。snapshot IDと同期時刻を追記するfile。既定は出力なし | cacheの不変keyへ渡す。CI用tokenやsecretは不要 |
| source URL・年度 | 公式JSON 2.0、2002年から実行時のUTC現在年まで。固定 | 2002年feedに初期年度分が含まれる。保存年度はCVE IDから決める |
| 差分継続の上限 | 7日未満。超過は年別から再構築 | 公式8日窓に余裕を設ける |
| 鮮度の上限 | 検証済み同期とmodified metaの両方が24時間以内。未来は300秒まで | 閾値を緩めず、古いデータを0件と扱わない |
| download境界 | 1応答最大256 MiB、JSON最大1 GiB、通信timeout 120秒 | 異常な入力を無制限に読まない。超過時は監視不能 |

`fetch-nvd.py --help`の公開optionは`-h`/`--help`、`--nvd-path`、`--github-output`です。表と照合しました。NVD API等の全optionを実装したという意味ではありません。

snapshotは内容hashで識別し、manifestにmeta・取得開始・同期完了・件数を保存します。取得失敗時は前回の公開先を維持してもjobは失敗します。古いcacheやOSVで成功に置き換えません。cacheは保存期間や存続を保証しないため、過去入力を確実に再現したい運用ではsnapshot全体を別途保持する必要があります。

## 一次資料と未確認

- [NVD feed案内](https://nvd.nist.gov/vuln/data-feeds)、[modified meta](https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-modified.meta)
- [NVD CVE API](https://nvd.nist.gov/developers/vulnerabilities)、[利用指針](https://nvd.nist.gov/developers/start-here)
- [NVD API schema](https://csrc.nist.gov/schema/nvd/api/2.0/cve_api_json_2.0.schema)
- [CVEProject](https://github.com/CVEProject/cvelistV5#readme)、[CISA](https://github.com/cisagov/vulnrichment#readme)
- [OSV API](https://google.github.io/osv.dev/api/)、[データ源](https://google.github.io/osv.dev/data/)、[GitHub Advisory Database](https://github.com/github/advisory-database#readme)
- [GitHub REST制限](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

先行調査ではNVD案内が403またはSPA shellになり、公式frontend bundleの説明本文と実feed/schemaを照合しました。全sourceのlicense比較、全API pagination、CI上のcache save/restore、長期間の上流障害、転送中の更新競合を伴う実試験は未確認です。今回の実装はBuildrootの既存consumerを使い、`vendor/`を変更しません。
