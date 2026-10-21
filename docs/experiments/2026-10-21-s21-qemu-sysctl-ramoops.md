# S21 sysctl 候補、panic 経路、QEMU の ramoops 試験

- 状態: build 完了、試験開始前
- 日付: 2026-10-21
- 担当: Devin
- 関連: [CPU・割り込み・sysctl](../research/cpu-irq-and-sysctl.md)、[simulation plan](../research/simulation-plan.md)
- 事前登録: v1、SHA-256 `2cac248825248d60d84ec99b9d5790bd8d07ca3304bb3185e8146662355411cd`

## 目的と仮説

sysctl の hardening 候補が起動時に適用され、`kernel.sysrq=32` の状態でも電源断時の emergency remount が動くかを確かめる。負の対照では `kernel.sysrq=0` により remount が起きないと予想する。QEMU の watchdog reset と `panic=` の経路を分け、再起動後に ramoops の panic 記録を読めるかを調べる。

製品設定は変更しない。製品への採否はこの試験では決めない。

## 採否の基準（結果を見る前に書く）

この節の条件、回数、期待値は事前登録 v1 のとおりとし、結果を見て変更しない。

### Y: sysctl drop-in

Y1 は `/etc/sysctl.d/90-msd-test.conf` に次の値を置く。Buildroot の `S02sysctl` が適用する。

```text
kernel.kptr_restrict=2
kernel.dmesg_restrict=1
kernel.sysrq=32
fs.protected_fifos=2
fs.protected_regular=2
fs.protected_hardlinks=1
fs.protected_symlinks=1
net.core.bpf_jit_harden=2
net.ipv4.conf.all.accept_redirects=0
net.ipv4.conf.default.accept_redirects=0
net.ipv4.conf.all.send_redirects=0
net.ipv4.conf.default.accept_source_route=0
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.all.log_martians=1
net.ipv4.conf.default.log_martians=1
```

`kernel.unprivileged_bpf_disabled=1` は不可逆であり、値 2 でも無効になるため除外する。`modules_disabled` は実機での判断が必要なため除外する。core dump がないため `core_uses_pid` も除外し、panic の値は P 条件で扱う。Y2 は負の対照とし、`kernel.sysrq=0` だけを設定する。

- Y0（drop-in なし）と Y1 を各 5 回起動する。
- Y1 と Y2 で `test-powerfail.sh` を各 5 回実行する。各 image は `POWERFAIL_IMAGE` で指定する。
- Y1 の `test-ab.sh` を 1 回実行する。
- Y1 は、起動 5/5 回で ready に達し、全 key の読み戻し値が指定値と一致すること、`Running sysctl: OK` が出ること、`check-serial-log.sh` が通ること、A/B 試験が通ること、powerfail 5/5 回で `SysRq U: emergency remount filesystems readonly` が出て powerfail 試験自身の基準を満たすことを条件とする。
- Y2 は、5/5 回で `SysRq U` による remount が出ないと予想する。出た場合は sysctl の読み取りからの予想と矛盾する結果として記録する。
- Y0 と Y1 の ready 中央値の差は観測値として記録し、合否には使わない。

### P: panic 経路（`QEMU_WATCHDOG=1`）

試験 hook は初回起動で `/data` に stage file を書き、`sync` し、marker を出してから `echo c > /proc/sysrq-trigger` を実行する。2 回目の起動では `s21: second boot` を出す。

- P0 は現行の `panic=0` と、動作中の watchdog daemon `-T 15` を使う。5 回とも marker の 8〜30 秒後に hardware watchdog が reset し、`Rebooting in` が出ず、2 回目の起動が ready になると予想する。
- P1 は test-only cmdline に `panic=5` を指定する。5 回とも `Rebooting in 5 seconds` が出て、marker の 3〜10 秒後に reset し、2 回目の起動が ready になると予想する。
- `panic_on_oops` は `CONFIG_LKDTM` がなく、non-fatal oops を起こす手段もないため、この試験では未確認とする。

### R: ramoops（`QEMU_WATCHDOG=1`、cmdline `panic=5`）

R1 は base DTB の copy に `/reserved-memory/ramoops@1f000000` を加える。`compatible = "ramoops"`、`reg = <0x0 0x1f000000 0x0 0x100000>`、`record-size = <0x20000>`、`console-size = <0x20000>` とし、DTB の `#address-cells` と `#size-cells` に合わせる。`/reserved-memory` がなければ追加する。dmesg に `ramoops: using 0x100000@0x1f000000` が出ることを確認する。

R0 は同じ test image と trigger を使い、base DTB を使う。R1 は R0 と同じ image と trigger に ramoops DTB copy を使う。2 回目の起動 hook は `/sys/fs/pstore` に pstore を mount し、file list と dmesg-ramoops record を出す。

