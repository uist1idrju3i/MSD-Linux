# 処理ごとの権限と可変設定の境界

[入口・基準revision](README.md) / [Linuxの仕組み](principles.md) / [通信](network.md) / [検証](verification.md)

## 現行コードから分かること

現行はBusyBox initが起動するshell scriptを中心に構成されています。以下の「提案」は専用user・helper・policyの設計案で、実装済みではありません。rootで起動する処理でも、全ての操作がrootを必要とするとは限りません。

| 処理とソース | 現行の責務・入力 | 提案する最小境界と注意 |
|---|---|---|
| PID 1、[S02msd-data](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data)、[S03msd-etc-overlay](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay) | data deviceの識別、必要時のformat、fsck、mount、etc overlay | 初期化専用の信頼処理。device・partitionを固定して検査し、通常userやnetwork parserから任意mount・formatを要求できないようにする。CAP_SYS_ADMINを通常serviceへ広げない |
| [msd-data-grow](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow) | partition tableと容量を読み、最後のdata領域を拡張 | boot領域とdata領域の境界を認可側が検査する。全diskへの書き込み能力を持つため、一般アプリへ実行権限だけを無条件に委譲しない |
| [S10mdev](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S10mdev)、[post-build](../../../board/cardputerzero/post-build.sh) | mdevの起動、sysfs modaliasからmodule load、eventに応じたhook | device作成・module load・hookの信頼処理を分けて監査する。hotplug入力をshellコマンドとして評価しない。module署名はhookとdevice権限の認可を代替しない |
| [keyboard helper](../../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/cardputer-keyboard) | tca8418cの名前を確認し、内蔵keyboardのsymlinkを管理 | input eventは現行root:root 0640のrule。一般アプリへ全input deviceの読み書きをまとめて与えない。読取りでも他の入力の観測、書込みやioctlでは操作の注入等を考慮し、必要nodeと操作を限定する |
| [S01msd-watchdog](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S01msd-watchdog)、[powerfail helper](../../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/powerfail-notify) | watchdog deviceへの定期通知、powerfail時のlogとsync | watchdogはopenしたdevice FDと必要な操作へ限定する案。rootでしかできないかはdeviceのmode・driverごとに確認する。restartとFD closeがrebootを起こす条件も試験する |
| [msd-hwinfo](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-hwinfo)、[S97](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S97msd-hwinfo) | sysfs等を読んで状態を出力 | 表示だけなら書き込み権限・network・block deviceを不要にする。取得失敗で他userへ権限を増やさない。read-only診断と設定変更を分ける |
| [msd-update](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) | archive一覧・展開、署名・hash・version検査、inactive slot書き込み、read-back、try/commit | 解析・認証・書き込みの分離候補。現行は一つの処理であり、署名前のtar解析も同じ権限で行う。特権writerへ任意path・コマンド・環境設定を渡さない |
| [S98ready](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S98msd-ready)、[S99health](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health) | ready marker、試験用module load、SquashFS/data mountとmarkerの確認後にcommit | readyの存在だけをsandbox・networkの健全性にしない。試験用起動引数も信頼入力。製品で必須のpolicyをhealth条件に追加する時は、失敗時のrollbackも試験する |

## 将来serviceの権限表

名前は役割を表す仮称です。固定UID/GIDの番号、user作成、device rule、profileは未実装であり、一般利用者のログイン方式も確認待ちです。各daemonの上流が既に提供するuser・特権分離を優先して使います。

| 役割 | user・必要な入力/FD | 書込み・通信 | 持たせない権限・IPCの認可 |
|---|---|---|---|
| 通常CLI・アプリ | 一般user、割り当てたconsoleと必要な周辺device | user自身のdata領域。通信は機能ごとに判断 | raw block、全GPIO/I2C、module load、mount、更新鍵変更。単なる同一groupを管理操作の無条件な許可にしない |
| Wi-Fi認証 | supplicantの必要なnl80211/control FD、秘密のprofile | 必要な無線認証・control socketのみ | root shell hook、AP/P2P/WPS等の不要機能。CAP_NET_ADMINが必要なら保持箇所と起動後dropの可否を上流コードで確認 |
| IP設定・DHCP | 上流のprivsep userと限定helper | lease/DUID、必要なinterfaceとroute操作 | DHCP入力から任意file・shell操作をさせない。helperへの要求はinterface・操作・長さを制限する |
| DNS・時刻 | 各専用user、限定した設定・CA、必要FD | 自身のcache、許可した上流。時刻変更は限定helper/必要capability | DNS parserに時刻変更権限、時刻parserに全data書込み等をまとめない。TLS初期時刻の扱いは[通信設計](network.md)へ分ける |
| 更新候補発見・download | 非特権user、CA・最小設定 | modeを限定したstaging領域、HTTPS | block device、boot file、管理socketの任意操作。ReleasesのAPI応答を更新認可にしない |
| 更新検証・展開 | networkなしの隔離process、上限付き入力 | boundedな作業領域と必要な出力FD | active slot、全data、mount、再起動、外向きsocket。展開内容・sizeを検査前に信用しない |
| 更新認可・writer | 短命の特権helper、信頼する公開鍵、認可済みtuple | 検査したinactive slot、限定した状態file | parserが選んだ任意device・offset・鍵・command。署名済みのhash/lengthと実際の入力bytesを独立に照合する |
| try/commit | boot状態を確認する限定操作 | P1の起動選択と既定の状態file | 一般の起動設定editorとして公開しない。healthと当該slotの対応、lock・fsync・回復を検査する |

