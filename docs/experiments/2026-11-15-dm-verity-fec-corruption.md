# dm-verity(crc32c)+FEC の破損注入試験（B3）

2026-11-15。root=SquashFS+dm-verity(crc32c)+FEC 方針（[設計調査](../research/storage/rootfs-squashfs-verity-fec-design.md)）に対し、破損を注入した sdcard image で QEMU 起動を反復し、検出・訂正・停止の挙動を確認した。

## 条件

- kernel: `devin/1794708015-kernel-config-integrity` の `output-integrity` ビルド（`DM_VERITY=y`、`DM_VERITY_FEC=y`、`DM_CRYPT=y`、`BTRFS_FS=y`、`CRYPTO_CRC32C=y`、`CRYPTO_ZSTD=y`）。起動 log に `device-mapper: verity: crc32c using "crc32c-lib"` を確認
- hash tree + FEC: `board/cardputerzero/tools/dm-verity/verityfmt`（自前実装）が生成。crc32c は `veritysetup format` が userspace で拒否するため同 tool を使用。`data_blocks=5832`、`hash_start_block=5833`、`hash_area_blocks=7`、salt 32 byte。FEC は `fec_roots=8`（RS(255,247)）・`fec_blocks=5839`・`fec_start=5840`・interleave `rounds=24`（cryptsetup `VERITY_FEC_process` と kernel `dm-verity-fec.c` の `fec_interleave` と同じ配置）
- error mode: `panic_on_corruption`（F6 のみ `restart_on_corruption`）
- 実行: `docker/msd-dev bash board/cardputerzero/tools/bench/dm-verity-fec/run-all.sh /work/output-fscmp /work/output-b3/cases /work/output-b3/results-b3 4 480`（各 case 5 boot・timeout 480s・`--expected` で起動結果を照合）
- case 生成: `board/cardputerzero/tools/bench/dm-verity-fec/make-case.sh`（rootfs.img への byte 反転を注入）
- QEMU raspi3ap + icount（TCG）。QEMU での結果であり実機の挙動確認ではない

## case と結果

| case | 注入内容 | FEC | error mode | 期待 | 結果（5 boot） | 判定 |
|---|---|---|---|---|---|---|
| F0-A2 | なし（clean） | あり | panic | ready | 5/5 ready | 期待通り |
| F1-A2 | data block 2916 の1 byte反転（offset 11944059） | あり | panic | ready（FECで訂正して起動） | 5/5で `FEC 49152: corrected 1 errors` の後ready | 期待通り。1 byte反転の訂正を観測 |
| F2-A2 | data 領域 24 block に各 1 byte 反転（分散、rsn=247・rounds=24 の interleave 全域） | あり | panic | verity-error | 5/5 で `corrected 8 errors` の後 `failed to correct (8 erasures)` → `Kernel panic: dm-verity device corrupted` | 期待通り。訂正能力超過で検出・panic |
| F3-A2 | **最上位 hash block 5833 の 1 byte 反転**（offset 23891985、top level の digest index 4 内） | あり | panic | ready（FEC で訂正して起動） | 5/5 で `metadata block 5833 is corrupted` → `Kernel panic` | **期待と不一致。訂正されず panic**（後述） |
| F4-A2 | cmdline の root_hash 改ざん（`2a3f426f` → `2a3f4260`。image 無改変） | あり | panic | verity-error | 5/5 で `metadata block 5833 is corrupted` → panic | 期待通り。root_hash 不一致を検出 |
| F5-A2 | data blockの1 byte反転（F1と同じoffset） | なし（fec_roots=0） | panic | verity-error | 5/5で `data block ... is corrupted` → panic | FEC無しの対照。1 bit試験とはしない |
| F6-A2 | F2と同じ24 block分散反転 | あり | restart_on_corruption | verity-error | 5/5で破損検出とshutdown開始後、host監視器がSIGTERM | 検出を観測。restart完了・別slot復帰は未確認 |

## F3の分析: 再入依存が有力な説明、原因の確定ではない

F3 は「FEC が修復できる程度の破損で起動継続（ready）」を期待した case だが、5/5 全て panic した。切り分けの結果:

