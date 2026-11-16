# verityfmtのRS由来監査

2026-11-16追補。比較監査の結論は、**Karn/libfec系で、直接の移植モデルはcryptsetupの2017年再構成・修正後が最有力**です。ただし取得経路の証明ではなく、正確なtagは識別できません。[追補の結論・出荷選択肢](#2026-11-16追補)に事実、推定、未確認を分けました。製品出荷の承認ではありません。

[storage研究索引](README.md)へ戻る。

追補を含む本文が20,000 byteを超えたため、[2026-11-15初期記録](rs-formatter-provenance-initial-2026-11-15.md)を分離しました。32 fileの固定証拠・hash、当時の未解決点と失敗記録は保持しています。以下が現在の結論です。

## 2026-11-16追補

### 1. 直接の由来とrevision範囲

**推定**: 直接の移植モデルはcryptsetup `lib/verity/rs_encode_char.c`の再構成・loop修正後が最有力です。確度は中程度で、Karn/libfec系という判定より弱いものです。最も整合する範囲は`54cb40fce7760a7fc41db9e8c8baab47880c66d9`（2017-04-05）以降、調査した`v2.0.0`〜`v2.8.8`の41正式tagです。これは本文が一致する比較範囲であり、実際の取得日・取得版の上下限を証明するものではありません。

**事実**: localのfile名への言及は`rs_encode_char.c`で、cryptsetupの再構成後の名前です。Karn/libfecとAOSP external/fecは`encode_rs_char.c`とtemplateの`encode_rs.h`です。さらにlocalはmacroでなく`rs->index_of`等を直接使い、GF表生成前に`index_of`をゼロ化しています。cryptsetupの再構成にはこのゼロ化があり、比較したlibfec/AOSPのinit templateにはありません。これらの組合せがcryptsetupを上位に置く根拠です。commentが正確であること、ゼロ化を独自追加したのではないことは**未確認**です。

| 履歴の固定点 | 読み取れた事実と限界 |
|---|---|
| cryptsetup `c2cf33af242e4cbd580c3feb27c833ec590402a4`（2015-12-12） | verity FECとvendored libfecを導入。旧`lib/verity/libfec/`にはKarn 2004/LGPLのtemplateがある |
| `e4f1faa478abd4673e7f92c3932f9d783e42eb29`（2017-04-05） | templateを再構成して`rs_encode_char.c`を導入。`modnn`と直接member参照、`index_of`のゼロ化はここへblameされる。ただしencoderの入力長にtypoがあった |
| `54cb40fc...`（同日） | loopを`nroots-pad`から`nn-nroots-pad`へ訂正。localの`nn-nroots`はpad=0で訂正後と一致。元から正しいlibfecからも導けるため、この修正の継承を証明したわけではない |
| `5e0db46f1790700a23bc9af14f1ab20bac4e7c5b`（2018-03-19） | decoder追加でstruct、A0、modnnを`rs.h`へ移動。encode/init関数本文は変わらない。localの単一file構成だけで移動前後を区別できない |
| `661f57def4e3aa158305d92079ced68d64be6d8a`（2024-05-07） | SPDX化。後のcopyright年更新も本文の版識別には使えない |

41 tagはstable branch上のpatch releaseも含めて比較しました。tagをdereferenceしたcommit、file hash、encode/initそれぞれのtoken列hashを`release-bodies.json`へ保存しています。空白とcommentを除くと、両関数とも41 tagで各1種類でした。したがって「2.7.5が直接元」「2024年のSPDX化後」といった絞り込みはできません。

### 2. token比較と対立候補による確認

追補archiveの`token-comparison.json`、`diffs/`、`normalized/`が結果です。比較単位はencoder関数本文、GF表生成loop、生成多項式の構築・index変換、mod関数です。comment・空白を除いたC tokenへ`SequenceMatcher(autojunk=False)`を適用しました。類似率は著作権判断や取得確率ではありません。

| encoder本文の比較先 | 未正規化の類似率 | 固定条件の正規化後 |
|---|---:|---|
| cryptsetup再構成直後 `e4f1faa...` | 0.830846 | 0.988571、不一致（入力長のtypo） |
| loop修正後 `54cb40fc...`と既存固定版`102e91cb...` | 0.822660 | 1.000000、token一致 |
| libfec固定版とAOSP external/fec固定版 | 0.721311 | 1.000000、token一致 |

正規化はtemplate macroのmember展開、`mm/symsize=8`、`A0=255`、pad=0、1 byte型、localの`rsn`の展開、無効な`UNNORMALIZED`枝の除去です。全関数の同一性ではなく、**固定条件下の抽出部分の一致**です。GF loop・多項式構築・modの抽出部分も4候補すべてと正規化後に一致しました。再構成直後の方が未正規化のencoder類似率は高く、単純に最高値を由来とする手法は誤ります。

最有力候補を反証するため、共通祖先と別実装も調べました。

- **Karn原配布**: FEC 3.0.1 release archiveの`encode_rs.h`、`init_rs.h`、`rs-common.h`、`char.h`、READMEは、commit固定したquiet/libfec版と5/5でbyte一致しました。原配布だけで同じ式・loopを説明できるため、cryptsetup直接取得は確定できません。`lesser.txt`は一致しません。mirrorにはKarn 2006のpackage通知が冒頭に追加され、LGPL 2.1本文を収めています。
- **AOSP external/fec**: 初期commit `4e213d510f437769f8a28578dd4f786fb7d16c44`と固定HEADを比較。`5767f2ce4658e4207ffacd88a268f79fa7ed0d50`のinit変更は`sizeof(data_t)`前の`(int)`追加です。localは該当の汎用parameter検査を削除しており、AOSP固有の手掛かりが残りません。METADATAはKarnのURLと3.0.1、2007-08-07を示しますが、それだけでlocalの取得経路とはしません。
- **AOSP system/extras**: `fc2494a2abd7ab21774d03deb09c1362bbb0bba8`の`libfec/fec_read.cpp`は`init_rs_char/decode_rs_char`を呼びます。`libfec/Android.bp`は外部の`libfec_rs`をlinkします。`external/fec/Android.bp`でその実体がKarn系の`encode_rs_char.c`等と分かります。system/extrasのApache-2.0をRS本体のlicenseにしてはいけません。保存したheader・呼出し側・build定義でこの境界を確認しました。
- **Linux**: 既存固定版に加え、初期Git snapshot `1da177e4c3f41524e886b7f1b8a0c1fc7321cac2`とSPDX追加`dc8f923eaee24061c557cb3221abeea3b95072c4`のencoder/initを比較。古い`rs_control`の時点でも`uint16_t`のparity、`invmsk`、len/pad検査があり、localの`uint8_t`固定encoderとは異なります。現行の`rs_codec`という型名だけでは直接由来の証拠になりません。Linuxを改変元から完全に排除したという意味でもありません。

**未確認**: squash前の移植patch、作業者が開いたURL・版、生成指示、複数候補を混ぜた可能性は未確認です。local履歴は`1cb907ad0c87d62cd1e5aceba715426e36c02c04`へ到達しますが、その前の取得履歴はありません。識別には当時のsession資料・元patchが必要です。今回の結論はその欠落を類似率で埋めません。

### 3. 著作権者とlicense

| 対象 | 一次資料で確認した表示と扱い |
|---|---|
| 最有力のcryptsetup RS | `rs_encode_char.c`はPhil Karn 2002、`rs.h`はPhil Karn 2004。両方にlibcryptsetup modificationsとしてRed Hat, Inc. 2017-2026と`LGPL-2.1-or-later`。年の範囲は固定版の通知であり、全期間にlocalへ変更を取り込んだという意味ではない |
| Karn/libfec原配布とAOSP external/fec | encoder/init templateはPhil Karn 2004とLGPLの表示。原配布のREADMEはKarn/package、添付本文はLGPL 2.1。初期記録のとおり、file冒頭の一般的なLGPL表記だけからor-laterを一律断定しない |
| AOSP system/extrasのwrapper | The Android Open Source Project 2015、Apache-2.0。RS本体の権利表示へ置き換える根拠ではない |
| LinuxのRS | Phil Karn、kernel adaptationのThomas Gleixner。SPDXは`GPL-2.0`。`dc8f923e...`はKarnからGPL v2でのkernel取込み許諾を得た経緯を記す。これはlibfec/cryptsetupの全コピーを自動的にGPLへ変える許諾ではない |

cryptsetupのproject既定GPLとRSのfile別LGPLを分けます。local先頭の`GPL-2.0-or-later`だけでは、取り込んだ部分の通知・改変表示・配布義務の処理を済ませた証拠になりません。Karnへの説明commentはありますが、Karn/Red Hatのcopyright通知そのものはありません。現段階で違反の法的認定はしません。

### 4. verityfmtで変えた部分

以下は最有力モデルとの**観察可能な差分**です。移植作業の時系列を復元したものではありません。

1. `init_rs_char/encode_rs_char/modnn`を`rs_init/rs_encode/mod255`へ改名。`struct rs`を`rs_codec`にし、動的tableを`uint8_t alpha_to[256]`、`index_of[256]`、`genpoly[64]`へ固定。呼出し側がstructを保持し、free関数・確保失敗処理を削除。
2. symsize=8、nn=255、pad=0を固定し、`mm/fcr/prim/iprim/pad`のstruct memberとdecoder用計算を削除。`gfpoly/fcr/prim/nroots`はinit引数に残す。実呼出しは`0x11d, 0, 1, roots`。これらの定数はcryptsetup/AOSP/kernelの互換条件で、取得元固有の印ではない。localに`NROOTS/FCR/PRIM/GFPOLY`というmacroはない。
3. initの汎用parameter検査を減らし、非primitive多項式の失敗は`-1`、成功は`0`へ変更。`nroots <= 0`も拒否。`genpoly[64]`に対しinitだけでは上限63を検査しないが、CLI側のrootsは2..24に制限される。今回これを修正・追加試験したわけではない。
4. encoderのdata/codecをconst化し、full-lengthの`rsn=nn-nroots`を導入。parity長を1 byte前提にし、A0 macroを255へ置換、無効な`UNNORMALIZED`枝とtemplate commentを削除。feedback、逆順XOR、memmove、末尾parityの処理順は維持。
5. 移植元header・license通知をそのまま残さず、local独自の由来commentとfile全体のGPL SPDXへ置換している。変数名・固定配列化だけで独立実装になったとは評価しない。

### 5. 出荷時の選択肢（利用者の判断待ち）

これは実装指示や法律意見ではありません。直接の取得経路が未確定でも、少なくとも最有力候補の権利を落とさない処理を前提に、配布形態とともに権利担当者へ確認する案です。**今回どの案も採用せず、研究限定・製品組込みと出荷の保留を継続します。**

| 案 | 必要な処理の案 | 利点 / 不利点 |
|---|---|---|
| A: LGPL由来部分を明示して継続 | RS範囲を別file等で明確にし、正しいKarn/Red Hat通知、上流commit、改変内容・日付を保持。RSは`LGPL-2.1-or-later`、MSDの独自部分は既存GPLを区別し、license本文と配布通知を添付。修正RS sourceとbuild手順、binary提供時の該当条項への適合を整備する | 既存挙動を維持しやすい / source提供だけでなく結合方法・再link手段の確認も必要 |
| B: LGPL 2.1第3条によるGPLへの変換を明示 | 同条の条件に沿って対象コピーの通知をordinary GPLへ変更し、著作権通知・改変表示は維持。選んだGPL版とSPDX、変換理由・対象を記録し、GPLの完全な対応source・build script・license/提供方法を用意 | GPLのformatterへまとめやすい / 対象コピーについて不可逆。現行のGPL headerだけで変換済みとは扱えず、条項適用と版選択の確認が要る |
| C: 独立した再実装へ置換 | 数学的仕様から新規実装。既存表現を写さない担当・資料の分離、実装経緯、選択licenseを記録。既知vector、境界・不正入力、既存imageとの互換性を検証 | 将来の由来を説明しやすい / 工数・新たな不具合の危険があり、見たcodeの書換えをclean-roomと称するだけでは解決しない |

AでLGPL 2.1を選ぶ場合、修正libraryには第1・2条、libraryのobject配布には第4条、結合workには該当する第5・6条等を確認します。第6条が適用される形では、利用者による変更とそのdebug用reverse engineeringを妨げず、修正libraryで再linkできるsource/objectと手順、または条件に合うshared-library方式等を用意します。完全なsource/build材料を渡す方式も候補です。**あらゆる配布でobject file必須という一律の判断はしません。** sourceの同梱・提供申出・同等のdownload提供はそれぞれ条文の条件があり、単にGitHubのHEADを案内して済ませません。

license本文はLGPL 2.1と参照するGPL本文を含めて配布物と対応付けます。cryptsetupの保管file名にはOpenSSL exceptionがありますが、RS各fileのSPDXは例外付きではありません。RSに例外を勝手に追加しません。SPDXも根拠なく`OR`や`AND`を並べて済ませず、由来部分と選択した扱いに合わせます。

出荷物にformatter自体を含めるのか、hostだけで使って生成imageのみを配るのかも先に確定する必要があります。生成したparityがtoolの出力であることだけで、そのimage全体へ自動的にLGPLが及ぶとはしません。他方、tool/source/binaryを一緒に配る場合の義務は別です。encoder以外のCRC/SHA・FEC配置codeの監査、実際の配布物・契約条件は今回の範囲外で、全formatterの出荷承認は出せません。

### 6. 追加証拠と再照合

[追補archive](rs-formatter-provenance-2026-11-15/followup-evidence.tar.gz)は280,964 byte、SHA-256は`1cfbe901468d54f874f17c629a9b35df0668fa69451b32a0cdaca77afad050fc`です。[既存32 fileのarchive](rs-formatter-provenance-2026-11-15/evidence.tar.gz)は書き換えず、全内部hashを再照合しました。

- `manifest.json`に取得URL、commit、path、byte数、SHA-256を記録。比較に用いた追加Git sourceはcommitで固定し、全memberは`SHA256SUMS`で照合できます。localの全file hashも初期記録と同じです。
- `history/`と`blame/`に固定点までの履歴とline単位の由来、`patches/`に2015/2017/2018/2024年等の変更を保存。cryptsetup/libfec/AOSPのcloneはnon-shallowです。Linuxはcommitを指定したAPI履歴とsourceによる構造比較で、全kernel履歴のclone/blameはしていません。
- 原配布`karn/fec-3.0.1.tar.bz2`はGit公開物ではないため架空のcommitを付けず、release名・取得URL・SHA-256を保存。`karn/mirror-equality.json`でcommit固定mirrorと5 fileのbyte一致を結び付けました。license fileの不一致も記録しています。
- `collector.py`、`METHOD.txt`、全41 tagのsource、未正規化diff、正規化後のtoken列を保存。集計はlocal RSの固定条件に限る方法で、暗号学的な同一性や実動作の証明ではありません。収集scriptは調査環境のpathを持ち、別環境では配置の指定を直す必要があります。
- GitHubのAOSP mirror clone失敗、Googleの履歴APIとLinux raw endpointのHTTP 429も記録。公式Git clone、同一commitのGitHub contents APIを代替に使い、失敗を由来判定の根拠にはしていません。

今回は文書と追加証拠だけです。製品code、既存raw、license header、vendor、bench scriptは未変更です。B3の後続結果は[総括](../../experiments/2026-11-16-dm-verity-fec-followup-summary.md)にあります。QEMUや実機の追加試験、配布形態の確認、法的承認、03914の台帳同期は行っていません。