## 書けるetcは読み取り専用rootfsの外側にある

[S03](../../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay)のlowerdirは`/data/etc:/etc`で、upper/workは`/run`です。このためrootfs内に配置したfileでも、可変層の同名fileで隠せることがあります。更新公開鍵は[post-build](../../../board/cardputerzero/post-build.sh)でetc配下へ配置され、[updater](../../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update)は実行時の設定・環境からpathを受け取ります。

これはrootfs全体のRO化が無効という意味でも、未確認の非特権攻撃が成立したという意味でもありません。**誰が可変層を書けるか、鍵・policyの正本をどこから読むか**を別途保証する必要があるという設計上の境界です。

- 更新trust anchor、必須policy、特権helperの実行file・設定は、一般userやdownloaderが隠せない場所を正本にする案です。read-only image側の正本を参照する経路と、正規の鍵更新手順を先に設計します。
- user設定、接続の秘密、更新状態、乱数seed、logは所有者と保存先を分けます。全serviceで書ける`/data`や`/data/etc`を共有しません。
- `/data`の`nodev,nosuid`や将来の`noexec`は、rootが読む設定の改変や、interpreterがdata上のscriptを読むことを一般には止めません。noexecを「データが実行されない保証」と呼びません。
- test用の`MSD_*`環境変数は現行host試験で使われています。将来管理helperを公開する時は、呼出し側のPATH、TMPDIR、鍵、version、device・state path等をそのまま引き継がない契約にします。現行CLIに非特権昇格機構があると主張しているわけではありません。

## 更新を分離しても認可を失わない

現行updaterはmemberを4つの通常fileへ制限し、署名とhashを確認してからinactive slotへ書き、read-backします。一方、展開後にimageのsizeを確認するため、取得量・展開量・CPU・作業領域には事前上限とquotaの設計が必要です。署名は、それ以前に実行するarchive parserを保護しません。

新たな分離案では、次を契約にします。自作を始める前に[更新framework](../alternatives/updates.md)の既存の検証・writerと比較します。

1. downloaderのAPI応答や「検証成功」という申告だけでは書きません。認可側は信頼鍵、署名対象bytes、機種、hash、length、更新番号、許可する操作を確認します。
2. path文字列を受け取り、あとでrootとして開き直す方式を避けます。[openat2](https://man7.org/linux/man-pages/man2/openat2.2.html)の解決制限や[FD受渡し](https://man7.org/linux/man-pages/man7/unix.7.html)は候補ですが、同じFDでも内容が不変とは限りません。検証中・書込み中の変更を防ぐ所有権・snapshot等と、実bytesのhash/length照合が必要です。
3. [sealed memfd](https://man7.org/linux/man-pages/man2/memfd_create.2.html)は小さいmetadata等の候補で、全imageを複製すれば512 MiB機器のRAMを圧迫します。上限付きdisk staging、認可側の所有する写し等とも比較し、必要RAM・SD書込み・競合を測ります。
4. UNIX socketなら接続時のpeer credentials等を確認し、渡せるFD、message種別、長さ、状態遷移を限定します。同じUIDや有効な署名だけで全管理操作を許可しません。
5. deviceの判定、inactive slot、連続した処理のlock、write/read-back/fsync、try/commitの正しさを認可側が保持します。parserへ書込み可能なboot device FDを渡せば、分離した意味を失います。

UID、AppArmor、seccomp等を何層重ねても、認可のないIPCが全ての特権操作を代行するなら、そのIPCが境界の抜け道になります。process数を増やすことではなく、侵害されたprocessに何ができないかで評価します。
