# Releaseの保護とEd25519署名鍵の設定

対象は、このリポジトリの管理者です。端末でのA/B更新は [UPDATE.md](UPDATE.md)、設計の根拠と未実装部分は [Releaseのセキュリティ調査](research/release-client/release-security.md)、その他の操作は [文書案内](README.md) を参照してください。

## まず確認すること

鍵の種類は、既存実装と同じ **Ed25519** を想定します。秘密鍵をチャット、Issue、PR、リポジトリへ送らないでください。Devinが本番鍵を受け取る必要はありません。

現在の署名対象は、A/B更新bundle内の `manifest` です。`sdcard.img.xz` 全体やReleaseの全assetを署名する仕組みではありません。2026-11-12、通常のbuildと独立した[署名workflow](../.github/workflows/release-sign.yml)を追加しました。管理者からEnvironment Secret登録済みとの申告を受けていますが、値や保護設定をこちらから読み取ったわけではありません。

**本番秘密鍵はEnvironment `release-signing`のSecretだけから、承認後の`sign` jobへ渡します。** 通常のBuildroot buildと`build` jobには渡しません。Repository Secretやcache、artifactへ複製せず、GitHub設定の保護を弱めて実行しないでください。

| 項目 | 実装の名前 | 内容 |
|---|---|---|
| GitHub Environment | `release-signing` | 署名jobだけが参照する保護された環境 |
| Environment secret | `MSD_RELEASE_ED25519_PRIVATE_KEY_PEM` | PEM形式の秘密鍵の内容。改行を含む |
| buildの公開鍵入力 | `MSD_UPDATE_PUBLIC_KEY` | PEM公開鍵のパス。秘密鍵なしでimageを作る |
| 互換用の既存入力 | `MSD_UPDATE_SIGNING_KEY` | ローカルの秘密鍵ファイルへのパス。本番workflowは使わない |
| image内の信頼鍵 | `/usr/share/msd-update/update-key.pem` | 秘密鍵と対になる公開鍵。初回導入時の信頼の出発点。`/etc` overlayの対象外 |

公開鍵は[`release-1-public.pem`](../board/cardputerzero/keys/release-1-public.pem)で管理します。DERのSHA-256は`ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42`です。署名scriptはEd25519型、固定fingerprint、秘密鍵から導いた公開鍵との一致を検査し、不一致時に開発鍵へ代替しません。

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
5. Deployment branches and tagsをSelected branches and tagsにし、Branchの `main` だけを許可します。現行workflowはmain上の手動起動だけを受け入れます。Tag起動は実装していません。
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

この例の秘密鍵PEM自体は暗号化されていません。0600はファイルへのアクセス制限であり、PCの侵害を防ぐ暗号化ではありません。Secretの値は読み戻せないため、Environment Secretを唯一の保管先にしません。復旧用の複製は暗号化したオフライン媒体に保存し、復元した鍵から導出する公開鍵とDER fingerprintが、保管した公開鍵とfingerprintに一致することを確認します。本番実行時の鍵はEnvironment Secretから供給します。登録のための一時ファイルは管理者が処分し、秘密鍵をrepo、cache、artifact、共有端末へ保存しません。Release用の鍵は、SSH、TLS、kernel module署名など別用途の鍵と共用しません。

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

## 5. mainの公開鍵buildと保護された署名jobを実行する

