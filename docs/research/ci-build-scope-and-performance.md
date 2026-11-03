# 文書差分で起動するCIと高速化の判断

[RESEARCH](../../RESEARCH.md) / [実行境界の監査](github-actions-audit.md) / [開発・CIの代替比較](alternatives/development.md)

## 署名CLI試験の分類を修正した範囲

2026-11-03の追補です。`tests/release-signing-key/run.py` 一件を軽量試験へ分類し、製品buildの有無に依存しない `MSD tests in development image` へ実行を追加しました。docsとこの試験だけの累積差分では製品buildを省略します。試験用の秘密鍵は使い捨てで、保存するログに秘密鍵を出しません。

全testを除外する変更ではありません。製品の署名・更新source、通常のhost試験、build workflow、未知のpath、差分判定不能は引き続き製品buildへ倒します。専用ディレクトリーに将来追加する別ファイルも、今回の例外には入りません。

[回帰試験](../../tests/check-build-scope/run.py)は、workflow内の実際のBashを実行し、path・累積三点差分・push/PR・週次/手動・SHA欠損・fetch/diff失敗をfixtureで確認します。GitHub上での新規runを代行した試験ではありません。試験呼出し削除、条件依存の追加、例外削除、全test除外、workflow例外削除の改変を検出します。詳細と実行revisionは[検証記録](../experiments/2026-11-03-maintenance-followup.md)に保存します。

今回の変更自体はbuild workflowを含むため、今回のPRでは製品buildが必要です。以下のPR #187等と117行の判定記録は変更前の履歴として残します。

## 結論

この本文は改善前の定義と実行履歴の記録です。改善後は[CIの説明](../CI.md)と[起動条件・cache・並列回帰の検証](../experiments/2026-11-03-ci-cache-and-parallel.md)を参照してください。以下の「現在」「未実装」は、本文に固定したcommitと観察時点を指します。host回帰の2並列化、未公開OCIの完全一致archive cache、ccache世代と再実行の分離を追加した後の性能を、この観察値から推定しません。

