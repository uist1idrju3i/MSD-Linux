# /dataのinode table同期初期化

- 状態: 測定完了。同期化の機能条件は達成、idle 0の採否基準は未達
- 日付: 2026-11-17
- 担当: Devin
- 関連: [従来の帰属測定](2026-11-15-data-first-boot-writes.md)、[書き込み台帳](../design/write-policy.md)

## 目的と仮説

`noinit_itable`でmountしてからonline growすると、新規groupのinode tableがresize中に同期初期化されるという固定kernelのsource上の判断をQEMUで確かめます。fallback mkfsにも `lazy_itable_init=0,lazy_journal_init=0` を指定します。総書き込み量をなくす変更ではありません。

## 採否の基準（測定前に記録）

変更後の3回全てで、grow後の全groupに `ITABLE_ZEROED` があり、guestのprocess一覧にext4lazyinitがなく、最初の120秒idle中のp7書き込みが0 sectorなら同期化を採用します。RAM controlとdisk positive controlがrunnerの検査に合格することも条件です。progress未実装と既存SDの未初期化tableは採否とは別の残課題です。

## 当初の条件と手順

- 基準: `origin/main` = `f132f3c4e3c1165632e4549834a930bd242e5afc`。
- 変更後: 同じ基準にS02msd-dataのmount・fallback formatとfstabの変更だけを適用します。
- warm buildの `output-openssl-lts` をdefconfigで更新し、mainと変更後を順にbuildします。以前のSquashFS sort wrapperも両条件で共通です。
- 同じwrite-inventory runnerを使い、base variant相当の未拡張imageを1 GiBに広げます。各条件3回、idleは120秒を3窓。bootとidle1を主評価とし、idle2・3も保存します。
- 生ログは `output-data-sync-itable` に保持し、大きなimageはcommitしません。版・hash・実行command・失敗試行・保存方法は完了後に追記します。

```sh
docker/msd-dev sh -c 'make -C vendor/buildroot BR2_EXTERNAL=/work O=/work/output-openssl-lts msd_cardputerzero_defconfig && make -C output-openssl-lts -j8'
# 条件ごとにimagesと.configをinput-before/input-afterへ保存してから各3回:
docker/msd-dev python3 board/cardputerzero/tools/bench/write-inventory/run.py \
  --output output-data-sync-itable/input-before \
  --run-dir output-data-sync-itable/runs/before-r1 \
  --variant before --seconds 120 --windows 3
```

## 実行した条件

上の計画原文は添付archiveの `preregistration.md` に保存しました。反復数は依頼に合わせて各3回です。各条件内は逐次実行し、beforeとafterの二つの列は並行しました。初回beforeはafterのbuildとも一部重なるため、起動時間やbuild時間の性能比較には使いません。両側ともwarm treeで、beforeはdefconfig更新により一部のpackageとkernelも再構築しました。afterは同じtreeへ製品の2ファイルの差分だけを適用して再buildしました。ccache統計は採っていません。

before build時点では文書・host testだけがdirtyで、製品sourceはmainのままでした。両側の表示versionは同じ `f132f3c-dirty` です。runner metadataの `base_commit` は両側とも基準SHAなので、afterの差分はarchiveの `product.patch` で特定します。

| 項目 | 実際に使った版・状態 |
|---|---|
| ホストkernel | Linux 7.0.0-43-generic、x86_64 |
| 開発container | Debian 13、`msd-dev:local`、image ID `47cc0b8cfd878a4fb413c376d52a2b6a9199454c97b1d2aec8df7a3a1b4a8e7d` |
| QEMU | 11.1.2、raspi3ap、512 MiB、icountなし |
| Buildroot / GCC | 2026.08.1 / Bootlin GCC 14.3.0 |
| guest kernel | 固定commitの6.18.59-v8。両側のImageは同一hash |
| mkfs / dumpe2fs | build出力のe2fsprogs 1.47.4 |
| rootfs | SquashFS、通常init。測定hookはserial経由でRAMへ転送 |

