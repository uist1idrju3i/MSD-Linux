# init・監視機構の詳細比較と移行費用

[比較の入口](init.md) / [代替比較の索引](README.md) / [実測計画](../../experiments/2026-11-03-init-comparison-plan.md)

## 判断の要約

2026-11-03の静的調査です。**採用は未決定で、代替構成のbuild・起動・実機試験は本リポジトリでは試していません。** 小ささを理由にBusyBoxを残す判断も、多機能さを理由にsystemdへ移す判断も、まだできません。PID 1単体ではなく、同じ製品機能を満たす構成全体を比べます。

実測の第一群は、現行BusyBox init + mdev、systemdの必要最小構成、BusyBox init + s6監視、s6-linux-init + s6-rc、OpenRC + supervise-daemonです。DinitとFinitは、外部package・起動統合の成立を先に確かめる第二群にします。機能不足を理由に除外したのではなく、固定Buildrootの統合費用を先に見積もるためです。runitは監視だけを加える対照、SysVinitは既存scriptを残す対照とします。

procdとGNU Shepherdは条件付き候補に残します。OpenWrtの周辺基盤ごと採るか、Guileによる動的な管理を製品で必要とするかが再評価条件です。supervisord、daemontools、コンテナー用の小さなinitは、OS全体の同等な置換ではなく補助部品です。

## 出典の版と限界

取得URL・時刻・HTTP状態・応答hashは[出典台帳](init-sources.json)、上流のbranch・license表示・公開状態の観察は[保守情報](init-maintenance.json)に保存します。取得と内容確認は別です。台帳には404、未認証APIの403、GNUのmanual URLが本文ではなくhomepageを返した例、Savannah取得失敗も残します。

