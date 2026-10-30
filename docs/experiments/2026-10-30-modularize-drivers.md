# 任意機能ドライバーのモジュール化（QEMU）

kernel Image を小さくするため、起動直後に必須でないドライバーを `=y` から `=m` に変えて QEMU で比較した記録です。

## 条件

- ベースカーネル: 6.18.58-v8（`bcm2711_defconfig` + `board/cardputerzero/linux.fragment` + 実験用追加分）
- 実験用追加分（両構成で共通）: `CONFIG_PREEMPT_RT=y`、`CONFIG_BLK_DEV_DM=y`、`CONFIG_DM_DELAY=y`、`CONFIG_DM_FLAKEY=y`、`CONFIG_BTRFS_FS=y`
- `=m` に変えた対象: `CONFIG_F2FS_FS`、`CONFIG_FAT_FS`、`CONFIG_MSDOS_FS`、`CONFIG_VFAT_FS`、`CONFIG_USB_STORAGE`、`CONFIG_USB_UAS`、Bluetooth 関連（`CONFIG_BT_HCIBCM203X` などの HCI トランスポート群。`BT_RFCOMM`、`BT_BNEP`、`BT_BCM`、`BT_HCIUART` は製品構成でも `=m`）
- モジュールは同じビルドツリーの署名鍵で署名され、rootfs に `/lib/modules/6.18.58-v8/kernel/` 以下へ `xz` 圧縮で収録される
- 計測は icount `shift=0,sleep=off`、n=1、ゲスト時刻は init ログより

## 結果

| 項目 | 全ビルトイン | モジュール化 |
|---|---:|---:|
| Image [B] | 24,082,944 | 23,222,784 |
| 差分 [B] | — | -860,160（-3.6%） |
| root マウント [s] | 約 1.3 | 1.346 |
| `MSD/Linux ready` | 到達 | 到達 |

- rootfs の SquashFS にはモジュール（`f2fs.ko`、`fat.ko`、`vfat.ko`、`usb-storage.ko`、`uas.ko` など）が追加される。正味のイメージ合計差は Image の減少分より小さい（実験 rootfs は追加ツール込みのため、モジュール分だけの純粋な増分は未分離）。
- モジュールは modalias 経由で自動ロードされる。テストでは loop デバイスの F2FS が `mount` 実行時に `f2fs.ko` を自動ロードして正常にマウントできた（`F2FS-fs (loop0): Mounted`）。
- `MSD/Linux ready` まで到達し、起動失敗やカーネルパニックは見られなかった。

## 結論

- モジュール化で Image は約 3.6%（860 KiB）小さくなり、QEMU 起動は問題なく通る。対象ドライバーは modalias 自動ロードで透過的に使える。
- ただしモジュールは rootfs に移るだけなので、フラッシュ使用量の節約効果は Image の減少分より小さい。またモジュール署名鍵はビルドツリーごとに生成されるため、カーネルと rootfs が別ツリー由来だと `modprobe` が拒否される（S17 の記録で確認済み）。
- 製品への適用を考えるなら、起動パスで使わないものに限るのが安全。`FAT_FS`/`VFAT_FS`/`MSDOS_FS` は `/boot`（boot.vfat）を扱う更新ツールが依存するためビルトイン維持が妥当。`F2FS_FS`（現行では /data は ext4 で未使用）と `USB_STORAGE`/`USB_UAS`（周辺機器のみ）はモジュール化候補になりうるが、節約量（数百 KiB 程度）に対して署名鍵ペア管理の複雑さを考えると現状では見送りが妥当。

## 失敗した試行・注意点

- 本検証の Image 差分は「対象ドライバーのみを `=m` 化」した 2 構成の直接比較ではなく、同じツリーでフラグだけを変えた前後ビルドの比較。カーネルの非決定的なサイズ変動（数 KiB）は含む。
- モジュールを `modprobe` する際は、カーネルと rootfs を同じビルドツリーから用意すること（`CONFIG_MODULE_SIG_FORCE=y` により別ツリーのモジュールは鍵不一致で拒否される）。
