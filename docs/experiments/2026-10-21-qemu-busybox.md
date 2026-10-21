# BusyBox の静的リンクと applet 削減（QEMU）

この実験は完了した。実施日は 2026-10-21 で、関連する文書は [実験計画](../research/simulation-plan.md) と #27 である。

## 目的と仮説

BusyBox を静的リンクした場合と、起動に必要な applet だけを残した場合の起動時間、`/bin/true` の反復時間、バイナリと rootfs のサイズを比較する。製品設定は変更しない。

## 結果を見る前に固定した事前登録

以下は、結果を見る前に決めた条件を日本語に訳したものである。

### Prereg v2

基準には非 PPD の `ce932cd0e83ebf10be853c51d9ae09116aea92bb` を使い、製品設定は変更しない。各 variant は試験用イメージとする。

Step 0 では、判定の前に applet を調べる。静的な一覧は `etc/init.d/*`、`etc/inittab`、`usr/sbin/msd-*`、`usr/libexec/msd/*`、`usr/share/udhcpc/*`、`etc/network/*` にあるコマンド語を BusyBox applet に対応づけて作成する。動的な一覧は `sched:sched_process_exec` と 4 MiB の trace buffer を有効にした QEMU 起動で取得し、S99 hook から trace を出す。`msd-update` の host test 相当を hook から実行する必要はない。N は静的・動的な集合と、inittab が使う `sh` と login/getty の連鎖の和とする。

B0 は基準とし、B1 では `CONFIG_STATIC=y` のみを追加し、B2 では N にある applet だけを残す。B2 では新しい `busybox.links` にない古い BusyBox symlink を削除し、残る link を検査する。

各 variant は初回に 1 回、続けて通常起動を 5 回行う。`QEMU_ICOUNT=shift=0` と既存の boottime harness を使う。初回の S99 hook では `id -u root`、`ls /`、`date`、`ps`、`mount`、`/usr/sbin/msd-update --help || true` を実行し、200 回の `/bin/true` を `date +%s%N` で計時する。各 probe の status を記録し、trace を出す。

指標には BusyBox の bytes 数、applet link 数、`rootfs.squashfs` の bytes 数、ready 時間の通常 5 回の中央値、1000 回 loop 時間の通常 5 回の中央値、起動の validity、test-boot・test-ab・test-powerfail の結果を使う。起動の有効性は ready marker、login prompt、serial allowlist 検査で判定する。

効果を主張する基準は、ready または loop の中央値が 5 % 以上かつ A/A の 0.85 % の 2 倍を超えることとする。サイズは絶対値と相対値を記録する。B1/B2 は、serial に「applet not found」「not found」「NSS error」が出る場合、またはいずれかの probe が失敗した場合に無効とする。N を直して再実行する場合は、B2b として別に記録する。

この実験の制限は、QEMU TCG/icount が実機 CPU と実 SD を模擬しない点にある。静的 glibc NSS は root とローカルファイルでのみ確認する。QEMU の結果だけで製品採用を決めない。保守・対話用 applet の範囲は利用者が決める。

### Amendment 1（2026-10-21、B1/B2 結果を見る前）

B0 の初回 hook が使った対象 BusyBox の `date` には `FEATURE_DATE_NANO` がなく、`date +%s%N` は `%N` を展開しなかった。その値を使った算術でゼロ除算が起きた。これは事前登録の誤りであり、variant の効果ではないため、B0 の初回試行は失敗として残す。B0 は初回に 1 回、続けて通常起動を 5 回やり直し、全 variant で同じ hook を使う。計時には `/proc/uptime` の先頭値（10 ms 単位）を使い、`/bin/true` を 1000 回実行する。各 probe は `=bb=\t<name>\trc\t<rc>` を出し、失敗しても hook を止めない。trace dump は最後に必ず実行する。

## 条件と再現手順

| 項目 | 値 |
|---|---|
| 基準 HEAD / Buildroot | `ce932cd0e83ebf10be853c51d9ae09116aea92bb` / `d6061d653d7fb215c2409c59e4bfad1b9d677215` |
| QEMU / mksquashfs | QEMU 11.1.2 / mksquashfs 4.7.5 |
| Buildroot / Linux / target GCC | 2026.08 / 6.18.57-v8 / 14.3.0 |
| Buildroot BusyBox | 1.38.0 |
| Host OS | 正確な版は実験時の証跡に未記録 |
| 出力先・再利用状態 | `O=output`。既存出力を再利用し、B1/B2 で BusyBox を再 configure/rebuild |
| 条件 | B0 は基準設定、B1 は `CONFIG_STATIC=y` のみ、B2 は need set N に含まれる 63 applet のみ |
| 固定条件 | QEMU icount `shift=0`、初回 1 回＋通常 5 回、試験用 rootfs のみ変更 |

