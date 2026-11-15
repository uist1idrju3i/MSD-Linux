# fs-compare matrix 反復測定（E3: T5 書き込み量、E4: T4-sync の idle 書き込み）

2026-11-15。第2段（125 variant、各1回）の差の反復可能性を調べた記録です。同条件で差が繰り返されたことと、option単独の因果・製品規則への適合は別に評価します。

## 目的

- **E3**: `T5`の24構成（比較base 6: E1/F1/F3/B2/I1/L1とvariant 18）を各5回、計120成功runで比較する。24全てがvariantではない
- **E4**: `T4-sync`（sync後600秒のidle window、`write_sectors`列）の18構成を各3回測り、第2段のidle writeの反復と比較baseとの差を確認する

## 条件

- harness: `board/cardputerzero/tools/bench/fs-compare-matrix.sh`、baseは`b9c57dabf6de17c6cdff5e77293cde8ccd3cf17d`。guestとvariant定義には後述のdirty patchがあります。mainとの同一性ではなくruntime hashで照合しました
- plan: `e34-2026-11-15`。174成功run=120 T5+54 T4-sync（18構成×3回）。後者はbase 6（F1/F3/B2/I1/I2/L3）とvariant 12。集計CSVは174行ではなく42群（T5 24+T4-sync 18）で、nの合計が174
- 実行時は`docker/msd-dev`内でmatrix driverへ`-j 4`とplanを渡しました。`<plan.tsv>`は旧文書のplaceholderであり標準入力redirectではありません。保存した`plan.tsv`を使い、baseとdirty patchを復元して同じ入力hashを用意した後、新しい出力先で `docker/msd-dev bash board/cardputerzero/tools/bench/fs-compare-matrix.sh -j 4 --matrix-id e34-2026-11-15 --runs-dir output-e34-replay/runs plan.tsv` を実行します。元出力へ再実行しません
- QEMU 11.1.2（TCG）、guest kernel 6.18.59-v8
- 実行 178 attempt: `ok` 174、`fail:terminated_signal_15` 4（中断時に停止された run。残行はやり直して全 174 行が `ok` で揃った）
- 各 run directory の `inputs.sha256` に入力 file（image・guest script・variants 定義）の SHA-256 が記録され、archive に含まれる

### 測定の読み方

`T4-sync` は workload → `sync` → 600 秒の idle window の順で、summary の `write_sectors`/`write_ios`/`last_write_s` は idle window 中の test device の書き込み（`T4_RESULT`）。`quiesce_write_sectors`/`quiesce_write_ios` は workload 前の `quiesce_device`（device が落ち着くまでの待機）中の書き込みであり、idle window とは別の区間である（第2段の記録と同じ列の意味）。

## 結果

### 固定した保存先と再集計

