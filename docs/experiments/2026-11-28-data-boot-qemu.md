# LUKS2とBtrfsの起動接続をQEMUで確認する

状態は段2の機能試験完了。2026-11-28に実行した。

## 目的と事前の合格条件

PR C段2の機能試験である。段1のcommitは
`8f5bfba0611bbe7ff7d849e0e1ad9a86c03b6488`。
同じcheckoutの段1target buildを使い、host側のharnessだけを変更する。
性能比較ではないため、A、B、GPIO6 smokeを各1回実行する。
各試験はfresh初期化と、同じdiskを使うready再起動を含む。

- PIN設定2回、recovery照合、grow、LUKS2、mkfs、同期、readyの順序を確認する。
- ready再起動はPIN入力からmapperのBtrfs mountへ進み、再formatしない。
- 解錠後にhealth、superblock、usage、mount表を読み、
  xxhash64、data/metadataのDUP、zstd:3、nodev、nosuid、noatimeを確認する。
- GPIO6は認証とreadyの後にだけ注入し、eventとemergency remount要求を確認する。
- 各起動はQMP quitの応答、終了値0、reap、fallbackなしを必須とする。
- PINとrecoveryはhostのRAM内だけに持つ。全受信をRAMで検査してから保存し、
  初回のrecovery表示1回の値だけを除く。echo、再表示、期限超過は失敗とする。
- 検出器は分割read、3表記、stdout/stderr、例外の負の対照で先に確認する。

開発imageは`msd-dev:work-pr-c`だけを使う。QEMUはraspi3ap、512 MiB、
icountなし。kernel、DTB、sdcard、QEMU binaryのhashは各serial logの
`run-qemu: sha256`に記録する。実行中のscriptは変更しない。

## 結果

生の値は[CSV](2026-11-28-data-boot-qemu.csv)へ記録する。
A slotはfresh 409秒、ready再起動46秒で成功した。
B slotはfresh 412秒、ready再起動43秒で成功した。
GPIO6 smokeはfresh 413秒、ready再起動と注入51秒で成功した。
以上は最終検査を追加する前の予備確認である。
最終版でもA/B/GPIO6の全6起動を通した。

| 最終版の経路 | fresh（秒） | ready再起動・検査（秒） |
|---|---:|---:|
| A slot | 373 | 48 |
| B slot | 415 | 50 |
| GPIO6/powerfail smoke | 376 | 51 |

全起動でQMP quit応答、終了値0、reap、fallbackなしを確認した。
freshの3回はPIN2回、recovery照合、grow、format、mkfs、同期、readyの
順序をlogで照合した。ready再起動の3回にはzero走査、grow、mkfsがない。
元のimageは全試験後も同じSHA-256だった。
freshのzero検査は512 MiBを読み、304秒かかった。
これはTCG上の機能試験であり、実機性能ではない。
従来の300秒ではfreshが収まらないため、harnessの起動期限は各600秒とした。
これはhost側の期限であり、製品のPIN待ちには期限を設けない。
QMP終了期限と、失敗時のTERM/KILL・reapの条件は緩めていない。

```text
Set a new PIN (4-64 printable ASCII characters):
Enter the new PIN again:
[recovery display removed]
Enter the recovery key to check your copy, or an empty line to skip:
Growing data partition: starting. Do not power off.
Formatting LUKS2: starting. Do not power off.
Creating Btrfs filesystem: starting. Do not power off.
Synchronizing data filesystem: starting. Do not power off.
Saving ready label: starting. Do not power off.
MSD/Linux ready
```

ready再起動ではPINを入力し、解錠後に次を確認した。

```text
msd-data: /data btrfs noatime,nodev,nosuid,compress=zstd:3
csum_type		1 (xxhash64)
Data,DUP: Size:71303168, Used:0 (0.00%)
Metadata,DUP: Size:71303168, Used:131072 (0.18%)
/dev/mapper/msd-data /data btrfs rw,nosuid,nodev,noatime,compress=zstd:3,ssd,space_cache=v2,subvolid=5,subvol=/ 0 0
harness: secret leakage check passed
```