固定Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`です。recipeの存在は、MSD/LinuxでPID 1として起動できる証拠ではありません。2026-11-03時点の`package/`ではDinit、Finit、runit、procd、Shepherdのrecipeは見つかりませんでした。外部treeの追加方法は[実測計画](../../experiments/2026-11-03-init-comparison-plan.md)で別の作業にします。

| 構成 | 固定recipeの版・license表示 | 版を混同しないための注意 |
|---|---|---|
| BusyBox | 1.38.0、GPL-2.0ほか | appletごとの条件・licenseは別確認。BusyBox内のrunit系appletと上流runitは同一実装ではない |
| systemd | 258.7、LGPL-2.1+ほか | Buildrootの依存・選択条件を優先。開発branchのmusl対応を固定recipeへ読み替えない |
| s6 / s6-linux-init / s6-rc | 2.13.1.0 / 1.1.2.1 / 0.5.5.0、ISC | 上流s6の入口は2.15.1.1。新しい説明・依存条件を固定版へ無条件に移さない |
| skalibs / execline | 2.14.3.0 / 2.9.6.1、ISC | 上流s6の入口はskalibs 2.16.0.0以上、execline 2.10.0.0以上を説明。組合せを勝手に更新しない |
| OpenRC | 0.56、BSD-2-Clause | この版のmanとservice guideで照合。上流branchの機能とは区別 |
| SysVinit | 3.14、GPL-2.0+ | inittabの監視機能を「監視なし」としない |
| eudev | 3.2.14、GPL-2.0+ / LGPL-2.1+ | 独立device manager。initの置換とは別の選択 |

この表は法的レビューではありません。生成binary・リンクするライブラリー・同梱scriptのlicense、ソース提供、noticeを、候補ごとのSBOM・legal-infoで再照合します。保守情報の更新時刻や`archived=false`も、security response・保守期限・支援契約の保証ではありません。利用料金だけでなく、統合・更新追従・障害解析・拒否試験を維持する費用を記録します。

## 役割ごとの比較

| 構成 | PID 1・起動依存・readiness | 継続監視・停止 | 権限と資源 | 別に必要なもの |
|---|---|---|---|---|
| BusyBox init + mdev | inittabと順次script。製品の依存・ready判定は自作部分 | respawn対象と一度きりのscriptを区別。通常daemonの失敗連動は別設計 | user切替・capability・seccomp等は各daemonまたは補助処理 | device rule、service graph、ログ・network・healthの契約 |
| systemd | native unit、依存と順序、`Type=notify`等を選択 | restart制限、timeout、cgroup単位の終了等。ただし設定とkernel機能が必要 | user、capability、namespace、seccomp、resource control等を組合せ | udev rule移行、製品health、更新helper、通信・ログの方針 |
| BusyBox + s6 | PID 1は現状維持。s6だけでは全起動graphにならない | 長期processをs6-superviseで監視 | setuidgidだけで全sandboxにはならない | 起動・停止との連携、依存manager、device・mount |
| s6-linux-init + s6-rc | 生成initとs6-svscan、oneshot/longrunの依存graph、通知FD | superviseとfinish、逆依存順停止。失敗連動の方針は別確認 | UID/GID等の小部品と必要な制限helperを構成 | runtime DB、mount、mdev、ログ、capability/cgroup等の統合 |
| OpenRC | openrc-initまたは別PID 1、runlevelとneed/use等 | supervise-daemonかs6を明示。単なるscript実行と区別 | UID/GID、capability、no-new-privs等は監視側のoption・buildに依存 | device・ログ・mountのscriptと製品health |
| Dinit | PID 1にもuser managerにも使用。依存種別、pipe通知 | restart上限・間隔、起動/停止timeout、依存停止の扱い | run-as、rlimit、任意buildのcapability/cgroup | device、cgroupの準備・予算、ログrotation、外部recipe |
| Finit | run/task/serviceと条件、systemd/s6方式のready通知 | restart上限、停止期限、hookとreload | user/group、rlimit、任意capability、cgroup v2 | device、ログ、条件の対応、外部recipeと周辺library |
| runit | 3段階initを構成可能。依存は待機script等で補う | runsv/finish、sv制御、svlogd。restart予算は別確認 | chpstのUID/GID・rlimit等。完全sandboxではない | device、依存graph、通知の製品契約、mount/更新統合 |
| SysVinit | inittab・runlevel。製品S scriptの移植量は比較的小さい候補 | respawnの抑制あり。一般serviceのgraph・意味的readyは別 | 各service script/helperで制限 | 継続監視、device、制限・ログ・更新との接続 |

共通して、起動順を待つだけの関係と「失敗したら起動させない」関係を分けます。依存先processが生存していても応答しない場合、ready通知後に不健全になった場合、停止時に子processが逃げる場合を試します。service managerのroot権限やD-Bus/制御socketへ到達できる主体も攻撃面です。

## s6系: 部品を組む費用を含める

[s6-supervise](https://skarnet.org/software/s6/s6-supervise.html)は`run`、`finish`、制御と通知を担当します。[readiness](https://skarnet.org/software/s6/notifywhenup.html)は`notification-fd`へdaemonが通知する方式で、process開始の`u`とreadyの`U`は同じではありません。通知できないdaemonへ`s6-notifyoncheck`を使う場合も、検査の意味、頻度、期限、偽陽性を製品側で決めます。

[s6-rc](https://skarnet.org/software/s6-rc/overview.html)はoneshotとlongrunを依存DBへまとめ、DBを事前compileし、可変なlive状態を`/run`等へ置きます。`dependencies.d`、`notification-fd`、`timeout-up/down`を使います。timeoutの未指定や0を無期限のまま放置しません。依存先が一度readyになった後の故障で、製品として何を止めるかは実験で確認します。

[s6-linux-init](https://skarnet.org/software/s6-linux-init/overview.html)はinit生成と初期・最終停止処理を担い、service managerとの接点は`rc.init`、`rc.shutdown`、`runlevel`等です。Buildrootのpackageを選ぶだけでは、この接続もmdev coldplugも完成しません。生成したearly getty、環境、catch-all loggerを含め、復旧consoleがlogin方針を迂回しないか確認します。

利点は責務を小さく分け、PID 1を変えず監視だけを足す比較もできることです。一方、script群、DB生成、停止、ログ、権限helperをMSD/Linuxで保守する費用が増えます。s6が小さいことを、同等な隔離を足した構成全体が小さい証拠にはしません。固定版で使う機能はbuild時に同梱manual・help・sourceへ戻って確認します。

## OpenRC: scriptと監視を分ける

[0.56のopenrc-run](https://raw.githubusercontent.com/OpenRC/openrc/0.56/man/openrc-run.8)には依存関係と`command_user`があり、監視は`supervisor=supervise-daemon`または`s6`を明示します。未指定・無効なsupervisorではstart-stop-daemonが使われるため、OpenRCへ変更しただけで全daemonを継続監視するとは限りません。

[0.56のsupervise-daemon](https://raw.githubusercontent.com/OpenRC/openrc/0.56/man/supervise-daemon.8)にはhealthcheck、respawn-delay/max/period、user/group、capability IAB、security bits、no-new-privs等があります。systemd以外に権限制限がないという評価は不正確です。ただし、hookがどの権限で走るか、子processの停止、resource accounting、device accessの境界は別確認です。

Buildrootには`BR2_INIT_OPENRC`と専用skeletonがあります。mount、clock、modules、getty等の既定serviceが製品scriptと重複しないよう、起動と停止を全件対応づけます。既存shell資産を利用しやすい候補ですが、SysVと同じ名前・引数のscriptを置けば正しい依存になるとはしません。

## Dinit: 小さな依存managerと任意機能

[v0.22.1のREADME](https://raw.githubusercontent.com/davmac314/dinit/v0.22.1/README.md)と[service定義](https://raw.githubusercontent.com/davmac314/dinit/v0.22.1/doc/manpages/dinit-service.5.m4)を基準にします。公式入口の版表示と開発branchの表示が異なるため、masterの機能を公開版の証拠にはしません。Apache-2.0の表示は上流情報であり、同梱Dasynq等も別に調べます。

`process`、`bgprocess`、`scripted`等、`depends-on`と`waits-for`、`ready-notification=pipefd/pipevar`、restart-delay/limit、start/stop-timeoutが比較点です。`waits-for`は依存先の失敗でも先へ進むため、更新commitや必須mountへ無条件に使いません。通知を設定しないprocess serviceは実行開始を起動済みと扱い、意味的readinessにはなりません。

`run-as`、rlimit、capability IAB、`no-new-privs`がありますが、後二者はcapability対応buildが条件です。`run-in-cgroup`もbuild条件付きで、cgroupは事前に作成済みである必要があります。groupを選ぶ機能だけで、作成・委譲・CPU/RAM予算まで管理済みとはしません。socketのFD受け渡しprotocolの互換と、要求時だけ起動するsocket activationも区別します。

利点は一つのmanagerへ依存・通知・再起動をまとめられることです。外部recipe、cross-build、C++ runtime、PID 1の初期mount・signal・shutdown、loggerとdevice managerの接続が追加費用です。既成の統合を流用できるかを先に調べ、自作のPID 1や依存resolverは作りません。

## Finit: 組込み向けの条件・通知・制限

上流は旧troglobit名から[finit-project/finit](https://github.com/finit-project/finit)へ移っています。[4.17の設定](https://raw.githubusercontent.com/finit-project/finit/4.17/man/finit.conf.5)と[configure.ac](https://raw.githubusercontent.com/finit-project/finit/4.17/configure.ac)を確認しました。MITの表示、libuev 2.4.1以上、libite 2.6.1以上、任意libcap等を、rootfsとhost buildの追加費用に含めます。

`run/task/service/sysv`、条件、`notify:systemd/s6`、restart回数、停止期限、pre/post/ready/cleanup hook、user/group、rlimit、cgroup v2が比較点です。通知protocolが共通でもsystemd unitをそのまま読めるという意味ではありません。libcapが見つからないbuildではcapability機能が無効になる経路があり、configure成功だけで権限制限済みとはしません。

小型組込み向け候補として残します。条件名と依存故障、hookの権限、設定reload、device/hotplug、ログ、read-only root、A/B更新を実際の製品契約へ結ぶ試験が必要です。上流の説明だけでsystemdと同等、あるいは軽量と断定しません。

## runit・SysVinit・監視専用tool

[runitの導入資料](https://smarden.org/runit/install.html)は2.3.1を示します。古い2.1系の公開年だけを理由に候補から外しません。[runsv](https://smarden.org/runit/runsv.8.html)、`sv`、`chpst`、`svlogd`で監視・制御・権限変更・ログを組めます。依存待ち、意味的ready、再起動stormの上限、停止時の全子process回収は別の製品契約です。単純なrestart間隔と、一定時間内の上限は同じではありません。

[SysVinit 3.14のinit](https://raw.githubusercontent.com/slicer69/sysvinit/3.14/man/init.8)には、短時間の過剰なrespawnを抑える処理があります。「依存graphやsandboxが不足する」と「監視が一切ない」は分けます。BusyBox initの動作も同一と仮定せず、固定版と製品inittabを確認します。

[supervisord](https://supervisord.org/introduction.html)はPID 1の置換を目的にしない監視機構で、Python等を含む費用があります。[daemontools](https://cr.yp.to/daemontools.html)も監視の比較にはなりますが、mount・device・OS停止を含む構成が別に要ります。コンテナー用initの孤児回収・signal転送を、CardputerZeroのboot managerと同等には扱いません。これらは第一群を置き換える候補ではなく、必要な責務だけの対照です。

## procd・GNU Shepherdを再評価する条件

[OpenWrtのprocd](https://openwrt.org/docs/techref/procd)と[service定義](https://openwrt.org/docs/guide-developer/procd-init-scripts)にはrespawn、event、user、limits、jail、seccomp、capability、no-new-privs等があります。固定した[build定義](https://raw.githubusercontent.com/openwrt/procd/fea76294a68196c633cd2f323a6958f8c0d25648/CMakeLists.txt)はubox、ubus、json-c、blobmsg_json、json_script、udebug等を参照します。ujail側のUCI等、rc.commonとshell library、logging、hotplug、network連携まで移植範囲を数えます。

取得したservice.cのheaderはLGPL-2.1を示しますが、repo全体・ujail・内包物のlicenseをこの一例から確定しません。OpenWrtの通信管理を広く再利用する設計なら再評価します。現行BuildrootへPID 1だけ移す案には、周辺基盤を持ち込む費用が大きいため、最初の性能比較では保留します。

[GNU Shepherdの公式入口](https://www.gnu.org/software/shepherd/)はGuile Scheme、PID 1またはuser manager、socket/inetd/timer、ログ関連serviceを説明しています。manualの個別URLは期待した本文を返さなかったため、細かな権限制限・restart・依存失敗の仕様は未確認です。機能がないとは判断しません。Guile、配布物のlicense、rootfs、設定を実行可能なSchemeで記述する信頼境界を調べ、動的なuser service等が必要になった場合に外部recipeから試します。

## MSD/Linux固有の移行契約

1. **read-only rootと可変設定**: 現行`S03msd-etc-overlay`は`/data/etc:/etc`をlowerとするOverlayFSを作り、`/etc`へbindします。unit・service定義・環境・device ruleを可変領域から隠せる境界と、managerがbind前後に設定を読む不一致が問題です。実行policyは不変側、可変設定は明示した項目だけにする案を全候補へ共通に適用して試します。単に`ProtectSystem=`やnoexecを付けても解決しません。
2. **起動helper**: watchdog、data検査・fsck・拡張、`/etc`、keymap、seedrng、mdev、hwinfo、ready、tryboot healthを全件移植します。post-buildが`S05seedrng`と`S98msd-ready`を要求するため、overlayだけの差替えでは不十分です。
3. **自動commit**: 現行S99はtryboot時にrootがSquashFS、dataがext4、ready fileがあることを見てcommitします。全周辺機器・network・継続healthの証明ではありません。互換試験と、強くした新healthの試験を分け、候補だけ条件を軽くしません。
4. **deviceとwatchdog**: systemdのudevとmdevを二重起動しません。各候補はcold/hotplug、module、owner/mode、input・I2C・GPIO・V4L2・音声・USBを照合します。watchdogも既存daemonとPID 1側で二重にopenせず、所有者、feed停止、15秒timeoutと更新・fsckの長時間処理を確認します。
5. **systemd特有の費用**: 固定recipeはglibc、D-Bus、merged-/usrとmerged-bin、libcap、libxcrypt、util-linux、kmod、timezone等を選びます。v258はcgroup v1を削除しv2を前提にします。kernelの自動fixup、namespace/seccomp、tmpfs ACL/xattrまで差分を保存します。journald、networkd、resolved、timesyncd等は必要性と実効configを個別に記録し、全suiteを必要最小構成と呼びません。
6. **セキュリティの比較**: UID/GID、group、capability各集合、no-new-privs、FD、namespace、device、resource、制御socket、hookを観測し、禁止操作が失敗することを試します。AppArmor・firewall・更新署名はinitとは別のpolicyです。DynamicUser等の有無だけで優劣を決めず、永続dataの所有、offline UID、認可helperの数とroot code量まで比較します。

## 次の判断と費用

第一群の構成成立を一度ずつ確認し、成立した候補だけを同じ計測器で反復します。設定・rootfs・kernelの差分、移植したservice数、自作helperと特権処理、上流の追従範囲を台帳に残します。第二群はrecipe・license・PID 1統合が成立したら同じ門を通します。候補ごとの数値がない段階で順位を確定しません。

可変`/etc`、未認証root、更新の権限分離、firewall、AppArmor、鍵更新をinit選定だけで完了扱いにはしません。公開版と内部anti-rollback番号の契約、login方針は利用者の判断待ちです。[残件台帳](../roadmap.md)と[実測計画](../../experiments/2026-11-03-init-comparison-plan.md)で、実装・実測・実機・承認を追跡します。
