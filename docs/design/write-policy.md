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
| [S02msd-data](../../board/cardputerzero/rootfs-overlay/etc/init.d/S02msd-data) の `mkfs.ext4` | 空の `/data`（p7）を初回起動でformatします。`lazy_itable_init=0,lazy_journal_init=0` でinode tableとjournalの初期化をformat中に行います | なし（未対応） | 未対応 | 同期化しても表示は未実装です。初期暗号化とともにprogressを表示する処理へ置き換えます |
| S02msd-data の `fsck.ext4 -p` | `/data` に問題があれば、起動のたびに修復を書き込みます | なし | 未対応 | 電源断の後の回復は必要なので、例外にする案です。修復した時は、そのことを表示します |
| S02msd-data の `mkdir -p` | `/data/etc`、`/data/msd-update` を、起動のたびに作ります（既にあれば書き込まない見込み、推測）。seed用directoryの作成は削除しました | なし | 未確認 | 残るdirectory作成の寄与は未分離です |
| [msd-data-grow](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-data-grow) | 初回起動でpartition tableを書き換え、`resize2fs` で `/data` を広げます。S02の `noinit_itable` mountにより新規inode tableをgrow中に同期初期化します | なし（未対応） | 未対応 | 待ち時間と書き込みをgrow内へ移しましたが、利用者の操作やprogressはまだありません。初期暗号化と同じ処理で表示します |
| seedrngの自動保存（旧`S05seedrng`） | post-buildでS01・S05のseed initと既定設定を除去し、S02の`/data/seedrng`作成も削除しました。起動・停止・reloadからseedrngを呼びません | なし | 対応済み | [QEMU記録](../experiments/2026-11-13-seedrng-zram.md)で新規imageのdirectory・init・設定の不在を確認しました。内蔵hwrngは維持しますが品質は未確認です。既存SDの古いseedは自動消去しません |
| [msd-update](../../board/cardputerzero/rootfs-overlay/usr/sbin/msd-update) の `install` | 利用者が実行した時に、待機中のslot（p2/p3、p5/p6）へ `dd ... conv=fsync` で書き、`/data/msd-update` に状態を書きます | なし | 未対応 | RAUCかSWUpdateへ移る時に、progressを表示します。利用者の操作で始まる点は規則に合います |
| [S99msd-health](../../board/cardputerzero/rootfs-overlay/etc/init.d/S99msd-health) からの `msd-update commit` | 試し起動（tryboot）の時だけ、`/data/msd-update` とFATの `autoboot.txt` を書きます | なし | 未対応 | 利用者が始めた更新の続きです。例外にする案で、起動の画面に更新中であることを表示します |
| ext4のjournal commit | 書き込みがある時に、既定で5秒ごとにcommitします。書き込みがなければ動かない見込みです（推測） | 対象外 | 未確認 | QEMUの記録で確かめます |
| ext4の `lazy_itable_init` | 通常imageはgenimage、fallback formatはS02が `lazy_itable_init=0,lazy_journal_init=0` を指定します。S02とfstabの `noinit_itable` はbackground初期化を抑止します | なし（未対応） | 未対応 | [固定版sourceの調査](../research/storage/data-inode-initialization.md)を参照。既存SDの `INODE_UNINIT` を伴う未zero tableは未zeroのまま残ります。zero完了の判定は別flagの `ITABLE_ZEROED` です。既存tableの完了処理は未対応で、後日init_itable付きmountをすると書き込みが再開し得ます |
| online resize後の書き込み | 変更前の[帰属測定](../experiments/2026-11-15-data-first-boot-writes.md)はp7計16,952 sector。新table寸法の16,384 sectorは寄与量の推定です。新規tableをgrow中に同期初期化した[追試](../experiments/2026-11-17-data-sync-itable.md)は全3回boot 16,848＋idle1 88 sector、idle2・3は0。全groupのITABLE_ZEROEDと観測時点のext4lazyinit不在を確認しました。[残量の帰属](../experiments/2026-11-17-data-idle-residual.md)はdirectory 24、bitmap 24、inode table 16、superblock 16、GDT 8 sectorの計88。[末尾syncfsの5回比較](../experiments/2026-11-18-data-syncfs.md)はbefore boot 16,848〜16,880＋idle1 88、after boot 16,936〜16,968＋idle1・2とも0。pilotで11 home-location blockの計88 sectorがhelper終了前へ移ったことを確認しました | なし（未対応） | 未対応 | S02がgrow・mkdir等の変更後に`msd-syncfs /data`を呼び、失敗を記録して非zeroを返します。変更なしなら省略します。総量の範囲は同じで、削減・規則への適合ではありません。発行worker・timerの実値、操作別の按分、progress、実機、既存SDの残存tableは未解決です |
| [powerfail-notify](../../board/cardputerzero/rootfs-overlay/usr/libexec/msd/powerfail-notify) | power-failのmdev eventでbackgroundの `sync` を呼び、既存のdirty dataをflushし得ます | なし | 未対応 | 従来の台帳の欠落です。緊急退避の例外候補ですが、許容時間・実機event・表示は未確認のままです |
| `/data` の常時rw | アプリや利用者が `/data` に作ったfileの更新に加え、ext4のmetadata・journalも永続書き込みになります | なし | 未対応 | 書き込み窓、roへの切替、`commit=`、discard等を、この調査だけで変更しません |