### 条件と再実行

| 項目 | 値 |
|---|---|
| 実行環境 | Linux 7.0.0-44-generic、開発containerはDebian 13 |
| QEMU | 11.1.3、raspi3ap、512 MiB、icountなし |
| 開発image | `msd-dev:work-pr-c`、ID `sha256:25d11254b14a76bfb459001d44ad7bba2351aaa9016268f8e4c29df2bcf72a79` |
| target | Buildroot 2026.08.2、Linux 6.18.64-v8、GCC 14.3.0。段1の`output/`を再利用。再configureなし |
| 秘密 | 各試験processでPINを乱数生成。recoveryはguest表示をRAMで受信し、そのまま照合。値とhashを記録しない |
| disk | 元のzero imageを一時copyし、2の累乗へ拡張。2回目は同じcopy。元imageは変更しない |
| log | serial、stdout、stderrはRAM内で全履歴を検査し、終了・reap後にだけ秘密を除いて保存。各channelに8 MiBの上限 |
| 終了 | QMPだけを使用。human monitorなし。quit応答・終了値0・reap・fallbackなしを必須とする |

以下の出力先が既にある場合は停止し、新しい名前へ変えてから実行する。
最初の確認後、別の鍵による2回目の表示案内も拒否する検査を追加した。
最終版は別の`qemu-final-*` directoryでA/B/GPIO6を再確認し、
初回の結果・logを上書きしない。

```sh
test ! -e output/pr-c-stage2-checks/qemu-a || exit 1
MSD_DEV_IMAGE=msd-dev:work-pr-c docker/msd-dev sh -c \
  'QEMU_LOG_DIR=/work/output/pr-c-stage2-checks/qemu-a board/cardputerzero/qemu/test-boot.sh'
test ! -e output/pr-c-stage2-checks/qemu-b || exit 1
MSD_DEV_IMAGE=msd-dev:work-pr-c docker/msd-dev sh -c \
  'QEMU_LOG_DIR=/work/output/pr-c-stage2-checks/qemu-b board/cardputerzero/qemu/test-ab.sh'
test ! -e output/pr-c-stage2-checks/qemu-gpio || exit 1
MSD_DEV_IMAGE=msd-dev:work-pr-c docker/msd-dev sh -c \
  'QEMU_LOG_DIR=/work/output/pr-c-stage2-checks/qemu-gpio board/cardputerzero/qemu/test-powerfail.sh --smoke'
```

元imageのSHA-256は
`859fbe345a66702e0e06f7ffd758a301dc224dfb341695184ff048c923c68a5f`、
kernelは`d73272ae0abaa18fb384e82b74a1d6d5007905897d2c9b1dfd4a179f6a285d83`、
rootfsは`f9dc5d8156e523df5893ab7b04c0d0c943977a10759f0973e4a48197735da00c`。
QEMU binaryは
`82248f8b0b31dcdc63d59c3f21b1f57a74e3f57346c582d740d33c0e8edcef04`。
Bluetooth無効化後のDTBは各serial logへhashを保存する。

最終版のharnessは、この記録と同じcommitの次のfileである。

| file（`board/cardputerzero/qemu/`以下） | SHA-256 |
|---|---|
| `serial-session.py` | `ee0f3cf283182e9feed708a583b2c4a485d491439c1c54c83ed1816cc3265fb4` |
| `boot-test.py` | `376699fa1f310715de7b11ada5836f29cdfc280e7062d949582cd002042403e5` |
| `run-qemu.sh` | `14b6f1098bd37e3d12c3aa4db70a93e6f380403fec616a7758c35aed3b1005bd` |
| `check-serial-log.sh` | `594259f0df5527902c4833777a2e09ae483b27614d10fc24d0f81aeede05da6c` |
| `test-powerfail.sh` | `35eb2f328bfd7b21671aa3d0975b0a122a6b5d5603b788534ee5af0c3043b314` |

### 検査器と失敗の扱い

