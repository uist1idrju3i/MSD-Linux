# CM0向けSDIO firmware配送の最小化

- 状態: 現行CI artifactの再pack・QEMU比較完了。実機・新規full buildは未実施
- 日付: 2026-11-23
- 基準: `922b245f9eb674d7ea27d508dca1d58fbda0328f`
- 関連: [kernel・firmwareの設定面](../research/component-options/kernel-firmware.md)

## 目的と採否の基準

候補1〜3を適用した現行CI artifactから、対象外の無線firmwareだけを削る。
採用条件は、保持集合の欠損を削除前に拒否すること、残すfileとsymlinkの不変、
rootfs通常file合計と同条件SquashFSの減少、前後のQEMU A/B全4 boot成功、
各bootのloadkeys終了0、moduleの名前・サイズ・依存・状態の一致である。
同じ入力のA/AはSquashFSのSHA-256一致を要求する。
容量と構築可否の単回比較なので性能の中央値は求めない。容量削減を起動時間の短縮とは扱わない。

## chipの資料と保持方針

[M5の製品資料](https://docs.m5stack.com/en/CardputerZero)は搭載moduleをRaspberry Pi CM0としている。
[CM0 datasheet Release 3、§2.1（印刷ページ4）](https://pip-assets.raspberrypi.com/categories/1286-raspberry-pi-compute-module-zero/documents/RP-009251-DS-3-cm0-datasheet.pdf)はCypress CYW43439を明記する。
datasheet PDFのSHA-256は`861c9d1849bf206cce79bfa1beaabe8f86b195356f8db8d534b58cb49e8cd28e`。
一方、固定firmwareにはCM0専用の43430/43436s名から43436sの実体へのaliasがある。
[Raspberry Piの配送commit](https://github.com/RPi-Distro/firmware-nonfree/commit/be2ca149fd609844a5d43b4dfa7d5ee56d9a7534)にも同じ対応がある。

datasheetとfirmware aliasが一致せず、対象実機のchip ID・revision・BT subversionも未取得なので、
単一familyには絞らない。利用者の承認に従いCYW43439、CM0専用43436sとそのfallbackを保持する。
両者が同一chipの別名だと確認したわけではない。chipを識別できないまま他board向けのfirmwareを流用する変更もしない。
board固有のCYW43439 fileが存在すれば優先して残すが、別boardのNVRAMから新しいCM0用fileは作らない。

## kernelが名前を作る規則

固定kernelはRaspberry Pi Linux `b3495ea401d709af0701a85babcba5e3d788a602`（6.18.59）。
以下はそのsourceから導いた規則で、実機で選択された名前の観測ではない。

| source | 名前の選択と保持への対応 |
|---|---|
| [sdio.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/sdio.c) | chip IDとrevision maskで基底名を選ぶ。43439は`brcmfmac43439-sdio`、43430 revision 1は`brcmfmac43430-sdio`。`.bin`、`.txt`、`.clm_blob`を区別する |
| [of.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/of.c) | `brcm,board-type`がなければroot compatibleの先頭をboard名にする。CM0 DTSは`raspberrypi,0-compute-module`。Wi-Fi compatible自体は汎用の`brcm,bcm4329-fmac` |
| [firmware.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/net/wireless/broadcom/brcm80211/brcmfmac/firmware.c) | 拡張子の前に`.`とboard名を挿入した候補を先に探し、汎用名へfallbackする。board固有のbin・txt・clm_blobも保持対象にする |
| [btbcm.c](https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/bluetooth/btbcm.c) | UARTのsubversion表からhw名を得る。`0x2310`はBCM4343A2、`0x2209`はBCM43430A1、`0x410c`はBCM43430B0。`brcm/HW.BOARD.hcd`、`brcm/HW.hcd`、`brcm/BCM.BOARD.hcd`、`brcm/BCM.hcd`の順に探す |

対象機のBT subversionは未取得で、実際に選ばれるBT名は未確認である。
`0x2310`ならBCM4343A2を探すため、このpatchを保持する。
43430A1/B0の汎用patchも保守的に残し、実機で選択名を確認してから再検討する。

## 配送optionと代替手段

固定Buildrootは`bbbdab36565d4941b6b0449a0eedb5aac8a10c2e`、
firmwareはLibreELECの`6596d332eaadd63e2413e3937715a084f61c39e2`。
upstreamのfirmwareはデータfileで、configure等によるchip選択optionはない。
`Config.in`のconfig token全3件を次の表と機械照合する。

[設定表と採否](../research/component-options/kernel-firmware.md#cm0のsdio-firmware配送)にpackage全3 optionと関連設定をまとめた。
2026-11-23取得のLibreELEC最新HEADも固定値と同じ。Buildroot masterのConfig.inは固定版とbyte単位で一致した。
取得物とsourceのhashは証拠archiveに保存した。firmware packageのlicenseは`PROPRIETARY`で、
Buildrootのlegal-infoやLICENSEを削る変更はしない。Blobの版・保守状況・CVE対応を改善したとの主張もしない。

recipeは`brcm/*.hcd`・`synaptics/*.hcd`と`brcm/brcmfmac*`・`cypress/cyfmac*`をまとめてcopyする。
`rpi-firmware`はboot/GPU側であり、このSDIO配送の供給元ではない。
linux-firmwareへの切替は、CM0専用NVRAM・alias・BT patchの対応と許諾を別に確認する必要があるため見送る。
vendorを編集せず、external post-buildの保持集合とsymlink到達先を検査してから不要分を削る。
未知の別package用fileやlicenseは削除しない。firmware探索path等の実行時設定は変更しない。

## 条件と実行計画

比較元は[CI run 45151315876](https://github.com/uist1idrju3i/MSD-Linux/actions/runs/45151315876)のartifact `14806469903`。
producer HEADは`99c89412ede4571955e72c73065c8ec74d7836ca`で、候補1〜3適用済み。
ZIPのSHA-256は`01b9950a0bac0cd848e619b843981f15a0da945d94527fc51f2a4625d64059f2`。
原本は読取り専用とし、SD・rootfsは使い捨ての写しを使う。新規full buildやccacheの比較ではない。
同じhost tool、sort、zstd level 22、block 131072、時刻0、root所有者でpackする。
観測hookは両側で同じものを使う。rootfs通常file合計はhook追加前、SquashFSはhook追加後のbytesである。
symlinkのbytesは通常file合計に加えない。

runnerは実行commit、入力・tool・script・serial除外一覧のhash、tool版、UUIDのrun_prefixを保存する。
planとCSVはtemplate列を使い、失敗後の再試行でも新しい空の出力先とUUIDを使う。
欠損した必須BT patchを使った負の対照では、他fileの削除前に拒否することを要求する。
各条件のA/Bを1回ずつ起動し、moduleはaddress・参照数を除いて比較し、生の行も保存する。

## 結果と保持file

実行commitは`7fc0e8906345d31116821d82e574207958ba91cc`、
run_prefixは`sdio-2b74f2b17fdd48268480f25641d26fe0`。
rootfs通常file合計47,359,454から45,600,428 bytes、SquashFS 25,088,000から24,018,944 bytesになった。
差はそれぞれ **−1,759,026 bytes**、**−1,069,056 bytes（1,044 KiB）**。
A/AのSquashFS SHA-256は両方`be0ea79a448f4716e04ee76d73e1f97e61e6b73032196883f3533e64db9ee141`。
afterは`bce3af6c51e65d2c0fd1ff9a5853432c4be2e4d15848ea684f10fe91c40555ec`。
13 regular fileと56 symlinkを削除し、残すfile・symlinkの内容変更は0だった。
実firmwareだけではなくrootfs全体を比較した値である。

全92 entryの名前・通常file bytes・hash・symlink到達先・採否は
[配送一覧](../research/component-options/sdio-firmware-files.csv)にある。
保持21 entryは以下のとおり。LCD用93 bytesとBMI270用8,192 bytesの2 fileも変更しない。
以下の相対pathには`lib/firmware/`を付ける。`{a,b}`は両方を表す。

| 用途 | 残す名前・到達先 |
|---|---|
| CYW43439 | `brcm/brcmfmac43439-sdio.{bin,txt,clm_blob}` → `cypress/cyfmac43439-sdio.{bin,txt,clm_blob}`。計6 entry |
| 現行CM0専用 | `brcm/brcmfmac43430-sdio.raspberrypi,0-compute-module.{bin,txt}`、`brcm/brcmfmac43436s-sdio.raspberrypi,0-compute-module.{bin,txt}` → binは`brcm/brcmfmac43436s-sdio.bin`、txtは`brcm/brcmfmac43436s-sdio.nolpo.txt`。汎用の`brcm/brcmfmac43436s-sdio.txt`も保守的に残す。計7 entry |
| 43430 fallback | `brcm/brcmfmac43430-sdio.{bin,clm_blob}` → `cypress/cyfmac43430-sdio.{bin,clm_blob}`と、`brcm/brcmfmac43430-sdio.txt`。計5 entry |
| BT patch | `brcm/BCM4343A2.hcd`、`brcm/BCM43430A1.hcd`、`brcm/BCM43430B0.hcd`。計3 entry |

43439のboard固有`.raspberrypi,0-compute-module.{bin,txt,clm_blob}`は現行artifactに存在しない。
現行kernelのboard優先・汎用fallbackの規則に従い、上記の汎用3種を残す。
将来追加された場合はboard固有3種と43430/43436sのCM0用clm_blobも保持する。
BTの`{BCM4343A2,BCM43430A1,BCM43430B0,BCM}.raspberrypi,0-compute-module.hcd`と`BCM.hcd`も、
存在すれば保持する。相対symlinkを再帰的に辿り、必要な実体も残す。
欠損・空・絶対symlink・領域外参照・循環は削除前に拒否する。保持集合は冪等で、欠けた必須fileを黙って省略しない。

QEMU前後A/B全4 bootはreadyとloginに到達し、終了0。
各logの`LOADKEYS_RESULT`は終了0、各19 moduleの名前・サイズ・依存・状態が一致した。
全4回ともQMP quit、process reap、QEMU returncode 0で、fallbackは空、errorはnullだった。
必須`BCM4343A2.hcd`欠損の負の対照は削除前に拒否し、他fileは不変だった。
host試験では正常・冪等性・空・欠損・不正alias・任意のboard固有aliasの到達先保持、
失敗した再試行のUUID分離・未実施21行の保存も確認した。

## 実行環境と証拠

pack用hostはDebian GNU/Linux 13、SquashFS 4.7.5、sfdisk 2.41.5、
SDK GCCは14.3.0。kernelとImageは上記CIから取得したもので、GCCによる新規compileはしていない。
QEMUは11.1.3。使用した`msd-dev:local`のimage IDは
`sha256:1aea11386e31cc82eff0807de3e372a0b4443c881f3bc3765a56810b32e2ca65`。
全4 serialの以下の行を確認した。

```text
run-qemu: sha256 8b5c759a21dd5d841d96b37be4e60e3b324869dff22250b581c856e36ac15b73  /usr/local/bin/qemu-system-aarch64
```

| 入力 | SHA-256 |
|---|---|
| `prune-sdio-firmware.py` | `9aff30892f91f32ce89c1fea8fb097fd3093b451b13909a2bd357c29b960c8a7` |
| `bench/sdio-firmware.py` | `1c6539254d3c653d2412836b30d317bfd20441f96032594dcbc99da745ccd432` |
| `squashfs-sort.txt` | `d0eaa8edda7da4c33aa670641bc1d2b2a042cd1175d0d442a142ed1eb0452e3c` |
| `post-build.sh` | `09c168d02cb43bcce28b5f01de4021434798653cd18a1bb43f6c5def0ca71f3c` |
| `qemu/serial-allowlist.txt` | `4a88637ae9593329d2d191da9a92efb62c56162f670d069816b952a359d9bece` |

その他の共通runner・boot試験・serial判定script、tool、入力Image・DTBのhashはresults.jsonに記録した。
共通の観測hookとsortの実体もarchiveに保存した。現行正規化configのbtrfs・cryptsetupを含むELFを検査し、
比較元に候補1〜3が適用済みであることを要求した。

[公開CSV](2026-11-23-sdio-firmware.csv)はrunnerのresults.csvのbyte単位の写しで、集計による行削除はない。
全21行がvalid=trueで、通常試行・A/A・負の対照を含む。
[証拠archive](2026-11-23-sdio-firmware.tar.gz)には全21行のCSV・plan、JSON、全4 serial・QMP・終了状態、
build.log、実行source、一次資料の抽出sourceとhash、準備時の失敗出力を保存した。
archive SHA-256は`d80b24f5ebaeaec4b5de83384bf963f3ee11b7655655389b4bcb2d9456e94bda`。

準備時にZIP内の`images/rootfs.squashfs`を直接読む手順は、member不存在のKeyErrorで失敗した。
正式runnerは`sdcard.img.xz`の第5 partitionから展開した。
展開はvar/wwwのuid/gidを変更できない既知の1 warningで終了2となった。
その1件だけを識別し、他のerrorがないことを要求した上で両側ともall-rootでpackした。
正式run自体の失敗・中止・欠損行はない。full Buildroot buildと最新HEADでの製品CIは未実施である。

## 再実行

上記実行commitを使い、ZIPのdigest一致を先に要求する。別のcommitや入力は別条件として記録する。
artifactはZIPのimagesを展開したdirectoryで、比較元は必須fileと対象外firmwareを含む削減前のものを使う。
host-toolsは記録と同じ版のBuildroot host tool directoryである。

```sh
printf '%s  %s\n' \
  01b9950a0bac0cd848e619b843981f15a0da945d94527fc51f2a4625d64059f2 \
  output-sdio-r1/ci-artifact.zip | sha256sum -c - && \
docker/msd-dev make -C vendor/buildroot BR2_EXTERNAL=/work \
  O=/work/output-sdio-replay-config msd_cardputerzero_defconfig && \
docker/msd-dev python3 board/cardputerzero/tools/bench/sdio-firmware.py \
  --artifact /work/output-sdio-r1/artifact \
  --host-tools /work/output-integrity/host \
  --config /work/output-sdio-replay-config/.config \
  --out /work/output-sdio-replay
```

既存の出力先なら停止する。再試行では新しい空の出力先を指定し、UUIDを使い回さない。
実験用の観測hookは通常の製品imageには追加しない。

## 実機で確認する残件

### Review後の事前確認の記録

PR #298のReview後、入力hashの計算を計画保存後の例外処理内へ移した。
今後の試行は従来の21行に`preflight_exit_code`を追加した22行になる。
入力image・config・host tool等の事前確認が失敗しても、UUID、計画、取得済みhash、errorを保存し、
事前確認は終了1・valid=false、未実施の測定は空欄・valid=falseで記録して非0終了する。
host試験ではconfigのhashを実際に計算し、存在しない入力imageのhash計算で失敗する経路を確認する。
初回の公開21行・証拠archive・実行commitは当時のまま保持する。

- brcmfmacが報告するchip ID・revision、実際に選んだbin・NVRAM・clm_blobのfile名と成功/失敗log。
- btbcmが報告するchip ID・revision・HCI/LM subversion、実際に選んだhcdのfile名とpatch適用結果。
- CM0の製造版・board compatible、Wi-Fiの接続・再接続・国別規制、BTの接続。

QEMUには対象SDIO hardwareがない。QEMUのA/B成功やmodule一覧の一致はfirmware読込みの実機検証ではない。
LCD・keyboard・M5 I2C・firmware tryboot・実機SDの電源断耐性もこの比較の対象外である。
