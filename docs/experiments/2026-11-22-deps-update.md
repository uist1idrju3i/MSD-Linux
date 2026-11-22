# 2026-11-22 依存一括更新の検証

## 条件

- 作業ブランチ: `devin/1795306418-deps-update`
- 実施日: 2026-11-22、環境は Devin VM（2 vCPU、Docker 内の `msd-dev` イメージで測定）
- 対象: Buildroot 2026.08 系 HEAD、m5stack dtoverlays、yomiyasu v3.2.3、kernel rpi-6.18.y 系、Go 1.27.4、Trivy 0.76.2、QEMU 11.1.3、Debian snapshot

## Debian snapshot の不整合と修正

- 症状: `docker/msd-dev build` が `libssl-dev : Depends: libssl3t64 (= 3.5.7-1~deb13u3) but 3.5.9-1~deb13u1 is to be installed` で失敗。
- 原因: base image 内の `libssl3t64` が 3.5.9 に上がった一方、pin の snapshot `20261107T075304Z` 側の `libssl-dev` は 3.5.7 で依存が不成立。
- 対応: `DEBIAN_SNAPSHOT` を `20261121T225354Z` に更新。snapshot 側の `libssl-dev` の候補が 3.5.9-1~deb13u1 となり base と一致することを確認。snapshot.debian.org は任意の日時から「それ以前の最新」へ 302 リダイレクトされるため、debian-security 側も同日時以前の最新で解決する。

## Buildroot build

- コマンド: `make -C vendor/buildroot BR2_EXTERNAL="$PWD" O="$PWD/output" msd_cardputerzero_defconfig && make -C output host-ccache && make -C output -j2 && make -C output legal-info`
- 結果: 成功。`output/images/` に `sdcard.img`、`rootfs.squashfs`、`data.ext4`、`msd-update-bundle.tar` などが生成された。`legal-info` も生成。
- `board/cardputerzero/check-image-layout.sh`: OK（7 分区、すべて先頭 8192 sector 境界）。
- `check-kernel-fragment.sh board/cardputerzero/linux.fragment output/build/linux-custom/.config`: `CONFIG_NODES_SHIFT` だけ不一致（`=1` 要求、`n`）。新旧いずれの kernel でも `arch/arm64/Kconfig` が `depends on NUMA` で `CONFIG_NUMA` は fragment で無効のため、現れない項目。更新前からの既存事項であり、今回の kernel 更新による退行ではない。
- License: yomiyasu v3.1.0→v3.2.3、m5stack dtoverlays 4f7aeee→a3fd3e8、buildroot 75f325ad→bbbdab36 のいずれも LICENSE/COPYING ファイルに差分なし。kernel の license hash も変更なし。

## QEMU icount gate

`board/cardputerzero/tools/compare-icount.sh` で `output/images/sdcard.img` の icount 起動（`shift=0,sleep=off`）の ready 実時間を比較。各 binary は `board/cardputerzero/tools/qemu-bisect/build-qemu.sh` で product パッチ込みで build したもの（11.1.2 は `msd-dev` image 同梱のもの）。

| 比較 | A | B | ready 実時間（A→B） | ratio | 判定 |
|---|---|---|---|---|---|
| 11.0.2 vs 11.1.3 | 11.0.2 | 11.1.3 | 19 s → 91 s | 4.79x | gate 不成立（1.5x 超過） |
| 11.1.2 vs 11.1.3 | 11.1.2 | 11.1.3 | 90 s → 98 s | 1.09x | gate 成立 |

- 11.1.x 系が 11.0.2 比で遅いのは 2026-10-31 の bisect で判明済みの regression（01b223f895、A-profile WFE sleeping）。現行 image の 11.1.2 も同程度（90 s）で、この退行は 11.1.2 採用時点で受け入れ済み。
- したがって patch 更新としての比較基準は現行 11.1.2 とし、1.09x で閾値内。QEMU は 11.1.3 に更新する。
- QEMU 11.1.2..11.1.3 は 99 commits、icount 関連の修正は含まれない（changelog 確認）。

## 未確認

- 実機（LCD、keyboard、M5 I2C、firmware tryboot、電源断）は QEMU で確認できない。
- m5stack dtoverlays の bq27220 gauge 変更（FCC 1350 mAh、raw FCC sysfs 停止など）は product の `bq27220_v5` overlay に影響するが、実機での確認は未実施。
- kernel の `.config` の新旧完全 diff は未実施（fragment 検査で要求 490 項目のうち `NODES_SHIFT` のみ不一致であることは確認済み）。
