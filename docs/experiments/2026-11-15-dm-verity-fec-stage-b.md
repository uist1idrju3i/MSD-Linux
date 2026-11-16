# B3 stage B：同一packのmode・通常/RAM読取り比較

[実験索引](README.md) / [事前登録・amendment](2026-11-15-dm-verity-fec-followup-prereg.md) / [host全43入力](2026-11-15-dm-verity-fec-host-dry-resume.md) / [研究上の訂正](../research/storage/storage-integrity-corrections.md)

## 条件と実行

2026-11-15 UTC、host全43入力の検査後、B clean通常/RAMの両成功を確認し、残り8条件を各1 boot、正式10条件を各5 boot実行しました。smokeと正式は別の新しい出力先で、standalone Docker cloneの固定source `400ff62`を変更していません。入力はalias修正済みB manifestを各case実行前に照合しました。正式反復にはclean失敗・中断・timeoutはありません。期待不一致10件は失敗試行として保持します。

固定imageは`sha256:47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d`、QEMU 11.1.2、研究kernel 6.18.59-v8-b3traceです。kernel/rootfsはwarm artifact再利用で、reconfigure・再build・ccache測定はしていません。Buildroot/GCC等の構築条件は[前回B記録](2026-11-15-dm-verity-fec-stage-b-smoke.md)を継承します。Bの新packはAとは異なるhashで、B内のF3全6条件は同じ破損bytesを使います。

```text
run-qemu: sha256 c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410  qemu-system-aarch64
run-qemu: sha256 bdd129e84f953f65fa2cbedac957c4b28c55ccccc9f8521e37dca3dd608e3c69  Image
pack: fedf1abe7f222f719b2287885079e0bcfe052f351f266b6ecbd684e26ba0a205
crc32c root: 3711f47a
```

上のbinary hash行はserialの実出力からパスだけ省略しました。入力設定・入力hash・serial/QMP・実sourceをarchiveに保存しています。通常は全mapper読取り→readall完了→ready→login、RAMはmountせずblock4096と全5832 blockを読み、両status 0を要求します。initramfsはalias以外のpayloadを変えず、host依存閉包を検査済みです。正常/panic/EIOはwatchdog無効、restartだけ有効という承認済み差があり、3 modeだけの単一変数比較とはしません。

```sh
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-b output-b4-clean --runs 1 \
  --case B-clean-normal --case B-clean-ram
# 残る8 caseを--caseで選び、output-b4-smokeへ各1回実行
python3 board/cardputerzero/tools/bench/dm-verity-fec/followup.py run \
  /prior/cases-b output-b4-formal --runs 5
```

`/prior/cases-b`は保存入力のread-only mountです。600秒/boot、入力不一致・clean失敗・未観測timeoutで停止する規則と、既登録の期待は不変です。正常とRAMのclean成功まで後続を始めていません。

## raw結果

smoke10件は8期待一致・EIO2件不一致でした。最初の通常/RAM cleanは236.82482568200794秒と224.18709510899498秒で、両方合格しました。全60件の生の値は[CSV](2026-11-15-dm-verity-fec-stage-b.csv)とarchiveにあります。次表の正式wallは小数第3位へ丸めています。

| case | 5回のwall秒（repeat0→4） | 中央値［最小–最大］秒 | 期待一致 |
|---|---|---|---:|
| clean通常 | 232.385, 234.316, 229.929, 231.754, 246.434 | 232.385［229.929–246.434］ | 5/5 |
| clean RAM | 236.304, 222.441, 229.673, 227.808, 216.760 | 227.808［216.760–236.304］ | 5/5 |
| F3 panic通常 | 207.730, 209.587, 216.380, 220.760, 203.937 | 209.587［203.937–220.760］ | 5/5 |
| F3 panic RAM | 207.835, 228.064, 213.679, 220.712, 211.137 | 213.679［207.835–228.064］ | 5/5 |
| F3 restart通常 | 243.356, 231.595, 229.320, 232.109, 238.075 | 232.109［229.320–243.356］ | 5/5 |
| F3 restart RAM | 228.835, 240.378, 229.006, 226.201, 237.225 | 229.006［226.201–240.378］ | 5/5 |
| F3 EIO通常 | 245.327, 240.235, 240.416, 248.582, 248.887 | 245.327［240.235–248.887］ | 0/5 |
| F3 EIO RAM | 224.334, 232.981, 226.914, 227.897, 229.957 | 227.897［224.334–232.981］ | 0/5 |
| 非FEC clean | 235.054, 236.820, 229.258, 230.624, 233.836 | 233.836［229.258–236.820］ | 5/5 |
| 非FEC data | 222.291, 219.008, 223.010, 220.929, 215.966 | 220.929［215.966–223.010］ | 5/5 |

正式50件は40期待一致・10不一致です。EIO期待は`verity-eio`のままで、通常/RAMとも5/5がRS訂正後read成功となり、期待に対する反証です。その他8条件は各5/5一致しました。restart10件はhost停止なしの自然終了0、その他40件は証拠観測後のhost停止で、最終exit 0を自然終了成功へ混ぜていません。

