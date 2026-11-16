# dm-verityの破損・I/O errorと再起動loopの設定

2026-11-17。[完全性設計](rootfs-squashfs-verity-fec-design.md)の補足。実験・build・設定変更なし。試行slotの即時再起動は許容、既定slotの無限再起動は回避する要件です。表はsource確認、対策評価は推論で採用判断ではありません。

## 固定版と読み方

main `dd3c09b`の[defconfig:31-33](../../../configs/msd_cardputerzero_defconfig)はrpi Linux **b3495ea401d709af0701a85babcba5e3d788a602**。Makefile:2-4は6.18.59。以下のkernel path・行番号はこのcommitです。

| 略号 | 一次資料 |
|---|---|
| T | [drivers/md/dm-verity-target.c][T] |
| F | drivers/md/dm-verity-fec.cと.h（archive） |
| S | drivers/md/dm-verity-verify-sig.cと.h（archive） |
| D | [Documentation/admin-guide/device-mapper/verity.rst][D] |
| W | [drivers/watchdog/bcm2835_wdt.c][W] |
| C | cryptsetup **v2.8.7**の[man][C]／[table生成][CL]（URLでcommit固定） |
| A/B/E | Raspberry Pi公式文書の[autoboot][A]／[boot設定][B]／[EEPROM][E]（URLでcommit固定） |

Buildrootの[cryptsetup][BC]は2.8.7、[firmware][BF]は`063bcab6c8a90efb0d19f69d88cbbc7ec79cab68`。非公開実装・固定binary/CM0での動作は未確認。source/hash/網羅照合は[evidence.tar.gz](dm-verity-error-options/evidence.tar.gz)へ保存。

現在の[cmdline A](../../../board/cardputerzero/cmdline_rootfs_a.txt):1／[B](../../../board/cardputerzero/cmdline_rootfs_b.txt):1はSD直接rootで**製品dm table未実装**。mode候補は再起動系4組ですが、調査ではEIO等も含めます。

## 1. tableの全optional parameter

T:36-43、F header:26-29、S header:12とparser T:1136-1238を照合した**全13 token**。引数数は値も含みます。未知token・値不足・上限超過は作成失敗です。

| option／source | 6.18.59の意味 | 製品現値 | loopとの関係 |
|---|---|---|---|
| 指定なし（T:161-213,543-572、dm-verity.h:22-26） | C=hash不一致、E=I/O失敗とも既定EIO | tableなし | root失敗からのpanicは別 |
| `ignore_corruption`（T:204-205） | 通知後も不一致dataを返す。I/O失敗は別 | 不採用方針 | 完全性を失う |
| `restart_on_corruption`（T:207-208） | kernel_restart | 候補 | slot/回数制限なし |
| `panic_on_corruption`（T:210-211） | panic | 候補 | timeout/WDT次第 |
| `restart_on_error`（T:535-568） | I/O失敗時にworkqueueからkernel_restart | 候補 | Cとは独立、発火例外あり |
| `panic_on_error`（同上） | 同条件でpanic | 候補 | slot切替なし |
| `ignore_zero_blocks`（T:1060-1092,1180-1188、D） | 期待digestがzeroなら実dataを検証せずzeroを返す | なし | loop制限なし |
| `check_at_most_once`（T:468-475,1190-1196、D） | dataは初回のみ検証。hash blockは従来通り | なし | 稼働後の検出を弱める |
| `use_fec_from_device <dev>`（F:577-586,644-679） | 訂正元。同一device可、data/hash block size一致が必要 | FEC採用 | 訂正成功ならfatal回避 |
| `fec_roots <n>`（F:606-613、header:16-17） | 2〜24 parity symbol。kernelは2を自動補完しない | 未決定、2候補 | 訂正能力の選択 |
| `fec_blocks <n>`（F:588-595,682-714） | 保護data＋hash＋任意metadata総数。data＋tree以上が必要 | 未決定 | loop制限なし |
| `fec_start <n>`（F:597-604、D） | parity開始位置、data block単位。既定0 | 未決定 | loop制限なし |
| `root_hash_sig_key_desc <desc>`（S:25-146） | user keyのPKCS#7でroot hash認証、失敗なら作成拒否 | なし | slot切替なし |
| `try_verify_in_tasklet`（T:1198-1203,241-297） | cache/size条件内はBH検証。I/O/FEC等は通常workqueueへ | なし | mode不変 |

