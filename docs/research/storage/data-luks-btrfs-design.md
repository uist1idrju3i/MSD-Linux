# /data の設計: LUKS + btrfs(dup data/metadata) + xxhash64 + zstd 透過圧縮

- 種類: 設計調査（一次資料照合 + 方針案）
- 作成日: 2026-11-15
- 利用者の方針（2026-11-15）: 「dataはLUKS + btrfs (metadataもdataもdup)にします。xxhash64にします。」「/dataのbtrfsはzstd透過圧縮も行いたいですね。」
- 関連: [filesystem-options-btrfs](filesystem-options-btrfs.md)、[filesystem-options-btrfs-progs](filesystem-options-btrfs-progs.md)、[filesystem-options-luks](filesystem-options-luks.md)、[filesystem-options-dm-integrity](filesystem-options-dm-integrity.md)、[filesystem-candidates](filesystem-candidates.md)

## 1. 目指す構成

```
p7 data パーティション
└── LUKS2（dm-crypt）
    └── btrfs
        ├── checksum: xxhash64（mkfs --csum xxhash）
        ├── data profile: dup（-d dup → 実質 RAID1C2 相当で単一デバイス上2重化）
        ├── metadata profile: dup（-m dup）
        └── mount: compress=zstd[:level]（透過圧縮）
```

## 2. 一次資料で確定した事実

### 2.1 固定版と kernel config

| 部品 | 版/状態 |
|---|---|
| cryptsetup | 2.8.7（target）、dev image 2.7.5 |
| btrfs-progs | 6.10 |
| kernel `CONFIG_BTRFS_FS` | **未設定** → =y 化が必要 |
| `CONFIG_XXHASH` | =y（btrfs xxhash csum に必要、既に済） |
| `CONFIG_CRYPTO_ZSTD` | =m → btrfs zstd 圧縮に =y が必要 |
| `CONFIG_DM_CRYPT` | =m → 起動時に unlock するなら =y 化が必要（initramfs なし想定なら =y） |

### 2.2 btrfs の option（一次資料: mkfs.btrfs 6.10 man + kernel btrfs doc + 既存 filesystem-options-btrfs.md）

mkfs 時の本設計に関係する option（全 option は既存 docs に網羅済み、ここでは採否対象を列挙）:

| option | 本設計での扱い |
|---|---|
| `--csum xxhash` | **採用**（xxhash64 指定の正式名。alias は `xxhash64`。crc32c/sha256/blake2b も可だが方針は xxhash64） |
| `-d dup`（data profile） | **採用**（単一デバイスで data 2重化。default は single） |
| `-m dup`（metadata profile） | **採用**（small device の default も dup だが明示） |
| `-O` features | default のまま（`no-holes`, `extref`, `skinny-metadata` 等は既定含む。`block-group-tree`, `raid-stripe-tree`, `raid1c34`, `zoned`, `quota` 等は不採用候補） |
| `--nodesize/-n` | 既定 16K（測定対象: 4K/16K/32K/64K） |
| `--sectorsize/-s` | 既定 4K（デバイス logical block と合わせる。測定対象） |
| `--features`/`--data`/`--metadata`/`--mixed` | mixed は不採用（dup と併用非対称） |
| `-L <label>` | 採用（`msd-data` など） |
| `--uuid` | 固定 UUID を release ごとに変えるか要検討 |
| `-K/--nodiscard` | discard 関連: SD カードでは `nodiscard` 既定扱いに近い |
| `--shrink` | 初期 image の最小化（genimage で展開する場合に関係） |

mount option（採否対象）:

| option | 本設計での扱い |
|---|---|
| `compress=zstd[:level]`（1-15） | **採用**。level は測定対象（default は 3） |
| `compress-force` | 不採用候補（無圧縮効果ファイルまで強制するかは利用者判断） |
| `autodefrag` | 測定対象（idle 書き込み規則との兼ね合いで不採用になり得る） |
| `commit=<sec>` | 測定対象（既定 30s → write-policy の idle 書き込みに関係） |
| `discard={sync,async}` / `nodiscard` | 測定対象。SD での discard 有無と wear |
| `noatime`/`relatime` | `noatime` 推奨（read での write 発生を避ける。write-policy 整合） |
| `flushoncommit`/`noflushoncommit` | 測定対象 |
| `ssd`/`nossd` | btrfs の SSD 検出を SD に当てはめるか測定（`ssd` 明示で write 挙動差） |
| `space_cache=v2`/`nospace_cache` | 既定 v2。free space tree の書き込み差を測定 |
| `rescue`/`ro` 系 | 復旧用、常時 mount ではない |
| `subvol`/`subvolid` | layout 設計に関係。測定対象外（機能差） |
| `thread_pool=<n>` | 測定対象 |
| `max_inline` | inline data 上限。compress 併用で変わる。測定対象 |

btrfs idle 書き込み規則（write-policy §10 との整合）: `commit` interval 30s で dirty data があるときだけ flush。idle 時に書き込みを発生させる主な要因は `space_cache=v2` の更新と `autodefrag`。`ssd` mount option は flush 挙動を変える。これらを fs-compare の phase（T4-sync, T5）で既測定手法に乗せて測る。

### 2.3 LUKS2 の option（一次資料: cryptsetup 2.8.7 man + 既存 filesystem-options-luks.md）

`cryptsetup luksFormat` 系:

