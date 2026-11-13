# 開発imageのDebian snapshot保守更新

- 状態：完了（amd64のローカルbuild・scan・QEMU。arm64のbuild・scanとCIは未実施）
- 日付：2026-11-12
- 基準commit：`c4ab37cebb847e3f3a44cfca45ac9c3ce6af80f6`
- 対象：開発用OCI。製品のBuildroot packageは更新しません。

## 目的と採否の基準

旧snapshot `20261103T023120Z`で検出されたaptとzlibの修正を、最初に収録したsnapshotへ移します。apt・libapt-pkg7.0の3.0.4、zlib1g・zlib1g-devの`1:1.3.dfsg+really1.3.1-1+deb13u1`以上が、amd64とarm64の署名付きindexに存在することを条件にします。直前のsnapshotに不足する修正があることも確認します。

最終imageとQEMU builderの全APT差分を列挙し、各source packageの中間版を含む変更履歴・security advisoryを読みます。新機能、option、既定値、互換性、licenseの採否を記録し、同じTrivy DBで旧新imageを比較します。新imageのgate対象は0件を採用条件とし、例外やgateの緩和は行いません。

amd64はローカルでbuildします。arm64は利用可能なbuilderで実行できる場合に限り、metadata照合と実行結果を区別します。過去の監査・生データは変更しません。

## 条件と範囲

| 項目 | 値 |
|---|---|
| ホスト | Ubuntu 26.04.1 LTS、x86_64 |
| 固定する入力 | 基準commitのDebian/Golang base digest、Go/actionlint stage、QEMU 11.1.2のsource・hash・署名鍵・patch、ShellCheck、zizmor、gate実装 |
| 変える入力 | Dockerfileのsnapshot ARG 2箇所と、QEMU builder・最終stageのinstall対象へのapt追加 |
| 反復 | 構築可否・gate・A/B起動を各条件1回。性能やbit単位の再現性を判断しない |
| cache | 旧OCIは既存BuildKit cacheを再利用。新snapshotとapt明示の各試行ではAPT取得とQEMU compileを再実行。cacheを全消去したcold比較ではない |
| 製品入力 | 既存`output-openssl-lts`のImage・SquashFS・SD imageを両OCIで共用。前タスクの公開鍵modeで増分生成したもの。今回、製品のfull build・reconfigure・legal-infoは再実行しない |
| QEMU試験 | SDのcopyを使用。旧新ともraspi3ap、同じkernel・rootfs、A/B起動を各1回。実機試験ではない |
| APT台帳 | amd64の最終stage全231件とQEMU builder全236件。Go builderはsnapshotを使わず、baseとsource固定値も未変更 |

## 最初のsnapshotの選択

[取得器](2026-11-12-dev-image-snapshot.py)で4 binaryの修正版についてamd64・arm64の`binfiles`と各fileの`first_seen`を読みました。aptとlibaptはdebian-securityの`20261104T120337Z`、zlib1gとzlib1g-devは`20261107T075304Z`が初出です。後者を共通のas-of日時に選びました。debian側のzlib初出`20261107T144357Z`を待つ必要はなく、security suiteから取得できます。

旧・直前・候補の各日時について、trixie、trixie-updates、trixie-securityのInReleaseをDebian archive keyring 2025.1とgpgv 2.4.8で検証し、署名されたSHA-256・byte数を両archのPackages.xzと照合しました。[候補一覧](2026-11-12-dev-image-snapshot-metadata.csv)と[保存fileのhash](2026-11-12-dev-image-snapshot-sources.csv)を残します。calendarで確認した直前のsecurity snapshotは`20261106T203307Z`で、そこには必要なzlib修正版がありません。取得器はこの負の対照と、候補の全8組の存在をassertします。

固定値監視はDockerfileのARGを読む方式のままで、新しい日付の二重管理は追加しません。監視のunit testにある旧日付は独立したfixtureであり、過去の監査台帳も書き換えません。署名・hash照合はmetadataの恒久的な鮮度保証ではなく、既存の`Check-Valid-Until: no`も変更していません。