- F0-A2のrootfs.imgで、24 round×4096 byte列のparityを同じ符号化器で再計算した98,304列は一致しました（covered=5839 block）。同じ実装の自己整合であり、formatterの欠陥を否定する独立検査ではありません。
- kernel の動作で説明できる。`verity_verify_io` で hash block 5833 の verify が root_hash と不整合 → `verity_fec_decode(METADATA, 5833)` → `fec_decode_rsb` が RS 入力 block を読む際、data block 入力は `verity_hash_for_block` で検証される → その検証は（壊れた）最上位 block 5833 の digest に依存 → `fio->level` の再入ガードで nested decode が `-EIO` → `verity_handle_err` → `panic_on_corruption` で panic。stack trace も `verity_fec_decode → fec_decode_rsb → verity_hash_for_block → verity_verify_level → verity_handle_err` の順で一致する
- stackと固定sourceの再入guardはこの説明を支持しますが、eio/restart対照、独立codecとのcrc32c/FEC相互検証が未実施です。全ての上位hash破損が修復不能という一般則にはしません。下位hash破損が訂正されるかも未測定です。
- 製品要件への接続は[切り戻し設計](../research/storage/rootfs-squashfs-verity-fec-design.md)の未実装項目です。panic/restartの検出からfirmwareの別slot選択までは証明していません。

## F5/F6 が示す対照

- F5（FEC無し）はF1と同じ1 byte反転でpanic。1 bitの試験結果ではありません。
- F6は破損検出後のshutdown開始までを観測しました。旧監視器は破損markerでhost SIGTERMを送り、自然終了やrestart markerを待っていません。no-rebootでの正常終了・再起動完了とは扱いません。

## 生データと再現

- `output-b3/results-b3/<case>/boot*/` に serial log・result.txt、`<case>.csv` に各 run の wall 秒・exit_status・log SHA-256。data branch `data/fs-compare-experiments` の `fs-compare/b3-dm-verity-fec.tar.zst` に同梱
- オフライン parity 検査: session 上の check 用 C tool（verityfmt と同一の RS 符号化）で rootfs.img の全列を再計算・照合

## 失敗した試行・注意点

- F3の旧期待 `ready` と5/5 panicの不一致は歴史的な事前登録として保持します。旧 `run-all.sh` の期待表・raw・CSVは修正しません。次回用は後述のv2です。
- 各runのCSVは `valid=0`。dmesg dump行がserialにないためboottimeは無効です。機能判定は別に記録し、generic panicやhostによる停止をverity成功へ読み替えません。
- QEMU/TCG での挙動。実機での検出・panic・restart・tryboot 連携は `docs/research/verification/hardware-measurements.md` の実機計測計画に含める

## 未確認

- `error_mode=eio`/`restart` での最上位 hash block 破損の訂復可否（追加 case で検証可能）
- restart_on_corruption の実機での tryboot 連携
- 破損が FEC parity 領域・superblock 領域に入った場合の挙動（別 case で要検証）
- sha256対照、FEC roots=2/16、下位hash破損、登録の連続領域破損、data/hash block size差、全optionの直積は未実施。35 bootだけでB3全matrix完了とはしません。

## 次回の期待値v2（今回のQEMU再実行なし）

[expectations-v2.tsv](../../board/cardputerzero/tools/bench/dm-verity-fec/expectations-v2.tsv)はF0/F1=ready、F2〜F5=verity-panic、F6=verity-restartです。F3の新期待は今回の観測に基づく次回仮説で、旧試行の合否を変更しません。新生成器はF2/F6を24 blockの各1 byte全反転へ揃えます。旧commitの生成器に残った9 block（roots+1）・1 bit反転と保存記録の24 blockを混同しません。

```sh
docker/msd-dev bash board/cardputerzero/tools/bench/dm-verity-fec/run-all-v2.sh /work/output-fscmp /work/output-b3-next/cases /work/output-b3-next/results 4 480
```

入力caseは現行make-case.shで新規生成し、F0から順に作ります。formatterはcaseごとに再buildしてsource/binary hashを保存します。旧cache binaryは再利用しません。v2は新しい出力先だけを受理し、機能判定をfunctional.json、時刻の妥当性をCSVのvalidとparse.logへ分けます。F6はverity固有の破損に加えrestart markerまたは新boot bannerが必要で、host signal・timeoutを成功にしません。boottime無効だけでは機能失敗にしません。

## RS移植元の監査（未解決）

verityfmtのRS部分はPhil Karn由来libfecのportとのcommentを持ちます。移植元の正確な版・copyright通知・変更範囲・LGPL/GPL条件の対応をまだ監査できていません。違反と断定する根拠はなく、互換性testの成功もlicense監査の代用ではありません。監査完了まで製品formatterとして出荷・組込みをしません。
