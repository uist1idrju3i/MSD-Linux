# rootfs の完全性設計: SquashFS + zstd + dm-verity(crc32c) + FEC + A/B 切り戻し

- 種類: 設計調査（一次資料照合 + 方針案）
- 作成日: 2026-11-15
- 利用者の方針（2026-11-15）: 「rootはSquashFS + zstd + dm-verity(crc32c)+ FECにします。破損検出時はA/Bブートの仕組みを使って切り戻せるようにしてください。」
- 関連: [ab-design-history](ab-design-history.md)、[recovery-and-watchdog](recovery-and-watchdog.md)、[filesystem-options](filesystem-options.md)、[filesystem-candidates](filesystem-candidates.md)

## 1. 目指す構成

```
p5/p6 rootfs パーティション (256MB 固定)
├── squashfs image（zstd 圧縮）
├── dm-verity hash tree（crc32c, hash-offset で squashfs 末尾に接続）
└── FEC 領域（RS(255,N) parity）
起動: dm-mod.create or veritysetup open → /dev/dm-* を / に mount
破損検出: FEC で訂正 → 訂正不能なら error mode で切り戻し（A/B）
```

## 2. 一次資料で確定した事実

### 2.1 固定版

| 部品 | 版 | 出所 |
|---|---|---|
| squashfs-tools | 4.7.5 | `vendor/buildroot/package/squashfs/squashfs.mk` |
| zstd | 1.5.7 | `vendor/buildroot/package/zstd/zstd.mk` |
| cryptsetup | 2.8.7 | `vendor/buildroot/package/cryptsetup/cryptsetup.mk`（dev image は 2.7.5） |
| kernel | 6.18.59-v8（rpi `b3495ea`） | `board/cardputerzero/linux.fragment` の base |

### 2.2 kernel config の現状と必要差分

実測 `.config`（rpi-6.18.59 + `linux.fragment`、`output-zram-m` で確認）:

| symbol | 現状 | 必要 | 理由 |
|---|---|---|---|
| `CONFIG_DM_VERITY` | =m | =y | boot 時に module なしで dm target を作るため（dm-mod.create 前提）。initramfs を使う設計なら =m 維持でも可 |
| `CONFIG_DM_VERITY_FEC` | 未設定 | =y | FEC（forward error correction）対応 |
| `CONFIG_DM_VERITY_VERIFY_ROOTHASH_SIG` | 未設定 | 任意 | root hash の署名検証を kernel keyring で行う場合のみ |
| `CONFIG_CRYPTO_CRC32C` | =m | =y | verity の hash=crc32c を boot 時に使うため |
| `CONFIG_BLK_DEV_DM` / `DM_INIT` | =m / 未設定 | =y | `dm-mod.create=` kernel 引数での直接起動に必要 |
| `CONFIG_REED_SOLOMON` | =y（enc8/dec8） | 維持 | FEC の RS 符号化 |
| `CONFIG_SQUASHFS` / `SQUASHFS_ZSTD` | =y | 維持 | 現行どおり |

### 2.3 mksquashfs 4.7.5 の全 option（一次資料: `mksquashfs -help-all`）

圧縮関連: `-b <4K..1M>`（既定 128K）、`-comp {gzip,lzo,lz4,xz,zstd,lzma}`、`-noI/-noId/-noD/-noF/-noX/-no-compression`、zstd 固有 `-Xcompression-level <1..22>`（既定 15、`EXTREME_COMP` は 22）。

構築関連: `-tar/-no-strip/-cpiostyle{,0}`、`-reproducible`（既定）/`-not-reproducible`、`-mkfs-time/-all-time/-root-time`、`-root-mode/-root-uid/-root-gid`、`-all-root/-force-uid/-force-gid/-pseudo-override`、`-exports/-no-exports`、`-no-sparse`、`-tailends/-no-tailends`（既定 off）、`-no-fragments`、`-no-duplicates`、`-no-hardlinks`、`-keep-as-directory`。

フィルタ・その他: `-p/-pf`（pseudo file）、`-e/-ef/-wildcards/-regex`、`-sort/-sortlist`（boot 時 read 順序最適化に関係）、`-processors`、`-mem`、`-quiet/-progress/-no-progress`、`-xattrs` 系。

測定対象に分類したものは §5。

