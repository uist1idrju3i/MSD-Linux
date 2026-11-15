# NVD feed停止とCVE checkの保護先変更

[Actions監査](github-actions-audit.md) / [監視失敗の扱い](../../ci-monitoring.md) / [Release保護](../release-client/release-security.md)

## 2026-11-15の結論

PR #247・#248・#254で報告された`product CVE scan`の失敗を調査しました。上流default branch自体のcommit更新が止まり、現行の24時間制限で監視stateの生成が失敗しています。古いSHAの固定やActions cacheの再利用が原因という説明は、取得経路とネットワーク照合に一致しません。**staleは監視未確認であって、CVE 0件ではありません。**

利用者は2026-11-15、同checkをmain rulesetのrequiredから外し、release rulesetへ移しました。エージェントはruleset、workflow、閾値、gateの意味を変更していません。これはmerge・tagの保護先の変更であり、scanを成功に変える判断でも、古いfeedで安全と認定する判断でもありません。

## 取得・判定経路

調査基準はmain `980b7c8549357922801edafd83ea2e1bc547b39e`です。

| 箇所 | 確認した動作 |
|---|---|
| `.github/workflows/security.yml:3–7,15–18` | `Security report`の`scan` job、表示名`product CVE scan`。PR、`25 */2 * * *`のschedule、手動dispatchが対象。**push/tag作成triggerはない** |
| 同`:71–79` | `https://github.com/fkie-cad/nvd-json-data-feeds`を毎回`git clone --depth 1`。ref/SHA指定なしでdefault branchの最新HEADを取得。取得後に`rev-parse HEAD`と`git log -1 --format=%ct`を実行 |
| 同`:78–79,89–98` | `output/images/nvd-feed-commit-time.txt`は上記committer epoch secondsの出力。取得時刻やNVD entryの更新時刻ではない。runnerの`date -u +%s`とともに`cve-monitor.py state`へ渡す |
| 同`:81–87,151–173` | Buildroot分析は`--no-nvd-update`。PR base/headで同じcloneを使い、base state・差分gateはhead state生成の後。今回の失敗は新規CRITICALの比較より前 |
| `.github/scripts/cve-monitor.py:423–429,655–671,722–724` | `now - feed_commit_time > 24 * 60 * 60`でValueError。stateを書き出さず、`cve-monitor: ...`を出して終了値1。これは監視入力の完全性エラー |
| `tests/check-cve-monitor/run.py:263–266` | 86400秒は許可、86401秒で拒否する境界fixture。調査時の全47 testは成功 |

設計上の24時間は[Actions監査](github-actions-audit.md)の`security.yml`行に明記され、導入commitは`d9525988e1666522d350b92c3c065e5c469d5646`（PR #197、2026-11-03）です。[当時の計測](../../experiments/2026-11-03-sbom-cve-monitor.md)は毎回cloneを採用し、空入力・feed鮮度の失敗を止める方針を記録しています。**24時間という数値を上流SLAや履歴統計から導出した根拠は、調べたdocs・導入差分では見つかりませんでした。** 2時間のcronと24時間の限度は別です。

## 上流へのネットワーク照合

