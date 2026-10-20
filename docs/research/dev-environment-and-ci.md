# 開発環境と CI

この記録は、Buildroot をビルドする開発環境と CI の選定、依存関係の監視、既存の比較結果をまとめます。数値は記載した調査日・CI 実行の範囲に限り、実機性能や未実施の比較を示すものではありません。

## 開発用コンテナーの選定

公式イメージだけを比較しました。サイズは amd64 のベースイメージのおおよその値で、開発ツールを入れた後のイメージサイズではありません。

| ベース | サイズ | libc・対象アーキテクチャ | 評価 |
|---|---:|---|---|
| Debian trixie-slim | 約29.8 MB | glibc、amd64 と arm64 | Buildroot 自身の CI と同じ Debian 系で、両アーキテクチャを使えます。snapshot を固定し、trixie-backports の QEMU `1:11.0.2+ds-2~bpo13+1` を使うため採用しました。 |
| Ubuntu 26.04 | 約42.1 MB | glibc | apt の QEMU は 10.2.1 です。 |
| Arch Linux `base-devel` | 約308.6 MB | amd64 のみ | arm64 イメージがないため対象外です。 |
| Alpine 3.23 | 約3.8 MB | musl | Bootlin toolchain は glibc バイナリーのため対象外です。 |

Debian で使う QEMU 版は trixie-backports の Packages index にあるバイナリーパッケージ版を基準にします。`sources.debian.org` のソース一覧には `11.1.2~bpo13` と表示されましたが、Packages index の版は `1:11.0.2+ds-2~bpo13+1` です。

## 開発イメージと CI の方針

- 開発イメージは GHCR で公開します。CI とローカルの lint・QEMU 起動確認に必要なツールはイメージに含め、CI で apt にフォールバックしません。
- SBOM と provenance の attestation には GitHub 公式の `actions/attest-*` を使い、許可する action はリポジトリーの allowlist で管理します。第三者 action で行っていた処理は、可能なものを CLI または `docker run` に置き換えました。hadolint の起動失敗を避けるため、lint は digest 固定イメージを直接実行します。
- `GITHUB_TOKEN` で作った bot の pull request では必須 CI が起動しないため、lock file と bot pull request による更新方式は採用しませんでした。
- PR #53 で、内容から `inputs-<hash>` タグを作り、GitHub CLI の `gh attestation verify` で公開イメージを検証する方式を採用しました。

actionlint v1.7.12 の公式配布バイナリーは Go 1.26.1 でビルドされており、Trivy 0.76.0 の検査で修正可能な HIGH の標準ライブラリー脆弱性が 23 件見つかりました。そのため開発イメージでは actionlint をソースからビルドし、`golang:1.27.2-trixie` を使います。zizmor の仮想環境に含まれていた pip 25.1.1 は実行時に使わないため削除します。

## 依存関係の鮮度

2026-10-19 の調査では、開発イメージのベース digest を最新と確認しました。apt パッケージ 250 件は、配信中の trixie、security、backports の各 index に対して更新可能なものが 0 件でした。QEMU は trixie-backports の `1:11.0.2+ds-2~bpo13+1` に対し、upstream と Debian sid は 11.1.2 です。ShellCheck 0.11.0、zizmor 1.31.1、hadolint 2.15.1 は調査時点の最新版です。

更新の監視は次のように分担します。

- Dependabot の Docker ecosystem は `docker/msd-dev.Dockerfile` を監視します。設定の `dockerfile|containerfile` filename regex がこの名前に一致します。
- Dependabot の pip ecosystem は zizmor の requirements を監視します。
- `check-pins.py` は Dockerfile の ARG で固定するツール、Trivy、Go、QEMU の upstream 版、Debian snapshot の経過日数を確認します。snapshot が 30 日を超えると更新ありとして扱います。

## ビルド結果の比較

ローカルの Buildroot イメージと CI 成果物を照合した一回の比較では、rootfs に含まれる 2,174 個のパスが一致し、`Image` は両方とも 26,380,800 bytes でした。一方、`.config` の `CONFIG_RUSTC_VERSION` は CI が `109900`、ローカルが `0` でした。

この結果は**予備的**です。同一性の範囲と再現条件をそろえた正式な実験記録は未作成で、第3段階の PR で記録する予定です。差分がある `.config` の意味もこの比較だけでは判断しません。

## CI ビルド時間

CI 実行 [39308965520](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/39308965520) で観測した**予備的な値**です。

| 項目 | 観測値 |
|---|---:|
| build job の所要時間 | 約23.5分 |
| `make` | 1,267秒、job 時間の約90% |
| QEMU A/B 起動 | 約15秒、約14秒 |
| 成果物の操作 | 約34秒、約24秒 |
| ccache hit rate | 94.15%（統計をリセットせずに数えた累計で、この実行だけの値ではない） |
| `build-time.log` の Linux | 475秒 |
| `build-time.log` の host-ccache | 73秒 |
| `build-time.log` の host-zstd | 43秒 |
| `build-time.log` の host-python3 | 37秒 |

