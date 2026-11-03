# Releaseの保護とEd25519署名鍵の設定

対象は、このリポジトリの管理者です。端末でのA/B更新は [UPDATE.md](UPDATE.md)、設計の根拠と未実装部分は [Releaseのセキュリティ調査](research/release-client/release-security.md)、その他の操作は [文書案内](README.md) を参照してください。

## まず確認すること

鍵の種類は、既存実装と同じ **Ed25519** を想定します。秘密鍵をチャット、Issue、PR、リポジトリへ送らないでください。Devinが本番鍵を受け取る必要はありません。

現在の署名対象は、A/B更新bundle内の `manifest` です。`sdcard.img.xz` 全体やReleaseの全assetを署名する仕組みではありません。2026-11-02の確認では、署名用Environmentと、それを使うRelease workflowはありません。Secrets一覧のAPIは403で閲覧できず、既存Secretの有無は未確認です。

**以下は設定の準備手順です。Secretを保存しただけでは、現在のビルドはその鍵を使いません。** 公開鍵だけをimageへ入れる処理と、独立した署名jobができるまで、本番鍵をbuild jobへ渡したり、署名済みの製品Releaseとして公開したりしないでください。

| 項目 | この手順で使う候補名 | 内容 |
|---|---|---|
| GitHub Environment | `release-signing` | 署名jobだけが参照する保護された環境 |
| Environment secret | `MSD_RELEASE_ED25519_PRIVATE_KEY_PEM` | PEM形式の秘密鍵の内容。改行を含む |
| 既存スクリプトの環境変数 | `MSD_UPDATE_SIGNING_KEY` | 秘密鍵の内容ではなく、署名job内の鍵ファイルへのパス |
| image内の信頼鍵 | `/usr/share/msd-update/update-key.pem` | 秘密鍵と対になる公開鍵。初回導入時の信頼の出発点。`/etc` overlayの対象外 |

Environment名とSecret名は新設案です。値を保存する前に、今後のworkflowで同じ名前を参照することを確認します。

## 1. 管理権限とReleaseの保護を確認する

