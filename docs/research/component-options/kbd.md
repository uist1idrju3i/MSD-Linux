# kbdのtool配送とloadkeysの保持

[一覧](README.md)へ戻る。[実験計画・結果](../../experiments/2026-11-23-kbd-tools.md)を参照。

## 対象と一次資料

固定版はkbd 2.9.0。Buildrootの`package/kbd/Config.in`はpackage選択だけで、tool個別選択を公開しない。
`kbd.mk`はvlock・testsを無効にし、全体をinstallする。圧縮libraryの有無はbzip2・xz・zlib・zstdの選択に連動する。
固定sourceのsrc/Makefile.amではloadkeysも他の通常toolも同じbin_PROGRAMSに属する。
一次資料は固定Buildrootの[recipe](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/kbd/kbd.mk)・[Config.in](https://github.com/buildroot/buildroot/blob/bbbdab36565d4941b6b0449a0eedb5aac8a10c2e/package/kbd/Config.in)、kbd 2.9.0の[Makefile.am](https://github.com/legionus/kbd/blob/v2.9.0/src/Makefile.am)・[configure.ac](https://github.com/legionus/kbd/blob/v2.9.0/configure.ac)である。
上流の最新releaseは調査時点で[2.10.0](https://github.com/legionus/kbd/releases/tag/v2.10.0)だが、この変更でバージョンを更新しない。
2.10.0のoption・挙動差は未調査で、ここでの判断は固定した2.9.0の配送に限る。

| 選択肢・option | 固定版での既定・状態 | 採否と理由 |
| --- | --- | --- |
| Buildroot `BR2_PACKAGE_KBD` | y。個別tool用symbolなし | 維持。製品のtext keymapをloadkeysで読む |
| `--enable-optional-progs` | no | 維持。既定の通常toolをloadkeysだけにはできない |
| `--enable-libkeymap`、`--enable-libkfont` | no。standalone libraryのinstallを選ぶ | 維持。toolの個別選択ではない |
| `--disable-vlock`、`--disable-tests` | recipeで指定 | 維持。loadkeys単独配送には不足する |
| `--with-bzip2`、`--with-lzma`、`--with-zlib`、`--with-zstd` | recipeがpackage選択で決める | 維持。今回は圧縮対応・libraryを変えない |
| `--disable-compress` | keymap・fontのinstall時圧縮に関わる | 不採用。配送toolを選ばない。製品独自keymapを維持 |
| Make変数でinstall対象を上書き | Config.inに対応なし。psf aliasのinstall hookも別にある | 不採用。内部install規則を部分上書きして壊れたaliasを残さない |
| external post-build | 既知の配送名と保持一覧を検査できる | 採用。loadkeysを保持し、削除予定toolへの参照があれば全削除前に拒否する |
| 全kbd維持 | 現状の配送 | 対照。使わないconsole/font操作toolも残る |
| BusyBox loadkmapへ置換 | text mapをそのまま読むloadkeysとは入力形式が違う | 不採用。S04とmapの形式を変えず、今回は未使用toolだけを対象にする |

共通configure引数と全採取optionは[既存の一覧](configure-options.csv)のkbd-2.9.0を参照。
今回もconfigure --helpの74 tokenを[option表](kbd-options.csv)と照合し、欠け0だった。
共通引数の未明示の既定値は今回再解決せず、その旨を表に残した。tool個別選択のoptionは見つからなかった。
版の更新、圧縮library・localeの削減、BusyBoxの再構成はこの候補に混ぜない。

## 製品の利用箇所と保持方針

S04msd-keymapだけが`loadkeys -C /dev/tty0 -q`で独自mapを読む。S10mdevはmoduleのmodalias処理を担当する。
overlayのcardputer-keyboardはinput device名を確認してsymlinkを作り、kbd toolを呼ばない。
loadkeysのtext parser・Unicode処理と、M5のevent driverを区別する。

| 配送tool群 | 製品の利用と判断 |
| --- | --- |
| loadkeys | S04から利用。全pathで保持する |
| dumpkeys、showkey、getkeycodes、setkeycodes、kbd_mode、kbdinfo、kbdrate | overlay・initで参照なし。削除対象 |
| setfont、showconsolefont、mapscrn、loadunimap、psfxtable、psfaddtable、psfgettable、psfstriptable | font・unimap操作。製品からfont dataも既に除かれており、利用箇所なし。削除対象 |
| setleds、setmetamode、fgconsole、chvt、deallocvt、openvt、setvtrgb | console操作。起動処理に利用箇所なし。削除対象 |
| unicode_start、unicode_stop | 他のkbd toolを呼ぶ補助script。製品から呼ばれず、まとめて削除対象 |
| resizecons、setlogcons、setvesablank、getunimap、clrunimap、outpsfheader、setpalette、screendump、spawn_console、spawn_login、vlock | arch条件・optional・vlock用。存在時も同じ参照検査を適用する |

BusyBoxの同名appletはbinary内の機能とcommandのsymlinkを分ける。kbdのregular fileとBusyBoxへのsymlinkを区別し、後者は削除しない。
削除予定tool以外のfileとsymlinkに同名参照があれば停止する。削除する補助script同士の参照は除外し、BusyBox本体もproviderとして除外する。
実行時に名前を組み立てる未知のcallerまで不存在を証明するものではない。将来callerを追加する場合は保持一覧も見直す。

固定sourceのinstall対象36名（vlock・optional・aliasを含む）と削除器・上の表を照合し、欠け0だった。
実際のCI imageにはloadkeys以外に21 regular fileと3 aliasがあり、これらを削除した。
QEMUで採取したBusyBoxのapplet一覧ではchvt・deallocvt・openvt・setkeycodes・setlogconsが重なる。
dumpkmap・loadkmap・loadfontは別名・別形式の機能であり、kbd_mode・setfont・fgconsole・showkeyは一覧にない。
同名appletがbinaryにあっても、削除したkbd fileのpathに新しいsymlinkを補う変更はしていない。
loadkeys本体・text mapを保持し、前後QEMU A/BのS04実行終了0を確認した。実機keyboardは未確認である。
