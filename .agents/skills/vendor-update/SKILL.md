---
name: vendor-update
description: Review and update MSD-Linux dependencies, read their complete change history, and compare build, boot, license, and security results.
---

# vendor-update（依存関係の更新）

依存を追加・更新するときは、対象の変更履歴とライセンスを確認し、更新前後の結果を比べます。Dependabot が作成した PR も同じ手順で確認してから、人間がマージします。

## 対象と変更履歴の参照先

| 依存 | 現在値の確認方法 | 変更履歴の参照先 |
|---|---|---|
| Buildroot submodule | `git -C vendor/buildroot rev-parse HEAD` と `.gitmodules` の `2026.08.x` | `vendor/buildroot/CHANGES`、リリースのお知らせ、`git -C vendor/buildroot log <old>..<new> -- package/<使用中のパッケージ> linux boot toolchain`。使用中のパッケージ版や CVE 修正も確認する |
| Raspberry Pi Linux | `configs/msd_cardputerzero_defconfig` のカスタム tarball URL、`.github/workflows/pins-check.yml` | `rpi-6.18.y` との GitHub compare、間の release/commit、`board/cardputerzero/linux.fragment` の Kconfig シンボルの改名・削除 |
| rpi-firmware | defconfig の `BR2_PACKAGE_RPI_FIRMWARE`、`vendor/buildroot/package/rpi-firmware/rpi-firmware.mk` と `.hash` | Raspberry Pi firmware の変更履歴と、Buildroot の package 更新履歴 |
| Bootlin toolchain | defconfig の `BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_*`、`vendor/buildroot/toolchain/toolchain-external/toolchain-external-bootlin/toolchain-external-bootlin.mk` と `.hash` | Bootlin toolchain のリリース情報と Buildroot の package 更新履歴 |
| M5Stack overlays | `git -C vendor/m5stack-linux-dtoverlays rev-parse HEAD` | submodule の README、release、`git -C vendor/m5stack-linux-dtoverlays log <old>..<new>`。CardputerZero の設定とドライバーも照合する |
| GitHub Actions | workflow の `uses:` にある commit SHA と `# vX.Y.Z` | 各 action の release と manifest。現在の major だけでなく、後続 major も確認し、`runs.using` の Node.js runtime がサポート対象か調べる |
| GitHub-hosted runner | workflow の `runs-on`。現在は `ubuntu-26.04` | `actions/runner-images` のリリースと該当イメージの README。インストール済みツールの版も確認する |
| apt ホスト依存 | `.github/workflows/build.yml` の `apt-get install` | Ubuntu のリリース情報と runner image の README。ビルドに必要なパッケージとその版を確認する |
| yomiyasu | `git -C vendor/yomiyasu rev-parse HEAD` | nanaism/yomiyasu の release と変更履歴 |
| actionlint / ShellCheck | `.github/workflows/lint.yml` にある版と archive SHA-256。現在は actionlint `1.7.12`、ShellCheck `0.11.0` | 各 release と公開 checksum。Dependabot の対象外なので、版や hash は手動で更新する |
| zizmor | `.github/zizmor-requirements.txt` と `.github/dependabot.yml` の `/.github` pip entry。現在は `1.31.1` | PyPI の release metadata と wheel/sdist の hash。`--offline` 監査を維持し、受け入れる指摘は `.github/zizmor.yml` に理由を一行で記録する。pip Dependabot が週次で版を確認する |
| kernel-hardening-checker | `.github/workflows/build.yml` にある tag と commit SHA。現在は `v0.6.17.1` / `afc376f2a935994793343cfeb05953583cc30191` | upstream release と tag の commit。workflow の SHA assertion も更新する |
| NVD mirror | `.github/workflows/security.yml` と `support/scripts/cve-check` の呼び出し | mirror の更新方式。版ではなく週次データを ISO week cache に保存し、shallow fetch/reset と `--no-nvd-update` で追加 download を避ける動作を保つ |

## 更新手順

1. 作業ブランチで、更新前の基準を記録します。CI の build/QEMU 結果、`tests/msd-update/run.sh`、成果物のサイズ、カーネル設定、legal-info、SBOM/VEX の CVE 件数を残します。
2. 更新する版の間にある変更履歴をすべて読みます。履歴が shallow clone に含まれない場合は必要な範囲を fetch するか、upstream の compare/release ページで補います。`.gitmodules` の `shallow = true` は維持します。
3. 変更点を次の四つに分けて記録します。新機能は安定性、セキュリティ、速度の順に採否と理由を判断します。
   - 破壊的な変更と、こちらで必要な対応
   - セキュリティ修正と対象範囲
   - 使える新機能と採否の理由
   - ライセンスまたはライセンス条件の変更
4. 更新します。submodule は `git -C vendor/<name> fetch --depth 1 origin <tag-or-commit>` の後に `git -C vendor/<name> checkout FETCH_HEAD` を使い、`.gitmodules` の shallow 設定を残します。GitHub Actions は full commit SHA と `# vX.Y.Z` を併記します。Security tool の版・hash・workflow pin も同じ変更でそろえます。
5. 更新後に回帰テストを行い、更新前の基準と比較します。
   - CI の Buildroot build と QEMU の `test-boot.sh`、`test-ab.sh`
   - `tests/msd-update/run.sh`
   - `output/images/Image`、`rootfs.squashfs`、`sdcard.img` のサイズ
   - QEMU 起動から ready marker までの時間
   - kernel `.config` の差分
   - `make legal-info` の `manifest.csv` とライセンス差分
   - SBOM/VEX の exploitable CVE 件数
6. PR 本文に、依存ごとの旧版 → 新版、変更履歴リンク、四分類の記録、回帰テストの比較結果を記載します。Dependabot PR にも同じ確認を行い、結果を確認した後に人間がマージします。
