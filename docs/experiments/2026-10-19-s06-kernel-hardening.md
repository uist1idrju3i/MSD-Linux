# S6：カーネル hardening tier A

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin（実装エージェント）
- 関連: [security-hardening.md](../research/security-hardening.md)、base commit `ecc0dead81285f8d5a8f9692b5cd1bd257e1a58f`

## 目的と仮説

kernel の tier-A hardening を有効にし、Buildroot の最終設定、module 署名、Yama、QEMU boot cost、イメージサイズ、kernel-hardening-checker の変化を測る。仮説は、署名強制と Yama の機能を有効にでき、サイズと QEMU 相対 boot cost の変化は実測で評価できることである。

## 採否の基準（結果を見る前に記載）

- 指定した tier-A 設定が最終 `.config` に反映され、fragment check が成功する。
- installed modules がすべて署名され、署名済み `usbnet` は `modprobe` でロードでき、未署名 copy は `insmod` で拒否される。
- 両 QEMU slot が起動し、Yama が初期化されて `ptrace_scope=1` になる。
- base と hardened のサイズ、boot 時間、checker OK/FAIL 数を同じ指標で比較し、劣化を含めて記録する。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `ecc0dead81285f8d5a8f9692b5cd1bd257e1a58f` |
| ホスト | Ubuntu 22.04.5 LTS、Linux 6.8.0-1061-aws、x86_64 |
| QEMU | 6.2.0 |
| Buildroot / GCC / kernel | Buildroot 2026.08（submodule `d6061d653d7fb215c2409c59e4bfad1b9d677215`） / aarch64 GCC 14.3.0 / 6.18.57-v8 |
| checker | kernel-hardening-checker v0.6.17.1、`afc376f2a935994793343cfeb05953583cc30191` |
| module 圧縮 | host kmod 34.2 `+XZ`。target は `CONFIG_MODULE_DECOMPRESS=y`。#28 の main への merge 後の設定。 |
| 出力先と状態 | `BASE_WORKTREE=<base commit の worktree>`、`REPO=<S6 repo root>`、`OUTPUT_DIR=<Buildroot の O= ディレクトリ>`、`LOG_DIR=<ローカルログの共通ルート>`。同じ Buildroot output を再利用し、base build 後に `host-kmod-reconfigure` と `linux-reconfigure` を実行。 |
| 変える条件 | base と hardened の kernel fragment。hardened では tier-A symbols、Yama、module signing を有効化。 |
| 変えない条件 | QEMU model、`QEMU_ICOUNT=shift=0`、ready-marker の抽出方法、Buildroot output、root filesystem と boot test。 |
| 繰り返し | boot time は各変種 3 run。各 run の値と中央値、最小・最大を記録。 |

## 手順

変数は各環境の checkout と Buildroot output に合わせて設定する。ログの共通ルートは `$LOG_DIR` とし、実験後の大きなログは repo 外に置く。

```sh
BASE_WORKTREE="<base commit の worktree>"
REPO="<S6 repo root>"
OUTPUT_DIR="<Buildroot の O= ディレクトリ>"
LOG_DIR="<ローカルログの共通ルート>"
CHECKER="<pinned checker checkout>"

{
  env -u BASH_ENV make -C "$BASE_WORKTREE/vendor/buildroot" \
    BR2_EXTERNAL="$BASE_WORKTREE" O="$OUTPUT_DIR" msd_cardputerzero_defconfig
  env -u BASH_ENV make -C "$OUTPUT_DIR" host-kmod-reconfigure
  env -u BASH_ENV make -C "$OUTPUT_DIR" -j2
} >"$LOG_DIR/s6-experiment/base-build.log" 2>&1

mkdir -p "$LOG_DIR/s6-experiment/base/images"
cp "$OUTPUT_DIR/build/linux-custom/.config" "$LOG_DIR/s6-experiment/base/linux.config"
cp "$OUTPUT_DIR/images/Image" "$OUTPUT_DIR/images/sdcard.img" \
  "$OUTPUT_DIR/images/bcm2710-rpi-3-b.dtb" "$LOG_DIR/s6-experiment/base/images/"

env -u BASH_ENV make -C "$OUTPUT_DIR" BR2_EXTERNAL="$REPO" linux-reconfigure \
  >"$LOG_DIR/s6-experiment/hardened-build-reconfigure.log" 2>&1
env -u BASH_ENV make -C "$OUTPUT_DIR" BR2_EXTERNAL="$REPO" -j2 \
  >>"$LOG_DIR/s6-experiment/hardened-build-reconfigure.log" 2>&1

"$CHECKER/bin/kernel-hardening-checker" \
  -c "$LOG_DIR/s6-experiment/base/linux.config" \
  -l "$REPO/board/cardputerzero/cmdline_rootfs_a.txt" -m json \
  >"$LOG_DIR/s6-experiment/base-checker.json"
"$CHECKER/bin/kernel-hardening-checker" \
  -c "$OUTPUT_DIR/build/linux-custom/.config" \
  -l "$REPO/board/cardputerzero/cmdline_rootfs_a.txt" -m json \
  >"$LOG_DIR/s6-experiment/hardened-checker.json"

env -u BASH_ENV "$REPO/board/cardputerzero/tools/bench/run-s6-guest-check.sh" \
  "$OUTPUT_DIR" "$LOG_DIR/s6-guest-check"
```

