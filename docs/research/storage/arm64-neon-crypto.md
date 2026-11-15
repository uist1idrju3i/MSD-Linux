# ARM64 NEON・crypto extension と hash 選択の調査（CardputerZero / Cortex-A53）

[調査の索引へ戻る](./README.md)

2026-11-15。dm-verity の hash 選択（crc32c か sha256 か）と、LUKS cipher・btrfs checksum の実装選択の根拠として、この機種の SoC で NEON（ASIMD）と ARMv8 crypto extension がどこまで効くかを kernel 6.18.59 の code と QEMU の guest 起動 log で確かめた記録です。

## QEMUの検出と実機未確認の区分

| 拡張 | QEMU側の検出 | source上の候補（実機では未確認） |
|---|---|---|
| NEON（`asimd`） | あり | 使える（Cortex-A53 標準） |
| CRC32 命令（`crc32`） | **あり** | `crc32c` の HW 加速に使える |
| SHA-1/SHA-2 命令（`sha1`, `sha2`） | **なし** | sha256 の HW 命令パスは使えない |
| AES 命令（`aes`） | **なし** | AES の HW パスは使えない |
| PMULL（`pmull`） | **なし** | crc32 の 4way 経路と ghash の HW パスは使えない |

命令拡張の公開情報・guestの検出・実機性能を分けます。NEONとSHA2専用命令は別です。QEMUのcapとsource上の分岐から実機の速度差は求められず、crc32cが「桁違いに速い」という旧説明を撤回します。

### 検出の根拠（QEMU guest、2026-11-15）

開発用 QEMU（raspi3ap、カーネル 6.18.59）の serial boot log で `CPU features: detected:` の行を確認した:

- 検出あり: `ARM erratum 845719`、`32-bit EL0 Support`、`32-bit EL1 Support`、`CRC32 instructions`、`PMUv3`
- 検出なし: `SHA-1/SHA-256 instructions`、`AES instructions`、`PMULL instructions`（存在すれば kernel は同じ形式で検出を出力する）

旧調査はBCM2710A1の公開cpuinfoとの一致も述べましたが、追跡可能な直接出典を本記録へ保存できていません。実機のcpuinfo・HWCAP・選択された実装は未確認です。SoC名やCortex-A53という名前だけでoptional crypto拡張の有無を確定しません。

## kernel 6.18 の実装経路

6.18 では arm64 向けの最適化実装が `arch/arm64/crypto/` から `lib/crypto/<arch>/` と `lib/crc/<arch>/` に再配置されている。dm-verity が使う shash は、最終的にこれらの lib 実装へ落ちる。

### crc32c

- `crypto/crc32c.c` の shash `crc32c-lib` → lib `crc32c()` → `lib/crc/arm64/crc32.h` の arch 分岐。
- `ARM64_HAS_CRC32` cap があると `crc32c_le_arm64`（`crc32cd` 命令の逐次版）を使う。guest で `CRC32 instructions` 検出済みなのでこの経路が動く。
- 1024 byte以上・PMULL cap・`may_use_simd()` が揃うと4way候補になります。それ以外はCRC32命令の逐次版、CRC32 capがなければbase版です。「1 byte/cycle」「十分に速い」という未測定の説明を撤回します。
- config: `CRYPTO_CRC32C=y`（現行 defconfig で有効、lib の arm64 実装は arch hook 経由で自動選択）。

### sha256

- `lib/crypto/arm64/sha256.h` は 3 段分岐: `have_ce`（SHA2 cap）→ `__sha256_ce_transform`（HW 命令）、`have_neon`（ASIMD cap）→ `sha256_block_neon`（NEON）、どちらも無ければ `sha256_block_data_order`（scalar）。
- ASIMDだけで常にNEON版にはなりません。`CONFIG_KERNEL_MODE_NEON`、初期化時のASIMD検出による `have_neon`、呼出し時の `may_use_simd()` がgateです。その内側でSHA2由来の `have_ce` があればCE版、なければ `sha256_block_neon`。gate不成立ではscalarです。旧「2〜3倍」「100〜200 MB/s」は直接出典・実測がないため撤回し、実機で測ります。
- `CONFIG_KERNEL_MODE_NEON=y` が必須（現行 defconfig で有効）。
- 余談として `sha256_finup_2x`（CE なら 2 stream 並列）も CE cap 必須なのでこの機種では無関係。

### AES / LUKS cipher への影響

