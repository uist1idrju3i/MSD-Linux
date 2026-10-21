# dm-verity による rootfs 改ざん拒否（QEMU）

この実験は完了した。実施日は 2026-10-21 で、関連する文書は [実験計画](../research/simulation-plan.md) と #27 である。

## 目的と仮説

dm-verity で保護した SquashFS rootfs が無改ざんで起動し、data・hash tree・root hash の改ざんでは検証エラーになることを QEMU で調べる。製品設定は変更しない。

## 結果を見る前に固定した事前登録

以下は、結果を見る前に決めた条件を日本語に訳したものである。

### Prereg v1

検証する問いは、verity で保護した rootfs が無改ざんで起動し、改ざん後は起動を拒否するか、破損 block の読み出しを拒否するかである。

基準には BusyBox 実験と同じ `ce932cd0e83ebf10be853c51d9ae09116aea92bb` を使う。試験イメージだけを変更し、製品設定は変更しない。

Kernel variant には `CONFIG_BLK_DEV_DM=y`、`CONFIG_DM_VERITY=y`、`CONFIG_DM_INIT=y` を設定し、initramfs は使わない。最終 `.config` の DM 設定を記録する。

Buildroot host-cryptsetup の `veritysetup format --data-block-size=4096 --hash-block-size=4096 --hash-offset=<data bytes を 4096 へ切り上げ> rootfs.img rootfs.img` を使い、同じ rootfs partition の SquashFS の後方に hash tree を置く。合計が 256 MiB 以下であることを確認し、root hash、salt、data blocks、hash 開始 block を記録する。

A slot だけを試験する。cmdline に `root=/dev/dm-0` と `dm-mod.create="vroot,,,ro,0 <data_sectors> verity 1 /dev/mmcblk0p5 /dev/mmcblk0p5 4096 4096 <data_blocks> <hash_start_block> sha256 <root_hash> <salt> 1 panic_on_corruption"` を加え、残りは変更しない。QEMU は `-no-reboot` で起動する。

各 case は QEMU icount `shift=0` で 5 回起動する。V0 は verity なしの基準、T0 は verity 有効・無改ざん、T1 は SquashFS superblock 領域の byte 0x60、T2 は inode table 先頭+16、T3 は data 領域中央の `4096 × floor(data_blocks/2) + 123`、T4 は hash tree 先頭を変更する。T5 では data を変更せず、cmdline の root hash 末尾 1 桁を変更する。

合格条件は、T0 が 5/5 valid となり、T1/T2/T4/T5 が各 5/5 で ready に到達せず、serial log に verity error または verity 起因 panic が出ることである。T3 では ready の有無と、破損 block を読んだ時の挙動を記録する。ready 前に当該 block を読まなければ verity error は期待しない。T0 と V0 の ready 中央値の差を報告するが、閾値は設けず、QEMU の値として扱う。

この実験の制限は、CardputerZero に secure boot がなく、cmdline と boot FAT が未署名であること、A/B 更新で `msd-update` が hash tree と slot ごとの root hash を書く処理が未実装であること、FEC と root hash 署名を試していないこと、実 SD を模擬していないことにある。

### Amendment 1（2026-10-21、T0 初回の後、T1〜T5 起動前）

初回 T0 では dm-init が非同期 probe 中の MMC partition より先に動き、`verity: Data device lookup failed (-ENODEV)`、続いて `Waiting for root device /dev/dm-0...` となって timeout した。事前登録から `dm-mod.waitfor=` が漏れていたため、T0〜T5 の verity cmdline に `dm-mod.waitfor=/dev/mmcblk0p5` を加え、他の条件は変えない。初回 T0 の boot0 timeout と停止時の boot1/boot2 部分試行は失敗として残す。T0 を 5 回やり直し、その後 T1〜T5 を各 5 回実行する。復元 kernel の `.config` は V0 と同じ hash だったが、Image には 67 bytes・12 区間の build metadata 差があった。追加 build はせず、V0 の起動には元の Image を使ったことを記録する。

### Amendment 2（2026-10-21、T0-A1 の boot0/boot1 後、T1〜T5 起動前）

Buildroot の既定設定 `BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW=y` は、`/etc/inittab` に `::sysinit:/bin/mount -o remount,rw /` を追加する。mmcblk 上では read-only SquashFS への remount は実質何もせずに成功する。一方、read-only dm device では `reconfigure_super()` が `-EACCES` を返し、serial error check によって起動が invalid になる。dm-0 の準備、root mount、ready marker まで進んでおり、verity 自体は動作していた。