`host-kmod-reconfigure` enables XZ support in host `depmod`; target module decompression uses the merged `CONFIG_MODULE_DECOMPRESS=y`. Buildroot sets `BR2_LINUX_KERNEL_NEEDS_HOST_OPENSSL=y`, and `linux.mk` adds `host-openssl`. The default `CONFIG_MODULE_SIG_KEY="certs/signing_key.pem"` generates a per-build key. Generated keys and certificates remain under Buildroot output and are not committed. The guest runner temporarily adds its hook and unsigned test module to the overlay, runs both slots, then removes those files. The bench hook is not included in the default image.

Boot time uses `QEMU_ICOUNT=shift=0` and `QEMU_EXTRA_APPEND='initcall_debug printk.time=1 msd.sweep=1'`. 次の二つの command を実行する。

```sh
"$REPO/board/cardputerzero/tools/bench/run-s6-boot-cost.sh" base \
  "$LOG_DIR/s6-experiment/base/images/sdcard.img" \
  "$LOG_DIR/s6-experiment/base/images/Image" \
  "$LOG_DIR/s6-experiment/base/images/bcm2710-rpi-3-b.dtb" \
  "$LOG_DIR/s6-experiment/boot/base" "$LOG_DIR/s6-experiment/boot-cost.csv"
"$REPO/board/cardputerzero/tools/bench/run-s6-boot-cost.sh" hardened \
  "$OUTPUT_DIR/images/sdcard.img" "$OUTPUT_DIR/images/Image" \
  "$OUTPUT_DIR/images/bcm2710-rpi-3-b.dtb" \
  "$LOG_DIR/s6-experiment/boot/hardened" "$LOG_DIR/s6-experiment/boot-cost.csv"
```

サイズは `stat -c %s Image`、`gzip -9n -c Image | wc -c`、boot VFAT 内の `kernel8.img`、installed `.ko.xz` の合計で計算する。checker は workflow と同じ pinned binary を使い、JSON の `check_result_bool` を集計する。

## 計測器の検証

guest hook は未署名 `usbnet` を `insmod` して署名・鍵エラーでの拒否を確認し、その後、同じ module の署名済み配布版を `modprobe` して `lsmod` に表示されることを確認した。この正負両方の応答で guest hook の検査経路を検証した。

Boot timestamp は `MSD/Linux ready` 行から抽出した。QEMU ICOUNT 条件で base/hardened を各 3 回実行したところ、base の最大−最小は `0.006140 s`、hardened は `0.011278 s`（0.001 s 単位では 0.011 s）で、中央値差 `0.082673 s`（0.001 s 単位では 0.083 s）より小さかった。既定の 5 回ではなく 3 回にしたのは ICOUNT の決定性とこの run 間 spread を理由とする。これは boot timer の再現性の確認であり、実機計測ではない。

## 結果

| artifact | base (B) | hardened (B) | 差 (B) |
|---|---:|---:|---:|
| `Image` | 26,249,728 | 26,380,800 | +131,072 |
| `gzip -9n Image` | 10,495,325 | 10,521,065 | +25,740 |
| boot VFAT 内 `kernel8.img` | 10,082,566 | 10,103,524 | +20,958 |
| installed compressed modules | 10,604,912 | 11,313,872 | +708,960 |
| 署名済み module | — | 1,039 / 1,039 | 全件 |

Boot 値の単位は秒。QEMU 内の kernel timestamp であり、実機の boot time ではない。

