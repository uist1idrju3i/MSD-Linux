# Buildroot・外部ツールチェーンの設定と引数

[調査の入口](../../../RESEARCH.md)へ戻る。

## 設定を読む順序

基準はBuildrootの固定commit `8b238854d909c9cce32ef9671d968b03e323b55d`と、監査時のMSD/Linux `641a6f5d1d31081832a5ea2da04ef89a6d681f4b`。製品設定は変更せず、同じdefconfigを固定開発用OCIで正規化した。新しい`.config`の確認と、過去のCI生成物の確認は別の証拠である。

| 層 | 調べるもの | 言えること・言えないこと |
|---|---|---|
| 指定 | `configs/msd_cardputerzero_defconfig` | 利用者が明示した要求。省略された既定値や依存解決後の結果は含まない |
| 正規化 | defconfigから生成したBuildroot `.config` | その版のKconfigで選ばれた値。アプリケーションやkernel固有の全設定ではない |
| レシピ | 各packageの`.mk`、`Config.in`、Kconfig・CMake・Meson等の下位設定 | 設定がどの処理へ伝わるか。変数名だけで適用を断定しない |
| 展開値 | upstreamの`show-vars`にある`raw`と`expanded` | 条件分岐と変数参照の確認。対象packageを実行していないため、`PKG`や`$@`に依存する値は実際のbuild時と異なり得る |
| 実行と結果 | compile/linkログ、ELF、実行時の値 | 指定したbinaryについての適用結果。別revisionや別binaryへ一般化しない |

`show-vars`の`BUILD_CMDS`を、そのまま実行可能なビルドコマンドとして扱わない。例えばMakeの対象がないと`$(@D)`が`.`となり、packageの作業ディレクトリーを表さなくなる。正規化した設定、静的な引数展開、実行したコマンドを混同しないための資料である。

## 現行の設定と適用経路

| 項目 | 正規化した値・確認した経路 | 注意点 |
|---|---|---|
| CPU・ABI | AArch64 / Cortex-A53。外部Bootlin SDKは`--with-cpu=cortex-a53`、LP64 | `TARGET_CFLAGS`に`-mcpu`がなくても、SDKの既定値が関わる。他SoC向けの最適化を流用しない |
| 最適化 | `BR2_OPTIMIZE_S=y`。`TARGET_CFLAGS`は`-Os -g0`を含む | kernelや独自Makefileの全compileに同じフラグが渡る証明ではない |
| Fortify | `BR2_FORTIFY_SOURCE_3=y`。`-D_FORTIFY_SOURCE=3`を展開値で確認 | 対応するlibc・compiler、最適化、有効な対象関数が必要 |
| SSP | `BR2_SSP_STRONG=y`。wrapperの追加フラグに`-fstack-protector-strong` | 共通CFLAGSだけを読んでは見落とす。対象外の関数や上書きもある |
| PIE | `BR2_PIC_PIE=y`。wrapperへ`BR2_PIC_PIE`を定義 | wrapperはkernel、static、明示的な無効化等を区別する。全ELFのPIEを保証しない |
| RELRO | `BR2_RELRO_FULL=y`。wrapperがlink時に`-Wl,-z,now`と`-Wl,-z,relro`を追加 | `TARGET_LDFLAGS`が空でも無効とは限らない。ELFのsegmentとdynamic flagsで確認する |
| LTO | `BR2_ENABLE_LTO=y` | **全packageへ`-flto`を追加する設定ではない**。下記参照 |
| rootfs | SquashFS、128 KiB block、zstd、extreme、`-Xcompression-level 22` | 配布時の圧縮条件。CPU・RAM・読み取り量・起動時間との背反は実測が必要 |

共通CFLAGSの展開値は次のとおり。これだけではwrapperの追加引数やpackage独自の上書きは読めない。

```text
-D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64 -Os -g0 -D_FORTIFY_SOURCE=3
```

### LTOについての訂正

