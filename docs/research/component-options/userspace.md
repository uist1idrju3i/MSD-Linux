# ユーザー空間・libcの機能と設定

[調査の入口](README.md)へ戻る。

## 対象と読み方

選択されたtarget 18件の機能と、compilerやlibcの役割は以下に整理した。各版・レシピ・下位設定の場所は[package台帳](packages.csv)、条件分岐後の引数は[package変数](package-variables.json)にある。台帳はSBOMの`bom-ref`で対応づけ、同名のhost版とtarget版を区別する。

packageの機能は、そのpackageが提供できる範囲である。配布rootfsへの全commandの収録、全optionの利用、実機動作を意味しない。kernel・firmware・M5は[別の本文](kernel-firmware.md)、host側は[生成ツール](host-image.md)を参照する。

| target component | 機能と設定面 | 現行の要点・確認が必要なこと |
|---|---|---|
| `busybox` | init、ash、mdev、ファイル・network・保守commandを一つのbinaryにまとめる。Kconfigでappletと機能を選ぶ | Buildrootの基底設定、MSD fragment、レシピのfixupを重ねる。最終BusyBox設定は今回のCI artifactに含まれず、初期値を最終値としない |
| `e2fsprogs` | ext系の作成・検査・拡張。configureでutilities・library・fuse等を選ぶ | `--enable-fsck --enable-resizer`、debugfs・defrag・uuidd・fuse2fs等は無効化。`/data`の拡張と起動後の検査は別の操作 |
| `ifupdown-scripts` | interfaceのup/down hookと設定連携 | 認証方式やWi-Fi接続管理そのものではない。使用するifup/down実装とDHCP clientも確認する |
| `initscripts` | SysV系の起動・終了script | 起動順と失敗の扱いが実際の既定値になる。daemonの自動再起動・権限分離を一律には提供しない |
| `kbd` | console keymap・font等の操作 | M5内蔵keyboard用keymapと機器driverを区別する。locale、UTF-8、LCD上の視認性は別に確認する |
| `kmod` | moduleの検索・依存・読み込み等 | kernelのmodule署名、圧縮形式、depmodの生成先と組み合わせる。toolの存在はmoduleのロード成功を保証しない |
| `libopenssl` | 暗号library、TLS、provider、openssl CLI | 下記のとおりbuild機能と実行時policyを分離する。A/B署名検証にCLIを使う |
| `libv4l` | V4L library、capture/制御utilities、IR等の関連機能 | `-Dv4l-utils=true`、Qt GUI・BPF decoder・JPEG・DVB library・tracer等は無効。camera/IRのdriver・node・実機とは別 |
| `libzlib` | deflate圧縮・展開のlibrary | 利用者向けdaemonではない。呼出し元の入力・buffer・圧縮levelと、libraryのbuild設定を分ける |
| `skeleton-init-common`、`skeleton-init-sysv` | rootfsの基底directoryとinit方式に応じた土台 | packageを増やさずとも、overlayと生成scriptが設定を書き換え得る。生成後の権限とsymlinkも調べる |
| `urandom-scripts` | 起動・終了時の乱数seedの扱い | 永続領域、権限、乱数の初期化時期が重要。seedを複数端末へ同一内容で配る運用を避ける |
| `util-linux` | block/partition、mount関連library、多数の保守utilities | basic setと`partx`を選択。recipeは`--enable-all-programs`の後に個別の無効化を加えるため、先頭だけでは判断しない |
| `toolchain-external-bootlin` | SDK内のcompiler、binutils、libcを取り込む | glibcは独立Buildroot packageとして今回の67件に数えられない。内包物と実binaryの依存はSDK単位のSBOMだけでは分からない |
| `linux`、`rpi-firmware`、`brcmfmac_sdio-firmware-rpi`、`m5stack-cardputerzero` | kernel、GPU/boot・無線firmware、外部moduleとDTBO等 | [kernel・firmwareの本文](kernel-firmware.md)に設定経路・機器依存・確認範囲を記載 |

## BusyBoxと重複command

現行のMSD fragmentは`FSYNC`、`DESKTOP`、`FEATURE_DD_IBS_OBS`、`FEATURE_MD5_SHA1_SUM_CHECK`を選ぶ。ddのblock指定や照合用の機能は、更新scriptの受入条件にもなる。名前にMD5/SHA-1を含む機能があることと、更新の真正性をその方式で保証することは異なる。更新はEd25519署名とSHA-256を使う。

Buildrootの基底BusyBox設定はwget、udhcpc、syslogd等を含むが、これをそのまま生成後の利用可能一覧とはしない。Kconfigの依存、fragment、Buildroot fixup、他packageが提供するcommandの優先順位、post-buildが関わる。実binaryの`busybox --list-full`、`busybox APPLET --help`、symlinkの行き先で確かめる必要がある。

特にHTTPSは、wgetという名前だけでは判定できない。BusyBox自身のTLS、外部openssl連携、CA・hostname検証、認証情報・redirectの扱いを実行したbinaryで確認する。TLSの設定がないまま「GitHubから安全に取得できる」とはしない。

再検討候補は、不要applet・SUID機能・serverの削減、エラー時の終了状態の統一、network取得と特権書込みの分離。削減前に全起動・更新・回復scriptのcommand依存を調べる。BusyBox、util-linux、e2fsprogs間のcommand置換では、同名でも引数・出力・終了状態が異なるため、symlinkだけで互換性を判断しない。

