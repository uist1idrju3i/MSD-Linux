# dm-verity によるrootfs改ざん拒否（QEMU）

- 状態: 完了
- 日付: 2026-10-21
- 関連: [実験計画](../research/simulation-plan.md)、#27

## 目的と仮説

dm-verityで保護したSquashFS rootfsが無改ざんで起動し、data/hash tree/root hashの改ざんでは検証エラーになることをQEMUで調べる。製品設定は変更しない。

## 結果を見る前に固定した事前登録

以下は結果を見る前に決めた条件の日本語訳である。

### Prereg v1

- 問いは、verity保護rootfsが無改ざんで起動し、改ざん後は起動拒否または破損読出し拒否となるか。
- 基準はBusyBox実験と同じ`ce932cd0e83ebf10be853c51d9ae09116aea92bb`。試験イメージのみ変更し、製品設定は変えない。
- Kernel variantには`CONFIG_BLK_DEV_DM=y`、`CONFIG_DM_VERITY=y`、`CONFIG_DM_INIT=y`を入れ、initramfsは使わない。最終`.config`のDM設定を記録する。
- Buildroot host-cryptsetupの`veritysetup format --data-block-size=4096 --hash-block-size=4096 --hash-offset=<data bytesを4096へ切り上げ> rootfs.img rootfs.img`を使い、同じrootfs partitionのSquashFS後方にhash treeを置く。合計が256 MiB以下であることを確認し、root hash、salt、data blocks、hash開始blockを記録する。
- A slotだけを試験する。cmdlineは`root=/dev/dm-0`と`dm-mod.create="vroot,,,ro,0 <data_sectors> verity 1 /dev/mmcblk0p5 /dev/mmcblk0p5 4096 4096 <data_blocks> <hash_start_block> sha256 <root_hash> <salt> 1 panic_on_corruption"`を加え、残りは変更しない。QEMUは`-no-reboot`で起動する。
- 各caseをQEMU icount `shift=0` で5回起動する。V0はverityなしの基準、T0はverity有効・無改ざん、T1はSquashFS superblock領域のbyte 0x60、T2はinode table先頭+16、T3はdata領域中央の`4096 × floor(data_blocks/2) + 123`、T4はhash tree先頭、T5はdata無改ざんでcmdlineのroot hash末尾1桁を変更する。
- 合格条件はT0が5/5 valid、T1/T2/T4/T5が各5/5でreadyなし、かつserial logにverity errorまたはverity起因panicが出ること。T3はreadyの有無と破損blockを読んだ時の挙動を記録する。ready前に当該blockを読まなければverity errorは期待しない。T0とV0のready中央値差を報告するが閾値は設けず、QEMU値として扱う。
- 制限はCardputerZeroにsecure bootがなくcmdline/boot FATが未署名であること、A/B更新でhash treeとslotごとのroot hashを`msd-update`が書く処理が未実装であること、FEC/root-hash署名未試験、実SD未模擬であること。

### Amendment 1（2026-10-21、T0初回の後、T1〜T5起動前）

初回T0ではdm-initが非同期probe中のMMC partitionより先に動き、`verity: Data device lookup failed (-ENODEV)`、続いて`Waiting for root device /dev/dm-0...`となりtimeoutした。事前登録から`dm-mod.waitfor=`を漏らしたため、T0〜T5のverity cmdlineに`dm-mod.waitfor=/dev/mmcblk0p5`を加え、他条件は変えない。初回T0のboot0 timeoutと停止時のboot1/boot2部分試行は失敗として残す。T0を5回やり直し、その後T1〜T5を各5回実行する。復元kernelの`.config`はV0と同じhashだがImageに67 byte・12範囲のbuild metadata差があった。追加buildはせず、V0は元のImageを使ったことを記録する。

### Amendment 2（2026-10-21、T0-A1のboot0/boot1後、T1〜T5起動前）

Buildroot既定の`BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW=y`が`/etc/inittab`に`::sysinit:/bin/mount -o remount,rw /`を追加する。mmcblk上ではread-only SquashFSへのremountは実質何もせず成功するが、read-only dm deviceでは`reconfigure_super()`が`-EACCES`を返し、serial error checkにより起動がinvalidになる。dm-0の準備、root mount、ready markerまで進んでおりverity自体は動作していた。

T0〜T5の試験用rootfsに限り、veritysetup formatの前にこの1行だけを削除する。削除前に一致1件、削除後に0件をassertし、新しいroot hash/saltを得る。T1〜T3のoffsetは新imageのsuperblockから再計算する。V0には変更しない。T0-A1は失敗試行として保持し、T0を5回、その後T1〜T5を各5回実行する。製品での削除は`/var`の扱いを決めた後の別taskとする。

## 条件・format値・再現

