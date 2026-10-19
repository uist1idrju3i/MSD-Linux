# 開発用コンテナー

CI と同じ版に固定した lint ツールを使い、ホスト環境による差を抑えます。ホストの apt より新しい QEMU で、起動確認も実行できます。

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

## 固定値の更新

`docker/msd-dev.Dockerfile` の `DEBIAN_SNAPSHOT` を更新するときは、snapshot.debian.org に存在する日時を選びます。`QEMU_DEB_VERSION` はその snapshot の trixie-backports にある版へ合わせます。ベースイメージの digest を変えるときは、`docker buildx imagetools inspect debian:trixie-slim` の結果と照合してください。

GHCR への公開と CI の実行環境のイメージへの移行は、後続の PR で行います。
