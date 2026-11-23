# module binary indexの配送を見直すための監査

- 状態: 利用者を検出したため削除前に停止。製品の変更・build・QEMU試験は未実施
- 日付: 2026-11-23
- 基準: `723b664abc1e6bde1a4010261bb90a082e0c6ebc`
- 関連: [kernelの設定面](../research/component-options/kernel-firmware.md)、[以前のOpenSSL設定実験](2026-11-18-openssl-cnf.md)

## 目的と停止条件

容量候補1として`modules.*.bin`の削除を検討する。依頼時の条件は、読む利用者がいれば削除せず、理由を記録して止めることだった。
通常起動と、repositoryに残る測定器の利用を分けて調べた。測定器からlibkmodを使う経路があるため、ここで停止する。
この記録は削減実験の成功報告ではなく、既存artifactの容量確認とsource監査である。

## 条件と確認方法

| 項目 | 条件 |
|---|---|
| host | Ubuntu 26.04.1 LTS、GNU readelf 2.46 |
| Buildroot | `bbbdab36565d4941b6b0449a0eedb5aac8a10c2e` |
| 部品 | BusyBox 1.38.0、kmod 34.2。版は今回変更しない |
| 新規設定の正規化 | `O=output-module-index-config`。defconfig生成だけで、製品のcompileは行わない |
| 容量の対象 | 既存`output-integrity/target`と`images/rootfs.squashfs`を読取り専用で確認。現HEADから新規buildしたものではない |
| 回数 | 静的なfile容量とsourceの単回監査。時間の中央値・性能差は測定しない |
| 結果 | [CSV](2026-11-23-module-binary-index.csv)、[入力hash・ELF監査・保存log照合](2026-11-23-module-binary-index.json) |

rootfsの通常fileはsymlinkを除き、hardlinkをdevice/inodeで一度だけ数えた。146 ELF全てに`readelf -d`を実行し、
`(NEEDED)`のlibrary名を抽出した。少なくとも一つのELFで空でないNEEDEDを得ることを対照にした。
SONAMEに自分の名前があることを利用者とは数えない。libkmod自身以外のELF内に`libkmod`という文字列があるかも調べた。
通常fileの集計は展開後の論理bytesであり、SquashFSの圧縮後容量やSD上の占有量とは別である。

## 通常起動はBusyBoxを使う

1. `S10mdev`は`modprobe -abq`でcoldplugし、`etc/mdev.conf`のmodalias規則も`modprobe`を呼ぶ。
   `S98msd-ready`のmodule確認も同じcommandを呼ぶ。既存artifactの`/sbin/modprobe`は`../bin/busybox`へのsymlinkだった。
2. defconfigには`BR2_PACKAGE_KMOD_TOOLS=y`があるが、[Buildrootの依存条件](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/kmod/Config.in)は
   `BR2_PACKAGE_BUSYBOX_SHOW_OTHERS`を要求する。新規に正規化しても同symbolは無効で、KMOD_TOOLSの指定は残らなかった。
   kmod libraryの有効化と、kmod CLIの配送を混同しない。
