# S11 QEMU watchdog の検証

- 状態: v1 の QEMU 実験済み、v2 は測定前（実機未確認）
- 日付: 2026-10-20
- 担当: Devin
- 関連: [S11 調査計画](../research/simulation-plan.md)

## 目的と仮説

QEMU 11.1.2 の BCM2835 power-management watchdog に仮想時間タイマーを追加し、Linux の watchdog driver と init script が行う給餌、停止、再起動、電源オフを観測する。給餌を停止した場合は watchdog expiry により同じ SD image から再起動し、Linux の `reboot` と `poweroff` はそれぞれ再起動と QEMU 終了になると予測する。

## 採否の基準（結果を見る前に書く）

TCG で各 mode を 5 回ずつ実行する。以下の基準を測定前に定めた。

- `none` は 5/5 回で 60 秒以内に reset せず、watchdog state が active、timeout が 15 であることを求める。
- `stop` と `kill9` は 5/5 回で reset し、marker から reset までが 8〜30 秒であること、reset 前に `reboot: Restarting system` が出ないこと、second boot が ready になることを求める。
- `reboot` は 5/5 回で `reboot: Restarting system` の後 10 秒以内に reset し、second boot が ready になることを求める。
- `poweroff` は 5/5 回で reset せず、30 秒以内に QEMU が自ら終了することを求める。
- `term` は観察のみとする。BusyBox が magic close `V` を書き watchdog を停止するため reset しない、という仮説を記録するが、合否は判定しない。
- `QEMU_WATCHDOG` を設定しない既定の `board/cardputerzero/qemu/test-boot.sh` が exit 0 となることを回帰条件とする。

## Amendment 1（v2、2026-10-21T16:16:10Z、測定前）

v1 は initial marker から 40 秒で観測を打ち切ったため、`stop` と `kill9` では reset 後 23〜26 秒までしか観測できず、second boot ready は各 0/5 回だった。この 30 試行は失敗した v1 の記録として残す。`reboot` では reset から ready まで 28.215〜29.307 秒かかったため、stop と kill9 の観測時間が不足していた。

v2 では、`stop` と `kill9` の試行で marker の後 30 秒以内に reset を検出し、その reset から最大 120 秒まで second boot ready を待つ。120 秒は `reboot` で観測した reset から ready までの最大 29.3 秒のおよそ 4 倍である。marker から reset までの 8〜30 秒、reset 前に restart message がないこと、その他の v1 基準は変えない。

6 mode × 5 回をすべて、rebase 後の `origin/main` HEAD `d1f65609cb314491556071c9399b974445a96319` から build した image で測り直す。v1 の 30 試行は CSV と本文に残し、`version=v1` として区別する。v2 は別の run ID（`s11-v2-<UTC>-<run>-<mode>-<repeat>`）と別の CSV 行にし、version 列を追加して `version=v2` と記録する。

## 条件

| 項目 | 値 |
|---|---|
| v1 image の source commit | `fca902408e1e6e83f4317870ef9cb082051a120b` |
| v2 image の source commit | `d1f65609cb314491556071c9399b974445a96319` |
| ホスト | Ubuntu 26.04.1 x86_64、Linux 7.0.0-38-generic |
| 開発コンテナー | Debian 13、Python 3.13.5、Bash 5.2.37 |
| QEMU | QEMU emulator 11.1.2。GCC 14.2.0 でビルドした `msd-dev:local` 内の binary |
| Buildroot | 2026.08 系の既存出力 |
| cross GCC | `aarch64-linux-gcc.br_real` 14.3.0 |
| kernel | 6.18.57-v8 |
| rootfs / image tools | unsquashfs と mksquashfs 4.7.5、sfdisk 2.41.5 |
| v1 出力先と状態 | 既存の `OUTPUT_DIR` を再利用。Buildroot の再 configure / 再 build は行わなかった。 |
| v2 出力先と状態 | v2 条件として `origin/main` の HEAD から再 configure / build する。実施結果は後述する。 |
| v2 QEMU image | `msd-dev:local`（QEMU 11.1.2、image ID `sha256:763f112a609ec5839867c1a20df3e2612ca865e14a4a6fc3fbdfb582c65201ad`） |
| 変える条件 | watchdog の停止・終了・reboot・poweroff 動作 |
| 変えない条件 | QEMU machine、kernel、DTB、SD image、仮想時間設定、rootfs 以外の image 内容 |
| 繰り返し | TCG で各 mode 5 回。中央値と最小・最大を報告する。 |

