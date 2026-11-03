# init・service監視・device管理の代替

[代替比較の索引](README.md)へ戻る。

## 結論と確認範囲

BusyBox initとmdevを比較基準に残し、常駐serviceが増える段階で、PID 1を変えずにs6等の監視を加える構成を先に試す案を勧めます。systemd、OpenRC、Dinitも候補に残します。小さいことだけを目的に自作の再起動・依存管理を増やすより、既存の監視・権限制限を再利用した方が総費用を下げる可能性があります。

これは採用決定ではありません。代替init/supervisorの製品build・実行、RAM・起動時間等の比較は本リポジトリでは試していません。現行ソースは`8aaf2e1958fd71b571a2f40cbe8199409c931c37`、Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`を基準に、2026-11-02に一次資料を確認しました。取得の状態・ref・hashは[sources.json](sources.json)に記録します。

## 四つの役割を分ける

| 役割 | 必要な契約 | 同じものとして扱わないこと |
|---|---|---|
| PID 1 | 初期化、孤児processの回収、signal、停止・rebootへの遷移 | serviceを一度起動するscriptと、processを監視し続ける仕組み |
| service管理 | foreground process、起動依存、readiness、異常停止後の処理、停止順 | processが存在することと、Wi-Fi・DNS・更新に使えること |
| device管理 | devtmpfs上のnode、所有権・mode、hotplug/coldplug、module load | PID 1を変えればmdev/udevの規則も自動で移行するという仮定 |
| 権限制限・記録 | UID/GID、capability、FD、file/device access、resource制限、log | supervisorがrootだから全子processもrootでよい、あるいはsupervisionだけでsandboxになるという仮定 |

どれも製品のtarget/runtimeです。構築時のservice定義生成器・依存graph compiler・test helperはhost/build-timeにも分けます。kernelのLSM・seccomp・namespace対応と、userspaceの実効policyは別に確認します。

## 現行の起動契約

設定採取では`BR2_INIT_BUSYBOX=y`、`BR2_ROOTFS_DEVICE_CREATION_DYNAMIC_MDEV=y`です。[system/Config.in](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/system/Config.in)の選択肢と、製品の[init scripts](../../../board/cardputerzero/rootfs-overlay/etc/init.d)を照合しました。

| script | 現行の役割 | 移行時に確認すること |
|---|---|---|
| S01msd-watchdog | watchdog開始 | bootの失敗・停止時にも適切にwatchdogが働くか |
| S02msd-data | blank判定、fsck、制限付きmount、data拡張 | 未知の非空領域を拒否する条件と、異常時の動作を保存する |
| S03msd-etc-overlay | `/data/etc`と既定`/etc`を使うtmpfs overlay | 書込可能なservice定義で特権を増やせないか。起動順と復旧を確認 |
| S04msd-keymap | keymap読込み | console・キーボードの復旧経路を失わないか |
| S10mdev | daemon起動、sysfs coldplugとmodule load | nodeのmode/owner、module集合、hotplug、停止後の再起動を確認 |
| S97msd-hwinfo / S98msd-ready | 構成情報とready marker | initの起動完了と製品の利用可能状態を混同しない |
| S99msd-health | tryboot時のroot/data/ready確認、commitまたはreboot | serviceの再起動loop中に更新を確定しない。A/Bのrollbackと停止順を保存 |

既存scriptがあることは、全serviceに専用UID・capability制限・sandboxが実効化されている証拠ではありません。Wi-Fi、DNS、更新取得を追加する前に、rootが必要な設定操作と、非特権にできるparser・取得処理を分ける必要があります。

## 候補と導入費用

| 候補 | 機能と利点 | 主な背反・統合作業 | 提案 |
|---|---|---|---|
| BusyBox init + mdev | 現行の小さな起動経路。inittabと既存scriptを維持できる | scriptの起動成功だけでは常駐serviceの継続監視・readiness・権限制限にならない | **現行維持**。service増加に合わせ監視不足を評価 |
| BusyBox PID 1 + s6 | foreground daemonの監視・再起動・log等を追加できる（I1） | scan directory、停止連携、readiness、専用UID、log容量とrestart制限の設計が必要 | **実験候補**。まず少数の常駐serviceだけで比較 |
| s6-linux-init + 必要ならs6-rc | s6-svscanをPID 1にする構成と、別packageの依存管理（I1/I2） | 初期mount、生成設定、shutdown、console、A/B healthの移植。複数packageの版をそろえる | **実験候補**。監視だけの追加と分けて検証 |
| runit | 3段階のinit、runsvによる監視、svlogd、chpst等（I3） | 依存はdaemonの再試行やsv/check scriptでも表す。明示graphと同じ仕組みではない。recipeとboot統合が必要 | **実験候補**。s6と同じ機能・失敗条件で比較 |
| OpenRC | dependencyに基づく起動・停止。system提供のinitとの連携を説明する（I4） | PID 1、監視、起動scriptをそれぞれ確認。固定Buildrootではlibcap、ncurses、kmod等の選択も増える | **実験候補**。既存起動処理との重複を除く |
| systemd | service依存・監視と宣言的な権限制限をまとめて扱える（I5） | 選択する機能と依存が広い。unit、cgroup、udev、log・永続領域、usr構成、更新・復旧を一体で設計 | **実験候補**。「大きい」という印象だけで除外しない |
| Dinit | 依存付きsupervision。system/user serviceとPID 1を扱い、依存serviceを含む再起動を説明する（I6） | C++と内包Dasynqも依存として扱う。recipe・cross build・boot統合・policyの確認が必要 | **実験候補**。統合費用を含めて比較 |
| tini / catatonit | container内の子process起動・回収等を目的とする（I7） | 本機のmount・device・更新確定・停止までを提供するhost OS設計とは役割が違う | **用途限定**。CardputerZeroの全initを置き換える案にはしない |

s6本体、s6-linux-init、s6-rc、container向けのs6-overlayは別の部品です。s6本体を追加するために、最初からPID 1や全serviceを置き換える必要はありません。一方、部分導入でもwatchdog・停止・A/B healthとの整合を検証する必要があります。

## 上流の対応と固定Buildrootの条件

| 対象 | 固定Buildrootで確認したこと | 上流との違い・残件 |
|---|---|---|
| s6 | 2.13.1.0。execlineを選択し、その依存にskalibsがある | 上流の新しいs6-linux-init 1.2.0.2は、s6/skalibs 2.15.1.0以降、execline 2.9.9.2以降を要求する。単独更新で組み合わせられるとはしない |
| s6-linux-init / s6-rc | 1.1.2.1 / 0.5.5.0。packageはあるが、汎用のinit選択肢にs6はない | binaryのinstallと、使えるPID 1・生成設定・service graphの用意を区別する |
| OpenRC | 0.56。動的library、glibcまたはmuslを要する選択条件。kmod/tools・libcap・ncurses、glibcならlibxcrypt等を選択 | 上流READMEのPAM付きstatic非対応という説明と、固定recipeの制約を混同しない |
| systemd | init選択にglibc・動的library・thread・SSP・headers等の条件がある | 確認した開発HEADのREADMEにはmusl 1.2.6以降の条件とcontainer向けstatic PID 1の説明がある。上流を永久にglibc専用・static不可能とは評価しない |
| runit / Dinit | 同名のpackage directoryは固定treeで確認できない | 別名・外部packageの有無、選ぶ安定版、AArch64/Cortex-A53、toolchain、kernel・cross条件を採用前に閉じる |

上流systemdの開発HEADは安定releaseの証拠ではありません。APIで取得した最新安定releaseは`v262.1`ですが、そのREADMEが開発HEADと同じ条件かは別に照合する必要があります。Dinitの確認したREADMEは`v0.23.0pre`でした。OpenRCとDinitのlatest Release APIの404も、tagや保守が存在しない意味にはしません。[libc比較](libc.md)と同じく、init・libc・device管理を一度に変更して原因を曖昧にしない方針です。

表の依存は固定recipeで確認できた必須・条件付きの例です。候補構成を生成していないため、target/host別の閉じたpackage数、実際に残るlibraryとhelper数は未確認です。AArch64対応表やC/C++での実装だけでは、本機の命令・syscall・shutdown・周辺deviceの動作を保証できません。

## 最小特権と安全な既定値

systemdの`User=`・`Group=`・`CapabilityBoundingSet=`・`NoNewPrivileges=`・`ProtectSystem=`・`PrivateDevices=`・`SystemCallFilter=`等は、制限を宣言する候補です（I5）。ただし、`NoNewPrivileges`は既に持つ権限を全て落とす指定ではありません。deviceを隠す設定も、LCD・audio・input・GPIO・update書込みを必要とするserviceへ一律に適用できません。kernel・library・unit設定と、拒否された実動作まで確認します。

s6/runit/DinitやBusyBoxでも、専用UID/GID、不要なgroup・capabilityの放棄、限定したFD、read-only mount、seccomp/Landlock等を組み合わせる設計は可能です。しかし、supervisorを入れただけでその制限が付くわけではありません。共通の小さな実行wrapperと定義で済むか、再実装が増えるかをsystemdの統合機能と比較します。

比較の際は、rootが必要なmount・module・device設定と、取得・構文解析・表示を分けます。service定義・control socket・log directoryのowner/mode、渡す環境変数とFD、restart storm、停止不能、disk fullを確認します。永続logの書込み量と秘密値の混入、tmpfs logを失う場合の診断費用も評価対象です。これらは実装前の条件であり、現行製品の保護を認定するものではありません。

## 保守・ライセンス・見送り理由の再評価

- **BusyBox**: [基本コマンド比較](commands.md)のsource・patch・license条件を引き継ぎます。全appletを残すことも、起動traceだけで削ることも既定の結論にはしません。
- **s6系**: 公式はISC。s6-linux-initのshared/staticによって、skalibs等がbuild時だけかboot時にも必要かが変わります（I1/I2）。全packageを一つの版・license・security窓口とみなしません。今回読んだ資料だけでは固定版のsecurity保守期間を確定できません。
- **runit**: 公式から案内されたGit treeのCOPYINGはBSD-3-Clause相当の3条件を定めます。source/binaryでnotice等を保持し、著者名を無断の推奨に使わない条件です。CHANGESには2.3.1とその後の変更があるため、古い2.1.2だけを見て保守停止とは評価しません。選ぶrelease・patch・security窓口・全fileの配布条件は採用前に照合します。公式の小さなPID 1という設計と運用例は本機の測定ではありません（I3）。
- **OpenRC**: LICENSEはBSD-2-Clause。選ぶ依存・helperのlicenseは別です。上流は生成AI/LLMによるcontributionを受け付けない方針も明記しています。使用・再配布の条件とは分け、上流へ報告・貢献する人手と方針順守も保守費用に含めます（I4）。
- **systemd**: READMEは原則LGPL-2.1-or-laterで、例外をLICENSES/READMEへ案内しています。その一覧ではudevのprogram等がGPL-2.0-or-later、kernel由来headersにはsyscall例外等があり、runtime・headers・試験・helperを分けています。実際に配布するfile/binaryのSPDXとlicenseを閉じる必要があります。SECURITYは非公開報告・実際の境界違反を示すreproducerを求め、解決時期は保証していません（I5）。
- **Dinit**: LICENSEはApache-2.0。内包Dasynq、C++ runtime、build/testを別に照合します。README・設計資料とNEWSを取得したことは、全履歴・全依存の監査完了ではありません（I6）。

過去の「小型initが常に有利」「systemdは大きいので不採用」「serviceが少ないので監視は不要」という判断は固定しません。network・更新取得・権限制限が増えるなら、独立部品の統合費用を含めて再比較します。ただし、導入候補の数や設定可能項目の多さを、現行より安全という根拠にはしません。

## 採用前の比較試験

以下は未実施です。同じlibc・kernel・必要service・ログ方針・周辺機能をそろえます。

1. 起動順とreadinessを明示し、正常・起動失敗・再起動・signal・依存先消失・停止・rebootを試します。親子process、孤児の回収、restart上限、watchdogも記録します。
2. UID/GID・group・capability・namespace・mount・FD・control socket・device nodeを実物で採取します。期待する操作が通り、禁止したfile/device/syscallへの操作が拒否されることを確かめます。
3. data初期化・overlay・console・hotplug/coldplug・全M5 moduleと周辺機能を確認します。mdev/udevの切替は別条件とし、udev採用をsystemd導入の無検証な副作用にしません。
4. A/B起動、health条件不足、署名拒否、network不通、read-onlyやdisk full、電源断・rollbackを試します。ネットワーク障害が無限restartや誤commitになる構成を拒否します。
5. image/依存/最大RAM/process数/FD数/boot・stop・build時間/log書込みを5回以上記録します。上流のサイズ例や別機種の測定と分け、初回・失敗・復旧費用も比較します。

## 一次資料

| 記号 | 資料と読んだ範囲 |
|---|---|
| I1 | [s6](https://skarnet.org/software/s6/)、[overview](https://skarnet.org/software/s6/overview.html)。supervisionと周辺packageの役割、logging、policy |
| I2 | [s6-linux-init](https://skarnet.org/software/s6-linux-init/)、固定Buildrootの[s6](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/s6/s6.mk)・[s6-linux-init](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/s6-linux-init/s6-linux-init.mk)・[s6-rc](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/s6-rc/s6-rc.mk)。PID 1、版、依存、license |
| I3 | [runit](https://smarden.org/runit/)、[依存](https://smarden.org/runit/dependencies.html)、[chpst](https://smarden.org/runit/chpst.8.html)、公式から案内されたGitの[COPYING](https://github.com/g-pape/runit/blob/0735b3f0ffb1bca58e9aadf5016b6172c47e9c69/COPYING)と[CHANGES](https://github.com/g-pape/runit/blob/0735b3f0ffb1bca58e9aadf5016b6172c47e9c69/package/CHANGES)。3段階、監視・再試行とcheck、UID/GID、license、近年の変更。全履歴の精読ではなく、古い運用例の数値は比較に使っていない |
| I4 | [OpenRC README](https://github.com/OpenRC/openrc/blob/14e11b7f5b09072aa1433e790bbf832800858fec/README.md)、[LICENSE](https://github.com/OpenRC/openrc/blob/14e11b7f5b09072aa1433e790bbf832800858fec/LICENSE)、[Meson設定](https://github.com/OpenRC/openrc/blob/14e11b7f5b09072aa1433e790bbf832800858fec/meson_options.txt)、固定Buildrootの[設定](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/package/openrc/Config.in)。init連携・構築条件・上流方針 |
| I5 | [systemd README](https://github.com/systemd/systemd/blob/f6613445d97a2c0fba2a5ea8578c3168963b9d59/README)、[license区分](https://github.com/systemd/systemd/blob/f6613445d97a2c0fba2a5ea8578c3168963b9d59/LICENSES/README.md)、[SECURITY](https://github.com/systemd/systemd/blob/f6613445d97a2c0fba2a5ea8578c3168963b9d59/docs/SECURITY.md)、[systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)。構築・依存と権限制限の関連節。manual全体の精読ではない |
| I6 | [Dinit README](https://github.com/davmac314/dinit/blob/e518520e7c6bb63f14b3061e9f1c9fe7da813b43/README.md)、[設計](https://github.com/davmac314/dinit/blob/e518520e7c6bb63f14b3061e9f1c9fe7da813b43/doc/DESIGN)、[LICENSE](https://github.com/davmac314/dinit/blob/e518520e7c6bb63f14b3061e9f1c9fe7da813b43/LICENSE)。service・PID 1・C++/内包依存 |
| I7 | 固定Buildrootの[init選択](https://github.com/buildroot/buildroot/blob/8b238854d909c9cce32ef9671d968b03e323b55d/system/Config.in)。tini/catatonitの用途と、initごとのtoolchain条件 |