| 項目 | 値 |
|---|---|
| 基準HEAD / Buildroot | `ce932cd0e83ebf10be853c51d9ae09116aea92bb` / `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| Buildroot / Linux / target GCC | 2026.08 / 6.18.57-v8 / 14.3.0 |
| QEMU / mksquashfs / veritysetup | QEMU 11.1.2 / mksquashfs 4.7.5 / veritysetup 2.8.7 |
| Host OS | 正確な版は実験時の証跡に未記録 |
| 出力先・再利用状態 | `O=output`。既存出力を再利用。dm用kernelはvariant configを適用し、復元後の追加buildは行わなかった |
| Linux config SHA-256 | `409a020d493d9e049b49b377421f21309f06382851b4b6910804a2caeb00426d` |
| Buildroot config SHA-256 | `8f8d8ef964dd6c51bd7966a296a660aa33c3b94e25e06bb8c5605e3d13a9bc3e` |
| T0〜T5 Image / DTB SHA-256 | `c1d775efd05b21e1129f21a4c9563f0939f3dd3c3d0810c8c2dbd3eb8bab3792` / `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` |
| V0 Image SHA-256 | `a9d2167486208eea88d75a53ceca83e9e243a3a6af7c6c00db71bb376d50ea47`（元Image） |
| Format | data blocks 5833、hash blocks 47、offset 23,891,968、hash start block 5834、data sectors 46,664 |
| Root hash / salt | `1cb37caeb790095844ee096064ef64748b6ce3c9a63926c1d71b88eb0fd165cd` / `c9eab80204ec24fb273d841ea7644d7bc0602bd3af8f29dd648b0ba74cde8c2b` |
| Timeout | tamper boot 422秒。T0でreadyまでのhost時間最大302秒に120秒を加え、最初のtamper起動より前にdeviationsへ記録。 |

再現例。変数は各利用環境で設定する。rootfsのremount行を検査・削除してからformatし、tamperはformat後に実行する。

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

V0は既存boottime runnerで初回1回と通常4回起動する。たとえば`docker/msd-dev board/cardputerzero/tools/bench/boottime/run-boottime.sh --variant V0 --runs 4 --mode icount --csv "$CASE_DIR/V0-boottime.csv" --log-dir "$CASE_DIR/V0-boottime"`とする。T0〜T5の一行削除、format、tamper offsetsは`make-case.sh`にまとめた。T1 offsetは96 (`0x28→0x29`)、T2は新SquashFS superblockのinode table start 23,845,319に16を加えた23,845,335 (`0x30→0x31`)、T3は11,944,059 (`0xaa→0xab`)、T4は23,896,064 (`0x06→0x07`)、T5はroot hash末尾`d→0`。早期monitorの誤判定を再現する場合はT3を`--expected verity-error`で走らせる。上記の`ready`指定は誤判定を避けた422秒追試である。

## 結果

T0-A2は5/5 valid、ready/login到達。ready中央値は4.074023秒。V0は5/5 valid、中央値3.747029秒。差は0.326994秒（+8.7%）。T0はV0とinittabの1行が異なるため単独差ではない。いずれもQEMUの値で、実機の負担見積りには使わない。

| Case | 起動結果 | ready / tamper error |
|---|---|---|
| V0 | 5/5 valid | ready中央値3.747029秒 |
| T0-A2 | 5/5 valid | ready中央値4.074023秒 |
| T1-A2 | 5/5 readyなし | `device-mapper: verity: data block 0 is corrupted`、verity panic |
| T2-A2 | 5/5 readyなし | `device-mapper: verity: data block 5821 is corrupted`、verity panic |
| T3-A2追試 | 5/5 readyなし（422秒timeout） | `data block 2916 is corrupted`、`Kernel panic - not syncing: dm-verity device corrupted` |
| T4-A2 | 5/5 readyなし | `device-mapper: verity: metadata block 5834 is corrupted`、verity panic |
| T5-A2 | 5/5 readyなし | `device-mapper: verity: metadata block 5834 is corrupted`、verity panic |

T1/T2/T4/T5の起動はpanicでrunnerがstatus 1を返した。T3追試はpanic後もQEMUが終了しないため、事前に定めた422秒timeoutで終了status 124となった。これらはready successではない。T3の中央blockを読んだ時点でverity error/panicを確認した。

| Case | `rootfs.img` SHA-256 | `sdcard.img` SHA-256 |
|---|---|---|
| T0-A2 | `87ddb143494a73bf73e9760a34dbf8adeb8eb66135e1a47835fe0d71ba2d6594` | `570b9669061f38777f9c91984a6c904d262d3a96b90c73b5da7eb846d730b75f` |
| T1-A2 | `fad841f472af545c6dcaf8ff67e450a09868198aeba7e2d1f3f3ff40b4c60010` | `98e82ed8e55bd440e57d5dc655c9699f417b8b806af8dae96a1a6bdb82ef4231` |
| T2-A2 | `a6c505aaa797e9e330f0a8168ee193776f0f29ebe5c2b8815ea38e9d7f090007` | `c4a6b0b4b90ab327635e0818013d92daa47abaf04a27b94f63d819d20aa26447` |
| T3-A2 | `40cd3f1685aff05a517b1e5851fb05b050b3d46c6a10a70729f3f3bc2a685e72` | `7aefb8fc0696971d812c97305877573dc431906a2e8bb248c8985879cfed3067` |
| T4-A2 | `67007b6a37d43e7f092619cbd6c40a931f31276f48e860ef6bae02138ac717f4` | `3f81e0c1184e928dd5d191de4e17886a589eac12fa35ea367e46302e71fe5ef5` |
| T5-A2 | T0-A2と同じ | T0-A2と同じ |

## 副次の発見: rw remount

`BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW=y`でBuildrootが生成するinittabのremount行は、通常のSquashFS rootではread-onlyのままで何も変えない。read-only dm tableでは拒否を起動エラーとして検出した。Linux `fs/super.c`の`reconfigure_super()`は次の条件で`-EACCES`を返す。

```c
if (!(fc->sb_flags & SB_RDONLY) && sb->s_bdev &&
    bdev_read_only(sb->s_bdev))
	return -EACCES;
