# 全構成要素の母集団と比較の範囲

[比較の索引](README.md) / [依存とSBOMの監査](../dependencies/README.md)

## どこまで調べたか

「全構成要素」はBuildrootの67行だけではありません。製品、構築側、開発OCI、Action、その内包物、runnerと配信サービスを別の層として比較します。次表は既知の有限な母集団と、未だ完全には列挙していない層を区別します。一覧への全行対応は、全候補の全option・license・同等性の認定ではありません。

| 母集団 | 全件の対応と比較単位 | 確認できていないこと |
|---|---|---|
| 製品SBOMとshow-infoの67 package | [既存67行](coverage.csv)。target 18、host 49を、暗号・通信・周辺・生成tool等の比較本文へ対応 | 生成物の全fileの独立同定、全license、runtimeでの到達性、代替構成の実行 |
| 最終amd64開発OCIの231 APT / 129 source | [全行](oci-coverage.csv)と[責務別比較](oci-components.md)。同じ固定OCIのmetadataで版・親・著作権資料を補足 | 中間stage・arm64、全実行時依存、各upstreamの全option・保守/EOL、配布適合の判断 |
| Actionsの11参照 | [直接8・子3](action-coverage.csv)を[機能・権限・置換の費用](ci-actions.md)へ対応 | API完全互換、全candidateのlicense・費用・EOL、実bundleの全内包物 |
| source lockfileの859 npm名 / 1,574 name/version | [各組と親Action](npm-coverage.csv)。親更新、別Action、機能削減、source移植の単位で検討 | 859名が全て実行されるわけではない。個々のAPI移植案、bundleとの突合、全licenseの全文監査 |
| actionlintの11 Go module | [各moduleと親binary](go-coverage.csv)。別toolとの比較は[開発CI](development.md) | 別major path、Go標準library、配布binary全体のlicense/到達性。binary内のmoduleだけの差替えはしない |

数を単純に合計して一意の製品依存数にはしません。同じlibcやzlibがhost/target/OCIに別版で存在し、Actionのsource一覧はruntimeのSBOMではないためです。入力と反復・負の対照・初回失敗は[照合記録](../../experiments/2026-11-03-alternative-coverage.md)にあります。

## packageの行だけでは表現できない層

| 層・現行の役割 | 代替比較の正本と置換の単位 | 追加で必要な確認 |
|---|---|---|
| 外部Bootlin toolchain内のGCC・binutils・glibc・GDBとruntime | [toolchain](toolchains.md)、[libc](libc.md)、[現在の内包版とlicenseの不足](../dependencies/buildroot.md)。外部SDKの交換、Buildroot内での生成、Clang系等を比較 | toolchain一行のSBOMで内包全fileは覆わない。再配布条件、source、例外、target runtime、sysrootを別々に同定する |
| kernel、DT/DTBO、Pi firmware、Wi-Fi firmware、M5 overlay/BSP | [周辺/BSP](peripherals.md)、[機能library](peripheral-userspace.md)、[通信](network.md)、[公式OSとの差](../official-software.md) | kernelの置換、個々のdriver、API library、closed firmwareを同じ階層で比較しない。全周辺の実機・license・配布binaryの同定は残る |
| Go builder、QEMU builder、最終Debian OCIとsnapshot | [OCI比較](oci-components.md)、[構築基盤](development.md)、[PTXdist/Nix/Debian](system-builders.md) | base digestを固定してもbootstrap取得・全中間stage・host kernel/daemon/CPUまで不変ではない。段階ごとのSBOMと両CPUの証拠が必要 |
| QEMU、actionlint、ShellCheck、zizmorのnative binary/wheel | [開発tool比較](development.md)。更新/別tool/機能削減を分ける | QEMUの内包物、ShellCheckのHaskell library、zizmorのRust crate等をAPT/pip一覧だけで完全列挙していない。wheel/sourceのlockfileと実binaryも別 |
| hadolint・Trivyの独立したdigest固定container | [検査の代替と補完](development.md)、[全workflowの監査](../github-actions-audit.md) | 各OCIの内包packageと中間stageは開発用OCIの231件とは別。独立SBOM、検査DB・policy、同じdigestでの比較が必要 |
| runner OS、Docker/Podman/BuildKit、可変host | [実行環境の候補](development.md)、[Docker固定とhostの境界](system-builders.md) | hosted/self-hosted、native ARM、rootless、永続cache・socket・secret・未信頼PRの隔離費用。runner labelはimmutableなimageではない |
| download/ccache、artifact、GHCR、Pages、GitHub Releases | [CI追加調査](https://github.com/uist1idrju3i/MSD-Linux/blob/3914ad3dc104138e4a9be2f3250f23151a7a3e81/docs/research/ci-build-scope-and-performance.md)、[Actions比較](ci-actions.md)、[Release保護](../release-security.md) | cacheと信頼の証拠を分ける。storage/転送・公開権限・保護・期限、cache miss時の費用、取得失敗を確認する。GitHub内のhosted service全実装のSBOMは本調査の取得対象ではない |
| SPDX/CycloneDX、Syft/Trivy/Grype、VEX、attestation | [SBOMとscannerの比較](development.md)、[確認範囲](../sbom-coverage.md) | formatと生成元を換えても漏れは自動的に埋まらない。package同定、advisory、DB時刻、署名identity、許可する公開項目を別の契約にする |
| yomiyasu、fonttools、独自checker、text/GUI browser | [文書toolの比較](development.md)、[ロゴrequirements](../../logo/tools/requirements.txt) | 手動生成の依存とCI/製品を分ける。意味保存と視覚確認は別。全browser/描画環境の内包物や全fontの許諾を一つのpackage名で代表しない |

## 次に埋める不足

優先順位は、到達するコードと配布物・更新経路の信頼境界から決めます。まず製品の外部toolchainとfirmwareの内包物・license、次に配布する各OCIの全stage/両CPUとnative binary、Actionsの実bundleを独立同定します。個別libraryの置換実験は、その親が利用するAPI・ABIと脅威を確認してから行います。既知の859 npm名を全て別実装へ置換すること自体は目的にしません。

この追加照合で既知の有限な台帳の対応を揃えても、残した不足を完了とは扱いません。未リリースなので全面的な設計変更も候補ですが、rootfs・周辺機能・署名・更新・復旧・再現性の契約を失う費用まで評価します。製品・CIの変更は別の実施計画と試験で扱います。

[比較の索引へ戻る](README.md)
