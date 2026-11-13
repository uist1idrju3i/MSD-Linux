# 永続storageへの書き込みの台帳

[文書の案内へ戻る](../README.md)

[AGENTS.md §10](../../AGENTS.md) の規則（利用者が意図しない時に書き込まない、2秒以上かかり得る処理ではprogressを表示する）について、現行の製品で永続storage（SDカード）に書き込む箇所と、その扱いを記録します。手順は「product-io-policy」スキル（`.agents/skills/product-io-policy/SKILL.md`）にあります。

書き込みの経路を調べた過去の記録は、[書き込み経路・read-only policy案・S3](../research/storage/write-policy-and-s3.md) にあります。この台帳は、現在の規則に照らした判定だけを書きます。

## 状態の意味

| 状態 | 意味 |
|---|---|
| 例外 | 規則の例外として認めた書き込みです。理由と時機を書きます |
| 未対応 | 規則に合わない可能性がある現行の箇所です。直すPRで状態を変えます |
| 未確認 | 書き込みがあるかどうかを、まだ測っていない箇所です |

## 現行の箇所

2026-11-12に基準commit `d7d9d622eae2f5f78dc0b891203f3641f334123b` の外部tree、生成rootfs、BusyBox・kernelの生成configとsourceを棚卸ししました。[今回の実験](../experiments/2026-11-12-write-inventory.md)ではQEMUの起動後idleにもp7への書き込みがあり、規則への適合は未達です。実機、shutdown、tryboot、障害回復の量は未測定です。

| 箇所 | 書き込み先と時機 | progress | 状態 | 扱いの案 |
|---|---|---|---|---|
| [S02msd-data](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data) の `mkfs.ext4` | 空の `/data`（p7）を、初回起動の時にformatします | なし | 未対応 | `/data` の初期暗号化を実装する時に、progressを表示する処理へ置き換えます |
| S02msd-data の `fsck.ext4 -p` | `/data` に問題があれば、起動のたびに修復を書き込みます | なし | 未対応 | 電源断の後の回復は必要なので、例外にする案です。修復した時は、そのことを表示します |
| S02msd-data の `mkdir -p` | `/data/etc`、`/data/msd-update` を、起動のたびに作ります（既にあれば書き込まない見込み、推測）。seed用directoryの作成は削除しました | なし | 未確認 | 残るdirectory作成の寄与は未分離です |
| [msd-data-grow](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow) | 初回起動の時に、partition tableを書き換え、`resize2fs` で `/data` を広げます | なし | 未対応 | 初期暗号化と同じ処理の中で、progressを表示します |
| seedrngの自動保存（旧`S05seedrng`） | post-buildでS01・S05のseed initと既定設定を除去し、S02の`/data/seedrng`作成も削除しました。起動・停止・reloadからseedrngを呼びません | なし | 対応済み | [QEMU記録](../experiments/2026-11-13-seedrng-zram.md)で新規imageのdirectory・init・設定の不在を確認しました。内蔵hwrngは維持しますが品質は未確認です。既存SDの古いseedは自動消去しません |
| [msd-update](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) の `install` | 利用者が実行した時に、待機中のslot（p2/p3、p5/p6）へ `dd ... conv=fsync` で書き、`/data/msd-update` に状態を書きます | なし | 未対応 | RAUCかSWUpdateへ移る時に、progressを表示します。利用者の操作で始まる点は規則に合います |
| [S99msd-health](../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health) からの `msd-update commit` | 試し起動（tryboot）の時だけ、`/data/msd-update` とFATの `autoboot.txt` を書きます | なし | 未対応 | 利用者が始めた更新の続きです。例外にする案で、起動の画面に更新中であることを表示します |
| ext4のjournal commit | 書き込みがある時に、既定で5秒ごとにcommitします。書き込みがなければ動かない見込みです（推測） | 対象外 | 未確認 | QEMUの記録で確かめます |
| ext4の `lazy_itable_init` | 通常imageはgenimageが `lazy_itable_init=0,lazy_journal_init=0` を付けて構築します。S02msd-dataの空partitionへのfallback formatは別経路で、これらを指定していません | なし | 未確認 | 従来の「全て既定でlazy」という推測を訂正します。fallback formatの量とresize単独の寄与は未測定です |
| online resize後の書き込み | 新規imageを1 GiBのQEMU SDへ広げたbootでは、resizeとext4lazyinit workerを観測し、最初のidle 120秒でp7に8320 sector増えました。拡張済みの再bootでも64 sector増えました | なし | 未対応 | growや初期化、journal等の寄与は未分離です。全量をlazy initと断定せず、初期設定のprogress・完了条件と一緒に設計します |
| [powerfail-notify](../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/powerfail-notify) | power-failのmdev eventでbackgroundの `sync` を呼び、既存のdirty dataをflushし得ます | なし | 未対応 | 従来の台帳の欠落です。緊急退避の例外候補ですが、許容時間・実機event・表示は未確認のままです |
| `/data` の常時rw | アプリや利用者が `/data` に作ったfileの更新に加え、ext4のmetadata・journalも永続書き込みになります | なし | 未対応 | 書き込み窓、roへの切替、`commit=`、discard等を、この調査だけで変更しません |

