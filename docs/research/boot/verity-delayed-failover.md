# 稼働後のroot破損と、確認・待機後だけのFAT切替（調査・未決定）

[保存領域の索引](../storage/README.md) / [root前のRAM counter調査](warm-reset-counter.md) / [loop防止設計](../../design/boot-loop-prevention.md)

2026-11-17。基準main `082c50e`、先行調査`62e8e41`。**tryboot成功・commit後に既定slotのSD dataが壊れる場合**を対象にします。利用者の条件は、短い間隔でのreset・電源入切中はFATへ書かず、書くとしても起動済みの系が破損を確認し、数秒待った後だけ、というものです。秒数・採用方式・書込み例外は未決定。製品code、mode候補、Phase C計画は変更しません。

【静的確認】は固定sourceと製品code、【推論】は条件付き案、【未確認】は実機・実装なしです。製品はまだSD直接SquashFS rootでdm table未実装（[現行設計:20](../../design/boot-loop-prevention.md)）。以下のdm-verity経路は**予定のmapper導入後のsource上の動作**で、現在の製品で発生した観測ではありません。kernel・Buildroot・firmwareのpinは[RAM調査](warm-reset-counter.md)にまとめています。

## 1. userspaceが破損を知れる条件

T=[固定rpi 6.18.59のdm-verity-target.c][T]。訂正後に検証を通るFEC回復と、回復不能な不一致を区別します。

| 通知・mode | sourceで確認した動作 | 待機・確認への意味 |
|---|---|---|
| corruptionのuevent（T:28-34,161-211） | hash_failedを立て、KOBJ_CHANGEを発行。DM_VERITY_ERR_BLOCK_NR=type,block、typeはdata/metadataのenum値。最初の100件がlog/ueventの対象で、その後もfatal処理は続く | netlink等で受けるconsumerは新規に必要。配送・process生存を保証せず、通知なしを健全扱いできない |
| dmsetup status（T:775-780） | 一度でもhash不一致ならC、未検出ならV。block番号・回数・全域scan完了を表さない | Cは手掛かり、Vは未読領域を含めた健全証明ではない。dmsetup導入・監視は未実装 |
| dmesg（T:190-195） | block種別・番号をrate-limit付き出力 | log欠落や上書きがあり、制御用counterにはしない |
| 指定なし＝EIO | 不正readを失敗させる。kernel全体をdm-verity自身が直ちに停止するmodeではない | consumer・そのcode/lib・必要なFSが生きていれば処理できる余地はある。ただしroot mount失敗、PID 1死亡等から別のpanicも起こる |
| ignore_corruption | 不一致dataを返して継続 | 完全性を失うため不採用方針のまま。復旧案として復活させない |
| restart_on_corruption / panic_on_corruption（T:207-211） | uevent直後にkernel_restart / panic | **userspaceが確認・数秒待機する機会は保証されない**。先に通知する順序でも猶予時間にはならない |
| restart_on_error / panic_on_error（T:535-572） | 対象I/O失敗でworkqueue restartまたはpanic。先読み、既にhash不一致のI/O、shutdown中等は除外 | corruptionと同じueventが必ず出るわけではない。E側も待機可能なpolicyが必要 |

**現候補C={restart,panic}_on_corruption×E={restart,panic}_on_errorの4組を無変更のまま、userspaceで確認後に待ってFATへ書く方式は成立しません。** EIOは以前のPhase C対象外のまま、ここでは比較として説明しています。継続可能なmodeへの再検討か、kernelでの致命処理の変更等が必要で、利用者の再判断なしに切替えません。

「確認」は単なる起動成功ではありません。【推論】mapper/slotの同定、不一致通知とstatus Cの照合等の基準が必要です。同一不良SDの再読取りだけで原因や他slotの健全性を断定しません。root上のscript・動的lib自体が壊れて動かない問題も残ります。独立した既知のcodeをRAMに置く等の対策には、別の保守負担があります。

## 2. FATを書かずに別slotを一度試せるか

【静的確認】[autoboot.txt:1-5][A]は通常2（A）、tryboot3（B）、tryboot_a_b=1です。[公式autoboot:13-40][AB]ではrebootのpartition指定が優先し、0は既定の入口を探索します。[one-shot仕様:80-98][TB]は起動前にflagをclearするので、次のresetは通常経路へ戻ります。

| 時点 | 通常boot / reboot '0 tryboot' |
|---|---|
| 配布時のselector | A(p2) / B(p3) |
| Bの更新が成功しcommitした後 | B(p3) / A(p2)。[msd-update:251-261][U]が両方を交換する |
| その後、既定Bが破損 | 0 trybootはAを一度選べる。ただし現在動作中slotの単純な反転ではなく、selectorのtryboot側を選ぶ |
| Aも失敗 | flagは既にclear済みなので次は既定Bへ戻る。A/B往復loopを防ぐには別の上限・STOPが必要 |

Linuxの数値partition引数はPM_RSTS、trybootはmailbox経由です。FAT fileの変更を伴わない要求経路ですが、**固定firmware・CM0での実動作は未確認**。dm-verityのrestart reasonは固定の非数値文字列で、無変更では0 trybootを要求できません（[RAM調査](warm-reset-counter.md)）。

現行toolをそのまま使えるとは限りません。