- R1 は 5/5 回、reset 後の dmesg-ramoops record に `sysrq: Trigger a crash` と `Kernel panic` が含まれることを条件とする。
- R0 は 5/5 回、record がないことを条件とする。

QEMU は system reset をまたいで RAM を保持する。実機の watchdog reset 後に Raspberry Pi firmware が RAM を保持するか、指定 address が `gpu_mem` の領域と競合しないかは実機でしか確かめられない。製品への採否は未決定とする。

## Amendment 1（2026-10-21T22:27:52Z、R1 再試行前）

初回の R1 5 試行では、panic、reset、2 回目の ready、ramoops 登録を確認したが、pstore の mount 状態と record を取得できなかった。`s21-R1-1` の serial log は `MSD/Linux ready`、`s21: second boot` の直後に `qemu-system-aarch64: terminating on signal 15 from pid 1 (bash)` で終わっていた。ほかの R1 4 試行も同じく pstore collector の出力前に終了していた。

原因は runner が `s21: second boot` と 2 回目の `MSD/Linux ready` を確認した直後に QEMU を終了し、S99 hook の pstore 収集完了を待っていなかったことだった。初回 5 行と log は失敗した試行として保持する。test-only hook に収集完了 marker を追加し、runner がその marker を最大 120 秒待つようにしたうえで、R1 を同じ DTB、image、`panic=5`、watchdog 条件で 5 回置き換えて測る。置き換えた 5 行を事前登録の R1 5 試行として評価し、初回 5 行は不完全な実行として合否集計から除外する。条件、値、基準は変えず、ほかの条件は再実行しない。

## Amendment 2（2026-10-21T22:35:33Z、再試行前）

Amendment 1 の R1 再試行では、`docker/msd-dev` が環境変数の `S21_MODES`、`S21_RUN_TAG`、`S21_VARIANT_ROOT` を転送しなかったため、指定した R1 ではなく既定の P0 から runner が始まった。runner は既存 run ID の上書きを拒否しなかった。

元の P0-1〜P0-3 の serial log は上書きされた。対応する元の CSV 行は変更せず残すが、記録された log SHA-256 と現在の log SHA-256 が一致しないため、P0 の判定には使わない。誤実行の P0-1〜P0-4 の追加 CSV 行と P0-4 の不完全な log も保持し、合否集計から除外する。P0-5 の現在の log も元の CSV の hash と一致せず、途中で切れた内容が残るため、元の P0-5 行も判定に使わない。P0-5 の誤実行への到達経路は記録だけでは確定できない。

runner は選択 mode、run tag、variant root、CSV path を CLI 引数で受け取り、実行前に全 run ID の log directory と CSV 行の重複を検査するようにする。誤実行行と元の P0 行はそのまま残す。P0 は `amendment2` tag で元と同じ条件・基準の 5 試行を行い、この 5 行で P0 の判定を行う。R1 は Amendment 1 の手順で `amendment1` tag の 5 試行を行う。指定済みの値、条件、基準は変えない。

## Amendment 3（2026-10-21T23:01:56Z、R1 再試行前）

R1 の `amendment1` 5 試行では、second boot ready まで到達したが、runner の log に `pstore-collection-timeout` が記録された。調査すると、実行に使った `variants/R1/rootfs.squashfs` 内の `S99zz-s21probe` に、commit 済み hook の `s21: pstore collection complete` marker が含まれていなかった。5 log すべてにも marker がなく、runner は Amendment 1 が要求する収集完了を確認できなかった。これらの CSV 行と log は不完全な試行として保持し、R1 の判定から除外する。raw log には pstore mount status 0、`console-ramoops-0` と `dmesg-ramoops-0`、および必要な record 内容があるが、完了 marker の欠落を補うものとしては使わない。

また、serial log に NUL byte が含まれ、従来の `grep` と `sed` が dmesg-ramoops record を正しく抽出しないことを確認した。runner は NUL byte を除いて pstore status、file list、record marker を解析するように修正し、既存の raw log で `sysrq: Trigger a crash` と `Kernel panic` を抽出できることを確認する。

既存の R1 variant は保持し、現在の hook を含む R1 rootfs と SD image を別の `variants-amendment3` directory に作り直す。新しい DTB copy は引き続き `msd-dev` 内の `dtc` で生成する。この条件で R1 を `amendment3` tag の別 run ID で 5 回測り直し、その 5 行を R1 の判定に使う。試行条件、値、合否基準は変えない。P0 の `amendment2` 結果は変更しない。

## 条件

