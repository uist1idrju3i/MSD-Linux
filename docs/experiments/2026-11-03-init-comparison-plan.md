# init移行を判断する比較実験の計画

[実験一覧](README.md) / [候補の詳細比較](../research/alternatives/init-detail.md) / [残件と判断待ち](../research/roadmap.md)

**状態: 計画のみ。systemd・代替initのbuild、QEMU、実機計測は未実施です。** この記録は製品切替の承認や、候補の実測結果ではありません。生データの空欄を0や成功で埋めません。計測器・故障試験・結果形式の詳細は[試験手順](2026-11-03-init-comparison-protocol.md)に分けます。

## 目的と仮説

現在のBusyBox init + mdevから、依存・readiness・継続監視・権限制限を既存実装で補う構成へ移る便益と費用を測ります。未リリースなので破壊的変更も候補に含めますが、A/B更新と復旧の安全条件は緩めません。

- H1: systemdの必要最小構成で、既存機能を保ち、rootで実行する自作処理と権限制御の不足を減らせる。
- H2: s6系・OpenRC・Dinit・Finit等でも必要な契約を満たし、より少ない資源または保守費用で済む構成がある。
- H3: PID 1だけを変えるより、可変`/etc`、health、watchdog・deviceの所有者を先に明確にする方が安全性へ寄与する。

いずれも仮説です。設定項目の数、kernel hardeningのスコア、上流の採用例だけでは実証しません。

## 基準と固定入力

計画のソース基準は`1670bdd`です。実行開始前にこのcommitを完全SHAへ展開し、候補patchを含む各commitを確定します。Buildrootは`8b238854d909c9cce32ef9671d968b03e323b55d`、systemd recipeは258.7です。libcは現行のBootlin外部glibcを保ち、libcやtoolchainの更新実験を同時にしません。

| 入力 | 固定と採取の方法 |
|---|---|
| checkout | 独立cloneを使い、git worktreeではbuildしない。基準・patch・submodule SHA、dirty差分のhashを保存する |
| Docker | `docker/msd-dev`の入力tag、実際のimage ID、RepoDigestの有無、CPU archを保存。公開digestがないlocal buildを公開digest確認済みとは書かない |
| toolchain | Docker内で実際に起動したtarget compilerのpath・hash・`--version`・`-dumpmachine`・`-print-sysroot`、libc実物と版、host compilerを記録。VMのcompilerへ置換しない |
| kernel | source SHA、patch、fragment、最終`.config`、vmlinuxとImageのhash、module一覧、cmdlineを保存。候補が要求する自動fixup後の差分を検査 |
| 製品payload | firmware、DT/DTBO、keymap、rootfs overlay、更新helper、trust anchor、seedrng、genimage設定、package一覧と各hashを固定 |
| build | 各条件に専用`O=`とccache directory。download cacheは検証済み同一内容。build並列数、outputの初期状態、cold/warm、cache統計を保存 |
| QEMU | Docker内の実binaryの版・hashとpatch、machine、CPU/RAM、TCG thread、icount設定、実行CLI、host kernel/CPU/負荷を保存 |
| 実機 | CardputerZero/CM0の個体・回路rev、RAM、boot EEPROM/firmware、UART、SD型番・個体・使用履歴、給電、温度、周辺機器、radio/AP条件を記録 |

GCC、glibc、QEMU等の**実際に使用するbinaryの版・hashは、この計画では未採取**です。既存文書の値を転記して採取済みにしません。buildrootのhost packageはビルド側で動くpackageであり、VMへ直接入れたtoolchainを正とする意味ではありません。

## 比較群と交絡の分離

| 群 | 構成 | 役割 |
|---|---|---|
| A0 | 現行BusyBox init + mdev | 出荷候補そのままの基準。初回data準備と通常起動を分離 |
| A1 | BusyBox init + mdev、比較用の共通kernel・directory構成 | systemdに不可避なkernel/merged-/usr等の正規化費用を測る。A0との差を隠さない |
| B | systemd 258.7 + udev、必要最小の選択 | A1と比較。udev・D-Bus・追加libraryを含む構成全体の差であり、PID 1単独の差とは呼ばない |
| C1 / C2 | BusyBox + s6監視 / s6-linux-init + s6-rc + mdev | 監視追加とPID 1移行を分離。固定recipe一式で開始 |
| D | OpenRC 0.56 + supervise-daemon + mdev | 専用skeleton、監視、停止を移植 |
| E / F | Dinit / Finit + mdev | 外部recipe・cross-build・license・初期化が成立した場合に同じ試験へ追加 |
| 対照 | runitの監視追加、SysVinit | 単純な監視と既存script再利用の費用。第一群の結果次第で追加 |

