# B3 host検査の再開：独立復号の完全一致とD全18入力

[実験索引](README.md) / [事前登録](2026-11-15-dm-verity-fec-followup-prereg.md) / [前回停止](2026-11-15-dm-verity-fec-host-dry.md) / [製品設計への示唆](../research/storage/storage-integrity-corrections.md)

## 実施範囲

2026-11-15 UTC、利用者承認を`29d2c22`で先にcommit・pushし、計測器`400ff62`でD全18入力を新しい出力先に生成・検査しました。旧D部分生成・rawは上書きしていません。B/C/E/Fの既存成功入力と合わせた43入力のmanifest・全file hashを照合し、hostの再開条件が整いました。この記録はhost検査のみで、BのQEMU結果は別記します。

CLIの終了値やrepairable表示は観測値として保存します。回復と数えるのは、独立RS decoderの候補を元のimageへ反映し、**候補imageの全bytesがclean参照と一致した場合だけ**です。syndromeゼロでも別codewordは誤訂正として分離します。容量超過の誤訂正は想定される挙動で、訂正能力の保証範囲と混ぜません。

## 条件・手順

- standalone clone、固定image `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`。
- dataは前回と同じB pack、SHA-256 `fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205`の先頭data_blocks×4096 byte。
- crc32c/sha256、roots2/8/16の6 pack。UUIDを含め新生成結果を固定し、clean・data中央byte123・同column R+1 blockの3条件を作りました。
- formatterの保存済みbinary/source hashを照合。Buildroot/kernelはwarm artifact再利用で、再build・再configure・ccache測定はしません。今回はQEMUをhost検査に使っていません。
- 独立decoderへerasure位置のhintを渡さず、全変更columnを復号して候補image全体とcleanをbyte単位で比較しました。対象columnの選択には既知の全入力差分を使い、kernelでの未知I/O検出条件の再現とはしません。
- formatterのargv・終了値、packのhash/params、各RS境界結果、各caseの独立復号、各CLI応答を直後に保存します。境界の保証範囲内で失敗した場合も、失敗行を保存してから停止するfixtureを追加しました。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/remaining.py \
  /base /kernel output-d2 --stage D --formatter /formatter
python3 tests/dm-verity-format/test-remaining.py
```

`/base`は保存済みB入力、`/kernel`・`/formatter`は保存hashに合うartifactのread-only mountです。全体の再生成wallは未採取で、性能比較には使いません。構築と検査ができるかを1回確認したもので、正式5反復の代替ではありません。

## raw結果

[CSV](2026-11-15-dm-verity-fec-host-dry-resume.csv)に18回復判定・36境界・12 CLI応答を保存しました。

| hash | roots | clean | data 1 byte | 同column R+1 block |
|---|---:|---|---|---|
| crc32c | 2 | 完全一致 | 完全一致 | 別codeword |
| crc32c | 8 | 完全一致 | 完全一致 | 拒否 |
| crc32c | 16 | 完全一致 | 完全一致 | 拒否 |
| sha256 | 2 | 完全一致 | 完全一致 | 別codeword |
| sha256 | 8 | 完全一致 | 完全一致 | 拒否 |
| sha256 | 16 | 完全一致 | 完全一致 | 拒否 |

完全一致12、別codeword2、拒否4です。各recordにclean/candidateのSHA-256、全bytes比較結果、実際の修正offsetと値、columnごとの分類があります。RS容量境界は6 pack各6条件を即時保存しました。2e+v<=Rの全条件でcleanへ復元し、保証範囲外は復号拒否と別codewordを観測しました。

CLI応答の並びはclean非FEC、data非FEC、data FEC、R+1 FECです。終了0を回復判定へ加算していません。

| SHA-256 roots | CLI終了値4個 |
|---:|---|
| 2 | 0, 2, 0, 0 |
| 8 | 0, 2, 0, 2 |
| 16 | 0, 2, 0, 2 |

roots2のR+1は前回同様hash失敗表示とCLI終了0で、独立復号は別codewordでした。製品設計でCLI終了0/repairableをintegrityの証明にしない根拠はhost限定です。固定kernel sourceの`drivers/md/dm-verity-fec.c`にも、FEC後の候補blockをexpected hashと再比較する箇所を確認しましたが、そのguardを今回のhost検査で実行したわけではありません。kernelのFEC後hash再検査が必要という設計上の示唆と、製品適合・実機検証を分けます。

## 計測器検査・保存

```text
Ran 8 tests in 0.206s
OK
ok - all 43 smoke inputs generated, manifests and file hashes verified; D 18/18 complete
```

空image・不正geometry・FEC対象外の変更は拒否し、1 errorの元bytesへの回復、2 errorの拒否、3 errorの別codewordをfixtureで分けました。CLI終了0が容量超過で返っても観測として保存し、CLI起動errorもJSONへ保存するfixtureを追加しました。既存format suiteとShellCheckは、変更のない対象の先行成功を参照します。

[archive](2026-11-15-dm-verity-fec-host-dry-resume/evidence.tar.gz)は108 member、5,932,501 byte、SHA-256 `f1d6f1193fcbafb21b405c7d15f51ee56436cf5402d75dc25d8fee72935b959b`です。全memberのhashを再読込みして照合しました。生成source・18入力metadata/manifest・全中間値・全CLI log/argv/status・fixture・全43入力の最終照合を保存しました。

D6 packの新規suffixも保存しました。[前回archive](2026-11-15-dm-verity-fec-host-dry/evidence.tar.gz)の`payload/base-pack.img`先頭data bytesと新suffixから6 packを再構成し、元SHA-256と全て一致しました。共通dataとSD/kernel bodyは重複保存しません。前回欠損した中間rawを復元したとはせず、新しいrunとして扱います。

## 次の段階・制限

Bの通常/RAM両cleanを最初に実行し、両成功後だけ残るsmoke・正式反復へ進みます。boot期待、5反復、clean失敗と判断時の停止規則、36時間deadline（2026-11-17 00:17:52 UTC）は維持します。再開時点の保守的累積時計は約6時間半で、残り43 smoke＋215正式bootを240秒/boot・準備4時間とすると累積約28時間の仮見積りです。段階ごとに更新します。

RS研究限定・製品出荷禁止、03914台帳同期保留は不変です。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認で、host結果をkernelや製品の合格に拡張しません。
