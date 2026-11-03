# 圧縮・イメージ生成・host補助依存の代替

[比較の索引](README.md) / [保存領域](filesystems.md) / [開発・CI](development.md)

## 何を置換するか

Buildrootの構成要素には、製品で実行するlibraryだけでなく、hostで動く生成器・parser・build helperが含まれます。小さなtarget libraryに差し替えても、hostの依存が消えるとは限りません。67構成要素との対応は[比較台帳](coverage.csv)に示します。基準版は台帳の出所を参照し、以下を新しい製品構成とは扱いません。代替構成のbuild・実行は本リポジトリでは試していません。

## 圧縮の形式、API、利用場所を分ける

| 現行の構成要素 | 代替と互換条件 | 効果・費用・判定 | 採用前の検査 |
|---|---|---|---|
| target `libzlib` | zlib-ngのzlib互換mode / callerをlibdeflateへ移植 | zlib-ngは実験候補。libdeflateは同じ圧縮形式を扱うがzlib API互換の差し替えではない。callerごとの変更が必要 | API、symbol・version、gzFile、破損・途中切れ・巨大入力、展開サイズ上限、メモリー量とCPU命令を検査 |
| `host-libzlib` | host側もzlib-ngへ変更 / 現行を維持 | 固定Buildrootはhost providerを`host-libzlib`に固定する。targetのchoiceを変えただけでは置換しない。host全利用者の試験費用を考え、基準に維持 | host生成物の形式と内容、cross build、host/target library混入の負の試験 |
| `host-zstd`、`host-lz4`、`host-lzo`、`host-xz`、`host-lzip`、`host-pigz` | 同形式の別encoder / 圧縮形式そのものの変更 | encoderの変更とkernel・rootfs形式の変更を区別する。高速なencoderが製品の展開RAMを減らすとは限らない。filesystemの対応条件は[FS比較](filesystems.md)へ集約 | 生成物の再展開、kernelのdecoder、dictionary・block・level、worst-case RAM、破損、5回以上の同条件測定 |
| `host-libarchive` | GNU tar・BusyBox tar等の限定CLI / format別library | libarchive APIを使うcallerに別のtarコマンドを置いても互換にならない。複数形式・metadataを扱う機能を減らすなら、実際の利用者の要件が先 | path traversal、symlink、hardlink、absolute path、重複member、展開サイズ、owner/mode/xattr、非対応形式の拒否 |
| `host-blake3`、`host-xxhash` | callerに内包 / 別のhash方式 | これらはccacheの依存にもなる。cryptographic hashと高速な識別用hashを同一視せず、署名manifestのSHA-256を置換しない。現行の依存として維持 | cache keyの衝突・破損、compiler/flag変更時のmiss、異なるsource treeの分離 |

[zlib-ngの固定recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/zlib-ng/zlib-ng.mk)は2.3.3で、`ZLIB_COMPAT=1`、gzFile、最適化を指定し、AArch64ではNEONを有効にします。[choiceの定義](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/zlib/Config.in)にはAArch64対応条件と`ZLIB_FORCE_LIBZLIB`による制限があります。既存のsourceに互換modeのないnative APIを混ぜません。Cortex-A53で使える命令と、上流が最適化する新しいARM命令は別に確認します。