基準出力は既存の incremental build を使用した。再現時の例を示す。

```sh
docker/msd-dev make -C output
docker/msd-dev board/cardputerzero/tools/bench/busybox/make-variant.sh B0 "$PWD/output" "$PWD/board/cardputerzero/tools/bench/busybox/S99zz-bbprobe" "$PWD/out/B0"
# B1 では BusyBox の CONFIG_STATIC=y だけを設定して Buildroot の BusyBox を再 configure/rebuild した後、同じ script を使う。
docker/msd-dev board/cardputerzero/tools/bench/busybox/make-variant-b2.sh "$PWD/output" "$PWD/output/build/busybox-1.38.0/busybox.links" "$PWD/board/cardputerzero/tools/bench/busybox/S99zz-bbprobe" "$PWD/out/B2"
# 初回 1 回＋通常 5 回
docker/msd-dev env OUTPUT_DIR="$PWD/output" board/cardputerzero/tools/bench/busybox/run-boots.sh --variant B0-A1 --image "$PWD/out/B0/sdcard.img" --runs 5 --csv "$PWD/out/B0.csv" --log-dir "$PWD/out/B0"
```

この記録では既存の `output/` を再利用した。B1/B2 は Buildroot の reconfigure 後に測定し、各 case で build、確認、boot の順に進めた。B2 で削除した古い link の path 一覧は `B2-stale-symlinks.tsv` に、`busybox.links` との照合表は `B2-link-resolution.tsv` に記録した。repository helper では実験版を汎用化し、`output` と出力先を引数にした。画像作成と link 検査の処理は実験版から変更していない。

## 結果

QEMU icount の値であり、実機の秒数ではない。通常起動の中央値は repeat 1〜5 から算出した。

| Variant | BusyBox bytes | applet links | squashfs bytes | ready 生値（秒） | ready 中央値（秒） | 1000 回 `/bin/true` 生値（秒） | loop 中央値（秒） |
|---|---:|---:|---:|---|---:|---|---:|
| B0-A1 | 870,848 | 285 | 23,891,968 | 3.623070, 3.031650, 3.047606, 3.046419, 3.054205, 3.060156 | 3.047606 | 1.24, 1.25, 1.25, 1.26, 1.26, 1.25 | 1.25 |
| B1 | 1,831,360 | 285 | 24,363,008 | 3.519347, 3.026835, 3.011048, 3.022779, 2.999002, 3.080762 | 3.022779 | 0.82, 0.82, 0.82, 0.82, 0.81, 0.82 | 0.82 |
| B2 | 509,960 | 63 | 23,642,112 | 3.514489, 3.001435, 3.043712, 2.998117, 3.013158, 3.007391 | 3.007391 | 1.02, 1.03, 1.07, 1.05, 1.02, 1.02 | 1.03 |

全 18 回の起動は valid となり、ready marker と login prompt に到達した。3 条件すべてで test-ab と電源断 smoke test も pass した。通常起動 5 回の ready 中央値は、B0 の 3.048 秒から B1 の 3.023 秒へ（−0.8 %）、B2 では 3.007 秒（−1.3 %）となった。どちらも 5 % かつ A/A の 2 倍を超える基準には届かなかった。1000 回の loop 時間は B0 の 1.25 秒から B1 の 0.82 秒へ（−34 %）、B2 は 1.03 秒（−18 %）となり、基準を満たした。