Buildrootの`Config.in`は、`BR2_ENABLE_LTO`がLTOを明示的に選択できるpackageへ適用されると説明する。常時LTOを使うものもあるが、多くのpackageは有効化しない。固定ソース内の参照はfastd、Flutter、netdata、Cargo等にあり、設定を選んだだけでBusyBoxやOpenSSL等を一括LTO化する仕組みではない。

したがって「LTOを選択している」と「製品の全ユーザー空間をLTOで生成した」は異なる。また、確認したCI生成物のkernelは`CONFIG_LTO_NONE=y`で、Buildrootの選択をkernel LTOの証拠にしてはならない。

追加するなら、対象packageごとにcompile/linkの`-flto`、archive plugin、最終link、サイズ、起動・更新の回帰を確認する。最適化による利得を測る前に、適用対象と実際の引数を固定する。今回の調査では追加していない。

## SDKの機能と追加候補

固定Bootlin `aarch64--glibc--stable-2025.08-1`のREADMEは、GCC 14.3.0、binutils 2.43.1、glibc `2.41-70-g1502c248d58cb99a203731707987a4342926e830`を示す。archiveのSHA-256はBuildrootのhashと一致した。

```text
dfb47eee874eef9e8a7fc042eee4e0a183f444b6bcde6a82fef8f009918389c9
```

GCC実行ファイルの`-v`と、`-Q -Os -mcpu=cortex-a53 --help=common`、`warnings`、`params`、`optimizers`、`target`を取得した。これは**裸のSDKへ指定した条件での照会**であり、Buildroot wrapperを経た最終設定ではない。表示の空欄を無効と読み替えず、categoryをまたぐ同じoptionも別の照会結果として扱う。

| 候補 | 目的 | 背反・不適用条件・追加確認 |
|---|---|---|
| `-Oz`、`-O2`、`-O3` | サイズと速度の配分を変更 | `-Os`より小さい・速いとは未確認。同一機能・同一入力でbuild時間も測る |
| package単位のLTO | 翻訳単位を越える最適化 | link時間・RAM・plugin・独自buildとの互換性。kernelとは別に扱う |
| `-fhardened` | GNU/Linux向けのhardening設定をまとめる | GCCのmajorで集合が変わる。明示した弱いフラグでも自動追加を抑止し得るため、既存設定との重複と優先順を確認する |
| `-fstack-clash-protection` | stackのguard pageを飛び越える割当を抑える | 対応範囲はtarget依存。実際のコード、stack使用、時間・サイズの増加を確認する |
| `-ftrivial-auto-var-init=zero` | 自動変数の初期化を補助 | 元の未定義動作や初期化漏れを正当化しない。追加書込みとサイズ、性能を測る |
| `-fstrict-flex-arrays=3` | flexible arrayの扱いを厳格化 | 古い末尾配列の慣用表現と衝突し得る。対象ソースの修正・上流対応を先に確認する |
| `-mbranch-protection`、SLS対策 | Arm固有の防御コード | compilerの受付、CPUの機能、OSの対応、実行時の効果は別。Cortex-A53での効果を名前だけから判断しない |
| sanitizer、`-fanalyzer`、警告の追加 | 開発時に欠陥を発見 | runtime、RAM、時間、誤検出を伴う。配布用の一律有効化ではなく、検査用buildから比較する |

`-fhardened`のGCC 14.3の集合にはFortify、C++ assertions、自動変数のzero初期化、PIE、RELRO、SSP、stack clash対策が含まれる。`-fcf-protection=full`の追加はx86 GNU/Linuxに限られ、AArch64へ同じ効果を期待しない。既存のBuildroot hardeningを消して置き換える案ではない。

## 未使用libgompの配送（2026-11-23）

この節の基準は`f4e1f65`とBuildroot `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`。
SDKは同じBootlin 2025.08-1 / GCC 14.3.0を使い、更新していない。上流最新版の再調査やcompilerの全optionの再棚卸しではなく、targetへlibgompを配送する設定とcopy経路を対象とする。
[容量とQEMUの実験記録](../../experiments/2026-11-23-libgomp-prune.md)に監査方法、数値、生証拠、未確認範囲をまとめた。

