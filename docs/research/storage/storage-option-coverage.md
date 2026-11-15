# storage全optionの分類と設計監査（2026-11-15）

## 範囲と現在の判断

利用者の「全optionを測定する」という要求を、代表matrixだけで完了扱いにしないための分類です。今回はsourceと保存資料の監査で、新しい性能測定ではありません。rootのcrc32c/FEC、dataのLUKS+btrfs DUP/xxhash64/zstd、当面のLUKS cipher既定維持を変更しません。ext4/e2fsprogs撤去はbtrfs移行後です。

03914で保留された `pending-work.csv` / `roadmap.md` の同期は保留のままです。測定の進捗を本表へ記録することと、製品実装済みへ台帳を変更することを分けます。l22は利用者の「本当に展開側に悪影響がないのであれば22」という条件付き判断を保持します。QEMUの有限回の結果だけで実機性能・RAMへの悪影響なしを保証しません。

## tokenごとの分類

全行は[分類CSV](../../experiments/2026-11-15-storage-option-coverage.csv)。`surface,token,status,reason,reference` の列を持ち、同名tokenもconsumerごとに分けています。

| 状態 | 意味 |
|---|---|
| 実測済み | 今回新たに条件差を測ったもの。今回は該当なし |
| 既測定 | 過去の保存済み測定がある。ただしreasonに示す値・条件だけで、tokenの全値を測定済みとはしない |
| 対象外 | 説明・版表示。性能を変える設定ではないという理由を各行に残す。将来の監査対象から削除する意味ではない |
| 実行不能 | sourceに存在しても現行configでは無効、または要求したparameterが固定版にない。理由を明記 |
| 未実施 | 独立した比較がない。固定条件として使っただけのflag、build option、library parameterも含む |

### 固定した一次資料

[source manifest](../../experiments/2026-11-15-storage-option-coverage.json)に版・公開URL・抽出方式・member別SHA-256、[入力archive](../../experiments/2026-11-15-storage-option-coverage.tar.gz)に実際の抽出入力を保存しました。archiveのsourceは上流由来で、元のcopyright/SPDXを保持しています。Buildrootは `8b238854d909c9cce32ef9671d968b03e323b55d`、kernelは `b3495ea401d709af0701a85babcba5e3d788a602`（6.18.59）。最新版との比較・更新の採否ではありません。

| surface | 入力・抽出範囲 |
|---|---|
| mksquashfs / unsquashfs | 4.7.5の `-help-all` 出力。codec固有flagも含む |
| zstd-cli / zstd-lib | 1.5.7の `--help` と `lib/zstd.h` の `ZSTD_c_*` / `ZSTD_d_*` token |
| cryptsetup / veritysetup | 2.8.7の各familyのman `.adoc` と共通option定義。例示・非推奨項目も残す |
| mkfs-btrfs / btrfs-tools | 6.10のmkfs parserのlong/short optionと、`btrfs*.rst` にあるCLI token |
| btrfs-mount | 固定kernel `fs/btrfs/super.c` の `fsparam_*` と `flag_no` が作る否定名 |
| zram / zswap | 固定kernelのDEVICE_ATTR・module parameter定義 |
| verity-table / fec / sig | 固定kernelのoptional table parameter定数。必須の位置引数はrootfs設計の表で管理 |
| kernel build | zram、mm、btrfs、SquashFS、device-mapper、cryptoの各Kconfigに直接定義されたsymbol |
| Buildroot build | 対象4 packageのConfig.in。kernelの実行時設定やupstream library設定とは区別 |

抽出は保存した入力に対する機械照合です。CLIはoption形の字句を拾うため、引数値の例示・他commandの共通定義も含み、各actionで受理されることまでは証明しません。Kconfigのinclude先全体、libzstdの全関数、汎用VFSの全mount flagや全sysctlまで網羅したという意味でもありません。値の直積は無限になり得るため、まずtokenの欠落を防ぎ、測定可能な値域・非対応理由を個別の事前登録へ展開します。未実施行を自動で対象外に振り替えません。

再照合は `python3 tests/storage-option-coverage/run.py`。保存入力のhash、抽出tokenとCSVの集合一致、重複、状態・理由・参照の空欄を検査し、空入力・欠損・重複・不正状態のfixtureも含みます。missing=0はこの明記した入力集合に対する値で、性能測定の完了率ではありません。

### 既測定との対応