- AES 命令が無いので `aes-ce-*`（CE 版）は全部使えない。kernel の AES は `aes-neon-blk`（ASIMD の bit-slice）か scalar が上限になる。
- adiantumとAESの優劣を本記録では決めません。旧imageのmodule設定と実際のload成功は別で、全cipher/hashを実機計画で比較します。当面のcipherは利用者指定どおりaes-xts-plain64です。
- いずれにせよ cipher 実測は B4（`cryptsetup benchmark` in guest、`CRYPTO_USER_API_*=m` で AF_ALG 経由）で確かめる。QEMU TCG は cycle 精度が無いので、実機 ratio の推定には使わない。

## userspace（OpenSSL / cryptsetup / zstd）

- OpenSSLのbuild・HWCAP dispatchはkernelと別で、対象実機で選ばれる経路は未確認です。
- cryptsetupは用途・build backendによって処理が異なります。PBKDF、userspace crypto、dm-crypt/AF_ALGを区別し、kernelの関数速度がそのまま全処理の速度になるとはしません。
- zstdを含むconsumer全体の性能をNEON capだけから推定しません。

## dm-verity の hash 選択への含意

| 観点 | crc32c | sha256 |
|---|---|---|
| source上の加速候補 | CRC32/PMULLと実行文脈で分岐 | scalar/NEON/CEをcapと実行文脈で分岐 |
| 改ざん耐性 | なし（誤り検出のみ。root_hash 真正性は起動 chain 側で担保する必要） | あり（暗号学的 hash） |
| formatter | `veritysetup` が userspace 側で crc32c を拒否 → 自前の `verityfmt`（`board/cardputerzero/tools/dm-verity/`、sha256 版と byte 互換を検証済み） | `veritysetup` のまま使える |
| digest 長 | 4 byte（hash tree が小さい） | 32 byte |

利用者のroot hash=crc32cという判断を維持します。偶発破損検出用であり暗号学的な改ざん耐性とは区別します。sha256比較はその判断の実機検証で、採否を勝手に未決定へ戻しません。formatterの機能・RS移植元のlicense監査・製品A/B復帰は別の未完了項目です。[監査と訂正](storage-integrity-corrections.md)を参照してください。

## QEMU と実機の差

- QEMU raspi3apで観測したcapを実機全体へ一般化しません。命令実装があることと、実際のdm-verity呼出しでその経路を通ったことも別です。
- ただし TCG 実行は実機の cycle 数を再現しない。特に NEON 版の「実機での速さ」は QEMU の時間からは読み取れない。比率の推定は実機測定待ち。

## 参照

固定source: Raspberry Pi Linux 6.18.59、commit `b3495ea401d709af0701a85babcba5e3d788a602` の [sha256.h](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/lib/crypto/arm64/sha256.h) と [crc32.h](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/lib/crc/arm64/crc32.h)。上記gateはsource照合、過去guestの検出は保存logの観測です。実機dispatch traceとthroughputは未実施です。

- kernel 6.18.59 source: `lib/crypto/arm64/sha256.h`（`sha256_blocks` の have_neon/have_ce 分岐）、`lib/crypto/arm64/sha256-core.S`（`sha256_block_data_order` / `sha256_block_armv8` / `sha256_block_neon`）、`lib/crypto/arm64/sha256-ce.S`、`lib/crc/arm64/crc32.h`（`ARM64_HAS_CRC32` cap と PMULL 4way 分岐）、`crypto/crc32c.c`（`crc32c-lib`）、`drivers/md/dm-verity-fec.c`（FEC 経路の hash 呼び出し）
- guest 検出: 開発用 QEMU の serial log の `CPU features: detected:` 行（`CRC32 instructions` あり、`SHA-*/AES/PMULL` なし）
- kernel config: 現行 `.config` で `CONFIG_KERNEL_MODE_NEON=y`、`CONFIG_CRYPTO_CRC32C=y`、`CONFIG_CRYPTO_SHA256=y`、`CONFIG_CRYPTO_LIB_SHA256_ARCH=y`、`CONFIG_CRYPTO_ADIANTUM=m`、`CONFIG_CRYPTO_NHPOLY1305_NEON=m`、`CONFIG_CRYPTO_USER_API_HASH=m`、`CONFIG_CRYPTO_USER_API_SKCIPHER=m`
- 関連調査: [rootfs 完全性設計](rootfs-squashfs-verity-fec-design.md)、[data LUKS+btrfs 設計](data-luks-btrfs-design.md)、[zstd 使用箇所](zstd-usage-and-options.md)
