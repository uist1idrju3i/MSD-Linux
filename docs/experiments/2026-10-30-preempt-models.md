# PREEMPT モデル比較（NONE / PREEMPT / PREEMPT_RT）

## 目的

カーネルの preemption モデル 3 種（`PREEMPT_NONE`、`PREEMPT`、`PREEMPT_RT`）で、イメージサイズと QEMU 上の起動時間を比較し、現行の `PREEMPT` を維持する根拠を確認する。

## 条件

- ベース: main（Buildroot 2026.08.x、kernel 6.18.58 raspberrypi/linux aeadd6ed）
- カーネル設定の出発点: `bcm2711_defconfig` + `board/cardputerzero/linux.fragment`（`make ARCH=arm64 olddefconfig` で生成）
- 各モデルの切り替えは `./scripts/config` で排他指定し `make ARCH=arm64 olddefconfig` で確定
  - NONE: `--disable PREEMPT --enable PREEMPT_NONE`
  - PREEMPT: 既定（`CONFIG_PREEMPT=y`、動的 preemption なし）
  - RT: `CONFIG_PREEMPT=y` + `CONFIG_PREEMPT_RT=y`（6.18 では mainline に RT 統合済み）
- ビルド: `output2` ツリーで `make linux-rebuild -j2 && make -j2`（msd-dev イメージ内）
- 起動: `run-qemu.sh` + `QEMU_ICOUNT='shift=0,sleep=off'`、対象カーネルは `-e KERNEL_IMAGE=/work/output2/images/Image`
- 測定点: `VFS: Mounted root`（root マウント完了）と `EXT4-fs ... resized`（/data 拡張完了）のゲスト時刻。`MSD/Linux ready` 到達を起動成功とする
- n=1、同一 sdcard イメージ（output2 生成、rootfs.squashfs）

## 結果

| モデル | Image [B] | root マウント [s] | resize 完了 [s] | 起動バナー |
|---|---:|---:|---:|---|
| PREEMPT_NONE | 22,579,712 | 0.786 | 2.214 | `#3 SMP` |
| PREEMPT（現行） | 22,383,104 | 0.807 | 2.211 | `#4 SMP PREEMPT` |
| PREEMPT_RT | 22,465,024 | 0.844 | 2.235 | `#5 SMP PREEMPT_RT` |

3 モデルとも QEMU で `MSD/Linux ready` まで到達した。起動時間差は root マウントで最大 0.058 s（約 7 %）、resize 完了で 0.024 s と小さい。Image サイズは NONE が最大、PREEMPT が最小で差は約 0.9 %。

## 結論

起動時間とサイズの差は小さく、いずれのモデルでも QEMU 起動は成立する。現行の `PREEMPT` は妥当な既定として維持する。`PREEMPT_RT` も起動可能なことが確認できたため、実機でスケジューリング特性（入力応答・タイマー精度）が必要になった場合の選択肢として使える。実機でのレイテンシー測定（`cyclictest` など）は QEMU では評価できず未実施。

## 失敗した試行・注意点

- `make olddefconfig` に `ARCH=arm64` を付け忘れて作ったカーネルは起動即ハング（シリアル無出力）になった。カーネル `.config` の手動編集後は `make ARCH=arm64 olddefconfig` が必須。
- `KERNEL_IMAGE` の既定は `output/images/Image` であり、別ビルドツリーのカーネルを試すときは環境変数で明示する。指定を忘れると output/ のカーネルが走り、測定対象が違うものになる。
- QEMU 実行は `msd-dev:local` イメージで行う。`msd-qemu-test:local` には `qemu-system-aarch64` が PATH に無く（`/opt/qemu/bin` に存在）、run-qemu.sh が dtb 行の後に出力なく終了する。