Buildroot の package は順次ビルドされるため、`BR2_PER_PACKAGE_DIRECTORIES` は候補ですが、効果は未測定です。registry cache、変更検知、cache の分割、job 分割、150 分の timeout も見直し候補です。有料の上位 runner は採用しません。候補の採否や所要時間の短縮効果は未確認で、上記一回の CI 実行から一般化しません。

## Bootlin toolchain

Buildroot 2026.08.x が選択する aarch64 glibc stable toolchain は Bootlin 2025.08-1 で、GCC 14.3.0、binutils 2.43.1、glibc 2.41 です。Bootlin の最新 stable 2026.08-1 は GCC 15.3.0、binutils 2.45.1、glibc 2.44 ですが、Buildroot 2026.08.x からは選択できず、Buildroot master でのみ選択できます。GCC 16.2.0 の bleeding-edge 2026.08-1 は使いません。

Buildroot master は使わず、新しい Bootlin toolchain は安定版 Buildroot branch が提供した場合にのみ追従します。`check-pins.py` はその間の状態を `Buildroot 安定版待ち` として表示し、安定版 branch で選択可能になるまで更新対象にしません。Buildroot point release の監視では、系列名だけの最初の tag も初回リリースとして扱います。

開発イメージに入る Debian の host GCC 14.2 は host tools をビルドするためのものです。target toolchain は Bootlin が提供するため、host GCC の更新だけでは target に利点がありません。

## QEMU の範囲と予備的な結果

この調査時点の `main` は backports の QEMU 11.0.2 を使います。QEMU 11.1.2 のソースビルドは PR #55 の提案であり、`main` の現行版ではありません。

QEMU の `raspi3b` machine は 4 基の Cortex-A53 と 1 GiB RAM、`raspi3ap` は 4 基の Cortex-A53 と 512 MiB RAM です。GPIO、I2C、SPI0、SD host、DWC2 USB、25 C 固定の thermal sensor、mailbox/property、RNG、timer、CPRMAN、power management がモデル化されています。mailbox/property の clock set は未実装で、throttled の値は固定です。watchdog register write はログに記録します。RSTC reset は実装済みです。

次の機能はモデル化されていません。

- ST7789 LCD、TCA8418、M5IOE1
- GPIO6 の power-fail input
- GPU firmware と `tryboot`
- 実際の SD timing、wear、電源断挙動

パッチ適用前の `raspi3ap` の起動失敗は、Linux の `bcm2835-power` probe が読む ASB address `0x3f00a000` がモデル化されていないことによります。`raspi3b` は 1 GiB RAM がこの穴に alias するため起動できますが、`raspi3ap` では同期 external abort になります。この差を扱う QEMU の `create_unimp` パッチは、PR #55 で `docker/qemu-patches/` に追加されました。PR #61 以降、CI の既定 machine は `raspi3ap` です。

TCG plugin は guest の実行を測るもので、ハードウェアモデルを追加しません。これまでの起動結果は**単一回の予備的な実行**です。条件を固定した formal experiment record は未作成であり、実機の周辺機能・時間・SD 特性の検証結果ではありません。

## 参照

- ベースイメージ: [Debian](https://hub.docker.com/_/debian)、[Ubuntu](https://hub.docker.com/_/ubuntu)、[Arch Linux](https://hub.docker.com/r/archlinux/archlinux)、[Alpine](https://hub.docker.com/_/alpine)
- [Buildroot 2026.08 CI 設定](https://gitlab.com/buildroot.org/buildroot/-/blob/2026.08/.gitlab-ci.yml)、[trixie-backports Packages index](https://packages.debian.org/trixie-backports/qemu-system-arm)、[Debian QEMU source listing](https://sources.debian.org/src/qemu/)
- [actionlint v1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12)、[Go downloads](https://go.dev/dl/)、[official Go image](https://hub.docker.com/_/golang)、[Trivy v0.76.0](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0)
- [Bootlin aarch64 toolchains](https://toolchains.bootlin.com/releases_aarch64.html)、[Buildroot 2026.08 Bootlin options](https://gitlab.com/buildroot.org/buildroot/-/raw/2026.08/toolchain/toolchain-external/toolchain-external-bootlin/Config.in.options)
- [QEMU Raspberry Pi machine models](https://qemu.readthedocs.io/en/v11.1.2/system/arm/raspi.html)、[PR #53](https://github.com/uist1idrju3i/MSD-Linux/pull/53)、[PR #54](https://github.com/uist1idrju3i/MSD-Linux/pull/54)、[PR #55](https://github.com/uist1idrju3i/MSD-Linux/pull/55)
- [開発用コンテナーの設定](../../docker/README.md)、[CI の説明](../CI.md)、[開発用ビルド手順](../BUILD.md)
- 実装: [Dockerfile](../../docker/msd-dev.Dockerfile)、[launcher](../../docker/msd-dev)、[Dependabot 設定](../../.github/dependabot.yml)、[pin checker](../../.github/scripts/check-pins.py)、[lint workflow](../../.github/workflows/lint.yml)、[pin check workflow](../../.github/workflows/pins-check.yml)
