# Host package・イメージ生成の設定面

[調査の入口](README.md)へ戻る。

## 49 host packageの役割

以下はSBOMのhost 49件を全て対応づけたもの。hostはBuildrootがbuild環境へ入れるものを指し、開発用OCIにAPTで入るpackageと同じ母集団ではない。選択版・recipe・Config.in・採取した変数は[package台帳](packages.csv)と[展開値](package-variables.json)にある。全てに独立CLIや利用者向け設定があるわけではない。

| component | 機能 | 制御するもの・注意点 |
|---|---|---|
| `host-acl`、`host-attr` | POSIX ACL・拡張属性のlibraryと関連機能 | 対象FS、xattr/ACLの保存と除外、権限。libraryのbuildと生成imageへの属性保存を分ける |
| `host-autoconf`、`host-autoconf-archive`、`host-automake`、`host-libtool`、`host-m4` | configure・Makefile・共有libraryのbuild手順の生成とmacro | 再生成する版、macro探索、cross判定、sysroot。hostの検出結果をtargetへ混入させない |
| `host-bison`、`host-flex` | parser・lexerの生成 | grammar、出力言語、診断、生成file、再現性。実行時daemonを増やすpackageではない |
| `host-blake3`、`host-xxhash` | hash計算のlibrary等 | 呼出し元のキャッシュ・照合用途。速いhashの存在を更新の署名方式と読み替えない |
| `host-ccache`、`host-hiredis` | compileキャッシュとRedis client library | `CCACHE_*`、compiler identity、base directory、容量・remote storage・統計。remote cacheの認証・共有境界・入力の信頼が必要 |
| `host-dosfstools`、`host-mtools` | FATの作成・操作 | FAT形式・label・sector/cluster、時刻・serial、imageファイルへの操作。最終boot imageの互換性を確認する |
| `host-e2fsprogs`、`host-util-linux` | ext系imageとblock/partition関連の生成・操作 | FS feature、UUID、label、block数、journal、予約領域、検査・拡張。target版と同じ設定とは限らない |
| `host-squashfs` | mksquashfs等による読み取り専用imageの生成 | block、compressor/level、xattr、所有者、時刻、並列数。host toolの対応compressorと実際に選ぶ形式は別 |
| `host-genimage`、`host-libconfuse` | 設定を解析し、FS/partition/disk imageを組み立てる | image/partitionのsize・offset・alignment・type、tool path、入力と一時領域。実機のboot layoutに合わせる |
| `host-fakeroot`、`host-makedevs`、`host-skeleton` | root権限を常用せず所有者・特殊file・基底directoryを準備 | device table、uid/gid/mode、fakerootの境界。仮想metadataと実image内の値を照合する |
| `host-dtc`、`host-kmod` | DTB/DTBOとmodule依存情報等の生成 | DTS include・symbol/overlay、moduleの版・圧縮・署名・探索先。hostのkernelに対する処理と混同しない |
| `host-patchelf` | ELFのinterpreterやRPATH等を変更 | SDK/host binaryの再配置、loader、RPATH/RUNPATH。変更前後のELFと実行可否を確認する |
| `host-libarchive`、`host-libzlib`、`host-lz4`、`host-lzip`、`host-lzo`、`host-pigz`、`host-xz`、`host-zstd` | archive・圧縮・展開のlibraryとtool | 対応format、level、辞書、thread、RAM、時刻、入力上限。hostの圧縮機能の数はtarget decoderの数ではない |
| `host-expat`、`host-libffi`、`host-libopenssl` | XML、FFI、暗号等のhost library | optional機能と呼出し元。kernel build用opensslとtargetの更新検証用opensslは別binaryとして扱う |
| `host-gettext-tiny`、`host-pkgconf` | 翻訳catalogとpackageのcompile/link metadata | locale/catalog、`.pc`の探索、sysroot、CFLAGS/LIBS。targetにhostのinclude/libraryを混ぜない |
| `host-meson`、`host-ninja` | cross buildの設定・実行 | cross file、`-D` project option、buildtype、b_lto/b_pie等、jobs。Buildrootが生成する値とpackageの上書きを読む |
| `host-python3`、`host-python-flit-core`、`host-python-installer`、`host-python-packaging`、`host-python-pypa-build`、`host-python-pyproject-hooks`、`host-python-setuptools`、`host-python-wheel` | Python interpreterとPEP 517等のbuild・wheel生成・install | build backend、分離環境、networkを使う依存解決、wheel tagとinstall先。host用helperをtarget用Pythonと数えない |

