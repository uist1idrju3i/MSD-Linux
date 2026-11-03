# 開発OCIの全APTと置換の単位

[比較の索引](README.md) / [構築基盤・開発・CI](development.md) / [母集団と比較の範囲](inventory-boundaries.md)

## 結論

最終amd64 OCIの231 APTは、129 source packageに由来します。[全行の対応](oci-coverage.csv)で、版・architecture・source・責務・Dockerfileでの直接選択・導入済みの逆依存・著作権資料のhashを記録します。物理的な同梱物の存在を、削除可能・API互換・安全という判定へ変換しません。

Docker内の新しいtoolchainを再現性の基準にする方針は維持します。VMへcompilerを入れて代用する案ではありません。Docker内でも、Buildrootのhost toolを作るcompiler、target用の外部cross toolchain、そのruntimeは別の層です。OCIからGCCを除く案だけでtarget libcが置き換わるわけではありません。

## 129 sourceを責務へ対応づける

次表の分類は、[照合script](../../experiments/2026-11-03-alternative-coverage.py)の`FAMILIES`に全source名を列挙した閉じた集合です。新しいsourceを自動的に「その他の調査済み」へ入れません。個々のbinary packageと逆依存はCSVを参照します。

| 分類 | 現在の責務と具体例 | 代替・削減と背反 | 採用前に必要な確認 |
|---|---|---|---|
| base | apt/dpkg、debconf、shadow、systemdのlibrary、tzdata、keyring等。PID 1やdaemonが全て動いているという意味ではない | Debian維持とsnapshot更新を基準とし、別系列、Nix/Guix等の固定環境、Alpine、用途別stageへの分離を比較する。baseのEssentialを手作業で削るのでなく、基盤とrootfs生成の契約を変える | UID/GID、locale、時刻、CA/bootstrap、package署名、Buildrootのhost前提、両CPU、復旧手順。OCI label一つで全内包物のlicenseを代表しない |
| commands | Bash、dash、coreutils、find/diff/grep、sed、gawkとmawk等 | [BusyBox・Toybox・uutils・GNU](commands.md)を候補にできるが、targetの小さなコマンド構成を開発OCIへそのまま適用しない。複数awkやshellの削減は呼出元・引数を確かめてから | Buildrootの事前検査、GNU拡張、shellの意味、NUL付きpath、negative fixture、文書/生成scriptを含めた全呼出し |
| compiler | GCC/defaults、binutils、glibc、Linux headers、GMP/MPFR/MPC/ISL等 | [Clang/LLVM・Zig・別libc](toolchains.md)は別の選択肢。GCCの内部数値libraryだけを別ABIへ差し替える案ではない。Debian packageの版統一、別のOCI内toolchain、compiler stage分離を比較する | compiler自体と生成物、Buildroot host検査、cross compilerの実効flags、LTO/linker/plugin、C++ runtime、headers/sysroot、SBOM/再現性 |
| build | make、CMake、Bison/Flex、M4、Perl、patch、補助hash/option library | [構築部品](build-support.md)の選定と親projectのbuild system移植を分ける。makeをNinjaへ入れ替えただけで既存Makefileは動かない。検査専用imageではcompiler等を分離する候補 | configure/生成物の同等性、host toolの再生成、必要な正規表現・parser、Buildrootによる導入、stageを増やした保守/cache費用 |
| python | CPython、venv/pip wheel、setuptools、Expat、libffi、gdbm、SQLite等 | [Python構築](host-interfaces.md)のfrontend/backend/installerを分離して比較する。最終zizmor環境でpipを外しても、開発用Pythonのvenv機能の全依存は消えない | Buildroot/QEMUの使用module、Python版、wheel/tag/hash、削除前後のimport、source buildの禁止、license・native依存。CPythonと別VMの実行同等性は未確認 |
| images | cryptsetup/dm、SquashFS、e2fsprogs、FAT/mtools、cpio、dtc、ELF、file/libarchive等 | [生成部品](build-support.md)と[保存形式](filesystems.md)を分ける。EROFS採用でmkfsを追加・交換する案はrootfs/更新/bootの変更を伴う。libarchiveは各専用CLIの全引数の代替ではない | 4 MiB整列、permission/xattr/uid、volume識別子、A/B、verity、生成物の独立検査、既存shellの引数、壊れた入力 |
| compression | Brotli、zlib、zstd、xz、LZ4/LZO、bzip2、tar/unzip、xxHash等 | [形式・API・streamingの比較](build-support.md)を使う。同じ圧縮形式への対応だけでAPI互換としない。未使用形式の無効化は親toolのbuild optionと配布物を確認する | 展開する上流配布形式、kernel/imageの対応、memory/size/time、壊れたarchive、静的リンク・license。Brotliの修正延期を削除やgate緩和で代替しない |
| transport | Git、curl、wget、rsync、HTTP/2・3、IDN、PSL、SSH2、RTMP等 | downloaderの統合、不要protocolの無効化、curl等の最小buildは候補。APTの推移依存は、その親を変えずlibだけ抜かない。Gitのfetchは単純HTTP downloadの代替ではない | proxy、redirect、証明書、credential送信先、retry、mirror、IPv6、submodule、protocol、HTTP失敗伝搬、署名/hash確認。downloadをbuild前へ移す案はnetwork封鎖と再現性の別試験が必要 |
| auth | OpenSSL、GnuTLS/nettle、SASL、LDAP、Kerberos、PAM、keyutils、seccomp等 | [暗号](crypto.md)と各親のbuild optionを通して削減する。複数TLSが存在することだけで一方を削れない。container内にPAM等があることと、network認証サービスの稼働は別 | 親binaryのリンク・動的load、Git/curl/apt等の機能、FIPSや旧算法、実行権限、明示的な拒否試験、配布義務と保守系列 |
| qemu | GLib、pixman、libslirp等のQEMU runtime | QEMUの`--disable-*`で到達する機能を減らす候補と、[別model/Renode](development.md)への移行を分ける。slirpを外すとguest network試験を失う可能性がある | machine、headless表示、network、plugin ABI、既存QEMU試験。QEMU build stageと最終runtimeのpackageを混ぜない |
| helpers | ACL/xattr、DB/parser、terminal、readline、PCRE、process情報、capability/SELinux library等 | 各親と動的リンクの境界を通じて削減する。XML/JSON/parser/regexを同種だからと無条件に交換しない。[host API比較](host-interfaces.md)を併読する | 逆依存だけでなくdlopen・実行時data・script呼出し、機能とerror、locale/encoding、ABI、license。新しいsourceは個別に分類し直す |