## 手順

Buildroot 出力と SD image は既存のものを使い、watchdog init script を加えたテスト用 rootfs を作成した。`test-watchdog.sh` は各試行用に SD image をコピーし、`QEMU_ICOUNT` を解除して TCG で起動する。実行コマンドは次のとおり。

```sh
QEMU_WATCHDOG=1 \
OUTPUT_DIR=<既存の Buildroot 出力> \
QEMU_LOG_DIR=<永続ログディレクトリー> \
docker/msd-dev board/cardputerzero/qemu/test-watchdog.sh \
  --experiment --csv "$QEMU_LOG_DIR/watchdog.csv"

env -u QEMU_WATCHDOG \
OUTPUT_DIR=<既存の Buildroot 出力> \
QEMU_LOG_DIR=<永続ログディレクトリー> \
docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

v1 の `run_id` は `s11-20261020T215917Z-1-<mode>-<repeat>`。TCG 実験は 35 分 27.31 秒で完了し、stop / kill9 の事前登録基準を満たさなかったため、コマンドの終了 status は 1 だった。全 30 行は CSV に保存されている。

## 計測器の検証

serial の各行に host monotonic timestamp を付けた。30 個の serial log と CSV を照合した。全試行で `msd.wdtest=<mode>` が kernel command line にあり、watchdog driver の initcall blacklist はなかった。none と term の全試行で `state=active timeout=15` を確認した。reboot の restart message から次の `Booting Linux` までは 1.485–1.603 秒だった。

## 結果

| mode | 実測結果 | 事前登録基準 |
|---|---|---|
| none | 5/5 は 60 秒以内に reset なし。全て `state=active timeout=15`。 | 5/5。達成。 |
| stop | 5/5 reset。marker→reset は中央値 14.599 秒、範囲 14.269–15.314 秒。restart message は 0/5。40 秒の観測終了までに second boot ready は 0/5。 | 0/5。reset 時間と restart 条件は満たすが、ready 条件を満たさない。 |
| kill9 | 5/5 reset。marker→reset は中央値 17.002 秒、範囲 16.996–17.032 秒。restart message は 0/5。40 秒の観測終了までに second boot ready は 0/5。 | 0/5。reset 時間と restart 条件は満たすが、ready 条件を満たさない。 |
| reboot | 5/5 で `reboot: Restarting system` の後に reset。marker→reset は中央値 8.371 秒、範囲 8.171–8.644 秒。restart message→reset は中央値 1.560 秒、範囲 1.485–1.603 秒。second boot ready は 5/5。 | 5/5。達成。 |
| poweroff | 5/5 で reset なしに QEMU が status 0 で終了。marker→exit は中央値 7.100 秒、範囲 6.867–7.195 秒。 | 5/5。達成。 |
| term | 5/5 で 60 秒以内に reset なし。 | 観察のみ。pass/fail 判定なし。 |
| default boot regression | `QEMU_WATCHDOG` なしで `test-boot.sh` は exit 0、34 秒で ready。kernel command line に既定の initcall blacklist がある。 | exit 0。達成。 |

v1 の stop / kill9 は initial marker から 40 秒の制限内に second boot ready へ到達しなかった。該当試行では reset 後 23〜26 秒で QEMU を host 側から終了した。reboot 試行では reset 後 28.215〜29.307 秒で ready に到達した。v1 の測定値と判定はそのまま保持し、v2 の待ち時間は Amendment 1 のとおり変更する。

term は 5/5 で観測時間内に reset しなかった。この結果は magic close `V` の仮説と整合するが、serial log から close の方式そのものは確認できない。

全試行の生データは [CSV](2026-10-20-s11-qemu-watchdog.csv) を参照する。QEMU log には MMC1 timeout、補助 UART の `-EINVAL`、Bluetooth HCI timeout などの周辺機器診断が繰り返し記録された。watchdog の marker、reset または QEMU exit の記録とは別に扱った。

## 初回 after-run 後の停止処理判定基準の訂正

init script の stop guard を確認した初回 after-run の後、再起動区間の回帰判定を訂正した。最初の案は `msd-wdtest: action reboot` から `reboot: Restarting system` まで `MSD/Linux ready` がないことを求めていた。しかし `S97zz-wdtest` は `S98msd-ready` より前に実行され、reboot 要求後も sysinit の `rcS` は残りの start script を実行する。そのため、初回起動時の `S98msd-ready` が通常どおり ready を出力する。この出力は shutdown 時の stop 処理再実行を示さない。

訂正後は、serial log の先頭から最初の `reboot: Restarting system` までを初回起動区間とする。この区間で `MSD/Linux ready` が substring としてちょうど 1 回あり、次の文字列がすべて 0 回であれば合格とする。console の制御 byte は行頭に付く場合があるため、ready は行頭一致でなく substring で数える。

- `msd-wdtest: second boot`
- `e2fsck: Cannot continue`
- `overlayfs: upperdir is in-use`
- `overlayfs: workdir is in-use`

この確認は `QEMU_WATCHDOG=1` で `test-watchdog.sh --mode reboot --runs 1` を実行した fixed image の回帰判定であり、v1 の 30 試行と CSV は変更しない。

その後、PR #77 の start-only stop guard が main に入った。`S01msd-watchdog` などの既存 init script は start 以外の引数では処理せず、`S97zz-wdtest` も同じ guard を持つ。v2 はこの guard を含む `origin/main` の image で測る。この節に記録した after-run は履歴として残し、v2 の結果とは区別する。

修正前のログ `s11-20261020T215917Z-1-reboot-1/serial.log` は ready が 2 回で、禁止文字列は各 1 回出たため不合格だった。固定 image の after-run `s11-20261021T000920Z-1-reboot-1/serial.log` は ready が 1 回で、禁止文字列はすべて 0 回となり合格した。reset 後には `msd-wdtest: second boot` と `MSD/Linux ready` の両方を確認した。以下の行は初回起動区間の抜粋である。制御 byte は `\xNN` 表記に置き換えた。

修正前（不合格）

```text
289:30.958131451 msd-wdtest: action reboot
295:31.346294031 \x01\x03\x0c\x00MSD/Linux ready
298:32.037864511 MSD/Linux ready
302:32.157731931 msd-wdtest: second boot
316:33.721933723 [   31.063183] overlayfs: upperdir is in-use as upperdir/workdir of another mount, accessing files from both mounts will result in undefined behavior.
317:33.725321046 [   31.063574] overlayfs: workdir is in-use as upperdir/workdir of another mount, accessing files from both mounts will result in undefined behavior.
319:34.099835705 e2fsck: Cannot continue, aborting.
333:37.760717299 [   35.105470] reboot: Restarting system
```

修正後（合格）

```text
289:29.013162895 msd-wdtest: action reboot
297:29.351233144 MSD/Linux ready
319:34.531244687 [   31.521882] reboot: Restarting system
```

修正前の serial log の SHA-256 は `9cb3a7956b0631a6b2ca89e023cd14b4f3029c25bab8a2cac0afb5ae0577923f`、修正後は `6122347d05d6ed7b9a0f7bdfa42e46d47011caff9e0d45c403f5f1c37e543b66`。機械判定の出力 `s11-init-stop-guard-after-20261021T000911Z/first-boot-criterion.txt` の SHA-256 は `b0293e0447d56810283de1c081b2cecaffc34f4c85b26b9dbb1c0dff2d0a432d`。これらの log と判定出力は commit せず、永続ログ領域に保存した。判定は serial log を byte 列として読み、最初の restart marker までの部分で各文字列の出現数を数えた。

## 捨てた試行と経緯

事前確認として実施した stop ×1 の smoke は 72.37 秒で終了したが、marker→reset 14.582 秒の後、40 秒の観測期間内に second boot ready を確認できず、criteria-failed となった。serial log は `smoke/s11-smoke-20261020T215705Z-1-stop-1/serial.log`。このため、CI に追加していた watchdog smoke step は削除した。2 分以内ではあるが、現状の基準では CI を失敗させるためである。

この smoke の CSV 行（列名は本実験 CSV と同じ）は次のとおり。

```text
v1,s11-smoke-20261020T215705Z-1-stop-1,stop,1,30.306809702,44.888341572,14.581531870,no,no,killed@69.779983733,1,criteria-failed:v1-wait-window-too-short
```

v1 では stop 5/5 と kill9 5/5 が second-ready 基準を満たさず、全体の終了 status は 1 となった。この 10 試行は待ち時間の誤りによる失敗として、元の測定値を保持して CSV に記録した。その他の 20 試行も含め、全 30 行を CSV に記録した。

## 結論

QEMU 11.1.2 の watchdog timer は、stop / kill9 後の reset、Linux reboot 後の reset、poweroff による QEMU 終了を観測できた。none では watchdog が active のまま 60 秒 reset せず、term でも 60 秒 reset しなかった。stop / kill9 の reset 自体は全試行で観測したが、second boot ready の基準は満たしていないため、この実験の基準全体は未達である。

これは QEMU TCG の結果であり、実機の watchdog 動作を示すものではない。BCM2837 / CardputerZero 実機での reset と poweroff は未確認である。

## 未確認の点

QEMU は GPU firmware と tryboot を持たず、`-kernel` による再起動は同じ kernel を使うため、watchdog reset 後の slot selection は検証できない。BCM2837 / CardputerZero 実機の watchdog 動作も未確認である。

## ログ

再生成コマンドは「手順」に記載したとおり。`QEMU_LOG_DIR` は永続ディレクトリーを指定し、Buildroot 出力を既存のものに置き換える。生の CSV はこの文書と同じディレクトリーに保存し、大きな serial log はコミットしない。

以下は計測時の serial log、rootfs 作成ログ、smoke と regression log の SHA-256。ログは外部の永続ログディレクトリーに保存した。

| log | SHA-256 |
|---|---|
| experiment/s11-20261020T215917Z-1-none-1/serial.log | `22751c40fc072ae9499af978860a3fc45610726fe07cf0e3be41f0e4d3a2e927` |
| experiment/s11-20261020T215917Z-1-none-2/serial.log | `50fced4b7785d9f1255e75d71456fa3671760806b04d7ad5c6b1cd25d7d9c27f` |
| experiment/s11-20261020T215917Z-1-none-3/serial.log | `da9526d1b41f6ca756eb6c837e2da586afdc5f6313592ae2954816d6f45774e8` |
| experiment/s11-20261020T215917Z-1-none-4/serial.log | `bcdbc06c5bea80cc11c56daa9090cdf274f9365e9cdb4078788cdf14de6257f0` |
| experiment/s11-20261020T215917Z-1-none-5/serial.log | `66db937f27c3e11b5e0c89239eaee660c093411d72fedab1e7b6d393d047e188` |
| experiment/s11-20261020T215917Z-1-stop-1/serial.log | `95be330a45286a66c3ad2a3f3538666f095bd1be0c97ce53aabae275557d26e9` |
| experiment/s11-20261020T215917Z-1-stop-2/serial.log | `ccdcdcac11761efddb5bb7223301918ee999fe5be7d31b0738027194abe83b04` |
| experiment/s11-20261020T215917Z-1-stop-3/serial.log | `4d31a004badb49803095172d9fe40395b8561a59ecdf7c29ef9cf0be164197dc` |
| experiment/s11-20261020T215917Z-1-stop-4/serial.log | `10a82140b892d4ea564899be527efe411160f305f0e1c2183d7b68c0517637bd` |
| experiment/s11-20261020T215917Z-1-stop-5/serial.log | `bfdb27adda1fe4519ff9943b49d2b343a5032d6fc914d57e121dd5f279f93e5c` |
| experiment/s11-20261020T215917Z-1-kill9-1/serial.log | `2b168a5ab22516d72560f0c2d326afa3beb914374249f2c1997666ee7e2cbc1d` |
| experiment/s11-20261020T215917Z-1-kill9-2/serial.log | `2eff95acc8bdabd52641e5ff9ea3b6781485b22a0678791973a1737b38d42a62` |
| experiment/s11-20261020T215917Z-1-kill9-3/serial.log | `58c67cb0ca6e7ebe90251997489732b9658bd78240c2d53e94b8efcaaeb32819` |
| experiment/s11-20261020T215917Z-1-kill9-4/serial.log | `771e8b1bfa8d3758349a2aa057d5a08beff778e78c8c7e27155b7e9910051fb4` |
| experiment/s11-20261020T215917Z-1-kill9-5/serial.log | `c518115f63f3e7d9c0b511cec96d528882e73ec3e933782e96905350a447f1ea` |
| experiment/s11-20261020T215917Z-1-term-1/serial.log | `707d851326d49017f6e86a4f96e576161c029855c035c9fad967c40a6ae0ab0a` |
| experiment/s11-20261020T215917Z-1-term-2/serial.log | `7bcbcda1b241f75c5fddd7cc1aac7599abfe6b0899d4d497d204be9b5a691577` |
| experiment/s11-20261020T215917Z-1-term-3/serial.log | `f9b47d90efccebfe73eb661a39107c02156d8960be715c648ebb221e8b0c0e61` |
| experiment/s11-20261020T215917Z-1-term-4/serial.log | `dce0e2d5a412503bbd9f4721ff0b1be4aee79a6ce3fe3f43266350582d254264` |
| experiment/s11-20261020T215917Z-1-term-5/serial.log | `fdafc73c3f10e80d664fd533a7b1d8a6228b5d503f55ad3549c933fd73c9ebdc` |
| experiment/s11-20261020T215917Z-1-reboot-1/serial.log | `9cb3a7956b0631a6b2ca89e023cd14b4f3029c25bab8a2cac0afb5ae0577923f` |
| experiment/s11-20261020T215917Z-1-reboot-2/serial.log | `fe6c19c7a548731b92efc11ed8ba1b3b0ae043c982f98c6dead9c0a5d236b259` |
| experiment/s11-20261020T215917Z-1-reboot-3/serial.log | `e834efbcbfd8a803f1b433b6ef9c256f2f8a38d5e6e5642fec9cbbc380c7ad38` |
| experiment/s11-20261020T215917Z-1-reboot-4/serial.log | `a38c739a8d92539e23be7a1922c9e5079fa81173d84b8730dbbb69a141391820` |
| experiment/s11-20261020T215917Z-1-reboot-5/serial.log | `1a8b06189b09a797fdf55bd917cc76206031a9812fcdf1e62bd536dfaaf7c809` |
| experiment/s11-20261020T215917Z-1-poweroff-1/serial.log | `a70de1110542d6218b8ccb197b0e0828d307e96987ec2ecb664b7ef5bd7b5420` |
| experiment/s11-20261020T215917Z-1-poweroff-2/serial.log | `6d1a69066061906fbed37f42e12d72bc12a06f791e9f54dc251e9066f00d1606` |
| experiment/s11-20261020T215917Z-1-poweroff-3/serial.log | `07a7e61dd556886994931f6c9b34e14928643f13ceb013055c3e83fb8414a82b` |
| experiment/s11-20261020T215917Z-1-poweroff-4/serial.log | `5e6fb72938f32c9e0e5d0c48eaf27f639ab47cc0c064c2195c99346d5accc29f` |
| experiment/s11-20261020T215917Z-1-poweroff-5/serial.log | `6bac75d1efb53e9d3c1462f761759863112bbebafa305e7f77c59576226fe678` |
| experiment/work/image-20261020T215915-1/unsquashfs.log | `cffab08dc89b2b8a82a0fad1bc3b5d221a05f15e206a6e80344f8abb37dc750f` |
| experiment/work/image-20261020T215915-1/mksquashfs.log | `611bb56d9ae8a0b93bda6f0e18fc6d75ddd75a3c82f05217b257a1c48bac977c` |
| smoke/s11-smoke-20261020T215705Z-1-stop-1/serial.log | `cb1af4d483a16d666f34533bbff4d0ad173b608f6368a427eb6d2a1e899a2135` |
| smoke/work/image-20261020T215703-1/unsquashfs.log | `a4d0d19bcd68ddb7366a878a90beaca09904f86eb201fb2bc78fc456c474b9d9` |
| smoke/work/image-20261020T215703-1/mksquashfs.log | `4e3da4b52b38842334df9e5400fb32fd4d126755ccc2e08f0ca40c8ded7447d3` |
| regression/serial-mmcblk0p5.log | `8f839720704b1783839ae3dcc7cc4ba447c8b207e2e7c9f262dd5f2a5` |