1. [リポジトリのSettings](https://github.com/uist1idrju3i/MSD-Linux/settings) を開きます。個人所有のリポジトリでは所有者の権限が必要です。
2. GeneralのReleases欄で **Enable release immutability** を有効にします。画面や権限が異なる場合は [GitHubの手順](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes) を確認し、利用できない状態で保護済みと扱わないでください。
3. この設定は今後のReleaseに適用されます。既存の開発プレリリース `v0.0.0` を、自動でimmutableにする設定ではありません。既存assetの置換で署名済みに見せる運用はしません。
4. RulesのRulesetsで、既存の `release` rulesetが有効か確認します。確認時点では `refs/tags/v*` に削除禁止とnon-fast-forward禁止が設定されています。これだけでは、新規タグの作成者、SemVer、試験結果、Release assetの変更までは制限できません。
5. ActionsのGeneralで、既定のworkflow権限が必要最小限か確認します。既定は読み取りのみを推奨します。公開jobの `contents: write` などは、そのjobだけに与える設計にします。こちらからルールセットやブランチ保護は変更しません。

## 2. 署名用Environmentを先に作る

1. [SettingsのEnvironments](https://github.com/uist1idrju3i/MSD-Linux/settings/environments) を開き、New environmentから `release-signing` を作ります。`github-pages` は流用しません。
2. Required reviewersに、署名対象のcommitとassetを確認できる人を指定します。複数人を列挙しても、GitHub標準のこの設定は「そのうち1人の承認」であり、複数人の同意を必須にするものではありません。
3. 別の承認者がいる場合はPrevent self-reviewを有効にします。所有者1人だけで、自分が起動したjobを自分で承認する運用では、この設定により実行できなくなります。別の承認者を用意するか、自己承認を許すリスクを明示して採用するかを先に決めます。保護を迂回して実行する手順にはしません。
4. 管理者による保護ルールの迂回を許す設定は、無効を推奨します。復旧担当と手順も決めておきます。
5. Deployment branches and tagsをSelected branches and tagsにし、将来の署名workflowに必要なrefだけを許可します。推奨する「保護されたmain上の手動workflow」ならBranchの `main` を許可します。Tag起動を採る場合は別にTagルールが必要です。
6. ここで検査されるrefはworkflowが動くrefです。入力欄のタグ名や、後からcheckoutするcommitを、この設定だけで検証できるわけではありません。手動workflowでも対象タグ、commit、成功したbuildとの対応を別に検査します。
7. [GitHubのEnvironment管理手順](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) と画面を照合し、保護の保存を確認します。workflowから存在しないEnvironmentを参照すると、保護のない環境が自動作成される場合があるため、Secretの保存より先に作成・点検します。

## 3. 手元の信頼できるPCで鍵を作る

本番鍵は自分で管理するPCで生成します。共有端末、オンラインの鍵生成サイト、PRのrunnerでは生成しません。OpenSSL 3系とBashを前提にした例です。macOSなどで `openssl version` がLibreSSLを示す場合は、この手順の動作確認範囲ではありません。

次の一まとまりの処理は、既存の鍵ファイルがあれば上書きせず停止します。ディレクトリは同期・共有対象にしないでください。ファイル名の `release-1` は鍵の識別子であり、OSのリリース番号ではありません。

```bash
(
    set -euo pipefail
    umask 077
    openssl version
    key_dir="$HOME/.local/share/msd-linux/release-keys"
    mkdir -p "$key_dir"
    chmod 700 "$key_dir"
    private_key="$key_dir/release-1-private.pem"
    public_key="$key_dir/release-1-public.pem"
    test ! -e "$private_key"
    test ! -e "$public_key"
    openssl genpkey -algorithm Ed25519 -out "$private_key"
    chmod 600 "$private_key"
    openssl pkey -in "$private_key" -check -noout
    openssl pkey -in "$private_key" -pubout -out "$public_key"
    openssl pkey -pubin -in "$public_key" -text -noout
    openssl pkey -pubin -in "$public_key" -outform DER |
        openssl dgst -sha256
)
```

表示する鍵情報は公開鍵だけです。`ED25519` であることと、最後のSHA-256を確認します。fingerprintは公開鍵のDER表現のSHA-256であり、PEMファイルの改行の違いには依存しません。公開鍵とfingerprintは、秘密鍵とは別に保管・照合できるようにします。

この例の秘密鍵PEM自体は暗号化されていません。0600はファイルへのアクセス制限であり、PCの侵害やバックアップ流出を防ぐ暗号化ではありません。暗号化したオフライン媒体などへ復旧用の複製を作り、復元後に同じ公開鍵とfingerprintを得られることを確認します。Secretを唯一の保管先にしないでください。Release用の鍵は、SSH、TLS、kernel module署名など別用途の鍵と共用しません。

鍵を既に持っている場合は、新しい鍵を不用意に作らず、公開鍵と型を確認します。Ed25519の鍵であっても、既存imageが信頼している公開鍵と異なれば、そのままでは更新できません。

## 4. Secretを登録する

方法はUIかCLIのどちらか一つです。**環境変数 `MSD_UPDATE_SIGNING_KEY` にPEMの内容を入れる操作ではありません。**

### GitHub UIで登録する場合

1. Environmentsから `release-signing` を開き、保護設定を再確認します。
2. Environment secretsのAdd secretを選びます。Repository secretsの画面ではありません。
3. Nameへ `MSD_RELEASE_ED25519_PRIVATE_KEY_PEM` を入力します。
4. Valueへ手元の秘密鍵PEMの全体を入力します。ヘッダー、本文、フッター、改行を含めます。公開鍵と取り違えないでください。秘密鍵を画面共有やチャットへ表示しません。
5. 保存後にSecret名が表示されることを確認し、クリップボードも消去します。値を再表示して確認する方法はありません。

### GitHub CLIで登録する場合

`gh auth status` で自分のアカウントと管理対象を確認します。鍵の値ではなくファイルから標準入力で渡します。

```bash
gh auth status
gh secret set MSD_RELEASE_ED25519_PRIVATE_KEY_PEM \
    --repo uist1idrju3i/MSD-Linux \
    --env release-signing \
    < "$HOME/.local/share/msd-linux/release-keys/release-1-private.pem"
gh secret list --repo uist1idrju3i/MSD-Linux --env release-signing
```

一覧に出るのは名前などの情報で、鍵の値ではありません。`--body '秘密鍵の文字列'`、`echo`、デバッグの `set -x`、base64への変換による表示は使いません。秘密鍵の値を含むdotenvファイルも不要です。

## 5. 公開鍵の配備と署名jobの完成を待つ

登録後に必要な開発作業は次のとおりです。**この手順の文書化だけでは実装されません。**

- 秘密鍵なしでbuildし、事前確認した公開鍵だけをimageへ入れる入力を追加する。現在のpost-buildは秘密鍵から公開鍵を生成するため、改修が必要です。
- 承認済みの署名jobがEnvironmentを参照し、Secretから0600の一時ファイルを作る。鍵はcompiler、任意のbuild script、PR、fork、キャッシュ、artifactへ渡さない。
- 公開鍵のfingerprintと、Secretに対応する公開鍵が一致することを検査する。鍵がない、型が違う、一致しない場合は停止し、開発鍵へ代替しない。
- 署名jobへ渡すassetの出所、commit、hash、長さ、機種、版を検査する。別workflowのartifactであっても未信頼として扱い、そこから取得したスクリプトを秘密鍵のあるjobで実行しない。
- 更新manifestと、初回導入用の圧縮SD imageを認証するmetadataを分け、実際に公開する正確なバイト列を署名する。公開鍵だけを信頼できる経路で配布し、端末の初回導入・鍵移行を試験する。

`docker/msd-dev` は決まった環境変数だけを転送します。ホストで `MSD_UPDATE_SIGNING_KEY` をexportして呼ぶだけでは、鍵のパスや内容はコンテナーへ渡りません。本番鍵を渡すためにbuildコンテナーへ無条件mountする回避策も採りません。

## 6. 将来の署名済みReleaseを公開・確認する

1. 本番鍵ではなく試験鍵で、正常な署名の受理、改変、別鍵、欠落、未知の機種、古い更新、容量不足の拒否を先に確認します。host、生成image、QEMU、実機の範囲を区別します。
2. 対象タグ、commit、公開SemVer、内部更新番号、信頼する鍵、build結果を確認します。SemVerと内部番号の対応は[Release対応表](releases/README.md)のとおり承認済みです（内部番号はtag commitのcommit時刻）。この手順でmanifest仕様は変更しません。
3. Releaseをdraftとして作り、image、update bundle、署名metadata、SBOM、ライセンス資料など、必要なassetを全て添付します。公開後の追加や差し替えを前提にしません。
4. ダウンロードし直したassetの長さ・hash・Ed25519署名、image内の公開鍵、開発鍵でないことを照合します。現在の `manifest.sig` だけでSD image全体を確認したことにはなりません。
5. 承認後にpublishし、ReleaseページのImmutable表示を確認します。公開後に説明文やlatestの指定が変わる可能性は残るため、端末の信頼判断を説明文やlatestだけに依存させません。
6. 対応するGitHub CLIで、将来公開したimmutable Releaseを検証します。例のタグは実在する対象へ置き換えます。

```bash
tag='vX.Y.Z'  # 実際に公開したタグへ置き換える
gh release verify "$tag" --repo uist1idrju3i/MSD-Linux
gh release verify-asset "$tag" ./sdcard.img.xz \
    --repo uist1idrju3i/MSD-Linux
```

GitHubが自動生成するsource zip/tarballは、このasset検証の対象外です。GitHubのattestation検証と、端末が行うEd25519更新署名検証は別です。現在の `v0.0.0` はimmutableではなく、この確認の成功例には使えません。

## 7. 鍵の更新・紛失・漏えいに備える

平常時のローテーションは、新鍵を信頼させる更新を旧鍵で認証し、配備を確認してから署名鍵を切り替える設計が必要です。旧鍵・新鍵を受け入れる期間、未更新端末、期限、失効情報、復旧時の扱いを決めます。現在の単一公開鍵ファイルだけでは、この運用は完成していません。

漏えい時は署名・公開を止め、影響するworkflow・run・公開物を調べます。Secretの削除・交換だけでは、流出した秘密鍵で作られた署名は無効になりません。端末側で旧鍵を拒否する仕組みと、信頼できる媒体からの再導入を含む復旧方法が必要です。immutable assetを差し替えるのではなく、新しいReleaseと利用者への案内で対処します。

紛失時にバックアップもなければ、既存端末へ同じ鍵で更新することはできません。更新を配布する前に復旧手順を試します。microSD上の公開鍵、検証コード、rootfsを丸ごと交換できる物理攻撃は、署名付き更新だけでは防げません。

## この手順で確認した範囲

公式手順、閲覧可能なリポジトリ設定、ローカルCLIのhelpと、試験鍵による生成・公開鍵導出・raw署名・検証・改変と別鍵の拒否を確認しました。本番鍵の生成・登録、GitHub設定の変更、本番署名job、image署名、実機での鍵移行は実施していません。詳細と失敗した確認は [調査記録](research/release-client/release-security.md) にあります。