### 2.4 dm-verity の option（一次資料: kernel `Documentation/admin-guide/device-mapper/verity.rst` @ b3495ea + cryptsetup 2.8.7 man）

dm table 引数（`dm-mod.create` / `dmsetup` / `veritysetup open` の裏側）:

| 引数 | 意味 |
|---|---|
| `<dev> <hash_dev>` | データと hash tree のデバイス（同じでも可、offset で分離） |
| `<data_block_size> <hash_block_size>` | 両方 512 の倍数、4K が一般的。測定対象 |
| `<num_data_blocks> <hash_start_block>` | tree 配置。hash-offset = data bytes で連結可 |
| `<hash_algorithm>` | sha256 / sha1 / sha512 / ripemd160（cryptsetup）＋ kernel crypto API が持つもの。**crc32c は kernel 側で使えるが veritysetup は拒否**（§3） |
| `<root_digest> <salt>` | root hash と salt（- は salt なし） |
| opt params | `ignore_corruption` / `restart_on_corruption` / `panic_on_corruption` / `restart_on_error` / `panic_on_error` / `ignore_zero_blocks` / `use_fec_from_device <dev>` + `fec_roots <2..24>` + `fec_blocks <n>` + `fec_start <s>` / `check_at_most_once` / `root_hash_sig_key_desc` / `try_verify_in_tasklet` |

veritysetup 側の format/open option: `--hash`、`--no-superblock`、`--format 0|1`、`--data-block-size`、`--hash-block-size`、`--data-blocks`、`--hash-offset`、`--salt`、`--uuid`、`--root-hash-file`、`--fec-device`、`--fec-offset`、`--fec-roots`、`--error-as-corruption`、`--ignore-zero-blocks`、`--check-at-most-once`、`--root-hash-signature`、`--use-tasklets`、`--shared`、`--deferred`。

## 3. 主要な制約: veritysetup は crc32c を拒否する

`veritysetup format --hash=crc32c` → `Hash algorithm crc32c not supported`（2.7.5 で実測）。crc32/crc32c/xxhash64/wp512 も同様に拒否。cryptsetup の crypto backend（openssl 等）が持つ crypto hash（sha1/sha256/sha512/ripemd160）しか通らない。

一方 kernel の `/proc/crypto` には `crc32c` があり、dm-verity は kernel crypto API の名前をそのまま受け付ける。つまり:

- **hash tree の生成**: veritysetup が使えない → 自前 formatter（hash tree を crc32c で計算し superblock/no-superblock で書く小ツール）または cryptsetup patch が必要。hash tree の構造はシンプル（各 level で block ごとに hash を畳み込む）なので自前実装は現実的。FEC parity は `veritysetup format` の RS 生成ロジックを参考に自前で、または fec のみ別 device で veritysetup（sha256 で format して FEC 部分だけ流用）は hash 不一致で使えないので不可 → FEC 生成も自前。kernel の `reed_solomon` API は存在するが userspace からは使えないため、parity 生成は userspace で RS(255,N) を実装するか libfec/isa-l 系のライブラリを使う。
- **起動時の open**: `veritysetup open` は root hash の検証のみで tree を再計算しないので、table を直接 `dm-mod.create`/`dmsetup` に渡せば `--hash=crc32c` を kernel に指定できる。veritysetup open に `--hash=crc32c` を渡すと userspace 側で拒否されるため、`dm-mod.create` 経由が前提。

**設計上の帰結**: crc32c 採用 = 「format は自前ツール」が必須条件。crc32c は暗号学的でないため改ざん耐性はない（誤り検出のみ）。SD カードのビット化け検出が目的なら成立するが、悪意ある改ざんへの耐性は sha256 に譲る。ここは利用者判断（方針は crc32c と明記）。

## 4. 設計案

### 4.1 パーティション・レイアウト

現行 p5/p6 は 256MB 固定、squashfs image がそのまま入る（`genimage.cfg`）。hash tree と FEC の置き場:

- **案 A（同一パーティション内連結）**: squashfs 末尾に hash tree → FEC を続けて書き、verity の hash_dev=fec_dev=同一パーティション。`--hash-offset`/`fec_start` で指定。メリット: パーティション表不変。256MB 内に収まるかが条件（hash tree は sha256 4K block で約 1/4096×log、128MB data なら数 MB。crc32c は 4B/hash でさらに小さい。FEC は fec_roots に比例）。
- **案 B（別パーティション）**: p8 などに verity 領域。genimage 変更が必要。管理は楽。
- **推奨**: 案 A を既定案とし、256MB 制約内で fec_roots を決める。