最終版の秘密検査はhost 7試験、終了・期限・設定検査は22試験で成功した。
負の対照はPIN echo、同じ鍵・別の鍵の再表示、3表記それぞれの全split、
serial/stdout/stderr、QMP例外payloadを含む。漏洩時は全transcriptを保存しない。
fs-compare-v2は79試験、boottimeは8試験、write-inventoryは21試験で成功した。
ShellCheck、actionlint、zizmorも終了値0だった。

初回のhost試験ではmount表の末尾の`0 0`までoptionに含めたため、
正常なinspect結果を拒否した。option欄だけを読むよう修正した。
また、Python selectorsが`InterruptedError`を処理するため、
signalによる中断が期限超過になる問題を負の対照で検出した。
handlerを`ValueError`に変更し、終了・reapの回帰20試験を通した。

fs-compare-v2の判定器・fixture・原証拠は変更しない。
host試験のgrow marker照合先だけを現行S02から既存の試行09証拠へ移した。
boottimeとwrite-inventoryも旧条件のhost試験として保持する。
`test-powerfail.sh`の旧ext4向けintegrity/experiment測定は停止案内を出す。
新しいstorage条件で測ったことにはせず、再設計は別PRとする。
両旧modeが終了値2で止まることも確認した。overlayの入力とbuild logは
その確認前にarchiveへ保存し、実行済みGPIO6の入力を保全した。

GPIO6の最終logは次のとおりである。eventとremount要求の表示順を
固定して判定しない。

```text
[   44.135545] powerfail-suo powerfail: SysRq U: emergency remount filesystems readonly
[   44.137366] sysrq: Emergency Remount R/O
[   44.141543] Emergency Remount complete
[   44.319043] msd-powerfail: power-fail event received
```

partition更新時には`sfdisk`の`Re-reading the partition table failed.:
Device or resource busy`を確認した。後続の`partx --update`を含むhelperは
成功し、初期化と再起動を通した。この行をallowlistには追加していない。
停止通知、Btrfs error、device-mapper errorはallowlist適用前に拒否する。

### 最終版のlog

CIの保存先は`qemu-serial-logs` artifact。以下は再生成手順の
`output/pr-c-stage2-checks/`以下の相対pathとSHA-256である。
`acceptance.json`には同じhash、終了状態、recovery照合成立の真偽だけを保存する。

| log | SHA-256 |
|---|---|
| `qemu-final-a/serial-mmcblk0p5-fresh.log` | `906de1918563983152b797a8f5951ffa4e031aa3d6e8fa166b1fddb47fea43eb` |
| `qemu-final-a/serial-mmcblk0p5.log` | `b9e2590da4d83596937d8c2acd4e9ee7c2c4a7b9d38bea379fa224bdd1995dac` |
| `qemu-final-b/serial-mmcblk0p6-fresh.log` | `d4d1a9e9d1b98e501bcae7550ee26d0ecf4051aedd710b7ea4403bb6a323beca` |
| `qemu-final-b/serial-mmcblk0p6.log` | `667b4e10c51d901b4afdc97241b652f4ddbd085fb398a1855ee23a067d8eb2d0` |
| `qemu-final-gpio/powerfail/smoke-20261128T061214Z/serial-mmcblk0p5-fresh.log` | `3b81d30472f888c6869ed5baa53cc90da3172d7434ee7dacaa908c089960230b` |
| `qemu-final-gpio/powerfail/smoke-20261128T061214Z/serial-mmcblk0p5.log` | `450356d117de8447a171cd7660932fe1a04a85d695b714fdce8c4629a495a465` |

予備確認と最終確認のlog、process JSON、host試験出力、入力metadataは
`output/pr-c-stage2-checks/stage2-evidence.tar.gz`へ保全した。
SHA-256は
`936cf9385bdc9adf04b64027de635a375b5c8123f355015f1087faf1442dfd4d`。
本文とCSVは上記の手順・条件・生の値を再生成の根拠として残す。

### 未確認

LCD、内蔵keyboard、実SDのFTL、実電源断、firmware trybootと実機の
Argon2所要時間は確認範囲外である。idle時の書込み量、中断matrix、
pending再初期化、recoveryのみの再起動、誤PIN10回のQEMU確認も段3に残す。