T0〜T5 の試験用 rootfs に限り、veritysetup format の前にこの 1 行だけを削除する。削除前に 1 件、削除後に 0 件であることを assert し、新しい root hash と salt を得る。T1〜T3 の offset は新しい image の superblock から再計算する。V0 は変更しない。T0-A1 は失敗試行として保持し、T0 を 5 回、その後 T1〜T5 を各 5 回実行する。製品でこの行を削除する作業は、`/var` の扱いを決めた後に別 task として行う。

## 条件・ format 値・再現

| 項目 | 値 |
|---|---|
| 基準 HEAD / Buildroot | `ce932cd0e83ebf10be853c51d9ae09116aea92bb` / `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| Buildroot / Linux / target GCC | 2026.08 / 6.18.57-v8 / 14.3.0 |
| QEMU / mksquashfs / veritysetup | QEMU 11.1.2 / mksquashfs 4.7.5 / veritysetup 2.8.7 |
| Host OS | 正確な版は実験時の証跡に未記録 |
| 出力先・再利用状態 | `O=output`。既存出力を再利用。dm 用 kernel は variant config を適用し、復元後の追加 build は行わなかった |
| Linux config SHA-256 | `409a020d493d9e049b49b377421f21309f06382851b4b6910804a2caeb00426d` |
| Buildroot config SHA-256 | `8f8d8ef964dd6c51bd7966a296a660aa33c3b94e25e06bb8c5605e3d13a9bc3e` |
| T0〜T5 Image / DTB SHA-256 | `c1d775efd05b21e1129f21a4c9563f0939f3dd3c3d0810c8c2dbd3eb8bab3792` / `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` |
| V0 Image SHA-256 | `a9d2167486208eea88d75a53ceca83e9e243a3a6af7c6c00db71bb376d50ea47`（元 Image） |
| Format | data blocks 5833、hash blocks 47、offset 23,891,968、hash start block 5834、data sectors 46,664 |
| Root hash / salt | `1cb37caeb790095844ee096064ef64748b6ce3c9a63926c1d71b88eb0fd165cd` / `c9eab80204ec24fb273d841ea7644d7bc0602bd3af8f29dd648b0ba74cde8c2b` |
| Timeout | tamper boot は 422 秒とした。T0 で ready までにかかった host 時間の最大 302 秒に 120 秒を加え、最初の tamper 起動より前に deviations へ記録した。 |

次に再現例を示す。変数は各利用環境で設定する。rootfs の remount 行を検査・削除してから format し、tamper は format 後に実行する。

```sh
docker/msd-dev board/cardputerzero/tools/bench/dm-verity/make-case.sh \
  T0-A2 "$OUTPUT_DIR" "$BASE_DIR" "$CASE_DIR/T0-A2"
docker/msd-dev board/cardputerzero/tools/bench/dm-verity/run-boots.sh \
  --case T0-A2 --image "$CASE_DIR/T0-A2/images/sdcard.img" --runs 4 --timeout 422 \
  --log-dir "$CASE_DIR/T0-A2-boottime" --csv "$CASE_DIR/T0-A2-boottime.csv"
for case_name in T1-A2 T2-A2 T3-A2 T4-A2 T5-A2; do
  docker/msd-dev board/cardputerzero/tools/bench/dm-verity/make-case.sh \
    "$case_name" "$OUTPUT_DIR" "$BASE_DIR" "$CASE_DIR/$case_name"
  expected=verity-error
  if [ "$case_name" = T3-A2 ]; then expected=ready; fi
  docker/msd-dev board/cardputerzero/tools/bench/dm-verity/run-boots.sh \
    --case "$case_name" --image "$CASE_DIR/$case_name/images/sdcard.img" \
    --runs 4 --timeout 422 --expected "$expected" \
    --log-dir "$CASE_DIR/$case_name-boottime" --csv "$CASE_DIR/$case_name-boottime.csv"