3. 既存BusyBoxの設定は`CONFIG_MODPROBE=y`、MODPROBE_SMALL無効、ALIAS/SYMBOLS有効、DEFAULT_DEPMOD_FILEは`modules.dep`。
   [modprobe.c](https://git.busybox.net/busybox/tree/modutils/modprobe.c?h=1_38_0)の`load_modules_dep()`、`read_config()`は
   テキストの`modules.dep`・`modules.alias`・`modules.symbols`と`modules.builtin`を読む。
4. 146 ELFにlibkmodへのDT_NEEDED利用者はなく、他のELF内にもlibkmod名の参照は見つからなかった。
   これは当該artifactの確認であり、将来のpackage追加や任意のdlopen名生成まで否定する証明ではない。

kmod CLIが有効になれば事情が変わる。[recipe](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/kmod/kmod.mk)は
BusyBoxより先にmodutilsのcommandを配置し、BusyBoxのinstall-noclobberは置換しない。
現在のBusyBox経路だけを根拠に、他の構成でも削除してよいとは扱わない。

## 停止理由は既存測定器のlibkmod利用

製品へ自動配送されるcallerは見つからなかった。一方、次の測定経路はrepository内に残っている。

- [run.py](../../board/cardputerzero/tools/bench/openssl-cnf/run.py)のprepareは`module.c`を`-lkmod`でlinkし、boot時に`/run/kmod-probe`へ転送する。
- [guest.sh](../../board/cardputerzero/tools/bench/openssl-cnf/guest.sh)は`check module /run/kmod-probe`を実行する。
- [module.c](../../board/cardputerzero/tools/bench/openssl-cnf/module.c)は`configs`を名前で生成し、`kmod_module_probe_insert_module()`を呼ぶ。
- 未loadのmoduleでは、[libkmod-module.c](https://github.com/kmod-project/kmod/blob/v34.2/libkmod/libkmod-module.c)のprobe list生成から
  `kmod_module_get_dependencies()`、`module_get_dependencies_noref()`、`kmod_search_moddep()`へ進む。
  [libkmod.c](https://github.com/kmod-project/kmod/blob/v34.2/libkmod/libkmod.c)の`lookup_file()`は`modules.dep.bin`を開く。
  ここにテキスト`modules.dep`へのfallbackはない。[同版のmanual](https://github.com/kmod-project/kmod/blob/v34.2/man/modules.dep.5.scd)も区別している。

反証として「libraryは配送されるだけで誰も呼ばない」可能性を調べたが、保存済みOpenSSL実験の正式12 bootでcaller実行と終了0を確認した。
証拠archive内のserialにあるguest logをdecodeすると、12件全てで`libkmod configs load rc=0`だった。現行`module.c`とarchive内の写しもbyte一致した。
ただし、既にload済みならprobeは早期returnし得る。過去の各bootでのindexのopen syscallまでは観測しておらず、削除後の失敗も新規に実験していない。
停止の根拠は、維持中の測定器にbinary indexを必要とするload経路があることで、全bootで同じfileを開いたという主張ではない。

## 現状容量と未実施の比較

| 対象 | 既存artifactのbytes | 削除後 |
|---|---:|---|
| rootfsの通常file合計 | 37,049,861（1,411 file） | 未実施 |
| rootfs.squashfs | 20,500,480 | 未実施 |
| modules.dep.bin | 141,048 | 削除しない |
| modules.builtin.bin | 19,011 | 削除しない |
| modules.alias.bin | 442,710 | 削除しない |
| modules.builtin.alias.bin | 95,714 | 削除しない |
| modules.symbols.bin | 239,799 | 削除しない |
| binary index計 | 938,282（約0.895 MiB） | 削除しない |

938,282 bytesは対象fileの非圧縮合計で、圧縮後の削減量ではない。新規imageを作っておらず、容量差・起動時間の改善・module loadの同等性は未測定である。
停止条件に達したのでpost-build、sort list、module本体、vendorは変更しない。新しい製品buildとQEMU A/Bは実行せず、過去の成功を今回の受入試験へ転用しない。

## 再確認の手順と再開条件

repository rootから設定を正規化できる。出力先は未使用のものを選ぶ。

```sh
make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output-module-index-config" msd_cardputerzero_defconfig
grep -E 'BUSYBOX_SHOW_OTHERS|KMOD' output-module-index-config/.config
readlink output-integrity/target/sbin/modprobe
find output-integrity/target/lib/modules -name 'modules.*.bin' -printf '%P %s\n'
stat -c '%s' output-integrity/images/rootfs.squashfs
```

inputのSHA-256、ELFごとのNEEDEDとhash、既存archiveのhashと正式12 serialのhashをJSONへ保存した。
既存rootfs/imageの再取得元は今回確認しておらず、これらの容量を最新mainのbuild結果として再現できるとはしない。
module callerのrawはrepository内の[既存archive](2026-11-18-openssl-cnf-evidence.tar.gz)にあり、今回上書きしていない。
既存の失敗bootもarchiveに保持し、今回引用した正式12件と混ぜない。

再開には、通常製品だけを対象にしてこの測定器を対象外としてよいか、測定器の変更も許可するかの判断が必要である。
選択肢はBusyBox経由の署名付きmodule試験への変更、または測定時だけbinary indexを用意する方法。
どちらも今回は実装しない。削除へ進む場合も、host depmod後のexternal post-buildで対象を限定し、テキストindexと全moduleを保持する。
その後に同条件の容量比較、A/A、QEMU A/Bと`/proc/modules`の比較、製品buildを行う。SDや実機の表示・速度は別途確認する。