## 生成物に直結する設定

現行rootfsはSquashFS zstd、128 KiB block、極限圧縮level 22。`HOST_SQUASHFS_BUILD_CMDS`はxattr、xz/gzip/lz4/lzo/zstd等のtool側機能も有効にするが、配布rootfsがそれら全てを使うわけではない。単に「zstd有効」とするのではなく、mksquashfsの最終引数、superblockのcompression/block size、kernelのdecoderを照合する。

block・level・parallel数の候補は、配布サイズ、build時間とRAM、展開時CPU・RAM、読み取り量の背反がある。別compressor、EROFS、辞書の変更を行うなら、imageを作れたことだけで採用せず、起動・A/Bの容量・readback・電断時の回復まで同じ条件で比較する。今回、性能比較や形式の変更は行っていない。

genimage 20の上流READMEは、image、partition、flash、configとinclude、typeごとのoptionを定義する。対応typeにはext4、vfat、squashfs、erofs、verity等もあるが、対応していることはMSD/Linuxが使っていることを意味しない。`exec-pre`/`exec-post`等で外部commandも起動できるため、取得した設定を無検査で信頼境界の内側へ入れない。

FAT/ext4のUUID・serial・時刻・乱数・所有者、host toolの版、locale、umask、SOURCE_DATE_EPOCHが再現性を左右し得る。日時を揃える一つのoptionだけで再現性を保証せず、binary・image・SBOM・署名対象ごとにどこまで一致させるかを決める。署名鍵と乱数seedを固定することは、再現性のための既定の解決策にしない。

## 引数索引と限界

[configure option索引](configure-options.csv)は、hashを記録したsourceを全体展開し、28の`sh configure --help`を実行して採取した。hostとtargetが同じsourceを使う場合はsource単位の索引であり、適用済み設定の記録ではない。第1行の説明だけを収録するため、折返しの条件・既定値は元のhelpとソースへ戻る。

Autoconf以外は、OpenSSLのINSTALL/Configure、BusyBox Kconfig、Mesonの`meson_options.txt`、CMakeの`option()`/cache、Makeの変数等が設定面になる。例えばv4l-utilsのproject optionは、GUI・IR BPF・DVB・wrapper・plugin・32 bit/time64検査・install directoryを分けている。CLIの`--help`を一度読むだけで、全ての設定を列挙できたとはしない。

sourceの部分抽出だけで最初に実行したときは、28件中19件が失敗した。`AC_CONFIG_SRCDIR`が確認するsource fileの不足等によるもので、optionが非対応という結果ではない。全体展開後は28件がexit 0となった。失敗・修正方法と入力hashは[採取手順](reproduction.md)に保存する。mtoolsの`.tar.lz`は今回のPython tar抽出の対象外であり、設定がないという意味ではない。

## 一次資料

- [固定Buildrootのpackage群](https://github.com/buildroot/buildroot/tree/8b238854d909c9cce32ef9671d968b03e323b55d/package)。各componentへの相対pathは[台帳](packages.csv)に記録。
- [genimage 20のREADME](https://github.com/pengutronix/genimage/blob/v20/README.rst)、[SquashFSの上流](https://github.com/plougher/squashfs-tools)。実際に採取した版は[source archiveとhash](source-archives.json)を優先。
- [Buildroot manual](https://buildroot.org/downloads/manual/manual.html)。最新版の説明と固定sourceの差は、固定sourceを優先する。
- [台帳の生成コード](collect.py)。product buildやrecipeの実行はしない。
