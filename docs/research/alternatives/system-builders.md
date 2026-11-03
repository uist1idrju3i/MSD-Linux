# PTXdist・Nix・Debianによる構築の再検討

[比較の索引](README.md) / [構築基盤と開発・CIの全体比較](development.md)

## 比較する単位

未リリースのため構築基盤の変更も候補にします。ただし、rootfsを生成できることと、CardputerZeroのboot firmware・BSP・microSD配置・署名付き更新・電源断復旧まで揃うことは別です。下記は取得した一次資料に基づく比較であり、代替構成のbuild・実行は本リポジトリでは試していません。

| 候補 | 資料から確認した主な機能 | 取り込める利点 | 移行で引き受ける費用 |
|---|---|---|---|
| 現行Buildroot | 選択したpackageと外部BSPからimageを構築する。固定値・SBOM・生成物は既存監査を参照 | 既存recipe・QEMU・更新試験を基準に実験できる | 独自BSP・更新・security policyの保守。package選択だけでは権限分離を提供しない |
| PTXdist | Kconfig、Make/Bash系のrecipe、BSPとlayer、toolchainの選定、license追跡、code signingの手順 | 組み込みBSPの分離、runtime依存とlicenseの扱い、read-only製品の構成を比較できる | 現行recipe・image配置・外部toolchain・kernel・M5 module・CIを移植。RAUC等との統合は別 |
| Nixをhost側に導入 | build入力・依存closure・store、複数versionの共存 | 開発toolやCI入力を固定する実験候補 | Nix daemon/store/cache・trust・GC・sandboxを運用する。既存OCIと二重管理にしない設計が必要 |
| NixOSへtargetを変更 | 宣言的なsystem構成、generationの切替とrollback、service構成 | system単位の構築・切替・policyをまとめる案 | targetのstore、boot integration、容量・RAM、BSP、mutable data、更新の信頼根を再設計 |
| Debian系rootfsを縮小構築 | APT/dpkgのpackage、mmdebstrapのvariant・mode・hook・出力形式 | 配布package、security更新、豊富なtoolを利用する別基盤 | 採用packageのsupport、依存closure、image化、boot、製品policy、A/B更新と共有dataを統合 |

YoctoとAlpine等も候補から除外しません。既存の[Yocto検討](../yocto-migration/README.md)と[libc比較](libc.md)にある実験条件を引き継ぎ、別基盤の一般的な機能を過去の本機試験へ加算しません。

## PTXdist: 組み込み基盤として比較する

