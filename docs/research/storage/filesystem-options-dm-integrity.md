# dm-integrityとintegritysetup

[保存領域へ戻る](README.md) / [option調査の索引](filesystem-options.md) / [LUKS2とdm-crypt](filesystem-options-luks.md) / [調査の索引](../../../RESEARCH.md)

## 範囲と出典

固定版はcryptsetup 2.8.7、最新版は2.8.8です。kernelは6.18.59とmainline 7.4-rc1を参照します。一次資料は[cryptsetup v2.8.7 `integritysetup(8)`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.7/man/integritysetup.8.adoc)、[v2.8.8 `integritysetup(8)`](https://gitlab.com/cryptsetup/cryptsetup/-/blob/v2.8.8/man/integritysetup.8.adoc)、[kernel dm-integrity documentation at the pinned commit](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/device-mapper/dm-integrity.rst)、[cryptsetup v2.8.8 release tag](https://gitlab.com/cryptsetup/cryptsetup/-/tags/v2.8.8)、[mainline kernel v7.4-rc1](https://github.com/torvalds/linux/blob/v7.4-rc1/Documentation/admin-guide/device-mapper/dm-integrity.rst)です。

dm-integrityはsectorごとのintegrity tagをblock deviceに付けます。standaloneではchecksum、hash、HMACを計算し、dm-cryptと組み合わせるとencrypted dataのauthenticated integrityに利用できます。filesystemより下のblock layerで働くため各filesystemで使えますが、MSD/Linuxではcryptsetupもdm-integrityも有効化済みと確認していません。

## idle writeとprogressの製品条件

journal/bitmap/direct modeごとにtag metadataのwrite時刻とbyte数をtraceし、journal flushやbitmap updateがidle中にも発生するか確認する。user operationの完了後にtimerでflushする動作を許容せず、journal/bitmap modeはno-unprompted-write条件に合う場合だけ候補にする。format、recalculate、repair、長時間checkには利用者が開始するprogress表示を必須にし、background timerから起動しない。

## `integritysetup format`、`open`と共通option

最新版との差分列は、option tokenの追加・削除を固定版と比較する。`同`はoption token差分なしを示し、defaultの全文比較は未確認。

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `--integrity` | internal checksum/hash/HMAC | 無効 | 可 | 同 | 実験で比べる | CRC、xxhash、SHA、HMACの性能と検出範囲を測る。 |
| `--tag-size` | sectorごとのtag byte数 | algorithm依存 | 可 | 同 | 実験で比べる | metadata overheadと検出方式を比較する。 |
| `--sector-size` | integrity block size | 512 byte | 可 | 同 | 実験で比べる | 512/1024/2048/4096 byteを測る。 |
| `--integrity-key-file` | HMAC key file | なし | 可 | 同 | 実験で比べる | HMAC利用時のkey sourceと保護が必要。 |
| `--integrity-key-size` | integrity key size | algorithm依存 | 可 | 同 | 実験で比べる | HMAC algorithm選択後に仕様上のkey lengthとkey provisioning方法を固定する。誤った長さはformat/open失敗になるため性能差では決めない。 |
| `--integrity-bitmap-mode` | journalの代わりにbitmap | 無効 | 可 | 同 | 実験で比べる | write costを減らすがcrash時に未同期tagが残る。 |
| `--integrity-no-journal` | direct write、journalなし | 無効 | 可 | 同 | 実験で比べる | data/tagがatomicでなく、crash時不一致の可能性。 |
| `--integrity-inline` | hardware sector protection fieldへtag保存 | 無効 | 可 | 同 | 除外 | 対応integrity profile付きdeviceがない。 |
| `--integrity-recalculate` | activation時にtag再計算 | 無効 | 可 | 同 | 実験で比べる | 未初期化dataを保つ条件と完了状態を検証する。 |
| `--integrity-recalculate-reset` | recalculate位置をreset | 無効 | 可 | 同 | 除外 | 更新中のtag stateをresetする運用がない。 |
| `--integrity-recovery-mode` | recovery用、tag checkを停止 | 無効 | 可 | 同 | 除外 | 通常mountで検査を無効にしない。 |
| `--allow-discards-keyed` | HMAC付きtagでdiscarded blockを識別 | 無効 | 固定版2.8.7では不可。最新版2.8.8で追加。版上げで使える候補 | 最新版で追加; 版上げで使える候補 | 実験で比べる | fresh volumeが必要。tag偽造への耐性とdiscard性能を測る。 |
| `--integrity-legacy-padding` | 旧tag area padding | 無効 | 可 | 同 | 除外 | 旧kernel互換専用。 |
| `--integrity-legacy-hmac` | legacy HMAC処理 | 無効 | 可 | 同 | 除外 | 旧kernel互換専用。 |
| `--integrity-legacy-recalculate` | legacy recalculate | 無効 | 可 | 同 | 除外 | key付きvolumeの危険な旧動作を許可しない。 |
| `--no-wipe` | `integritysetup format`後のdata-device wipeを省略 | wipe有効 | 可 | 同 | 除外 | 既存dataを保持する用途以外では使わず、tagを初期化するrecalculate完了前のmountを避ける。 |
| `--integrity-no-wipe` | LUKS2 format時wipeを省略 | wipe有効 | 可 | 同 | 除外 | 未初期化領域のtagを有効と誤認しない。 |
| `--journal-size` | journal byte数 | tool計算 | 可 | 同 | 実験で比べる | 容量・write amplificationを測る。 |
| `--journal-watermark` | journal flush watermark | 50% | 可 | 同 | 実験で比べる | flush頻度とthroughputを測る。 |
| `--journal-commit-time` | journal commit間隔 | 10秒 | 可 | 同 | 実験で比べる | latencyと電断時のdirty領域を測る。 |
| `--journal-crypt` | journal data encryption | 無効 | 可 | 同 | 除外 | kernel docsはjournal metadata confidentiality用途とし、data encryptionの代わりではない。 |
| `--journal-integrity` | journal tag algorithm | 無効 | 可 | 同 | 実験で比べる | journal MACのCPU・space costを測る。 |
| `--journal-crypt-key-file` / `--journal-crypt-key-size` | journal encryption key | なし | 可 | 同 | 除外 | journal encryptionを製品要件にしていない。 |
| `--journal-integrity-key-file` / `--journal-integrity-key-size` | journal integrity key | なし | 可 | 同 | 実験で比べる | key management設計と一緒に測る。 |
| `--interleave-sectors` | data/tag interleave幅 | 32768 sectors | 可 | 同 | 既定のまま | 値ごとにmetadata占有量、sequential throughput、random I/O latencyを同一block deviceで比較し、tag layoutの変更が必要な場合にだけ変える。 |
| `--buffer-sectors` | metadata buffer size | 128 sectors | 可 | 同 | 既定のまま | RAM使用量、throughput、p99 write latencyを負荷中に測り、buffer変更が改善する場合だけ調整する。 |
| `--data-device` | metadataとdataを別deviceへ分離 | 同一device | 可 | 同 | 除外 | multi-device layoutがない。 |
| `--allow-discards` | integrity mappingでdiscard許可 | 無効 | 可 | 同 | 実験で比べる | discarded tagの偽造riskとSD性能を比較する。 |
| `--bitmap-flush-time` | dirty bitmap flush間隔 | 10秒 | 可 | 同 | 実験で比べる | crash windowとthroughputを測る。 |
| `--bitmap-sectors-per-bit` | bitmap 1 bit当たりsector数 | 64 | 可 | 同 | 実験で比べる | dirty region粒度とmemory使用量を比較する。 |
| `--progress-frequency` / `--progress-json` | format progress表示 | 1秒 / 無効 | 可 | 同 | 既定のまま | 表示・automation用でFS policyではない。 |
| `--wipe` | resize時に新領域をwipe | 有効 | 可 | 同 | 既定のまま | 新領域を未初期化で露出させない。 |
| `--size` / `--device-size` | active mapping size | device依存 | 可 | 同 | 既定のまま | layout変更は評価対象外。 |
| `--deferred` / `--cancel-deferred` | closeを遅延 / 取消 | 即時close | 可 | 同 | 除外 | runtime close制御専用。 |
| `--debug`、`--verbose`、`--batch-mode` | 診断・対話制御 | quiet/default | 可 | 同 | 既定のまま | integrity policyを変えない。 |

integrity algorithmとしてman pageが記載するのは`crc32c`、`crc32`、`xxhash64`、`sha1`、`sha256`、`hmac-sha256`等です。cryptographic authenticationが必要な場合はkey付きHMACを使います。CRCは偶発的破損の検出用で、攻撃者に対するauthenticationではありません。

## kernel target arguments

| option | 意味 | 既定値 | 固定版で使えるか | 最新版の変化 | MSD/Linuxでの扱い | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| `D` | direct write、journalなし | journaled | 可 | 同 | 実験で比べる | dataとtagの非atomic更新を許す。 |
| `J` | journaled write | journaled | 可 | 同 | 実験で比べる | data/tagのwrite atomicityと約2倍のwrite負荷。 |
| `B` | bitmap mode | journaled | 可 | 同 | 実験で比べる | fasterだがcrash時の破損を見逃す可能性。 |
| `R` | recovery、journal/tag checkなし | 無効 | 可 | 同 | 除外 | recovery専用。 |
| `I` | inline hardware integrity | 無効 | 可 | 同 | 除外 | 下位deviceに適切なintegrity profileが必要。 |
| `journal_sectors` | journal size | format時に計算 | 可 | 同 | 実験で比べる | device容量とwrite throughputを測る。 |
| `interleave_sectors` | data/tagのinterleave幅 | 32768 | 可 | 同 | 既定のまま | metadata占有量、sequential throughput、random I/O latencyを同一block deviceで比較し、改善が確認された場合だけ変更する。 |
| `meta_device` | metadata専用device | なし | 可 | 同 | 除外 | multi-device構成がない。 |
| `buffer_sectors` | metadata bufferのsector数 | 128 | 可 | 同 | 既定のまま | RAM使用量、throughput、p99 write latencyを負荷中に測り、変更による改善が確認された場合だけ調整する。 |
| `journal_watermark` / `commit_time` | journal flush trigger/time | 50% / 10000 ms | 可 | 同 | 実験で比べる | throughputとcrash windowを測る。 |
| `internal_hash` | internal CRC/hash/HMAC | 無効 | 可 | 同 | 実験で比べる | standalone data integrityを比較する。 |
| `recalculate` | internal tagを再計算 | 無効 | 可 | 同 | 実験で比べる | keyなしの再計算可否・期間を測る。 |
| `journal_crypt` / `journal_mac` | journal encryption/MAC | 無効 | 可 | 同 | 実験で比べる | confidentiality/integrityとCPU costを分けて検証する。 |
| `block_size` | data block byte数 | 512 | 可 | 同 | 実験で比べる | 512/1024/2048/4096を比較する。 |
| `sectors_per_bit` / `bitmap_flush_interval` | bitmap粒度/flush間隔 | 既定 | 可 | 同 | 実験で比べる | dirty bitmapのspaceとcrash windowを比較する。 |
| `allow_discards` | discard許可 | 無効 | 可 | 同 | 実験で比べる | unkeyed filler tagをraw accessから偽造できる。 |
| `allow_discards_keyed` | keyed discard tag | 無効 | 可 | 同 | 実験で比べる | HMACでdiscard tagを保護するがfresh volumeが必要。 |
| `fix_padding` / `fix_hmac` | 新padding / journal MAC強化 | 無効 | 可 | 同 | 実験で比べる | compatibilityとsecurityを比較する。 |
| `legacy_recalculate` | key付きvolumeの旧再計算 | 無効 | 可 | 同 | 除外 | 攻撃者がrecalc stateを操作できるriskを避ける。 |

## LUKS2との組合せと破損検出

`cryptsetup luksFormat --integrity <algorithm>`でLUKS2 dm-integrity layerを構成できます。資料はAEAD形式と`hmac-sha256`などのintegrity algorithmを扱います。`--integrity-no-journal`はjournalを使わない性能/atomicity tradeoff、`--integrity-no-wipe`は初期format時のwipe省略を選びます。これらは既定にせず、別々の候補行として上表に記録しました。正確な組合せ可能性はcryptsetup版、kernel target、選択algorithmに依存し、製品環境では未確認です。

dm-integrity standaloneではblock dataとtagの不一致を検出できます。dm-cryptと組み合わせる場合はauthenticated encryptionによりmodified ciphertextをrandom plaintextとして返す代わりにI/O errorにできます。journalはdata/tagのatomicityを高めますがkernel資料ではwrite throughputが約半分になると説明します。bitmap/direct modeはwrite負荷を下げる一方、crash時のtag不整合を検出できない場合があります。dm-integrityは冗長copyを作らないため、検出と修復を区別します。修復元がなければ破損dataを再構成できません。

### 最新版との差分とoption件数

cryptsetup v2.8.7からv2.8.8では、integritysetupに`--allow-discards-keyed`が追加されています。これは固定cryptsetup 2.8.7では利用できず、2.8.8へ版上げした場合の候補です。kernel dm-integrityのpinned commit版とmainline v7.4-rc1のtarget argument名を照合し、default差分は確認していません。固定kernelで利用可能な範囲を最新版の記載で上書きしません。

表の行数はintegritysetupやkernel target optionの総数を示しません。integritysetup source tokenは固定版2.8.7から最新版2.8.8で`--allow-discards-keyed`が追加されています。kernel target argumentは固定版と最新版の完全照合を終えていないため、未確認の項目を利用可能と断定せず、採用前に生成済みkernel configと実機targetを確認します。