文書変更でもworkflow自体、文書検査、lint、host回帰は動きます。製品imageのbuildは別の判定です。[PR #187](https://github.com/uist1idrju3i/MSD-Linux/pull/187)では、累積差分125ファイル中の`tests/release-signing-key/run.py`だけが製品buildを要求しました。その後のcommitが文書だけでも、このファイルはPR差分に残ります。対して、純粋な文書整理の[PR #188](https://github.com/uist1idrju3i/MSD-Linux/pull/188)は9検査成功、製品buildはskipでした。

高速化は適用済みですが、最適化の完了ではありません。BuildrootのCPU並列化、独立job、OCIのnative amd64/arm64、download cache、ccache、公開開発OCIの再利用、古いPR実行の取消があります。一方、host回帰のsuite内は直列で、Docker layerを後続runnerへ渡す明示的な外部cacheはありません。OCIが未公開の場合、複数jobが各々同じ開発環境を再構築します。

以下は`5d5b275f27da0cf2de6402eeb21b36fb9095a02a`の定義と、2026-11-03 UTCに取得した実行記録の観察です。workflow・製品設定・依存版は変更していません。制御した性能比較でも、実機試験でもありません。生CSV、失敗した抽出、再照合手順は[検査記録](../experiments/2026-11-03-ci-scope.md)へ保存します。

## 何を差分判定しているか

定義は[build.yml](../../.github/workflows/build.yml)にあります。`changes`の`steps.filter.outputs.build`をjob出力へ渡し、`build`が`needs.changes.outputs.build == 'true'`で起動します。`MSD tests in development image`はこの出力に依存しないため、文書差分でも実行します。

| 入口・差分 | 現在の処理 | 理由・注意点 |
|---|---|---|
| PR | base SHAとhead SHAの三点差分 | merge-base以降のPR全体。直前commitとの差分ではない |
| main push | beforeと現在SHAの三点差分 | PRの成功を理由に自動省略しない。mainでの統合確認を兼ねる |
| 手動・週次 | 製品buildを要求 | 差分に関係なく定期・任意の検査を残す |
| headが見えないPR | PR head refのfetchを試す | fetch失敗はbuildへ倒す |
| base/head不明、全0のbase、diff失敗 | 製品buildを要求 | 判定不能を「不要」と扱わない |
| `.github/workflows/build.yml` | 製品buildを要求 | 下記の`.github/*`より先の特例 |
| `*.md`、`docs/*`、`public_html/*`、`.agents/*`、`.claude/*` | 製品buildを省略 | 文書・site等の専用検査は別に実行する |
| `vendor/yomiyasu`、`LICENSE`、`.devin/*`、`tests/check-*/*`、残りの`.github/*` | 製品buildを省略 | checker等の変更。全てのPythonや全testを除外してはいない |
| その他のpathが一つでもある | 製品buildを要求 | defconfig、kernel、Docker入力、通常のhost test等も含む |

`PR #187`の固定head `20a80264d65647e933e553cdc33c8a61f0549050`はmainを取り込んだmerge commitです。第二親からheadまでの三点差分と、GitHubのPR files一覧の125件を照合しました。上記の署名CLIテストだけが除外規則に入りません。固定したcase部分を19条件で5回ずつ実行し、build workflowの特例を消す改変と、全testを除外する改変も検出しました。event/fetch/diff失敗の分岐はソースを読んだ範囲で、模擬実行はしていません。

署名CLIテストは使い捨て鍵でOpenSSLの操作を確かめるhost試験です。ただし、現行workflow内にはこのrunnerを呼ぶ記述がありません。製品buildが動いたことを、このCLI試験がCIで動いた証拠にはできません。軽量化するなら、名前を`tests/check-*`へ変えるだけでは不十分です。固定OCIのhost回帰へ明示的に組み込み、鍵の出力先を一時領域へ限定してartifactへ載せず、成功・改変・別鍵拒否を確認してから分類を変えます。未知のtestを全て除外する広い規則は採りません。

## 適用済みの並列化とcache

| 層 | 現在 | 残る制約 |
|---|---|---|
| workflow/job | 文書・lint・security等は独立。buildとhost回帰も別job | runnerの待ち時間、独立した環境準備の重複は残る |
| Buildroot | `make -C output -j"$(nproc)"`、`BR2_CCACHE=y` | package内とpackage間の並列化は同じではない。PPDの比較と成果物差は[既存記録](dev-environment-and-ci.md)を参照 |
| host回帰 | 9 runnerを同じOCIで順に実行 | 更新・init・hwinfo・data拡張・ログ検査・wrapper・Trivy・SBOM。matrixにすれば環境準備も増える |
| 開発OCIの公開 | amd64は`ubuntu-26.04`、arm64は`ubuntu-26.04-arm`、`fail-fast: false` | native ARM採用はOCI構築であり、製品Buildroot jobはamd64。標準runnerか有料runnerかはlabelだけで料金を確定しない |
| 公開OCIの再利用 | 内容から`inputs-<hash>`を作り、manifestを照会してpull。CIはattestation必須 | 未公開ならlocal build。attestation不正や一般の取得失敗を無条件に成功へ落とす設計ではない |
| Buildroot download | `dl`。OSとdefconfig/外部recipe/hashのhashをkeyにし、OS prefixで復元 | vendor Buildroot revisionはprimary keyへ直接入らない。recipe側のhash等の検証も別に確認し、cacheをsource認証の代替にしない |
| ccache | `.ccache`。OSとrun IDのprimary key、OS prefixのrestore、成功buildの後で保存 | 毎run別key。再実行は同run IDになり得る。compiler/source/options等の内部keyとは別。長期の容量・転送・evictionは未評価 |
| Docker layer | job内のDocker/BuildKitによる再利用 | 現行の`docker build`には`cache-from`/`cache-to`等の外部cache指定がない。別runnerへのlayer再利用が保証されるわけではない |
| Trivy DB | OCI公開job内で同じ一時volumeを再利用 | これはBuildrootのNVD cacheともDocker layerとも別。明示的なjob間DB cacheはない |
| concurrency | PRは新しいrunで古いrunをcancel | main pushはcancelしない。concurrency groupは直列化・保留にも関わるが、全pushを必ず最後まで実行する保証でもない |

Docker内のhost compilerとBuildrootのhost packageは、VMに直接あるcompilerを製品buildへ使う意味ではありません。targetはBootlin等、host補助toolは開発OCI内のtoolchainで構築する現在の境界を維持します。速さのためにこの区別を崩しません。

## 実際のログで確認した費用

取得時点の直近の完了30 runは成功21、cancelled 9、失敗0でした。そのうち新しい成功5 runを、構成差のある観察例として選びました。成功例の抽出を全実行の信頼性・平均時間の推定へ使いません。2 runは製品buildがskipで、実行された製品buildは3件だけです。

| run | host回帰のOCI準備 | 製品buildのOCI準備 | image + legal-info step |
|---|---:|---:|---:|
| [41548215940](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41548215940) | local build、412秒 | local build、281秒 | 812秒 |
| [41547703403](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41547703403) | local build、417秒 | local build、428秒 | 1,250秒 |
| [41547627611](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41547627611) | 公開OCI、13秒 | skip | skip |
| [41540889739](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41540889739) | 公開OCI、15秒 | 公開OCI、13秒 | 1,199秒 |
| [41528679681](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41528679681) | 公開OCI、17秒 | skip | skip |

これらを同条件のcold/warm 5反復と数えたり、短縮率へ換算したりしません。最新の文書PRでも`inputs-fcf14a3abc4d89ac`がなく、host回帰・lint・zizmorでlocal buildしたことを読みました。`inputs`の一致する公開物がないことはログの事実ですが、その理由をregistry障害とは断定しません。Brotliの公開ゲート失敗、入力hash、公開run、manifestの対応を保ったまま調べる必要があります。ゲートを緩めたり、異なる入力の古いimageを正しいimageとして使ったりはしません。

3 buildのccacheは、いずれも15,853/21,949 callsがcacheable、6,096 callsがuncacheableでした。hitは15,838、15,825、15,847で、それぞれcacheable calls中99.91%、99.82%、99.96%です。全呼出しの99%以上が省略されたという意味ではありません。workflowは`host-ccache`の準備後に`-z`を実行するため、それより前の準備時間もこの比率には入りません。高hit率でもlink、configure、host準備、legal-info、image作成等の費用は残ります。

download復元は8〜11秒、ccache復元は各9秒、ccache保存は5〜6秒でした。復元したarchiveはdownloadが1,282,529,261 bytes、ccacheが1,051,053,440〜1,051,079,000 bytesです。これも3件の観察であって長期の転送費用ではありません。build stepは`CCACHE_MAXSIZE=3G`を指定し、wrapperもこれを転送しますが、統計stepにはその指定がなく、表示は上限5.0 GiBです。統計の表示条件が異なるため、これをbuild中の上限が無効だった証拠にはしません。cache全削除や上限変更を、この調査では行っていません。

## cacheの安全性と次の改善

[GitHub公式のcache参照](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)では、現在・default・PR baseの読み出し範囲と、PR merge refへの保存を区別しています。通常の`pull_request`のcacheをmainがそのまま復元できるとはしません。`pull_request_target`、`workflow_run`等のdefault scopeへの書込制限と新しい`cache-mode`も説明されていますが、MSD/Linuxのbuildは`pull_request`です。scopeの制限はcache内容の署名ではなく、同じkeyやSHA固定Actionだけでcacheの信頼性を証明できません。cacheへ秘密鍵、認証情報、設定済み資格情報を保存しません。

2026-11-03 00:37:58 UTCのAPI観察では、cacheは16件、10,781,149,193 bytesでした。公式資料は既定上限10 GB、古いcacheのevictionや容量追加時の課金を説明しますが、当repoの設定上限・契約・実際の課金は未確認です。容量の観察だけで有料になったとは断定しません。runごとのccache保存は、個々のhit率が高くても容量競合を起こし得るため、追加layer cacheと同じ予算で評価します。

| 優先 | 改善候補 | 効果・背反・採用条件 |
|---|---|---|
| 1 | 署名CLIテストを明示的な軽量回帰へ | 不要な製品buildを防ぐ。名前だけ変えずCIで実行し、製品source混在・build.yml変更・判定不能でbuildが残ることを負の試験で確認する |
| 1 | 開発OCIの再構築を可視化し、同入力の準備を共有する方式を比較 | 今回のログではhost回帰の実行より環境準備の費用が目立つ。信頼済み公開OCIの再利用を第一候補とし、PR変更時はnativeな準備jobとartifact転送を比較する。転送・展開・容量・検証の費用が増えるため、共有が必ず速いとはしない |
| 2 | ccacheの世代・保存頻度・上限を調整 | OSだけでなくhost arch、target、toolchain/Buildroot/OCIの世代を区別する候補。commitごとの全source hashは再利用を狭める。ccache内部のcompiler検査・options/source/headerの扱いを維持し、key変更だけで正しさを保証しない。run attempt衝突と並行saveも試す |
| 2 | 外部Docker layer cacheを小さく試す | native archと用途でscopeを分離し、runner driver条件、`mode=min/max`、転送容量、API制限、未信頼PRとの境界を確認する。cacheでscan・SBOM・attestationの対象がずれないことが必要 |
| 3 | host回帰を計測後に少数groupへ分割 | suite分離の壁時間短縮と、OCI準備の重複を同時に測る。9 runnerを単純に9 jobへ増やさない。状態・一時path・終了値・失敗を隠すsummaryを確認する |
| 3 | mainの古い実行取消を変更種別別に検討 | 通常PRとmainの重複費用は減らせるが、mainだけの統合差分、週次、Release、必須checkを失わない。単にpush入口を消さない |
| 4 | 製品buildのnative ARMや別cache backend | QEMU emulation、toolchainのhost対応、再現性、標準runnerの利用条件を先に確認する。OCIのnative ARM成功を製品buildの互換・高速化の証明にはしない |

ccacheの動作は[公式manual](https://ccache.dev/manual/4.14.2.html)、Dockerの外部cacheは[公式gha backend](https://docs.docker.com/build/cache/backends/gha/)、取消・保留は[GitHub公式concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)で再確認しました。採用実験は同じcommit・image digest・runner archでcold/warm各5回以上、総時間・runner時間・転送bytes・保存量・成果物一致・拒否試験を事前に基準化します。今回これらの最適化を実装・実測したとはしません。