## 仮説別の判定

**F3：本条件ではFEC内部hash lookupの再入→guard EIO→modeのfatal方針を高確度で支持します。** F3の全mode・全反復で同じbio IDについてlevel0 enter、FEC内hash lookupのlevel1、同じmetadata block5833への再入、`B3_GUARD level=1 result=-5`を観測しました。計装sourceではこのmarkerは実際の再入guardが-EIOを返す直前です。panic/restartは最初のguardの後、RS訂正の前にそれぞれdm-verity panic/restartへ進みました。全反復でguard各1回です。

反対に、同じ破損のEIOはguardを各243回通過した後にRSがcolumn17を1 symbol訂正し、`B3_EXIT ... result=0`、通常readall/loginまたはRAM両read status 0へ到達しました。例えばEIO RAMのrepeat0は次の実行順でした。

```text
B3_RAM_BEGIN target=4096 blocks=5832
B3_ENTER id=1 type=1 block=5833 level=0 mode=0
B3_HASH id=1 data_block=0 level=1
B3_ENTER id=1 type=1 block=5833 level=1 mode=0
B3_GUARD id=1 level=1 result=-5
# guardは計243回
B3_RS id=1 column=17 neras=0 result=1
B3_EXIT id=1 level=1 result=0
```

上の抜粋はtimestamp・共通prefixを省略しています。guard後もEIOでは訂正できる対照により、容量超過だけを原因とする説明を反証します。RAMの明示的read開始後にも全5回同じ経路へ入り、root mount/init開始前に限る説明も反証します。非FEC cleanは5/5成功、data1 byte対照は5/5 dm-verity panicで、guardは0回でした。ただしguard無効化の反実仮想や全hash/rootsを試したわけではなく、必要十分性・製品一般へは広げません。

EIOの「訂正後read成功」はmapperの読取り完了とRS/verity traceに基づきます。読み出した全data bytes自体は保存しておらず、hostの独立候補imageとcleanの全bytes一致とは別の観測です。

**F6関連：** BではF3 restartの両pathで自然終了0を各5/5観測しました。RESET継続や2回目bannerはBの要件ではなく、Fで別に観測します。別slot復帰・trybootの証拠ではありません。

**alias修正：** 通常/RAMのcleanがsmokeと正式で各6/6成功し、旧RAM loader失敗を再現しませんでした。CPIO payload不変・aliasだけの修正と依存閉包の負対照を合わせ、alias欠落の説明を強く支持します。loaderの動的openat traceは未採取です。

## 保存・検査・予算

[archive](2026-11-15-dm-verity-fec-stage-b/evidence.tar.gz)は244 member、8,994,014 byte、SHA-256 `15d4a84c9bb2779aeefe90528b2f2b32d3a3c12bb43b217303d2555bfc4cb1a4`です。全memberのhashを再読込みして照合しました。全60 serial/QMP/判定、case共通の入力設定、source、input manifest/位置、kernel config/trace patch/関係source、initramfs、raw driver log・wall、collectorを含みます。common SD/pack/kernel bodyは[host archive](2026-11-15-dm-verity-fec-host-dry/evidence.tar.gz)を参照し、重複保存しません。bootごとのPopen argv/env全体の独立snapshotは未保存で、case設定・固定source・serial実cmdline/hashから再現する情報と区別します。

```text
ok - 60 unique trials (10 smoke + 50 formal); 40 formal matches; no timeout or clean failure
formal_boot_wall_sum=11416.051653823088
formal_host_terminated=40
```

正式driverの実経過wallは**11,445.745秒（3時間10分45.745秒）**、boot wall合計は上記です。host検査後のsmokeは別枠です。終了時の保守的累積時計は約10時間18分で、36時間上限には近づいていません。残りC〜Fは33 smoke＋165正式boot、240秒/boot＋準備4時間で、累積約27時間半の仮見積りです。空きは約150 GiB、deadlineは2026-11-17 00:17:52 UTCのままです。

実行中にmainへのPR #259 squash-merge通知を受け、別の作業treeへfresh main `ddb5b69`を通常merge（`4539c54`）しました。3文書の競合はstage Aの内容とB以降の追記を保持し、merge前後のtreeが同一であることを確認しました。実行cloneは変更していません。PRはmain対象で、rebase・force pushはしません。

文書とsourceの最終検査結果は本段階のcommit・報告に添付します。bench sourceはhost fixture成功後から不変で、mergeによる変更もありません。今回の既知のmodule署名拒否もrawに残し、正常製品bootや全module loadの合格とはしません。RS誤訂正をkernelが拒否する容量超過対照はDで未実行で、CLIの製品設計上の示唆は依然host限定です。実機SD/LCD/firmware tryboot/電断/A-B復旧は未確認。RS研究限定・製品出荷禁止、03914台帳同期保留を維持します。