## RAMに置いているもの

| 対象 | 置き場所 | 根拠 |
|---|---|---|
| `/var/log`、`/var/cache` | `/tmp`（tmpfs）へのsymlink | Buildrootのskeleton |
| `/var/tmp`、`/var/spool`、`/var/lib/misc` | `/tmp`へのsymlink | 生成rootfs。`/var/lib`全体がtmpfsという意味ではありません |
| `/var/run`、`/var/lock` | `/run`、`/run/lock`へのsymlink | 生成rootfs。daemonのpid、ifupdownのifstateもここです |
| `/tmp`、`/run`、`/dev/shm` | tmpfs | [fstab](../../board/cardputerzero/rootfs-overlay/etc/fstab) |
| `/etc` の変更 | overlayのupperが `/run/etc-overlay`（tmpfs） | [S03msd-etc-overlay](../../board/cardputerzero/rootfs-overlay/etc/init.d/S03msd-etc-overlay) |
| `/dev`、`/dev/log`、inputのsymlink | devtmpfs上のnode・socket | mdev、syslogd、cardputer-keyboard。SD上のdevice fileではありません |
| hwinfo、ready、keyboard処理 | `/run/msd/hardware`、`/run/msd-ready`、`/dev/input` | S97msd-hwinfo、S98msd-ready、cardputer-keyboard |
| watchdog、sysctl、keymap、module load | device・kernelの状態。pidや診断logは `/run`・`/tmp` | S01msd-watchdog、S02sysctl、S04msd-keymap、S10mdev、S11modules。SDへの保存処理ではありません |
| 更新bundleの展開・検証 | `${TMPDIR:-/tmp}/msd-update.*` | msd-update。既定はRAMで、利用者がTMPDIRを変えた場合は別です |

tmpfs自体は圧縮していません。2026-11-13にzram swapを実装し、memory pressure時にRAMのpageを圧縮して保持します。tmpfsの配置は変えません。[今回の記録](../experiments/2026-11-13-seedrng-zram.md)と[過去のQEMU実験](../experiments/2026-10-21-qemu-zram.md)を分けて参照します。

## daemon・任意実行toolの棚卸し

生成rootfsのinitは `rcS` がS番号順、`rcK` が逆順に呼びます。startup scriptと、binaryが存在するだけのtoolを分けます。任意のアプリが任意のpathへ書く動作まで網羅した保証ではありません。

| 経路 | 現行の到達条件と書き込み先 | 判定・残る範囲 |
|---|---|---|
| syslogd / klogd | S01syslogdとS02klogdが起動。default引数は空で、klogd→syslogd→`/var/log/messages`、rotation先も同じdirectory | QEMUのprocess一覧で両daemonを確認。RAM配置を維持し、設定変更後の外部log先は再確認します |
| crond | S50crondが起動。生成BusyBoxの既定は `/etc/cron/crontabs`、logはsyslog | 現行rootfsにjobはありません。後で `/data/etc/cron` に置かれたjobはoverlayのlowerから読めるため、そのjobの書き込み先を別途審査します |
| utmp / wtmp / lastlog | `FEATURE_UTMP`・`FEATURE_WTMP`が有効。`/var/run/utmp` と `/var/log/wtmp` はRAM。BusyBoxのwtmp処理はfileを自動作成しません | lastlogを永続化するinitや専用daemonはありません。loginの実行とSDへの記録を同一視しません |
| DHCP / resolver | S40networkは現行 `auto lo` だけ。udhcpcは選択済みですが自動起動するDHCP interfaceはありません。`/etc/resolv.conf` は `/run/resolv.conf`へのsymlink | ifstate・pid・resolver更新はRAM。将来のWi-Fi・lease保存tool・server設定は未確認です |
| SSH / host key / known_hosts | Dropbear・OpenSSHは未選択。`/etc/dropbear`、host key生成init、SSHのknown_hosts更新は現行経路にありません | 導入時にhost keyの安全な永続化と保存時機を設計します。鍵を毎回RAMで作る案は採用していません |
| shell history | BusyBox ashの保存機能は有効。既定HISTFILEは `$HOME/.ash_history`、rootのHOMEはSquashFS上の `/root` | 既定pathへ永続書き込みはできません。利用者によるHOME/HISTFILE変更や、アプリの作業directory変更は別扱いです |
| hwclock / fake-hwclock | hwclock appletはありますが、呼ぶinit・cron job・fake-hwclock packageはありません。`/etc/adjtime`を作る操作はetc overlayのRAM側 | RTCへの明示書込みはSDとは別。RX8130CEの実機挙動、起動時のRTC読込みは今回未確認です |
| swap / zram / zswap | `CONFIG_ZRAM=y`、zstd backendとzsmallocもbuilt-in。S99msd-zramのbackground workerがPID 1のconsole getty／login／shell開始を待ち、1秒後にMemTotalの約50%をpriority 100でswaponします | 対応済み。QEMUでlogin prompt後の有効化と負荷時のswap使用を確認。圧縮はzstd優先、なければlzo-rle。writebackはkernelで無効にし、disk swapやbacking deviceを使いません。zswapも既定で無効です |
| core dump | `CONFIG_COREDUMP=y`、既定patternは `core`。QEMUのshellのsoft limitは0。kernelの初期RLIMIT_COREも0 | 任意のprocessがlimitと作業directoryを変えれば `/data` へcoreを書けます。全processのlimitsとcrash動作は未測定です |
| pstore / ramoops | kernel設定は有効。予約RAMを使い、SDへ回収するdaemonはありません | RAMの保持とSD永続化を区別します。panic・再起動後の回収は今回未測定です |
| atime / periodic metadata | `/data` は `noatime`、rootはSquashFS ro。tmpfsのrelatimeはRAMだけ。ext4 journal、resize、修復、`sync` は上表の経路です | atime・commit・flush・SD内部FTLを同じ量と扱いません。mount optionは変更していません |