[libdeflateのREADME](https://github.com/ebiggers/libdeflate/blob/0758d0a12d34fac281b0fe27c5155fbe753d9511/README.md)はwhole-bufferのDEFLATE/zlib/gzipを対象とし、streaming非対応を明記しています。[同じcommitのheader](https://github.com/ebiggers/libdeflate/blob/0758d0a12d34fac281b0fe27c5155fbe753d9511/libdeflate.h)でも、専用のcompressorと入力・出力bufferを取るAPIを確認しました。「zlib API一部互換」とした旧記述は誤りでした。対応するfile formatとlibrary APIを分けて訂正します。RAMの少ない環境で、全入力・出力bufferを持つ移植が有利とは限りません。1.26のRelease候補と取得した開発HEADも区別します。

現行rootfsはzstdのSquashFSで、updaterはそのimageを署名・hashで照合して扱います。DEFLATEの高速化をそのままrootfs展開やA/B更新の改善値にしません。`msd-update`、bundle生成、依存libraryがどこで何を展開するかを確認し、実際にCPU時間が占められる場所だけを最適化候補にします。

## イメージとmetadataの生成

| 現行 | 代替・削減案 | 保持する契約と判断 |
|---|---|---|
| `host-genimage`、`host-libconfuse` | Wic、別のimage builder、明示的なpartition作成script | genimageの設定parserだけを別parserに変えても互換ではない。WicはYoctoとの統合条件が異なる。自作scriptは境界・offset・再実行・エラー処理を自分で保守する費用が増える。現行を基準に維持し、partition type、alignment、boot/data内容と再現性を比較する |
| `host-dosfstools`、`host-mtools` | mountして書き込む / 別のFAT生成器 | block deviceやmountの特権を増やさず生成できることを重視する。FATのvolume情報、timestamp、長い名前、容量境界、firmwareが読むboot imageを検査する。機能を同じにせずbinaryの小ささだけで選ばない |
| `host-e2fsprogs`、target `e2fsprogs` | 別FSと生成・修復tool / 機能を絞ったutil | ext4を維持する間は対応した生成・検査・修復が必要。toolの削除とFS変更は別の判断。電断・空き容量・fsck後の復帰まで[FS比較](filesystems.md)の条件を満たす |
| `host-squashfs` | 別のSquashFS生成器 / EROFS | on-disk形式、kernel decoder、mtime/owner/xattr、sort順、重複排除、blockとcompression optionを揃える。別FSへの変更はupdaterとmount・health試験も対象 |
| `host-fakeroot`、`host-makedevs`、`host-acl`、`host-attr` | user namespace内の生成 / image builderのmetadata指定 | UID/GID、mode、device node、ACL/xattrはhost上の見え方とimage内の値を分ける。fakerootはsecurity sandboxではない。rootでbuildすることを代替の前提にせず、最終imageを展開・検査して同等性を判定 |
| `host-dtc` | DTS生成方法の変更 / dt-schemaによる追加検証 | DTB/DTBOのcompilerとschema validatorは異なる。schemaを足してもoverlay合成、phandle、配線、実機probeの確認を置き換えない。現行compilerを基準に維持し、schemaは補完候補 |
| `host-kmod`、target `kmod` | BusyBoxの対応applet / built-in driver化 | depmod、圧縮module、署名・依存順・alias・blacklist等を比べる。built-in化でhotplugや署名の契約も変わる。moduleを読めるだけでは機能同等としない |
| `host-util-linux`、target `util-linux` | BusyBox applet / 個別util | 同名でもmount・block device・fsync等の引数とerrorが異なる。[基本コマンド](commands.md)と更新処理の負の試験を基準にする。hostの生成toolとtargetの復旧toolを一括削除しない |

## build systemとその内包library

| 現行のまとまり | 比較・削減案 | 費用と再検討条件 |
|---|---|---|
| `host-autoconf`、`host-autoconf-archive`、`host-automake`、`host-libtool`、`host-m4` | upstreamのMeson/CMake移行を追従 / 配布済みconfigureで再生成を減らす | build frontendは同じ出力を得る単なるaliasではない。patch後のautoreconf、cross判定、libtoolのsysroot処理が必要なpackageでは勝手に外さない。upstreamが正式に用意する経路を先に評価 |
| `host-bison`、`host-flex` | release同梱の生成済みparser / 他のparser generator | grammar・生成API・skeletonのlicenseを含む変更。Buildrootのhost dependencyを削るだけでは再生成できない。固定sourceとpatchの経路に必要かを確認し、必要な間は保持 |
| `host-meson`、`host-ninja` | CMake/Make等、upstreamが対応する経路 | [Mesonのcross file](https://mesonbuild.com/Cross-compilation.html)はbuild/host/target、compiler、sysroot、実行wrapperの区別を持つ。[Ninja](https://ninja-build.org/manual.html)は実行する低位のbuild engineで、設定・依存解決の全てを代替しない。生成物とcross testが同等でなければ移行しない |
| `host-pkgconf` | pkg-configの別実装 / 個別のinclude・link flags | `.pc`、sysroot、static linkのprivate依存を保つ必要がある。手書きflagでhost libraryを拾う危険があるため、削減目的だけの自作置換はしない |
| `host-python3`、`host-python-pypa-build`、`host-python-installer`、`host-python-packaging`、`host-python-pyproject-hooks`、`host-python-setuptools`、`host-python-wheel`、`host-python-flit-core` | upstream backendを変える / hostへ配布済みwheelを固定導入 | Python interpreter、build frontend、backend、wheel installerは異なる層。新installer一つで全てを置換できるとは限らない。target Pythonを入れる理由にはしない。network access、hash、architecture、source buildの有無を検査 |
| `host-expat`、`host-libffi`、`host-gettext-tiny` | 利用者のoptional機能を落とす / 別XML・FFI・gettext実装へ移植 | parserやFFI ABI、locale/catalogの契約はcaller側にある。単に別libraryをlinkして終わる代替ではない。親packageの最終configと利用機能を特定し、不要な機能の削減から検討 |
| `host-ccache`と`host-hiredis`等 | cacheなし / ccacheの機能を絞る / sccache | 固定ccache recipeはhiredis・zstd・xxhash・blake3へ依存する。Redis serverがtargetで起動するという意味ではない。cache自体の代替は[開発・CI比較](development.md)へ集約 |
| `host-libopenssl` | host署名処理を別実装へ / signerを分離 | targetのTLS実装の変更とhost signerの変更は別。鍵形式・raw Ed25519・manifest bytes・key loadingを[署名比較](signing.md)の契約で評価する |

`host-skeleton`やtargetのskeleton/initscripts等は独立した汎用アプリではなく、Buildrootのrootfs構成をつなぐ要素です。[initの比較](init.md)と[通信の比較](network.md)で責務ごとに判断します。名前だけを消してSBOMを小さくする手法は採りません。

## 根拠と残る検証

固定Buildrootのrecipe・Kconfig、[sources.json](sources.json)のzlib-ng/libdeflate README・license、Meson、Ninja、ccacheの資料を照合しました。[XML・FFI・翻訳・Python構築の詳細](host-interfaces.md)では親package・API・backendの移植条件も比較します。host-libraryの全内部APIを読み切った監査ではなく、親packageを含む代替buildは本リポジトリでは試していません。67行の対応は比較対象を漏らさないための索引であり、全候補の同等性・license・securityの認定ではありません。

削減実験では、選択package、host/targetの最終依存、生成物、SBOM、license、QEMUのboot/A-B、復旧tool、実機の機能を同じ基準で確認します。cacheの有無で少なくとも5回ずつ測り、cold/warmとCPU・I/O・networkを分けます。ソースの変更、未追跡logの消失、異なるbase imageを混ぜた比較は採用根拠にしません。

[比較の索引へ戻る](README.md)