C群3 tokenは排他、E群2 tokenも排他。C/E内は同一token重複もEINVAL。両群は独立、E単独・混合fatalも可（T:1095-1133）。try_verify_in_taskletの重複は許容（T:1198-1200）。既定込みC4×E3＝12組。FEC deviceなしでは他のFEC値だけ指定しても訂正は無効（F:649-650）。

## 2. 何をcorruption／I/O errorと扱うか

| 処理／source | source確認結果 | 製品現値・loopへの意味 |
|---|---|---|
| data（T:405-435） | 再read→FEC。下位bio失敗ならEIO、不一致ならC handler。戻る場合had_mismatch=true | FEC成功はfatal不要 |
| metadata（T:256-310） | hash read失敗もFEC。不一致後訂正不能はC。再入guardは-EIO（F:401-405） | FEC途中でC fatalもある |
| FEC（F:377-387） | 訂正候補も期待hashと再照合、不一致は失敗 | RS正値だけでは成功にしない |
| E条件（T:554-570,614-619） | status非成功、非REQ_RAHEAD、had_mismatch=false、非shutdown | 下位errorすべてではない |
| `DM_VERITY_MAX_CORRUPTED_ERRS=100`（T:34,170-213） | targetごとのlog/uevent上限。以後もhash_failedとmode処理は継続 | 定数、**boot回数制限ではない** |
| uevent（T:198-201、dm-verity.h:29-32） | block diskのKOBJ_CHANGE、`DM_VERITY_ERR_BLOCK_NR=0,<block>`はdata、1はmetadata。ACTION=change/DEVPATH/SUBSYSTEMはlib/kobject_uevent.c:552-558 | C到達時のみ。純粋I/O error/訂正成功は別。userspaceを待たずfatalへ |
| dmesg（T:190-195,208-211,535-559、F:385-387） | `data/metadata block ... is corrupted`はrate limitあり。100回目に`reached maximum errors`。`FEC ... failed to correct (... erasures)`等 | log欠如≠破損なし。audit有効時も別途記録 |
| status（T:779-782） | V/Cはhash_failed。6.18にFEC訂正数なし | V≠全領域検査済み |
| early boot（drivers/md/dm-init.c:269-327、init/do_mounts.c:184-249） | dm-mod.createのread handlerは通常と同じ、全走査はしない | CONFIG_DM_INIT=y。userspace/WDT前のroot失敗はVFS panicもある |

restart引数はCが`dm-verity device corrupted`、Eが`dm-verity device has I/O error`で固定。kernel/reboot.c:101-106,288-300はnotifier→device shutdown→machine_restart(cmd)、arm64/kernel/process.c:127-147はhandlerへ渡します。dm-verityはslotを判定しません。

## 3. build・module・veritysetup

| option／一次資料 | 意味 | 製品現値 | loopとの関係 |
|---|---|---|---|
| `CONFIG_DM_VERITY`、`CONFIG_DM_VERITY_FEC`（drivers/md/Kconfig:544-606） | FECはREED_SOLOMON/DEC8を選択 | [fragment:37-38](../../../board/cardputerzero/linux.fragment)はy | modeは別 |
| `CONFIG_DM_VERITY_VERIFY_ROOTHASH_SIG`と末尾`_SECONDARY_KEYRING`／`_PLATFORM_KEYRING`（同:564-594） | builtin/secondary鍵、失敗時platform鍵で署名照合 | base/fragmentにenableなし | slot変更なし |
| `dm_verity.require_signatures`（S:17-23,123-127） | 署名機能build時のみ、既定false、0444。trueなら署名必須 | overrideなし | SIG_FORCE Kconfigではない |
| `dm_verity.prefetch_cluster`（T:31,48-50,648-674） | 先読みbyte幅、既定262144、0644 | overrideなし | mode不変 |
| `dm_verity.use_bh_bytes`（T:32,52-59、D） | NONE/RT/BE/IDLEのBH上限byte、既定8192,8192,8192,0、0644 | overrideなし | 他の公開use_bh_*なし |
| `--ignore-corruption`、`--restart-on-corruption`、`--panic-on-corruption`（C:177-185、CL:717-719） | 同名underscore table tokenへ変換 | 製品はcrc32cの直接table案 | kernel parserとCLI検査を混同しない |
| `--error-as-corruption`（C:127-129、CL:720-721） | C=restartならrestart_on_error、panicならpanic_on_error追加 | 未決定 | kernel tokenではない |
| `--ignore-zero-blocks`、`--check-at-most-once`、`--use-tasklets`（C:107,187,213、CL:722-724） | 順にignore_zero_blocks、check_at_most_once、try_verify_in_tasklet | なし | 検出範囲／実行contextの変更 |
| `--fec-device/--fec-offset/--fec-roots`（C:131-155、CL:691-696） | FEC4 tokenを生成。offsetはbyteからblockへ | 未実装 | loop制限なし |
| `--root-hash-signature/--no-superblock`（C:192-200、CL:706-709） | 署名key経由でroot_hash_sig_key_desc／header非使用 | 未決定 | modeではない |

