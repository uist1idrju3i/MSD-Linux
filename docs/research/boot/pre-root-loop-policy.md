# root前の無書込み復旧policy比較（調査・未決定）

[保存領域の索引](../storage/README.md) / [RAM・registerの保持事実](warm-reset-counter.md) / [稼働後の遅延切替](verity-delayed-failover.md) / [loop防止設計](../../design/boot-loop-prevention.md)

2026-11-17、基準main `082c50e`、先行調査`62e8e41`。保持の調査と分け、**userspaceより前の処理を第一の選択肢として**比較します。利用者条件は、tryboot成功・commit後の既定root破損に対し、短いreset・電源入切中はFAT無書込み、書くなら起動・破損確認・数秒待機後だけです。採用方式・待機秒数は未決定。製品変更・実験・buildはありません。

【静的確認】と【推論】を分けます。固定rpi 6.18.59 source、firmware/Buildroot pin、reset種別・RAM保持・PM_RSTSの根拠と未確認範囲は[保持調査](warm-reset-counter.md)にあります。現製品はSD直接root、dm table未実装。以下は予定のmapper導入後を検討する案で、実動作の報告ではありません。

## 1. root前で動かす場所

【静的確認】built-in ramoopsは[ram.c:976-987][RC]のpostcore_initcall、dm_initは[dm-init.c:322][DI]のlate_initcall。[init/main.c:1553-1570][IM]は基本initcall後にroot mountへ進みます。S00はrootが読めて初めて動くため「早いscript」だけではroot mountやinit/libc破損を覆いません。

次表は【推論】です。共通して短時間reset中はRAM/register操作だけでFAT writeなし、電断で状態を失い得ます。FATの遅延更新は起動できた系の別処理です。

| 段階 | 検出・loop上限 | 電断・表示・保守・未確認 |
|---|---|---|
| 既存cmdlineだけ | dm mode、panic=、reboot=、ramoops.*は設定可だがcounter判定・slot別有限試行のknobはない。panic=0でWDT非稼働なら停止候補 | 正/負panic timeoutは再起動時機だけ。WDT動作中のpanic=0はSTOPでない。初期LCD日本語も未保証 |
| kernel patch / built-in処理 | dm-verity restart/エラー処理でreasonをRAMへ記録し、root前gateが試行済みを確認して別partition/trybootまたはSTOP。正常read経路・bootへの影響を限定する実装が必要 | **kernel変更で構成する候補**。初期化・atomic性・全panic/WDT経路・ABI・更新ごとの追従負担。dm-verity patch禁止規則は調査範囲に見当たらず、禁止とはしない |
| 外付けmodule、S00、uevent consumer | root上からload/起動するだけでは早期故障より後。built-in module_init相当ならroot前へ配置し得るが新しいhook/gateは必要 | 既存moduleだけでfatal callを確実に置換する機能はない。kprobe等を製品policyの保証とはしない |
| 無FAT initramfs chooser | 独立rootでRAM recordを検査、未試行slotだけsetup/mountし、両方試行済みならSTOP | 保持消失問題は残る。kernel側の事前arm/失敗記録との協調、WDT、dm setup、表示・fontの保守負担は[先行調査](initramfs-for-loop-prevention.md)。状態writeはRAMだけにできる |
| firmware段階 | autoboot/tryboot/partition引数はroot前にboot先を選ぶ。だがLinux rootの不一致やN回失敗を判定する公開counter policyは未確認 | CM0はbootcode/start系。Pi4/5 EEPROM counter/rescueを適用しない。独自stage追加は配布・認証・保守の別設計で、現機能による解決とはしない |

kernel案では**dm_init_initの前、最初の保護対象readより前にgate完了**が必要です。initcall名だけでdriver probe完了を保証せず、RAM予約・WDT・選択元情報が揃わなければrootへ進めない案です。kernel_restartの引数を変えるだけではpanic＋WDTを覆えません。panic/IRQから通常notifier/mailboxへ安全に戻れる前提を置かず、事前armとpanic-safeな記録・reset先を別に設計します。

## 2. A→B→STOPの具体例と限界（推論）

例は既定が物理A(p2)、他方B(p3)。既定Bなら対称です。前提は同一領域が全bootで保持され、読書きが検証でき、両slotのkernel/gateが同じpolicyを持つこと。firmware・kernelが読める範囲のroot故障を対象にします。

| 状態・event | root前gateとRAMだけの更新 |
|---|---|
| 明示した新epoch、tried=0 | Aを試す前にtried=A、armed=Aを保存・検証してからrootへ進む |
| Aのhash/I/O障害、またはarmedのまま予告なしwarm reset | hash/I/O/原因不明を区別。未試行Bを一度だけ選び、Bのroot前にtried=A+B、armed=Bを保存。別partitionのkernelへ無FAT redirectする案 |
| Bも失敗、次bootのgate | tried=A+Bなのでrootを読まずSTOP。tryboot one-shotでfirmwareがAへ戻ってもgateが遮断し、再redirectしない |
| A/Bでready・health | 試行maskを自動clearしない。稼働後に同じ破損で再試行し続ける経路を作らない。正常再起動・更新・解除のルールは別途必要 |
| record不正・世代不一致・readback失敗 | STOPとする厳格案。任意に0へ初期化しない |

保持が成立する1 epochでは各slotのroot試行最大1回で有限です。正常再起動・手動resetも失敗疑いとして数える誤除外があり、healthだけのclearでは逆に稼働後loopが復活します。未読領域の完全性をhealthから推定しません。確認済み破損と原因不明resetを区別し、**後者だけを理由に数秒後FATへ書く案にはしません**。

電断後にrecordが消えれば、通常の揮発案は既定から再開し、上限は保持が成立する電源cycle内だけです。**firmwareが毎warm resetで消す場合まで「電断扱いで初期化」すると無限loopが残ります。** 全欠損をSTOPにする厳格案ならこれを避けますが、正常なcold bootにも明示解除・新epochが必要です。cold reset判別と解除手段は未確定。非SD状態のみで電断を越えた失敗履歴の保持まで保証しません。

STOPはWDTを放置して再resetする状態ではありません。停止可能性を実証するか給餌を継続し、再試行しない必要があります。S01前panicはtimeout既定0・WDT未開始なら永久停止し得て、これは自動復帰成功ではありません。[S01:8][S1]は-T 15 -t 5、[S99][S99]はroot/data/readyだけのhealthです。

serialにはkernel内で英日bytesを出す案があります。LCDはVC4/panel等のmodule・firmwareと日本語fontがroot前に使える実証がなく、**initramfsなしで英日LCD STOPを保証できません**。built-in化・必要字形の独立描画等が追加設計です。STOP例は`Both slots failed. Rewrite the SD card from a verified bundle.`／`どちらのきどうもできません。かくにんずみbundleでSDカードをつくりなおしてください。`。表示・解除・中断可否は[AGENTS §10](../../../AGENTS.md)に従い、描画は未確認です。

未確認事項はCM0固定版の各resetでの保持、cache/電源品質、予約address、hook順序、両slot互換、root前WDT制御、LCD、電断・途中更新です。QEMUでfirmware保持を検証したとはしません。**利用者の判断待ちのまま、root前の無書込みgateと、稼働後の確認・待機処理を分けて比較した調査です。**

[RC]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/fs/pstore/ram.c#L976-L987
[DI]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/drivers/md/dm-init.c#L322
[IM]: https://github.com/raspberrypi/linux/blob/b3495ea401d709af0701a85babcba5e3d788a602/init/main.c#L1553-L1570
[S1]: ../../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog
[S99]: ../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health