候補の第一群はA0/A1/B/C1/C2/Dです。全候補へ直ちに重い反復buildをかけず、構成成立の一回検査で絞ります。E/Fは性能が劣るから後回しにしたのではありません。procd、Shepherd等の条件付き候補は[詳細比較](../research/alternatives/init-detail.md)の再評価条件を使います。

共通kernelは全候補が必要とする設定の和から作り、最終configと**同じImage hash**を確認できた比較だけを同一kernelと呼びます。BのBuildroot fixupが更に変えたら停止して共通kernelを作り直し、A1を再生成します。機能削減で速くするために候補だけ異なるkernelを使いません。A0→A1の追加コストと、A1→候補の追加コストをそれぞれ表示します。正規化不能なら構成全体の比較へ格下げし、因果をPID 1へ限定しません。

アプリ・firmwareの共通payloadは一致を確認し、init・device・library・unit/script・directory・kernel等の許容差分を理由付きallowlistへ書きます。使われない許可行、説明のないpackage増減、古いstamp・別`O=`からの混入は失敗です。不要な依存をA1へ足して差を小さく見せません。

各候補にP0「現行機能互換」とP1「同じ権限・health契約」を設けます。P0は現行root/data/readyによる自動commitを含む互換確認、P1はcommit前の強いhealthと制限を全候補へ同じ意味で課す比較です。既存の弱い判定を候補だけ改善して、その性能差をinit単独の費用とはしません。Bだけ全部のsystemd suiteを有効にすることも、Bだけlogging/networkを省くこともしません。

## 構成を成立させる門

この順序は実験の依存関係であり、今回実装した手順ではありません。

1. **設定**: 新しい実験専用defconfig/外部packageを既存のcloneへ作り、最終Kconfigを解決する。選択不能・依存追加・licenseを保存する。vendorは直接編集しない。
2. **移植**: watchdog、data検査/fsck/拡張、`/etc`、keymap、seedrng、mdev/udev、hwinfo、ready、tryboot healthをserviceごとに対応づける。post-buildのS05/S98前提、fstab検査、getty、shutdownも条件別に直す。単にsystemdを選び、旧S scriptが自動実行されると仮定しない。
3. **信頼境界**: 可変`/data/etc`がunit・service script・環境・udev rule・認可設定を上書きできない配置案を実験branchへ作る。managerが`/etc` bind前に読んだ設定との不一致も確認する。設定の互換破壊と既存data移行を別に記録する。
4. **build**: 候補ごとのclean buildを一度行い、rootfs、SBOM/legal-info、package/file/ELF依存、起動artifact、partition寸法を検査する。build可能という判定だけに使い、性能結論には使わない。
5. **QEMU成立**: A/B両slot、通常/tryboot/復旧、readiness、停止、module、ログを一度ずつ確認する。kernel・SDモデルが表せない項目を実機へ残す。
6. **計測器**: A/A、既知の遅延・RAM負荷・失敗注入、marker順序・終了値で計測系を検証する。通るまで本計測を始めない。
7. **反復**: 同じprofile・状態の5回以上を測定し、ばらつきが大きければ原因を調べて新しいrun IDで追加する。
8. **実機**: 機材と安全条件を確認し、犠牲にできるSDと復旧手段で測る。QEMU成功を実機合格に繰り上げない。

## 測る値と場所

| 分野 | 値・動作 | 証拠の範囲 |
|---|---|---|
| 構築 | config・kernel差分、依存/自作helper/特権処理の数、clean/warm build時間、CPU時間、disk peak、cache hit/miss | Docker内。構成成立は1回、時間比較は各状態5回以上 |
| 容量 | 展開rootfs、SquashFS bytes、kernel/modules、boot領域、SD image、A/B各slot余裕、SBOM/license/notice増分 | 生成物。圧縮前後、見掛けと割当済みbytesを別列 |
| 起動 | 電源投入、kernel最初のUART、PID 1 helper、data/etc/coldplug完了、製品ready、login、network/DNS、tryboot commitの時刻・順序 | QEMUはvirtual/host wallを分離。実機は電源・UARTを同一host clockへ同期 |
| 資源 | process全体のPSS、cgroup memory.current/peak、MemAvailable最小、kernel/slab、FD、process数、CPU、steady状態、startup peak | ゲスト。PID 1のRSSだけでOS全体を比較しない |
| 監視 | crash/hang、依存失敗、ready前終了、restart storm、timeout、停止順、子process、reload、設定破損 | QEMUと実機。想定拒否と試験器の失敗を区別 |
| device | cold/hotplug、firmware/module、owner/group/mode、mdev/udev rule、接続・切断後の権限 | QEMUは表せる機器だけ。I2C/GPIO/LCD/音声等は実機 |
| 通信 | Wi-Fi認証、link、DHCP、DNS、切断・再接続、firewall前の送受信、更新の通信権限 | network機能は現行未完成。initの合格だけで対応済みとしない |
| 安全 | read-only root、`/etc`、data mount、UID/GID/capability、FD/device、namespace、cgroup、AppArmor/認可helperの拒否 | P1。設定だけでなく禁止操作と残存権限を検査 |
| 更新・復旧 | 正常/不正bundle、slot選択、rollback、anti-rollback、commit時点、watchdog、GPIO6、SysRq、停止・再起動 | QEMUは既存モデルの範囲。真のtryboot・電断・SD永続性は実機 |
| 記録・電力 | log量・rotation・RAM/永続領域の書込bytes、電断後の読取、boot/shutdownエネルギー、idle電力 | 書込観測はguestとhostを分離。電力は外部計測器が必要 |

