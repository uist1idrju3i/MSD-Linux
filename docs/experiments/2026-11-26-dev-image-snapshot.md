# 開発imageのKerberos・zstd・Linux header保守更新

- 状態：amd64のbuild・scan・host test・QEMU A/B完了。arm64の実行は未確認。
- 日付：2026-11-26
- 基準：最新main `9abf1683e32820334e18a898f2a8b351ba259322`
- 範囲：開発用OCIのDebian snapshot。#309のdevelopment header追加は含めない。

## 計画と採否

固定snapshotを`20261121T225354Z`から、Kerberos・zstd・linux-libc-devの修正版を両archの署名付きindexで取得できる最初の共通日時へ進める。base digest、Go stage、QEMU source・hash・patch・configure、ShellCheck、zizmor、Trivyの版・digestとgate条件は変えない。

最終stageとQEMU builderの導入済みAPT全件を比較し、更新sourceごとの中間バージョンを含むchangelogとcopyrightを読む。新機能・option・既定値・互換性・licenseの採否を記録する。固定Trivy 0.76.2と同じDBで旧新imageを比較し、blocker 0件を採用条件とする。残る場合は件数と理由を報告し、gateを緩和しない。

build・gate・host test・QEMU A/B起動は構築可否の検査として各条件1回とし、性能比較には使わない。旧imageはmainと同じDockerfileから作った`msd-dev:base309`を使用する。新snapshotはAPT取得とQEMU compileを再実行する。cacheを消したcold buildの時間比較ではない。製品のsource・kernel config・rootfsは変更せず、既存の`output-openssl-lts`の成果物を起動試験で共用する。製品のfull build・legal-infoは今回再実行せず、開発imageのlicense・package inventory・scanを比較する。

## snapshotの選定

署名付きindexの取得・負の対照の確認は[取得器](2026-11-26-dev-image-snapshot.py)で再現する。11月12日の取得器を再利用し、`Architecture: all`のLinux headerの初出も別に確認した。Debian archive keyringによる`gpgv`検証と、Release内のSHA-256・byte数によるPackages.xzの照合を、旧・直前候補・新の3日時、trixie・trixie-updates・trixie-security、amd64・arm64で行った。

| 修正版 | 両archでの初出 | 採否 |
|---|---|---|
| krb5 `1.21.3-5+deb13u2`の4 library | `20261122T195129Z` | 採用 |
| libzstd `1.5.7+dfsg-1+deb13u1`の2 package | `20261124T215723Z` | 採用 |
| linux-libc-dev `6.12.118-1` | `20261122T200302Z`、共通のall binary | 採用 |
| 共通日時 `20261124T184346Z` | zstd修正前 | 不採用 |
| 共通日時 `20261124T215723Z` | 上記すべての修正版あり | 最初に条件を満たす日時として採用 |

結果は[候補の版とdeb hash](2026-11-26-dev-image-snapshot-metadata.csv)、[metadata原本のhash](2026-11-26-dev-image-snapshot-metadata-sources.csv)、[入力・出力のhash](2026-11-26-dev-image-snapshot-sources.csv)に残す。取得器のCSV原本はCRLFで、収録CSVはLFに正規化した。`Check-Valid-Until: no`は既存のままで、過去snapshotの期限ではなく署名と固定内容を検証した。bootstrapのCA取得、Go builder、runner全体をこのAPT検証に含めない。

## 全package差分と変更履歴

QEMU builderは236件、最終stageは231件。追加・削除はどちらも0件で、更新は同じ7 binary packageだけだった。[全467行の版・architecture・source対応](2026-11-26-dev-image-snapshot-packages.csv)には不変のpackageも含めた。snapshot内の候補だけでなく、旧新imageの`dpkg-query`から比較した。例えば新indexにあるbase-filesの`13.8+deb13u8`は導入されず、固定baseの`13.8+deb13u7`を維持している。dist-upgradeを加えた更新ではない。

| binary package | source | 旧版 | 新版 |
|---|---|---|---|
| libgssapi-krb5-2、libk5crypto3、libkrb5-3、libkrb5support0 | krb5 | `1.21.3-5+deb13u1` | `1.21.3-5+deb13u2` |
| libzstd1、libzstd-dev | libzstd | `1.5.7+dfsg-1` | `1.5.7+dfsg-1+deb13u1` |
| linux-libc-dev | linux | `6.12.117-1` | `6.12.118-1` |

