# RAUC adaptiveと差分更新の比較

[更新framework](updates.md) / [更新経路と配信](update-delivery.md) / [build option](update-build-options.md) / [代替比較](README.md)

## 決定と調査の範囲

利用者はRAUCで進め、imageをGitHub Releasesへ配置し、差分更新にRAUC adaptiveの`block-hash-index`を使う計画を承認した。現在の条件は[導入契約](../../design/rauc-update-contract.md)、全optionの採否は[棚卸し](../component-options/rauc.md)を参照する。frameworkの製品導入はまだ行っていない。RAUCでは完全imageとindexを含むbundleのRelease asset化を計画する。現行の`sdcard.img.xz`をそのままRAUCへ渡せるという意味ではない。

比較対象は固定Buildroot `8b238854d909c9cce32ef9671d968b03e323b55d`のRAUC 1.15.2とSWUpdate 2026.05.1。以下は一次資料と実装を調べた結果で、build・QEMU・CM0実機での更新、転送量、RAM、所要時間は未測定である。SWUpdateとcasyncは比較として残し、並行採用する方針にはしない。

## 方式と必要な配信構成

| 方式 | 配信側 | 端末のseedと処理 | 制約 |
|---|---|---|---|
| RAUC adaptive | 完全imageとindexを含むbundleをHTTP Range対応serverへ配置。専用chunk store不要 | activeとtargetの両slotから一致blockを再利用。不足分をbundleから取得 | 特定の旧版に依存しない。block device限定でtar archiveには使えない |
| RAUC casync | bundleをindex形式へ変換し、別途chunk storeを公開 | 通常はbooted slot groupの同classのactive slotをseedにし、外部`casync extract`へ委譲 | block imageとdirectoryを扱える。別toolとchunk配信の運用が増える。desyncも代替実装 |
| SWUpdate `delta` | imageの`.zck`をHTTP Range対応serverへ配置し、zchunk headerをSWUに含める | 明示したsource file／partitionを走査し、不足chunkを取得。復元streamをraw等の次handlerへ渡す | active slotの自動選択ではない。Range非対応時はabortし、full downloadへのfallbackなし |
| SWUpdate `rdiff_image`／`rdiff_file` | 特定baseから対象imageへのlibrsync patchを生成し、通常配信 | `rdiffbase`等で指定したbaseを使ってpatch適用 | 特定base限定だが直前版限定ではない。Rangeやchunk storeは不要 |

