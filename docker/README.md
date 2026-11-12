# 開発用コンテナー

ローカル開発とCI/CDで共通の開発環境を使うため、開発用Docker imageを構築し、公開検査を通過した版をGHCRから配布します。開発者のOSの標準パッケージとは独立して、Buildrootの構築、QEMUによる起動確認、テスト、静的解析に必要な版とパッチを管理します。利用者ごとにツールを選び直すのではなく、同じDockerfileと固定した入力に基づく環境を使うための仕組みです。

ビルド補助用のcompilerとライブラリーはimage内に用意します。target用のBootlin toolchainはimageへの同梱ではなく、Buildrootが選択した固定版をコンテナー内で取得・使用します。ツールの版、base imageのdigest、APT snapshot、追加パッチは[Dockerfile](msd-dev.Dockerfile)等で管理し、[CIの固定版監視](../docs/CI.md)の対象にします。環境を固定することと、生成物のbit単位での再現性を証明することは別です。

actionlintは、配布binaryに含まれるGo標準ライブラリーの版も管理するため、Dockerfileで固定したGoを使ってsourceからbuildします。

## イメージの選定

Debian trixie-slim を使います。Buildroot 自身の CI が Debian を使うこと、slim 版で不要なパッケージを減らせることが理由です。apt の参照先は snapshot 日時で固定します。Alpine は Bootlin toolchain が glibc バイナリーのため使わず、Arch Linux は arm64 イメージがないため対象外です。

QEMU 11.1.2 は署名付きソースからビルドします。`docker/qemu-signing-key.asc` の鍵指紋と tarball の署名をビルド時に検証し、`docker/qemu-patches/` のパッチを適用します。ASB 領域へのパッチにより、512 MiB の `raspi3ap` でも起動可能です。パッチの理由と上流への提出状況は `docker/qemu-patches/README.md` を参照してください。

## ビルドと実行

```sh
docker/msd-dev ensure
docker/msd-dev bash -lc 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

`ensure`は対応する入力タグが公開済みなら取得し、未公開ならローカルでbuildします。公開imageのpull・通信・検証が失敗したときには、別のimageへ切り替えて続行しません。公開状態にかかわらずsourceから構築したい場合は、`ensure`の代わりに`docker/msd-dev build`を使います。

QEMU は既定で `raspi3ap`（512 MiB）と `bcm2710-rpi-cm0.dtb` を使います。1 GiB の `raspi3b` と Pi 3 の DTB で確認する場合は、次のように実行します。

```sh
QEMU_MACHINE=raspi3b docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

`output/`、`dl/`、`.ccache/` はホスト側のリポジトリーに置き、コンテナーには bind mount します。`BR2_DL_DIR`、`BR2_CCACHE_DIR`、`OUTPUT_DIR` にリポジトリー外のパスを指定した場合も、そのパスを同じ位置に mount します。これらのデータはイメージには入りません。

Bootlin toolchain は x86_64 専用です。arm64 ホストでは開発用イメージを使った lint、QEMU 起動確認、テストを実行できますが、Buildroot のビルドは実行できません。

## CIの準備とキャッシュ

Buildrootのdefconfig、通常build、legal-info、QEMU、host回帰、コードのlintは、CIでも`docker/msd-dev`経由で固定した開発OCI内で実行します。target用はBuildrootが選択するBootlin toolchain、ビルド補助用はOCI内のtoolchainです。checkout・差分判定・cacheの保存/復元などの制御処理はrunner上で動きますが、runner側のcompilerで製品を構築しません。

CIの共通actionは最初に公開タグを調べます。公開済みなら毎回pullとattestation検証を行い、失敗時に未検証cacheへ逃がしません。未公開の場合だけ、OS・runner arch・入力タグ・形式版が完全一致するarchiveを復元します。load前にmetadata、サイズ、SHA-256、platformを確認し、load後にimage IDも照合します。これは破損検出であり、署名・source再現性の証明ではありません。

cacheがなければ従来どおり同じDockerfileをbuildし、512 MiB以下のarchiveを保存します。初回は独立jobが各々buildする可能性があります。GitHubのbranch/ref別scopeを超えてcacheを移す処理はありません。token・Docker認証設定・署名鍵・raw scanはcacheに入れません。

更新・init・hardware情報・data拡張・QEMUログ・電源断ログ・wrapperのhost回帰7組は、一つのOCI内で最大2組ずつ並列実行します。全組の終了状態と分離したログを保存し、一つでも失敗・timeoutならjobを失敗させます。TrivyとSBOM等の既存検査も維持します。[起動条件と検証記録](../docs/experiments/2026-11-03-ci-cache-and-parallel.md)を参照してください。

## rootless Docker での実行

`docker/msd-dev` は `docker info --format '{{.SecurityOptions}}'` の出力から rootless Docker を自動判定します。rootless の場合はコンテナー内の実行ユーザーを `0:0` にします。rootless Docker の user namespace ではコンテナー内の root がホストの実行ユーザーに対応するため、bind mount した作業ツリーにも書き込み可能です。通常の Docker ではホストの uid:gid で実行します。判定の上書きには `MSD_DEV_ROOTLESS=1` または `0` を指定します。両モードで `--cap-drop ALL` と `--security-opt no-new-privileges` が有効です。