| token・条件 | 記録・限界 |
|---|---|
| mksquashfs `-comp` / `-b` / `-Xcompression-level` / `-Xbcj` | [B1 raw](https://github.com/uist1idrju3i/MSD-Linux/tree/ab61a9ffa86635b02e0382f357d7da9e7d084077/storage-options)。16K〜1M×正level6点とcodec比較。負level・他flag・全値は未測定 |
| verityのFEC各引数、restart/panic | [B3 raw](https://github.com/uist1idrju3i/MSD-Linux/tree/ab61a9ffa86635b02e0382f357d7da9e7d084077/session-2026-11-15/evidence)。限定した35 boot。F3は旧期待readyに対してpanic、F6はshutdown後host SIGTERMで再起動完了未確認。過去の期待・失敗記録を変更しない |
| その他の全token | CSVの理由欄に沿って未実施または対象外・実行不能。既存fs-compareの比較は[既存option調査](filesystem-options.md)から参照できるが、B4〜B7の全条件へ読み替えない |

## 4K/8KがB1から消えた経緯

当初の事前登録は4K/8Kを含む9 block size×6 levelでしたが、[保存済み実行script](https://github.com/uist1idrju3i/MSD-Linux/blob/328bece4cd9f724aaafa83e5cc350c632762dc20/storage-options/mksquashfs-quick-scan/run-mksquashfs-matrix.sh)は16Kから始まります。後続も7×6＋codec比較4点＝46構成でした。除外理由と4K/8Kの失敗を示す記録は確認できません。実行不能や性能劣化で除外したとはせず、理由不明の計画逸脱・未実施として残します。元の条件を消さず、追加測定前にこの2値の構築可否を検査して記録します。

## 旧説明からの訂正

| 旧説明 | 訂正・一次資料の場所 |
|---|---|
| 正level1..22が全量、19..22はultra | zstd CLIは20..22に `--ultra` が必要、19には不要。mksquashfsはlibzstdへ `-Xcompression-level 22` を直接渡す。4.7.5のzstd wrapperは負levelも受理。`zstd_wrapper.c/.h` を参照 |
| zramの `comp_algorithm` に `zstd:1` 等を指定、dict非対応 | 名前選択と `algorithm_params` を分ける。固定 `zram.rst` は `algo=zstd level=8 dict=/etc/dictionary` を例示。sourceの存在と実imageのbuild/load成功は別 |
| zswapのzpool・exclusive_loads・same/non_same_filled_pagesを全比較 | 固定 `mm/zswap.c` の公開parameterは5件のみ。これら4旧parameterは実行不能。allocatorはzsmallocを直接使用し、zbud/z3fold切替も実行不能。旧計画として記録を残す |
| btrfs DUPはRAID1C2相当、xxhashがLUKSの完全性を代替 | DUPは同一device内2copy、xxhashは非暗号学的checksum。別device故障耐性や認証を追加しない。LUKS AES-XTSは暗号化だが認証ではない |
| luksChangeKeyでvolume key rotation | passphrase/keyslot変更でありvolume keyは不変。利用者方針を満たすreencryptと電断復旧は未設計。平文keyfileのFAT配置は既定採用しない。cryptsetup 2.8.7の `luksChangeKey` manを参照 |
| panic→再起動→別slotが自動成立 | [rootfs設計](rootfs-squashfs-verity-fec-design.md)にpanic timeout/watchdog、default/trial、health後の破損、両slot破損、永続flag時機を列挙。製品経路は未実装 |
| ARMにAES-NI、QEMU相対順位を実機選定へ使用 | AES-NIはx86の命令拡張。ARMのAES/NEON実装は別。QEMUは絶対速度・相対順位とも実機の代理ではない |
| PBKDFとcipher、key sizeと安全性を一括比較 | PBKDFの時間/RAM、data cipher throughput、hashの用途、security strengthを分離。XTSの2本分の合計鍵長を安全性bit数としない |

`/proc/crypto` は登録済み実装の一覧で、未load moduleや未buildの候補を列挙しません。全cipher/hash要求は維持し、固定Kconfig・module一覧・load結果・各APIが受理する組合せとの集合差を保存します。hardware用の候補をQEMUで使えないだけで削除しません。数値閾値と保存参照は[事前登録](../../experiments/2026-11-15-storage-options-prereg.md)を保持し、全数測定・実機・製品化は未完了です。