`docker/msd-dev available` はfalseでしたが、ローカルの開発imageは利用できました。新しいimageの公開・取得や依存版の変更はしていません。buildには既存のsort wrapperを共通で使いました。現在はbuilt-inのmoduleや無効なutilityを指す古いsort entryに `Cannot stat sortlist entry` が出ています。sortの対象がないという警告で、containerのツールは利用可能でした。wrapperとsort入力のhash・原文をarchiveへ保存し、比較の途中では変更していません。development update-signing keyの警告もあり、Release用imageではありません。

### 入力のSHA-256

| 入力 | SHA-256 |
|---|---|
| QEMU binary（共通） | `c8cf5be13646711580e18346dcd036c0f2a210dd90f84bf784247c5838940410` |
| Image（共通） | `c651cfd86fcb08943a863ecbc31f6fa0f2f6fea0f7c7bcd25fc8e3cdd327c261` |
| 元DTB（共通） | `f6c9ee59ccc5adb164ddba6508acc99e8038d2fe2017bd1f5fd5567af4999094` |
| QEMU用Bluetooth無効化DTB（共通） | `211465fc4c8d0da8657daacbc0fea9ed4d4aff91f7d9c2059a0fe05caa0190a5` |
| .config（共通） | `7ba1421598d13671f0087b4ef80caa103509585a32a9cbf1ae131036393621bf` |
| before rootfs | `dd289b690d027c6ec3dd529d3cfe56cddbb36e75c30fe1cf9a2173b93870fa74` |
| after rootfs | `b6d0c1dab4f94631771580f6f1f5e6d8b16449ab3f12afc0e1c4637a4e4b9ab2` |
| before sdcard.img | `df91f70ec3f351a2344e7999c2e02309b8712cf81c7ea9745c875669044ca9aa` |
| after sdcard.img | `55b2b3e01af1a37bf6e40f8213ac782ebdd0c9fca6c32b8ae472f88a8f03e541` |

実行時は各buildの直後に次のように入力を保存しました。`variant=before` は製品の2ファイルを変更する前、`variant=after` は変更後です。再現時は新しい出力先を使い、既存の入力・runを上書きしません。

```sh
variant=before # 変更後のbuild直後はafter
mkdir -p "output-data-sync-itable/input-$variant/images"
cp output-openssl-lts/.config "output-data-sync-itable/input-$variant/.config"
cp --sparse=always output-openssl-lts/images/{sdcard.img,rootfs.squashfs,Image,bcm2710-rpi-cm0.dtb} \
  "output-data-sync-itable/input-$variant/images/"
docker/msd-dev sh -c 'variant="$1"; for n in 1 2 3; do
  python3 board/cardputerzero/tools/bench/write-inventory/run.py \
    --output "output-data-sync-itable/input-$variant" \
    --run-dir "output-data-sync-itable/runs/$variant-r$n" \
    --variant "$variant" --seconds 120 --windows 3 &&
  python3 docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py \
    "output-data-sync-itable/runs/$variant-r$n" --complete || exit
done' sh "$variant"
docker/msd-dev python3 docs/experiments/2026-11-15-data-first-boot-writes-aggregate.py \
  output-data-sync-itable/runs --variants before,after
# p7の開始位置672 MiB、grow後352 MiB（sfdiskで照合）:
docker/msd-dev sh -c 'for n in 1 2 3; do
  dd if=output-data-sync-itable/runs/after-r$n/sdcard.img \
    of=output-data-sync-itable/after-r$n-p7.img bs=4M skip=168 count=88 status=none
  output-openssl-lts/host/sbin/dumpe2fs output-data-sync-itable/after-r$n-p7.img \
    >output-data-sync-itable/after-r$n-dumpe2fs.log 2>&1 || exit
done'
```