1. mainの対象commit、公開鍵とfingerprint、成功した試験を確認します。Actionsの`Build and sign a release update`からRun workflowを選び、branchを`main`にします。入力で任意のcommit、タグ、artifactを指定する機能はありません。
2. `build` jobは同じ`github.sha`をcheckoutし、公開鍵だけでBuildrootを構築します。`key-origin=release`と公開鍵の一致を確認し、3 fileの`msd-update-bundle.unsigned.tar`、`sdcard.img.xz`、`COMMIT`、`SHA256SUMS`を`release-unsigned-<run ID>-<attempt>` artifactへ保存します。内部番号はcommit時刻で、`MSD_UPDATE_VERSION`は上書きしません。
3. Environmentの承認画面ではcommitとbuildのartifactを照合してから承認します。`sign` jobは同じcommitのscriptと公開鍵だけをcheckoutし、同じrunのbuild artifactを取得します。build出力のcommitとtar hash、全memberとmanifest hashを検査し、artifact内のscriptは実行しません。
4. Secretが空なら失敗します。鍵は`umask 077`でrunnerの一時領域へ書き、公開鍵との一致を確認してmanifestへraw Ed25519署名します。直後に公開鍵で署名を検証し、`msd-update-bundle.tar`を作ります。成功・失敗時とも後続のcleanup stepで鍵ファイルを削除し、公開候補と証拠のPEM・秘密鍵header検査後に`release-signed-<attempt>`を保存します。runnerの強制停止等ではstepの実行を保証できないため、使い捨てrunnerを前提にします。
5. 署名済みtar、`COMMIT`、`SHA256SUMS`を取得し、hashと公開鍵による署名を再検証します。署名済みtarの4 memberと端末clientの形式は変更していません。workflowはtagやGitHub Releaseを作成せず、公開は管理者が行います。

ローカルで同じ公開鍵buildを試す場合は、コンテナー内のパスを指定します。

```sh
MSD_UPDATE_PUBLIC_KEY=/work/board/cardputerzero/keys/release-1-public.pem \
    docker/msd-dev make -C output
```

`docker/msd-dev`はこの公開鍵変数を転送しますが、互換用の`MSD_UPDATE_SIGNING_KEY`は転送もmountもしません。post-buildへ両方を直接指定した場合は一致が必要です。どちらも指定しない既存buildは開発鍵を生成・再利用し、`key-origin=development`と署名済みtarを作ります。公開鍵modeでは古い署名済みtarを残しません。

tar hashと`SHA256SUMS`は同じrunの成果物を結び付ける証拠であり、初回導入用SD imageの独立した署名ではありません。manifestに機種IDやSemVerを追加しておらず、失効・配信client・初回導入経路の認証も別途必要です。

## 6. 署名済みReleaseを公開・確認する

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

端末が信頼する鍵は一つだけです。ローテーションには、新公開鍵を収録した更新を旧鍵で署名し、端末への配備を確認してから署名鍵を切り替える必要があります。通常のworkflowはbuild鍵と署名鍵の一致を要求するため、この鍵移行には旧公開鍵を保持する移行用の変更・承認・試験が別途必要です。Secretと公開鍵を同時に置換するだけでは、旧鍵の端末は更新できません。未更新端末、期限、失効情報、復旧時の扱いは未実装です。

漏えい時は署名・公開を止め、影響するworkflow・run・公開物を調べます。Secretの削除・交換だけでは、流出した秘密鍵で作られた署名は無効になりません。端末側で旧鍵を拒否する仕組みと、信頼できる媒体からの再導入を含む復旧方法が必要です。immutable assetを差し替えるのではなく、新しいReleaseと利用者への案内で対処します。

紛失時にバックアップもなければ、既存端末へ同じ鍵で更新することはできません。更新を配布する前に復旧手順を試します。microSD上の公開鍵、検証コード、rootfsを丸ごと交換できる物理攻撃は、署名付き更新だけでは防げません。

## この手順で確認した範囲

試験鍵による署名・client検証、改変と鍵不一致等の負試験は[`tests/release-signing/`](../tests/release-signing/run.py)で再実行できます。本番鍵の読み取り、GitHub設定の変更、本番Environment jobの実行、SD image全体の署名、実機での鍵移行は実施していません。過去の確認範囲は[調査記録](research/release-client/release-security.md)に保持します。

2026-11-13、管理者がrun `43331379685`から取得した本番署名artifactを[QEMU受入試験](experiments/2026-11-13-release-signing-qemu.md)に使いました。imageとguestのrelease公開鍵を照合し、同じ内部version `1794526865`の通常installが受理され、signature改変と署名なしが拒否されることを観測しました。書き込み済みBのpayloadを指定した起動とhealth commitも確認しました。

これはartifactを使ったguest試験です。こちらが本番Secretを読み取ったりEnvironment jobを起動したりしたという意味ではなく、live保護設定・immutable公開・実SD・実機firmware trybootは未確認です。