署名付きPackagesでhashを確認した修正版debを展開し、`changelog.Debian.gz`の旧source版より後のentryを最後まで読んだ。各sourceとも中間のDebian releaseはなく1 entry。Linuxは732行の対象entryを確認した。zstdの短いCVE記載は[Debian security tracker](https://security-tracker.debian.org/tracker/CVE-2026-124851)で補った。

### 変更の分類とoptionの採否

| source | security修正と範囲 | 互換性・新機能・option・既定値の判断 |
|---|---|---|
| krb5 | upstream 1.22.3からのbackportとlibkdb_ldapのread overrun修正。ASN.1の境界・計算量、RPC/GSSの認証とbuffer解放、PAC/CAMMAC、PKINIT、kadmindの権限・入力検査など18 CVEの修正を採用 | upstream 1.22系列へは移行しない。entryに新CLI・option・既定値の変更はない。導入するのは4 libraryで、KDC・kadmindを導入した検証ではない。特定daemonの脆弱な処理がこのimageで実行されるとは主張しない |
| libzstd | `CVE-2026-124851`。細工した圧縮入力が、未初期化又は以前の展開内容を含む内部bufferを出力へ露出させる修正を採用 | upstream 1.6.0へは移行せず、1.5.7へのDebian backportを使う。entryに新API・CLI・option・既定値の変更はない。QEMUの`--enable-zstd`と既存の圧縮設定を維持し、悪性入力への防御修正を受ける |
| linux | stable 6.12.118の全entryを確認。SMB・NFS・KVM・USB・network・memory・filesystem・driverの境界検査、寿命、locking修正、Debianのx86 PATの2 revertなど | 取得するのはuserspace headerのみ。ホストや製品kernelを6.12.118へ更新せず、kernelの新driver・quirk・内部helperは製品へ採用しない。build-timeのUAPI差分を別に照合し、QEMUの同じconfigureでbuildできることを確認した |

圧縮形式・QEMU option・製品kernel configは変更しない。別系列への更新や未固定APTの全面upgradeは、依存と互換性の差分を不必要に広げるため見送る。修正版debへの更新だけを採用する。

`linux-libc-dev`の`/usr/include/`内の1,974 fileを旧新でhash照合した。差は`linux/version.h`の版と、`linux/iommufd.h`のdirty bitmap ioctlに関する範囲・失敗時の説明コメントだけだった。新しいstruct・定数の利用やoptionの追加は不要と判断した。

### license

両stageの7 binaryすべてで`/usr/share/doc/<package>/copyright`を照合し、旧新hashの一致を確認した。対応するsourceのcopyrightは次のとおり。宣言と配布条件に変更はなく、新しいlicense義務は確認されなかった。Debianの配布物を使う判断であり、製品のlegal-infoやGo・Rustの全内包依存を再監査したものではない。

| source | copyright SHA-256、旧新共通 |
|---|---|
| krb5 | `936728f4181718f42951b881c1e8f1386bf6b2723c4fbc533c374d6f42c71816` |
| libzstd | `5cec9fef4d3fa7e0371fbef4ec3fc416e0105dc2a9922117f84e825cb11f50f8` |
| linux | `2ae27ed8a5581e2cc4969c266e655a280a8982f87dfe72c011c3f03d91897076` |

## buildと固定Trivyの比較

hostはUbuntu 26.04.1 LTS、x86_64、kernel `7.0.0-44-generic`、Docker 29.10.1。新imageはDebian 13.7、GCC 14.2.0-19、QEMU 11.1.3。旧imageのDockerfileと基準mainのDockerfileはbyte一致を照合した。新snapshotでQEMU builder・最終stageをbuildし、arm64のimage build・scanは行っていない。

| amd64の最終image | image ID | Docker inspectのSize |
|---|---|---:|
| 旧 | `sha256:c2a887cf29b5613ad4fad21917f3894528d286edccd11c51b9e63a4f2a50896b` | 1,349,899,770 bytes |
| 新 | `sha256:d36ae25cd56a7fd4e1354a22fa5c38b3eaacc15f317a97e2065936d265c62e74` | 1,351,102,174 bytes |

Sizeは1,202,404 bytes増。製品rootfsの増加ではない。独立したcold buildの再現性や性能同等を証明した値でもない。

TrivyはCIと同じ`ghcr.io/aquasecurity/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`を使用。scannersは`vuln,secret,misconfig`。DBのUpdatedAtは`2026-11-26T19:04:08.560197506Z`、DownloadedAtは`2026-11-26T22:41:04.107085862Z`。旧scan時のDBを`--skip-db-update`で固定して新scanに使った。gateは基準mainのスクリプトそのもので、除外やVEXは加えていない。

比較時のcacheに保持していたDB本体をReview対応時に照合し、次を追記した。metadataのSHA-256は当初の記録と一致した。DB本体のhashはscan実行時には記録しておらず、保持した本体から今回取得した値である。配布元から同じDBを新たに取得できるかは未確認。

| DBの識別情報 | 値 |
|---|---|
| schema Version | `2` |
| UpdatedAt | `2026-11-26T19:04:08.560197506Z` |
| NextUpdate | `2026-11-27T19:04:08.560197215Z` |
| trivy.dbの大きさ | 1,849,851,904 bytes |
| trivy.dbのSHA-256 | `80b72081e35c6d7fb3df5897576145d15ffaa6c9843d02df2e68c25b99eb7d7f` |

DB本体の大きさ・hashも[入力・出力の記録](2026-11-26-dev-image-snapshot-sources.csv)に収録した。DB本体はcommitしない。

| 検査 | 旧 | 新 |
|---|---:|---:|
| 脆弱性の検出レコード | 1,983 | 1,727 |
| gate対象の脆弱性 | 77 | 0 |
| 秘密情報・設定不備 | 0・0 | 0・0 |
| gate終了値 | 1 | 0 |

[旧blocker全77件と新版の対応](2026-11-26-dev-image-snapshot-blockers.csv)を残す。新imageに残る1,727件はgate条件外で、脆弱性ゼロという結論ではない。`linux-libc-dev`の検出が消えても、実行中のhost kernelや別に固定する製品kernelのCVE修正を意味しない。最終image以外のGo builder・runner・QEMU builder全体のTrivy scanは未実施。

## 回帰検査と限界

- CI登録のhost 13 suiteはすべて終了値0。`msd-update`、`version-info`、`init-scripts`、`early-io`、`msd-hwinfo`、`msd-data-grow`、`qemu-log-check`、`qemu-boot`、`powerfail-log`、`msd-dev`、`release-signing`、`legal-info-supplement`、`fs-compare-v2`を実行した。
- lint workflow相当のactionlint、pins consistencyとtest、kernel fragment・firmware config・Yocto比較のtest、shellcheck-tracked、zizmorを実行した。固定hadolintとDocker build check、Trivy gate test、CI scope testも終了値0。
- 同じ既存product imageを旧新QEMUで起動した。旧A/Bは40・41秒、新A/Bは26・26秒でreadyとloginを検出し、QMP quit・終了値0・serial検査まで成功した。各1回で、旧側ではimageのcompileとも並行したため、時間の差を性能改善とは扱わない。
- 最初の`--help`試行はCLIがimage pathとして解釈して拒否した。次の旧A試行は`OUTPUT_DIR`未指定で既定の`output/images/Image`がなく開始前に失敗した。正しい出力先を明示した上記の旧新A/Bは成功した。`--help`の一時serial logは未保存で、以後のQEMU原logは専用の出力先に残した。inventory採取はbuilder tagのexport前にも試みて失敗し、export完了後に両stageの全件を取得した。
- 製品のsource・最終kernel configは変更していない。同じimage・kernel・DTBを使い、通常のharnessどおりSD imageをcopyして起動した。最新mainのfull製品build、製品SBOM/VEX・legal-infoの再生成、実機LCD・keyboard・SD・電源断の確認は行っていない。

## 再現手順と記録先

作業時のraw outputは非追跡の`output-dev-snapshot-20261126/`に保存した。過去の旧scan・DBは`output-data-unlock-helper/`のものを再利用し、hashを上記CSVに記録した。raw Trivy JSON、DB、image tarはcommitしない。これらのローカル出力の存在を文書の根拠にはせず、候補・全package・blocker・hashを本記録に保存する。

```sh
python3 docs/experiments/2026-11-26-dev-image-snapshot.py NEW_METADATA_DIR --keyring-image OLD_IMAGE
docker/msd-dev build
docker build --target qemu -f docker/msd-dev.Dockerfile -t msd-dev:qemu-new .
docker run --rm --entrypoint dpkg-query IMAGE -W '-f=${binary:Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\n'
docker save -o msd-dev-new.tar msd-dev:local
docker run --rm -v "$PWD:/work" -v "$DB_CACHE:/root/.cache/trivy" ghcr.io/aquasecurity/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb image --input /work/msd-dev-new.tar --skip-db-update --scanners vuln,secret,misconfig --format json --output /work/trivy-new.json
python3 .github/scripts/trivy-gate.py gate trivy-new.json
docker/msd-dev python3 .github/scripts/run-host-tests.py --output-dir NEW_TEST_DIR --jobs 2 --timeout 300
docker/msd-dev env OUTPUT_DIR=/work/output-openssl-lts QEMU_LOG_DIR=/work/NEW_LOG_DIR board/cardputerzero/qemu/test-boot.sh
docker/msd-dev env OUTPUT_DIR=/work/output-openssl-lts QEMU_LOG_DIR=/work/NEW_LOG_DIR board/cardputerzero/qemu/test-ab.sh
```

旧buildは同じDockerfileに`--build-arg DEBIAN_SNAPSHOT=20261121T225354Z`を渡す。旧起動は`MSD_DEV_IMAGE=msd-dev:base309`を指定した。出力先は既存結果に重ねず新設する。将来のDBでは件数が変わるため、上記のDB日時・hashと区別する。CI・arm64・実機の成功をこのlocal結果から推定しない。