## RAUC導入で追加する計画

[導入契約](rauc-update-contract.md)の後続PR②〜⑦で実装する予定の台帳である。
以下は**計画・未実装**であり、現行の未対応を解消した記録や、測定済みの例外ではない。
RAUCの自動mark-goodは利用者が始めた更新をhealth成功後に完結するためのwriteとして登録する。

| 対象 | 書込み先・時機・量の目安 | progressと見え方 | 状態・受入条件 |
|---|---|---|---|
| RAUC install | 同意・署名検証後だけinactive p2/p3・p5/p6へwrite。量はimage長を上限の基準としてfull/adaptiveで別測定 | 取得・write・read-backのbytes/割合・経過とcancel可否を英日表示 | 計画。悪署名時はp1・全slot・p7のwrite 0を⑥で検査 |
| status・adaptive index | `/data/rauc`。更新操作の間だけstatusと4 KiB block hash indexを生成・再利用・必要時再生成。indexは概算32 byte/4 KiB、metadataとjournalの量は別途測定 | index処理も更新のprogress区間に含める | 計画。background再生成・起動ごとの再生成なし。cold/warm/corruptを測る |
| custom backendのtrying | 両imageの同期・全長read-back後、`/data/rauc/bootstate`へ候補を保存。小さい状態fileだがfsync・rename・directory同期とFSのwrite量は未測定 | 次回が試し起動であることと、中断可否を英日表示 | 計画。`set-primary`ではp1の確定primaryを書かない。get-primary/get-stateはwrite 0 |
| health後の自動mark-good | 試し起動の`S99msd-health`成功後だけ、p1の`autoboot.txt`とp7のbootstate/statusを書いて確定。通常起動では同じ状態を書き直さない。FAT cluster・FS metadataを含む量は未測定 | 起動画面とconsoleで確定中・電源断不可を英日表示。2秒以上は進捗又は経過時間も表示 | 計画・自動writeの登録。更新の完結に必要。p1と/dataの原子性は仮定せず、各境界で電断後の整合を試す |
| 内部版の永続下限 | health・mark-good成功後、完了表示前に`/data/rauc`の下限を署名済みtag commitの`%ct`へ引き上げる。小さい状態fileだがFS metadata・journalを含むwrite量は未測定 | 更新確定中の英日progressと電源断不可表示に含める | 計画・未実装。replay/rollback拒否に必要。一時file・fsync・rename・directory同期を使い、失敗時は完了としない。通常起動の同値再書込みなし。中断後の回復writeも表示し、③④⑥で境界を検証 |
| 起動時reconcile | 前回の更新・確定が途切れた時だけp1・p7・実bootを照合。読取りは無書込み。回復writeが必要な場合の量は未測定 | 不整合と回復内容を英日表示し、progress付き回復処理とする | 計画。get操作内の修復は禁止。③で冪等性を試験し、実SD電断は実機で確認 |

RAUCのevent log・download buffer・lock・一時fileはRAMへ置く。
非常駐の構成を計画し、service起動時のboot ID保存を持ち込まない。
LCD・日本語fontと実SDのFTL writeは未確認で、QEMUの0件をその保証にしない。
実装PRで各行のwrite量・起動条件・表示・失敗時の動作を照合して状態を更新する。

## RAMに置いているもの

### /dataより前の入出力準備

[早期I/O](early-io.md)はS02より前に必要なmoduleだけを読み、firmware・keymapを読取り、
deviceの登録とdevtmpfsのinput symlinkを確認します。状態はtmpfsの`/run/msd-early-io/state`、
診断はconsoleとkernel logだけです。永続writeやPIN保存は追加しません。
準備期限は既定20秒で、開始・段階・待ち時間・成功失敗・中断可否を英日表示します。
失敗時はS02のformat・fsck・mountへ進みません。QEMUのdevice不在は明示された試験状態へ分けます。
LCDにまだ表示できない間はconsole出力だけです。実機画面のprogress・中断可否・英日表示の適合確認は未対応で、入力・SD writeも未確認です。
この変更は既存S02の永続writeやprogressの未対応を解消するものではありません。