## 決定済み項目と残る測定・判断

| 判断 | 選択肢と推奨 | 今回の扱い |
|---|---|---|
| seedの保存 | 永続保存しない方針を実装。hwrngが弱い場合に保存seedのbackupはありません | 対応済み。crng初期化時刻はQEMUで採取しましたが、実機の時刻・品質、jitterの供給経路と起動時の保証は未確認です |
| zram | 初回からbuilt-in zramを採用し、RAM約50%、zstd優先、console開始後にbackgroundで有効化 | 対応済み。QEMUの圧縮可能な負荷でswap使用とOOMなしを確認。`=y`対`=m`の単独比較、実機CPU負荷・thrash・metadata RAMの評価は未実施です |
| `/data` のmount・journal | 既存実験を材料にrw・journal・commit方針を決め、追加試験で耐電断性と書き込み量を一緒に評価します | 未対応、具体値は未決定。idleが0でも常時roの代わりにはなりません |
| format・grow・fsck・tryboot commit・powerfail | 初期設定や更新のprogress付き処理へまとめるか、理由付き例外にするか。緊急flushと回復を黙って無効にしない案を推奨します | 未対応。今回の計測で例外を承認したとは扱いません |

実SD、FTL、Wi-FiやSSHの導入後、tryboot、shutdown、crash・電源断の書き込みは未確認です。

## `/data`のmount方針を決めるための資料と追加計画

2026-11-13の決定は、既存の証拠から方針を選ぶことです。以下は判断材料と未実施の追加計画であり、mount optionの変更や新しい測定結果ではありません。

| 既存の証拠 | 方針を決める前に追加する比較 |
|---|---|
| [S03 ext4書き込み・電断](../experiments/2026-10-19-s03-data-ext4-writes.md)。4 KiB／`data=ordered`を採用したQEMU workloadと電断条件に限る | 同じ書き込み・fsync・rename負荷で常時rwと排他的なrw窓、journal方式、`commit=`の候補を一因子ずつ比較し、guest sectorと回復後の旧内容／新内容を記録します |
| [S4 fs-compare](../experiments/2026-10-30-s4-fs-compare.md)。QEMU内loop device、単一回の値 | 小さいvolumeの容量・metadata差と現在のfilesystem比較を照合し、同じ負荷で反復します。QEMUの速度を実SDの速度・耐久性に読み替えません |
| [rootfs-stay-ro](../experiments/2026-10-25-rootfs-stay-ro.md)。SquashFS rootfsのremount抑止であり、`/data`のro化ではない | 拡張前・拡張済みimageを分け、format・grow・fsck・journalの寄与、idle、起動・停止と書き込み窓の完了条件を測ります |
| [GPIO6 powerfail](../experiments/2026-10-20-qemu-powerfail-gpio6.md)。QEMUでの通知経路と実機eventは別 | 通知からsync完了まで、write中のcut時点、progress表示、復旧時のfsckと整合性を比較します。実機の電源保持時間・SD・FTLは別に測ります |

各実験は実行前に反復数・採否基準・対照を定め、raw値と失敗試行を保存します。既存の[起動直後の書き込み](../experiments/2026-11-12-write-inventory.md)の原因は未分離のままです。