## 結果

単位は512 byte sector、対象はp7です。bootはprobe開始時の累積値、idleは各窓の前後差分です。同名の[CSV](2026-11-17-data-sync-itable.csv)に全8 device・全phaseの528行を保存しました。

| 条件 | 回 | boot | idle1 | idle2 | idle3 | boot＋idle1 |
|---|---|---|---|---|---|---|
| main | 1 | 8,648 | 8,312 | 0 | 0 | 16,960 |
| main | 2 | 8,648 | 8,304 | 0 | 0 | 16,952 |
| main | 3 | 8,648 | 8,312 | 0 | 0 | 16,960 |
| B1＋D | 1 | 16,848 | 88 | 0 | 0 | 16,936 |
| B1＋D | 2 | 16,848 | 88 | 0 | 0 | 16,936 |
| B1＋D | 3 | 16,848 | 88 | 0 | 0 | 16,936 |

mainの中央値（最小–最大）はboot 8,648（8,648–8,648）、idle1 8,312（8,304–8,312）、合計16,960（16,952–16,960）です。変更後は全3回同じ値でした。総量はほぼ維持され、書き込みの大部分がboot内へ移っています。

afterの全3回でgroup 0・1・2全てに `ITABLE_ZEROED` があり、guestのpsにはext4lazyinitがありませんでした。beforeのpsには全3回とも1 threadありました。afterのgroup 2には `INODE_UNINIT` と `ITABLE_ZEROED` が共存しています。`INODE_UNINIT` だけで未zeroと判定できないことも実測で確認しました。dumpe2fsはrunner終了後のimageを読んだもので、稼働中の全時刻を連続監視したものではありません。

### 計測器と失敗の扱い

各runでRAM controlのdisk・p7差分は0、disk positive controlは両方2,112 sectorでした。全6回のphase数・区間長・counter単調性・正の対照・完了記録hashは既存集計器で合格しました。集計器の負のfixtureを含む既存12 testも成功しています。測定失敗・中止・除外は0回です。

ただし**idle1を0とした事前の採否基準は未達**です。全3回に88 sector（45,056 byte）が残りました。table完了とthread不在は確認しましたが、この残量をjournalやmkdir等へ帰属する追試はしていません。sourceに該当writerがあるだけで原因を断定しません。

## 結論

依頼されたB1＋Dの実装は維持します。新規growのtableがzero済みとなり、観測時点のbackground threadもなくなるという機能条件は満たしました。一方、事前基準全体への合格や「起動後の書き込み解消」とは扱いません。残るidle1の88 sector、progress、既存SDの未zero tableは台帳で未対応のままです。fallback formatの実行経路はhostのstub testで検査し、QEMUの空partitionでの量・時間は未測定です。

## ログの保存

[evidence.tar.gz](2026-11-17-data-sync-itable/evidence.tar.gz)は258,045 byte、SHA-256は `a0d706ffae9efaa01bc9f3d47db6991ddb794a05b43283d89fbd7bc2b30c7df7` です。54 fileのsizeとSHA-256を内部の `evidence-manifest.json` に記録し、archiveを再読して全件照合しました。serial・raw・metadata・完了marker、build・host test・boot test log、dumpe2fs、版、入力hash、製品patch、事前計画、sort wrapperを収録しています。小さい圧縮archiveは過去のboot-slot記録と同様にこの枝へ収録し、保護対象のdata枝は変更しません。

大きなSD・rootfs・kernel imageはarchiveに入れていません。上記手順とcommit・patchで再生成できますが、warm tree由来のsort条件や生成時刻・UUID等もあるため、buildのbyte単位の再現を保証しません。各入力の内容は保存したhashで照合します。

## 未確認の点

実SDの時間・FTL・電源断、LCD上の表示、既存SDの未初期化tableの完了処理は対象外です。QEMUのsector値を実機の書き込み量と扱いません。
