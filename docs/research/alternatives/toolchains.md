# コンパイラー・linker・ランタイムの代替比較

[代替比較](README.md) / [RESEARCH](../../../RESEARCH.md)

## 現行の基準

2026-11-02に固定設定と一次資料を照合しました。製品設定は変更していません。以下の代替構成は本リポジトリでは試していません。

[defconfig](../../../configs/msd_cardputerzero_defconfig)は外部Bootlin AArch64/glibc stable toolchainを選びます。固定したSDK `2025.08-1`のREADMEは、GCC 14.3.0、binutils 2.43.1、GDB 15.2、glibc `2.41-70-g1502c248d58cb99a203731707987a4342926e830`を記載しています（資料T1）。Buildroot内蔵toolchainの既定版や上流最新版とは別です。glibcを2.44として現行SDKの機能を評価しません。

| 層 | 実行先・役割 | 置換で確認すること |
|---|---|---|
| GCC / Clang | host上でtarget向けのC/C++・assembler入力を生成 | GNU拡張、inline asm、警告、最適化、CPU・sysroot・headers |
| GNU binutils / LLVM utilities | host上のassembler、linker、archive、ELF操作 | linker script、relocation、LTO plugin、`objcopy`・strip・debug情報 |
| libgcc / compiler-rt builtins | target側で除算・変換等を補助 | compilerが生成する未定義参照、atomic、stack protector等との組合せ |
| libgcc_s / libunwind | target側で例外・stack unwindを処理 | 同じprocess中のC++ ABI、例外、signal、shared object |
| libstdc++ / libc++ とC++ ABI library | target側のC++標準APIと例外・RTTI等 | Cライブラリーとは別。標準APIが同じでもbinaryの置換互換性は別問題 |
| glibc等 | targetのC/POSIX・Linux API | [libc比較](libc.md)を参照。Clangを選んでもLLVM libcを選ぶ必要はない |

SDKに存在するライブラリーと、最終rootfsに実際に入るライブラリーも区別します。不要なC++ runtimeを置換するために、新たなC++ runtimeを製品へ入れることは提案しません。

## コンパイラーの候補

| 候補 | 必要な機能との対応・利点 | 費用・制約・削除時の影響 | 再評価 |
|---|---|---|---|
| 現行GCC + GNU binutils | 現行Buildroot、Raspberry Pi kernel、M5 moduleの比較基準を保てる。SDKとして一式が固定済み | 外部SDKの内包物と更新を別に監視する必要がある。GCC固有pluginを使えるかもSDKの構築条件次第 | 現行維持。古いバージョンを使うこと自体を目的にせず、SDK更新とcompiler変更を分離して検証 |
| Clang + 現行GNU sysroot/runtime | Clangだけを置換し、glibcやC++ runtimeの変更を避けて差を調べられる（T2） | `--target`だけではsysroot・startup object・runtimeの選択は確定しない。GNU拡張・警告・asm、link先を確認する必要がある | 優先する実験候補。compiler単体の差を測る |
| Clang + LLVM utilities/runtime | kernel公式が`LLVM=1 ARCH=arm64`を説明する（T3）。LLVMのLTOやcompiler固有の保護機能を検討できる | hostのLLVM一式、builtins、unwinder、linker等の固定が増える。Buildroot全体・全M5 moduleの対応を意味しない | kernelと全外部moduleを一組にした実験候補 |
| ZigのC/C++ compile driver | 公式overviewはC/C++ compilerとしての利用とcross compileを説明する（T4）。個別のhost/helperやSDK配布を簡素化する余地 | Zig自身と内包するClang・libc等も監視対象になる。`zig cc`を`CC`に指定するだけでBuildroot・kernelの全処理が対応するとは限らない | 用途限定の実験候補。OS全体の既定置換より、小さいhelperから調べる |

Clangを導入することと、OSのユーザー空間をC++やRustで書き直すことは別です。Zigの小さいサンプルやClangの公開性能値も、MSD/Linuxのimage・起動時間の値にはできません。

## LLVMとGNUのruntimeは一括選択ではない

Clang公式のtoolchain資料（T2）は、構成要素とtargetによってruntimeの既定が変わることを説明しています。

| 選択 | 一次資料で確認した条件 | 本機で必要な検証 |
|---|---|---|
| `--rtlib=compiler-rt` | builtinsの選択であり、すべてのplatformが対応するわけではない | AArch64用runtimeの実体・hash、compilerが生成した全参照の解決 |
| `--rtlib=libgcc` | libgcc_sはClangが生成する一部のoverflow builtinを提供しない場合がある | 実際のtargetコードをlinkし、未解決参照や意図しないhost混入を検査 |
| atomic support | libgcc_s構成ではnon-native atomicに`-latomic`が必要な場合があり、Clangが自動で追加するとは限らない | `__atomic_*`、lock-freeの前提、`DT_NEEDED`を調べる。AArch64なら全atomicが同じ費用とは決めない |
| unwinder | libgcc_sはunwinderを含む。libc++abiはLLVM libunwindを使う設定も持つ | 例外をshared object境界で送る試験、C++ ABI実装の重複を検出 |
| sanitizer | Clangのsanitizerは対応するcompiler-rt runtimeを必要とする | 試験用imageでのRAM・CPU・kernel条件。製品へ無条件で同梱しない |
| C++標準ライブラリー | libc++とlibstdc++は同じものではない。公式は低レベルの一部ABI互換を述べるにとどまる（T5） | STL型を共有する境界を全て再build。libstdc++自体にもdual ABIの選択がある（T6） |