## libc：SDKの固定値と実行時の調整

固定SDKはglibc `2.41-70-g1502c248d58cb99a203731707987a4342926e830`。現在は外部SDKなので、MSD/Linuxのdefconfigからglibcのconfigure optionを一つずつ変更する構成ではない。変更にはSDKの再生成またはtoolchainの変更が必要になる。

glibcにはmalloc、dynamic loader、thread、CPU選択等の調整面があり、`GLIBC_TUNABLES`はcolon区切りの`name=value`で指定する。上流はtunablesをstable ABIに含めず、版・distributionで変わると明記している。文書のx86用項目をAArch64へ流用しない。

動的loaderの`--list-tunables`、`--list-diagnostics`等と、最終binaryのinterpreter・NEEDED・symbol versionを確認する手順が必要である。今回、target loaderを実行した結果は採取していない。host glibcの値を代用せず、allocator変更、arena/tcache・thread cache調整、static link、musl等への変更は別の比較候補として残す。RAM削減だけでなくABI、DNS/NSS、locale、thread、toolchain、外部moduleのbuild経路に及ぶ費用を評価する。

## OpenSSL：旧機能の削減と実行時policy

固定版は3.6.5。正規化したBuildroot設定はRC2・RC4・MD4・DES、SSL3・weak SSL、ECX、QUIC等のsymbolを`y`とする。recipeは無効を選んだときに`no-rc2`、`no-ssl3`等を渡す。**symbolが`y`であることは、上流で既定無効の機能を明示的にenableすることとは異なる。** 上流の既定値、Configureの依存・cascadeも読む必要がある。

展開後のConfigureは`linux-aarch64`、`threads shared`、`no-rc5 enable-camellia no-docs no-tests no-fuzz-libfuzzer no-fuzz-afl no-afalgeng no-engine zlib-dynamic`を含む。これはBuildrootの引数の記録であり、生成した`configdata.pm`やheaderの全機能判定ではない。`no-tests`も製品全体の検証を不要にする意味ではない。

| 候補 | 目的と背反 | 採否の前に行う確認 |
|---|---|---|
| RC2/RC4/MD4/DES等の無効化、`no-legacy` | 不要な旧機能とproviderを減らす。`no-legacy`だけでは全ての古いalgorithm/APIを消すわけではない | recipeで表現できる範囲、default providerの範囲、全呼出し元、証明書・署名形式、最終binaryのalgorithm一覧 |
| SSL3・weak cipherの明示無効化、TLS policyの固定 | 意図を既定値へ依存させない。対応不要な旧相手を切り捨てる | build対応、実protocol/cipher、最低TLS版と証明書検証の拒否試験。現在のnetwork serviceの存在を仮定しない |
| `no-deprecated`とAPI level指定 | 古いAPIの新規利用を抑える。既存呼出し元がbuildできなくなる場合がある | upstreamの`--api`との関係、targetとhostそれぞれのAPI使用、全buildと更新回帰 |
| ECX・Ed25519とSHA-256を必要機能として保持 | 現行bundleの検証と整合させる。TLS向けの選定とは別の判断 | `pkeyutl -verify -rawin`、正常・破損・別鍵・署名なし・downgradeの検査を最終binaryで実施 |
| QUIC・trace・debug・未使用providerの削減 | サイズと保守対象を減らす可能性がある。将来の取得方式が必要とする場合は再検討 | 呼出し元と上流の依存条件、実際のサイズ差、診断・回復の代替手段 |

providerをbuild・installすること、`openssl.cnf`からloadすること、アプリが選択すること、TLS policyで許可すること、外部へserviceを公開することは別の層である。`openssl version -a`、`openssl list -providers`、algorithm/cipher一覧、実際のクライアントの試験を使い分ける。CLIのprovider一覧だけで全アプリを証明しない。

今回は設定削減を実装していない。単に最新のlibraryへ置換する案でなく、未リリースで互換性維持が不要な前提で、必要な暗号・protocol・APIを先に定めるための調査である。

## 一次資料

- 固定Buildrootの[BusyBox recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/busybox/busybox.mk)、[OpenSSL recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libopenssl/libopenssl.mk)、[util-linux定義](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/util-linux/Config.in)、[v4l-utils recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/libv4l/libv4l.mk)
- [BusyBoxのMSD fragment](../../../board/cardputerzero/busybox.fragment)、[製品defconfig](../../../configs/msd_cardputerzero_defconfig)
- [glibc 2.41 tunables](https://sourceware.org/glibc/manual/2.41/html_node/Tunables.html)、[SDK同版README](https://toolchains.bootlin.com/downloads/releases/toolchains/aarch64/readmes/aarch64--glibc--stable-2025.08-1.readme)
- [OpenSSL 3.6.5のINSTALL](https://github.com/openssl/openssl/blob/openssl-3.6.5/INSTALL.md)、[Configure](https://github.com/openssl/openssl/blob/openssl-3.6.5/Configure)。tagと取得archiveの対応は[source hash記録](source-archives.json)で確認する。
- [各configureの引数の索引](configure-options.csv)。28ソースの`configure --help`からoption行を採取したもので、折返し後の説明・全既定値・条件・Meson/CMake/Make等を完全に展開した一覧ではない。
