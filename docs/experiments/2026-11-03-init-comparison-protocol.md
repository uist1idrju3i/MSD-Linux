# init比較の計測器・故障試験・結果形式

[比較の計画と採否基準](2026-11-03-init-comparison-plan.md) / [実験一覧](README.md)

**この文書は未実装の試験仕様です。** runnerが完成した、測定できたという記録ではありません。実装後のCLIと再実行コマンドは、その実装commitと結果記録へ追記します。存在しないrunnerのコマンドを実行済みとして示しません。

## 共通readinessと起動順

現在の`S98msd-ready`はfileを作ってからmodule試験・console markerへ進みます。PID 1の起動完了、default target、`/run/msd-ready`、`MSD/Linux ready`、login、network ready、tryboot commitは別の事象です。時刻が同じ値になるように一つのmarkerから代用しません。

P0では現行helperの意味を保って移植し、その弱い境界も記録します。P1では不変な共通helperがroot/data/設定境界・必須service・deviceの準備を検査して通知します。networkが起動に必須か任意かをprofileで固定し、offline端末の正常起動と更新のnetwork readinessを分けます。manager固有の通知はこのhelperから接続し、候補ごとにreadyの意味を変えません。

| 事象 | 採取と確認 |
|---|---|
| 電源・kernel | 実機は外部電源計測器のtriggerとUART収録を同じhost monotonic clockへ対応づける。QEMUには実電源投入時刻がない |
| PID 1・初期mount | 最初の実験helperでguest uptimeとboot IDを記録。kernel開始と同一ではない |
| data・etc・device | fsck終了・mount成功・grow状態、設定読込点、coldplug/module/rule完了を別markerにする |
| 製品ready | 共通helperの検査結果と通知、console/kmsgの位置を保存。fileだけの存在を十分条件にしない |
| login・通信・commit | getty到達と認証試験、link/IP/DNS/認可、更新commitの監査を別々に採取 |

serial出力の遅延がbootを変えるため、同じbaud・console level・記録方式を使います。QEMUのicount virtual timeとhost wall timeは別列とし、TCGのhost速度を実機bootの改善と呼びません。UARTと電力のclock offset・分解能・欠落を計測します。

## 計測器の事前検証

1. 同一binary・同一初期SD・同一cache状態のA/Aを最低5回行い、中央値・最小・最大と元の全行を出す。差が大きい場合は温度・host負荷・並列・出力状態を先に調べる。
2. ready直前へ既知の1秒遅延を入れる対照を作り、遅延がready以降に現れ、kernelやそれ以前のmarkerに混入しないことを確認する。
3. 既知の16 MiBを確保し各pageへ書く試験processを加え、PSS/cgroup/使用可能RAMが方向と大きさに反応することを確認する。zero pageだけの確保を負荷としない。
4. 起動失敗・ready未通知・marker逆順・重複・欠測・非有限値・後続の非0終了を入力し、成功markerがあっても集計器が拒否することを確認する。
5. watchdog feedを止める対照と、電源操作をしない対照を分け、reboot原因・slot・stateが判定できることを確認する。QEMUのresetを実電源断に読み替えない。
6. 不正bundleや禁止操作の試験器自身を故障させ、期待した拒否と単なるcommand-not-found・timeoutを区別する。

採取hookを有効にした条件と無効の条件をA/Aで比較し、計測の侵襲を報告します。採取周期の初期案はstartup 100 ms、steady 1秒で10分です。これで捉えられない短いpeakはcgroup peak等を併用し、周期を変えたら別群にします。cold/warmはbuild・host cache・guest初期data・電源再投入をそれぞれ明記し、曖昧な「cold」一語で済ませません。

## 故障・拒否scenario

| ID | 操作 | 合格の観測点 | 場所と限界 |
|---|---|---|---|
| F01 | 必須依存を失敗・欠落・timeoutにする | 後続がready/commitしない、原因と復旧が分かる | host/QEMU、実機 |
| F02 | ready前/後のdaemon crash、hang、孫processを作る | restart方針・停止範囲・予算・子process回収が仕様どおり | QEMU、実機 |
| F03 | 連続crash、停止拒否、設定reload失敗 | storm上限・timeout・逆依存停止・回復手順が働く | QEMU、実機 |
| F04 | unit/script/env/ruleを`/data/etc`から差し替える | 未認可な実行policyにならず、起動前後とreload後も同じ境界 | QEMU、実機。壊してよいdataを使う |
| F05 | root/data mount失敗、未知の非空data、fsckエラー、満杯 | 誤format・誤commitせず、復旧とログに到達する | QEMUのモデルが表す範囲と実機を分離 |
| F06 | device抜差し、module失敗、group外userのopen | 正しいrule/権限、拒否、復帰、切断時の停止 | 仮想deviceと実I2C/USB等を区別 |
| F07 | DHCP/DNS/認証失敗、radio切断、firewall前通信 | 任意networkでbootを壊さず、更新等の必須通信は未readyになる | AP・radio・packet captureは実機/適切なnetwork環境 |
| F08 | 別鍵・改変・切断・古い番号・異形式bundle | 検証前書込・誤slot切替・downgradeを拒否し状態不変 | host/guestと実媒体の永続性を分離 |
| F09 | 正常更新、試験起動失敗、watchdog feed停止 | A/B・自動commit・rollback・root/data状態を確認 | QEMUは実firmware trybootの証明ではない |
| F10 | 更新の各永続化点、fsck、grow、shutdownの電断 | 既知good slotへ復帰、署名/rollback状態に矛盾なし | 実機。QEMU SIGKILLは補助試験 |
| F11 | log flood、満杯、電断、時計の巻戻り | bounded storage、起動を妨げない、ログ欠落と破損を検出 | QEMUと実機。全ログ完全保存を要求しない |
| F12 | UID/GID/capability/FD/device/namespaceの禁止操作 | 拒否理由とkernel実効状態が一致、制御socketやhookで迂回できない | P1。profile未実装なら未試験 |
| F13 | GPIO6、watchdog、SysRq remountと正常停止の競合 | 所有者・feed・remount・復旧の順が破綻しない | 実回路・充電・給電は実機のみ |