[公式download](https://www.ptxdist.org/pages/download.html)は`2026.10.0`を最新公開版とします。一方、取得したonline manualは`2026.10.0-00072-g25578c250315`で、公開版そのものではありません。資料のoptionや手順を公開版の既定値と決めつけません。

[開発manual](https://www.ptxdist.org/doc/dev_manual.html)は、recipe、patch、binary-only file、license情報、layer、Kconfig差分、code signingを扱います。[日常作業のmanual](https://www.ptxdist.org/doc/daily_work_section.html)ではtoolchain・PTXdistを含むcontainer、prebuilt archive、runtime依存等の運用を分けています。Buildrootの`legal-info`やSBOMと同じ内容を全て自動生成するという確認にはしていません。

同じPengutronixの[DistroKit](https://www.pengutronix.de/en/software/distrokit.html)は、Raspberry Piを含むARM Cortex-A board向けの最小BSPを案内します。ただし、これだけではCM0・CardputerZeroの公式BSPや起動実績にはなりません。RAUC・bareboxを使う案も、CM0 firmwareのboot選択・tryboot・health・rollbackの統合と電源断試験を別に扱います。

取得した`COPYING`はbuild system自体をGPL version 2とし、管理するsoftwareのlicenseを変えないと明示します。BSP、toolchain、kernel、配布firmware、runtimeのlicenseや再配布条件は個別のままです。選定前に、現行全67構成要素との対応、sourceの固定・hash、SBOM、license、再現性、cacheと失敗報告を比較します。

**再検討案**: 全面移行を先に確定せず、現行の最小CLI image・署名更新に相当する一つの独立BSPを作る実験候補とします。buildの成否だけでなく、依存数、保守差分、CI費用、生成物の追跡性、起動・更新失敗時の復旧が改善することを採用条件にします。

## NixとNixOS: hostの固定化とtarget OSを分ける

取得した[NixOS stable manual](https://nixos.org/manual/nixos/stable/)は`26.05`、[Nix stable manual](https://nix.dev/manual/nix/stable/)は`2.34.9`です。NixOSのchannelとNix自体の版は別です。GitHub Release APIで最新版を取得できなくても、release停止や古い版しかない証拠とはしません。

NixOSの`system.stateVersion`はstatefulな設定の互換性に関係する値であり、OSの更新番号ではありません。channelの更新に合わせて機械的に増やさず、必要なstate移行を判断します。generationのrollbackも、共有databaseや`/var`等の変更を元に戻す保証ではありません。GCが旧closureを削除する条件、復旧用generationを保持する方針、microSD容量を含めて比較します。

hostの再現可能なtool環境にNixを利用する案と、端末をNixOSへ移行する案を混ぜません。前者ではOCIと入力固定をどう分担するか、後者ではboot chain・BSP・署名付き配信・信頼するsubstituter・cache鍵・offline復旧を新たに設計します。storeやbuild式に秘密値を入れず、world-readableになり得る構築出力と、device固有の秘密・永続dataを分けます。

NixOS/nixpkgsの取得した`COPYING`はMIT系、Nixの`COPYING`はLGPL-2.1の本文です。これは生成したsystemの全packageを同じlicenseにする意味ではありません。安定channelへの更新とpackageごとのsecurity supportも別です。取得manualは安定channelの保守範囲を説明しますが、全packageのbackportや将来の期限を独自に保証しません。

**再検討案**: hostのtool固定化を小さな実験候補にします。target OSの採用は、storeの容量・RAM・boot・更新の責務を含めて別評価とし、generationがあるだけで現行A/B・署名・anti-rollbackを不要としません。

## Debian: 「最小」のpackage集合を明示する

[Debianのrelease案内](https://www.debian.org/releases/)は、取得時のstableを`13.7`、codenameを`trixie`とします。[trixieの案内](https://www.debian.org/releases/trixie/)は通常supportを2028-08-09まで、LTSを2030-06-30までとし、LTSで対象architectureが減ると説明します。全package・全architectureが同じ条件で保守される保証ではありません。testingやunstableの版が新しいことだけで、製品のsecurity対応が優位とは判断しません。

[mmdebstrapのDebian manual](https://manpages.debian.org/testing/mmdebstrap/mmdebstrap.1.en.html)は、APTを用いてrootfsを構築し、variant、実行mode、hook、出力形式を選べます。

- `essential`、`apt`、`minbase`等はpackage集合が異なります。既定は`debootstrap`で、「常に最小」「常にAPTなし」とはしません。依存packageも含めて決まります。
- `unshare`等を使う構築と、最終imageでserviceを非root実行することは別です。hostのuser namespaceやcross実行の条件も確認します。
- `tar`、SquashFS、ext2/ext4等の出力があっても、microSD全体のpartition、CM0のboot file、BSP、A/B状態管理は別途必要です。
- repositoryの認証鍵・`signed-by`、suite、snapshot時点、package版とhashを固定します。rollingな`stable`参照だけでは同じrootfsを再生成できません。
- hookは構築中の任意処理です。実行主体・入力・network・秘密へのアクセスを限定し、`SOURCE_DATE_EPOCH`に加え、host由来のhostname・resolver等も再現性の対象にします。

Debian全体に一つのlicenseを付けず、採用する各packageのcopyrightとsource提供条件を確認します。今回、mmdebstrap自体のlicenseを取得しようとしたURLは404でした。manualの取得をlicense確認の成功へ読み替えず、採用前の確認事項に残します。

**再検討案**: 開発・診断機能が必要な構成として、最小variantと実際に必要なtoolを固定した実験候補です。製品のrootfsをAPTで直接更新する方式と、Debian由来rootfsを不変の署名付きimageとしてA/B配信する方式は別に比較します。後者でも共有dataのschema移行、rollback、device権限とsecurity policyは必要です。

## 共通の採用試験

1. 同じBSP、kernelの意図した機能、user向け機能をそろえ、差を表へ残す。
2. source・toolchain・構築入力・network依存・SBOM・licenseとcacheの条件を固定する。
3. 通常buildと意図的な取得失敗・検査失敗を試し、失敗をCIの成功にしないことを確認する。
4. 同じ実機・SDで5回以上の起動・更新を行い、容量・RAM・電源断・復旧・消費電力・保守差分を比較する。build時間とruntimeの効果を混ぜない。
5. 全面移行の費用より、現行Buildrootへの小さな改善として還元できる部分を先に採る。

現時点では選定の資料比較であり、これらの試験は未実施です。取得元・hash・失敗は[sources.json](sources.json)、照合の条件と再実行は[追加調査の検査記録](../../experiments/2026-11-02-alternatives-followup-audit.md)へ保存します。