CLIはerror-as-corruptionにC=restart/panicを要求し、独立した`--restart-on-error/--panic-on-error`はありません（src/veritysetup.c:665-669、arg_list.h）。kernel tableはE単独・混合fatalも可。`veritysetup verify`はuserspace検証でmapperを作らず、kernelのpanic/restart設定は作用しません（C:69-78、src/veritysetup.c:284-321）。終了0/repairableを完全性の証拠にしません。

## 4. panic・restart・記録・watchdog

K=kernel/panic.c、R=kernel/reboot.c。cmdline両slot・fragment・overlayにpanic/reboot/sysctl overrideなし。実機の実効値は未確認です。

| option／一次資料 | 意味 | 製品現値 | loopとの関係 |
|---|---|---|---|
| `panic=`、`CONFIG_PANIC_TIMEOUT`、`kernel.panic`（lib/Kconfig.debug:1070-1079、K:72,159,558-582,1000） | 正=N秒後、0=待機、負=即時emergency_restart | 指定なし、既定0 | 0でもWDT稼働中ならreset |
| `CONFIG_PANIC_ON_OOPS`、`oops=panic`、`kernel.panic_on_oops`（K:56,165,1023-1031） | Oopsをpanic化 | 既定off | 明示panic()には無関係 |
| `panic_on_warn=`、`kernel.panic_on_warn`（K:63,179,372-377,1002） | WARNをpanic化 | 既定0 | loop制限なし |
| `reboot=`（R:1098-1177） | warm/cold/hard/soft/gpio、panic_ prefix等、arch依存 | 指定なし | slot引数ではない |
| `panic_print/panic_sys_info/panic_console_replay`（K:75-83,551-553,1004-1021） | 出力情報。panic_printはdeprecated | overrideなし | 記録量のみ |
| `CONFIG_PSTORE/CONFIG_PSTORE_RAM`、`ramoops.*`（fs/pstore/ram.c:29-85、Documentation/admin-guide/ramoops.rst） | 予約RAM。mem_address/mem_name/mem_size/mem_type、record_size/console_size/ftrace_size/pmsg_size、max_reason/ecc、旧dump_oops | fragment:55-56はy。独自予約・回収経路なし | reset保持未確認、電断で消失 |
| `bcm2835_wdt.heartbeat/nowayout`（W:48-49,157-162,194-206,244-249） | 初期秒数（0はDT/driver既定）、停止禁止 | fragment:52はbuilt-in。overrideなし、NOWAYOUT既定off | nowayoutは停止困難化 |
| `watchdog.handle_boot_enabled/open_timeout`（watchdog_dev.c:60-73,1322-1329） | boot時に動くWDTを給餌。open待ち0は無期限 | 既定y/0 | 初回armとは別 |
| `watchdog.stop_on_reboot`（watchdog_core.c:47-49,295-304、W:211） | -1はdriver判断、0継続、1停止 | -1、Wは停止要求 | 通常restartとpanicで差 |
| `watchdog -T 15 -t 5 /dev/watchdog`（[S01:8](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog)、watchdog_dev.c:894、BusyBox watchdog.cはarchive） | openでstart、15秒・給餌5秒を要求 | 現行script | 開始前panicは永久停止も。約15秒resetは実機未確認 |

