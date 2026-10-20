# 開発用コンテナー

CI と同じ版に固定した lint ツールを使い、ホスト環境による差を抑えます。ホストの apt より新しい QEMU で、起動確認も実行できます。

actionlint は、公式配布バイナリーに修正可能な Go 標準ライブラリーの脆弱性が含まれていたため、Dockerfile で固定した最新の Go でソースからビルドします。

## イメージの選定

Debian trixie-slim を使います。Buildroot 自身の CI が Debian を使うこと、slim 版で不要なパッケージを減らせること、backports から QEMU を導入できることが理由です。apt の参照先は snapshot 日時で固定します。Alpine は Bootlin toolchain が glibc バイナリーのため使わず、Arch Linux は arm64 イメージがないため対象外です。

## ビルドと実行

```sh
docker/msd-dev build
docker/msd-dev bash -lc 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output msd_cardputerzero_defconfig && make -C output'
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

`output/`、`dl/`、`.ccache/` はホスト側のリポジトリーに置き、コンテナーには bind mount します。`BR2_DL_DIR`、`BR2_CCACHE_DIR`、`OUTPUT_DIR` にリポジトリー外のパスを指定した場合も、そのパスを同じ位置に mount します。これらのデータはイメージには入りません。

Bootlin toolchain は x86_64 専用です。arm64 ホストでは lint、QEMU 起動確認、ホストテストを実行できますが、Buildroot のビルドは実行できません。

## GHCR 公開イメージ

公開イメージは `docker/msd-dev pull` で取得できます。取得後のローカル名は `MSD_DEV_IMAGE` で指定でき、省略時は `msd-dev:local` です。

タグは `inputs-` と SHA-256 の先頭 16 桁で構成します。ハッシュ対象は `docker/msd-dev.Dockerfile`、`docker/debian.sources`、`.github/zizmor-requirements.txt` の内容とパスです。入力の内容が変わるとタグも変わります。

公開時には同じ multi-arch イメージに `sha-<commit>` と `latest` のタグも付け、SPDX SBOM と provenance の attestation を付けます。GitHub CLI がある環境では `docker/msd-dev pull` が attestation を検証し、検証に失敗すると取得処理も失敗します。GitHub CLI がない場合は、検証省略の警告を出して取得を続ける仕様です。

最初の公開直後は GHCR パッケージが非公開のため、所有者が公開設定に変更するまで取得できません。毎週月曜に `latest` を検査し、検出事項があれば「開発用イメージの脆弱性」Issue を作成または更新します。検出事項がなくなった後の検査では、Issue にコメントして閉じます。

## 固定値の更新

`docker/msd-dev.Dockerfile` の `DEBIAN_SNAPSHOT` を更新するときは、snapshot.debian.org に存在する日時を選びます。`QEMU_DEB_VERSION` はその snapshot の trixie-backports にある版へ合わせます。ベースイメージの digest を変えるときは、`docker buildx imagetools inspect debian:trixie-slim` の結果と照合してください。
固定版の更新確認では、Debian snapshot の日時が 30 日を超えると更新ありとして通知します。
QEMU の最新上流版も参考情報として表示し、backports の版との比較に使います。

CI の実行環境の移行は後続の PR で行います。