done
```

V0 は既存 boottime runner で初回に 1 回、通常起動を 4 回行う。たとえば `docker/msd-dev board/cardputerzero/tools/bench/boottime/run-boottime.sh --variant V0 --runs 4 --mode icount --csv "$CASE_DIR/V0-boottime.csv" --log-dir "$CASE_DIR/V0-boottime"` とする。T0〜T5 の一行削除、format、tamper offsets は `make-case.sh` にまとめた。T1 の offset は 96 (`0x28→0x29`) である。T2 の offset は新しい SquashFS superblock の inode table start 23,845,319 に 16 を加えた 23,845,335 (`0x30→0x31`) である。T3 の offset は 11,944,059 (`0xaa→0xab`)、T4 は 23,896,064 (`0x06→0x07`)、T5 は root hash の末尾 `d→0` である。早期 monitor の誤判定を再現する場合は T3 を `--expected verity-error` で走らせる。上記の `ready` 指定は誤判定を避けた 422 秒の追試である。

## 結果

T0-A2 の 5 回の起動はすべて valid であり、ready marker と login prompt に到達した。ready の中央値は 4.074023 秒だった。V0 の 5 回の起動もすべて valid で、ready の中央値は 3.747029 秒だった。差は 0.326994 秒（+8.7 %）である。T0 と V0 では inittab の 1 行が異なる。ready 時間の差に寄与した要因は、この比較だけでは単独に特定できない。いずれも QEMU の値であり、実機の負担の見積もりには使わない。

| Case | 起動結果 | ready / tamper error |
|---|---|---|
| V0 | 5/5 valid | ready 中央値 3.747029 秒 |
| T0-A2 | 5/5 valid | ready 中央値 4.074023 秒 |
| T1-A2 | 5/5 ready なし | `device-mapper: verity: data block 0 is corrupted`、verity panic |
| T2-A2 | 5/5 ready なし | `device-mapper: verity: data block 5821 is corrupted`、verity panic |
| T3-A2 追試 | 5/5 ready なし（422 秒 timeout） | `data block 2916 is corrupted`、`Kernel panic - not syncing: dm-verity device corrupted` |
| T4-A2 | 5/5 ready なし | `device-mapper: verity: metadata block 5834 is corrupted`、verity panic |
| T5-A2 | 5/5 ready なし | `device-mapper: verity: metadata block 5834 is corrupted`、verity panic |

T1/T2/T4/T5 の起動では panic が起き、runner は status 1 を返した。T3 の追試では panic 後も QEMU が終了しなかったため、事前に定めた 422 秒の timeout で終了し、status 124 となった。これらの起動は ready success ではない。T3 では中央 block を読んだ時点で verity error と panic を確認した。

| Case | `rootfs.img` SHA-256 | `sdcard.img` SHA-256 |
|---|---|---|
| T0-A2 | `87ddb143494a73bf73e9760a34dbf8adeb8eb66135e1a47835fe0d71ba2d6594` | `570b9669061f38777f9c91984a6c904d262d3a96b90c73b5da7eb846d730b75f` |
| T1-A2 | `fad841f472af545c6dcaf8ff67e450a09868198aeba7e2d1f3f3ff40b4c60010` | `98e82ed8e55bd440e57d5dc655c9699f417b8b806af8dae96a1a6bdb82ef4231` |
| T2-A2 | `a6c505aaa797e9e330f0a8168ee193776f0f29ebe5c2b8815ea38e9d7f090007` | `c4a6b0b4b90ab327635e0818013d92daa47abaf04a27b94f63d819d20aa26447` |
| T3-A2 | `40cd3f1685aff05a517b1e5851fb05b050b3d46c6a10a70729f3f3bc2a685e72` | `7aefb8fc0696971d812c97305877573dc431906a2e8bb248c8985879cfed3067` |
| T4-A2 | `67007b6a37d43e7f092619cbd6c40a931f31276f48e860ef6bae02138ac717f4` | `3f81e0c1184e928dd5d191de4e17886a589eac12fa35ea367e46302e71fe5ef5` |
| T5-A2 | T0-A2 と同じ | T0-A2 と同じ |

## 副次の発見: rw remount

`BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW=y` のときに Buildroot が生成する inittab の remount 行は、通常の SquashFS root では read-only のままで何も変えない。read-only dm table では remount が拒否されたことを起動エラーとして検出した。Linux の `fs/super.c` にある `reconfigure_super()` は、次の条件で `-EACCES` を返す。

```c
if (!(fc->sb_flags & SB_RDONLY) && sb->s_bdev &&
    bdev_read_only(sb->s_bdev))
	return -EACCES;