emergency_restartは通常notifierを通らずreasonもありません（R:93-98）。pstoreのpanicと通常restartの記録条件も別。SDへの自動保存は[書込み規則](../../design/write-policy.md)の判断が必要です。

## 5. firmwareのslot選択

| option／一次資料 | 意味 | 製品現値 | loopとの関係 |
|---|---|---|---|
| `boot_partition`、`[all]/[none]/[tryboot]`（A:9-19） | boot FAT選択。reboot指定優先、0は既定探索 | [autoboot:1-5](../../../board/cardputerzero/autoboot.txt)は既定2、試行3 | root健全性は判定しない |
| `tryboot_a_b=1`、`reboot '0 tryboot'`（A:36-40、[bootflow:80-98][FLOW]） | boot前にone-shot clear、通常configを別partitionから読む | autoboot=1、msd-update:221-261でtry/commit | 次resetは既定へ。既定破損はloop |
| `reboot N`／`reboot 'N tryboot'`（A:15、W:95-140、drivers/firmware/raspberrypi.c:186-222） | 0〜62をPM_RSTS bit0,2,4,6,8,10へ。63はhalt。空白trybootはmailbox flagへ | updaterは0 tryboot | dm-verity reasonは非数値、trybootなし。Wは0を選ぶ |
| `kernel_watchdog_timeout/kernel_watchdog_partition`（B:242-271） | bootからWDT引継ぎ、reset後partition指定 | config指定なし | 固定firmware/CM0未確認 |
| `BOOT_WATCHDOG_TIMEOUT/BOOT_WATCHDOG_PARTITION`（E:157-179、B:253） | bootloader timeout/reset先。OS監視は別 | Pi4/5 EEPROM用 | CM0へ適用しない |
| `PARTITION`、高番号条件（E:573-599） | >31のWDT識別値をrecoveryへremapする記載 | 未使用 | CM0未確認 |
| `MAX_RESTARTS/REBOOT_ON_FATAL_ERROR/PARTITION_WALK`（E:181-197,601-607） | BOOT_ORDER反復／bootloader fatal／FAT探索 | CM0で未採用 | **verity失敗counterではない** |

CM0のLinux失敗回数counterは公開資料で未確認。非公開firmware内部の不存在証明ではありません。dm-verityにreboot引数指定optionはありません。

## 6. anti-loop案の評価と未確認

以下はsourceからの推論で、実装・採用・動作確認はしていません。

| 案 | 利点 | 必要条件・限界 |
|---|---|---|
| slot別mode | 試行slotだけ再起動 | table生成変更。panic=0でもWDT稼働ならloop |
| uevent/EIOからuserspace policy | 別slotへ一度tryboot | fatalでは処理前に停止。早期boot用の独立基盤が必要。EIO案は実験対象外、再承認が必要 |
| fatal時にpartition/tryboot指定 | kernel→firmware引数経路あり | 固定reason変更等が必要。両slot失敗時の往復loopにも対策 |
| firmware WDT partitionでrescue | 早期bootを覆う可能性 | 固定版/CM0対応とrescue健全性を確認 |
| 試行数・失敗slotを記憶 | 有限回で停止 | reset/電断保持を設計。SD書込みは規則上の判断が必要 |

再起動系optionだけではanti-loopになりません。ignore/check省略も完全性を弱めます。handler登録・WDT開始/reset原因・固定版tryboot・電断・両slot破損・LCDは実機未確認。QEMU RESET≠firmware復帰です。

[T]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-verity-target.c
[D]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/Documentation/admin-guide/device-mapper/verity.rst
[W]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/watchdog/bcm2835_wdt.c
[C]: https://gitlab.com/cryptsetup/cryptsetup/-/blob/0e2fadbd02be23796006d57d448dbf1080b79cea/man/veritysetup.8.adoc
[CL]: https://gitlab.com/cryptsetup/cryptsetup/-/blob/0e2fadbd02be23796006d57d448dbf1080b79cea/lib/libdevmapper.c
[BC]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/cryptsetup/cryptsetup.mk
[BF]: https://github.com/buildroot/buildroot/blob/75f325ad84251ee9d903467f84d3683e3bcf3fd5/package/rpi-firmware/rpi-firmware.mk
[A]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/autoboot.adoc
[B]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/boot.adoc
[E]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc
[FLOW]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc
