# fs-compare matrix 反復測定（E3: T5 書き込み量、E4: T4-sync の idle 書き込み）

2026-11-15。第2段（125 variant、各1回）で観測した差が、実際のoption差なのか一過性のばらつきなのかを、反復測定で確かめた記録です。

## 目的

- **E3**: 第2段の `T5`（workload 中の総書き込み sector 数）で base との差が出た 24 variant を各 5 回測り、median/min/max で差の再現性を評価する
- **E4**: 第2段の `T4-sync`（sync 後 600 秒の idle window での書き込み、`write_sectors` 列）で idle 書き込みが観測された 18 構成を各 3 回測り、継続的な idle 書き込みかを確かめる

## 条件

- harness: `board/cardputerzero/tools/bench/fs-compare-matrix.sh`（branch `devin/1794125029-fs-compare-harness` の commit `b9c57da` + 第2段 harness の staged 修正。guest 側の script は main と同一内容）
- plan: `e34-2026-11-15`（174 行。T5 は 24 variant x 5 回、T4-sync は 18 構成 x 3 回）。plan の写し（`plan.tsv`）は data branch の archive に同梱
- 実行: `docker/msd-dev` 内で `board/cardputerzero/tools/bench/fs-compare-matrix.sh -j 4 <plan.tsv>` を実行
- QEMU 11.1.2（TCG）、guest kernel 6.18.59-v8
- 実行 178 attempt: `ok` 174、`fail:terminated_signal_15` 4（中断時に停止された run。残行はやり直して全 174 行が `ok` で揃った）
- 各 run directory の `inputs.sha256` に入力 file（image・guest script・variants 定義）の SHA-256 が記録され、archive に含まれる

### 測定の読み方

`T4-sync` は workload → `sync` → 600 秒の idle window の順で、summary の `write_sectors`/`write_ios`/`last_write_s` は idle window 中の test device の書き込み（`T4_RESULT`）。`quiesce_write_sectors`/`quiesce_write_ios` は workload 前の `quiesce_device`（device が落ち着くまでの待機）中の書き込みであり、idle window とは別の区間である（第2段の記録と同じ列の意味）。

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
| P136 | L1 | LUKS `--perf-submit_from_crypt_cpus` | 96,168 | +8 (+0.0%) | **再現せず**（第2段は +32%） |

18 variant のうち **P136 を除く 17 variant** で、第2段の 1 回測定と同じ方向・同じ大きさの差が再現した（各 run の min-max 幅は median の数 %以内）。**P136 は第2段で +32% だったが、今回は base の L1 とほぼ同値（+0.0%）** で、第2段の観測は一過性だったと判断する。`submit_from_crypt_cpus` の書き込み量への効果がないとまでは言い切れず、「今回の条件では第2段の増加が再現しなかった」が結論になる。

その他の注目点:

- **btrfs の透過圧縮（P089/P090/P091/P104）は書き込みを 56〜62% 削減**し、dup metadata と合わせた B2 の書き込み倍率を大きく下げる。`/data` の LUKS+btrfs+dup+xxhash64 方針で compress 系 option が有効な根拠になる
- **dm-integrity の `--integrity-no-journal`（P113）は書き込みを -70.3%** に減らす。journal 付き integrity（I1）は base と比べて最も書き込みが多い
- ext4 の `fast_commit`（P006）は -17.7% 削減。`chattr +S`（P023）は sync 動作のため +47.7% と最大の増加

### E4: T4-sync の idle window 書き込み（`write_sectors`、median / 各 run）

第2段で idle 書き込みが非 zero だった構成の再測定結果:

| 構成 | base | idle sectors（3 run） | 最後の write（秒） | 判定 |
|---|---|---|---|---|
| P044 | F1 | 6,720 / 6,720 / 6,720 | 259〜268 | **継続的**（`active_logs` が原因。F1 base は 0） |
| F3 | - | 5,736 / 5,736 / 5,736 | 219〜221 | **継続的**（F3 構成自体の idle 書き込み） |
| P070 | F3 | 5,736 / 5,736 / 5,736 | 231〜235 | F3 base と同じ（variant による増分なし） |
| P071 | F3 | 5,736 / 5,736 / 5,736 | 145〜234 | 同上 |
| P072 | F3 | 5,736 / 5,736 / 5,736 | 144〜151 | 同上 |
| P073 | F3 | 5,736 / 5,736 / 5,736 | 206〜215 | 同上 |
| P097 | B2 | 0 / 0 / 0 | なし | 再現せず（第2段の 592 sector は一過性） |
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

- **f2fs の F3（圧縮有効の構成）系は、600 秒の idle window の後半（140〜270 秒）に 5,736 sector の書き込みが毎回出る**。variant 差はなく F3 構成自体の挙動。P044（F1 + `active_logs`）も 6,720 sector が継続的に出て、`active_logs` が F1 に idle 書き込みを持ち込んでいる
- **dm-integrity 系（I1/I2）と LUKS+integrity 系（L3）の idle window 書き込みは最大でも 88 sector で、window 最初の約 25 秒以内の追い書きだけ**。sync 後に継続する書き込みではない。第2段で `quiesce_*` 列に見えた約 32K sector は workload 前の settling であり、idle window の書き込みではなかった
- **btrfs（B2・P097）は idle window で 0**。第2段で見えた 592 sector は一過性

## 結論

1. 第2段の T5 のずれは P136 を除き全て実差。btrfs の compress 系・`-m single`・`--nodesize`・`--mixed`、integrity の no-journal・internal_hash、ext4 の fast_commit は書き込み削減として有効
2. 継続的な idle 書き込みがあるのは **f2fs の F3 系（5,736 sector/回）と P044（F1 + active_logs、6,720 sector/回）**。dm-integrity 系・LUKS 系・btrfs は sync 後すぐに静まる（btrfs は 0）。ただし I2/L3 系に残る最大 88 sector の追い書きをもって直ちに §10 適合とはしない — 追い書きが終わるまでの操作・progress の扱い、または [書き込みの台帳](../design/write-policy.md) の例外としての登録が必要で、評価は台帳側で行う
3. f2fs 圧縮系を `/data` に使う案があるなら、この idle 書き込み（どの process が何を書くか）を実機前に切り分ける価値がある

## 失敗した試行

- `fail:terminated_signal_15` が 4 attempt（作業中断時に QEMU が停止された run）。やり直しで `ok` を揃えたため測定値への影響はなし。中断された run の log は archive に残っている

## 未確認

- QEMU/TCG での値であり、実機の絶対値・実 SD への影響は未確認（性能値は実機でのみ確定する方針）
- f2fs F3 系の 5,736 sector idle 書き込みの主体（GC・圧縮関連の background 処理等）は未同定
- P136（`submit_from_crypt_cpus`）の第2段 +32% は再現しなかったが、どちらの条件でも効果なしとまでは言い切れない（単回の外れ値の可能性が高いが、さらなる反復はしていない）
