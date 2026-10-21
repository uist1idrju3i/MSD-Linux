# BusyBox の静的リンクと applet 削減（QEMU）

- 状態: 完了
- 日付: 2026-10-21
- 関連: [実験計画](../research/simulation-plan.md)、#27

## 目的と仮説

BusyBox を静的リンクした場合と、起動に必要な applet だけを残した場合の起動時間、`/bin/true` の反復時間、バイナリ・rootfs サイズを比較する。製品設定の変更は決めない。

## 結果を見る前に固定した事前登録

以下は結果を見る前に決めた条件の日本語訳である。

### Prereg v2

- 基準は非 PPD の `ce932cd0e83ebf10be853c51d9ae09116aea92bb`。製品設定は変更せず、各variantは試験用イメージとする。
- Step 0では判定前に applet を調べる。静的な一覧は `etc/init.d/*`、`etc/inittab`、`usr/sbin/msd-*`、`usr/libexec/msd/*`、`usr/share/udhcpc/*`、`etc/network/*` のコマンド語をBusyBox appletへ対応づける。動的な一覧は `sched:sched_process_exec` と4 MiB trace bufferを有効にしたQEMU起動で取得し、S99 hookからtraceを出す。`msd-update` のhost test相当をhookから実行する必要はない。Nは静的・動的な集合と、inittabが使う `sh`・login/gettyの連鎖の和とする。
- B0は基準、B1は `CONFIG_STATIC=y` のみ追加、B2はNにあるappletだけを残す。B2では新しい `busybox.links` にない古いBusyBox symlinkを削除し、残るlinkを検査する。
- 各variantを初回1回と通常5回起動する。`QEMU_ICOUNT=shift=0` と既存のboottime harnessを使う。初回S99 hookは `id -u root`、`ls /`、`date`、`ps`、`mount`、`/usr/sbin/msd-update --help || true`、200回の`/bin/true`を`date +%s%N`で測る。各probeのstatusを記録し、traceを出す。
- 指標はBusyBox bytes、applet link数、`rootfs.squashfs` bytes、ready時間の通常5回中央値、1000回loop時間の通常5回中央値、起動のvalidityとtest-boot・test-ab・test-powerfailの結果とする。起動はready marker、login prompt、serial allowlist検査で判定する。
- 効果を主張する基準は、readyまたはloop中央値が5%以上かつA/Aの0.85%の2倍を超えること。サイズは絶対値と相対値を記録する。B1/B2はserialの「applet not found」「not found」「NSS error」、またはいずれかのprobe失敗があれば無効とする。Nを直して再実行する場合はB2bとして別記録にする。
- 制限はQEMU TCG/icountで実機CPU・実SDを模擬しないこと、静的glibc NSSはrootとローカルファイルでのみ確認すること。QEMU結果だけで製品採用を決めない。対話・保守用appletの範囲は利用者が決める。

### Amendment 1（2026-10-21、B1/B2結果を見る前）

B0の初回hookが対象BusyBoxの `date` に `FEATURE_DATE_NANO` がなく、`date +%s%N` が `%N` を展開せず、算術でゼロ除算になった。これは事前登録の誤りでvariantの効果ではない。B0の初回試行は失敗として残す。B0を初回1回と通常5回で再実行し、全variantで同一のhookを使う。計時は `/proc/uptime` の先頭値（10 ms単位）を使った1000回の `/bin/true` とする。各probeは `=bb=\t<name>\trc\t<rc>` を出し、失敗してもhookを止めない。trace dumpは最後に必ず実行する。

## 条件と再現手順

