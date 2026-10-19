# S6 圧縮モジュールの依存 index とロード

- 状態: 完了
- 日付: 2026-10-19
- 担当: Devin
- 関連: PR #28、[Build workflow](../../.github/workflows/build.yml)、[訂正済み事項](../research/corrections.md)

## 目的と仮説

S6 の QEMU module-load 試験で `/lib/modules/6.18.57-v8/modules.dep` が空と判明した。host depmod が XZ 対応なら、圧縮アルゴリズムを変えず `.ko.xz` を index 化し、guest `modprobe usbnet` がロードできると考えた。

## 採否の基準（結果を見る前に書く）

Buildroot の `modules.dep` が空でなく `usbnet` entry を持つこと、A/B 両 slot の QEMU で `modprobe usbnet` 成功後に `lsmod` が `usbnet` を示すことを合格条件とする。

## 条件

| 項目 | 値 |
|---|---|
| 基準の commit | `e08efe2f1ea80a3307eb9a7aa4c95ed8be56a89e` |
| ホスト | Ubuntu 22.04 |
| QEMU | 6.2.0 |
| Buildroot / GCC / カーネル | 2026.08（source revision `d6061d65`）/ 14.3.0 / 6.18.57-v8 |
| 使ったツールの版 | host kmod/depmod 34.2 `+XZ`。Buildroot host GCC 14.3.0 |
| 出力先と状態 | `OUTPUT_DIR=<Buildroot の O= ディレクトリ>`。既存 output を再利用し `host-kmod-reconfigure` 後に build |
| 変える条件 | `BR2_PACKAGE_HOST_KMOD_XZ=y`、`CONFIG_MODULE_DECOMPRESS=y` |
| 変えない条件 | XZ module compression、target BusyBox modprobe |
| 繰り返し | p5 と p6 を各 1 回 |

## 手順

```sh
REPO=<リポジトリのルート>
OUTPUT_DIR=<Buildroot の O= ディレクトリ>
LOG_DIR=<ローカルログの保存先>
env -u BASH_ENV make -C "$OUTPUT_DIR" host-kmod-reconfigure
env -u BASH_ENV make -C "$OUTPUT_DIR"
"$REPO/board/cardputerzero/tools/check-modules-dep.sh" "$OUTPUT_DIR/target"
QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-boot.sh" \
  "$OUTPUT_DIR/images/sdcard.img"
QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-ab.sh" \
  "$OUTPUT_DIR/images/sdcard.img"
```

## 計測器の検証

Buildroot host depmod は変更前に `kmod version 34.2 -ZSTD -XZ -ZLIB -OPENSSL` と表示し、圧縮済み `.ko.xz` を読み飛ばして `modules.dep` 0 bytes を生成していた。`host-kmod-reconfigure` 後は `kmod version 34.2 -ZSTD +XZ -ZLIB -OPENSSL` となり、index に `kernel/drivers/net/usb/usbnet.ko.xz:` が記録された。target は BusyBox `modprobe` であり、圧縮済み module の展開は kernel の `CONFIG_MODULE_DECOMPRESS=y` で行う。

## 結果

`modules.dep` は 100,501 bytes で、`usbnet.ko.xz` entry を含んだ。p5 と p6 の QEMU serial log はともに `MODULE_CHECK: usbnet loaded via modprobe and shown by lsmod` を記録した。

## 捨てた試行と経緯

当初の module dependency file は空で、既存の boot smoke test は module をロードしていなかったため、この不具合を検出できなかった。target に XZ userspace package を追加するのではなく、kernel 内蔵 decompressor を使う構成を採用した。圧縮方式は変更していない。

`modules.dep` が空の間、Wi-Fi、Bluetooth、audio、USB-net module の autoload が動かなかった可能性があるが、実機での状態は未確認である。A/B の local QEMU 試験後も CI module-load assertion が不足していた。この gap を検出する QEMU assertion は別ブランチ `devin/ci-test-gaps` に追加したが、CI 実行結果は未確認である。

## 結論

`BR2_PACKAGE_HOST_KMOD_XZ=y` と `CONFIG_MODULE_DECOMPRESS=y` を採用し、Build 後の `check-modules-dep.sh` で空 index と `usbnet` entry 欠落を検査する。QEMU は A/B の guest module load を確認したが、実機 autoload は未確認である。

## 未確認の点

Wi-Fi、Bluetooth、audio、USB-net の自動ロードが実機で動作するかは未確認である。QEMU smoke test は実際の peripheral を検証しない。

## ログ

大きなログは**リポジトリ外（ローカルのみ）**。以下の名前は `$LOG_DIR` からの相対パスである。

| 相対名 | SHA-256 | 再生成コマンド |
|---|---|---|
| `build.log` | `591973d087150c5b77b02a76dd787da584d481bab1bedd5210adbb73429ee2f3` | `env -u BASH_ENV make -C "$OUTPUT_DIR"` |
| `host-kmod-reconfigure.log` | `a6c0c2deb95b6c99ea0a0f7ab802a431ef6d3772922887dd09cb660a0c4d5f4e` | `env -u BASH_ENV make -C "$OUTPUT_DIR" host-kmod-reconfigure` |
| `qemu/serial-mmcblk0p5.log` | `003b79a36097848a8e92af03f7ca02bbc7d59f9b7cd96e5959e41d17d2b195b8` | `QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-boot.sh" "$OUTPUT_DIR/images/sdcard.img"` |
| `qemu/serial-mmcblk0p6.log` | `5a3d17b6b1363da34fedb7f51d1017e47f71225bdf0d417fda6d4d3e6541a707` | `QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-ab.sh" "$OUTPUT_DIR/images/sdcard.img"` |
| `qemu/test-boot.log` | `166554fe9101680d60e34f974145a9224f203e1971aa3f061982046de41a6e43` | `QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-boot.sh" "$OUTPUT_DIR/images/sdcard.img"` |
| `qemu/test-ab.log` | `9b3cbf443e669fee78f914b88439ddaf2ef1daa87aa052f07cec2ac5577f41df` | `QEMU_LOG_DIR="$LOG_DIR/qemu" "$REPO/board/cardputerzero/qemu/test-ab.sh" "$OUTPUT_DIR/images/sdcard.img"` |