未リリースなのでC++ ABIを変えられるとしても、異なるABIの部品を混ぜてよいわけではありません。外部binaryを残すならその制約を調べ、残さないなら全体を同じ構成で作り直します。

## kernel・moduleと最適化の境界

- kernel公式はconfigureとbuildで同じ`LLVM=`指定を使うよう求めます（T3）。AArch64ではcross compiler prefixが不要になる構成もありますが、GNUの一部toolを混ぜる場合等の条件は同資料に従います。
- M5の外部moduleも同じkernel出力・compiler・headers・保護設定で再buildします。kernelだけ起動できても、16個のM5 moduleやDeviceTree、必要機能の検証は終わりません。
- GCC LTOのobjectとLLVM bitcodeを、同じLTO入力として扱いません。linkerとpluginを含む一式を固定し、通常objectとの混在可否を実際のlinkで確認します。
- `BR2_ENABLE_LTO=y`は全packageに適用した証拠ではありません。package recipe、展開後のcompile/link引数、生成ELFを調べます。設定名だけでサイズ・速度向上を報告しません。
- compiler固有のCFIやGCC pluginは、保護範囲・module互換・未対応箇所・性能費用を含めて比較します。Cortex-A53にないCPU機能を前提とする保護を、Kconfigで選べるだけで実効化したとしません。

## 保守・ライセンス・検証の費用

GNU、LLVM、Zigの開発は別々です。Buildrootの固定だけでZig内包のLLVMや外部SDKのglibcまで同じsecurity対応になるわけではありません。compiler binary・source・runtime・sysrootのバージョンを別々に記録し、security advisoryの修正が自分の固定版へ入ったか確認します。

LLVMのlibc++・libcは原文のLICENSE.TXTでApache-2.0 with LLVM Exceptionsを確認しました（T7）。これは外部SDK全体やGNU runtimeの配布条件の確認完了ではありません。LLVM内の例外・第三者由来部分、GNU側のruntime例外、headers、再配布するSDKの全ライセンスと対応sourceを別途照合します。ライセンスの違いだけでcompiler・runtime一式を不要とする判断はしません。

採用前には、基準SDKを一つ残し、次の順で差を一つずつ作ります。以下は未実施の検証案です。

1. 同じglibc・headers・runtimeでGCCとClangを比較する。`-###`等のdriver出力、sysroot、ELFのinterpreterと`DT_NEEDED`、CPU属性を保存する。
2. kernelと全M5 moduleを同じLLVM構成で作り、module署名・vermagic・依存、image layout、両slot起動、更新拒否・rollback、GPIO6 smokeを確かめる。
3. 必要ならcompiler-rt・linker・C++ runtimeを一要素ずつ切り替える。設定・recipe・生成物の差から、何が効果を生んだか分離する。
4. 全条件で5回以上、build時間・最大RAM・imageとELFのサイズ・起動終点・失敗を記録する。QEMUと実機の結果を分ける。
5. libcの変更はさらに別の構成で試す。最新系に変えただけの差を、compilerやlibcの実装差と混同しない。

数値の改善幅は未測定です。現段階の推奨は現行を比較基準に残し、まずClang + 同じsysroot、次にkernel + 全外部moduleを調べることです。glibc、init、暗号まで同時に変える案は原因を追いにくくするため、最初の実験には勧めません。

## 一次資料

本文確認日は2026-11-02 UTCです。取得時刻と本文のhashは[sources.json](sources.json)を参照してください。

| ID | 資料と確認範囲 |
|---|---|
| T1 | [固定BuildrootのBootlin定義](https://github.com/buildroot/buildroot/tree/8b238854d909c9cce32ef9671d968b03e323b55d/toolchain/toolchain-external/toolchain-external-bootlin)、Bootlin SDKのREADME。SDK内包版とBuildroot内蔵版を区別 |
| T2 | [Clang Toolchain](https://clang.llvm.org/docs/Toolchain.html)。runtime・atomic・unwinder・C++ libraryの条件 |
| T3 | [固定Raspberry Pi kernelのLLVM資料](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/kbuild/llvm.rst)。arm64とconfigure/build時の指定 |
| T4 | [Zig overview](https://ziglang.org/learn/overview/)。C/C++ compiler・cross compile。サンプルの性能値を本機へ転用しない |
| T5 | [libc++](https://libcxx.llvm.org/)。機能・ABI互換の範囲。開発中のrelease noteへのリンクを安定版の公開とは扱わない |
| T6 | [GCC 14.3のlibstdc++ manual原文](https://github.com/gcc-mirror/gcc/blob/releases/gcc-14.3.0/libstdc++-v3/doc/xml/manual/using.xml)。`_GLIBCXX_USE_CXX11_ABI`の型・ABIへの影響 |
| T7 | [LLVM libc++のlicense](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libcxx/LICENSE.TXT)、[LLVM libcのlicense](https://github.com/llvm/llvm-project/blob/7a35ab1791fbfc25a0ab56b14693a516cf205bbe/libc/LICENSE.TXT) |
