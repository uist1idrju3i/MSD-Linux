# Release payloadの公開と匿名取得

[自己更新の設計](README.md) / [実装の比較](implementations.md) / [信頼と復旧](trust-and-state.md)

## Releaseとmetadataを別に扱う

GitHubのimmutable Releaseは、公開後のasset・tagの変更を防ぐ配布側の境界です。端末のTUF root、metadata署名、OS版の認可、A/B復旧を代替しません。期限付きmetadataを同じimmutable Releaseで上書きし続ける設計にはしません。[Release保護の調査](../release-security.md)と役割を分けます。

| 構成案 | 利点 | 費用・不足 | 評価 |
|---|---|---|---|
| 全てをRelease内へ置く | 配布物を一まとまりで参照できる | 変更不能なassetでtimestampの定期再署名を続けられない。新Releaseを探すために別の安全な発見手段が必要 | 最初の構成にはしない |
| 更新可能なTUF repositoryからRelease payloadを直接参照 | payloadのlength/hashをTUF targetとして扱える。大きなfileをgitへ入れない | 各libraryのbase URL・consistent snapshot・hash付き名と、Release asset URLの対応を統合する必要がある | 比較候補 |
| TUF targetを小さなOS descriptorにし、そこからRelease payloadを取得 | metadata側は小さく、Releaseは不変のまま。tuf-on-ciの小さなtarget管理を使う余地がある | descriptor schemaと二段階検証、payload署名・URL認可・publisher改修が増える。上流templateの無改造対応は未確認 | 最初の実験で比較する案 |
| 独自の署名付きJSON catalogだけを使う | 配信構成は小さい | root更新、threshold、expiry、世代混在、委任、長期offline復帰を独自に保守する | TUF再利用より先に選ばない |

ここでのdescriptorはTUFで認証した小さなtarget fileの案であり、新しい署名protocolではありません。記載するpayloadのhash/lengthを検証し終わるまでwriterへ渡しません。HTTPS取得やchecksumの一致だけを発行者の認証にはしません。

## 公開の順序

以下は未実装のpublisher案です。現行buildに署名jobがあるという意味ではありません。

1. 本番鍵を持たないbuild jobでimage、bundle、SBOM、licenseとprovenanceを生成し、入力commitと出力digestを固定する。
2. 狭い署名jobで対象を検証し、必要なpayload署名を付ける。任意のcheckoutやBuildroot処理へ秘密鍵を渡さない。
3. draft Releaseへ全assetを添付し、名前・長さ・hash・署名・provenanceを別の検査で照合する。immutableとしてpublishした後に公開assetの取得可能性とdigestを確認する。
4. targetsまたはdescriptorを署名する。整合するsnapshotとtimestampを生成し、clientが必要とするpayload、version付きmetadata、root履歴を先に取得可能にする。新timestampは最後に参照可能にする。
5. metadataの公開を検査する。CDNで旧・新応答が混ざっても検証失敗として安全に再試行できるようにする。途中の不整合を避けるため署名検査を緩めない。
6. OSを変更しない期間も、timestamp等の期限に十分先行して再署名・publishし、残り期限とjob失敗を監視する。権限や鍵をtargetsの発行と分離する。

root履歴や旧metadataを無条件に掃除すると、長期offlineの端末が信頼鎖を辿れなくなります。保持期間・想定offline期間・復旧手順を一緒に定めます。オンライン鍵の侵害は可用性や鮮度を損なえるため、root/targetsを同じ常設Secretへまとめません。

## GitHub APIを認可に使わない

[Release API](https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28)は公開dataの匿名取得を認めます。`latest`はdraft/prereleaseを除くなどGitHubの規則による選択で、MSD/LinuxのchannelやSemVer、署名済みの最高許可版を保証しません。Releaseの説明、作成日時、asset名、APIのdigest fieldは、署名したmetadataの代わりに使いません。

通常はimageに固定したmetadata repositoryを確認し、Release APIを必須の信頼鎖から外す案を優先します。UIでRelease一覧を表示する場合も未信頼の候補として扱います。stable/beta等の選択は認証済みcatalogと端末policyで決め、GitHubのprerelease flagだけで選びません。

[匿名REST取得のprimary上限](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)は送信元IP単位で毎時60件です。同一NAT下の端末が枠を共有するため、固定時刻の一斉取得を避け、頻度・jitter・backoffを設けます。端末へPATを配って解消しません。

[公式best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)のETag/Last-Modifiedを使いますが、304でもmetadataの期限は再検査します。primary枠を消費しないという説明は認可済みの条件付きrequestの場合であり、匿名304へその保証を転用しません。キャッシュは通信を減らす手段で、鮮度を証明するものではありません。

## 取得clientに必要な制限

| 境界 | 必要な動作と拒否試験 |
|---|---|
| TLS・URL | 証明書、hostname、有効期限を検証する。HTTPS限定、許すhost/port/schemeとredirect回数をpolicy化する。`file:`、loopback、private/link-local、userinfo、別protocolへの誘導を拒否する。CDNのhost変更時は安全に停止し、無制限許可へ自動変更しない |
| redirect | [asset API](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28)の200と302の両方を扱う。hopごとにURLと接続先を検査し、DNS再解決も制限の対象にする。認証headerやcookieを別hostへ転送しない。端末の通常取得にはGitHub credentialを持たせない |
| HTTP失敗 | 403/429ではRetry-Afterやrate-limit headerを確認し、上限付きで待つ。5xx/切断はbackoffし、404の反復も制限する。検査失敗を「更新なし」「導入済み」へ変えない |
| bytes・時間 | metadata role別の上限、file数、root更新数、委任深度、接続・read・総時間を決める。Content-Length欠落・偽装、chunked、低速無限stream、圧縮HTTP本文の膨張も、実際に受け取るbytesで制限する |
| payload | 認証したhash/lengthと端末の絶対上限を両方守る。短い・長い・部分的なfile、別機種・別channelを拒否する。imageのpartition上限もwriterが別に確認する |
| retry/resume | 部分fileは未検証として分離し、Range/ETag/応答status・範囲を確認する。200の全体応答を追記しない。最後に全体hash/lengthを検証する。初期実装ではresumeを無効にし、単純さと再転送費用を比較する |
| 空き容量 | download用の領域、展開領域、metadata、journalと運用余白を含める。現行writerはtarを`/tmp`へ展開するので、`/data`だけの確認では足りない。`/tmp`がtmpfsならRAMも予算に含める |
| archive | 認証したtarでもmember数、展開後サイズ、通常file種別、許す名前だけに制限する。絶対path、`..`、link、device、重複member、archive bombを拒否し、network入力をrootで汎用展開しない |

host allowlistは配信元の変更で更新不能になる背反があります。緩めて可用性を優先するのではなく、想定CDN・障害時の復旧・policy更新を試験してから決めます。IP制限とDNSの検証を別々の時点に行うだけでは、DNS rebindingへの対策として不十分です。

metadata・payloadの中身をlogへ無制限に出さず、URIのquery、Wi-Fi credential、署名鍵は記録しません。公開記録は版、digest、長さ、状態と必要なerror分類に絞ります。これらは要件であり、新clientで確認済みの機能ではありません。
