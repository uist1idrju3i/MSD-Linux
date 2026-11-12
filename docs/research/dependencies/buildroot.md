# Buildrootと外部toolchainの依存監査

## 固定した入力とSBOM実物

基準はBuildroot commit `8b238854d909c9cce32ef9671d968b03e323b55d` とMSD/Linux commit `1395e9d142a0970fc68e57818e51af02e2d99f2f`。通常buildの[run 41486595026](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41486595026)が保存した[artifact](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/41486595026/artifacts/13163313182)の `sbom.cdx.json` と `buildroot-show-info.json` を読んだ。取得した入力のhash・byte数は[source-record.json](source-record.json)にある。

このrunのheadは `1147512a54f1f1b68f97ad1b5a7d053de644cb10`、SBOMのproject versionはPR用test mergeの `d9ae8a33f348b6ff77d236d02c1d56e7ae81d70e` である。head、test merge、mainへのmergeは区別する。[既存の照合関数](../../../.github/scripts/set-kernel-version.py)で実artifactの構成要素・host/target・版・依存先を生成元show-infoと再照合した。Linuxは `custom` ではなく `6.18.59`、source commitは `b3495ea401d709af0701a85babcba5e3d788a602` だった。

67 componentの全件は[CSV](buildroot-packages.csv)と[JSON](buildroot-packages.json)にある。rootfsやvirtual providerの情報は生成元にもあるが、component件数と混ぜない。67件の内訳、68 dependencyレコードと267本の参照は従来の[SBOM調査](../operations/sbom-coverage.md)と同じ。今回の実物照合は、その後の版補正経路の検証に当たる。

## 最新版候補の確認方法

Buildroot packageのdownload定義からupstreamを選び、公式のrelease、tag、配布index、PyPI JSONを読んだ。取得先・時刻・hashは[upstream-checks.json](upstream-checks.json)、補足資料は[source-record.json](source-record.json)にある。一般的な数字の抽出だけではrevisionや年を誤認したため、packageごとに正式なtag名・tarball名で絞り込んだ。OpenSSL、ccache、MesonはGitHub Releasesを最後のページまで取得して安定版を比較した。最初に返るreleaseを無条件に最新版にしない。

| 分野 | 現行版から見つかった候補の例 | 採用前の注意 |
|---|---|---|
| ビルド基盤 | automake 1.16.5 → 1.19、Meson 1.11.1 → 1.12.1、pkgconf 2.3.0 → 3.0.10、patchelf 0.13 → 0.19.3 | Buildrootのpackage patch、依存制約、host実行環境との整合が必要 |
| 生成・圧縮 | dtc 1.7.2 → 1.8.1、libarchive 3.8.9 → 3.8.10、mtools 4.0.49 → 4.0.50、xxhash 0.8.3 → 0.8.4 | DT生成物、image layout、既存hash、再現性への影響を比較する |
| target/host library | OpenSSL 3.6.5 → 4.1.0、kmod 34.2 → 34.3 | major更新を修正のみと扱わず、API/ABI・サポート期間・廃止機能を調べる |
| host Python | Python 3.14.8 → 3.15.2、setuptools 80.9.0 → 84.2.1、flit-core 3.12.0 → 4.2.0 | host packageの更新であり、Pythonを製品rootfsへ追加する提案ではない |
| util-linux | 2.41.5 → 2.42.2 | targetとhostを別行に残し、選択したutilityごとに影響を見る |

これは全件一覧の要約である。同一nameがtargetとhostにあるため、件数はnameの種類数ではない。新しい候補があることだけを理由にBuildrootのpackage定義を個別に上書きしない。採用する場合は、[vendor-update](../../../.agents/skills/vendor-update/SKILL.md)の全変更履歴・許諾・ビルド・起動・更新処理の比較を行う。

### 安定版と即断できない項目

- `fakeroot` は現行1.37.2。Debianのsource poolで2.1.4のorig tarballを見つけたが、upstreamの正式tagとしては未確認。一覧では `distribution-candidate-not-upstream-confirmed` とした。
- `makedevs`、skeleton、init・ifupdown・urandomのscript類など7件はBuildroot内部の版なしpackage。最新番号を捏造せず、固定Buildroot commitの変更として追う。
- Raspberry Pi Linuxの「同じ」は選択系列 `rpi-6.18.y` のHEADとの比較。`rpi-7.3.y` のbranchも取得されたが、最新安定kernelへの採用可否を意味しない。
- Raspberry Pi firmwareは固定 `063bcab6c8a90efb0d19f69d88cbbc7ec79cab68` に対し、default branch HEAD `ab5c7f86283ceb58b7adb269cae1d16092a31bf6` に差があった。HEADはSemVer releaseではない。GPU起動はQEMUで検証できない。
- Wi-Fi firmwareのLibreELEC配布元とM5 overlayのHEADは今回の固定値と同じ。接続・音声・周辺機器の実機動作を証明するものではない。

