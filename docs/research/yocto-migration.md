# Yocto Project への移行検討（Buildroot との比較）

CardputerZero の現行構成は Buildroot（BR2_EXTERNAL・msd_cardputerzero_defconfig・SquashFS+dm-verity・A/B tryboot・BusyBox init・msd-dev+QEMU ゲート）で成立している。Yocto Project（OpenEmbedded/bitbake）への移行の pros/cons を検討した。

**結論: 移行の利点（パッケージ管理・レイヤー・sstate・SBOM/CVE・LTS 4 年）は本プロジェクトの要件（固定 rootfs・最小サイズ・起動最速・既存の QEMU 検証基盤）では効果が薄く、コスト（bitbake の複雑さ・長いビルド・検証基盤の再実装・サイズ増）が大きい。現行 Buildroot を維持する。**

## Yocto の現在

- 最新 LTS: Wrynose 6.0（2026-04 リリース、2030-04 までの 4 年 LTS）。kernel 6.18 LTS、GCC 15.2、glibc 2.43、`sbom-cve-check` 統合、SPDX 3.0 出力。【一次】
- 前 LTS: Scarthgap 5.0（2028-04 まで）。
- モデル: 層（layer）+ レシピ + イメージレシピ。パッケージ（rpm/ipk/deb）単位で rootfs を構成し、`sstate-cache` と `hashequiv` で増分・再現ビルドを高速化。

## Buildroot（現行）と Yocto の比較

| 軸 | Buildroot（現行） | Yocto |
|---|---|---|
| 生成物 | 固定機能の rootfs イメージ。バイナリパッケージ管理なし | パッケージ化したディストリビューション。個別更新・版管理が可能 |
| 構成 | `defconfig` + fragment + overlay で単純 | layer/recipe/bbclass の多層。表現力高いが複雑 |
| ビルド | 単純で速い。設定変更で全面再ビルドになる場面がある | 重いが sstate/hashequiv で増分ビルドが効く |
| エコシステム | 一つの tree に全パッケージ。質が均一 | 多数の meta-layer（meta-raspberrypi・meta-mender 等）。品質は層ごとに差 |
| 学習 | 浅い（make+Kconfig） | 急（bitbake の構文・多ファイル構成） |
| ライセンス/監査 | 基本的 | archiver・SBOM・`sbom-cve-check` など製品コンプライアンス向けが充実 |
| 保守周期 | Buildroot 安定系を随時追従 | LTS 4 年。アップグレードガイド付き |

## Pros（Yocto にした場合）

1. **パッケージ管理**: rootfs を ipk/rpm で構成でき、部分更新や依存解決が容易。ただし MSD は squashfs+verity の固定イメージを前提にしており、実行時の個別パッケージ更新は A/B イメージ更新モデルと矛盾するため効果が薄い。
2. **sstate/hashequiv**: 設定変更後の増分ビルドが速い。現行 Buildroot は config 変更で全面再ビルドになる場面があり、kernel sweep のような反復作業では利点がある（sweep は別途並列化と tree 複製で対処済み）。
3. **meta-raspberrypi / meta-mender / RAUC 層**: RasPi 系 BSP と A/B 更新フレームワークが既成品としてある。ただし MSD は独自の p1 selector+tryboot+raw A/B payload+verity 構成で、フレームワークの想定更新モデルとは一致しない。逆に今の設計を捨てることになる。
4. **SBOM/CVE**: CRA 対応を意識した SPDX 生成と `sbom-cve-check` が統合済み。ライセンスアーカイブもクラス一発。監査要件が増える場合に強い。
5. **長期 LTS**: Wrynose は 2030-04 まで。Buildroot は安定系列への追従を自分で管理している（pins-check + 週次監視で運用できている）。

## Cons（MSD/Linux にとって）

1. **rootfs モデルの不一致**: Yocto は「パッケージを配る distro」を作る。MSD の「検証済み固定イメージを A/B で配る」設計では、パッケージ管理は不要かつイメージを増やす方向になる。squashfs+verity のまま作るには package-management を切って distoless 相当に寄せる設定が必要で、Yocto の強みを捨てる。
2. **ビルドコストと容量**: bitbake+sstate は初回ビルドが Buildroot より重い。CI 時間と成果物容量の増加は「最小で最速」方針に反する。
3. **検証基盤の再実装**: test-qemu.sh/test-boot.sh/sweep/pins-check/defconfig 系の QEMU ゲートは Buildroot output 前提で作られている。Yocto の deploy 出力と MACHINE/layer 構成に全面移植が必要。
4. **再現性の作り直し**: 現行は defconfig+固定 URL/SHA256+Docker digest で再現性を構成している。Yocto では layer のバージョン pin・premirror・sstate 管理を新たに設計する必要がある。
5. **複雑さ**: bitbake の多層構成は、単一 tree の Buildroot に比べて監査・レビュー・CI 再現のコストが大きい。AGENTS.md の「シンプルで監査可能な構成」と相性が悪い。

## 判定

- **移行しない**。Yocto の利点（パッケージ管理・部分更新・SBOM/LTS）が MSD の固定イメージ方式と食い合わず、検証基盤の作り直しと引き換えになるため。
- Buildroot 維持で補う部分: sstate 相当の速い増分は現行の差分ビルド+`--jobs` で賄う、CVE 追跡は pins-check・Dependabot・Trivy で代替、LTS は Buildroot 安定系列を pins で固定して追従。
- Yocto を再検討する条件: 製品が「ランタイムに個別パッケージを配る distro」モデルに変わるか、CRA 向けの正式 SBOM が必須になった場合。

## 出典

- [Yocto Releases（wiki）](https://wiki.yoctoproject.org/wiki/Releases)【一次】Wrynose 6.0 LTS（2030-04）・Scarthgap 5.0（2028-04）
- [Yocto Project 6.0 "Wrynose"](https://www.yoctoproject.org/blog/2026/05/13/yocto-project-6-0-wrynose-is-here/)【一次】kernel 6.18・GCC 15.2・sbom-cve-check・SPDX 3.0
- [Bootlin「Buildroot vs. Yocto」比較資料](https://bootlin.com/pub/conferences/2022/elc/petazzoni-buildroot-whats-new/petazzoni-buildroot-whats-new.pdf)【一次】distro vs 固定 rootfs、sstate、層・品質・学習コストの整理
- [Bootlin「Buildroot vs. OpenEmbedded/Yocto」](https://bootlin.com/pub/conferences/2016/elc/belloni-petazzoni-buildroot-oe/belloni-petazzoni-buildroot-oe.pdf)【一次】設計思想・BR2_EXTERNAL vs meta-layer
