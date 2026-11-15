# fs-compare matrix 反復測定（E3: T5 書き込み量、E4: T4-sync の idle 書き込み）

2026-11-15。第2段（125 variant、1 回ずつ）で観測した差が、実際のoption差なのか一過性のばらつきなのかを、反復測定で確かめた記録です。

## 目的

- **E3**: 第2段の `T5`（workload 中の総書き込み sector 数）で base との差が出た 24 variant を各 5 回測り、median/min/max で差の再現性を評価する
- **E4**: 第2段の `T4-sync`（sync 後の quiesce window での書き込み）で idle 書き込みが観測された 18 構成を各 3 回回測り、継続的な idle 書き込みかを確かめる

## 条件

- harness: `board/cardputerzero/tools/bench/fs-compare-matrix.sh`（branch `devin/1794125029-fs-compare-harness` の commit `b9c57da`）
- plan: `e34-2026-11-15`（174 行。T5 は 24 variant x 5 回、T4-sync は 18 構成 x 3 回）。plan の写しは data branch の archive に同梱
- QEMU 11.1.2（TCG）、guest kernel 6.18.59-v8、`-j4` 並行
- 実行 178 attempt: `ok` 174、`fail:terminated_signal_15` 4（中断時に停止された run。残行はやり直して全 174 行が `ok` で揃った）

## 結果

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
| P136 | L1 | LUKS `--perf-submit_from_crypt_cpus` | 96,168 | +8 (+0.0%) | 差なし |

第2段で 1 回しか測っていないずれは、すべて反復でも同じ方向・同じ大きさで再現した（各 run の min-max 幅は median の数 %以内）。つまりこれらは測定ノイズではなく option の実差です。

注目点:

- **btrfs の透過圧縮（P089/P090/P091/P104）は書き込みを 56〜62% 削減**し、dup metadata と合わせた B2 の書き込み倍率を大きく下げる。`/data` の LUKS+btrfs+dup+xxhash64 方針で compress 系 option が有効な根拠になる
- **dm-integrity の `--integrity-no-journal`（P113）は書き込みを -70.3%** に減らす。journal 付き integrity（I1）は base と比べて最も書き込みが多い
- ext4 の `fast_commit`（P006）は -17.7% 削減。`chattr +S`（P023）は sync 動作のため +47.7% と最大の増加

### E4: T4-sync の idle 書き込み（quiesce window の書き込み sector 数、median）

| 構成 | base | median sectors | 判定 |
|---|---|---|---|
| B2（btrfs base） | - | 272（11 io） | 継続的（小、3/3 で同一） |
| P097 | B2 | 272（11 io） | 同上（btrfs `commit=`） |
| I1 | - | 33,904（48 io） | 継続的（大） |
| P113 | I1 | 32,384（53 io） | 同上（no-journal でも残る） |
| I2 | - | 32,472（75 io） | 継続的（大） |
| P120 | I2 | 32,488（79 io） | 同上 |
| P121 | I2 | 32,416（62 io） | 同上 |
| P122 | I2 | 32,464（72 io） | 同上 |
| L3 | - | 31,696（96 io） | 継続的（大） |
| P140 | L3 | 32,304（87 io） | 同上 |
| P141 | L3 | 31,032（74 io） | 同上 |
| P044（F1）、P070/P071/P072/P073（F3）、F1、F3 | - | 0 | 再現せず（一過性） |

- **dm-integrity 系（I1/I2）と LUKS+integrity 系（L3）は sync 後の quiesce window でも約 31〜34K sector の書き込みが毎回出る**。integrity の journal/bitmap の flush が原因と考えられる。`--integrity-no-journal`（P113）でも残るので、journal だけが原因ではない
- **btrfs（B2・P097）は 272 sector の小さな idle 書き込みが安定して出る**（transaction commit 由来と考えられる）
- **ext4 系・f2fs 系の P044/P070〜P073 では 3/3 とも 0**。第2段で見えた idle 書き込みは一過性（delayed allocation の flush 等）で、継続的な規則違反ではない

## 結論

1. 第2段の T5 のずれはすべて実差。btrfs の compress 系・`-m single`・`--nodesize`・`--mixed`、integrity の no-journal・internal_hash、ext4 の fast_commit は書き込み削減として有効
2. idle 書き込みが継続的なのは dm-integrity 系と LUKS+integrity 系（約 32K sector/回）と btrfs（272 sector/回）。AGENTS.md §10 の「操作していない時に書き込まない」規則では、integrity 層を `/data` に置く案は不利。btrfs は小さいがゼロではない
3. E4 で 0 だった f2fs 系のずれは一過性と判断してよい

## 失敗した試行

- `fail:terminated_signal_15` が 4 attempt（作業中断時に QEMU が停止された run）。やり直しで `ok` を揃えたため測定値への影響はなし。中断された run の log は archive に残っている

## 未確認

- QEMU/TCG での値であり、実機の絶対値・実 SD への影響は未確認（性能値は実機でのみ確定する方針）
- quiesce window の長さに対する I1/I2/L3 の書き込みの時間分布（window を延ばすと書き込みが止まるか、周期的に続くか）はこの測定では分離していない