| option・方法 | 意味・既定と固定版での動作 | 採否・理由 |
|---|---|---|
| `BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE` | 製品が明示選択。外部Bootlin SDKを使う | 維持。runtime削減のためにSDKとABIを交換しない |
| `BR2_TOOLCHAIN_HAS_OPENMP` | 選択したSDKからselectされる能力。外部toolchain recipeは有効なら`libgomp.so.*`をtargetへcopy | 能力の記述は維持。Kconfigで無効を要求してもselectで戻り、SDKの機能を偽る手段にはしない |
| `BR2_GCC_ENABLE_OPENMP` | 内部GCCのOpenMP buildとlibgomp配送を制御 | 今回は対象外。製品は内部GCCをbuildしないため、この値を変えても配送を止められない |
| `BR2_TOOLCHAIN_EXTERNAL_OPENMP` | custom外部toolchainの能力申告 | 不採用。Bootlin presetからcustomへ変えて能力を偽る案は、今後のpackage判定と矛盾する |
| `BR2_TOOLCHAIN_EXTRA_LIBS` | 既定は空。外部toolchainが追加でcopyするlibraryの指定 | 維持。追加用であり、libgompをcopy対象から除く設定ではない |
| external post-build | 全通常fileの`libgomp`・`GOMP_`文字列と別名symlinkを調べ、参照があれば削除前に拒否 | 採用。利用者不在の製品だけから本体・配送用symlinkを削除し、SDKとstagingには触れない |
| libgomp維持・LLVM libompへの置換・自作runtime | 維持は互換性を保つが未使用の容量を残す。置換は別のOpenMP実装を追加する | 今回は不採用。OpenMP機能を要求する製品packageがないため、別runtimeの導入や自作は不要 |

関連する5つのKconfig tokenを表へ収録した。`TOOLCHAIN_EXTERNAL_LIBS`、`TOOLCHAIN_EXTERNAL_INSTALL_TARGET_LIBS`、`copy_toolchain_lib_root`はrecipe内部のcopy経路であり、製品向けの除外optionではない。
`OMP_*`や`GOMP_*`環境変数はload済みruntimeの動作を変えるもので、未使用libraryの配送を抑止しないため、今回のoption照合の対象外とした。
新しい設定を追加する案は採っておらず、compilerがOpenMPを扱えることと製品がruntimeを使うことを区別する。
Buildroot recipeの広い文字列検索にはOpenMPTなど似た名前も含めたが、該当16 packageは現在の正規化設定ですべて無効だった。
初回の旧構成imageの146 ELFにlibgompのDT_NEEDEDはなく、他fileのliteral参照と`GOMP_`もなかった。
追試では現行構成のCI成果物184 ELFを調べ、btrfs・cryptsetupを含めて同じ参照がないことを確認した。現行構成の削除前imageとの比較は未実施である。
実行時に名前を組み立てる未知のloaderや将来追加するpluginまで、不使用を証明したものではない。

固定版の一次資料: [Bootlinのselect](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/toolchain/toolchain-external/toolchain-external-bootlin/Config.in.options)、[外部toolchainのcopy](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/toolchain/toolchain-external/pkg-toolchain-external.mk)、[内部GCCの配送](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/gcc/gcc-final/gcc-final.mk)、[custom SDKの能力申告](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/toolchain/toolchain-external/toolchain-external-custom/Config.in.options)。

## 一次資料

- [固定Buildrootの設定定義](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/Config.in)、[Makeの変数照会](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/Makefile)
- [wrapperの生成引数](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/toolchain/toolchain-wrapper.mk)、[wrapperの処理](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/toolchain/toolchain-wrapper.c)
- [固定SDKのhash](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/toolchain/toolchain-external/toolchain-external-bootlin/toolchain-external-bootlin.hash)、[Bootlinの同版README](https://toolchains.bootlin.com/downloads/releases/toolchains/aarch64/readmes/aarch64--glibc--stable-2025.08-1.readme)
- [GCC 14.3の防御・計測](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Instrumentation-Options.html)、[AArch64の引数](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/AArch64-Options.html)