2026-11-15 **10:25:23 UTC**、[commit API](https://api.github.com/repos/fkie-cad/nvd-json-data-feeds/commits/main)と`git ls-remote --symref`でdefault branch `main`のHEADを照合しました。

| 項目 | 観測 |
|---|---|
| 最新commit | [`2ea002cc3b166ddbd3dfaf54371d7e6729fac92a`](https://github.com/fkie-cad/nvd-json-data-feeds/commit/2ea002cc3b166ddbd3dfaf54371d7e6729fac92a) |
| author/committer時刻 | ともに2026-11-13 03:23:31 UTC |
| message | `Auto-Update: 2026-11-13T03:18:03.569477+00:00` |
| 観測時のcommit age | 約55時間2分。新しいcloneでも24時間制限を超える |
| [直近35 commit](https://api.github.com/repos/fkie-cad/nvd-json-data-feeds/commits?sha=main&per_page=35) | 11/10 07:05:55〜11/13 03:23:31 UTC。34間隔の中央値7199.5秒、最小6888秒、最大8356秒。通常は約2時間だが、SLAの証明ではない |

直近の時刻は11/12 21:06:00、23:05:58、11/13 01:04:15、03:23:31 UTCでした。Repository APIの`pushed_at`は11/15 01:23:07 UTCでしたが、default branch HEADの新しさとは一致しません。`pushed_at`だけを鮮度の代用にしません。上流の更新停止の内部原因と、NVD本体・他mirrorの現在の鮮度までは調べていません。

## mainでも起きた失敗

[mainのsecurity run一覧](https://api.github.com/repos/uist1idrju3i/MSD-Linux/actions/workflows/security.yml/runs?branch=main&per_page=60)の48件を照会しました。現在の連続失敗は11/14以降のscheduleで、同じmain commit `733d27e66c8499aa306325cb4ce928c6ed2f1034`上です。

| run・scan job | UTCの時刻と結果 |
|---|---|
| [43529416783](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/43529416783) / `132243114638` | 11/13 23:45:04開始、scan成功。今回の連続失敗直前の成功 |
| [43568210795](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/43568210795) / `132366624389` | 11/14 06:49:40開始、**06:52:58.4288632に同じstaleエラー**。確認できた今回の連続失敗の最初 |
| [43700413337](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/43700413337) / `132770098792` | 11/15 09:41:00開始、**09:44:21.3927995に同じstaleエラー**。調査時の最新schedule |
| [43702983703](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/43702983703) / `132777933020` | PR #254、11/15 10:15:58.4818431に同じstaleエラー |

```text
cve-monitor: NVD feed commit is older than 24 hours
##[error]Process completed with exit code 1.
```

中間の11/14 15:14、20:50、11/15 02:00開始runもfailureでしたが、この表の両端のscan logと区別します。24時間境界は11/14 03:23:31 UTCで、最初の確認済み失敗時には約27時間29分です。以前の11/05 failureはjob API上artifact uploadの失敗であり、staleの開始時点には数えません。最新main HEADへのpushでCVE checkがないことも成功を示しません。workflowにpush triggerがなく、scheduleはdefault branchのHEADを対象にします。

## 保護先の変更とRelease運用の未確認

同日の利用者申告と、公開[main ruleset API](https://api.github.com/repos/uist1idrju3i/MSD-Linux/rulesets/25345093)・[release ruleset API](https://api.github.com/repos/uist1idrju3i/MSD-Linux/rulesets/26334422)を照合しました。設定を変更するAPIは呼んでいません。

- main `25345093`のrequiredは`build`、`changes`、`lint`、`zizmor`、`check`、`MSD tests in development image`、`dev-image gate`。`product CVE scan`は含まれません。
- release `26334422`はactive、target=tag、include=`refs/tags/v*`と`~ALL`。rulesはdeletion / non_fast_forward / update / creation / required_status_checks、requiredは`product CVE scan`（integration `15368`）、strict=falseです。
- **`~ALL`によりv*以外も含む全tagへ広がります。意図した範囲かは利用者確認待ち**です。
- creation restrictionの例外として作成できるbypass actorの設定が必要ですが、公開APIではactor設定を確認できません。作成可能な運用は未検証です。ruleset全体のbypassはrequired checkも迂回し得るため、check成功の代わりに使いません。[rulesetの説明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)と実際の権限・例外を管理者が照合する必要があります。

tag対象commitには同じSHAでのscan成功が必要です。main HEADのschedule成功を別の古いcommitへ流用しません。上流feedが古い間は、requiredから外したmainでmergeできても、scanは失敗したままです。fresh feedを得て当該commitのschedule/dispatchを成功させる運用が残ります。過去の成功checkだけでRelease時点のfeed鮮度が保証されるわけでもありません。

### 古いcommitへの手動dispatch

[GitHub公式REST仕様](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)ではdispatchの`ref`は**branchまたはtag名**です。main HEADだけに限定されません。古いcommitを指す既存branch/tagがあれば、そのref上のworkflowを実行する設計が可能です。任意の古いSHAを直接`ref`へ渡すことは仕様上の保証がなく、今回APIで試していません。

当該refに`workflow_dispatch`対応のworkflowが必要で、default branchにもworkflowが存在する必要があります。[公式event仕様](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)は`GITHUB_SHA`をdispatch先branch/tagの最後のcommitと定義します。新tag作成自体が制限される場合、「tagを作ってからscan」では循環し得るので、作成前の同一SHAの検査経路を管理者が決める必要があります。`security.yml:213`のreportはmain ref限定のため、別branch/tagへのdispatchではscanとIssue更新の動作も区別します。dispatch、tag作成、bypassの実動作は試していません。

## 今回変更しないもの

閾値・判定・workflow・rulesetは変更しません。比較した改善案は、(1) 更新間隔を踏まえた警告/失敗閾値の明文化、(2) 鮮度不足とCVE差分を別状態・別checkで表示、(3) freshなmirrorまたはNVD本体へ対応する取得器の検討です。それぞれ猶予拡大による見逃し期間、requiredの運用判断、schema/信頼/完全性/履歴の検証費用があります。今回の約55時間停止を通常の2時間間隔の揺れとして扱わず、いずれも未採用・未実装とします。

監視不能時は件数・解消を報告せず、既存Issueの最後の成功結果と失敗を区別する[現行方針](../../ci-monitoring.md)を維持します。Release作成、保護の迂回、実機・製品の安全性は検証していません。
