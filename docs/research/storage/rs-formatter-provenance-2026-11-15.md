# verityfmtのRS由来を調べた初期記録

2026-11-15。状態は**監査中**です。B3追試に使うformatterの由来候補・license表示・類似箇所を調べました。違反や製品出荷可否を確定する法的判断ではありません。

利用者は同日の本sessionで、監査と並行する**研究限定利用**を承認しました。[B3追試の事前登録](../../experiments/2026-11-15-dm-verity-fec-followup-prereg.md)はその範囲です。監査完了まで製品への組込み・出荷をしない条件は維持します。

## 対象と方法

対象はmain `cc4a9522999b22f6bf00c38bb9650678369d8309`の[verityfmt.c](../../../board/cardputerzero/tools/dm-verity/verityfmt.c)です。SHA-256は`15089f2a3f2e2e7f2d08b39eb60c9c94d72da9aabdc683e0076211d0059de799`。履歴上はsquash commit `1cb907a`（#247）で導入されており、それ以前の移植作業の履歴はこのfile履歴だけでは分かりません。

`rs_init`・`rs_encode`・`mod255`とstructを比較しました。**このformatterにRS decoderはありません**。読取り時のdecoderはkernel側であり、比較用にはLinuxとlibfec/AOSP/cryptsetupのdecoder sourceも取得しています。encoderとdecoderの由来を一括して同定したとはしません。

候補のbranch HEADをAPIで解決し、以降は以下のcommitを指定してsourceを取得しました。これらは比較snapshotであり、移植時の版やB3実行kernelのrevisionと同一という意味ではありません。

| 候補・固定commit | 取得した主なfile・license表示 |
|---|---|
| [Linux](https://github.com/torvalds/linux/tree/23c62304dde29abe92013d85910d03a77dada35d/lib/reed_solomon) `23c62304dde29abe92013d85910d03a77dada35d` | reed_solomon.c、encode_rs.c、decode_rs.c、include/linux/rslib.h。SPDX `GPL-2.0`、Phil Karn 2002・Thomas Gleixner 2004の通知。COPYINGとGPL-2.0本文も取得 |
| [libfecのquiet fork](https://github.com/quiet/libfec/tree/9750ca0a6d0a786b506e44692776b541f90daa91) `9750ca0a6d0a786b506e44692776b541f90daa91` | encode_rs_char.c/encode_rs.h、init_rs_char.c/init_rs.h、decode_rs_char.c/decode_rs.h、char.h。Karnの著作権とLGPL表記、lesser.txtは2.1。file先頭だけではor-laterの版指定まで確定しない |
| [AOSP external/fec](https://android.googlesource.com/platform/external/fec/+/90857deb7973c0ca24c79b9c1809fc9667f32c4f/) `90857deb7973c0ca24c79b9c1809fc9667f32c4f` | 同名encoder/init/decoderとchar.h、NOTICE、MODULE_LICENSE_LGPL、lesser.txt。Karn/LGPL表示、NOTICEはLGPL 2.1本文 |
| [cryptsetup](https://github.com/mbroz/cryptsetup/tree/102e91cb0fee849bb86fb1ec4d6ea218e45563cd/lib/verity) `102e91cb0fee849bb86fb1ec4d6ea218e45563cd` | rs_encode_char.c、rs_decode_char.c、rs.h、verity_fec.c、README.licensing/COPYING。RS各fileは`LGPL-2.1-or-later`、KarnとRed Hatの通知。project全体の既定GPLをRSへ一律適用しない |

## 構造・識別子・commentの比較

| 観察した一致と差 | 評価 |
|---|---|
| local commentはKarn/libfec由来、LGPL-2.1-or-later、`rs_encode_char.c`を指す。cryptsetupにその名前のfileがあり、libfec/AOSPは`encode_rs_char.c`という名前 | cryptsetup系を調べる手掛かり。ただしcomment自体が正しい由来証明とは限らない |
| `alpha_to/index_of/genpoly`、A0、srのGF表生成、root/fcr/prim、genpolyの逆順XOR、index formへの変換が共通 | Karn系の構造に強く一致。GF(256)/0x11dの一致だけより具体的だが、共通祖先を持つ候補間の区別には不足 |
| local `mod255`の反復減算・shift/addはcryptsetup rs.hの`modnn`と同型。localはmm=8/nn=255へ固定 | cryptsetup表現に近い。ただしlibfecのmacro展開・固定化からも作れる |
| local encodeのfeedback、逆順genpoly更新、memmove、末尾parity設定はcryptsetupと同じ順。localはstatic uint8配列、pad/短縮符号・動的確保・decoder用iprim・UNNORMALIZEDを省略 | encoder本体の近さは高い。直接の移植元revisionまでは識別できない |
| Linuxも同じshift/XOR骨格だがrs_control/rs_codec、uint16、invmsk・len検査を持つ。localにそれらはなく、型名rs_codecだけが共通 | Linuxからの直接portに固有な証拠は今回見つからない。候補から排除する証拠でもない |
| libfecとAOSPのencode_rs_char.c、encode_rs.h、init_rs_char.c、decode_rs_char.c、decode_rs.h、char.h、READMEはbyte一致。init_rs.hとlesser.txtは不一致 | AOSP経由とlibfec直接を一致fileだけで区別できない。cryptsetupだけを起源とする仮説への反証候補 |

比較は原文の構造・識別子・commentの読取りとraw unified diffです。空白・macro展開を含む完全な同一性証明や、類似率からの著作権判定はしていません。**Karn系のencoderである確度は高く、cryptsetup表現との近さは確認できますが、直接の供給元・正確なrevisionの確度は低い**という暫定評価です。

## 保存した証拠・取得の失敗

[証拠archive](rs-formatter-provenance-2026-11-15/evidence.tar.gz)に、固定版の上流32 file（sourceとlicense/通知）、local RS section、候補4種とのraw diff、取得URL・commit・byte数・SHA-256のmanifest、内部SHA256SUMSを保存しました。原文のcopyright・licenseは変更していません。

archive SHA-256は`d7c0e89b793ba29f1160c8ff25d772a393757b78945e5abc57dc7aefc9285bb6`、66,506 byteです。内部hashを再読して照合しました。初回の並列raw endpoint取得はLinux分がHTTP 429となり、同じ固定SHAのGitHub contents APIから取得し直しました。他候補の成功済みsourceは上書きしていません。

## 未解決・製品出荷を止める条件

1. 移植時に実際に参照したsource/版・生成過程を、元patch・session資料と突き合わせる。現行branch HEADの比較だけでは埋まらない。
2. local全体はGPL-2.0-or-later表示で、RS sectionにはKarnへの説明はあるものの上流のcopyright通知そのものはない。どの候補から何を取り込んだかを確定し、必要な通知・license本文・改変表示を整理する。表示差だけで違反とは断定しない。
3. encoder以外のCRC/SHA実装とFEC配置codeの由来、製品への組込み方、source提供・通知の配布方法も監査する。
4. 独立codecとの一致は互換性検査であり、法的な監査完了ではない。同じKarn実装同士の一致を独立実装による検証とも呼ばない。

今回は監査の開始とsource比較だけです。formatter、license header、harness、製品設定は変更していません。次段のharness拡張やB3追試はまだ行っていません。03914の台帳同期保留も継続します。