| Variant | BusyBox SHA-256 | 試験 rootfs SHA-256 | 試験 SD SHA-256 | Image SHA-256 |
|---|---|---|---|---|
| B0-A1 | `55dcf2940e90d83539b57c970955f784c4eaf1ed98b22270b96e8dc5339b5e8d` | `f6061c793faa83dcec9a93a827cc5e5a747fe649ad683bfd8db2ed6e1afdaa41` | `6cf2232aeba4e72a6db067d0f52b3c545d33026b4321f53cbd6c81ab9f418fbc` | `a9d2167486208eea88d75a53ceca83e9e243a3a6af7c6c00db71bb376d50ea47` |
| B1 | `997d554a56f95317019403c429320b0ccb59752781cf53ce175430e404657da7` | `d5bf5218ac69838e8d0b6a9b15f55782e552e6d500b6aac11bf311f5b21fff60` | `9cea85d47fa2ecf47f87070e99fe9d189f60681713f91889b4d39b642818a83d` | 同上 |
| B2 | `b513e6569276e0bd21cc8d0d00fe7f36fc32affb57f3487f51d1ec6213fb0bdd` | `6553f565876b394080a0df75eae2a40782c8562466788ecd4e97e46c5a90d494` | `7c08793c9c8f3ce31f9df4c11e5bfaaf098a20ab4f873d5d4c04de0ee4efc13c` | 同上 |

DTB の SHA-256 は全条件で `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f` だった。B2 の BusyBox config の SHA-256 は `fc5448a1654c20df8e52cac0155b4a4c0ad237837765e2ff74c24c008493d147` だった。B2 の 63 個の link は N と一致し、古い symlink 203 件を削除した。N は静的な command-word inventory、必須 link と login/getty の連鎖、動的 trace の和である。

### B2 build warning 19 件

警告はすべて既存の `-Wunused-result` などであり、N に含まれる applet または共通実装に関係する。ビルドは成功したが、実行への影響は判断していない。

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

警告の対象は `tar`、共通 applet 実装、`login`、`sed`、`getty`、modutils、`watchdog`、`ifconfig`/iproute で使う共通 header、`mdev`、`ash` であり、いずれも N の範囲に関係する。

V0 の dm-verity 基準における ready 中央値は 3.747029 秒であり、B0-A1 の 3.047606 秒より約 0.699 秒長かった。両者の Image は同一だった。保存ログでは両方の hook が ready marker の後に始まっていた。rootfs と hook は異なるため、その差の寄与は分離できず、原因は不明である。

製品設定は変更しない。保守用・対話用 applet の範囲は利用者が決める。静的リンクの glibc NSS は root とローカルファイルでのみ確認した。B1 と B2 の組み合わせは試していない。

## 失敗した試行

B0 の初回 hook は `date +%N` の誤りにより終了 status 2 となり、loop と trace dump に到達しなかった。初回 B0 の起動ログは失敗として保持し、Amendment 1 の hook で B0 を再測定した。

B1 は Image symlink が不足し、QEMU の起動前に失敗した。修正後の 6 回の起動は別の CSV に保存した。

B2 は初回の BusyBox config 適用に失敗したため、その試行を保持したうえで retry1 を実施した。

## 結論と限界

B1 の ready 時間は基準に届かなかったが、1000 回の loop 時間は基準を満たした。BusyBox は 870,848 bytes から 1,831,360 bytes（+110 %）となり、squashfs は 23,891,968 bytes から 24,363,008 bytes（+2.0 %）となった。B2 の ready 時間は基準に届かなかったが、loop 時間は基準を満たした。BusyBox は 509,960 bytes（−41 %）、squashfs は 23,642,112 bytes（−1.0 %）だった。製品設定は変更しない。QEMU icount の値であり、実機の速度と SD の特性は未確認である。

## ログと再生成

保存済み log はコミットしない。raw 値は同名の CSV に転記した。主要な元ファイルと SHA-256 を下表に示す。各起動の serial log は `<variant>-boottime/bootN/serial-mmcblk0p5.log` にあり、対応する hash は下表の boottime CSV の `log_sha256` 行で確認できる。再現手順の build と boot command でログを再生成する。V0 と B0-A1 の約 0.7 秒差の原因は不明である。

| 元 CSV | SHA-256 |
|---|---|
| `B0-boottime.csv`（初回 hook 失敗） | `a80648254d3dedd1b68acff7ab9003d204ca9936c398bedc0406de1bd3b8d614` |
| `B0-A1-boottime.csv` | `2ef40a75bece5189e7506d265db50b05f289c56f9c27e30634434ef75ac97afd` |
| `B1-boottime-retry1.csv` | `84b1245fbb5c8df746e411555820f1f6ac77ad8277248e6d2b575f2c57b2d3ba` |
| `B2-boottime.csv` | `f7930cc10c7bc44d1a655726ad9002de981a4f7234b3000571946840b81e12e1` |