| 変種 | run 1 | run 2 | run 3 | 中央値 | 最小−最大 |
|---|---:|---:|---:|---:|---:|
| base | 3.142622 | 3.142595 | 3.136482 | 3.142595 | 3.136482−3.142622 |
| hardened | 3.235654 | 3.225268 | 3.224376 | 3.225268 | 3.224376−3.235654 |

| 変種 | checker OK | checker FAIL |
|---|---:|---:|
| base | 146 | 125 |
| hardened | 160 | 111 |

base の FAIL から消えた項目は `CONFIG_HARDENED_USERCOPY`、`CONFIG_HARDENED_USERCOPY_DEFAULT_ON`、`CONFIG_HARDENED_USERCOPY_FALLBACK`、`CONFIG_HARDENED_USERCOPY_PAGESPAN`、`CONFIG_LSM`、`CONFIG_MODULE_SIG`、`CONFIG_MODULE_SIG_ALL`、`CONFIG_MODULE_SIG_FORCE`、`CONFIG_SECURITY_YAMA`、`hardened_usercopy`、`module.sig_enforce`。新しい FAIL はなかった。

最終 `.config` は `CONFIG_LSM="landlock,lockdown,yama,loadpin,safesetid,apparmor,selinux,smack,tomoyo,ipe,bpf"`。QEMU は `LSM: initializing lsm=capability,yama,apparmor` と記録し、両 slot で `ptrace_scope=1` を確認した。p5 の `test-boot.sh`、p6 の `test-ab.sh` は成功した。`modules.dep` guard は成功し、index は 100,501 B で `usbnet` entry を含んだ。生値は[隣接する CSV](2026-10-19-s06-kernel-hardening.csv)に記録した。

## 捨てた試行と経緯

`CONFIG_SECURITY_YAMA=y` だけで `CONFIG_LSM` が空のときは Yama が初期化されず、`ptrace_scope` もなかった。`CONFIG_LSM="yama"` だけでは他の既定 LSM を外すため、既定一覧を維持して Yama を加えた。

先行する guest check では `modules.dep` が 0 B で `modprobe usbnet` が失敗した。host depmod が `.ko.xz` を読めないことが原因で、#28 の host kmod XZ 修正につながった。現在の main では `+XZ` が有効。

最初の再利用 output での hardened build は古い `.config` のまま実行され、空の `signing_key.x509` による `Short read` で失敗した。`linux-reconfigure` 後の再 build で fragment が適用され、OpenSSL による per-build key generation と module signing が成功した。

## 結論

