# /dataより前のLCD・キーボードの準備

## 範囲と起動順序

`S02a-msd-early-io`を`S02msd-data`より前に同期実行します。
BusyBoxのrcSは子scriptの失敗後も進むため、準備の失敗時はinit script自身が待機し、後続を実行しません。
S02にも独立した状態確認を置き、状態が欠けている場合も、format・fsck・mountより前で止めます。
watchdogの給餌は既存のS01 daemonが続けます。失敗待機から自動retryはしません。

helperは[early-io](../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/early-io)です。
S10のmodalias走査は前倒しせず、次のmoduleだけを読み込みます。

1. `gpio-forwarder`
2. `m5ioe1`
3. `pwm_bl_m5stack`
4. `panel-mipi-dbi-m`
5. `tca8418_keypad_m5stack`

ELF依存はmodprobeとmodules.depに任せます。DTのprovider依存はこの順序と準備待ちで扱います。
firmwareとkeymapの存在を先に確認します。LCDとキーボードはDTのcompatibleとdriverのbindで識別します。
DRM・fb・backlight・inputは、対応するdevice配下のsysfsとdevtmpfsのnodeを確認し、番号を固定しません。
input名`tca8418c`を確認して既存helperでsymlinkを作り、loadkeysが成功して初めて準備完了とします。
S04は状態確認だけにし、keymapを再読込みしません。

## 期限と失敗時の制御

既定の準備期限は20秒です。全module、loadkeys、device待ちで一つのmonotonic期限を共有します。
時刻はuptimeの整数秒を使い、外部command停止の丸め差は1秒未満です。
外部commandには残り時間をtimeoutで渡し、期限後はKILLします。kernel内の割込み不能な処理からの復帰を保証するものではありません。
timeout、module・bind・firmware・keymap・inputの不備では成功状態を残しません。
`MSD_EARLY_IO_TIMEOUT`は1〜60秒の診断用設定です。`MSD_EARLY_IO_ROOT`はhost試験の偽rootに使います。
製品のinit scriptはどちらも設定しません。

状態はtmpfsの`/run/msd-early-io/state`だけへatomic renameで保存します。
準備開始時は`failed`に戻し、成功時だけ`ready`にします。PINや解錠はまだ実装していません。
将来の実機PIN処理は`ready`だけを入力可能の条件にし、下記のQEMU状態を入力成功と扱いません。

## QEMUでhardwareが無い場合

通常の製品cmdlineには例外を設定しません。DT nodeが欠けた実機は起動を停止します。
QEMU launcherだけが`msd.early_io=qemu`を追加します。例外は次のすべてが一致した場合に限ります。

- mode指定が一つだけで、値が`qemu`。
- DT rootがPi 3BまたはCM0の既知compatible。
- LCD、キーボード、M5IOE1、GPIO forwarder、backlightのcompatibleがすべて無い。

一部だけ残るDTや未知のmachineは例外にしません。
状態は`hardware-absent-qemu`とし、LCD bound・keyboard readyのmarkerにも`skipped hardware-absent`を付けます。
これはemulatorの暗号学的な識別ではなく、試験launcherからの明示指定です。製品boot設定へコピーしません。
重複modeは拒否するため、QEMUで`QEMU_EXTRA_APPEND=msd.early_io=required`を追加すると失敗側を試せます。

## 書込み・表示と残件

moduleとfirmwareの読取り、kernelの登録、devtmpfsのsymlink、tmpfsの状態だけを変更します。
永続fileへの保存は追加しません。[書込みの台帳](write-policy.md)の既存S02の未対応を解消したものではありません。
boot中の画面の文言は、利用者が決めた案Cに従い、英語だけにします。
kernel fbconでは日本語を描けないためで、[AGENTS.md §10の例外](write-policy.md#boot中の画面の文言案c)として理由と範囲を記録しています。
開始・module段階・device待ちの経過・終了・中断可否をconsole/kernel logへ英語で出力します。secretは扱いません。

markerは`early-io begin`、`LCD bound`、`keyboard ready`、`early-io end`です。
将来の測定はPINの人間待ち時間とdriver準備時間を分け、同一buildのA/A、初回と通常起動を分けて各5回以上測ります。
今回のsoftware試験を起動時間の改善値へ転用しません。

実機の残件は、driver bindとsysfs配置、firmwareの実配送、最初の可読frame、backlight、英語の文字とprogressの見え方、全必要keyとkeymap、
入力の取りこぼし、watchdog、I2C/SPI、A/B両slot、実SD write・FTL・電断です。
QEMUのhardware-absent成功は、表示・入力の確認ではありません。

## 再現手順

host試験は`tests/early-io/run.sh`です。偽sysfs・modprobe・loadkeysで正常、欠損、期限、失敗時停止を確認します。
既存initの回帰試験は`tests/init-scripts/run.sh`、QEMU supervisorの試験は`tests/qemu-boot/run.sh`です。

既存buildから別のfixtureを作る場合は、固定開発image内で次を実行します。
これは新規製品full buildではありません。baseのkernelとlibraryを使い、変更したinit/helperとtimeoutを有効にしたBusyBoxを両slotへ入れます。
実行するsourceは変更せず、生成物・入力hashは指定した別directoryに保存します。

```sh
docker/msd-dev python3 board/cardputerzero/tools/bench/early-io-fixture.py output-openssl-lts output-early-io-new
OUTPUT_DIR="$PWD/output-early-io-new" QEMU_MACHINE=raspi3b QEMU_MODULE_TEST='' QEMU_BOOT_TIMEOUT=120 QEMU_LOG_DIR="$PWD/output-early-io-new/logs-a" docker/msd-dev board/cardputerzero/qemu/test-boot.sh
OUTPUT_DIR="$PWD/output-early-io-new" QEMU_MACHINE=raspi3b QEMU_MODULE_TEST='' QEMU_BOOT_TIMEOUT=120 QEMU_LOG_DIR="$PWD/output-early-io-new/logs-b" docker/msd-dev board/cardputerzero/qemu/test-ab.sh
```

moduleの実load試験はこのQEMU条件から除外しています。fixtureの元imageと生成imageのhashは`fixture.json`を参照します。
期限の負対照は生成器の`--module-timeout`を別directoryに指定します。
試験専用wrapperがRAM上に偽DTとsleepするmodprobeを作り、同じ製品helperを3秒期限で呼びます。
実際のBusyBox timeoutと進捗表示、失敗後にS02へ進まないことを確かめるためのもので、driverの実probeではありません。
このwrapperは製品overlayへ入りません。通常のA/Bは上記を一つずつ実行します。
gate導入時のQEMU結果・入力hash・失敗した構築は[検証記録](../experiments/2026-11-25-early-io.md)に残しています。
案Cへ文言を変えた後のQEMU起動と実機表示は未確認です。
