# S4: `/data` ファイルシステム比較（ext4 / F2FS / btrfs）

読み取り専用領域と FS 比較の対象として、ext4・F2FS・btrfs を QEMU ゲスト内の loop デバイスで計測した。製品の /data は引き続き ext4。

## 条件

- 基準: `origin/main` + output2 実験ツリー。カーネル 6.18.58（`PREEMPT_RT`、計測系に影響しない範囲で変形済みのため明記）
- 追加設定（実験のみ・製品 defconfig には入れない）: `CONFIG_BLK_DEV_DM=y`、`CONFIG_DM_DELAY=y`、`CONFIG_DM_FLAKEY=y`、`CONFIG_BTRFS_FS=y`、BR2 `F2FS_TOOLS`・`BTRFS_PROGS`・`LVM2`
- 計測対象: `/data` 上の 128 MiB ファイルを loop0 にアタッチし各 FS を mkfs→mount→書込→drop_caches→読出
- データ: `/dev/urandom` 16 MiB、busybox `time`、ゲスト時刻・n=1
- btrfs-progs 6.10、f2fs-tools、e2fsprogs 1.47.4

## 手順

テスト用 init.d フック（`S99ztest`）を第 2 rootfs-overlay 経由で試験イメージにだけ混入させ、シリアル出力から結果を回収した（製品 overlay は未変更）。

## 生の値

| FS | mkfs | write 16 MiB | sync | read 16 MiB | df 使用 / 空き [KiB] |
|---|---:|---:|---:|---:|---:|
| ext4 | 0.29 s | 0.12 s | 0.17 s | 0.08 s | 16,526 / 91,503 |
| F2FS | 0.24 s | 0.06 s | 0.20 s | 0.08 s | 57,376 / 71,648 |
| btrfs | 0.24 s | 0.11 s | 0.17 s | 0.09 s | 22,368 / 31,744 |

128 MiB ボリュームで btrfs は metadata DUP により usable が約 3 割少ない。mkfs・読み書き速度はこの規模では差が見えない。F2FS は `mkfs.f2fs` に `-f` が必要だった（既存 signature 上の上書き）。

## 結論

QEMU 規模の計測では mkfs・シーケンシャル読み書きの差は小さい。決定的な違いは btrfs のメタデータオーバーヘッド（128 MiB で usable 約 32 MiB）で、小容量 /data には不利。F2FS は flash 向きだが mount 時 `f2fs_recover_fsync_data` の回復経路が走る。ext4 は journal + `fsck -p` による透過回復が S16 で確認済みで、現行 ext4 の維持が妥当。

## 失敗した試行・注意点

- `mkfs.btrfs` は 128 MiB 未満を拒否（min 114,294,784 B ≒ 109 MiB）。96 MiB では `ERROR: '/dev/loop0' is too small`。
- `mkfs.f2fs` の既定は既存 signature を拒否（exit 255）。`-f` が必要。
- `CONFIG_MODULE_SIG_FORCE=y` の製品設定では未署名モジュールが拒否されるため、実験用ドライバは `=m` ではなく `=y` 組み込みにする必要がある（今回 dm-flakey・btrfs が該当）。
- カーネル側は `dm`・`dm-flakey`・`btrfs` を `=y` にしたが、ゲスト内 `/dev/mapper/control` が無いと dmsetup は失敗する（別途 dev node が必要、S17 記録参照）。
- `docker run -i` の pipe stdin は QEMU の `mon:stdio` が tty 判定するため入力が届かない。`-serial unix:` ソケットでも同時接続は 1 クライアントのみで、双方向は同一接続を使う必要がある。交互入力より init.d フックの方が確実。

## 未検証

- 実機 SD カードでの FTL レイテンシー・ウェアの差異
- 電源断時の F2FS/btrfs 回復（S16 相当の試験は ext4 のみ）
- btrfs の最小ボリューム（`-M` mixed や DUP 解除）での usable 改善
