# S21 sysctl 候補、panic 経路、QEMU の ramoops 試験

- 状態: 計画（事前登録済み）
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

## 条件

| 項目 | 値 |
|---|---|
| 事前登録の SHA-256 | `2cac248825248d60d84ec99b9d5790bd8d07ca3304bb3185e8146662355411cd` |
| 基準の commit | `0cc65a9379acd9263e3de50522bafc5f1e5ba79e`（S11 watchdog branch、stacked PR） |
| ホスト | Ubuntu 26.04.1 LTS、Linux 7.0.0-38-generic、x86_64 |
| QEMU | msd-dev image `sha256:f9785d712ccab0dcb26ce2ebbad502c6c8a29a49000f56c60766fa7551b1d087`、QEMU 11.1.2、binary SHA-256 `7199b846fb617f519c80962e2008ee63d2ce73bd125c05b0206dfca1ed73f3a6` |
| Buildroot / toolchain / kernel | Buildroot submodule `d6061d653d7fb215c2409c59e4bfad1b9d677215`、kernel `6.18.57-v8`。GCC と host tool の版は、試験に使う binary から記録する |
| 出力と入力 | 既存 output tree を再利用する。`.config` SHA-256 `f80716ec65ffaf5e9c9691135116ef4cb85a99007cf4de91e4cfe9810278bb33`。試験前に defconfig と一致することを確認する |
| base artifact SHA-256 | `Image` `3f3abfcbd8c0ce8c4f8beb230d2661b8fec745f80979837ee2d9917c377edcf4`、base DTB `e035db2336d4081dcaf76bf2d336404aca4d9421a8c0de8133e8962ef385c98f`、base rootfs `db6d3437d9b6b8324c030a31e9b03eb66947a85e0851c77802b9012bc1dbf8c4`、base `sdcard.img` `e9be1675b865f51f321209340f692b47869d4deb1ee038cfac681c7e78987165` |
| QEMU machine / RAM | TCG、`raspi3ap`、512 MiB、base DTB `bcm2710-rpi-cm0.dtb` |
| 条件と回数 | Y0/Y1 boot 各 5、Y1/Y2 powerfail 各 5、Y1 A/B 1、P0/P1/R0/R1 各 5 |
| 変えない条件 | 製品 config と product files。全 variant は test-only rootfs または DTB copy とする |
| second-boot 待ち | reset 後、最大 120 秒 |

## 手順

結果を見る前にこの記録と CSV header を commit する。その後、`board/cardputerzero/tools/bench/sysctl-ramoops/` の builder で test-only variant を作り、同 directory の runner で上記の条件を実行する。`test-powerfail.sh` は `POWERFAIL_IMAGE` で variant image を指定し、`test-ab.sh` と `test-boot.sh` は変更せずに使う。実行 command、tool version、variant hash、log manifest は結果の追記に残す。

## 計測器の検証

未実施。Y0 の事前登録 5 回の最初の 2 回を同条件の A/A 確認として使い、hook marker と読み出しの再現性を記録する。追加試行は行わない。

## 結果

未実施。

## 失敗した試行と経緯

未実施。実行した失敗試行は削除せず、CSV と log manifest に残す。条件や値を変える場合は、対象 run の前に時刻と理由を Amendment として記録する。

## 結論

未実施。QEMU での結果は実機の結果ではなく、製品への採否は利用者が判断する。

## 未確認の点

- 実機 watchdog reset 後の ramoops retention。
- ramoops address と firmware の `gpu_mem` 領域との関係。
- `panic_on_oops`（`CONFIG_LKDTM` がなく、non-fatal oops trigger を使えない）。
- 製品への採否。

## ログ

生ログは repository 外の `~/work/s21-logs/` に保存し、SHA-256 manifest を作成する。ログ本体は commit しない。
