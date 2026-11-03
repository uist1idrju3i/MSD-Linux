# OpenSSLの版と保守期限の監視

## 結論

Buildrootのtarget `libopenssl` と `host-libopenssl` は同じrecipeの3.6.5です。上流の[Release Strategy](https://openssl-library.org/policies/releasestrat/)は3.6系列の通常保守期限を2026-11-01としています。2026-11-03の確認では期限超過です。下流が継続保守する根拠は未確認であり、新たなCVEがあると確認した意味でもありません。

公式[Downloads](https://openssl-library.org/source/)では、保守対象の候補は次のとおりです。公開順の先頭だけで最新版を決めません。

| 系列 | 配布版 | 上流の保守期限 | MSD/Linuxでの扱い |
|---|---|---|---|
| 4.1 | 4.1.0 | 2027-11-23 | 最大の安定版候補。major移行としてAPI/ABI・廃止機能・Buildroot統合を調べる |
| 4.0 | 4.0.3 | 2027-05-14 | 4系の別候補。4.1より保守期限が短い |
| 3.5 LTS | 3.5.9 | 2030-04-08 | 長期保守候補。3.6からの機能後退と既存利用を調べる |

現時点では依存版を変更していません。最新版への追従を優先するなら4.1、保守期間を優先するなら3.5 LTSを比較します。API/ABI互換は同一major内という上流方針であり、CLIやproviderの既定動作まで同一とは断定しません。採用前に全変更履歴、target/hostの利用箇所、署名CLI、更新検証、TLS、license、SBOM、legal-info、生成物、QEMUを確認します。実機での暗号性能・更新確認も別に残します。

## 自動監視へ追加した境界

[固定版チェッカー](../../../.github/scripts/check-pins.py)は、親repositoryのHEADに記録されたBuildroot gitlinkのrecipeを取得します。未初期化・別revision・dirtyなローカルsubmoduleの内容を固定版として読みません。取得先は[.gitmodules](../../../.gitmodules)のBuildroot mirrorの固定SHAです。

- `OpenSSL (Buildroot target/host)` は公式配布表の安定版候補と固定版を比較します。全majorの保守対象系列を数値で比較し、pre-releaseや不正な版・系列は受理しません。
- `OpenSSL upstream support` は版比較と別行です。現行配布表の期限を優先し、表にない旧系列はRelease Strategyの明示的な期限を調べます。期限当日は超過とせず、翌日から `保守期限超過` とします。
- 表の形式変更、欠測、重複、日付不正、期限がreleaseより早い表、保守対象なのに配布表にない系列を `確認できず` とします。取得失敗を「最新」に変えません。
- 期限超過・確認不能は[既存の週次workflow](../../../.github/workflows/pins-check.yml)で[Issue #112](https://github.com/uist1idrju3i/MSD-Linux/issues/112)へ通知する条件です。今回はIssueの手動編集・週次workflowの手動起動はしていません。PRではネットワークを使わないfixtureを試します。

開発OCIのDebian配布版とBuildrootの版を混ぜません。既存の[APT台帳](development-apt.csv)ではOpenSSL 3.5.7-1~deb13u3です。今回の追加はDebianのbackport判定や全APTの最新版監視ではありません。署名CLIのhost試験も製品target版の実行証拠にはなりません。

## 残件

R24全体は未完了です。外部toolchainの内包物、全recipeの独立した最新版・保守期限、OCI全stage/arm64、Actions実bundleとrunner、CVE通知・未照合の扱いは[監視差分](README.md#監視の差分)に残ります。今回の修正で全依存が安全、保守中、最新版と認定したわけではありません。Brotliの延期と公開ゲートも変更しません。

再実行・負の対照・実際の入力hashは[検証記録](../../experiments/2026-11-03-maintenance-followup.md)を参照してください。

[依存監査へ戻る](README.md)
