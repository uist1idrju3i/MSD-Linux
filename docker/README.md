# 開発用コンテナー

CI と同じ版に固定した lint ツールを使い、ホスト環境による差を抑えます。ホストの apt より新しい QEMU で、起動確認も実行できます。

actionlint は、公式配布バイナリーに修正可能な Go 標準ライブラリーの脆弱性が含まれていたため、Dockerfile で固定した最新の Go でソースからビルドします。

## イメージの選定

Debian trixie-slim を使います。Buildroot 自身の CI が Debian を使うこと、slim 版で不要なパッケージを減らせることが理由です。apt の参照先は snapshot 日時で固定します。Alpine は Bootlin toolchain が glibc バイナリーのため使わず、Arch Linux は arm64 イメージがないため対象外です。

QEMU 11.1.2 は署名付きソースからビルドします。`docker/qemu-signing-key.asc` の鍵指紋と tarball の署名をビルド時に検証し、`docker/qemu-patches/` のパッチを適用します。ASB 領域へのパッチにより、512 MiB の `raspi3ap` でも起動可能です。パッチの理由と上流への提出状況は `docker/qemu-patches/README.md` を参照してください。

## ビルドと実行

```sh
docker/msd-dev ensure
docker/msd-dev build
docker/msd-dev bash -lc 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

QEMU は既定で `raspi3b`（1 GiB）を使います。CM0 の DTB で `raspi3ap`（512 MiB）を確認する場合は、次のように実行します。

```sh
QEMU_MACHINE=raspi3ap DTB_IMAGE=output/images/bcm2710-rpi-cm0.dtb \
  docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

`output/`、`dl/`、`.ccache/` はホスト側のリポジトリーに置き、コンテナーには bind mount します。`BR2_DL_DIR`、`BR2_CCACHE_DIR`、`OUTPUT_DIR` にリポジトリー外のパスを指定した場合も、そのパスを同じ位置に mount します。これらのデータはイメージには入りません。

Bootlin toolchain は x86_64 専用です。arm64 ホストでは開発用イメージを使った lint、QEMU 起動確認、テストを実行できますが、Buildroot のビルドは実行できません。

## GHCR 公開イメージ

公開イメージは `docker/msd-dev ensure` で用意できます。取得後のローカル名は `MSD_DEV_IMAGE` で指定でき、省略時は `msd-dev:local` です。`docker/msd-dev pull` は公開イメージを直接取得するコマンドです。

タグは `inputs-` と SHA-256 の先頭 16 桁で構成します。ハッシュ対象は `docker/msd-dev.Dockerfile`、`docker/debian.sources`、QEMU の署名鍵とパッチ、`.github/zizmor-requirements.txt` の内容とパスです。入力の内容が変わるとタグも変わります。

公開時には同じ multi-arch イメージに `sha-<commit>` と `latest` のタグも付け、SPDX SBOM と provenance の attestation を付けます。`ensure` は入力タグを `imagetools inspect` で確認し、公開済みなら pull と attestation 検証を行います。タグが見つからない場合の処理はローカルビルドです。認証や通信など、それ以外の検査エラー、pull の失敗、attestation 検証の失敗ではビルドせずに終了します。通常の `pull` は GitHub CLI がない場合に警告して検証を省略しますが、`MSD_DEV_REQUIRE_ATTESTATION=1` を指定すると GitHub CLI がない場合も失敗します。CI ではこの設定が必須です。

最初の公開直後は GHCR パッケージが非公開のため、所有者が公開設定に変更するまで取得できません。毎週月曜に `latest` を検査し、検出事項があれば「開発用イメージの脆弱性」Issue を作成または更新します。検出事項がなくなった後の検査では、Issue にコメントして閉じます。

## 固定値の更新

`docker/msd-dev.Dockerfile` の `DEBIAN_SNAPSHOT` を更新するときは、snapshot.debian.org に存在する日時を選びます。固定版の更新確認では、snapshot の日時が 30 日を超えると更新ありとして通知します。
QEMU を更新するときは、`QEMU_VERSION`、`QEMU_SHA256` と署名鍵の指紋を合わせて変更し、`docker/qemu-patches/README.md` の一覧と上流への提出状況も併せて更新してください。上流の最新安定版との差は固定版の更新確認で調べます。
ベースイメージの digest を変えるときは、`docker buildx imagetools inspect debian:trixie-slim` の結果と照合してください。

CI の実行環境の移行は後続の PR で行います。