これらは置換単位の提案です。各129 upstreamの全option、全license、EOLの独立監査や、候補を組み合わせたOCIのbuild・実行は本リポジトリでは試していません。

## 直接導入・推移依存・baseを分ける

`selected_in_final_stage`は固定Dockerfileの最終stageの`apt-get install`に明記したpackageです。`false`は不要という意味ではなく、base由来・推移依存・既定のtoolchain package等を含みます。`installed_reverse_dependencies`はDependsとPre-Dependsに記載された、導入済みの候補への辺です。alternativesのどの分岐をAPTが採用したか、Provides、実行時load、scriptの呼出しを完全に解決したgraphではありません。原文の依存式は[採取metadata](oci-package-metadata.json)に残します。

削減するなら、まず検査専用の軽い環境と、製品build/QEMUの環境を分ける案を試します。full OCIの機能を削って全jobを速くする案より、不要なjobへcompiler/QEMUを配らない案です。一方で、入力固定、2種類の環境の保守、共通test、両CPUの検査が増えます。現在のcache/OCI再利用の[調査](https://github.com/uist1idrju3i/MSD-Linux/blob/3914ad3dc104138e4a9be2f3250f23151a7a3e81/docs/research/ci-build-scope-and-performance.md)と合わせて費用を測るまで採用しません。

## 著作権資料と保守の範囲

同じdigestのOCIで231件全ての`/usr/share/doc/<package>/copyright`を読み、bytes・SHA-256を記録しました。CSVの`observed_license_fields`は先頭が`License:`の行を機械抽出したJSON配列です。自由形式の文書、続きの行、各fileの適用範囲、exception、静的リンク等を完全に解釈したSPDX式ではありません。空配列はlicenseなしではなく、その形式の欄を抽出しなかったことを示します。配布適合の認定には使いません。

導入版とDebianの更新候補は[APT台帳](../dependencies/development-apt.json)にあります。Debian側のbackportとupstream版・EOLは別です。snapshotの固定を維持したまま、保守更新・署名・期限・差分・機能の検査を経て新しいsnapshotへ移す設計を基準にします。これを実行済みの更新とは扱いません。

Go module 11件は[親actionlintとの対応](go-coverage.csv)へ記録しました。globbing、色・terminal、shellword、cron、YAML、同期、syscall等の実装を別libraryへ換えるなら、actionlint側のsource変更とtestが必要です。当リポジトリでbinary内のmoduleだけを入れ替える案ではありません。moduleごとの別major・license・到達性の監査は残ります。

[比較の索引へ戻る](README.md)