data・ログ・boot file・anti-rollbackの保存点ごとに試験を分けます。実機電断はcurrent/voltageの許容範囲、MCUやcharger、カード寿命、復旧consoleとimageを確認してから行い、利用者の機材を無断で破壊的試験へ使いません。重大な破損・異常発熱・復旧不能なら即停止し、元ログとmediaを保全します。

## 資源・容量・保守費用の採取

PSSは全processの`smaps_rollup`等から採り、共有pageをRSS合計で重複計上しません。権限やkernel設定で採取不能なら欠測にし、RSSをPSS列へ代入しません。cgroup値はuser/kernel accountingを含み得る別指標で、PSSへ足しません。`/proc/meminfo`、slab、全process/FD数、PID 1と依存daemonの内訳も採取します。cgroupがないA0のpeakは同じ指標へ代用せず、共通指標と候補固有指標を分けます。

rootfsは展開file tree、ELFのdynamic依存、package/license、圧縮後SquashFS、kernel/modules、boot file、slot容量を比較します。SD imageはsparse fileの見掛けと割当bytesを分離します。machine-id、random seed、SSH host key等を固定して良い測定条件と、製品で個体ごとに生成すべき秘密を区別し、本番鍵を使いません。

ログは揮発・永続の保存先、容量上限、rotation、rate limit、権限、書込bytesを揃えます。journaldだけを永続化し対照を無記録にする比較はしません。daemonのUID/GID・capability、rootで解釈する設定とscript、認可helper、制御socket、package/CVE/更新主体、自作コード量を差分一覧へ保存します。行数の少なさだけで保守性や安全性を判定しません。

## 実行と保存の契約

runnerは候補、profile、scenario、反復、初期SD、出力先、QEMU条件を**CLI引数**で受け取り、wrapperが転送しない環境変数に依存しません。既存の出力先・CSVがあれば上書きせず失敗します。root権限が必要な実機操作は対象deviceと確認を別の段階へ分けます。通常製品imageへ計測hookを残しません。

各runを`metadata.json`、入力/生成物のhash manifest、解決済みconfig、コマンドと終了値、serial/guest/host/電源ログ、`results.csv`、`checks.csv`で一組にします。CSVの列は次を初期仕様とします。

```text
run_id,plan_revision,source_commit,patch_sha256,image_sha256,kernel_sha256,qemu_sha256,oci_id,host_arch,target_id,variant,profile,scenario,repeat,build_state,guest_state,clock,metric,unit,value,status,exit_code,reason,log_path,log_sha256
```

`status`は`passed/failed/untested/aborted`を使い、欠測の`value`は空欄にします。`reason`を必須とし、期待どおり拒否した試験は`checks.csv`で具体的な不変条件を示します。単にprocessのexit 1を成功へ変換しません。run IDとmetric/clockの組を一意にし、非有限値・重複・反復不足・hash不一致・ログ不在を拒否します。

全試行の状態を先に集計し、成功した同一条件だけの中央値・最小・最大・絶対差・比率を出します。失敗・中止・未試験数、除外理由、順番とraw値を併記します。0に近い基準の比率は無理に算出しません。A/Bの順序はseed付きで交互または無作為化し、warm-upは別IDで残します。最低5回の値から信頼性やp95を主張しません。

生ログは一時領域だけに置かず、恒久的artifactまたは管理された証拠保管先へ保存し、取得方法・期限・hashを結果記録へ書きます。1 MBを超えるCSVや大きなログは分離し、記録から追えるようにします。作業clone/outputを消す前にコピーの数とhashを照合します。実行中のrunnerは編集せず、修正は別版と新run IDで行います。

## 完了と未確認の表示

構成成立、計測器検証、QEMU比較、実機機能、実機電断、採否判断を別々に報告します。QEMUのSDモデルがguestへエラーを伝えない既存の制約、firmware tryboot・実SD・周辺回路の非模擬は残します。networkやAppArmorが未実装なら、無効なまま「非回帰」とせず該当試験を未実施にします。

結果の報告時は計画版、実commit/binary、条件と全CSV列、失敗ログ、各門の合否を読み、候補ごとの未確認を残します。採用後も実機の実用負荷と更新を追試するまで、CardputerZeroの全機能対応やrelease準備完了とはしません。
