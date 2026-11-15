# ARM64 NEON・crypto extension と hash 選択の調査（CardputerZero / Cortex-A53）

[調査の索引へ戻る](./README.md)

2026-11-15。dm-verity の hash 選択（crc32c か sha256 か）と、LUKS cipher・btrfs checksum の実装選択の根拠として、この機種の SoC で NEON（ASIMD）と ARMv8 crypto extension がどこまで効くかを kernel 6.18.59 の code と QEMU の guest 起動 log で確かめた記録です。

## 対象 hardware の結論（先に）

| 拡張 | cpuinfo/検出 | CardputerZero で使えるか |
|---|---|---|
| NEON（`asimd`） | あり | 使える（Cortex-A53 標準） |
| CRC32 命令（`crc32`） | **あり** | `crc32c` の HW 加速に使える |
| SHA-1/SHA-2 命令（`sha1`, `sha2`） | **なし** | sha256 の HW 命令パスは使えない |
| AES 命令（`aes`） | **なし** | AES の HW パスは使えない |
| PMULL（`pmull`） | **なし** | crc32 の 4way 経路と ghash の HW パスは使えない |

「sha256 は NEON が効く」は**半分だけ正しい**: この CPU には ASIMD（NEON 相当）はあるので kernel の NEON 版 sha256 は動きますが、ARMv8 crypto extension の SHA-256 専用命令（`sha2` feature）は A53 実装に無いため、最速パス（`sha256-ce`）には届きません。逆に crc32c は CRC32 命令があるので HW 加速されます。つまりこの機種では **crc32c のほうが sha256 より桁違いに速い**構成です。

### 検出の根拠（QEMU guest、2026-11-15）

開発用 QEMU（raspi3ap、カーネル 6.18.59）の serial boot log で `CPU features: detected:` の行を確認した:

- 検出あり: `ARM erratum 845719`、`32-bit EL0 Support`、`32-bit EL1 Support`、`CRC32 instructions`、`PMUv3`
- 検出なし: `SHA-1/SHA-256 instructions`、`AES instructions`、`PMULL instructions`（存在すれば kernel は同じ形式で検出を出力する）

BCM2710A1（Raspberry Pi Zero 2 W、Cortex-A53×4）の公開 cpuinfo でも feature フラグは `fp asimd evtstrm crc32 cpuid` で、QEMU の検出結果と一致する。**実機での cpuinfo 直接確認は未実施**（実機依存として残す）。

## kernel 6.18 の実装経路

6.18 では arm64 向けの最適化実装が `arch/arm64/crypto/` から `lib/crypto/<arch>/` と `lib/crc/<arch>/` に再配置されている。dm-verity が使う shash は、最終的にこれらの lib 実装へ落ちる。

### crc32c

- `crypto/crc32c.c` の shash `crc32c-lib` → lib `crc32c()` → `lib/crc/arm64/crc32.h` の arch 分岐。
- `ARM64_HAS_CRC32` cap があると `crc32c_le_arm64`（`crc32cd` 命令の逐次版）を使う。guest で `CRC32 instructions` 検出済みなのでこの経路が動く。
- 1024 byte 以上では `crc32c_le_arm64_4way`（PMULL 使う 4-way interleave）を選ぼうとするが、`PMULL` cap が必要で **A53 には無い** → 常に 1-way 版。それでも 1 byte/cycle 級なので、dm-verity の 4KiB block 検証としては十分に速い。
- config: `CRYPTO_CRC32C=y`（現行 defconfig で有効、lib の arm64 実装は arch hook 経由で自動選択）。

### sha256

- `lib/crypto/arm64/sha256.h` は 3 段分岐: `have_ce`（SHA2 cap）→ `__sha256_ce_transform`（HW 命令）、`have_neon`（ASIMD cap）→ `sha256_block_neon`（NEON）、どちらも無ければ `sha256_block_data_order`（scalar）。
- A53 は ASIMD あり・SHA2 なしなので、**NEON 版（`sha256_block_neon`）が選ばれる**。scalar の 2〜3 倍程度が目安で、100〜200 MB/s 前後（A53 1GHz 級）が文献値。実測は B4 の QEMU 実験で取る。
- `CONFIG_KERNEL_MODE_NEON=y` が必須（現行 defconfig で有効）。
- 余談として `sha256_finup_2x`（CE なら 2 stream 並列）も CE cap 必須なのでこの機種では無関係。

### AES / LUKS cipher への影響

