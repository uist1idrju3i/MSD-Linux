# 基本コマンド・シェルの代替

[代替比較の索引](README.md)へ戻る。

## 結論と確認範囲

BusyBoxを比較基準に残し、まず必要なコマンドと引数を確定してから、applet削減、Toyboxとの部分的な併用、必要なGNUコマンドだけの追加を比較する案を勧めます。uutilsも候補から除外しませんが、Rustという実装言語やGNU互換という目標だけで、更新処理に使えるとは判断しません。

これは製品設定の変更ではありません。Toybox、GNU coreutils、uutilsで置換した製品のbuild・実行は、本リポジトリでは試していません。2026-11-02に上流資料を確認し、現行ソースは`8aaf2e1958fd71b571a2f40cbe8199409c931c37`、Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`を基準にしました。取得の状態とhashは[sources.json](sources.json)に記録します。

## 何を置き換えるのか

BusyBoxは単なるcoreutilsではありません。現行ではshell、PID 1、device管理、ネットワーク関連のappletも提供します。これらはtarget/runtimeの直接選択ですが、実際のELFに入るlibc等は別の依存です。host/CIのGNUコマンドを製品に入れ替える比較とは分けます。

設定元はBuildrootの[busybox.config](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/busybox/busybox.config)と[製品fragment](../../../board/cardputerzero/busybox.fragment)です。default側に`ASH`・`INIT`・`MDEV`・`UDHCPC`・`SETPRIV`、fragmentに`FSYNC`・`DESKTOP`・`FEATURE_DD_IBS_OBS`・`FEATURE_MD5_SHA1_SUM_CHECK`があります。ここで読んだのは設定元であり、全appletの最終config・ELF・実効権限の再確認ではありません。

| 現行の利用箇所 | 失ってはいけない契約 | 置換時の注意 |
|---|---|---|
| [更新処理](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) | `dd iflag=count_bytes`、`dd conv=fsync`、`sha256sum -c`、fileとdirectoryへの`fsync`、rename、mount/umount | 同名コマンドでも引数・終了値・永続化の意味が違えば置換できない。coreutilsだけで`fsync`・tar・awk・shell等が全てそろうわけではない |
| 同じ更新処理のbundle検査 | tar一覧の型・member検査、awk、grep、sed、hash照合 | locale、空白・改行を含む名前、symlink、path traversal、重複member、途中失敗時の出力を含める。検査と展開の別解釈を防ぐ |
| [data初期化](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data) | blank領域だけの初期化、magic確認、fsckの終了値、mount option | `dd`・`cmp -n`・`od`等を省くと、未知の非空領域を拒否する条件が変わり得る。e2fsprogsの代替比較とは分ける |
| [device初期化](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S10mdev) | mdev daemon、sysfsのcoldplug、NUL区切り、modprobe | `find`・`xargs`・`sort`・`tr`の引数とパイプラインを調べる。device管理自体は[initの比較](init.md)で扱う |
| 起動・対話・復旧 | `/bin/sh`、init、getty/login、watchdog、調査用コマンド | 通常起動のtraceに現れないコマンドも必要。更新拒否、rollback、電源断、復旧用consoleを対象にする |

この表は重要な利用例であり、全コマンドの閉じた一覧ではありません。将来のWi-Fi、DHCP、DNS、firewall、更新取得が使うコマンドも、導入時に加える必要があります。CのABIを維持していても、shellから見る引数・出力・終了値の契約は壊せます。

## 候補の比較

| 候補 | 利点・必要機能との関係 | 制約と費用 | 提案 |
|---|---|---|---|
| BusyBox | 小型のmulti-call utility。既存のshell/init/mdevと統合済み（C1） | 共有実装の修正が複数appletに及ぶ。不要appletの削減と保守用機能の確保が必要 | **現行維持**。安全性や最小サイズの認定ではない |
| Toybox | 0BSD。POSIX等を目標とし、Androidでの利用実績がある（C3） | GNU/BusyBox固有optionは別確認。通常実装・pending・未実装のstatusを分ける。Android採用は本機のshell/init/mdevの置換完了を示さない | **実験候補**。BusyBoxを丸ごと削る前にコマンド単位で比較 |
| GNU coreutils | GNUの引数・出力が必要な処理の基準。固定Buildrootにpackageがある（C4） | shell、tar、awk、init等は別。GNU拡張を増やすほど最小構成へ戻す費用が増える。サイズ・RAM差は未測定 | **用途限定**。必要な機能に根拠がある場合だけ追加 |
| uutils coreutils | RustによるGNU coreutils再実装。全programを実装済みとするが、欠けたoptionや挙動差も明記（C5） | Cargo依存・cross build・Rust runtimeの構築条件、GNUとの差を確認する必要がある。coreutils外の機能は別 | **実験候補**。非特権のコマンドから比較し、署名付き更新へ直ちに投入しない |

固定BuildrootにはGNU coreutilsのrecipeがあり、既定はsymlink付きsingle binaryです。個別binaryを選ぶ設定もありますが、動的libraryを必要とします（C4）。「GNUは常に個別binaryだから不利」とは評価しません。同じ固定treeの`package/toybox`・`package/uutils`は確認できず、追加recipeと監視・license・cross-buildの整備費用を見込みます。これは上流のLinux/AArch64非対応を意味しません。

どの候補もAArch64向けに作っただけではCortex-A53での全命令・syscallの動作を保証できません。host由来の`-march=native`、配布済みbinaryのglibc下限、必要なCPU拡張、loaderと`DT_NEEDED`を確認します。uutilsの安定releaseは取得時のAPIで`0.12.0`でしたが、READMEを確認した開発commitと同一の内容とは限りません。

## 保守・security・配布

| 候補 | 今回確認できた範囲 | 採用前に残す条件 |
|---|---|---|
| BusyBox | 固定recipeは1.38.0。上流の公開案内はこれをunstableと表記する（C2）。Buildroot側にはsecurity patchとCVE処理理由がある | 上流の版名だけでなく、適用patchを照合する。`security.html`は404だったため、この取得失敗を窓口不存在や安全性の証拠にしない |
| Toybox | 公式licenseページは0BSD、current releaseは0.8.15（C3） | 固定source・各機能の状態・release差・securityの連絡経路を採用時に確認する。公開statusを本機の検証結果にしない |
| GNU coreutils | 固定recipeは9.10、`GPL-3.0+`。公式はbug報告とsecurity連絡を案内する（C4） | 配布source・改変・notice・build条件をlegal-infoと対応づける。別のGNU utilityのlicenseまで一括処理しない |
| uutils | LICENSEはMIT。SECURITYは原則として最新releaseだけにsecurity更新を提供し、権限境界・filesystem race・untrusted input等をscopeにする（C5） | 固定版を長期維持できるとは限らない。依存crateとbuild/test helperのlicense・advisoryを別に照合し、入力がroot処理へ渡る経路も確認 |

BusyBoxの固定recipeは`GPL-2.0`と内包bzip2部分の`bzip2-1.0.6`を記録しています。上流のlicense説明に従い、配布するbinaryに対応するsourceと構築・改変条件を提供できるようにします（C1）。MITや0BSDへの変更を、kernelや残るGPL部品の配布義務の解消とは扱いません。今回は外部コードを取り込んでいません。

小型binaryにまとめることと、root権限を与えることは別です。`FEATURE_SUID=y`も、実物にsetuid bitが付いている証拠ではありません。binaryのmode、owner、capability、呼出し元のUID/GID、環境変数、引数と入力fileを確認します。Rustでも論理誤り・path traversal・不適切な権限は残るため、「memory安全だから更新処理も安全」とは評価しません。

## 過去の見送りをどう再評価するか

[BusyBox実験](../../experiments/2026-10-21-qemu-busybox.md)では、静的linkとapplet削減のready時間は事前の改善基準に届かず、反復起動する`true`のloop時間は基準を満たしました。サイズとの背反があり、glibc NSSの確認はroot・local fileに限られ、静的linkと削減の組合せは試していません。このセッションで再実行した結果ではありません。

したがって、applet削減を恒久的に不採用とはしません。通常起動、更新、復旧、対話、ネットワークの必要集合を定めたうえで再実験する価値があります。一方、QEMU/icountの値を実機の速度やSDの書込み性能へ読み替えず、静的化でrootfs全体が必ず小さくなるとも主張しません。

## 採用前の試験

以下は未実施です。候補ごとに同じtoolchain・libc・kernel・機能集合を使い、変えた要素を記録します。

1. scriptとinittabの静的な呼出し一覧に、通常・失敗・更新・rollback・保守の動的traceを加えます。shell builtin、絶対path、PATH探索、symlinkの行先、optional appletを区別します。
2. 引数だけでなく、stdout/stderr・終了値・locale・signal・timeout・partial I/O・rename・file/directoryのfsyncを比較します。一般利用者とrootで同じ失敗条件を与え、既存の[更新回帰試験](../../../tests/msd-update/run.sh)と拒否試験をtargetでも実施します。
3. duplicate commandのinstall順、古いsymlink、呼び分け、fallbackを検査します。GNU系でhost testが通っても、targetのBusyBox/Toyboxで通ったことにはしません。
4. image/ELFのbytes、依存、最大RAM、起動・停止、build時間、反復コマンドのCPU時間を5回以上記録します。失った機能・初回・失敗も残し、同じ機能で比較します。
5. A/Bの両slot、署名・hash拒否、readback、rollback、電源断、復旧console、周辺deviceのsmokeを確認します。更新途中で代替コマンドが欠ける構成は採用しません。

## 一次資料

| 記号 | 資料と読んだ範囲 |
|---|---|
| C1 | [BusyBox公式](https://www.busybox.net/about.html)と[license](https://www.busybox.net/license.html)。multi-call utilityの目的、source提供、配布条件 |
| C2 | [BusyBox公開案内](https://www.busybox.net/)、固定Buildrootの[recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/busybox/busybox.mk)。版・patch・license。上流changelog全件の精読とはしない |
| C3 | [Toybox公式](https://landley.net/toybox/)、[license](https://landley.net/toybox/license.html)、[status](https://landley.net/toybox/status.html)。目的・配布条件・機能ごとの状態 |
| C4 | [GNU coreutils公式](https://www.gnu.org/software/coreutils/)、固定Buildrootの[設定](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/coreutils/Config.in)と[recipe](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/coreutils/coreutils.mk)。single binary・依存・license |
| C5 | [uutils README](https://github.com/uutils/coreutils/blob/6201c4fd963c9e5cc43579b45b26d9a38941ece2/README.md)、[LICENSE](https://github.com/uutils/coreutils/blob/6201c4fd963c9e5cc43579b45b26d9a38941ece2/LICENSE)、[SECURITY](https://github.com/uutils/coreutils/blob/6201c4fd963c9e5cc43579b45b26d9a38941ece2/SECURITY.md)、[Cargo設定](https://github.com/uutils/coreutils/blob/6201c4fd963c9e5cc43579b45b26d9a38941ece2/Cargo.toml)。目的・制約・連絡経路・依存の入口。全crateの閉包監査は未完了 |
