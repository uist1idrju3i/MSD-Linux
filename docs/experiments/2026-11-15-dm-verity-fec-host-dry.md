# B3残条件のhost一括検査と容量超過対照での停止

[実験索引](README.md) / [事前登録](2026-11-15-dm-verity-fec-followup-prereg.md) / [storage訂正](../research/storage/storage-integrity-corrections.md)

## 状態

2026-11-15 UTC、利用者承認後のalias保存・依存閉包検査を実装しました。全43 smoke入力を一括で生成・検査する過程で、DのSHA-256/roots2の容量超過対照がhost gateと食い違ったため停止しました。**37入力を生成し、Dの残り6入力は未生成です。新しいQEMU bootは0回、Bのclean再試行・正式B〜Fは未実行です。** host検査の成功をRAM起動の成功には数えません。

事前amendmentは`e3f6553`、alias修正は`089f89a`、一括実行sourceは`ad7d6d2225746275e7b441f946bff2554488228d`です。C/D/E/Fの注入位置・期待は生成前の個別commitで固定しました。旧raw/CSV/v3期待、RS研究限定・製品出荷禁止、03914台帳同期保留を維持しています。

## 条件・手順

- standalone clone、固定Docker image `sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`を使用。
- kernelは再buildせず、保存済み`6.18.59-v8-b3trace`（SHA-256 `bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69`）を再利用。QEMUは呼び出していません。
- B新pack `fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205`を保持。全source caseのhashを照合し、fresh出力でBをrefresh、C〜Fを順番に生成しました。stageで失敗しても残るstageの安全なhost生成だけを同じ1 passで試し、最後は非0終了とします。
- Buildroot/kernel treeはwarm artifactを再利用し、再configure・ccache測定・性能比較はしていません。formatterは既存binary/sourceの保存hashを照合し、Dでは新規packを生成しました。これは構築・検査ができるかの1回のdry checkで、5反復の正式測定や性能評価ではありません。
- 実行後のprobeは入力をread-only mountしました。実行中のscript・旧入力は編集せず、実行済みsourceをarchiveに保存しました。

portableなmount名を使った実行コマンドです。`/base`は前回Bの全10入力と`repacked-seed`、`/kernel`・`/formatter`は保存hashに合うartifactです。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/host_dry.py \
  /base /kernel /formatter output-host-dry