公開タグの確認には Docker CLI 標準の `docker manifest inspect` を使うため、`ensure` に Docker Buildx plugin は不要です。rootless Docker を設定済みのホストでは、sudo なしでイメージの取得、ビルド、コンテナーの実行ができます。

## 配布イメージの取得と検証

公開イメージを取得するだけなら GitHub への認証は不要です。attestation の検証には、`gh auth login` または `GH_TOKEN` / `GITHUB_TOKEN` による `gh` の認証が必要です。`gh` が未認証の場合、通常は警告を出して検証を省略し、`MSD_DEV_REQUIRE_ATTESTATION=1` では失敗します。CI の `Ensure development image` は `GH_TOKEN` に `secrets.GITHUB_TOKEN` を渡し、job に `packages: read` と `attestations: read` を設定しています。

Devin Outposts の worker（Docker 29.8.2 の rootless、sudo なし、Docker Buildx plugin なし、`gh` 未認証、x86_64、12 スレッド）での、commit `dbe83fa` の検証結果です。ツリーに変更を加えず、`docker/msd-dev ensure` で公開イメージを取得しました。未認証の `gh` のため attestation 検証は警告付きで省略され、`MSD_DEV_REQUIRE_ATTESTATION=1` では設計どおり失敗する仕様です。actionlint、ShellCheck、`tests/check-pins/run.sh`、`tests/msd-update/run.sh`、`tests/msd-hwinfo/run.sh`、`tests/msd-data-grow/run.sh`、`tests/qemu-log-check/run.sh`、`tests/trivy-gate/run.sh`、`tests/msd-dev/run.sh` は成功しました。空の ccache で 12 スレッドを使った Buildroot のフルビルドは 3,199 秒（1 回）でした。`QEMU_MACHINE=raspi3ap` と `bcm2710-rpi-cm0.dtb` を使う `test-boot.sh` と `test-ab.sh` も成功し、生成物はすべて worker ユーザーの所有です。

commit `e9b3b3f` のツリーを変更せずに、Docker Buildx plugin がない環境で `docker/msd-dev build` を legacy builder で実行したところ、no-cache のビルドが 812 秒（1 回）で成功しました。そのイメージでは ShellCheck 0.11.0 と QEMU 11.1.2 が動作し、`tests/msd-dev/run.sh` の 21 件と `tests/check-pins/run.sh` の 26 件も成功しました。記載した時間は、いずれも単一回の実行結果です。

## GHCR 公開イメージ

公開イメージは `docker/msd-dev ensure` で用意できます。取得後のローカル名は `MSD_DEV_IMAGE` で指定でき、省略時は `msd-dev:local` です。`docker/msd-dev pull` は公開イメージを直接取得するコマンドです。

タグは `inputs-` と SHA-256 の先頭 16 桁で構成します。ハッシュ対象は `docker/msd-dev.Dockerfile`、`docker/debian.sources`、QEMU の署名鍵とパッチ、`.github/zizmor-requirements.txt` の内容とパスです。入力の内容が変わるとタグも変わります。

公開時には同じ multi-arch イメージに `sha-<commit>` と `latest` のタグも付け、SPDX SBOM と provenance の attestation を付けます。`ensure` は入力タグを `docker manifest inspect` で確認し、公開済みなら pull と attestation 検証を行います。タグが見つからない場合の処理はローカルビルドです。認証や通信などの検査エラー、pull の失敗、attestation 検証の失敗は、ローカルビルドへ切り替えずエラー扱いです。`gh` がない、または未認証の場合、通常の `pull` は警告を出して検証を省略します。`MSD_DEV_REQUIRE_ATTESTATION=1` を指定すると、`gh` の未導入または未認証で失敗します。CI ではこの設定が必須です。

`ghcr.io/uist1idrju3i/msd-dev` は、認証なしで pull できる公開パッケージです。毎週月曜に `latest` を検査し、検出事項があれば「開発用イメージの脆弱性」Issue を作成または更新します。検出事項がなくなった後の検査では、Issue にコメントして閉じます。

## 固定値の更新

`docker/msd-dev.Dockerfile` の `DEBIAN_SNAPSHOT` を更新するときは、snapshot.debian.org に存在する日時を選びます。固定版の更新確認では、snapshot の日時が 30 日を超えると更新ありとして通知します。

2026-11-12の更新では、apt 3.0.4とzlibの`+deb13u1`を両CPUで初めて収録した`20261107T075304Z`を選びました。QEMU builderと最終stageの両方を更新し、固定baseに残るaptもsnapshotから更新するためinstall対象に明示します。全packageのupgradeは行いません。[実験記録](../docs/experiments/2026-11-12-dev-image-snapshot.md)に全APT差分、変更履歴、署名付きindex、旧新のgate結果と未確認範囲を残します。監視はDockerfileから日付を読む既存方式を維持し、30日以内でも脆弱性がないとは扱いません。

QEMU を更新するときは、`QEMU_VERSION`、`QEMU_SHA256` と署名鍵の指紋を合わせて変更し、`docker/qemu-patches/README.md` の一覧と上流への提出状況も併せて更新してください。上流の最新安定版との差は固定版の更新確認で調べます。
ベースイメージの digest を変えるときは、`docker buildx imagetools inspect debian:trixie-slim` の結果と照合してください。

CI の実行環境の移行は後続の PR で行います。