raw archiveは[data枝の固定commit](https://github.com/uist1idrju3i/MSD-Linux/blob/e9d4d1431bb3fafb91a8c3c449ad99be6d6992ed/fs-compare/e34-matrix.tar.zst)、SHA-256 `3369f24a65454966d6ea2ad59360221740d39d4f74d82e02ecfcd588790b4530`です。[追補](https://github.com/uist1idrju3i/MSD-Linux/tree/e9d4d1431bb3fafb91a8c3c449ad99be6d6992ed/fs-compare/e34-provenance)にplan、4中断run ID、dirty patch、元集計command、可搬な監査用集計器を保存しました。追補のSHA256SUMS自体のhashは `d067f83a7a333b9267b05c04cf8b1ce938741f322947065f5c32f7353afd2df2`です。

全1,073 memberを既存manifestと照合し、178本のinputs.sha256に記録された10 harness入力と現存fileの一致を確認しました。matrix driver自体はruntime hash未収録で、今回のsnapshotと区別します。patchはb9c57dabf6de17c6cdff5e77293cde8ccd3cf17dとの差であり、当時のindex状態や未保存binaryの同一性まで証明するものではありません。可搬集計器で成功174・42群・中断4を確認し、既存CSV全fieldを再現しました。新規QEMU測定ではありません。

集計は [2026-11-15-fs-compare-matrix.csv](2026-11-15-fs-compare-matrix.csv)。raw data は data branch `data/fs-compare-experiments` の `fs-compare/e34-matrix.tar.zst`（中身の file 別 SHA-256 は `e34-matrix.files.sha256`）。

### E3: T5 書き込み量（base に対する差、median、sector 数）

| variant | base | option | median | 差 | 再現性 |
|---|---|---|---|---|---|
| P006 | E1 | ext4 `fast_commit` | 79,120 | -17,040 (-17.7%) | 5/5 で一貫 |
| P020 | E1 | mount `dirsync` | 109,344 | +13,184 (+13.7%) | 5/5 で一貫 |
| P023 | E1 | `chattr +S` | 142,056 | +45,896 (+47.7%) | 5/5 で一貫 |
| P024 | E1 | `chattr +D` | 109,360 | +13,200 (+13.7%) | 5/5 で一貫 |
| P044 | F1 | f2fs `active_logs` | 85,496 | +10,968 (+14.7%) | 5/5 で一貫 |
| P072 | F3 | f2fs `compress_log_size` | 24,752 | -12,312 (-33.2%) | 5/5 で一貫 |
| P074 | F3 | f2fs `compress_mode` | 86,312 | +49,248 (+132.9%) | 5/5 で一貫 |
| P080 | B2 | btrfs `-m single` | 179,800 | -47,504 (-20.9%) | 5/5 で一貫 |
| P086 | B2 | btrfs `--nodesize` | 169,160 | -58,144 (-25.6%) | 5/5 で一貫 |
| P087 | B2 | btrfs `--mixed` | 169,656 | -57,648 (-25.4%) | 5/5 で一貫 |
| P089 | B2 | btrfs `compress` | 86,728 | -140,576 (-61.8%) | 5/5 で一貫 |
| P090 | B2 | btrfs `compress` | 99,448 | -127,856 (-56.2%) | 5/5 で一貫 |
| P091 | B2 | btrfs `compress-force` | 90,744 | -136,560 (-60.1%) | 5/5 で一貫 |
| P104 | B2 | `chattr +c` | 92,984 | -134,320 (-59.1%) | 5/5 で一貫 |
| P110 | I1 | integrity `internal_hash` | 284,752 | -74,152 (-20.7%) | 5/5 で一貫 |
| P112 | I1 | integrity `--sector-size` | 541,872 | +182,968 (+51.0%) | 5/5 で一貫 |
| P113 | I1 | integrity `--integrity-no-journal` | 106,560 | -252,344 (-70.3%) | 5/5 で一貫 |
| P136 | L1 | LUKS `--perf-submit_from_crypt_cpus` | 96,168 | +8 (+0.0%) | **再現せず**（第2段は +32%） |

18 variant中17で第2段と同方向の差を反復しました。P136は第2段の+32%に対し今回はL1比+8 sector（+0.0%）で増加を再現しませんでした。一過性のばらつきは候補ですが、両測定の差の原因は未同定です。効果なし・統計的同等性の証明ではありません。

その他の注目点:

- btrfs圧縮のP089/P090/P091/P104は、このworkloadでB2比56〜62%少ない書き込みを反復しました。新設計のLUKS+btrfs（data/metadata DUP・xxhash64・zstd）そのものの測定や規則適合の証拠ではありません
- **dm-integrity の `--integrity-no-journal`（P113）は書き込みを -70.3%** に減らす。journal 付き integrity（I1）は base と比べて最も書き込みが多い
- ext4 の `fast_commit`（P006）は -17.7% 削減。`chattr +S`（P023）は sync 動作のため +47.7% と最大の増加

### E4: T4-sync の idle window 書き込み（`write_sectors`、median / 各 run）

第2段で idle 書き込みが非 zero だった構成の再測定結果:

| 構成 | base | idle sectors（3 run） | 最後の write（秒） | 判定 |
|---|---|---|---|---|
| P044 | F1 | 6,720 / 6,720 / 6,720 | 259〜268 | 遅い時刻の書き込みを反復。active_logs変更との関連はあるがwriter未同定 |
| F1 | - | 0 / 0 / 0 | なし | P044の比較base |
| F3 | - | 5,736 / 5,736 / 5,736 | 219〜221 | 遅いwriteを各3回観測。writerは未同定 |
| P070 | F3 | 5,736 / 5,736 / 5,736 | 231〜235 | F3 base と同じ（variant による増分なし） |
| P071 | F3 | 5,736 / 5,736 / 5,736 | 145〜234 | 同上 |
| P072 | F3 | 5,736 / 5,736 / 5,736 | 144〜151 | 同上 |
| P073 | F3 | 5,736 / 5,736 / 5,736 | 206〜215 | 同上 |
| P097 | B2 | 0 / 0 / 0 | なし | 第2段の592 sectorは再現せず、原因は未同定 |
| B2 | - | 0 / 0 / 0 | なし | idle 書き込みなし |
| I1 | - | 0 / 0 / 0 | なし | なし |
| P113 | I1 | 0 / 0 / 0 | 7 秒のものあり | ほぼなし |
| I2 | - | 0 / 8 / 8 | 2〜7 秒 | ごく小さい追い書きのみ |
| P120 | I2 | 0 / 0 / 0 | 6〜7 秒 | ほぼなし |
| P121 | I2 | 32 / 8 / 8 | 18〜24 秒 | ごく小さい追い書きのみ |
| P122 | I2 | 32 / 8 / 32 | 5〜7 秒 | ごく小さい追い書きのみ |
| L3 | - | 88 / 0 / 88 | 6〜7 秒 | ごく小さい追い書きのみ |
| P140 | L3 | 88 / 88 / 0 | 6〜7 秒 | ごく小さい追い書きのみ |
| P141 | L3 | 88 / 0 / 0 | 5 秒のものあり | ごく小さい追い書きのみ |

読み取り:

- f2fs F3系は5,736 sector、P044は6,720 sectorを各3回観測しました。最後のwriteはF3系144〜235秒、P044 259〜268秒で、600秒の観測窓全体で継続していたという意味ではありません。F1は0でしたが、GC等のwriterと因果経路は未同定です
- **dm-integrity 系（I1/I2）と LUKS+integrity 系（L3）の idle window 書き込みは最大でも 88 sector で、window 最初の約 25 秒以内の追い書きだけ**。sync 後に継続する書き込みではない。第2段で `quiesce_*` 列に見えた約 32K sector は workload 前の settling であり、idle window の書き込みではなかった
- btrfs B2/P097は各3回0でした。第2段の592 sectorは再現せず、原因は未同定です。新しいLUKS+btrfs設計や全時間帯のwrite禁止を満たすとはしません

## 結論

1. T5の差は18 variant中17で反復し、P136の増加は再現しませんでした。同条件での反復可能性を示す結果で、因果の確定・安全性や製品設定の採用判定ではありません
2. f2fs F3系/P044の遅いwriteと、I2/L3系の最大88 sector・24秒までの追い書きは新しい判断材料です。量が小さい、観測窓内に静まるというだけで§10適合にはしません。操作・progressの完了時刻か例外登録を[台帳](../design/write-policy.md)で判断するまで未対応です。B2の0も新設計への適合判定とはしません
3. f2fs 圧縮系を `/data` に使う案があるなら、この idle 書き込み（どの process が何を書くか）を実機前に切り分ける価値がある

## 失敗した試行

- `fail:terminated_signal_15` が4 attempt。T5のP072 r5、P074 r1/r2/r3です。失敗行を成功統計へ混ぜず再試行を採用しました。中断の影響が全くないとは証明していません。run ID・元log・再試行はarchiveと追補に保持します

## 未確認

- QEMU/TCG での値であり、実機の絶対値・実 SD への影響は未確認（性能値は実機でのみ確定する方針）
- f2fs F3 系の 5,736 sector idle 書き込みの主体（GC・圧縮関連の background 処理等）は未同定
- P136の増加を再現しなかった理由、host負荷・cache等の交絡、実機への外挿は未確認です。今回新しいQEMU反復は実施していません