| option | 本設計での扱い |
|---|---|
| `--type luks2` | 採用 |
| `--cipher aes-xts-plain64` | 既定・採用候補。`xchacha12,aes-adiantum-plain64` / `xchacha20,aes-adiantum-plain64`（AES-NI なし ARM 向け）も測定対象 |
| `--key-size` | cipher に応じ 256/512 bit。測定対象 |
| `--hash sha256`（PBKDF） | 既定。測定対象外だが `--pbkdf` argon2i/argon2id/pbkdf2 の比較対象 |
| `--pbkdf argon2id` | 既定・採用候補。`--pbkdf-memory/--pbkdf-parallel/--iter-time` はメモリ制約で測定 |
| `--sector-size 512/4096` | 測定対象（DM integrity 込みで 4096 推奨か） |
| `--integrity <alg>` | LUKS2 integrity（hmac-sha256 等）。**方針は btrfs csum で integrity 担保なので LUKS 側は無し前提**だが、dup+xhash64 と integrity の併用比較は測定対象（I1/I2 経験あり） |
| `--key-slot`/`--keyfile` | 鍵 lifecycle 設計に関係（§4） |
| `--luks2-metadata-size`/`--keyslots-size` | 既定。key rotation 回数見積もりに関係 |
| `--sector-size`/`--offset`/`--align-payload` | payload 整列。256MB 中の整合 |
| `--use-random`/`--use-urandom` | format 時の source。既定 random |
| `--perf-*` | same_cpu_crypt/submit_from_crypt_cpus 等。測定対象 |
| `resilver`/`refresh`（repair 系） | 運用ツール。測定対象外 |

### 2.4 LUKS ↔ btrfs の重なり（設計上の重複検査）

- **完全性**: btrfs xxhash64 は data+metadata の内容 checksum。LUKS integrity（hmac-sha256）はブロック単位の完全性。両方入れると overhead 大。方針どおり btrfs 側に寄せる場合、LUKS integrity は掛けない（replay/rollback 耐性は LUKS の AEAD でも完全ではないため、別途設計が必要なら manifest 側で）。
- **dup vs LUKS**: dup の 2 箇所書き込みは LUKS 経由で 2 回暗号化される。sector 単位では別 offset → 別 IV で問題なし。

## 3. 設計案

### 3.1 mkfs 構成

```
cryptsetup luksFormat --type luks2 --cipher aes-xts-plain64 --key-size 512 \
  --pbkdf argon2id --sector-size 4096 /dev/mmcblk0p7
cryptsetup open /dev/mmcblk0p7 msd-data
mkfs.btrfs -L msd-data --csum xxhash -m dup -d dup -n 16384 -s 4096 /dev/mapper/msd-data
mount -o noatime,compress=zstd:3,ssd /dev/mapper/msd-data /data
```

初回起動時の暗号化は product-decisions 2026-11-03「/dataは初回起動から暗号化する方向」に一致。device 固有 volume key を初回起動で生成、keyfile は key-slot に。progress 表示必須（§10）。

### 3.2 zstd 透過圧縮

`compress=zstd:3` 採用案。`compress-force` は incompressible 判定を潰すため不採用方向。level は圧縮率/CPU 測定で 1/3/9 比較。`max_inline`（既定 2048）は小 file の inline 圧縮に関係、level との掛け合わせで測る。

### 3.3 subvolume layout（案）

- `/data` 直下: `@data`（既定 subvol を分けておくと snapshot/rollback 可）
- `log` 系は RAM（write-policy どおり `/data` には書かない）

### 3.4 鍵 lifecycle

- volume key: 初回起動に `/dev/urandom` から生成、LUKS keyslot0 に keyfile として登録。
- PIN/password 変更時は `cryptsetup luksChangeKey` で key rotation（product-decisions 2026-11-03 の記述に整合）。
- keyfile の保管: boot partition(FAT) に置くか verity 領域内に置くか → A/B 設計と整合させる必要あり（rootfs は ro+verity なので writable な場所は boot/data のみ）。

## 4. 測定計画（experiment-record 準拠）

/data 系の測定対象:

1. **btrfs mkfs**: `-m dup -d dup` 固定で `csum {crc32c, xxhash, sha256, blake2b}`、`nodesize {4K,16K,32K}`、`sectorsize {4K}` の差。
2. **btrfs mount**: `compress=zstd:{1,3,9}`、`compress-force` 有無、`commit={30,5,0}`、`ssd/nossd`、`autodefrag` 有無、`space_cache` v2/none、`thread_pool`、`flushoncommit`。
3. **LUKS**: cipher {aes-xts-plain64, xchacha12-adiantum, xchacha20-adiantum}、`sector-size {512,4096}`、`--perf` 系、`--integrity` 有無比較。
4. **fs-compare 連携**: 新設定を `B*`（plain btrfs）、`L*`（LUKS+btrfs 新規系統）として fs-compare-configs に追加し、T4-sync/T5/write inventory を既存手法で測る（E3/E4 matrix 完了後に同じ harness で）。
5. **写り性能**: 200MB data file 書き込み・ランダム 4K rw・fsync 頻度差。
6. **電源断・破損試験**: dup+xxhash の復旧動作、scrub、btrfs check。電源断反復（既存 harness）。

## 5. 未解決・利用者確認点

1. **dup data の容量倍率**: data が 2 倍消費される。`/data` の想定使用量と容量見積もりが要。利用者確認点。
2. **LUKS integrity 無しの確定**: btrfs xxhash64 で破損検出する方針。悪意ある改ざんは keyslot があっても平文攻撃には非耐性（どちらも暗号学的でない）。要確認。
3. **compress-force**: 方針は「zstd 透過圧縮」、force まで含むか。
4. **keyfile の保管場所**: boot FAT（SD 抜き取りで key が漏れる）vs TPM 相当機能なし → 端末内 keyfile 前提か、起動時に user PIN を要求するか。利用者判断。
5. **subvolume layout**: snapshot/rollback を使うか。
6. **sector-size**: SD の erase block との整列。実機測定課題。