- [msd-update try:221-235][U]は/data/msd-update/installed、現在が既定slot、installedがtryboot側であることを要求。過去slotへの障害復帰commandではありません。
- [commit:238-269][U]はtryboot=1とinstalledの一致を要求し、成功時installedを削除します。commit済み後の旧slot復帰では通常この条件を満たしません。
- [S99msd-health:8-23][H]はtryboot=1ならroot=SquashFS、data=ext4、ready fileを見て即commitし、失敗ならrebootします。**数秒待ち・破損確認はなく、任意の旧slot trialをそのまま起動するとcommit失敗から既定へ戻る可能性があります。** 条件が揃えば待機前にFATへ書きます。
- DTのtrybootは起動時snapshotです。同じboot内でcommitしても「いまの既定slotか」をそれだけで判定できません。recovery trialの識別とS99の扱いを別途設計する必要があります。

## 3. 確認・待機した後だけ書く案（未決定）

【推論】成立の前提は、確認・表示・待機・書込みを行う実行環境が生きていることです。現在の4 fatal modeで数秒遅らせる実装はなく、下記を既存挙動とは扱いません。破損した既定rootで無理に実行するより、別slotへ無書込みで移り、そこで確認履歴を引き継ぐ案もありますが、RAM保持と旧slotの信頼・互換性が前提です。

1. 破損通知、対象slot/mapper、確認根拠をRAMだけへ保存。FATはmountするならro。boot済み・破損確認成立後に単調clockでN秒の待機を始め、reset・電断・追加異常で取消し。Nは数秒、値は未決定。未確認状態を待ち時間だけで昇格させない。
2. recovery trialではS99の通常commitを抑止する仕組みが必要。**既存codeは変更していません**。RAMが失われて識別できないときも、待機前の自動commitは禁止する案です。
3. 表示例は`Corruption confirmed. Waiting before changing boot selection.`／`はそんをかくにんしました。きどうさきをかえるまえにまちます。`。経過・残り時間と中断可否を表示。待機中の中断は無書込みで終える。
4. 根拠・対象・N秒の安定稼働を再確認して、初めてFATをrw mount。新default/tryboot値の整合を確認し、現行commitの順序「autoboot.txt.newへ出力→file fsync→rename→directory fsync→unmount」を参照する。**現行commitのguardや/data状態管理を迂回して流用しない**。復旧用の検査・再実行条件は新規に必要。
5. 書込み中は`Writing boot selection. Do not power off.`／`かきこみちゅうはでんげんをきらないでください。`等で進行状態と中断不可を示し、終わればreadbackと結果を確認。失敗時にbootごとの自動再試行をしない。STOP維持中はWDTを放置せず給餌または検証済み停止が必要。

**fsync＋renameは現行の順序であり、FAT・SD controllerの耐電断保証ではありません。** 古い状態・新しい状態・途中破損をどう回復するかは未検証です。短時間resetではN秒に届かず書かない設計にできますが、実際にwriteを始めた直後の電断リスクは残ります。

【推論】利用者の「書くならこの時機」という必要条件に合わせる案で、書込み承認そのものではありません。[AGENTS §10](../../../AGENTS.md)と[書込み台帳](../../design/write-policy.md)に、確認条件、N秒、上限回数・量、表示、取消し、失敗時STOPを登録する例外審査が必要です。既存S99の即commitも、このrecovery経路では見直し対象。表示・中断・耐電断・FAT無書込みの実機確認は未実施です。

## 4. userspaceより前に壊れている場合

| 時機・mode | 起こり得ること | root前の扱い |
|---|---|---|
| root mount、/sbin/init、libc等のreadで不一致、C fatal | kernel内でrestartまたはpanic。S00もS01も未実行になり得る | userspace確認・待機・遅延writeでは対処できない |
| 実I/O失敗、E fatal | sourceの発火条件に応じrestart/panic | 不一致ueventを待つdaemonだけでは覆えない |
| EIOでroot/initが読めない | VFS panic、init実行失敗・PID 1死亡等へ至ることがある | EIOでも起動成功・daemon生存の保証なし |
| panic、WDT daemon前 | 製品はpanic timeout既定0。停止したままの可能性 | loopは止まっても、自動復帰・英日LCDを保証しない |
| panic、WDT動作中 | S01の-T 15 -t 5によりresetし得る | panic=0だけではSTOPにできない |

init実行失敗のpanicは[init/main.c:1499-1506][I]、PID 1死亡時のpanicは[kernel/exit.c:940-942][X]も参照します。EIOであれば常にdaemonが処理できる、という意味ではありません。

root前を第一の選択肢として、[root前policy比較](pre-root-loop-policy.md)でkernel内gate、無FAT initramfs chooser、firmware段階を同条件で比較します。RAM-onlyの上限には保持の実証が必要で、pstoreのpanic記録だけでcounterは完成しません。**稼働中の確認後遅延writeと、root前の無書込みSTOPは別経路として必要性を比較し、どちらも採用しません。**

[T]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-verity-target.c
[A]: ../../../board/cardputerzero/autoboot.txt
[U]: ../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update
[H]: ../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health
[AB]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/config_txt/autoboot.adoc#L13-L40
[TB]: https://github.com/raspberrypi/documentation/blob/c6a64966af136da21a1e55551c5a395cb6987fce/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc#L80-L98
[I]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/init/main.c#L1499-L1506
[X]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/kernel/exit.c#L940-L942
