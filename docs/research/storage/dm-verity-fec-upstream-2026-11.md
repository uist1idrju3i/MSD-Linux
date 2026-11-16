# dm-verity FECの上流動向とB3追試への含意（2026-11-16調査）

[保存領域の調査へ戻る](README.md)

dm-verityのforward error correction（FEC）について、kernel、cryptsetup、Android、RAUC、communityの一次資料を2026-11-16に調べました。それを、MSD/Linuxの現行kernelのsourceと、B3追試の観測に照らし合わせます。この文書は調査と推論の記録です。製品の設定は変更していません。kernelの計装と実機での試験は、まだ行っていません。

## 1. 結論

1. **現行kernelでは、FECの再帰が無効です**。現行kernelは、Raspberry Pi kernel `b3495ea401d709af0701a85babcba5e3d788a602`（Linux 6.18.59）です。このsourceの `verity_fec_decode()` は、`if (fio->level) return -EIO;` で、2段目以降のFECを拒否します。これは上流commit `d9f3e47d3fae`（「dm-verity: disable recursive forward error correction」、CVE-2025-71161）の内容と同じです。
2. **そのため、panicモードでは、hash treeの破損をFECで直せないことがあると推論できます**。FECは、RS codewordを組み立てるときに、同じcodewordに入る各data blockについて `verity_hash_for_block()` を呼びます。そのとき必要になるhash blockが壊れていると、2段目のFECになるので `-EIO` が返り、`verity_handle_err()` が呼ばれます。`panic_on_corruption` では、この時点でpanicします。外側の訂正は終わっていません。EIOモードでは、`verity_handle_err()` が1を返すだけなので、そのblockは消失の候補にならないまま外側の復号が続き、訂正に成功し得ます。
3. この推論は、B3の観測と合います。F3（上位hashの破損）は、panicモードでは5+5回panicしました。同じ破損をEIOモードで試すと、10回すべてで訂正され、全体を読み切りました。段階Cの下位hashの先頭への破損（C-lower-head）も、panicモードで4回panicしています（2026-11-16 09:30 JSTの時点）。ただし、根拠はsourceを読んだことと、結果の対応だけです。kprobeなどで経路を計測したわけではありません。
4. **veritysetupの `verify` が示すFECの結果は、参考情報にとどまります**。cryptsetup main（`ce9a98cd4237`、2026-11-15）の `lib/verity/verity.c` は、「Found %u repairable errors with FEC device.」を出した直後に、「If root hash failed, we cannot be sure it was properly repaired」というcommentを置いています。v2.3.5のrelease notesにも、userspaceのFEC verifyは情報だけで、FECの後にhashを確かめないと書かれています。B3で見た、誤訂正でも終了値0を返す動き（host、2.7.5）は、上流の既知の制約と一致します。
5. **kernelでは、FECで直したblockをhashで確かめてから使います**（kernel文書の「dm-verity validates any FEC-corrected block against the wanted hash before using it」）。製品で完全性の根拠にできるのは、userspaceの終了値ではなく、kernelのこの検査です。

## 2. 一次資料