S02の末尾同期の成功・失敗表示は英日併記です。consoleの日本語fontの収録文字とLCDでの見え方は未確認です。かなに限る案とfontの選定は未決定であり、既存の英語のみの表示やprogressの未対応を解消したものではありません。

2026-11-15のslot表示追加は、[03914の最終判断](../research/verification/session-decisions-2026-11-15.md#03914の判断と最終slot表示)に従います。`S98msd-ready`が`MSD/Linux ready`直前の別行に`Boot from slot A`/`Boot from slot B`、試し起動は` (try)`付き、不明は`Boot from slot ?`を表示します。この行の英語のみは利用者が承認した限定例外で、他の画面の英日併記は維持します。既存のserial出力経路と利用可能な`/dev/tty1`へ表示し、tty1がなければ作成せずskipします。`msd-update status`はDTを読むだけで、失敗時のcmdline fallbackも読取りだけです。追加の保存先はなく、既存の`/run/msd-ready`はRAMのまま、`/etc/issue`と永続storageは変更しません。LCD/firmware trybootは実機待ちです。

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
| SSH / host key / known_hosts | Dropbear・OpenSSH・PuTTYは製品未選択。`/etc/dropbear`、host key生成init、SSHのknown_hosts更新は現行経路にありません。[client限定比較](../experiments/2026-11-23-ssh-client-compare.md)はRAM内の別rootで実行しました | 未対応。clientの秘密鍵・known_hostsとserverのhost keyを分け、保存先・利用者の登録操作・progressを設計します。PuTTYのrandomseed更新も対象です。実験で永続writeの例外を承認したものではなく、鍵を毎回RAMで作る案も採用していません |
| shell history | BusyBox ashの保存機能は有効。既定HISTFILEは `$HOME/.ash_history`、rootのHOMEはSquashFS上の `/root` | 既定pathへ永続書き込みはできません。利用者によるHOME/HISTFILE変更や、アプリの作業directory変更は別扱いです |
| hwclock / fake-hwclock | hwclock appletはありますが、呼ぶinit・cron job・fake-hwclock packageはありません。`/etc/adjtime`を作る操作はetc overlayのRAM側 | RTCへの明示書込みはSDとは別。RX8130CEの実機挙動、起動時のRTC読込みは今回未確認です |
| swap / zram / zswap | `CONFIG_ZRAM=y`、zstd backendとzsmallocもbuilt-in。S99msd-zramのbackground workerがPID 1のconsole getty／login／shell開始を待ち、1秒後にMemTotalの約50%をpriority 100でswaponします | 対応済み。QEMUでlogin prompt後の有効化と負荷時のswap使用を確認。圧縮はzstd優先、なければlzo-rle。writebackはkernelで無効にし、disk swapやbacking deviceを使いません。zswapも既定で無効です |
| core dump | `CONFIG_COREDUMP=y`、既定patternは `core`。QEMUのshellのsoft limitは0。kernelの初期RLIMIT_COREも0 | 任意のprocessがlimitと作業directoryを変えれば `/data` へcoreを書けます。全processのlimitsとcrash動作は未測定です |
| pstore / ramoops | kernel設定は有効。予約RAMを使い、SDへ回収するdaemonはありません | RAMの保持とSD永続化を区別します。panic・再起動後の回収は今回未測定です |
| atime / periodic metadata | `/data` は `noatime`、rootはSquashFS ro。tmpfsのrelatimeはRAMだけ。ext4 journal、resize、修復、`sync` は上表の経路です | atime・commit・flush・SD内部FTLを同じ量と扱いません。mount optionは変更していません |

## 任意のrootfs検査（設計のみ、2026-11-16）

[任意検査command設計](rootfs-integrity-check.md)は未実装です。利用者が開始した時だけ全mapped dataを読み、SDの全partitionへの書込みを禁止します。log・lock・中間値はRAMのみで、FECは読取り結果を訂正するだけです。slot修復・切替・再起動・boot flag変更を検査から自動実行せず、書込みの例外は追加しません。2秒以上かかり得るためbytes/割合/経過と中断可否を英日表示します。panic/restart modeの危険とPhase C判断待ち、EIO・中断・観測欠損を成功にしない扱いもリンク先で定義します。commandの間接writeと既存writerの区別、QEMUでの時刻付き計測、実機SD/LCD・電断は未確認で、この行は§10適合確認済みを意味しません。

## 決定済み項目と残る測定・判断

| 判断 | 選択肢と推奨 | 今回の扱い |
|---|---|---|
| seedの保存 | 永続保存しない方針を実装。hwrngが弱い場合に保存seedのbackupはありません | 対応済み。crng初期化時刻はQEMUで採取しましたが、実機の時刻・品質、jitterの供給経路と起動時の保証は未確認です |
| zram | 初回からbuilt-in zramを採用し、RAM約50%、zstd優先、console開始後にbackgroundで有効化 | 対応済み。QEMUの圧縮可能な負荷でswap使用とOOMなしを確認。[y対m比較](../experiments/2026-11-15-zram-builtin-vs-module.md)はm側swap無効で機能非等価です。現行yを維持しますが、明示load後の利得は未測定。実機CPU負荷・thrash・metadata RAMの評価も未実施です |
| `/data` のmount・journal | 既存実験を材料にrw・journal・commit方針を決め、追加試験で耐電断性と書き込み量を一緒に評価します | 未対応、具体値は未決定。idleが0でも常時roの代わりにはなりません |
| format・grow・fsck・tryboot commit・powerfail | 初期設定や更新のprogress付き処理へまとめるか、理由付き例外にするか。緊急flushと回復を黙って無効にしない案を推奨します | 未対応。今回の計測で例外を承認したとは扱いません |

実SD、FTL、Wi-FiやSSHの導入後、tryboot、shutdown、crash・電源断の書き込みは未確認です。

## `/data`のmount方針を決めるための資料と追加計画

### E34で新たに観測した判断待ち（2026-11-15）

[E34](../experiments/2026-11-15-fs-compare-matrix.md)のQEMU内test deviceでの記録です。現行製品のwriterを追加・変更したものではなく、例外の承認でもありません。

| 構成 | 新しい観測 | §10上の状態・必要な判断 |
|---|---|---|
| f2fs F3系・P044 | idle窓で各5,736・6,720 sector、各3回。最後のwriteは144〜268秒 | 未対応。writerの同定と、利用者操作・progressの完了まで含める設計か例外登録を判断する |
| I2/L3系と関連variant | 最大88 sectorの追い書き、最後は24秒以内 | 未対応。小さい量や収束だけで適合にはしない。write終了までの操作・progress、または理由付き例外が必要 |
| btrfs B2/P097 | idle窓で各3回0 | この条件の0だけで適合済みとしない。新設計LUKS+btrfsのdata/metadata DUP・xxhash64・zstdのwriter・format/grow/回復は未測定 |

T5は18 variant中17で差を反復し、P136の増加は再現しませんでした。反復可能性をoption単独の因果や採用判断と同一視せず、03914の台帳同期保留も維持します。

2026-11-13の決定は、既存の証拠から方針を選ぶことです。以下は判断材料と未実施の追加計画であり、mount optionの変更や新しい測定結果ではありません。

| 既存の証拠 | 方針を決める前に追加する比較 |
|---|---|
| [S03 ext4書き込み・電断](../experiments/2026-10-19-s03-data-ext4-writes.md)。4 KiB／`data=ordered`を採用したQEMU workloadと電断条件に限る | 同じ書き込み・fsync・rename負荷で常時rwと排他的なrw窓、journal方式、`commit=`の候補を一因子ずつ比較し、guest sectorと回復後の旧内容／新内容を記録します |
| [S4 fs-compare](../experiments/2026-10-30-s4-fs-compare.md)。QEMU内loop device、単一回の値 | 小さいvolumeの容量・metadata差と現在のfilesystem比較を照合し、同じ負荷で反復します。QEMUの速度を実SDの速度・耐久性に読み替えません |
| [rootfs-stay-ro](../experiments/2026-10-25-rootfs-stay-ro.md)。SquashFS rootfsのremount抑止であり、`/data`のro化ではない | 拡張前・拡張済みimageを分け、format・grow・fsck・journalの寄与、idle、起動・停止と書き込み窓の完了条件を測ります |
| [GPIO6 powerfail](../experiments/2026-10-20-qemu-powerfail-gpio6.md)。QEMUでの通知経路と実機eventは別 | 通知からsync完了まで、write中のcut時点、progress表示、復旧時のfsckと整合性を比較します。実機の電源保持時間・SD・FTLは別に測ります |

各実験は実行前に反復数・採否基準・対照を定め、raw値と失敗試行を保存します。既存の[起動直後の書き込み](../experiments/2026-11-12-write-inventory.md)の原因は未分離のままです。