```

## 失敗・未完了試行

初回 T0 は `dm-mod.waitfor` なしで `-ENODEV` となった。boot0 は 600 秒で timeout し、停止中の boot1/boot2 も失敗・部分試行として保持した。

T0-A1 は waitfor 追加後、dm-0 の準備、root mount、ready marker まで進んだ。しかし、inittab remount で `-EACCES` となり、boot0/boot1 は invalid だった。boot2 は部分試行として保持した。

T1-A2 の初回試行では、panic 後に SIGINT を送っても runner/QEMU が停止せず、timeout となった。driver を SIGTERM で停止するように変更し、container と QEMU の終了を確認してから、別 path で 5 回再実行した。

T3 の初回 5 回では、早期 monitor が通常の初期化行 `device-mapper: verity: sha256 using "sha256-lib"` にも一致し、data corruption または panic を確認する前に停止した。これらは未完了として保持し、同じ image を使って 422 秒の timeout で 5 回追試した。

## 結論と限界

QEMU では事前登録の tamper 拒否基準を満たした。T0 の 5 回の起動はすべて valid だった。T1/T2/T4/T5 は各 5 回とも ready に到達せず、verity error または panic を記録した。T3 の追試では 5 回すべてで中央 data block 2916 の破損と panic を確認した。製品設定は変更しない。

製品へ導入する前に、DM・DM_INIT・DM_VERITY を組み込み、`dm-mod.waitfor` を追加する必要がある。また、`/var` の扱いを決めてから inittab の remount 行を外す必要がある。更新イメージに hash tree と slot ごとの root hash を含め、`cmdline_rootfs_a.txt`、`cmdline_rootfs_b.txt`、`msd-update` を更新する作業は未実施である。boot 領域の cmdline は未署名であるため、SD を書き換えられる攻撃者は root hash も変更できる。この方式で守れるのは破損と、cmdline に手を出さない改ざんまでである。FEC と root hash 署名は試していない。実 SD と実機性能も未検証である。

kernel を復元した後の Image は元の V0 Image と一致せず、build metadata の 67 bytes・12 区間だけが異なった。追加 build は行わず、V0 の起動には元の Image を使った。

## ログと再生成

保存済み log はコミットしない。各起動の serial log は case ごとの `bootN/serial-dm-0.log` にある。生成元 CSV と SHA-256 を下表に示す。再現は上記の `make-case.sh` と `run-boots.sh` を使い、同じ case と timeout を指定する。T1 初回、T3 早期停止、T3 追試の試行も含める。QEMU panic 後に driver と container が残らないことを確認する。

| 元 CSV | SHA-256 |
|---|---|
| `V0-boottime.csv` | `ef1edeb72b1361d01ea9eadd1231cb33020da43e29615a5343b77afa1cccfab4` |
| `T0-boottime.csv`（waitfor なし） | `02a04ea734da28306332baa9989c9041bd668f937ab4d1fed6245d9db4011b7f` |
| `T0-A1-boottime.csv`（remount 失敗） | `636537572e563d5d8d2919020ded845abce409facfc296f28f83365c1d7ca6c0` |
| `T0-A2-boottime.csv` | `1da9d1d0e46f398d722cbee59dc4af9991ce94307815a9d3f5d52089be1cc2e1` |
| `T1-A2-boottime.csv`（初回） | `e5994130876ab555331cfb4c427edc9c3e4790a68b908d7cd13cccc13febdbca` |
| `T1-A2-rerun-boottime.csv` | `d1bd55cdd4f1e56fadd6a5f9ee7ea24239c7fe1d2059dcf91f081ad9d332aaf4` |
| `T2-A2-boottime.csv` | `c23013c3a8cedeabdce22c06a9eadeb4b6b7808e3f6904531f81879645112847` |
| `T3-A2-boottime.csv`（早期停止） | `d679419fb1858449af47078af897846e4158c3f1437753940ed7399a87acbae4` |
| `T3-A2-timeout-boottime.csv`（追試） | `ae078a052e34dedcd37ca91bc7919afc4acf8dc51e33678815a078a9179a67aa` |
| `T4-A2-boottime.csv` | `69d96c0a70fabc135019adf0c4ca259e450b9ca768563772f0bc7d903e1670c0` |
| `T5-A2-boottime.csv` | `e3d68dc6101f0f97b250bf56fbb3494770eaeb4e548024122a4e0e95c792c7d2` |
