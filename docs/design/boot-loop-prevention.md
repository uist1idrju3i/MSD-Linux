# boot loop防止（案・未決定）

2026-11-17。「tryboot試行slotの即時resetは許容、既定slot／両slot破損の無限resetは不可」が利用者決定。[rootfs設計][RD]／[error option調査](../research/storage/dm-verity-error-options.md)の補足案。実装・実験・例外承認なし。

Phase CはC={restart_on_corruption, panic_on_corruption}×E={restart_on_error, panic_on_error}の4組。既定EIO、ignore、検査専用EIO mapperは除外。本案は次回root前の選択を制御します。

## 1. 現行の事実と実行できる場所

fresh origin/main **2ece5cc86f4c84d59ff628999a484424d8828ad3**を静的確認。U=[msd-update][U]、F=[kernel fragment][F]。行番号はこの版です。

| 根拠（path:line） | 現行と設計上の制約 |
|---|---|
| [genimage.cfg:1-26,38-80][G] | p1=bootsel FAT 16MiB、p2/p3=boot-a/b FAT各64MiB、p4=拡張、p5/p6=rootfs各256MiB、p7=data。p1はautoboot/bootcode、p2/p3はfirmware/kernel/DT/config/cmdline。rescueなし |
| [post-image.sh:26-49][PI]、U:179-218 | build時image作成。installは署名・hash確認後inactive boot/rootを書きreadback、dataのinstalledをfsync/rename |
| [autoboot.txt:1-5][AB]、[config.txt:36-41][CF] | tryboot_a_b=1、既定boot 2、試行3。boot 2→root p5、3→p6のcmdlineを選ぶ |
| U:221-235 | installed、DT、p1を照合し`reboot '0 tryboot'`。**try自身は永続pending-attemptを書かない**。installedは候補で試行回数ではない |
| U:238-269 | tryboot=1・installed一致を要求。p1のautoboot交換をfile fsync→rename→directory fsync。その後dataのcommitted記録・installed削除。単一transactionではない |
| [Buildroot rcS:3-6,23][RC]、[S01:8][S01] | 数字順にinit実行。S01で`watchdog -T 15 -t 5 /dev/watchdog`。root mount失敗には間に合わない |
| [S98:13,40-70][S98]、[S99:8-24][S99] | ready作成・表示後、trialのみhealth判定。root=squashfs、data=ext4、readyありならcommit、失敗ならreboot。全root検証・継続稼働の保証ではない |
| [cmdline A:1][CA]／[B:1][CB]、[defconfig:28-41][DC]、config全体 | SD root直接mount。製品initramfsもdm tableも未実装。将来は[rootfs設計:93,130-133][RD]のdm-mod.create。現状root前にはshell、U、S01/S98/S99なし |
| F:35-40,52-56、cmdline両slot | DM_INIT/VERITY/FEC、BCM2835_WDT、PSTORE/RAM=y。panic timeout指定なし。WDT開始前のpanicは永久停止もある |
| [書込み台帳:9-29,69][WP]、[AGENTS §10](../../AGENTS.md#10-製品の規則) | 自動counter等には理由・時機・量・表示を伴う例外承認が必要。S99自動commitも表示なし・未対応。log/cacheはRAM |

### firmwareとkernelの一次資料

kernelは[defconfig:31][DC]固定のrpi 6.18.59。一次URLはcommit固定。[PR #269 archive](../research/storage/dm-verity-error-options/evidence.tar.gz)にsource/hashがあります。

| 一次資料 | 確認した仕様／未確認 |
|---|---|
| [公式autoboot:9-40][AUTO]、[tryboot:80-98][TRY] | rebootのpartition指定優先。trybootは起動前clear、次の通常resetで既定へ。tryboot_a_bはpartition単位。**既定破損なら戻るだけでは復旧しない** |
| [bcm2835_wdt.c:95-140][WD]、[raspberrypi.c:186-222][FW] | 数値0〜62をPM_RSTSのpartition bitへ、` tryboot`をfirmware flagへ。63はhalt用途だが`reboot 63`を停止手順とはしない。registerを独自counterへ転用しない |
| [boot設定:242-271][BOOT]、[EEPROM設定][EEP] | kernel_watchdog_timeout/partition、BOOT_WATCHDOG_TIMEOUT/PARTITION、高番号のreset識別等。BOOT系はPi4/5用。CM0・固定firmwareのrescueは未確認。verity失敗counterではない |
| [dm-verity-target.c:207-211,535-568][VT]、[reboot.c:280-301][KR] | reasonはC=`dm-verity device corrupted`、E=`dm-verity device has I/O error`。notifier→shutdown→machine_restart(cmd)。固定文字列はslot/trybootを指示しない。変更にはpatch等が必要 |
| [panic.c:558-582][KP] | panic=0は待機、正は秒数後、負は即emergency_restart。通常restartと別経路、reasonなし。timeout/WDTは回数制限ではない |
| [ramoops.rst:11-26,38-49][RAM]、F:55-56 | 保持RAMへpanic等を記録。max_reasonで対象が違う。専用予約・回収daemonなし。CM0のwarm reset保持、firmware上書き、cache、初期利用は未確認。電断で失う |

## 2. 選択肢の比較（推論）

修復は別機構。firmware/kernelまで読めなければ同じSDだけで表示・復旧を保証できません。

| 案 | loop防止と両slot失敗 | SD書込み・時機／摩耗 | 電断時の整合 |
|---|---|---|---|
| a. 毎boot FAT counter、health後clear | Nで別slot／停止。health直後の破損ではclearがloopを招く | 毎boot加算・healthでclear。高頻度、例外要承認 | renameの原子性を仮定せず、更新不明なら停止 |
| b. 更新前pending＋既定counter | trialはone-shot、既定N回。両slot失敗履歴も必要 | 更新時pending、既定boot加算。installedとは別 | pending/selector/data不一致は停止 |
| c. ramoops／保持RAM register | 次bootで失敗slot除外。欠損を正常扱いするとloop | SDなし、電断で禁止状態を失う | cold boot、欠損、古い記録が弱点。補助のみ |
| d. firmware partition／tryboot | 別bootへ移るだけ。往復loopには別の上限が必要 | reboot引数はSDなし、autoboot変更はFAT write | 永続counterではない。電断・再armに注意 |
| e. panic timeout＋WDT／停止 | 単独ではloop防止不可。0＋reset停止はhalt候補、restart modeは別 | SDなし | RAM表示消失。WDTが残ると停止不可 |
| f. initramfs chooser | root外で上限・停止。a/b/c等と組合せ | 自体はRAM、状態方式に依存 | 状態不明ならrootへ進まない |

| 案 | root mount前／panic経路 | initramfs | firmware依存 | 複雑さ・未確認 |
|---|---|---|---|---|
| a | root上script不可／panic前にarm | root前には必要 | slot切替 | 中。FAT耐電断、runtime failure |
| b | 同上、既定root失敗も数える | 必要 | one-shot | 中。pendingとcommit整合 |
| c | 次bootで読む／panic記録はbest effort | root前には必要 | RAM保持・register所有権 | 中〜高。restart/早期panicの記録漏れ |
| d | kernel handlerならroot前も候補。userspace/ueventはfatalに間に合わない | handlerだけなら不要 | **CM0で未確認** | 高。通常restartとpanic/WDTの別経路 |
| e | kernelで可能だがLCD文言は別基盤が必要 | 単純haltだけなら不要 | WDT停止可否 | 低〜中。hung CPUと意図的停止の区別 |
| f | root前arm、panic後は次bootで判定 | 新規 | kernel切替 | 高。依存closure、RAM/時間/容量、LCD、自身の故障 |

## 3. 推奨案（未決定）

**f＋bの永続arm/失敗集合＋dの一回切替**を推奨。cは診断補助。root前panicとhealth後の破損を事前記録で扱います。SD write例外を認めなければ、独立した保持機構の立証か自動復旧の断念が必要です。

### 状態と遷移の案

- p1にschema、bundle世代、sequence、armed slot、failed A/B、切替済み、STOPを記録。Nは**障害対応中に各slot最大1回**を提案。正常boot回数とは別です。空・読取り不能・版不明はSTOP。初期状態はimageで用意します。
- boot-a/bに最小initramfsを加え、serial・LCD/font・状態I/O・WDT制御をrootから独立。先行dm-mod.createを避け、chooserが状態確定後に同じkernel targetを作ります。crc32c/FEC・4 modeは維持します。
- DT slotと照合し、前回armedが残ればそのslotを失敗集合へ。panic／電断不明も成功扱いしません。正常slotを誤除外し得ます。
- **root読取り前にarmedを保存・flush・readback**。失敗ならSTOP。panic中のFAT writeは行いません。trialにもarmを書くので、bのwrite削減案そのものではありません。
- 別slotへは切替済み・予定先を保存しreboot N等で一度だけ対応kernelへ。同じkernelで相手rootだけを使うABI混在は避けます。予定先に来なければ再redirectせずSTOP。CM0実証までは有効化不可です。
- trialのfatalはone-shotで既定へ戻る想定。既定も失敗ならSTOP。既定破損は他slotを一度試し、両slot失敗・予算切れ・状態不明ならSTOP。trybootを再armし続けません。
- **healthでarmedをclearしません。** 稼働後panicも対象です。正常な利用者の停止／再起動だけ、一回限りの予定reset許可を保存する案。次bootで消費してからarmし直します。自動failure処理はこの許可を作れません。保存直後のpanicを誤認しても、利用者の新操作なしに許可を再発行しません。
- failed・切替予算はhealthやclean shutdownで復活させず、bundle書直し／明示した保守操作でのみ新世代へ。recovery先の昇格も利用者確認後。既存S99→commitは統合前に流用不可。STOPは電源入直しだけでは解除しません。

### 耐電断・書込みの条件

世代・checksum付き2記録を交互更新する案。古い記録へ戻すと再試行し得るため、途中・矛盾はSTOP。初期化・fsync・readback・再boot許可を仕様化。FTL/flushは未確認で、二重化/CRC/renameを耐電断保証とはしません。selector不一致も停止します。

状態writeのbytes/回数、metadata/flush、失敗時停止、表示を[台帳][WP]で例外審査。既存未対応は未承認のまま。logはRAMのみです。

## 4. 両slot失敗時の停止と利用者表示（案）

STOPでは**root外のchooserを稼働させ**画面を維持。WDTは給餌し、停止可能と実証した場合だけ無効化。panic=0に頼らず次bootもSTOP。LCD/font・serialは状態write前に初期化する案で、描画未確認です。

| 状態 | LCD・serial文言（EN / JA） |
|---|---|
| 起動判定 | `Checking boot state: {s}s. Do not power off while saving.` / `起動確認中：{s}秒。保存中は電源を切らないでください。` |
| 失敗slot回避 | `Slot {x} failed. Trying {y} once.` / `slot {x}失敗。{y}を一度試します。` |
| 両slot失敗 | `Both slots failed. Reboot stopped. Rewrite from a verified update bundle.` / `両slot失敗。自動再起動を停止。検証済み更新bundleから書き直してください。` |
| 状態不明 | `Invalid boot state. Boot stopped. Use recovery media or a PC.` / `起動状態不明。起動停止。復旧mediaまたはPCを使用してください。` |
| 停止完了 | `Not writing. You may power off.` / `書込みなし。電源を切れます。` |
| 復旧write | `Rewriting {x}: {done}/{total} bytes. Do not interrupt or power off.` / `slot {x}書直し中：{done}/{total} bytes。中断・電源断はしないでください。` |

2秒以上なら経過/bytesを継続表示。読取り/確認は保存前に中断可。保存〜flushは中断不可と前後に表示。未完了write中は電源断可としません。自動修復・format・既定交換なし。

両root破損では独立環境でbundle署名・hashを確認し、同意後にslotを書直します。この復旧commandは未実装、現行Uも壊れたrootでは動きません。boot/kernel/chooser・p1も壊れれば表示を保証せず、[PCで全SD再作成](../INSTALL.md)へ。

## 5. 利用者が決めることとPhase Cへの追加

1. initramfsと状態write例外を認めるか。認めない場合の代替・保証範囲。
2. N=各slot1回、電断/欠損の失敗扱い、STOP保持と解除。誤除外をどこまで許すか。
3. fallback昇格・commit統合、bundle世代/downgrade時の予算、正常停止許可。
4. 状態配置・耐電断条件、LCD初期化失敗時のserialのみ停止の可否。
5. panic timeout/WDT引継ぎ。約15秒はscript要求値で実機保証ではありません。

承認後に「initramfsなし」の計画を改訂し、4 mode×trial/既定×root mount前/S01前/health後、単独/両slot破損、実I/O失敗を事前登録。slot列・RESET数・状態・health/commit時刻から、上限Nと状態不明時の再試行ゼロを判定します。正常/FEC回復、空/短い/不正版/破損状態、write/readback失敗、torn記録、古いpstore、selector不一致、redirect無視、中断もfixture化。**まだ実行しません。**

QEMUのpanic条件は[run-qemu.sh:97-99](../../board/cardputerzero/qemu/run-qemu.sh)の`QEMU_WATCHDOG=1`必須。WDT前の停止と稼働後resetを分けます。[test-ab.sh:5-7](../../board/cardputerzero/qemu/test-ab.sh)はp6固定、tryboot模擬ではありません。host模擬と実firmware復帰を混同せず、時刻付きblock write・進捗/中断/英日表示、実機warm reset/電断/両slot失敗/LCDを別途受入検証します。完了まで出荷可とはしません。

[U]: ../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update
[F]: ../../board/cardputerzero/linux.fragment
[G]: ../../board/cardputerzero/genimage.cfg
[PI]: ../../board/cardputerzero/post-image.sh
[AB]: ../../board/cardputerzero/autoboot.txt
[CF]: ../../board/cardputerzero/config.txt
[S01]: ../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog
[S98]: ../../board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready
[S99]: ../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health
[CA]: ../../board/cardputerzero/cmdline_rootfs_a.txt
[CB]: ../../board/cardputerzero/cmdline_rootfs_b.txt
[DC]: ../../configs/msd_cardputerzero_defconfig
[RD]: ../research/storage/rootfs-squashfs-verity-fec-design.md
[WP]: write-policy.md
[RC]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/initscripts/init.d/rcS#L3-L6
[AUTO]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/autoboot.adoc#L9-L40
[TRY]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/bootflow.adoc#L80-L98
[WD]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/watchdog/bcm2835_wdt.c#L95-L140
[FW]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/firmware/raspberrypi.c#L186-L222
[BOOT]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/boot.adoc#L242-L271
[EEP]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc
[VT]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-verity-target.c#L207-L211
[KR]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/kernel/reboot.c#L280-L301
[KP]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/kernel/panic.c#L558-L582
[RAM]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/ramoops.rst