| 項目 | 値 |
|---|---|
| 基準HEAD / Buildroot | `ce932cd0e83ebf10be853c51d9ae09116aea92bb` / `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| QEMU / mksquashfs | QEMU 11.1.2 / mksquashfs 4.7.5 |
| Buildroot / Linux / target GCC | 2026.08 / 6.18.57-v8 / 14.3.0 |
| Buildroot BusyBox | 1.38.0 |
| Host OS | 正確な版は実験時の証跡に未記録 |
| 出力先・再利用状態 | `O=output`。既存出力を再利用し、B1/B2でBusyBoxを再configure/rebuild |
| 条件 | B0基準、B1は`CONFIG_STATIC=y`のみ、B2はneed set Nの63 applet |
| 固定条件 | QEMU icount `shift=0`、初回1回＋通常5回、試験用rootfsのみ変更 |

基準出力は既存のincremental buildを使用した。再現時の例を示す。

```sh
docker/msd-dev make -C output
docker/msd-dev board/cardputerzero/tools/bench/busybox/make-variant.sh B0 "$PWD/output" "$PWD/board/cardputerzero/tools/bench/busybox/S99zz-bbprobe" "$PWD/out/B0"
# B1ではBusyBoxのCONFIG_STATIC=yだけを設定してBuildrootのBusyBoxを再configure/rebuild後、同じscriptを使う。
docker/msd-dev board/cardputerzero/tools/bench/busybox/make-variant-b2.sh "$PWD/output" "$PWD/output/build/busybox-1.38.0/busybox.links" "$PWD/board/cardputerzero/tools/bench/busybox/S99zz-bbprobe" "$PWD/out/B2"
# 初回1回＋通常5回
docker/msd-dev env OUTPUT_DIR="$PWD/output" board/cardputerzero/tools/bench/busybox/run-boots.sh --variant B0-A1 --image "$PWD/out/B0/sdcard.img" --runs 5 --csv "$PWD/out/B0.csv" --log-dir "$PWD/out/B0"
```

この記録では既存 `output/` を再利用した。B1/B2のBuildroot reconfigure後に測定し、各caseごとにbuild、確認、bootの順で行った。B2の古いlinkを落とすpath一覧は `B2-stale-symlinks.tsv`、`busybox.links`との照合表は `B2-link-resolution.tsv` に相当する。repository helperは実験版を汎用化し、`output`と出力先を引数化した。画像作成・link検査の処理は同じである。

## 結果

QEMU icountの値であり、実機の秒数ではない。通常起動の中央値はrepeat 1〜5から算出した。

| Variant | BusyBox bytes | applet links | squashfs bytes | ready生値（秒） | ready中央値（秒） | 1000回`/bin/true`生値（秒） | loop中央値（秒） |
|---|---:|---:|---:|---|---:|---|---:|
| B0-A1 | 870,848 | 285 | 23,891,968 | 3.623070, 3.031650, 3.047606, 3.046419, 3.054205, 3.060156 | 3.047606 | 1.24, 1.25, 1.25, 1.26, 1.26, 1.25 | 1.25 |
| B1 | 1,831,360 | 285 | 24,363,008 | 3.519347, 3.026835, 3.011048, 3.022779, 2.999002, 3.080762 | 3.022779 | 0.82, 0.82, 0.82, 0.82, 0.81, 0.82 | 0.82 |
| B2 | 509,960 | 63 | 23,642,112 | 3.514489, 3.001435, 3.043712, 2.998117, 3.013158, 3.007391 | 3.007391 | 1.02, 1.03, 1.07, 1.05, 1.02, 1.02 | 1.03 |

全18起動はvalidでreadyとloginに到達した。test-abとpowerfail smokeも3条件でpass。通常5回のready中央値はB0からB1で3.048→3.023秒（−0.8%）、B2で3.007秒（−1.3%）。どちらも5%かつA/Aの2倍超の基準には届かない。1000回loopは1.25→0.82秒（−34%）、B2は1.03秒（−18%）で基準を満たす。

| Variant | BusyBox SHA-256 | 試験rootfs SHA-256 | 試験SD SHA-256 | Image SHA-256 |
|---|---|---|---|---|
| B0-A1 | `55dcf2940e90d83539b57c970955f784c4eaf1ed98b22270b96e8dc5339b5e8d` | `f6061c793faa83dcec9a93a827cc5e5a747fe649ad683bfd8db2ed6e1afdaa41` | `6cf2232aeba4e72a6db067d0f52b3c545d33026b4321f53cbd6c81ab9f418fbc` | `a9d2167486208eea88d75a53ceca83e9e243a3a6af7c6c00db71bb376d50ea47` |
| B1 | `997d554a56f95317019403c429320b0ccb59752781cf53ce175430e404657da7` | `d5bf5218ac69838e8d0b6a9b15f55782e552e6d500b6aac11bf311f5b21fff60` | `9cea85d47fa2ecf47f87070e99fe9d189f60681713f91889b4d39b642818a83d` | 同上 |
| B2 | `b513e6569276e0bd21cc8d0d00fe7f36fc32affb57f3487f51d1ec6213fb0bdd` | `6553f565876b394080a0df75eae2a40782c8562466788ecd4e97e46c5a90d494` | `7c08793c9c8f3ce31f9df4c11e5bfaaf098a20ab4f873d5d4c04de0ee4efc13c` | 同上 |

DTB SHA-256は全条件で`e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f`。B2 BusyBox config SHA-256は`fc5448a1654c20df8e52cac0155b4a4c0ad237837765e2ff74c24c008493d147`。B2は63 linkがNと一致し、古いsymlink 203件を削除した。Nは静的なcommand-word inventory、必須link・login/getty連鎖、動的traceの和である。

### B2 build warning 19件

全て既存の`-Wunused-result`などで、Nに含まれるappletまたは共通実装に関係する。ビルドは成功した。実行への影響がないとは判断していない。

```text
archival/libarchive/data_extract_all.c:246:25: warning: ignoring return value of 'chown' declared with attribute 'warn_unused_result' [-Wunused-result]
libbb/appletlib.c:641:17: warning: ignoring return value of 'setgid' declared with attribute 'warn_unused_result' [-Wunused-result]
libbb/appletlib.c:642:17: warning: ignoring return value of 'setuid' declared with attribute 'warn_unused_result' [-Wunused-result]
loginutils/login.c:558:9: warning: ignoring return value of 'fchown' declared with attribute 'warn_unused_result' [-Wunused-result]
editors/sed.c:1647:25: warning: ignoring return value of 'fchown' declared with attribute 'warn_unused_result' [-Wunused-result]
loginutils/getty.c:224:17: warning: ignoring return value of 'fchown' declared with attribute 'warn_unused_result' [-Wunused-result]
modutils/modutils.c:109:1: warning: function may return address of local variable [-Wreturn-local-addr]
miscutils/watchdog.c:161:17: warning: ignoring return value of 'write' declared with attribute 'warn_unused_result' [-Wunused-result]
miscutils/watchdog.c:71:9: warning: ignoring return value of 'write' declared with attribute 'warn_unused_result' [-Wunused-result]
include/libbb.h:236:28: warning: ignoring return value of 'fgets_unlocked' declared with attribute 'warn_unused_result' [-Wunused-result]
include/libbb.h:236:28: warning: ignoring return value of 'fgets_unlocked' declared with attribute 'warn_unused_result' [-Wunused-result]
include/libbb.h:236:28: warning: ignoring return value of 'fgets_unlocked' declared with attribute 'warn_unused_result' [-Wunused-result]
include/libbb.h:236:28: warning: ignoring return value of 'fgets_unlocked' declared with attribute 'warn_unused_result' [-Wunused-result]
util-linux/mdev.c:787:33: warning: ignoring return value of 'chown' declared with attribute 'warn_unused_result' [-Wunused-result]
util-linux/mdev.c:790:33: warning: ignoring return value of 'symlink' declared with attribute 'warn_unused_result' [-Wunused-result]
util-linux/mdev.c:797:41: warning: ignoring return value of 'symlink' declared with attribute 'warn_unused_result' [-Wunused-result]
shell/ash.c:11390:25: warning: ignoring return value of 'write' declared with attribute 'warn_unused_result' [-Wunused-result]
shell/ash.c:11394:25: warning: ignoring return value of 'write' declared with attribute 'warn_unused_result' [-Wunused-result]
shell/ash.c:11416:41: warning: ignoring return value of 'write' declared with attribute 'warn_unused_result' [-Wunused-result]
```

対象は`tar`、共通のapplet実装、`login`、`sed`、`getty`、modutils、`watchdog`、`ifconfig`/iprouteで使う共通header、`mdev`、`ash`。いずれもNの範囲に関係する。

V0 dm-verity基準のready中央値3.747029秒とB0-A1の3.047606秒の差は約0.699秒である。両者のImageは同一。保存ログでは両hookともready markerの後に始まる。rootfsとhookは異なるため、それらの差の寄与は分離できず、原因は不明。

製品の設定は変えない。appletの保守用・対話用の範囲は利用者が決める。静的リンクのglibc NSSはrootとローカルファイルでのみ確認した。B1とB2の組み合わせは試していない。

## 失敗した試行

- B0の最初のhookは`date +%N`の誤りで終了status 2となり、loopとtrace dumpに到達しなかった。初回B0の起動ログを失敗として保持し、Amendment 1のhookでB0を取り直した。
- B1はImage symlink不足でQEMU開始前に失敗した。修正後の6起動を別のCSVに保存した。
- B2は初回のBusyBox config適用が失敗したため、その試行を保持し、retry1を実施した。

## 結論と限界

B1のready差は基準未達、1000回loopは基準達成。BusyBoxは870,848から1,831,360 bytes（+110%）、squashfsは23,891,968から24,363,008 bytes（+2.0%）。B2のready差は基準未達、loopは基準達成。BusyBoxは509,960 bytes（−41%）、squashfsは23,642,112 bytes（−1.0%）。製品設定は変更しない。QEMU icountの値であり、実機の速度・SD特性は未確認。

## ログと再生成

保存済みlogはコミットしない。raw値は同名CSVに転記した。主要な元ファイルとSHA-256は次のとおり。各起動のserial logは`<variant>-boottime/bootN/serial-mmcblk0p5.log`で、下表のboottime CSVの`log_sha256`行から対応するhashを確認できる。再現手順のbuild・boot commandで再生成する。V0とB0-A1の約0.7秒差の原因は不明。

| 元CSV | SHA-256 |
|---|---|
| `B0-boottime.csv`（初回hook失敗） | `a80648254d3dedd1b68acff7ab9003d204ca9936c398bedc0406de1bd3b8d614` |
| `B0-A1-boottime.csv` | `2ef40a75bece5189e7506d265db50b05f289c56f9c27e30634434ef75ac97afd` |
| `B1-boottime-retry1.csv` | `84b1245fbb5c8df746e411555820f1f6ac77ad8277248e6d2b575f2c57b2d3ba` |
| `B2-boottime.csv` | `f7930cc10c7bc44d1a655726ad9002de981a4f7234b3000571946840b81e12e1` |