掲載CSVは元のfieldを保ったまま改行をLFにしたcopyです。`sources.csv`のhashは出力directory内の元fileに対応し、改行を変える前のCSVも保持します。初回の`git diff --check`は生成CSVのCRLFを末尾空白として拒否しました。測定値や元fileは変更していません。

## 全APT差分と変更履歴の評価

配布archiveの未導入package全体ではなく、各OCI stageの導入済みbinary全件を比較します。arm64の全依存closureやOCI実行は、このamd64台帳から推定しません。各binaryとsourceの対応、旧新の版、採否は[差分CSV](2026-11-12-dev-image-snapshot-packages.csv)に残します。

| source | 読んだ範囲と一次資料 | 採否・必要な対応 |
|---|---|---|
| apt | 3.0.3の直後にある3.0.4の全changelog entry。[修正版deb](https://snapshot.debian.org/package/apt/3.0.4/)の`usr/share/doc/apt/changelog.gz`と[DSA-6607-1](https://www.debian.org/security/2026/dsa-6607) | CVE-2026-109518のdownload検証回避、deb/control末尾のunderflow、gpgvの終端越え、Version欠落debの拒否、DNS応答buffer越え、tagfileの逆向き走査、solverの順序関係を修正。すべて採用。aptを両stageで明示してlibaptも依存関係で更新する。再試行5回の設定と署名検証を維持する |
| zlib | source版`1:1.3.dfsg+really1.3.1-1`から`+deb13u1`までの全entry。旧binaryの`+b1`はsource版の更新ではない。[修正版deb](https://snapshot.debian.org/package/zlib/1%3A1.3.dfsg%2Breally1.3.1-1%2Bdeb13u1/)の`changelog.Debian.gz`と[DSA-6613-1](https://www.debian.org/security/2026/dsa-6613) | crc32_combineの負の長さ（CVE-2026-27171）とgzwriteのbuffer越えを修正。DSAとtrackerでは同じgzwrite修正がCVE-2026-76844とCVE-2026-85091に対応する。両binaryで採用。製品rootfsのzlib更新とは別 |

aptの残りの変更も読みました。遅延download項目の開始失敗messageをdebug扱いにすることでmemory消費を抑える変更は受け入れます。valgrindのopen file上限1024とGitLab CIのtrixie指定は上流test用であり、このrepoのrunnerやlimitへ移植しません。新しいCLI、option、formatや既定のsolverを選ぶ変更はなく、新しいflagの採用・延期はありません。zlibもupstreamの別系列へ移す更新ではなく、1.3.1に対するDebianの保守修正です。新しいAPIや圧縮設定は採用していません。

互換性については、不正debや異常なgzip書込み状態の扱いが変わることを受け入れます。正規のAPT install、QEMU compile・起動、host testで回帰を確認し、個別のexploitや全consumerの互換性を検証したとはしません。

licenseはaptのGPL-2+と例外・付属fileのcurl/BSD-3-clause/Expat/GPL-2、zlibのZlib表記を確認しました。両sourceの修正版debを署名付きindexのhashで照合し、copyright原文は旧OCIとbyte単位で同じでした。SHA-256はaptが`77ab918ade9bce20b07524572fc8eab3f8c0cab4d246f282043892aaa9538803`、zlib1gが`9e5b96d63773a5d177ba264254390f792be07e41748ebd94730981c6cac31cc6`です。OCI全体のlicense確認や法令適合の証明ではありません。

## 失敗・中止した試行

1. snapshotだけを変えた初回はbuild成功、zlib 2 binaryのみ更新でした。apt/libaptは固定baseの3.0.3のままでした。install対象にない導入済みpackageは自動でupgradeされないため、両stageへaptを追加しました。全packageのupgradeで差分を広げる対応はしていません。
2. 旧QEMU stageのexport完了前に台帳を読もうとした初回は、tagがまだなくDockerがpullを試みて終了値125でした。空の台帳は`qemu-old-packages.initial-failure.tsv`として保持し、build完了後の236件だけを採用しました。
3. arm64の固定baseをpullし`/bin/true`を実行したprobeは`exec format error`、終了値255でした。builderの公開platformはamd64のみで、binfmtにarm64 interpreterはありません。ホストの特権設定は変えず、arm64 imageのbuild・scanは実施していません。

新buildにはman pageのlink作成を省く`update-alternatives`の警告が残ります。slim imageのdpkg設定がmanualを除外しているためで、`xz-utils`の導入と`xz`の実行は確認しました。警告だけを消すためにmanualを追加する変更はしていません。

## 結果

最終stageは231件中4件、QEMU builderは236件中4件だけが変わり、追加・削除は各0件でした。両stageの差分は同じ次の4 binaryで、sourceは2件です。GCC、binutils、make、Python、git、curl、OpenSSL等の導入版は同じでした。

| binary | 旧版 | 新版 |
|---|---|---|
| apt | 3.0.3 | 3.0.4 |
| libapt-pkg7.0:amd64 | 3.0.3 | 3.0.4 |
| zlib1g:amd64 | 1:1.3.dfsg+really1.3.1-1+b1 | 1:1.3.dfsg+really1.3.1-1+deb13u1 |
| zlib1g-dev:amd64 | 1:1.3.dfsg+really1.3.1-1+b1 | 1:1.3.dfsg+really1.3.1-1+deb13u1 |

旧新とも最終OCIとQEMU builderのbuildは終了値0でした。`docker image inspect`のIdは旧が`sha256:a7888fa6b6b4354b0b2049cf3174c6930f35ea5b9c35f50521fa787278186692`、新が`sha256:41357c6d6123a5477f04ad0f53185e91f3e9c599b34e20c94fd96f94e82b7bee`です。Sizeは旧1,315,961,186 byte、新1,323,384,361 byteで、7,423,175 byte増えました。サイズの悪化も保持し、buildの再現性を証明する値とは扱いません。

### 同じDBでのgate比較

CIと同じTrivy 0.76.1、digest `sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c`でOCI tarをscanしました。scannerは`vuln,secret,misconfig`です。DBは1回だけ取得し、旧新とも更新を止めました。Version 2、UpdatedAtは`2026-11-12T12:59:19.777478911Z`で、DBのSHA-256は両scan後も`99fdc77556d4c2870c4288db54e6cddc88a7234a3db6e6895d101d441ed86e57`でした。

| 条件 | 脆弱性レコード | 公開gate対象 | 秘密情報 | 設定不備 | gate終了値 |
|---|---:|---:|---:|---:|---:|
| 旧 | 1732 | 6 | 0 | 0 | 1 |
| 新 | 1724 | 0 | 0 | 0 | 0 |

旧の6件はapt/libaptのCVE-2026-109518、zlib1g/zlib1g-devのCVE-2026-76844とCVE-2026-85091でした。旧の負の対照で失敗を検出し、新では成功しました。gate実装、閾値、例外は変更していません。総件数は一意のCVE数でも製品の検出数でもなく、0件となったのは公開gate対象だけです。新OCIのSPDX SBOMも生成しましたが、licenseの完全確認や配布許諾とは扱いません。

### 回帰の確認範囲

QEMUは旧新とも11.1.2、OCI内のGCCは14.2.0です。QEMU binaryのSHA-256は旧`c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410`、新`2ccefc16585d3df5147234241a02aee0be6b84cdd97cbdf1843109b1f64622f1`で、各serial logの`run-qemu: sha256`と照合しました。同一source・patchを異なるAPT入力で再compileした結果であり、binaryが同一とはしません。

既存のLinux 6.18.59-v8、target GCC 14.3.0の製品入力で、旧新ともA/B起動とmodule・mount条件の検査に成功しました。readyまでの時間は旧A/Bが30/29秒、新A/Bが26/30秒でした。各1回で、同時期のcompile負荷もそろえておらず、性能改善の根拠にはしません。新OCIで`tests/msd-update/run.sh`も成功しました。

両試験前後で次の入力は同じでした。kernelの最終`.config`のSHA-256は`74d625a1c9dad65fd2999abd0b0a572874a39b32dbd1d685edcb3153ea8a0739`です。今回kernel設定を再生成した比較ではありません。

| 入力 | byte数 | SHA-256 |
|---|---:|---|
| Image | 18016768 | `982c8617205d36d331e3909519e48d68a694c1b67cfacc35739658fceb73a434` |
| rootfs.squashfs | 20680704 | `f3abd8cf3daded1a2bf00df9c37e71a6fcf2f408595d6bc3703fb82423d60107` |
| sdcard.img | 771751936 | `a4c7d1613ac0e6fa769a0d84ba610d552af261ce0b698c6e5d444dde2d67cea6` |

## 再実行する手順

出力先は存在しない名前を選びます。旧Dockerfileの写しは基準commitから取得し、branchは切り替えません。ほかのCOPY入力は今回変更していません。

```sh
EVIDENCE=output-dev-image-snapshot-new-run
mkdir "$EVIDENCE"
git show c4ab37cebb847e3f3a44cfca45ac9c3ce6af80f6:docker/msd-dev.Dockerfile \
  > "$EVIDENCE/Dockerfile.old"
docker build --progress=plain -f "$EVIDENCE/Dockerfile.old" -t msd-dev-snapshot:old .
docker build --progress=plain --target qemu -f "$EVIDENCE/Dockerfile.old" \
  -t msd-dev-snapshot:qemu-old .
python3 docs/experiments/2026-11-12-dev-image-snapshot.py "$EVIDENCE/metadata" \
  --keyring-image msd-dev-snapshot:old
docker build --progress=plain -f docker/msd-dev.Dockerfile -t msd-dev-snapshot:fixed .
docker build --progress=plain --target qemu -f docker/msd-dev.Dockerfile \
  -t msd-dev-snapshot:qemu-fixed .
for stage in old fixed qemu-old qemu-fixed; do
  docker run --rm --entrypoint dpkg-query "msd-dev-snapshot:$stage" \
    -W '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\t${Architecture}\n' \
    > "$EVIDENCE/$stage-packages.tsv"
done
TRIVY=ghcr.io/aquasecurity/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
mkdir "$EVIDENCE/trivy-cache"
docker run --rm -v "$PWD/$EVIDENCE/trivy-cache:/root/.cache/trivy" \
  "$TRIVY" image --download-db-only
for variant in old fixed; do
  docker save -o "$EVIDENCE/$variant.tar" "msd-dev-snapshot:$variant"
  docker run --rm -v "$PWD/$EVIDENCE:/work" \
    -v "$PWD/$EVIDENCE/trivy-cache:/root/.cache/trivy" "$TRIVY" image \
    --input "/work/$variant.tar" --skip-db-update --skip-java-db-update \
    --scanners vuln,secret,misconfig --format json --output "/work/$variant-trivy.json"
  python3 .github/scripts/trivy-gate.py report "$EVIDENCE/$variant-trivy.json" \
    --findings-json "$EVIDENCE/$variant-findings.json"
  status=0
  python3 .github/scripts/trivy-gate.py gate "$EVIDENCE/$variant-trivy.json" || status=$?
  printf '%s gate exit=%s\n' "$variant" "$status"
  MSD_DEV_IMAGE="msd-dev-snapshot:$variant" OUTPUT_DIR=output-openssl-lts \
    QEMU_LOG_DIR="$EVIDENCE/qemu-$variant" QEMU_COPY_IMAGE=1 \
    docker/msd-dev board/cardputerzero/qemu/test-boot.sh
  MSD_DEV_IMAGE="msd-dev-snapshot:$variant" OUTPUT_DIR=output-openssl-lts \
    QEMU_LOG_DIR="$EVIDENCE/qemu-$variant" QEMU_COPY_IMAGE=1 \
    docker/msd-dev board/cardputerzero/qemu/test-ab.sh
done
MSD_DEV_IMAGE=msd-dev-snapshot:fixed docker/msd-dev tests/msd-update/run.sh
```

再取得するDBやbootstrap時のCAは変わり得るため、同じpackage件数・scan件数・image IDになる保証はありません。取得器は古い出力directoryへの上書きを拒否します。raw Trivy JSON、DB、OCI tar、大きなbuild logはコミットしません。

## ログと未確認

永続的な出力先はrepo内の`output-dev-image-snapshot/`です。metadata初回、移植可能な旧OCI tagを指定した最終取得、snapshotだけの初回build、旧新build、台帳、sanitized findings、gate、SPDX、serial logを保持しました。測定値は[CSV](2026-11-12-dev-image-snapshot.csv)にまとめ、失敗・未実行を成功の数値に混ぜていません。

| log | SHA-256 |
|---|---|
| metadata-final.log | `728bf3bf66348ef820420cc9eac3d6879798e5f433cf64b594e026d1d87b63b7` |
| old-build.log | `1c229f621994e92c652699aa1c3ba922280e55de6c5ed7884227b031cdfc2a74` |
| fixed-build.log | `b9f0b70fdbd947154b7bbdc21cd339fc980bfdbb3e9753abfcb5ac8352b6991b` |
| qemu-old-build.log | `39f3066ba5e367e38d875943523d7036608bd82580ae14c161aa0d8f92ac0ca9` |
| qemu-fixed-build.log | `850f7d31e410f61b9451be3e86fcc49255b6f0e4bfd5a5eb7d377bf15a343241` |
| old-gate.md | `c2a7842410f73af88f05bce139a03f6a172f278599aa71eb91260b78b47a07f2` |
| fixed-gate.md | `8673e3fa154de7aae6c5fe04ed80d43ff63703a3e0ffe6566e4fbd5be14c2e4b` |

採用するのはローカルamd64の公開gate解消です。arm64は修正版の署名付きindexだけを確認し、OCIのbuild・scanは未実施です。CI・公開attestation、製品のcold/full build、今回のlegal-info、実機LCD・keyboard・I2C・firmware tryboot・実電源断、全依存の安全性は未確認です。通常のbuildには既存のCA bootstrap取得も残り、完全な再現性や無脆弱性を主張しません。文書の画面表示も未確認です。

## 2026-11-13の保存監査による補足

上記の実験時にcommitしなかったraw Trivy JSON、build/QEMU log、APTの取得metadata等は、[保存監査](../research/verification/session-evidence-2026-11-13.md)でdata branchへ追加しました。Trivy DB本文1,764,192,256 bytesと旧新OCI tarは引き続きGit未保存で、原本を削除せず、sizeとhashを一覧へ残しています。今回再hashしたDBは元の値と一致しました。新しいscanやQEMUの再試験は行っておらず、実験当時の確認範囲は変更しません。

保存した`pr229-arm64-verified.zip`の中も読みました。`image-provenance.json`はarchitectureを`arm64`、image IDを`sha256:527357b9f4129d62a3cd476fa982d7779fd1df570ea8220b2d046400a2075088`と記録しています。Trivy 0.76.1、DB UpdatedAt `2026-11-12T12:59:19.777478911Z`のreportは脆弱性1718件・公開gate対象0件で、findings JSONの`blockers`も空でした。これは保存artifact内の観測です。zip内にはrun/commitとの対応がなく、file名だけでPR #229の特定runの結果と認定したり、上記のローカル実験をarm64実行済みへ書き換えたりはしません。