tests/dm-verity-format/run.sh
```

## raw値と到達範囲

[CSV](2026-11-15-dm-verity-fec-host-dry.csv)。時間はstage内部の生成・検査wallで、host全体の性能やend-to-end所要時間ではありません。

| stage | 予定入力 | 生成入力 | host判定 | wall秒 |
|---|---:|---:|---|---:|
| B | 10 | 10 | 成功 | 158.0244755029853 |
| C | 10 | 10 | 成功 | 103.2050619799993 |
| D | 18 | 12 | gate不一致で停止 | 95.44485510300728 |
| E | 4 | 4 | 成功 | 42.88704147702083 |
| F | 1 | 1 | 成功 | 12.837630046007689 |

一括runnerの計時は412.46539126100834秒です。source caseの最初の照合は計時前で、各stage間の微小な処理を含みます。Dはcrc32cのroots2/8/16とSHA-256のroots2まで生成済み、SHA-256のroots8/16は未生成です。B/C/E/Fの各manifestとp5 readbackは検査済みです。Dの各生成caseもemit時に検査しましたが、stage全体の完了検査は未到達です。

### initramfsの修正と負対照

旧CPIOと新CPIOの差は、`lib64 -> lib`と`usr/lib64 -> lib`の追加だけです。他entryのmode・payloadは同一で、SD/rootfs/kernel/cmdline bytesも保持しました。

| 項目 | SHA-256 |
|---|---|
| 旧initramfs | `95aa45499badb5ba6952062eb4e903fe7239c438133777dcebcead6e3421d8b7` |
| 新initramfs | `8ceae084797426bace25942f35da20bd0060c74888761a9493393b6382e8a1ab` |

新CPIO内のBusyBoxからPT_INTERP・DT_NEEDEDをたどり、loader・libc・libresolvの4 ELF objectを`/lib64`・`/usr/lib64`経由で解決しました。host filesystemへのfallbackはしません。実際の旧CPIOを同じcheckerに与えた負対照は次で拒否され、前回の欠落を検出できます。

```text
unresolved DT_NEEDED: bin/busybox: libresolv.so.2
```

alias欠落・library欠落・不正ELF・symlink loopに加え、refreshでinitramfs以外の入力が変わらないこと、既存出力先・source hash不一致の拒否もfixtureで検査しました。実loaderのopenat traceと修正後RAM起動は未確認です。

### Dの停止と切り分け

追加したhost gateは、SHA-256の各rootsで「cleanは非FEC verify成功、1 byte破損は非FECで拒否・FECで成功、同column R+1 block破損はFECでも非0」を要求していました。最後の要求が強すぎました。事前登録の容量超過域は保証範囲外の挙動も記録する方針で、CLI終了値を完全回復の証明にはできません。bootの`verity-panic`期待は変更していません。

実入力の破損はoffset `0, 98304, 196608`、data block `0, 24, 48`のbyte0、いずれも同じFEC column `[0,0]`のsymbol `0,1,2`です。XOR ffの3変更だけであることをcleanとの全byte比較で再確認しました。rootsは2です。最初の実行と、同じ入力のread-only probeで次を観測しました。

```text
Verification failed at position 0.
Verification of data area failed.
Found 1 repairable errors with FEC device.
```

probeで保存した実際の終了値は**0**。入力hash `3f61c392b85ea18103c7c2ec066d43bc7af23c45dadea21be178ae7e0e8e5281`は前後で同一です。実binaryはveritysetup 2.7.5、SHA-256 `f5e4fa1c6b3ba9b0b302dba409370e48df5bbb1e442ca81e366dd9db2271793a`です。この終了0と非0を要求するgateとの不一致が、host停止の直接原因です。

入力が実は直ったという説明も、独立BM/Chien decoderで検討しました。実columnのsyndromeはcleanが`[0,0]`、破損後が`[255,124]`。未知誤り復号はsymbol59を変更してsyndromeを`[0,0]`に戻しますが、cleanとはsymbol `0,1,2,59`が異なる**別codeword**になります。これは独立decoderの結果で、libcryptsetupの内部bufferを観測したものではありません。syndromeゼロや「1 repairable」を元bytesへの回復と同一視しない根拠です。

固定上流tag v2.7.5、commit `3c3a8210e4927b5ce06481f91468c6ad9779b3aa`も確認しました。

- [CLI action_verify](https://github.com/mbroz/cryptsetup/blob/3c3a8210e4927b5ce06481f91468c6ad9779b3aa/src/veritysetup.c#L279)はCHECK_HASH付きのuserspace経路を選択します。
- [VERITY_verify_params](https://github.com/mbroz/cryptsetup/blob/3c3a8210e4927b5ce06481f91468c6ad9779b3aa/lib/verity/verity.c#L273)はdata hash不一致後にFEC checkの戻り値を使い、そこでMerkle全体の再検証はしません。
- [FEC_process_inputs](https://github.com/mbroz/cryptsetup/blob/3c3a8210e4927b5ce06481f91468c6ad9779b3aa/lib/verity/verity_fec.c#L165)はRS decoderの非負結果をerror数へ加算して0を返します。実際に両検証messageが出ている点は、この説明と一致します。

上流sourceとDebian実binaryの完全なbuild対応・全patch差分は未照合です。従ってtool内部の実行経路をsourceだけで確定とはしません。実測したCLI終了0、表示された失敗、独立decoderの別codewordを区別します。formatterのlicense違反、kernelの訂正成功・失敗、Dのboot仮説の反証を示す結果ではありません。

## 保存・不足

[evidence archive](2026-11-15-dm-verity-fec-host-dry/evidence.tar.gz)に、一括生成の全log・37入力metadata/manifest・source・fixture出力・probe argv/終了値・固定上流4 fileとlicenseを保存しました。共通B pack本体、旧/新initramfs、Dの4 packの新規suffixも含みます。Dの全4 packは共通dataとsuffixからbyte単位で再構成し、元SHA-256と一致しました。SD全体とkernel bodyは重複保存せず、既存artifactとhash・生成sourceを用います。

Dは例外前の中間RS境界結果をメモリーに蓄積し、stage末尾で保存する実装でした。このため原runのD `host-check.json`と当該中間raw値は未保存です。各caseの既知消失検査・生成pack・sourceは保存しましたが、失われた中間rawを保存済みとはしません。unit fixtureのroots2/8/16境界検査と実入力の中間rawも混同しません。

archiveは42,286,806 byte、SHA-256は`12bf421426af7b87725c0a243d21829f085b1911e6b2518d8ee386b3ce299f73`です。179 memberの内部hashを再読込みして照合しました。

## 再開に必要な判断・予算

提案は、先にdated amendmentを記録し、容量超過域のCLI終了0を「完全回復」と数えず観測値として保存することです。hostの回復判定には独立decoder出力とclean参照bytesの一致を要求し、SHA-256のclean/非FEC負対照と容量内FEC検査は維持します。各pack/checkを例外前に永続化してDを完走し、全43入力のhost条件が整ってからB clean通常/RAMへ進みます。bootの既存期待は不変で、両clean成功前に正式反復は開始しません。**この提案は未承認・未実装です。**

停止時の累積時計は約6時間で、起点2026-11-15 12:17:52 UTC、36時間deadlineは2026-11-17 00:17:52 UTCのままです。残り43 smoke＋215正式bootを240秒/boot、準備4時間と仮置きすると累積約27時間です。これは未測定段階の仮見積りで、再開時と各stage後に更新します。上限でなくhost gateの判断待ちによる停止です。

実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認です。今回新しいF3/F6のkernel仮説評価はありません。push後CIは別で、今回のhost検査に含めません。