## 外部toolchainは一件のpackageでは説明しきれない

現行は `aarch64--glibc--stable-2025.08-1`。公式の[配布表](https://toolchains.bootlin.com/releases_aarch64.html)とarchive内のREADMEを照合した。Buildroot SBOMでは `toolchain-external-bootlin` の一行になるため、内包compilerやlibcの版をその一行から推測しない。

| 内包物 | 現行archiveの版 | 今回の一次資料で見つかった上位系列・版 |
|---|---|---|
| GCC | 14.3.0 | [公式release一覧](https://gcc.gnu.org/releases.html)の16.2 |
| binutils | 2.43.1 | [GNU配布index](https://ftp.gnu.org/gnu/binutils/)の2.47 |
| GDB | 15.2 | [GNU配布index](https://ftp.gnu.org/gnu/gdb/)の18.1 |
| glibc | 2.41-70-g1502c248d58cb99a203731707987a4342926e830 | [GNU配布index](https://ftp.gnu.org/gnu/glibc/)の2.44 |

上位版の表記は一次資料に合わせたもので、実際に置き換えてビルドした結果ではない。Cortex-A53、AArch64 ABI、kernel headers、libc、libstdc++、exception・TLS・atomic・sanitizer対応、最小kernel版、再現性を一緒に比較する必要がある。GCCとLLVM、glibcとmusl等の採否は別の比較課題である。newlibはLinux向けlibcの同等な差し替え候補とは限らず、OS interfaceの前提から比較する。

Bootlinには2026.08-1があるが、固定したBuildroot安定系列の選択肢にはまだない。[固定値確認](pinned-versions.md)はこれを「Buildroot安定版待ち」と区別する。toolchain全体の更新と、内包GCC等のupstream最新版への追従は同じ意味ではない。

## ライセンス・脆弱性の残件

- LinuxのCPE版補正後も、SBOMのcomponent直下のhashとpurlは0件。59 componentにはsource-distribution参照内のhashがある。source hashをbinary hashと読み替えない。
- `toolchain-external-bootlin` と一部M5配布物はlicenseがunknown。Wi-Fi firmwareのPROPRIETARY表記も、配布条件の確認を省ける意味ではない。
- 今回のCIログにもLinux license fileのhash欠落、Buildroot source未保存、外部toolchainのlicense file未定義が残る。legal-infoのjob成功だけを配布可能判定に使わない。
- Bootlinには[source](https://toolchains.bootlin.com/downloads/releases/sources/)と[license](https://toolchains.bootlin.com/downloads/releases/licenses/)の公式経路がある。必要なソースと許諾をarchive単位で収集・対応付けし、再配布時の提供方法を決める。
- BuildrootのCPE照合は、内包glibcやlibstdc++を個別componentとして自動列挙した結果ではない。kernel versionが合ったことと、全依存のCVE判定が正しいことを分ける。

2026-11-12追記：上記のhash欠落は当時の記録です。固定kernelのlicense 3 fileを[外部linux.hash](../../../board/cardputerzero/patches/linux/linux.hash)へ、M5のCOPYINGを[packageのhash](../../../package/m5stack-cardputerzero/m5stack-cardputerzero.hash)へ追加しました。固定上流原文と照合し、同じ既存出力で`legal-info`を変更前後に各1回実行した結果、対象のERROR 3行・WARNING 1行はなくなりました。[検証記録](../../experiments/2026-11-12-legal-info-hashes.md)に検査経路・manifest・残る警告を記載します。Buildroot source未保存とBootlinのlicense file未定義、M5 firmware等のunknownは未解決です。

## 再確認の手順

1. [source-record.json](source-record.json)のrunからartifactを取得し、SBOMとshow-infoのbyte数・SHA-256を照合する。権限と保存期限によりartifactを取得できない場合は、同じheadではなく同じtest mergeを再現できるかも確認する。
2. SBOM内のproject versionを読み、headと混同しない。通常buildと同じ `set-kernel-version.py --show-info ... --project-version ...` で生成元と照合する。元の入力は保存し、作業用の写しで実行する。
3. BOM refをキーに、67 componentと依存先・host/target・版をCSV/JSONと比較する。virtual providerとrootfsを別扱いにする。
4. 各行のupstream URLを再取得する。URL、取得時刻、hash、tagのpre-release除外、paginationの終端を残す。現在の候補が変わっても、今回の記録を現時点の値で上書きしない。

初回のartifact取得中には不完全なZIPを確認した。その状態ではSBOMを読んだと扱わず、取得完了後にZIPを開き、必要な二つのJSONを抽出して照合した。性能実験ではないため、最新版取得を5回反復して中央値を出すことはしていない。

[依存関係の一覧へ戻る](README.md)