RAUC adaptiveはSHA-256を4 KiB blockごとに持ち、slotのindexをshared data-directoryへ保存する。indexがなければその場で生成する。再利用blockは読んだdataをhash照合するため、古いindexだけを信用しない。中断したtargetの一致blockも再利用候補になるが、中断位置からの単純な続行とは区別する。[RAUC advanced:788–857](https://github.com/rauc/rauc/blob/v1.15.2/docs/advanced.rst#L788-L857)

casyncの変換・chunk store・seedの契約は[同資料:859–1048](https://github.com/rauc/rauc/blob/v1.15.2/docs/advanced.rst#L859-L1048)にある。SWUpdateのzchunk header、別download process、Range必須、SHA-256指定は[delta資料:171–244](https://github.com/sbabic/swupdate/blob/2026.05.1/doc/source/delta-update.rst#L171-L244)、rdiffのbase指定とpatch適用は[handler:221–339](https://github.com/sbabic/swupdate/blob/2026.05.1/handlers/rdiff_handler.c#L221-L339)で確認した。固定版の比較資料にxdeltaやcasyncへの言及があっても、それだけでSWUpdate標準handlerとは数えない。

SquashFSのrootfsは不透明なblock imageとして扱える。ただし圧縮による変更の波及が再利用率に影響する。RAUC資料の`--mksquashfs-args="-b 64k"`はbundle側の圧縮設定例で、製品rootfsのblock sizeを決めたものではない。installed-rootfsのdm-verityとbundleの検証は別であり、前者の採用・rollback方針はこの調査では決めない。

## 認証と失敗後の状態

| 方式 | 検証経路 | 中断・不一致時の注意 |
|---|---|---|
| RAUC adaptive | CMS署名で認証したbundleとverity streamingを基礎にする。slot再利用blockは書込み前に読取りhashを照合する | 途中失敗時にtargetが部分更新済みになり得る。active不変と失敗時非activateは統合試験が必要 |
| RAUC casync | 署名bundle内のindexを基に外部toolで抽出する | 固定casyncで全chunkがtarget書込み前に検証されるかは追跡未完了。RAUC単体の保証として断定しない |
| SWUpdate zchunk | 署名済み`sw-description`、header hash、chunk hashを結び付ける構成が必要。headerと非圧縮chunkを含むSHA-256指定を使う | chunk検証完了前に下流writerへ流れ得る。不一致で失敗してもinactive領域は部分変更済みになり得る |
| SWUpdate rdiff | 署名とpatch hashだけでは、正しいbaseと最終imageの正しさを証明しない | base認証と復元後readback hashを別途試す。baseを`rb+`で開く実装のため、read-only active領域との互換性も未確認 |

SWUpdateのnetwork chunkは[delta_handler.c:153–183](https://github.com/sbabic/swupdate/blob/2026.05.1/handlers/delta_handler.c#L153-L183)、source再利用chunkも[同:828–874](https://github.com/sbabic/swupdate/blob/2026.05.1/handlers/delta_handler.c#L828-L874)で`copyfile()`へ渡される。[cpio_utils.c:826–860](https://github.com/sbabic/swupdate/blob/2026.05.1/core/cpio_utils.c#L826-L860)は出力callbackを呼んだ後に最終hashを比較する。この順序は実装の確認であり、本機で破損を注入して観測した結果ではない。[署名資料](https://github.com/sbabic/swupdate/blob/2026.05.1/doc/source/signed_images.rst)に沿った強制検証の設定も必要である。

RAUCのbundle形式とstreamingは[advanced資料](https://github.com/rauc/rauc/blob/v1.15.2/docs/advanced.rst)を参照する。casyncへの委譲は[update_handler.c:471–545](https://github.com/rauc/rauc/blob/v1.15.2/src/update_handler.c#L471-L545)、rdiffの`rb+`は[handler:308–339](https://github.com/sbabic/swupdate/blob/2026.05.1/handlers/rdiff_handler.c#L308-L339)にある。

## 依存と永続書込み

| 項目 | 固定Buildrootでの確認と製品で残る判断 |
|---|---|
| RAUC streaming／adaptive | OpenSSL、GLib、squashfs。networkはlibcurl、streamingはlibnlとkernel NBDが必要。shared data-directoryの配置・index更新・status保存を設計する |
| casync | 独立したrecipeが存在。commitは`0efa7abffe5fffbde8c457d3c8fafbdde0bb6e4f`。RAUC recipeが自動で追加する依存ではない |
| SWUpdate delta | curl、zstd、zchunkが必要。zchunk recipeは1.3.2。復元writerとsource／destination分離も設定する |
| SWUpdate rdiff | librsync recipeは2.3.4。固定base用patch生成と、baseを誤った場合の拒否を管理する |
| OpenSSL機能 | CMS/X.509、SHA-256、採用署名算法、HTTPSのTLSを保持する。固定RAUC recipeはENGINEもselectする。差分方式だけを理由にlegacy provider必須とはしない |

一次資料は固定Buildrootの[rauc Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/rauc/Config.in)、[rauc.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/rauc/rauc.mk)、[casync.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/casync/casync.mk)、[zchunk.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/zchunk/zchunk.mk)、[librsync.mk](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/librsync/librsync.mk)、[swupdate.mk:160–192](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/swupdate/swupdate.mk#L160-L192)である。

RAUC adaptiveのslot indexは永続保存の対象だが、完全なchunk cacheは不要。他方式も永続chunk cache必須とは確認していない。download buffer・一時file・logはRAMへ置き、slot書込み、index生成・保存、status更新と復旧時の書込みを[製品の書込み規則](../../design/write-policy.md)に沿うprogress付き操作へ含める。未操作時のindex更新を許したことにはしない。各段階の時間・安全な中断・再開が必要な状態を英日表示する実装は未着手である。

adaptiveはRAUC 1.8から文書化された機能で、[casyncとの比較](https://github.com/rauc/rauc/blob/v1.15.2/docs/advanced.rst#L911-L944)も公開されている。SWUpdateの[DELTA／RDIFFHANDLER設定](https://github.com/sbabic/swupdate/blob/2026.05.1/handlers/Kconfig)はdefault nで、当該項目にexperimental表示はない。これらを本機での運用実績とは扱わない。

上流RAUCの小変更ext4例は取得約10%、index約0.8%。[SWUpdateの比較資料](https://github.com/sbabic/swupdate/blob/2026.05.1/doc/source/delta-update.rst#L50-L95)はrdiffが変更量次第で元imageより大きくなることを説明する。いずれも上流の説明であり、本製品のSquashFSで帯域削減率を測定したものではない。

## GitHub ReleasesのRange観測

2026-11-19に依頼者から共有された観測は次のとおり。本調査では再実行しておらず、RAUC自身の取得試験ではない。

| 対象・要求 | 応答 |
|---|---|
| [RAUC 1.15.2のsource asset](https://github.com/rauc/rauc/releases/download/v1.15.2/rauc-1.15.2.tar.xz)に`curl -r 100-199` | HTTP/2 302で`release-assets.githubusercontent.com`へredirect |
| 転送先 | HTTP/2 206、`accept-ranges: bytes`、`content-range: bytes 100-199/990656` |

このassetの当該要求でRange応答を観測した範囲に限る。RAUC streamingによるredirectの追従、転送先signed URLの期限切れ・更新中の再接続、rate limitの処理は未検証である。Release探索APIとasset downloadの制限・認証も分けて試す。GitHub Releasesを選んだことだけで、長時間のadaptive更新が成立したとは判断しない。

## Phase A第2段の測定案

承認済みの[導入契約](../../design/rauc-update-contract.md)に従い、RAUC fullとadaptiveを主比較にする。casync・zchunk・rdiffは差分方式の対照として別構成で評価する案で、製品へ追加する決定ではない。[全optionの採否](../component-options/rauc.md)とboot連携の受入条件を固定し、測定は後続PR⑥で行う。

| 試験 | 入力と対照 | 記録・判定 |
|---|---|---|
| 再現性 | 別`O=`、commit、toolchain、kernel、QEMU、圧縮条件、全binary・image hashを固定。cold/warm・ccacheを区別。A/Aと各条件5回以上 | 正常・失敗・中止を保存し、生成物の容量・RAM・一時領域・時間を絶対値で記録 |
| 転送削減 | 同一image、小変更、大変更、複数の旧版、indexなし、空・欠損入力、部分更新済みtarget | 取得bytes、Range要求数、index生成費用、source読取り、slotと`/data`のwrite量。帯域削減率の採用閾値は本測定前に利用者と決める |
| 配信異常 | Range非対応、redirect、signed URL期限切れ、rate limit、通信断、中断再実行 | full fallbackと失敗を区別し、再試行回数・再取得量・progress・中断後の状態を記録 |
| 検証と復旧 | 不正署名、破損header／chunk／base、誤base、read-only active、容量不足、writer失敗 | 失敗時非activate、active不変、最終readback hashと起動・healthを確認。途中targetの部分書込みを隠さない |
| 永続write | 更新前・中・終了後idleを同じ時間条件で採取。既知書込みの正対照と、機能を止めた負対照 | block統計と段階別progressを対応付け、終了後の未帰属writeも記録。index・status・復旧を除外しない |

生log・CSV・command・環境とhashを日付付き実験記録へ残す。QEMUで機能を確認した後、CM0でRAM・KDF等の競合、SD flush、firmware、電断・復旧を別途試す。QEMUのblock統計を物理SDの書込み量や実機耐電断性の証拠にはしない。