| 資料 | 日付 | 内容 |
|---|---|---|
| [kernel文書 verity](https://docs.kernel.org/admin-guide/device-mapper/verity.html) | 2026-11-16取得 | FECで直したblockもhashで検査する。`fec_roots` は2〜24で、interleaveがあるので2を推奨する（約0.8%）。hashを消失位置の特定に使うので、訂正できる量が2倍になる |
| [torvalds/linux d9f3e47d3fae](https://github.com/torvalds/linux/commit/d9f3e47d3fae0c101d9094bc956ed24e7a0ee801) | 2025-11-14 | 再帰FECを無効にした。理由は、最大253^4回のDoS（Red Hat QEが再現）と、`fio->bufs` を共有しているため再帰では正しく動かないこと |
| [CVE-2025-71161の解説](https://www.sentinelone.com/vulnerability-database/cve-2025-71161/) | 2026-01-23公開 | 上記をCVE化したもの。stableのcommitは232948cf、4220cb37、897d9006、e227d2b2。AIが生成した二次資料なので、commit番号以外は使わない |
| [stable 6.12: RS rootsの境界の修正（take 2）](https://ratatoskr.run/linux-patches/2025/01/7052910) | 2025-01 | rootsがblock境界をまたぐと、parityを誤って読んでいた（cryptsetup issue 923） |
| [Eric Biggers: FECの最適化と修正 v2（7件）](https://lwn.net/Articles/1051610/) | 2025-12-19 | `fec_io` のmempool化、REED_SOLOMONを `m` にできるようにする、など |
| [Eric Biggers: FECの修正と整理（22件）](https://patchew.org/linux/20260206045942.52965-1-ebiggers@kernel.org/) | 2026-02-05 | 小さすぎるFEC・hash deviceの拒否、訂正数の重複計数、erasures配列の大きさ、block境界をまたぐparityの範囲外読み出し（take 3）、文書の改訂 |
| [stable 6.18.y: FEC計算のbuffer overflowの修正](https://www.spinics.net/lists/stable/msg987612.html)（上流 `31d6e6c0ba8d`） | 2026-07-08 | `*neras <= roots` が `roots+1` に達し、`decode_rs8()` の `lambda[]` から1要素はみ出していた |
| [Android: 訂正数のstatus表示 ae97648e14f7](https://android.googlesource.com/kernel/common/+/a328ecdaed9d18dca9eec61b1e09f7cc8c347e12) | 2025-11-18（上流） | `dmsetup status` に `fec_corrected_blocks` を加えた。v6.19-rc1から |
| [RAUC PR 1846](https://github.com/rauc/rauc/pull/1846) | 2026-01-05 merge | 上の表示の追加で、RAUCのstatusの解析が壊れたため直した |
| [cryptsetup v2.3.5 release notes](https://gitlab.com/cryptsetup/cryptsetup/-/blob/65239e38b829affdcc1c3634aa562fb664759c5c/docs/v2.3.5-ReleaseNotes) | 2021 | userspaceのFEC verifyは情報だけ。RS decoderは、parityが壊れていても「直せた」と報告し得る |
| [cryptsetup v2.8.0 release notes](https://cdn.kernel.org/pub/linux/utils/cryptsetup/v2.8/v2.8.0-ReleaseNotes) | 2025 | `--error-as-corruption`（kernel 6.12の `*_on_error`）、hash deviceの大きさの事前検査 |
| [dm-crypt ML 2019](https://www.spinics.net/lists/dm-crypt/msg07942.html) | 2019 | roots=24でkernelが1 bitを直せず、veritysetup verifyは「repairable」と出した報告 |
| [systemd PR 18789](https://github.com/systemd/systemd/pull/18789) | 2023-04 merge | systemd-veritysetupにFECのoptionを加えた |

## 3. 現行kernel（6.18.59）に入っているもの

configsが固定するtarball（[raspberrypi/linux b3495ea](https://github.com/raspberrypi/linux/tree/b3495ea401d709af0701a85babcba5e3d788a602)）をBuildrootで展開したsourceを読んで確かめました（version: `VERSION=6 PATCHLEVEL=18 SUBLEVEL=59`）。

| 上流の変更 | 6.18.59 | 根拠 |
|---|---|---|
| 再帰FECの無効化（d9f3e47d3fae） | 入っている | `dm-verity-fec.c` の `if (fio->level) return -EIO;` |
| buffer overflowの修正（31d6e6c0ba8d） | 入っている | read失敗時の条件が `*neras < v->fec->roots` |
| parityがblock境界をまたぐ場合の扱い | 入っている（`par_buf` で連結） | `dm-verity-fec.c` の `par_buf[DM_VERITY_FEC_MAX_ROOTS]` |
| 小さすぎるdeviceの拒否 | 一部を確認 | `FEC device is too small` などの文言。22件のseries全体は照合していない |
| `fec_corrected_blocks` のstatus表示（ae97648e14f7） | 入っていない | `dm-verity-target.c` に該当する出力がない |

## 4. B3追試への含意

| 項目 | 含意 | 確度 |
|---|---|---|
| F3の仮説3（kernelのFEC再入） | sourceの経路で裏付けられる。panicモードでは、2段目のFECが `-EIO` を返したところで `verity_handle_err()` がpanicするので、訂正の前に止まる。仮説4（panicが訂正より先に止める）も、同じ経路の別の見方として成り立つ | 中（sourceと結果は対応するが、計測していない） |
| C-lower-headのpanic | 下位hash blockを直すFECが、codewordのdata blockを検査するために同じhash blockを必要とすると、2段目になって止まる、と説明できる | 中 |
| EIOモードでの回復 | 2段目の失敗が消失の候補を減らすだけで済むので、外側の復号が成功し得る | 中 |
| 予測 | panic/restartモードでは、hash treeの破損はFECで救えないことが多い。EIOモードでは救える場合がある。段階Cの他のhash条件とFで確かめられる | 推論 |

kernelの経路を確かめるには、`verity_fec_decode` と `verity_handle_err` にkprobe（またはtrace_printkを入れた研究用kernel）を付け、levelと戻り値を記録します。これは事前登録にない追加の計測なので、実行前に追記してから行います。

## 5. 製品の設計への含意（案。採否は利用者が決める）

1. **error modeとFECの組み合わせ**：`panic_on_corruption`（または `restart_on_corruption`）とFECを組み合わせても、hash treeの破損は直せないことが多いと推論します。data blockの破損は、必要なhash blockが健全であれば直せます。hash treeはdataに比べて小さい（B3の条件ではD=5832に対してhashは7 block）ため、偶発的な破損が当たる確率は低いです。ただし、上位のhash blockは、すべてのreadで必要になります。
2. **EIOモードの検討**：EIOモードとFECの組み合わせは、F3で回復しました。訂正したblockはhashで確かめてから使うので、改ざんの検出力は落ちません。一方で、直せない破損は、applicationからはEIOに見え、起動の途中で止まる場合があります。panicとrestart loopの回避、A/Bの切り戻しとの関係を、Phase Cで比べる必要があります。
3. **任意に実行する破損checkのcommand**：`veritysetup verify` の終了値や「repairable」を、完全性の根拠にしません。checkは、dm-verityのdeviceを全体読みして、kernelのEIOとlogで判定する形が候補です。2秒以上かかるので、progressと中断の可否を表示します（AGENTS.md §10）。
4. **fec_rootsの選び方**：kernel文書は、interleaveがあるのでroots=2を推奨しています。B3の段階Dの結果（roots 2/8/16）と、256MBの制約に照らして決めます。
5. **観測性**：訂正したblockの数（`fec_corrected_blocks`）はv6.19以降のstatusにあり、6.18.59にはありません。kernelを更新するときに使えるようになります。RAUCを使うなら、PR 1846以降の版が必要です。
6. **kernelの更新**：Eric Biggersの整理（22件）など、FECのcodeは2025〜2026年に大きく変わっています。kernelを更新したときは、B3の代表的な条件（F1、F3のpanic/EIO、C-lower-head）を回帰試験として流し直します。

## 6. communityとSNS

Hacker News、Reddit、Mastodonなどを検索しましたが、FECの挙動を具体的に論じた投稿は見つかりませんでした。見つかったのは、dm-verity全般やEROFSとの組み合わせの話題です。実際の運用で問題として報告されていたのは、mailing list（dm-crypt、dm-devel、stable）、Red Hat bugzilla、RAUCのissueでした。SNSで見つからなかったことは、問題がないことの根拠にはしません。

## 7. 未確認

- 再帰の拒否からpanicに至る経路を、kernelの計装で確かめていない。
- Raspberry Pi kernelの6.18.59に、上流の22件のseriesのどこまでが入っているかを、すべて照合していない。
- cryptsetup mainで、userspaceのFEC verifyの後にhashを検査し直すかどうかを、`verity.c` のcomment以外で確かめていない（2.7.5の挙動はhostで観測済み）。
- 実機、SDの実際のread error、firmwareのtryboot、電源断は試していない。