## 採否基準の初期案

以下は**実測前に固定する予算案**です。製品の確定仕様ではありません。実行前に利用者と数値・機材制約を確認して版を固定し、結果を見て閾値だけを緩めません。変更した場合は旧試行を残し、新しい計画版と新しい試行群にします。

| 指標 | 初期案 |
|---|---|
| 正常性 | build、A/B起動、ready、停止、更新・復旧、device権限の必須試験が全て合格。欠測・skipは合格に含めない |
| ready時間 | A0比の通常起動中央値の増分が0.5秒以下かつ10%以下。初回data準備は別群。最大値と各試行も報告 |
| steady RAM | 全体PSS増分16 MiB以下、かつ実機の使用可能RAMの5%以下。RSS/PSS/cgroupの重複計上はしない |
| peak RAM | A0比32 MiB以下の増分、かつ負荷後MemAvailableの最小64 MiB以上。使えるRAMは実機で確認 |
| SquashFS | 圧縮後の増分16 MiB以下かつ25%以下。固定slotに10%以上の余裕。SD imageのpartition寸法は維持 |
| CPU・ログ | idle CPU平均の増分1 percentage point以下。idleの永続logは10分で1 MiB以下、rotationで決めた上限を超えない |
| 電力 | idle平均+5%以下、bootと正常停止のenergy増分+10%以下。計測器の誤差以内なら差がないと断定しない |
| 復旧・停止 | 正常停止30秒以内。fault後の既知good slot到達はA0比+5秒以下、かつ120秒以内。watchdog所有者は一つ |
| 監視 | 必須serviceの未ready・故障で誤commitしない。試験用crash serviceのrestartは60秒に5回以下で、その後は定義した停止・復旧へ移る |
| 保守・安全性 | 同等機能の特権処理・自作helperが増える場合は理由と長期保守先を示す。root継続を不要にできたserviceと拒否試験を少なくとも一組示す |

重大な機能欠落、誤commit、復旧不能、署名・anti-rollback境界の破壊、可変領域からの実行policy上書きが未制御、禁止操作の成功は、性能が良くても不合格です。A0自体がP1の安全条件に失敗した場合も記録し、現行だから免除はしません。

各指標を満たすだけで採用は確定しません。便益・移植費用・依存・CVE追従・復旧操作を併記し、Pareto比較で利用者に採否を提示します。将来のWi-Fi・更新client・sandboxを含むP1の価値と、P0の小ささを混同しません。

## 実施量・費用・停止点

構成成立の一回検査は候補ごとに行い、失敗した候補の重い反復は止めます。成立後のbuild性能はclean/warmを各5回以上、bootは初回/通常を各5回以上、故障はscenarioごと5回以上を基本とします。初回起動は各回同じ初期SDから復元し、通常起動とは混ぜません。

候補数×profile数×反復数の総run数、予想runner時間・download/ccache/OCI転送量・保存量・実機作業を実行前に見積もります。実験は専用branchで行い、CIの通常PRへ重い反復を追加しません。5回は最小の比較であり、低頻度故障の安全証明ではありません。実機電断の拡張試験はscenarioを層別した200回以上の案とし、機材・時間・カード寿命・停止条件の確認後に別記録で実施します。

今回は調査と計画だけをコミットします。次の開始条件は、構成成立用patch・共通の計測器・予算の固定です。実機未入手、実験承認待ち、機材未対応、上流資料未取得等を明示し、待ちの項目を成功にしません。