```

## 失敗・未完了試行

- 初回T0は`dm-mod.waitfor`なしで`-ENODEV`。boot0は600秒timeout、停止中のboot1/boot2も失敗・部分試行として保持した。
- T0-A1はwaitfor追加後、dm-0準備・root mount・ready markerまで進んだが、inittab remountで`-EACCES`となりboot0/boot1がinvalid。boot2は部分試行。
- T1-A2初回はpanic後にSIGINTでrunner/QEMUが止まらずtimeout。driverをSIGTERM停止へ変更し、containerとQEMU終了を確認してから別pathで5回再実行した。
- T3初回5回は早期monitorが`device-mapper: verity: sha256 using "sha256-lib"`という通常の初期化行にも一致し、data corruption/panic前に停止した。これらは未完了として保持し、同じimageを422秒timeoutで5回追試した。

## 結論と限界

QEMUでは事前登録のtamper拒否基準を満たした。T0は5/5 valid、T1/T2/T4/T5は5/5でreadyなしとverity error/panic、T3追試は5/5で中央data block 2916の破損とpanicを確認した。製品設定は変更しない。

製品へ入れる前に、DM・DM_INIT・DM_VERITYを組み込み、`dm-mod.waitfor`を追加し、`/var`の扱いを決めてからinittabのremount行を外す必要がある。更新イメージへhash treeとslotごとのroot hashを含め、`cmdline_rootfs_a.txt`、`cmdline_rootfs_b.txt`、`msd-update`を更新する作業は未実施。boot領域cmdlineは未署名のため、SDを書き換えられる攻撃者はroot hashも変更できる。守れるのは破損とcmdlineに手を出さない改ざんまで。FECとroot hash署名は試していない。実SD・実機性能も未検証。

kernelを復元した後のImageは元のV0 Imageと一致せず、build metadataだけ67 byte・12範囲が異なる。追加buildは行わず、V0起動には元のImageを使った。

## ログと再生成

保存済みlogはコミットしない。各起動のserial logはcaseごとの`bootN/serial-dm-0.log`で、生成元CSVとSHA-256を次に示す。再現は上記の`make-case.sh`、`run-boots.sh`と同じcase・timeoutで行う。T1初回、T3早期停止、T3追試の試験回数も含める。QEMU panic後もdriver/containerが残らないことを確認する。

| 元CSV | SHA-256 |
|---|---|
| `V0-boottime.csv` | `ef1edeb72b1361d01ea9eadd1231cb33020da43e29615a5343b77afa1cccfab4` |
| `T0-boottime.csv`（waitforなし） | `02a04ea734da28306332baa9989c9041bd668f937ab4d1fed6245d9db4011b7f` |
| `T0-A1-boottime.csv`（remount失敗） | `636537572e563d5d8d2919020ded845abce409facfc296f28f83365c1d7ca6c0` |
| `T0-A2-boottime.csv` | `1da9d1d0e46f398d722cbee59dc4af9991ce94307815a9d3f5d52089be1cc2e1` |
| `T1-A2-boottime.csv`（初回） | `e5994130876ab555331cfb4c427edc9c3e4790a68b908d7cd13cccc13febdbca` |
| `T1-A2-rerun-boottime.csv` | `d1bd55cdd4f1e56fadd6a5f9ee7ea24239c7fe1d2059dcf91f081ad9d332aaf4` |
| `T2-A2-boottime.csv` | `c23013c3a8cedeabdce22c06a9eadeb4b6b7808e3f6904531f81879645112847` |
| `T3-A2-boottime.csv`（早期停止） | `d679419fb1858449af47078af897846e4158c3f1437753940ed7399a87acbae4` |
| `T3-A2-timeout-boottime.csv`（追試） | `ae078a052e34dedcd37ca91bc7919afc4acf8dc51e33678815a078a9179a67aa` |
| `T4-A2-boottime.csv` | `69d96c0a70fabc135019adf0c4ca259e450b9ca768563772f0bc7d903e1670c0` |
| `T5-A2-boottime.csv` | `e3d68dc6101f0f97b250bf56fbb3494770eaeb4e548024122a4e0e95c792c7d2` |