### 4.2 error mode → A/B 切り戻し

現行 A/B は tryboot + msd-update で update 失敗時に戻す設計（[ab-design-history](ab-design-history.md)、[recovery-and-watchdog](recovery-and-watchdog.md)）。verity の破損検出を「このスロットは壊れている」として A/B に接続する案:

- **FEC が有効な間**: 読み出し時に訂正して継続（dm-verity が自動）。訂正が発生したことの観測は status 取得のみ。
- **訂正不能な破損**: `panic_on_corruption` は即 panic → 再起動。watchdog/boot counter 機構（既設計）が tryboot で別スロットへ。ただし panic は再起動理由を残しにくい。
- **restart_on_corruption**: kernel reboot。boot counter が進んで tryboot 切り戻し。
- **ignore_corruption** は方針外（検出して無視はしない）。
- **error_as_corruption**: I/O error も破損扱いにして FEC 経路へ流す。SD 読み出し error を破損とみなすかは要検討。
- **check_at_most_once**: 2 回目以降の読み出しを検査しない → 起動後の再検査を省く用途。セキュリティ低下、不採用候補。

**推奨**: `use_fec_from_device + fec_roots N` + `restart_on_corruption`（panic ではなく再起動で tryboot に委ねる）。panic_on_corruption との差を QEMU 実測で比較する。起動直後でなければ boot counter は既に良い起動として確定している可能性があるので、verity 破損検出時に「スロット不良」をどこへ永続化するかが未解決点（write-policy に合わせて bootsel フラグで扱う案）。

### 4.3 起動経路

- `dm-mod.create=verity,,,ro,0 <blockdev> <blockdev> 4096 4096 <datablocks> <hashstart> crc32c <roothash> <salt> <optparams>` を kernel 引数 or config.txt/cmdline.txt に。`dm-mod.waitfor` で mount 待ち。
- root hash / salt は release 時に確定 → boot-a/b の autoboot.txt か cmdline に埋める。msd-update が update 時に相手スロットの verity パラメータを書き込む設計に合わせる。

## 5. 測定計画（experiment-record 準拠の対象）

rootfs 系:

1. **SquashFS**: `-comp zstd -b {4K,8K,16K,32K,64K,128K,256K,512K,1M}` × `-Xcompression-level {1,3,9,15,19,22}` の圧縮率・build 時間・QEMU mount/boot 時間・ランダム read 時間。`-tailends`, `-no-fragments`, `-exports` 有無の差。比較に `-comp xz/lz4/gzip` 少量。
2. **zstd**: level vs 圧縮率・展開速度（SquashFS 側で測）。kernel decompressor の上限レベル確認（= 22 が使えるかの検証を兼ねる）。
3. **dm-verity**: hash {sha256, crc32c（自前 formatter）}、data/hash block {4K}、error mode {restart_on_corruption, panic_on_corruption}、FEC {なし, fec_roots 2/8/16}、破損注入（1 block ビット化け / 連続領域化け / hash tree 自身の化け）での検出・訂正・切り戻し。`error_as_corruption` の挙動差。
4. **起動時間影響**: verity あり/なし、FEC あり/なしでの T0〜T5（icount 既存手法）。

/data 系は `data-luks-btrfs-design.md`、zstd 系は `zstd-options-survey.md` に分割。

## 6. 未解決・利用者確認点

1. **crc32c の自前 formatter を作るか**: 現行ツールチェーンで唯一のギャップ。tree+FEC 生成を自前で持つ見積もりは小さくない。sha256 に逃げる選択肢は利用者の方針と異なるので前提で持たない。
2. **FEC の収容**: 256MB partition 内に squashfs+tree+FEC が入るか。rootfs 実 size 次第。
3. **error mode の確定**: restart vs panic、boot counter 連携。QEMU 実測後に案を提示。
4. **verity 破損時の永続化ポイント**: bootsel への flag 書き込みは write-policy 台帳に追加が必要。
5. **update 時の再署名**: msd-update が新 image ごとに root hash をどう配布するか（image 埋め込み / 署名付き manifest）。R36（信頼起点）と接続。