Tier A の `STACKPROTECTOR_STRONG`、`STRICT_KERNEL_RWX`、`RANDOMIZE_BASE`、`BPF_UNPRIV_DEFAULT_OFF`、`HARDENED_USERCOPY`、Yama、module signing を採用する。`MODULE_SIG_FORCE` は per-build key と組み合わせる。`modules_disabled=1` は USB／Wi-Fi／Bluetooth の hotplug autoload を妨げるため採用しない。信頼鍵で署名されていない第三者製 out-of-tree module はロードできない。kernel signing の外部根拠は [kernel module signing documentation](https://docs.kernel.org/admin-guide/module-signing.html) の “modules will be automatically signed during the modules_install phase of a build” と “only modules that have a valid signature that can be verified by a public key in the kernel’s possession will be loaded.” である。【一次】

## 未確認の点

Pi firmware が `kaslr-seed` を実機で渡すかは未確認であり、実機で確認する。QEMU のサイズ／boot cost は実機性能を示さない。

## ログ

下記はすべて「リポジトリ外（ローカルのみ）」の記録である。ファイル名は `$LOG_DIR` からの相対名。各 build/runner の stdout と stderr を同じファイルへ保存する。失敗した古い `.config` の build log は現状態では再現せず、表に記した旧状態と command の組み合わせでのみ再生成できる。

| `$LOG_DIR` からの相対名 | SHA-256 | 再生成 command |
|---|---|---|
| `s6-experiment/base-build.log` | `8d59c5c6bdedf7185fe11536acfbac813a89d8e1ae13c1a72db108c334c9d975` | 手順の base `defconfig`、`host-kmod-reconfigure`、build を `{ ...; } > "$LOG_DIR/s6-experiment/base-build.log" 2>&1` で実行 |
| `s6-experiment/hardened-build.log`（失敗試行） | `ed43920b6da6fb730c4179b6aa9f7b61be5b2c4829aeadec4758757e0205a746` | `env -u BASH_ENV make -C "$OUTPUT_DIR" -j2 >"$LOG_DIR/s6-experiment/hardened-build.log" 2>&1`（当時の stale `.config` と空の cert が必要） |
| `s6-experiment/hardened-build-reconfigure.log` | `e15e615bea5e71be42ba286faf83187e87b9c51747c05950ec7a7365d8245a50` | `env -u BASH_ENV make -C "$OUTPUT_DIR" BR2_EXTERNAL="$REPO" linux-reconfigure >"$LOG_DIR/s6-experiment/hardened-build-reconfigure.log" 2>&1` の後、`env -u BASH_ENV make -C "$OUTPUT_DIR" BR2_EXTERNAL="$REPO" -j2 >>"$LOG_DIR/s6-experiment/hardened-build-reconfigure.log" 2>&1` |
| `s6-experiment/base-checker.json` | `ab21b7c8e9e7ad8e41fcfb39bd7221c5cfefb09058fa977847c52b35f674fecc` | `"$CHECKER/bin/kernel-hardening-checker" -c "$LOG_DIR/s6-experiment/base/linux.config" -l "$REPO/board/cardputerzero/cmdline_rootfs_a.txt" -m json >"$LOG_DIR/s6-experiment/base-checker.json"` |
| `s6-experiment/hardened-checker.json` | `d517345d73025a1a30708660ee63aabbb26505bf782a38cb1b89ffd6bb7193ba` | `"$CHECKER/bin/kernel-hardening-checker" -c "$OUTPUT_DIR/build/linux-custom/.config" -l "$REPO/board/cardputerzero/cmdline_rootfs_a.txt" -m json >"$LOG_DIR/s6-experiment/hardened-checker.json"` |
| `fix-modules-dep/host-kmod-reconfigure.log` | `a6c0c2deb95b6c99ea0a0f7ab802a431ef6d3772922887dd09cb660a0c4d5f4e` | `env -u BASH_ENV make -C "$OUTPUT_DIR" host-kmod-reconfigure >"$LOG_DIR/fix-modules-dep/host-kmod-reconfigure.log" 2>&1` |
| `s6-experiment/boot-cost.csv` | `c96b238e448f698bd704342143f79bfe2998ac25710cb929cf34dccede504308` | base と hardened の `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/base/run1/serial-mmcblk0p5.log` | `503a5d1f0802842e1a62d6a2c9bd7f9a292318a616ac389f8365daf8de32cc64` | base `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/base/run2/serial-mmcblk0p5.log` | `5a837a955230c55ea83e9612cf575a8cf1f5ec28c6776f7fc34fe7459fd838ac` | base `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/base/run3/serial-mmcblk0p5.log` | `1e5a2e1b7b429940ea0cad28cb1cfb763e4ad389de944832743e89f99e428c83` | base `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/hardened/run1/serial-mmcblk0p5.log` | `d022681058db678e2341de63549492520ed13da19b93b0a16ccbe4d7a90236cf` | hardened `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/hardened/run2/serial-mmcblk0p5.log` | `885caa6b38005c5b143d6b8ce0558efb0f0cf4b13f5ce2b69050058ea6056e9f` | hardened `run-s6-boot-cost.sh` command in 手順 |
| `s6-experiment/boot/hardened/run3/serial-mmcblk0p5.log` | `0408bbab0dcffddd17fef92bdffab819c3abc5b604802ac513478dfaddce907b` | hardened `run-s6-boot-cost.sh` command in 手順 |
| `s6-guest-check/mmcblk0p5/serial-mmcblk0p5.log` | `90dfafad8eb3d8f2ea4f7a55cf2623d82a004dc57d41408ae47a1fceb913d1d8` | `env -u BASH_ENV "$REPO/board/cardputerzero/tools/bench/run-s6-guest-check.sh" "$OUTPUT_DIR" "$LOG_DIR/s6-guest-check"` |
| `s6-guest-check/mmcblk0p6/serial-mmcblk0p6.log` | `8aa1783b264d365fb4a5a47a8fbce3f8147a33c0c7411b160f98513e6f8f7e4b` | `env -u BASH_ENV "$REPO/board/cardputerzero/tools/bench/run-s6-guest-check.sh" "$OUTPUT_DIR" "$LOG_DIR/s6-guest-check"` |