- AES 命令が無いので `aes-ce-*`（CE 版）は全部使えない。kernel の AES は `aes-neon-blk`（ASIMD の bit-slice）か scalar が上限になる。
- A53 級では XChaCha12 + NH の `adiantum` のほうが AES-NEON より速いのが Android/組込みの定石で、`CONFIG_CRYPTO_ADIANTUM=m`・`CONFIG_CRYPTO_NHPOLY1305_NEON=m` は現行 .config にある（ただし `=m` で builtin ではない。/data を LUKS で root 起動に関与させるなら `=y` 化が要検討）。
- いずれにせよ cipher 実測は B4（`cryptsetup benchmark` in guest、`CRYPTO_USER_API_*=m` で AF_ALG 経由）で確かめる。QEMU TCG は cycle 精度が無いので、実機 ratio の推定には使わない。

## userspace（OpenSSL / cryptsetup / zstd）

- OpenSSL の aarch64 sha256 は `ARMV8_SHA256` HWCAP 必須の `sha256_block_armv8` と、NEON 版を持つ。この機種では NEON 版に落ちる（=「userspace でも NEON は効く」は正しい）。
- cryptsetup の暗号・hash は AF_ALG 経由で kernel crypto を使うので、上記 kernel 経路の速度がそのまま出る。
- zstd の圧縮・伸張には aarch64 専用の NEON 経路が無い（portable C が主）。SquashFS/zram/zswap/btrfs の zstd 性能に NEON はほぼ無関係。

## dm-verity の hash 選択への含意

| 観点 | crc32c | sha256 |
|---|---|---|
| HW/NEON 加速 | CRC32 命令あり（最速） | NEON のみ（中速） |
| 改ざん耐性 | なし（誤り検出のみ。root_hash 真正性は起動 chain 側で担保する必要） | あり（暗号学的 hash） |
| formatter | `veritysetup` が userspace 側で crc32c を拒否 → 自前の `verityfmt`（`board/cardputerzero/tools/dm-verity/`、sha256 版と byte 互換を検証済み） | `veritysetup` のまま使える |
| digest 長 | 4 byte（hash tree が小さい） | 32 byte |

現状の評価: crc32c の「難しさ」は formatter 不在が唯一の壁だったが、`verityfmt` ができて試験済みなので、速度面では crc32c が優位なまま。sha256 は改ざん耐性が必要と判断した場合の選択肢として残し、B 系列で両方の boot/verify 時間を測ってから決める。**hash 選択はまだ決定していない**。

## QEMU と実機の差

- QEMU raspi3ap は Cortex-A53 を cap レベルでは忠実に再現している（CRC32 検出・SHA2 未検出は実機の cpuinfo 公開値と一致）。
- ただし TCG 実行は実機の cycle 数を再現しない。特に NEON 版の「実機での速さ」は QEMU の時間からは読み取れない。比率の推定は実機測定待ち。

## 参照

- kernel 6.18.59 source: `lib/crypto/arm64/sha256.h`（`sha256_blocks` の have_neon/have_ce 分岐）、`lib/crypto/arm64/sha256-core.S`（`sha256_block_data_order` / `sha256_block_armv8` / `sha256_block_neon`）、`lib/crypto/arm64/sha256-ce.S`、`lib/crc/arm64/crc32.h`（`ARM64_HAS_CRC32` cap と PMULL 4way 分岐）、`crypto/crc32c.c`（`crc32c-lib`）、`drivers/md/dm-verity-fec.c`（FEC 経路の hash 呼び出し）
- guest 検出: 開発用 QEMU の serial log の `CPU features: detected:` 行（`CRC32 instructions` あり、`SHA-*/AES/PMULL` なし）
- kernel config: 現行 `.config` で `CONFIG_KERNEL_MODE_NEON=y`、`CONFIG_CRYPTO_CRC32C=y`、`CONFIG_CRYPTO_SHA256=y`、`CONFIG_CRYPTO_LIB_SHA256_ARCH=y`、`CONFIG_CRYPTO_ADIANTUM=m`、`CONFIG_CRYPTO_NHPOLY1305_NEON=m`、`CONFIG_CRYPTO_USER_API_HASH=m`、`CONFIG_CRYPTO_USER_API_SKCIPHER=m`
- 関連調査: [rootfs 完全性設計](rootfs-squashfs-verity-fec-design.md)、[data LUKS+btrfs 設計](data-luks-btrfs-design.md)、[zstd 使用箇所](zstd-usage-and-options.md)