| 項目 | 値 |
|---|---|
| 事前登録の SHA-256 | `2cac248825248d60d84ec99b9d5790bd8d07ca3304bb3185e8146662355411cd` |
| 基準の commit | `0cc65a9379acd9263e3de50522bafc5f1e5ba79e`（S11 watchdog branch、stacked PR） |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| QEMU | msd-dev image `sha256:f9785d712ccab0dcb26ce2ebbad502c6c8a29a49000f56c60766fa7551b1d087`、QEMU 11.1.2、binary SHA-256 `7199b846fb617f519c80962e2008ee63d2ce73bd125c05b0206dfca1ed73f3a6` |
| Buildroot / toolchain / kernel | Buildroot `2026.08`、submodule `d6061d653d7fb215c2409c59e4bfad1b9d677215`、GCC `14.3.0`、kernel `6.18.57-v8`。実使用した DTC は `1.7.2`、SquashFS tools は `4.7.5`、sfdisk は util-linux `2.41.5` |
| 出力と入力 | 基準 branch の output tree を完全 clean して再 build した。build 時の `.config` SHA-256 は `09a8a8f5292d6732b52faeac7dbca58fe3378c30c2fb7b73ea869879751c2647`。初期記録の `f80716ec...` から、S21 tree での defconfig 後は `9c8c6fab...`、基準 tree の defconfig 後は上記 hash になった。S21 tree と基準 tree の `.config` 比較では、差は外部 tree の path、version、defconfig path と生成 comment のみであり、package option に差はなかった |
| base artifact SHA-256 | `Image` `df9ee366c5e24c8819da50512cf008708f769f72b1439f23390a16e668cea686`、base DTB `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f`、base rootfs `683de811fd11d10949b3365c57599335274e168cd0cee449a994084c7a2a1879`、base `sdcard.img` `da1b172cb3be133896a92d77986f0f7bc7dddaf25f35bda47209a4761bba6930` |
| QEMU machine / RAM | TCG、`raspi3ap`、512 MiB、base DTB `bcm2710-rpi-cm0.dtb` |
| 条件と回数 | Y0/Y1 boot 各 5、Y1/Y2 powerfail 各 5、Y1 A/B 1、P0/P1/R0/R1 各 5 |
| 変えない条件 | 製品 config と product files。全 variant は test-only rootfs または DTB copy とする |
| second-boot 待ち | reset 後、最大 120 秒 |

## 手順

結果を見る前にこの記録と CSV header を commit した。Buildroot は既存 output tree を再利用して `make clean` の後に build した。build log は `s21-logs/buildroot-clean-envfix.log` に保存した。初回の 3 build は BusyBox の target install で失敗し、clean 後の build も host-skeleton install で一度失敗した。失敗 log と詳細は「失敗した試行と経緯」に残す。成功 build の `make` は `BASH_ENV` を unset して実行した。

次に `board/cardputerzero/tools/bench/sysctl-ramoops/` の builder で test-only variant を作り、同 directory の runner で上記の条件を実行する。`test-powerfail.sh` は `POWERFAIL_IMAGE` で variant image を指定し、`test-ab.sh` と `test-boot.sh` は変更せずに使う。実行 command、variant hash、log manifest は結果の追記に残す。

## 計測器の検証

未実施。Y0 の事前登録 5 回の最初の 2 回を同条件の A/A 確認として使い、hook marker と読み出しの再現性を記録する。追加試行は行わない。

## 結果

未実施。

## 失敗した試行と経緯

測定 run はまだない。Buildroot の失敗した build attempt は `s21-logs/` に残し、最終 manifest に含める。最初の 3 回は S21 tree または基準 tree の defconfig 後に BusyBox 1.38.0 の target install で失敗した。ログには次の結果がある。

```text
>>> busybox 1.38.0 Installing to target
# Use the 'noclobber' install rule, to prevent BusyBox from overwriting
make[1]: *** [package/pkg-generic.mk:364: .../busybox-1.38.0/.stamp_target_installed] Error 1
make: *** [Makefile:23: _all] Error 2
```

この時点では失敗した install command を特定できなかった。既存 output tree を clean して再 build した際は、host-skeleton の host install で一度失敗した。`make V=1` と shell trace でも command は特定できず、`BASH_ENV` を unset した `make` の再実行で build が完了した。clean build の warning は 273 件で、主に上流 package の configure、compiler、Python packaging warning だった。測定条件を変えた試行はない。条件や値を変える場合は、対象 run の前に時刻と理由を Amendment として記録する。

## 結論

未実施。QEMU での結果は実機の結果ではなく、製品への採否は利用者が判断する。

## 未確認の点

- 実機 watchdog reset 後の ramoops retention。
- ramoops address と firmware の `gpu_mem` 領域との関係。
- `panic_on_oops`（`CONFIG_LKDTM` がなく、non-fatal oops trigger を使えない）。
- 製品への採否。

## ログ

生ログは repository 外の `~/work/s21-logs/` に保存し、SHA-256 manifest を作成する。ログ本体は commit しない。
