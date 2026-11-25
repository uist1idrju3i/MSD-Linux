# 早期I/O fixtureのconsole出力を確かめる

- 状態: 通常Aとmodule期限対照が完了。実機・この条件のBは未確認。
- 日付: 2026-11-25
- 基準source: `b8efa6903bb2fb19b4d49ff23449779a9a739e3c`とfixture修正の作業tree
- 関連: [設計](../design/early-io.md)、[先行試験](2026-11-25-early-io.md)、[生の値](2026-11-25-early-io-console.csv)

## 目的・基準・回数

元imageにない`msd-console`をfixtureが収録し、QEMUでkernel logとは別にconsoleへ出力することを確かめます。
各条件1回のsoftware機能確認です。速度・実機表示・性能の中央値は評価しません。
通常Aでは、時刻prefixのない4 markerと/data・ready・login、QMP quit成功、終了0を要求します。
module期限対照では、時刻prefixのない`waiting elapsed=`と`early-io end failed`、電源断可の表示を要求します。
対照の/data・readyは0件、boot試験器の終了は124とします。host testでは欠損commandと設定を拒否することも確かめます。
これらの基準はQEMU実行前に固定します。

## 条件・手順

baseは先行試験と同じ`output-openssl-lts`、kernel・library・DTBは再buildしません。
既存BusyBox 1.38.0のtimeout有効版を再利用し、`msd-console`だけ同じbuildのcross compilerで現在のsourceから作ります。
warmな既存buildの利用であり、ccache・build時間・容量の比較ではありません。
両条件は同じ入力を使い、QEMUは並列起動しません。既存の出力は上書きしません。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/early-io-fixture.py output-openssl-lts output-early-io-console-01 --busybox output-early-io-02/busybox/busybox
docker/msd-dev python3 board/cardputerzero/tools/bench/early-io-fixture.py output-openssl-lts output-early-io-console-timeout-01 --busybox output-early-io-02/busybox/busybox --module-timeout
OUTPUT_DIR="$PWD/output-early-io-console-01" QEMU_MACHINE=raspi3b QEMU_MODULE_TEST='' QEMU_BOOT_TIMEOUT=120 QEMU_LOG_DIR="$PWD/output-early-io-console-01/logs-a" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
OUTPUT_DIR="$PWD/output-early-io-console-timeout-01" QEMU_MACHINE=raspi3b QEMU_MODULE_TEST='' QEMU_BOOT_TIMEOUT=45 QEMU_LOG_DIR="$PWD/output-early-io-console-timeout-01/logs-a" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
```

## 結果と範囲

hostはUbuntu 26.04.1 LTS、固定開発imageのQEMUは11.1.3、raspi3b・1 GiB・TCG・icountなしです。
kernelは既存6.18.59-v8、cross compilerはGCC 14.3.0、Buildroot表示は`2021.11-18033-g83947c7bb6`でした。
fixtureのC helperは`-Os -Wall -Wextra -Werror`で構築しました。製品full buildではありません。

```text
Ran 24 tests in 22.809s
OK
QEMU process result: {"qmp_quit": true, "returncode": 0, "reaped": true, "fallback": [], "error": null, "pid": 11}
QEMU boot marker and login prompt found for root /dev/mmcblk0p5.
```

通常Aのserial logには、kernelの時刻prefix付きの行と別に、次の4行がこの順で現れます。
元imageのcommandを使い回した結果ではなく、今回構築・収録した`msd-console`からのconsole出力です。

```text
msd-early-io: early-io begin; safe to power off
msd-early-io: LCD bound skipped hardware-absent
msd-early-io: keyboard ready skipped hardware-absent
msd-early-io: early-io end hardware-absent-qemu
```

module期限対照でも、時刻prefixなしの行を確認しました。

```text
msd-early-io: early-io begin; safe to power off
msd-early-io: loading gpio-forwarder; safe to power off
msd-early-io: waiting elapsed=2 limit=3; safe to power off
msd-early-io: early-io end failed; boot blocked; safe to power off
```

対照の/dataとreadyは各0件、boot試験器は予定どおり124で終了しました。
監視終了の後処理はQMP quitでなくSIGTERM fallbackで、processはreturncode 0・reaped trueです。
これは正常起動の成功ではありません。事後照合の初版は通常A用のQMP条件を対照にも適用してAssertionErrorとなりました。
QEMUは再実行せず、対照を当初の基準（console進捗・失敗・/dataとreadyの不在・終了124）で照合し直しました。

両logにはbase kernelの`__ioremap_prot` warningとmmc1 timeoutもあります。
同じwarningは先行04のlogにもあり、LCDの実probeや今回のconsole送信の成功を示す行ではありません。
ログは省略・上書きせずに保存しています。

## 入力・証拠のSHA-256

`run-qemu: sha256`が示す実行binary・kernel・Bluetooth無効化後DTBは次のとおりです。

| 入力 | SHA-256 |
|---|---|
| QEMU | `8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73` |
| kernel Image | `c651cfd86fcb08943a863ecbc31f6fa0f2f6fea0f7c7bcd25fc8e3cdd327c261` |
| 実行DTB | `887a37243ffa9cd8eedd9d3690c0aea6c9e81ad4ecc6ad0b15503e38b24164d2` |
| fixture生成器 | `ce5a9bd8aa094f7fe710cea9affca77c7d059bc32c18054a5a7bd9920da7271b` |
| console C source | `0c4e0ad8447552a42b80aab4fbdef41ecc1f40b53126a1782edd034a625287d1` |
| 収録したmsd-console（両条件共通） | `d8d632c5b10d37795e41f6f6d07ea5243484b278072381a1be12e9dba2552c82` |
| 通常SD image | `53ced0b387547b6af7a0ec9fd75482196870551a47a18987f46e79bf7add8223` |
| 対照SD image | `68d7eb64ab6ed79fc30d8a5ecc5706b3ece276efca695b7231f470688ad7b407` |
| 通常fixture.json | `16eca2d393fa6b5fbb474ddfdf911a006642922d15e75d167b3ffeaf56b64106` |
| 対照fixture.json | `1c92f9862183bd077f79b4bafb3da9125a8b5d13350e3701d10d8ab1bd8f1ee6` |
| 通常serial log | `9775b0627fd970f67edb3799da43c99df8da26d9d9bfbc9df7ac700ccc43362f` |
| 対照serial log | `22bdcc66ae5dcd5eecb689969632885dbd8afab6e775d0460b94a58df8a26757` |

logは各出力先の`logs-a/serial-mmcblk0p5.log`、終了状態は同名の`.process.json`にあります。
base image・SquashFS・BusyBox・各helperのhashは各`fixture.json`にも保存しました。
通常Aと対照はいずれも基準sourceにfixture修正を加えた作業treeで実行し、実行中のsourceは変更していません。
生成器のhashで今回の修正を識別します。新しい製品imageやBの試験と混同しません。
実機のLCD・keyboard・SPI/I2C・電源断は検証しません。QEMUの対象hardwareは不在です。
